"""Reports the assistant can generate. The server builds every number; the model only writes the summary.

Report: {title, subtitle?, generatedAt, kpis:[{label, value}], sections:[{heading, note?, table?{columns, rows}, chart?}], truncated?}
"""
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...database import utcnow
from ...enums import EligibilityState, OfferStatus
from ...errors import Forbidden, NotFound, ValidationFailed
from ...models import Application, AuditLog, Job, Student, User
from ...serializers import iso
from ..applications_service import STATUS_LABEL
from ..common import student_of
from ..companies_service import list_companies
from ..eligibility import evaluate
from ..interviews_service import list_interviews
from ..offers_service import list_mine as my_offers
from ..offers_service import list_staff as staff_offers
from ..reports_service import placement_report
from ..review_service import list_applications
from ..students_service import list_students
from ..users_service import list_users
from .charts import PLACEMENT_LABEL, _finish

ROW_CAP = 100
REPORT_PERMS = {
    "placement_summary": ("reports.view",),
    "student_directory": ("students.view",),
    "applicants": ("applications.review",),
    "offers": ("offers.manage",),
    "interviews": ("applications.review",),
    "eligible_students": ("students.view",),
    "user_accounts": ("users.manage",),
    "companies": ("companies.manage", "jobs.create", "applications.review", "students.view"),
    "audit_summary": ("audit.view",),
}


def _chart(title, type_, labels, series, unit=None):
    try:
        return _finish(title, type_, [type_, "bar", "hbar", "pie", "donut", "stacked", "line"], None, labels, series, unit)[0]
    except ValidationFailed:
        return None


def _table(heading, columns, rows, total=None, note=None, chart=None):
    total = len(rows) if total is None else total
    section = {"heading": heading, "table": {"columns": columns, "rows": [[("" if c is None else c) for c in r] for r in rows[:ROW_CAP]]}}
    notes = [n for n in [note, f"Showing the first {ROW_CAP} of {total}." if total > ROW_CAP or len(rows) > ROW_CAP else None] if n]
    if notes:
        section["note"] = " ".join(notes)
    if chart:
        section["chart"] = chart
    return section


def _report(title, kpis, sections, subtitle=None):
    out = {"title": title, "generatedAt": iso(utcnow()), "kpis": [{"label": k, "value": str(v)} for k, v in kpis], "sections": sections}
    if subtitle:
        out["subtitle"] = subtitle
    if any("Showing the first" in (s.get("note") or "") for s in sections):
        out["truncated"] = True
    return out


def counter_chart(title, counter, type_="pie", labels_map=None):
    keys = [k for k in (labels_map or counter) if counter.get(k)]
    return _chart(title, type_, [labels_map[k] if labels_map else k for k in keys], [{"name": "Count", "values": [counter[k] for k in keys]}])


