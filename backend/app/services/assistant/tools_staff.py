"""Tools for faculty / placement officers and administrators. Each needs the same permission as the matching screen."""
from typing import Literal

from pydantic import Field, model_validator
from sqlalchemy import func, or_, select

from ...enums import ApplicationStatus, EligibilityState, RoleName, UserStatus
from ...errors import NotFound, ValidationFailed
from ...models import (
    AcademicYear, Application, AuditLog, Company, Course, Department, Job, PlacementPolicy, Student, User,
)
from ...serializers import iso
from ..admin_service import dashboard as admin_dashboard
from ..applications_service import STATUS_LABEL
from ..companies_service import detail as company_detail
from ..companies_service import list_companies
from ..eligibility import evaluate
from ..interviews_service import list_interviews
from ..jobs_service import get_job
from ..offers_service import list_staff as staff_offers
from ..reports_service import faculty_dashboard, placement_report
from ..review_service import list_applications
from ..students_service import detail as student_detail
from ..students_service import list_students
from ..users_service import list_users, roles_overview
from . import charts, reports
from .framework import STAFF, Args, Context, NoArgs, cannot, propose, tool
from .tools_student import chart_result, job_brief

ADMIN = (RoleName.ADMIN,)
STAGES = Literal["all", "applied", "shortlisted", "interview", "selected", "offer_received", "rejected", "withdrawn"]
PLACEMENT = Literal["unplaced", "in_process", "placed", "opted_out"]


def dept_id(db, code: str | None) -> int | None:
    if not code:
        return None
    d = db.scalar(select(Department).where(func.lower(Department.code) == code.strip().lower()))
    if not d:
        raise ValidationFailed(f"Unknown department '{code}'. Use a code such as CSE, IT, ECE.")
    return d.id


# ---------------------------------------------------------------- charts & reports
class ChartArgs(Args):
    metric: Literal[tuple(charts.STAFF_METRICS)]
    chart_type: Literal["pie", "donut", "bar", "hbar", "stacked", "line", "area"] | None = None
    department: str | None = Field(None, max_length=16, description="Department code, e.g. CSE")
    graduation_year: int | None = Field(None, ge=2000, le=2100)


@tool("show_chart", "Show a chart of placement data. The server computes the numbers; you choose the metric and style.",
      ChartArgs, roles=STAFF, perms=("students.view", "reports.view", "applications.review"))
def show_chart(ctx: Context, a: ChartArgs):
    did = dept_id(ctx.db, a.department)
    return chart_result(ctx, *charts.staff_chart(ctx.db, ctx.user, a.metric, a.chart_type, did, a.graduation_year, a.department))


class ReportArgs(Args):
    report_type: Literal[tuple(reports.REPORT_PERMS)]
    job_id: int | None = Field(None, ge=1)
    status: str | None = Field(None, max_length=20)
    department: str | None = Field(None, max_length=16)
    graduation_year: int | None = Field(None, ge=2000, le=2100)
    min_cgpa: float | None = Field(None, ge=0, le=10)
    placement_status: PLACEMENT | None = None
    account_type: Literal["all", "admin", "faculty", "student"] | None = None
    result: Literal["all", "success", "denied", "failed"] | None = None


@tool("generate_report", "Build a full report (KPIs, tables, charts) that is shown to the user; then write a short executive summary.",
      ReportArgs, roles=STAFF, perms=("reports.view", "students.view", "applications.review", "offers.manage", "users.manage",
                                      "audit.view", "companies.manage", "jobs.create"))
def generate_report(ctx: Context, a: ReportArgs):
    if len(ctx.reports) >= 2:
        return cannot("At most two reports per reply.", "too_many_reports")
    if a.status and a.status not in [s.value for s in ApplicationStatus] + ["received", "accepted", "declined", "withdrawn", "pending",
                                                                            "scheduled", "completed", "cancelled", "no_show"]:
        return cannot("Unknown status.", "invalid_arguments")
    report = reports.build(ctx.db, ctx.user, a.report_type, a, dept_id(ctx.db, a.department))
    from ..audit import record
    record(ctx.db, "report.generate", report["title"], actor=ctx.user, reason=f"Assistant report: {a.report_type}")
    ctx.db.commit()
    ctx.reports.append(report)
    return reports.preview(report)


# ---------------------------------------------------------------- applicants, students, companies, offers
class ApplicantsArgs(Args):
    job_id: int | None = Field(None, ge=1)
    status: STAGES = "all"
    limit: int = Field(15, ge=1, le=25)


