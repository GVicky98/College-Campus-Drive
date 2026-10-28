"""Faculty / placement-officer endpoints: companies, jobs (write), students, applicant review, interviews,
offers, dashboard and reports. Every route checks its permission against the database."""
from typing import Annotated, Literal

from fastapi import APIRouter, Request
from pydantic import AfterValidator, Field, StrictBool, model_validator

from ..deps import Db, require_perm
from ..enums import ApplicationStatus, CompanyTier, EligibilityState, InterviewStatus, JobStatus, JobType, OfferStatus, PlacementStatus, RoundMode
from ..models import User
from ..schemas.common import CamelModel, PageParams, QueryModel, UtcDatetime, ok, paged
from ..serializers import company_dict, interview_dict, job_dict, offer_view
from ..services import (
    companies_service, interviews_admin, jobs_admin_service, offers_service, reports_service, review_service, students_service,
)
from ..services.interviews_service import interview_view

router = APIRouter(tags=["staff"])

Perm = lambda *p, mode="any": Annotated[User, require_perm(*p, mode=mode)]  # noqa: E731


def _clean_list(max_items: int, max_len: int):
    def check(v: list[str]) -> list[str]:
        v = [x.strip() for x in v if x and x.strip()]
        if len(v) > max_items:
            raise ValueError(f"At most {max_items} entries.")
        if any(len(x) > max_len for x in v):
            raise ValueError(f"Each entry can be at most {max_len} characters.")
        return list(dict.fromkeys(v))
    return AfterValidator(check)


# ---------------------------------------------------------------- schemas
class CompanyIn(CamelModel):
    name: str = Field(min_length=1, max_length=160)
    website: str = Field(max_length=300, pattern=r"^https?://\S+\.\S+")
    industry: str = Field(min_length=1, max_length=120)
    description: str = Field("", max_length=4000)
    contact_name: str = Field("", max_length=120)
    contact_email: str = Field("", max_length=190, pattern=r"^$|^\S+@\S+\.\S+$")
    contact_phone: str | None = Field(None, max_length=40)
    tier: CompanyTier = CompanyTier.REGULAR
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")


class CompanyQuery(PageParams):
    q: str | None = Field(None, max_length=100)
    industry: str | None = Field(None, max_length=120)
    tier: CompanyTier | None = None
    archived: Literal["exclude", "include", "only"] | None = None


class ArchiveIn(CamelModel):
    archived: StrictBool


class EligibilityIn(CamelModel):
    min_cgpa: float = Field(ge=0, le=10)
    max_active_arrears: int = Field(0, ge=0, le=30)
    max_arrear_history: int | None = Field(None, ge=0, le=30)
    department_ids: list[int] = Field([], max_length=50)
    graduation_years: list[Annotated[int, Field(ge=2000, le=2100)]] = Field([], max_length=10)
    required_skills: Annotated[list[str], _clean_list(30, 40)] = []


class RoundIn(CamelModel):
    name: str = Field(min_length=1, max_length=120)
    mode: RoundMode = RoundMode.ONLINE
    date: UtcDatetime | None = None
    location: str | None = Field(None, max_length=200)


class JobIn(CamelModel):
    company_id: int
    title: str = Field(min_length=1, max_length=160)
    domain: str = Field("General", min_length=1, max_length=80)
    location: str = Field("", max_length=160)
    type: JobType = JobType.FULL_TIME
    description: str = Field("", max_length=8000)
    responsibilities: Annotated[list[str], _clean_list(20, 300)] = []
    skills: Annotated[list[str], _clean_list(30, 40)] = []
    eligibility: EligibilityIn
    rounds: list[RoundIn] = Field([], max_length=12)
    ctc_lpa: float | None = Field(None, ge=0, le=1000)
    stipend_per_month: int | None = Field(None, ge=0, le=10_000_000)
    open_date: UtcDatetime
    deadline: UtcDatetime
    drive_date: UtcDatetime | None = None
    status: Literal["draft", "published"] = "draft"

    @model_validator(mode="after")
    def _dates(self):
        if self.deadline <= self.open_date:
            raise ValueError("The deadline must be after the opening date.")
        return self


class JobStatusIn(CamelModel):
    status: JobStatus
    reason: str | None = Field(None, max_length=400)


class StudentQuery(PageParams):
    q: str | None = Field(None, max_length=100)
    dept: int | None = None
    year: int | None = Field(None, ge=2000, le=2100)
    min_cgpa: float | None = Field(None, ge=0, le=10)
    skill: str | None = Field(None, max_length=60)
    placement: PlacementStatus | None = None