def build(db: Session, user: User, kind: str, a, dept_id: int | None = None) -> dict:
    if not any(user.can(p) for p in REPORT_PERMS[kind]):
        raise Forbidden("This report needs a permission you do not have.")
    year = a.graduation_year

    if kind == "placement_summary":
        r = placement_report(db, academic_year=year, dept=dept_id, company_id=None, job_id=None, app_status=None, offer_status=None)
        k = r["kpis"]
        dept_rows = [[d["dept"], d["students"], d["placedStudents"], d["offers"], d["accepted"],
                      f"{(100 * d['placedStudents'] / d['students']):.1f}%" if d["students"] else "0%"] for d in r["offersByDept"]]
        return _report("Placement summary", [
            ("Students", k["totalStudents"]), ("Eligible now", k["eligibleStudents"]), ("Applied", k["appliedStudents"]),
            ("Placed", k["uniqueStudentsPlaced"]), ("Placement %", f"{k['placementPct']}%"), ("Offers", k["totalOffers"]),
            ("Accepted offers", k["acceptedOffers"])], [
            _table("Placement by department", ["Department", "Students", "Placed", "Offers", "Accepted", "Placement %"], dept_rows,
                   chart=_chart("Placed vs not placed", "stacked", [d["dept"] for d in r["offersByDept"]],
                                [{"name": "Placed", "values": [d["placedStudents"] for d in r["offersByDept"]]},
                                 {"name": "Not placed", "values": [d["students"] - d["placedStudents"] for d in r["offersByDept"]]}])),
            {"heading": "Placement funnel", "chart": _chart("Funnel", "hbar", [f["stage"] for f in r["funnel"]], [{"name": "Count", "values": [f["value"] for f in r["funnel"]]}])},
            _table("Companies", ["Company", "Offers", "Accepted"], [[c["company"], c["offers"], c["accepted"]] for c in r["companyOffers"]]),
            {"heading": "Monthly trend", "chart": _chart("Applications and offers", "line", [m["month"] for m in r["monthly"]],
                                                         [{"name": "Applications", "values": [m["applications"] for m in r["monthly"]]},
                                                          {"name": "Offers", "values": [m["offers"] for m in r["monthly"]]}])},
            _table("Applications by stage", ["Stage", "Applications"], [[s["label"], s["count"]] for s in r["statusDist"]]),
        ], subtitle=" · ".join(x for x in [f"Department {a.department}" if a.department else "", f"Batch {year}" if year else ""] if x) or None)

    if kind == "student_directory":
        f = {"dept": dept_id, "year": year, "min_cgpa": a.min_cgpa, "placement": a.placement_status, "q": None, "skill": None}
        rows, total = list_students(db, user, f, 1, ROW_CAP)
        cg = [r["academic"].get("cgpa") for r in rows if r["academic"].get("cgpa") is not None]
        table = [[r["studentCode"], r["name"], r.get("departmentCode"), r["graduationYear"], r["academic"].get("cgpa", ""),
                  "Yes" if r["academic"]["cgpaVerified"] else "No", PLACEMENT_LABEL.get(r["placementStatus"]), r["applicationCount"], r["offerCount"]] for r in rows]
        return _report("Student directory", [("Students matching", total), ("Shown", len(rows)),
                                             ("Average CGPA", f"{sum(cg) / len(cg):.2f}" if cg else "—"),
                                             ("Placed (shown)", sum(1 for r in rows if r["placementStatus"] == "placed"))], [
            _table("Students", ["Student ID", "Name", "Department", "Batch", "CGPA", "CGPA verified", "Placement", "Applications", "Offers"], table, total),
            {"heading": "By placement status", "chart": counter_chart("Placement status", Counter(r["placementStatus"] for r in rows), "pie", PLACEMENT_LABEL)},
        ])

    if kind == "applicants":
        f = {"q": None, "status": a.status, "company_id": None, "job_id": a.job_id, "dept": dept_id, "eligibility": None, "sort": None}
        rows, total = list_applications(db, user, f, 1, ROW_CAP)
        table = [[r["student"]["studentCode"], r["student"]["name"], r["student"].get("departmentCode"), r["student"]["academic"].get("cgpa", ""),
                  r["company"]["name"], r["job"]["title"], (r["application"].get("eligibilitySnapshot") or {}).get("state", ""),
                  STATUS_LABEL[r["application"]["status"]], r["application"]["appliedAt"][:10]] for r in rows]
        sub = f"{rows[0]['company']['name']} — {rows[0]['job']['title']}" if a.job_id and rows else "All jobs"
        return _report("Applicants", [("Applications matching", total), ("Shown", len(rows))], [
            _table("Applicants", ["Student ID", "Name", "Dept", "CGPA", "Company", "Job", "Eligibility", "Stage", "Applied"], table, total),
            {"heading": "By stage", "chart": counter_chart("Applicants by stage", Counter(r["application"]["status"] for r in rows), "donut", STATUS_LABEL)},
        ], subtitle=sub)

    if kind == "offers":
        f = {"q": None, "status": a.status if a.status in [s.value for s in OfferStatus] else None, "dept": dept_id, "company_id": None}
        rows, total, meta = staff_offers(db, user, f, 1, ROW_CAP)
        t = meta["totals"]
        table = [[r["student"]["studentCode"], r["student"]["name"], r["company"]["name"], r["job"]["title"], r["offer"]["ctcLpa"],
                  r["offer"]["status"], r["offer"]["offeredAt"][:10]] for r in rows]
        by_co = meta["byCompany"][:12]
        return _report("Offers", [("Offers", t["offers"]), ("Accepted", t["accepted"]), ("Students placed", t["placed"]),
                                  ("Selected, no offer yet", len(meta["selectedWithoutOffer"]))], [
            _table("Offers", ["Student ID", "Name", "Company", "Job", "LPA", "Status", "Offered"], table, total),
            {"heading": "Offers by company", "chart": _chart("Offers by company", "bar", [c["company"] for c in by_co],
                                                             [{"name": "Offers", "values": [c["offers"] for c in by_co]}, {"name": "Accepted", "values": [c["accepted"] for c in by_co]}])},
            _table("By department", ["Department", "Students", "Offers", "Placed"], [[d["dept"], d["students"], d["offers"], d["placed"]] for d in meta["byDept"]]),
        ])

    if kind == "interviews":
        status = a.status if a.status in ("scheduled", "completed", "cancelled", "no_show") else None
        rows, total = list_interviews(db, user, a.job_id, status, 1, ROW_CAP)
        table = [[r["interview"]["at"][:16].replace("T", " ") + " UTC", r["company"]["name"], r["job"]["title"], r["interview"]["round"],
                  r["interview"]["location"], len(r["candidates"]), r["interview"]["status"]] for r in rows]
        return _report("Interviews", [("Interviews", total), ("Candidates scheduled", sum(len(r["candidates"]) for r in rows))], [
            _table("Interviews", ["When", "Company", "Job", "Round", "Location", "Candidates", "Status"], table, total),
        ], subtitle=f"Status: {status}" if status else None)

    if kind == "eligible_students":
        if not a.job_id:
            raise ValidationFailed("Which job? Give its jobId.")
        job = db.get(Job, a.job_id)
        if not job:
            raise NotFound("Job not found.")
        students = db.scalars(select(Student)).unique().all()
        eligible = [s for s in students if evaluate(db, s, job, ignore_open=True)["state"] == EligibilityState.ELIGIBLE]
        table = [[s.student_code, s.user.name, s.department.code, f"{s.academic.cgpa}" if s.academic and s.academic.cgpa is not None else ""] for s in eligible]
        return _report("Eligible students", [("Students evaluated", len(students)), ("Eligible", len(eligible)),
                                             ("Job accepting applications", "Yes" if job.status == "published" and job.deadline > utcnow() else "No")], [
            _table("Eligible students", ["Student ID", "Name", "Department", "CGPA"], table),
            {"heading": "By department", "chart": counter_chart("Eligible students by department", Counter(s.department.code for s in eligible), "bar")},
        ], subtitle=f"{job.company.name} — {job.title}")

    if kind == "user_accounts":
        role = None if a.account_type in (None, "all") else a.account_type
        rows, total = list_users(db, None, role, None, dept_id, 1, ROW_CAP)
        table = [[r["userCode"], r["name"], r["email"], r["role"], r.get("departmentCode") or "", r["status"], (r.get("lastLoginAt") or "")[:10]] for r in rows]
        st = Counter(r["status"] for r in rows)
        return _report("User accounts", [("Accounts matching", total), ("Shown", len(rows)), ("Active", st["active"]), ("Invited", st["invited"]), ("Inactive", st["inactive"])], [
            _table("Accounts", ["User ID", "Name", "E-mail", "Role", "Department", "Status", "Last sign-in"], table, total),
            {"heading": "By role", "chart": counter_chart("Accounts by role", Counter(r["role"] for r in rows), "pie")},
            {"heading": "By status", "chart": counter_chart("Accounts by status", st, "donut")},
        ])

    if kind == "companies":
        rows, total, _ = list_companies(db, None, None, None, "exclude", 1, ROW_CAP)
        table = [[r["company"]["name"], r["company"]["tier"], r["company"]["industry"], r["jobCount"], r["activeJobs"], r["offers"]] for r in rows]
        return _report("Companies", [("Companies", total), ("With active jobs", sum(1 for r in rows if r["activeJobs"])), ("Total offers", sum(r["offers"] for r in rows))], [
            _table("Companies", ["Company", "Tier", "Industry", "Jobs", "Active jobs", "Offers"], table, total),
            {"heading": "By tier", "chart": counter_chart("Companies by tier", Counter(r["company"]["tier"] for r in rows), "pie")},
        ])

    # audit_summary
    q = select(AuditLog).order_by(AuditLog.id.desc())
    if a.result in ("success", "denied", "failed"):
        q = q.where(AuditLog.result == a.result)
    entries = db.scalars(q.limit(50)).all()
    total = len(db.scalars(select(AuditLog.id)).all())
    table = [[iso(e.created_at)[:16].replace("T", " "), e.actor_name, e.action, e.resource, e.result, e.reason or ""] for e in entries]
    return _report("Audit summary", [("Entries in the log", total), ("Shown (latest)", len(entries)), ("Denied (shown)", sum(1 for e in entries if e.result == "denied"))], [
        _table("Latest entries", ["When (UTC)", "Actor", "Action", "Record", "Result", "Details"], table),
        {"heading": "By area", "chart": counter_chart("Entries by area", Counter(e.action.split(".")[0] for e in entries), "bar")},
        {"heading": "By result", "chart": counter_chart("Entries by result", Counter(e.result for e in entries), "donut")},
    ])