@tool("get_applicants", "List applicants (optionally for one job or stage). No contact details.", ApplicantsArgs,
      roles=STAFF, perms=("applications.review",))
def get_applicants(ctx: Context, a: ApplicantsArgs):
    f = {"q": None, "status": None if a.status == "all" else a.status, "company_id": None, "job_id": a.job_id, "dept": None, "eligibility": None, "sort": None}
    items, total = list_applications(ctx.db, ctx.user, f, 1, a.limit)
    return {"total": total, "applicants": [{
        "applicationId": v["application"]["id"], "name": v["student"]["name"], "studentCode": v["student"]["studentCode"],
        "department": v["student"].get("departmentCode"), "cgpa": v["student"]["academic"].get("cgpa"),
        "cgpaVerified": v["student"]["academic"]["cgpaVerified"], "title": v["job"]["title"], "company": v["company"]["name"],
        "stage": v["application"]["status"], "eligibilityAtApply": (v["application"].get("eligibilitySnapshot") or {}).get("state"),
        "appliedAt": v["application"]["appliedAt"]} for v in items]}


class EligibleArgs(Args):
    job_id: int = Field(ge=1)
    limit: int = Field(15, ge=1, le=25)


@tool("find_eligible_students", "Which students meet a job's eligibility rules.", EligibleArgs, roles=STAFF, perms=("students.view",))
def find_eligible_students(ctx: Context, a: EligibleArgs):
    job = ctx.db.get(Job, a.job_id)
    if not job:
        raise NotFound("Job not found.")
    get_job(ctx.db, ctx.user, a.job_id)
    students = ctx.db.scalars(select(Student)).unique().all()
    ok = [s for s in students if evaluate(ctx.db, s, job, ignore_open=True)["state"] == EligibilityState.ELIGIBLE]
    ok.sort(key=lambda s: -(float(s.academic.cgpa) if s.academic and s.academic.cgpa is not None else 0))
    ctx.remember_jobs([job.id])
    return {"jobId": str(job.id), "title": job.title, "company": job.company.name,
            "jobAcceptingApplications": job.status == "published", "studentsEvaluated": len(students), "totalEligible": len(ok),
            "students": [{"name": s.user.name, "studentCode": s.student_code, "department": s.department.code,
                          "cgpa": float(s.academic.cgpa) if s.academic and s.academic.cgpa is not None else None} for s in ok[:a.limit]],
            "truncated": len(ok) > a.limit, "note": "Eligibility ignores whether the job is still open, and requires a verified CGPA."}


class ScheduleArgs(Args):
    job_id: int | None = Field(None, ge=1)
    status: Literal["all", "scheduled", "completed", "cancelled", "no_show"] = "scheduled"
    limit: int = Field(10, ge=1, le=20)


@tool("get_interview_schedule", "Interview rounds and their candidates.", ScheduleArgs, roles=STAFF, perms=("applications.review",))
def get_interview_schedule(ctx: Context, a: ScheduleArgs):
    items, total = list_interviews(ctx.db, ctx.user, a.job_id, None if a.status == "all" else a.status, 1, a.limit)
    return {"total": total, "interviews": [{
        "round": i["interview"]["round"], "title": i["job"]["title"], "company": i["company"]["name"], "at": i["interview"]["at"],
        "location": i["interview"]["location"], "status": i["interview"]["status"], "candidateCount": len(i["candidates"]),
        "candidates": [{"name": c["name"], "studentCode": c["studentCode"], "stage": c["status"]} for c in i["candidates"][:10]]} for i in items]}


@tool("get_offers_overview", "Offer totals by department and company, and how many selected students still have no offer.",
      roles=STAFF, perms=("offers.manage",))
def get_offers_overview(ctx: Context, a: NoArgs):
    items, _, meta = staff_offers(ctx.db, ctx.user, {"q": None, "status": None, "dept": None, "company_id": None}, 1, 5)
    return {"totals": meta["totals"], "byDepartment": meta["byDept"], "byCompany": meta["byCompany"][:15],
            "selectedWithoutOffer": len(meta["selectedWithoutOffer"]),
            "recentOffers": [{"studentCode": o["student"]["studentCode"], "company": o["company"]["name"], "title": o["job"]["title"],
                              "ctcLpa": o["offer"]["ctcLpa"], "status": o["offer"]["status"]} for o in items]}


class StatsArgs(Args):
    department: str | None = Field(None, max_length=16)
    graduation_year: int | None = Field(None, ge=2000, le=2100)
    company_id: int | None = Field(None, ge=1)