class VerifyIn(CamelModel):
    cgpa: float | None = Field(None, ge=0, le=10)


class ReviewQuery(PageParams):
    q: str | None = Field(None, max_length=100)
    status: ApplicationStatus | None = None
    company_id: int | None = None
    job_id: int | None = None
    dept: int | None = None
    eligibility: EligibilityState | None = None
    sort: Literal["recent", "cgpa", "name"] | None = None

    def filters(self) -> dict:
        return self.model_dump(exclude={"page", "page_size"})


class ExceptionIn(CamelModel):
    reason: str = Field(min_length=3, max_length=300)
    approved_by: str = Field(min_length=2, max_length=120)


class StageIn(CamelModel):
    ids: list[int] = Field(min_length=1, max_length=100)
    status: Literal["shortlisted", "interview", "selected", "rejected"]
    note: str | None = Field(None, max_length=250)
    exception: ExceptionIn | None = None


class InterviewIn(CamelModel):
    job_id: int
    application_ids: list[int] = Field(min_length=1, max_length=200)
    round: str = Field(min_length=1, max_length=120)
    at: UtcDatetime
    duration_mins: int = Field(45, ge=5, le=600)
    location: str = Field(min_length=1, max_length=300)


class InterviewStatusIn(CamelModel):
    status: InterviewStatus


class OfferQuery(PageParams):
    q: str | None = Field(None, max_length=100)
    status: OfferStatus | None = None
    dept: int | None = None
    company_id: int | None = None


class OfferIn(CamelModel):
    application_id: int
    ctc_lpa: float = Field(gt=0, le=1000)
    accept_by: UtcDatetime


class OfferStatusIn(CamelModel):
    status: Literal["received", "accepted", "declined", "withdrawn"]
    reason: str | None = Field(None, max_length=300)


class DashboardQuery(QueryModel):
    dept: int | None = None
    graduation_year: int | None = Field(None, ge=2000, le=2100)
    company_id: int | None = None
    days: int | None = Field(None, ge=1, le=3650)


class ReportQuery(QueryModel):
    academic_year: int | None = Field(None, ge=2000, le=2100)
    dept: int | None = None
    company_id: int | None = None
    job_id: int | None = None
    app_status: ApplicationStatus | None = None
    offer_status: OfferStatus | None = None


# ---------------------------------------------------------------- companies
@router.get("/companies")
def list_companies(request: Request, user: Perm(*companies_service.COMPANY_VIEW_PERMS), db: Db):
    q = CompanyQuery.from_query(request.query_params)
    items, total, industries = companies_service.list_companies(db, q.q, q.industry, q.tier, q.archived, q.page, q.page_size)
    return paged(items, total, q.page, q.page_size, industries=industries)


@router.get("/companies/{company_id}")
def get_company(company_id: int, user: Perm(*companies_service.COMPANY_VIEW_PERMS), db: Db):
    return ok(companies_service.detail(db, company_id))


@router.post("/companies", status_code=201)
def create_company(body: CompanyIn, user: Perm("companies.manage"), db: Db):
    return ok(company_dict(companies_service.save(db, user, body)))


@router.put("/companies/{company_id}")
def update_company(company_id: int, body: CompanyIn, user: Perm("companies.manage"), db: Db):
    return ok(company_dict(companies_service.save(db, user, body, company_id)))


@router.post("/companies/{company_id}/archive")
def archive_company(company_id: int, body: ArchiveIn, user: Perm("companies.manage"), db: Db):
    return ok(company_dict(companies_service.archive(db, user, company_id, body.archived)))


# ---------------------------------------------------------------- jobs (write)
@router.post("/jobs", status_code=201)
def create_job(body: JobIn, user: Perm("jobs.create"), db: Db):
    return ok(job_dict(jobs_admin_service.save(db, user, body)))


@router.put("/jobs/{job_id}")
def update_job(job_id: int, body: JobIn, user: Perm("jobs.create"), db: Db):
    return ok(job_dict(jobs_admin_service.save(db, user, body, job_id)))


@router.post("/jobs/{job_id}/status")
def job_status(job_id: int, body: JobStatusIn, user: Perm("drives.publish"), db: Db):
    return ok(job_dict(jobs_admin_service.set_status(db, user, job_id, body.status, body.reason)))


@router.post("/jobs/{job_id}/archive")
def archive_job(job_id: int, body: ArchiveIn, user: Perm("drives.publish"), db: Db):
    return ok(job_dict(jobs_admin_service.archive(db, user, job_id, body.archived)))