def build_mine(db: Session, user: User) -> dict:
    s = student_of(db, user)
    apps = db.scalars(select(Application).where(Application.student_id == s.id).order_by(Application.applied_at.desc())).unique().all()
    offers = my_offers(db, user)
    interviews, _ = list_interviews(db, user, None, None, 1, 50)
    cg = s.academic.cgpa if s.academic else None
    cgpa = "not entered" if cg is None else f"{cg:.2f}" + ("" if s.academic.cgpa_verified else " (unverified)")
    sections = [_table("My applications", ["Company", "Job", "Stage", "Applied"],
                       [[a.job.company.name, a.job.title, STATUS_LABEL[a.status], f"{a.applied_at:%Y-%m-%d}"] for a in apps],
                       chart=counter_chart("Applications by stage", Counter(a.status for a in apps), "donut", STATUS_LABEL))]
    if offers:
        sections.append(_table("My offers", ["Company", "Job", "LPA", "Status", "Respond by"],
                               [[o["company"]["name"], o["job"]["title"], o["offer"]["ctcLpa"], o["offer"]["status"], o["offer"]["acceptBy"][:10]] for o in offers]))
    if interviews:
        sections.append(_table("My interviews", ["When (UTC)", "Company", "Round", "Location", "Status"],
                               [[i["interview"]["at"][:16].replace("T", " "), i["company"]["name"], i["interview"]["round"], i["interview"]["location"], i["interview"]["status"]] for i in interviews]))
    active = sum(1 for a in apps if a.status in ("applied", "shortlisted", "interview", "selected"))
    return _report("My placement report", [("Applications", len(apps)), ("Active", active), ("Offers", len(offers)),
                                           ("Placement status", PLACEMENT_LABEL[s.placement_status]), ("CGPA", cgpa)],
                   sections, subtitle=f"{user.name} · {s.student_code}")


def preview(report: dict) -> dict:
    """The compact version the model sees (it writes the summary; the user sees the full report)."""
    return {
        "status": "report_shown_to_user", "title": report["title"], "subtitle": report.get("subtitle"),
        "kpis": {k["label"]: k["value"] for k in report["kpis"]},
        "sections": [{"heading": s["heading"], "rows": len(s["table"]["rows"]) if s.get("table") else 0,
                      "columns": s["table"]["columns"] if s.get("table") else None,
                      "firstRows": s["table"]["rows"][:5] if s.get("table") else None,
                      "chart": s["chart"]["title"] if s.get("chart") else None} for s in report["sections"]],
        "truncated": report.get("truncated", False),
        "note": "The full report is displayed to the user. Write a short executive summary; do not repeat the tables.",
    }