@tool("get_placement_stats", "Aggregated placement statistics (KPIs, funnel, by department/company, monthly trend).", StatsArgs,
      roles=STAFF, perms=("reports.view",))
def get_placement_stats(ctx: Context, a: StatsArgs):
    r = placement_report(ctx.db, academic_year=a.graduation_year, dept=dept_id(ctx.db, a.department), company_id=a.company_id,
                         job_id=None, app_status=None, offer_status=None)
    return {"kpis": r["kpis"], "funnel": r["funnel"], "offersByDepartment": r["offersByDept"], "companyOffers": r["companyOffers"][:15],
            "monthlyTrend": r["monthly"][-12:], "applicationStatus": r["statusDist"]}


@tool("get_recruitment_activity", "Current recruitment activity: counts, upcoming drives, deadlines this week, upcoming interviews.",
      roles=STAFF, perms=("reports.view", "applications.review", "students.view"))
def get_recruitment_activity(ctx: Context, a: NoArgs):
    d = faculty_dashboard(ctx.db)
    return {"metrics": d["metrics"], "applicationsByStatus": d["statusDist"], "byDepartment": d["deptChart"],
            "upcomingDrives": [job_brief(v) for v in d["upcomingDrives"]], "deadlinesThisWeek": [job_brief(v) for v in d["nearingDeadline"]],
            "upcomingInterviews": [{k: i[k] for k in ("round", "job", "company", "at")} for i in d["upcomingInterviews"]]}


class StageArgs(Args):
    application_ids: list[int] = Field(min_length=1, max_length=20)
    status: Literal["shortlisted", "interview", "selected", "rejected"]
    note: str | None = Field(None, max_length=250)


@tool("prepare_stage_change", "Prepare moving applicants to a new stage (staff confirm it on a card).", StageArgs,
      roles=STAFF, perms=("applications.review",), prepares=True)
def prepare_stage_change(ctx: Context, a: StageArgs):
    apps = [ctx.db.get(Application, i) for i in dict.fromkeys(a.application_ids)]
    if any(x is None for x in apps):
        return cannot("Some application ids do not exist. Look them up with get_applicants first.")
    label = STATUS_LABEL[a.status]
    details = [(f"{x.student.user.name} ({x.student.student_code})", f"{x.job.company.name} — {x.job.title}: {STATUS_LABEL[x.status]} → {label}") for x in apps[:10]]
    if len(apps) > 10:
        details.append(("…", f"and {len(apps) - 10} more"))
    return propose(ctx, "update_stage", f"Move {len(apps)} applicant(s) to {label}", details,
                   {"ids": [x.id for x in apps], "status": a.status, "note": a.note},
                   description="Each student is notified. Stages only move forward; ineligible applicants need an exception on the Applications page.",
                   destructive=a.status == "rejected")


class StudentSearchArgs(Args):
    query: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=16)
    graduation_year: int | None = Field(None, ge=2000, le=2100)
    min_cgpa: float | None = Field(None, ge=0, le=10)
    skill: str | None = Field(None, max_length=60)
    placement_status: PLACEMENT | None = None
    limit: int = Field(15, ge=1, le=25)


@tool("search_students", "Search the student directory.", StudentSearchArgs, roles=STAFF, perms=("students.view",))
def search_students(ctx: Context, a: StudentSearchArgs):
    f = {"q": a.query, "dept": dept_id(ctx.db, a.department), "year": a.graduation_year, "min_cgpa": a.min_cgpa, "skill": a.skill, "placement": a.placement_status}
    rows, total = list_students(ctx.db, ctx.user, f, 1, a.limit)
    return {"total": total, "truncated": total > len(rows), "students": [{
        "studentId": r["id"], "name": r["name"], "studentCode": r["studentCode"], "department": r.get("departmentCode"), "degree": r["degree"],
        "currentYear": r["currentYear"], "graduationYear": r["graduationYear"], "cgpa": r["academic"].get("cgpa"),
        "cgpaVerified": r["academic"]["cgpaVerified"], "activeArrears": r["academic"]["activeArrears"], "skills": r["skills"],
        "placementStatus": r["placementStatus"], "applications": r["applicationCount"], "offers": r["offerCount"]} for r in rows],
        "note": "Use get_student_details for one student's full record."}