@router.get("/jobs/{job_id}/drive")
def job_drive(job_id: int, user: Perm("jobs.create", "drives.publish", "applications.review"), db: Db):
    return ok(jobs_admin_service.drive_detail(db, job_id))


# ---------------------------------------------------------------- students
@router.get("/students")
def list_students(request: Request, user: Perm("students.view"), db: Db):
    q = StudentQuery.from_query(request.query_params)
    items, total = students_service.list_students(db, user, q.model_dump(exclude={"page", "page_size"}), q.page, q.page_size)
    return paged(items, total, q.page, q.page_size)


@router.get("/students/{student_id}")
def get_student(student_id: int, user: Perm("students.view"), db: Db):
    return ok(students_service.detail(db, user, student_id))


@router.post("/students/{student_id}/verify-cgpa")
def verify_cgpa(student_id: int, body: VerifyIn, user: Perm("students.edit"), db: Db):
    return ok(students_service.verify_cgpa(db, user, student_id, body.cgpa))


# ---------------------------------------------------------------- applicant review
@router.get("/applications")
def list_applications(request: Request, user: Perm("applications.review"), db: Db):
    q = ReviewQuery.from_query(request.query_params)
    items, total = review_service.list_applications(db, user, q.filters(), q.page, q.page_size)
    return paged(items, total, q.page, q.page_size)


@router.post("/applications/stage")
def update_stage(body: StageIn, user: Perm("applications.review"), db: Db):
    return ok(review_service.update_stage(db, user, body.ids, body.status, body.note, body.exception))


@router.get("/applications/export")
def export_applications(request: Request, user: Perm("reports.view", "applications.review", mode="all"), db: Db):
    q = ReviewQuery.from_query(request.query_params)
    return ok(review_service.export_csv(db, user, q.filters()))


# ---------------------------------------------------------------- interviews (write)
@router.post("/interviews", status_code=201)
def create_interview(body: InterviewIn, user: Perm("applications.review"), db: Db):
    return ok(interview_view(interviews_admin.save(db, user, body), staff=True))


@router.put("/interviews/{interview_id}")
def update_interview(interview_id: int, body: InterviewIn, user: Perm("applications.review"), db: Db):
    return ok(interview_view(interviews_admin.save(db, user, body, interview_id), staff=True))


@router.post("/interviews/{interview_id}/status")
def interview_status(interview_id: int, body: InterviewStatusIn, user: Perm("applications.review"), db: Db):
    return ok(interview_dict(interviews_admin.set_status(db, user, interview_id, body.status)))


@router.post("/interviews/{interview_id}/notify")
def notify_interview(interview_id: int, user: Perm("applications.review"), db: Db):
    return ok({"notified": interviews_admin.notify_candidates(db, user, interview_id)})


# ---------------------------------------------------------------- offers (staff)
@router.get("/offers")
def list_offers(request: Request, user: Perm("offers.manage"), db: Db):
    q = OfferQuery.from_query(request.query_params)
    items, total, meta = offers_service.list_staff(db, user, q.model_dump(exclude={"page", "page_size"}), q.page, q.page_size)
    return paged(items, total, q.page, q.page_size, **meta)


@router.post("/offers", status_code=201)
def create_offer(body: OfferIn, user: Perm("offers.manage"), db: Db):
    o = offers_service.create(db, user, body.application_id, body.ctc_lpa, body.accept_by)
    return ok(offer_view(o, with_student=True))


@router.post("/offers/{offer_id}/status")
def offer_status(offer_id: int, body: OfferStatusIn, user: Perm("offers.manage"), db: Db):
    return ok(offer_view(offers_service.set_status_staff(db, user, offer_id, body.status, body.reason), with_student=True))


# ---------------------------------------------------------------- dashboard & reports
@router.get("/faculty/dashboard")
def faculty_dashboard(request: Request, user: Perm("reports.view", "applications.review", "students.view"), db: Db):
    q = DashboardQuery.from_query(request.query_params)
    return ok(reports_service.faculty_dashboard(db, q.dept, q.graduation_year, q.company_id, q.days))


@router.get("/reports/placement")
def placement_report(request: Request, user: Perm("reports.view"), db: Db):
    q = ReportQuery.from_query(request.query_params)
    return ok(reports_service.placement_report(db, **q.model_dump()))


@router.get("/reports/placement/export.csv")
def placement_csv(request: Request, user: Perm("reports.view"), db: Db):
    q = ReportQuery.from_query(request.query_params)
    return ok(reports_service.export_placement_csv(db, user, **q.model_dump()))