class StudentArgs(Args):
    student_id: int | None = Field(None, ge=1)
    student_code: str | None = Field(None, max_length=32)

    @model_validator(mode="after")
    def _one(self):
        if bool(self.student_id) == bool(self.student_code):
            raise ValueError("Give exactly one of student_id or student_code.")
        return self


@tool("get_student_details", "One student's full record: profile, academics, applications and offers. Viewing is audited.",
      StudentArgs, roles=STAFF, perms=("students.view",))
def get_student_details(ctx: Context, a: StudentArgs):
    sid = a.student_id or ctx.db.scalar(select(Student.id).where(func.lower(Student.student_code) == a.student_code.lower()))
    if not sid:
        raise NotFound("No student with that ID.")
    d = student_detail(ctx.db, ctx.user, sid)
    s = d["student"]
    keep = ("name", "studentCode", "departmentCode", "degree", "currentYear", "graduationYear", "academic", "skills", "placementStatus",
            "email", "phone", "interests", "preferredRoles", "profileCompletion")
    return {"student": {k: s.get(k) for k in keep},
            "applications": [{"title": v["job"]["title"], "company": v["company"]["name"], "status": v["application"]["status"],
                              "appliedAt": v["application"]["appliedAt"]} for v in d["applications"][:20]],
            "offers": [{"company": o["company"]["name"], "ctcLpa": o["offer"]["ctcLpa"], "status": o["offer"]["status"]} for o in d["offers"][:10]]}


class CompanySearchArgs(Args):
    query: str | None = Field(None, max_length=100)
    tier: Literal["regular", "dream", "super_dream"] | None = None
    limit: int = Field(15, ge=1, le=25)


COMPANY_PERMS = ("companies.manage", "jobs.create", "applications.review", "students.view")


@tool("search_companies", "Search recruiting companies.", CompanySearchArgs, roles=STAFF, perms=COMPANY_PERMS)
def search_companies(ctx: Context, a: CompanySearchArgs):
    rows, total, _ = list_companies(ctx.db, a.query, None, a.tier, "exclude", 1, a.limit)
    return {"total": total, "truncated": total > len(rows), "companies": [{
        "companyId": r["company"]["id"], "name": r["company"]["name"], "tier": r["company"]["tier"], "industry": r["company"]["industry"],
        "website": r["company"]["website"], "contactName": r["company"].get("contactName"), "contactEmail": r["company"].get("contactEmail"),
        "jobs": r["jobCount"], "activeJobs": r["activeJobs"], "offers": r["offers"]} for r in rows]}


class CompanyIdArgs(Args):
    company_id: int = Field(ge=1)


@tool("get_company_details", "One company's details and its jobs with applicant / offer counts.", CompanyIdArgs, roles=STAFF, perms=COMPANY_PERMS)
def get_company_details(ctx: Context, a: CompanyIdArgs):
    d = company_detail(ctx.db, a.company_id)
    c = d["company"]
    return {"company": {"name": c["name"], "tier": c["tier"], "industry": c["industry"], "description": c.get("description", "")[:500]},
            "interviews": d["interviews"], "jobs": [{"jobId": j["job"]["id"], "title": j["job"]["title"], "status": j["job"]["status"],
                                                      "deadline": j["job"]["deadline"], "applicants": j["applicants"], "selected": j["selected"],
                                                      "offers": j["offers"]} for j in d["jobs"]]}


class OfferSearchArgs(Args):
    query: str | None = Field(None, max_length=100)
    status: Literal["all", "pending", "received", "accepted", "declined", "withdrawn"] = "all"
    department: str | None = Field(None, max_length=16)
    limit: int = Field(15, ge=1, le=25)


@tool("search_offers", "Search offer records.", OfferSearchArgs, roles=STAFF, perms=("offers.manage",))
def search_offers(ctx: Context, a: OfferSearchArgs):
    f = {"q": a.query, "status": None if a.status == "all" else a.status, "dept": dept_id(ctx.db, a.department), "company_id": None}
    rows, total, _ = staff_offers(ctx.db, ctx.user, f, 1, a.limit)
    return {"total": total, "truncated": total > len(rows), "offers": [{
        "student": o["student"]["name"], "studentCode": o["student"]["studentCode"], "company": o["company"]["name"], "title": o["job"]["title"],
        "ctcLpa": o["offer"]["ctcLpa"], "status": o["offer"]["status"], "offeredAt": o["offer"]["offeredAt"], "acceptBy": o["offer"]["acceptBy"]} for o in rows]}


# ---------------------------------------------------------------- managing records (proposals only)
class UserChangeArgs(Args):
    operation: Literal["create", "update", "deactivate", "activate"]
    user: str | None = Field(None, max_length=190, description="E-mail or user ID of an existing account (update/deactivate/activate)")
    name: str | None = Field(None, max_length=120)
    email: str | None = Field(None, max_length=190)
    user_code: str | None = Field(None, max_length=32)
    account_type: Literal["student", "faculty"] | None = None
    department: str | None = Field(None, max_length=16)
    graduation_year: int | None = Field(None, ge=2000, le=2100)


@tool("prepare_user_change", "Prepare creating, editing, deactivating or re-activating a student or faculty account. "
      "Administrator accounts and roles cannot be managed here.", UserChangeArgs, roles=STAFF, perms=("users.manage",), prepares=True)
def prepare_user_change(ctx: Context, a: UserChangeArgs):
    from ...routers.admin import UserIn
    from pydantic import ValidationError
    did = dept_id(ctx.db, a.department)
    if a.operation == "create":
        missing = [n for n, v in (("name", a.name), ("email", a.email), ("user_code", a.user_code), ("account_type", a.account_type)) if not v]
        if a.account_type == "student" and not did:
            missing.append("department")
        if missing:
            return cannot("Ask the user for: " + ", ".join(missing), "missing_information")
        try:
            body = UserIn(name=a.name, email=a.email, user_code=a.user_code, role=a.account_type, department_id=did,
                          graduation_year=a.graduation_year if a.account_type == "student" else None)
        except ValidationError as e:
            return cannot(str(e)[:300], "invalid_arguments")
        if ctx.db.scalar(select(User.id).where(or_(func.lower(User.email) == a.email.lower(), func.lower(User.user_code) == a.user_code.lower()))):
            return cannot("An account with that e-mail or user ID already exists.", "already_exists")
        return propose(ctx, "user_create", f"Create {a.account_type} account for {a.name}",
                       [("Name", a.name), ("E-mail", a.email.lower()), ("User ID", a.user_code), ("Role", a.account_type), ("Department", a.department or "—")],
                       {"user": body.model_dump(mode="json", by_alias=True)}, description="The account is created as invited; the person sets a password from a one-time link.")
    target = ctx.db.scalar(select(User).where(or_(func.lower(User.email) == (a.user or "").lower(), func.lower(User.user_code) == (a.user or "").lower())))
    if not target:
        return cannot("No account matches that e-mail or user ID.", "not_found")
    if target.role_name == RoleName.ADMIN:
        return cannot("Administrator accounts cannot be managed through the assistant.", "not_allowed_here")
    if a.operation in ("deactivate", "activate"):
        if target.id == ctx.user.id:
            return cannot("You cannot change your own account status.", "not_allowed_here")
        status = UserStatus.INACTIVE if a.operation == "deactivate" else UserStatus.ACTIVE
        if target.status == status or (status == UserStatus.ACTIVE and target.status == UserStatus.INVITED):
            return cannot(f"The account is already {target.status}.", "nothing_to_change")
        return propose(ctx, "user_status", f"{'Deactivate' if a.operation == 'deactivate' else 'Re-activate'} {target.name}",
                       [("Account", f"{target.name} ({target.user_code})"), ("Role", target.role_name), ("New status", status.value)],
                       {"userId": target.id, "status": status.value}, destructive=status == UserStatus.INACTIVE,
                       description="Deactivated accounts are signed out everywhere; records are kept.")
    new = {"name": a.name or target.name, "email": (a.email or target.email).lower(), "user_code": a.user_code or target.user_code,
           "role": target.role_name, "department_id": did or target.department_id,
           "graduation_year": a.graduation_year if target.role_name == "student" else None}
    old = {"name": target.name, "email": target.email, "user_code": target.user_code, "department_id": target.department_id}
    changes = [(k, f"{old[k]} → {new[k]}") for k in old if old[k] != new[k]]
    if not changes and not a.graduation_year:
        return cannot("Nothing would change.", "nothing_to_change")
    body = UserIn(**new)
    return propose(ctx, "user_update", f"Update {target.name}", changes or [("Graduation year", str(a.graduation_year))],
                   {"userId": target.id, "user": body.model_dump(mode="json", by_alias=True)})


class ImportRowArgs(Args):
    student_code: str = Field(max_length=32)
    name: str = Field(max_length=120)
    email: str = Field(max_length=190)
    department_code: str = Field(max_length=16)
    graduation_year: int = Field(ge=2000, le=2100)
    cgpa: float | None = Field(None, ge=0, le=10)


class ImportArgs(Args):
    students: list[ImportRowArgs] = Field(min_length=1, max_length=25)


@tool("prepare_student_import", "Prepare creating up to 25 student accounts at once.", ImportArgs, roles=STAFF, perms=("users.manage",), prepares=True)
def prepare_student_import(ctx: Context, a: ImportArgs):
    rows = [{"studentCode": r.student_code, "name": r.name, "email": r.email, "departmentCode": r.department_code,
             "graduationYear": str(r.graduation_year), "cgpa": "" if r.cgpa is None else str(r.cgpa)} for r in a.students]
    details = [(r.student_code, f"{r.name} · {r.email} · {r.department_code} · {r.graduation_year}") for r in a.students[:10]]
    if len(rows) > 10:
        details.append(("…", f"and {len(rows) - 10} more"))
    return propose(ctx, "student_import", f"Create {len(rows)} student account(s)", details, {"rows": rows},
                   description="Rows that fail validation are skipped and reported; valid rows are invited.")


class CompanyChangeArgs(Args):
    operation: Literal["create", "update", "archive", "restore"]
    company: str | None = Field(None, max_length=160, description="Name or id of an existing company")
    name: str | None = Field(None, max_length=160)
    website: str | None = Field(None, max_length=300)
    industry: str | None = Field(None, max_length=120)
    description: str | None = Field(None, max_length=4000)
    contact_name: str | None = Field(None, max_length=120)
    contact_email: str | None = Field(None, max_length=190)
    contact_phone: str | None = Field(None, max_length=40)
    tier: Literal["regular", "dream", "super_dream"] | None = None


@tool("prepare_company_change", "Prepare adding, editing, archiving or restoring a company.", CompanyChangeArgs,
      roles=STAFF, perms=("companies.manage",), prepares=True)
def prepare_company_change(ctx: Context, a: CompanyChangeArgs):
    from ...routers.staff import CompanyIn
    from pydantic import ValidationError
    if a.operation == "create":
        try:
            body = CompanyIn(name=a.name or "", website=a.website or "", industry=a.industry or "", description=a.description or "",
                             contact_name=a.contact_name or "", contact_email=a.contact_email or "", contact_phone=a.contact_phone, tier=a.tier or "regular")
        except ValidationError as e:
            return cannot("Ask the user for the missing or invalid details: " + str(e)[:300], "missing_information")
        if ctx.db.scalar(select(Company.id).where(func.lower(Company.name) == body.name.lower())):
            return cannot("A company with this name already exists.", "already_exists")
        return propose(ctx, "company_save", f"Add company {body.name}",
                       [("Name", body.name), ("Website", body.website), ("Industry", body.industry), ("Tier", body.tier), ("Contact", body.contact_email or "—")],
                       {"company": body.model_dump(mode="json", by_alias=True)})
    q = a.company or ""
    c = ctx.db.get(Company, int(q)) if q.isdigit() else ctx.db.scalar(select(Company).where(func.lower(Company.name) == q.lower()))
    if not c:
        return cannot("No company matches that name or id.", "not_found")
    if a.operation in ("archive", "restore"):
        archived = a.operation == "archive"
        if archived and c.archived_at or (not archived and not c.archived_at):
            return cannot(f"{c.name} is already {'archived' if c.archived_at else 'active'}.", "nothing_to_change")
        if archived and ctx.db.scalar(select(func.count(Job.id)).where(Job.company_id == c.id, Job.status == "published")):
            return cannot(f"{c.name} has published jobs. Close or cancel them first.")
        return propose(ctx, "company_archive", f"{'Archive' if archived else 'Restore'} {c.name}", [("Company", c.name)],
                       {"companyId": c.id, "archived": archived}, destructive=archived,
                       description="Archived companies are hidden and read-only; their history is kept.")
    if c.archived_at:
        return cannot("Restore this company before editing it.")
    new = {"name": a.name or c.name, "website": a.website or c.website, "industry": a.industry or c.industry,
           "description": a.description if a.description is not None else c.description, "contact_name": a.contact_name or c.contact_name,
           "contact_email": a.contact_email or c.contact_email, "contact_phone": a.contact_phone or c.contact_phone, "tier": a.tier or c.tier}
    try:
        body = CompanyIn(**new)
    except ValidationError as e:
        return cannot(str(e)[:300], "invalid_arguments")
    old = {"name": c.name, "website": c.website, "industry": c.industry, "description": c.description, "contact_name": c.contact_name,
           "contact_email": c.contact_email, "contact_phone": c.contact_phone, "tier": c.tier}
    changes = [(k, f"{old[k]} → {new[k]}") for k in old if old[k] != new[k]]
    if not changes:
        return cannot("Nothing would change.", "nothing_to_change")
    return propose(ctx, "company_save", f"Update {c.name}", changes, {"companyId": c.id, "company": body.model_dump(mode="json", by_alias=True)})


class PolicyChangeArgs(Args):
    operation: Literal["create", "update", "delete"]
    policy_id: int | None = Field(None, ge=1)
    name: str | None = Field(None, max_length=160)
    description: str | None = Field(None, max_length=400)
    kind: Literal["max_offers", "tier_restriction", "application_limit", "accepted_offer", "exception_approval"] | None = None
    scope: Literal["college", "department", "academic_year"] | None = None
    scope_value: str | None = Field(None, max_length=32, description="Department code for department scope, graduation year for academic_year scope")
    params: dict | None = None
    enabled: bool | None = None
    reason: str | None = Field(None, max_length=300)


@tool("prepare_policy_change", "Prepare creating, updating, enabling/disabling or deleting a placement policy.", PolicyChangeArgs,
      roles=STAFF, perms=("policies.manage",), prepares=True)
def prepare_policy_change(ctx: Context, a: PolicyChangeArgs):
    from ...routers.admin import PolicyIn
    from pydantic import ValidationError
    p = ctx.db.get(PlacementPolicy, a.policy_id) if a.policy_id else None
    if a.operation != "create" and not p:
        return cannot("Give the policy_id of an existing policy (see get_placement_policies).", "not_found")
    if a.operation == "delete":
        if not a.reason or len(a.reason.strip()) < 3:
            return cannot("Ask the user why the policy should be deleted.", "missing_information")
        return propose(ctx, "policy_delete", f"Delete policy “{p.name}”", [("Policy", p.name), ("Kind", p.kind), ("Reason", a.reason)],
                       {"policyId": p.id, "reason": a.reason, "name": p.name}, destructive=True, description="The policy stops applying at once.")
    scope = a.scope or (p.scope if p else "college")
    scope_value = a.scope_value if a.scope_value is not None else (p.scope_value if p else None)
    if scope == "department" and scope_value and not scope_value.isdigit():
        scope_value = str(dept_id(ctx.db, scope_value))
    data = {"name": a.name or (p.name if p else None), "description": a.description if a.description is not None else (p.description if p else ""),
            "kind": a.kind or (p.kind if p else None), "scope": scope, "scope_value": scope_value if scope != "college" else None,
            "params": {**(p.params if p else {}), **(a.params or {})}, "enabled": a.enabled if a.enabled is not None else (p.enabled if p else True)}
    if not data["name"] or not data["kind"]:
        return cannot("Ask the user for the policy name and kind.", "missing_information")
    try:
        body = PolicyIn(**data)
    except ValidationError as e:
        return cannot(str(e)[:300], "invalid_arguments")
    details = [("Name", body.name), ("Kind", body.kind), ("Applies to", body.scope + (f" {body.scope_value}" if body.scope_value else "")),
               ("Parameters", ", ".join(f"{k}={v}" for k, v in body.params.items())), ("Enabled", "yes" if body.enabled else "no")]
    payload = {"policy": body.model_dump(mode="json", by_alias=True)}
    if p:
        payload["policyId"] = p.id
    return propose(ctx, "policy_save", f"{'Update' if p else 'Create'} policy “{body.name}”", details, payload,
                   description="Parameters are validated again when you confirm.")


class CgpaArgs(Args):
    student_code: str = Field(max_length=32)
    cgpa: float | None = Field(None, ge=0, le=10, description="Corrected value; omit to verify the value on file")


@tool("prepare_cgpa_verification", "Prepare verifying (and optionally correcting) a student's CGPA.", CgpaArgs,
      roles=STAFF, perms=("students.edit",), prepares=True)
def prepare_cgpa_verification(ctx: Context, a: CgpaArgs):
    s = ctx.db.scalar(select(Student).where(func.lower(Student.student_code) == a.student_code.lower()))
    if not s:
        return cannot("No student with that ID.", "not_found")
    current = float(s.academic.cgpa) if s.academic and s.academic.cgpa is not None else None
    if current is None and a.cgpa is None:
        return cannot("There is no CGPA on file. Ask the user for the correct value.")
    if s.academic and s.academic.cgpa_verified and (a.cgpa is None or a.cgpa == current):
        return cannot("This CGPA is already verified.", "nothing_to_change")
    details = [("Student", f"{s.user.name} ({s.student_code})"), ("CGPA on file", current if current is not None else "—")]
    if a.cgpa is not None and a.cgpa != current:
        details.append(("Corrected to", a.cgpa))
    return propose(ctx, "verify_cgpa", f"Verify CGPA of {s.user.name}", details, {"studentId": s.id, "cgpa": a.cgpa},
                   description="The student is notified.")


# ---------------------------------------------------------------- administrator
class UserSearchArgs(Args):
    query: str | None = Field(None, max_length=100)
    account_type: Literal["all", "admin", "faculty", "student"] = "all"
    status: Literal["all", "active", "inactive", "invited"] = "all"
    department: str | None = Field(None, max_length=16)
    limit: int = Field(15, ge=1, le=25)


@tool("search_users", "Search user accounts.", UserSearchArgs, roles=ADMIN, perms=("users.manage",))
def search_users(ctx: Context, a: UserSearchArgs):
    rows, total = list_users(ctx.db, a.query, None if a.account_type == "all" else a.account_type, None if a.status == "all" else a.status,
                             dept_id(ctx.db, a.department), 1, a.limit)
    return {"total": total, "truncated": total > len(rows), "users": [{
        "name": u["name"], "userCode": u["userCode"], "email": u["email"], "role": u["role"], "status": u["status"],
        "department": u.get("departmentCode"), "lastLoginAt": u.get("lastLoginAt")} for u in rows]}


@tool("get_academic_overview", "Departments, programmes and academic years.", roles=ADMIN)
def get_academic_overview(ctx: Context, a: NoArgs):
    db = ctx.db
    return {"departments": [{"code": d.code, "name": d.name, "headName": d.head_name,
                             "students": db.scalar(select(func.count(Student.id)).where(Student.department_id == d.id)) or 0,
                             "courses": db.scalar(select(func.count(Course.id)).where(Course.department_id == d.id)) or 0}
                            for d in db.scalars(select(Department).order_by(Department.code))],
            "courses": [{"code": c.code, "name": c.name, "degree": c.degree, "durationYears": c.duration_years} for c in db.scalars(select(Course))],
            "academicYears": [{"label": y.label, "graduationYear": y.graduation_year, "active": y.active}
                              for y in db.scalars(select(AcademicYear).order_by(AcademicYear.graduation_year))]}


@tool("get_roles_overview", "Which permissions each role has, and how many users hold each role.", roles=ADMIN, perms=("roles.manage",))
def get_roles_overview(ctx: Context, a: NoArgs):
    r = roles_overview(ctx.db)
    return {"permissions": [{k: p[k] for k in ("key", "label", "module")} for p in r["permissions"]], "grantsByRole": r["matrix"], "userCounts": r["userCounts"]}


@tool("get_admin_overview", "System overview: account and placement counts, and administrative alerts.", roles=ADMIN)
def get_admin_overview(ctx: Context, a: NoArgs):
    d = admin_dashboard(ctx.db, ctx.user)
    out = {"metrics": d["metrics"], "placement": d["placement"], "alerts": [{"level": x["level"], "text": x["text"]} for x in d["alerts"]]}
    if "activity" in d:
        out["recentActivity"] = [{k: e.get(k) for k in ("actor", "action", "resource", "result", "at")} for e in d["activity"]]
    return out


class AuditArgs(Args):
    action: str | None = Field(None, max_length=64, description="Action prefix, e.g. auth or user.create")
    result: Literal["all", "success", "denied", "failed"] = "all"
    limit: int = Field(10, ge=1, le=20)


@tool("get_audit_activity", "Recent entries from the audit log.", AuditArgs, roles=ADMIN, perms=("audit.view",))
def get_audit_activity(ctx: Context, a: AuditArgs):
    q = select(AuditLog)
    if a.action:
        q = q.where(or_(AuditLog.action == a.action, AuditLog.action.like(a.action.replace("%", "") + ".%")))
    if a.result != "all":
        q = q.where(AuditLog.result == a.result)
    total = ctx.db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = ctx.db.scalars(q.order_by(AuditLog.id.desc()).limit(a.limit)).all()
    return {"total": total, "entries": [{"actor": e.actor_name, "role": e.actor_role, "action": e.action, "resource": e.resource,
                                         "result": e.result, "reason": e.reason, "at": iso(e.created_at)} for e in rows]}


