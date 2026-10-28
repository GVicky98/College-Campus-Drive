"""Student self-service: /student/*, /jobs (read), /applications (student side), /offers (student side),
/interviews (list), /reminders."""
from typing import Literal

from typing import Annotated

from fastapi import APIRouter, Request
from pydantic import AfterValidator, Field

from ..deps import CurrentUser, Db, StudentUser, is_staff
from ..errors import ValidationFailed
from ..enums import ApplicationStatus, Degree, InterviewStatus, JobType, ReminderKind
from ..schemas.common import CamelModel, PageParams, QueryModel, UtcDatetime, ok, paged
from ..services import applications_service as apps
from ..services import content_service, interviews_service, jobs_service, offers_service, student_service

router = APIRouter(tags=["student"])

def _tags(v: list[str]) -> list[str]:
    v = [t.strip() for t in v if t and t.strip()]
    if len(v) > 30:
        raise ValueError("At most 30 entries.")
    if any(len(t) > 40 for t in v):
        raise ValueError("Each entry can be at most 40 characters.")
    return v


TagList = Annotated[list[str], AfterValidator(_tags)]


class ProfilePatch(CamelModel):
    phone: str | None = Field(None, pattern=r"^(\+?[0-9 ()-]{7,20})?$")
    portfolio_url: str | None = Field(None, max_length=300, pattern=r"^(https?://\S+\.\S+)?$")
    resume_file: str | None = Field(None, max_length=255)
    degree: Degree | None = None
    current_year: int | None = Field(None, ge=1, le=6)
    skills: TagList | None = None
    interests: TagList | None = None
    preferred_roles: TagList | None = None
    cgpa: float | None = Field(None, ge=0, le=10)
    active_arrears: int | None = Field(None, ge=0, le=30)
    arrear_history: int | None = Field(None, ge=0, le=30)



class OnboardingIn(CamelModel):
    student_code: str = Field(pattern=r"^[A-Za-z0-9-]{5,16}$")
    department_id: int
    degree: Degree
    current_year: int = Field(ge=1, le=6)
    graduation_year: int = Field(ge=2000, le=2100)
    cgpa: float = Field(ge=0, le=10)
    active_arrears: int = Field(0, ge=0, le=30)
    arrear_history: int = Field(0, ge=0, le=30)
    skills: TagList = []
    interests: TagList = []
    preferred_roles: TagList = []
    phone: str | None = Field(None, pattern=r"^(\+?[0-9 ()-]{7,20})?$")
    resume_file: str | None = Field(None, max_length=255)
    portfolio_url: str | None = Field(None, max_length=300, pattern=r"^(https?://\S+\.\S+)?$")



class JobQuery(PageParams):
    page_size: int = Field(9, ge=1, le=100)
    q: str | None = Field(None, max_length=100)
    dept: int | None = None
    min_cgpa: float | None = Field(None, ge=0, le=10)
    location: str | None = Field(None, max_length=100)
    type: JobType | None = None
    deadline_days: int | None = Field(None, ge=1, le=365)
    tab: Literal["all", "eligible", "not_eligible", "saved", "applied"] | None = None
    sort: Literal["deadline", "relevance", "recent"] | None = None
    status: Literal["all", "draft", "published", "closed", "cancelled"] | None = None
    company_id: int | None = None
    archived: Literal["exclude", "include", "only"] | None = None


class ApplyIn(CamelModel):
    job_id: int


class MyAppsQuery(PageParams):
    status: ApplicationStatus | None = None
    q: str | None = Field(None, max_length=100)


class RespondIn(CamelModel):
    decision: Literal["accepted", "declined"]


class InterviewQuery(PageParams):
    page_size: int = Field(50, ge=1, le=100)
    job_id: int | None = None
    status: InterviewStatus | None = None


class ReminderIn(CamelModel):
    title: str = Field(min_length=1, max_length=200)
    at: UtcDatetime
    job_id: int | None = None
    kind: ReminderKind | None = None


# ---------------------------------------------------------------- /student
@router.get("/student/profile")
def get_profile(user: StudentUser, db: Db):
    return ok(student_service.profile(db, user))


@router.patch("/student/profile")
async def patch_profile(request: Request, user: StudentUser, db: Db):
    raw = await request.json() if await request.body() else {}
    if not isinstance(raw, dict):
        raise ValidationFailed("The body must be a JSON object.")
    # Controlled fields are refused (and audited) before validation, so the student sees why.
    patch = None if student_service.CONTROLLED_FIELDS & set(raw) else ProfilePatch.model_validate(raw)
    return ok(student_service.update_profile(db, user, raw, patch))


@router.post("/student/onboarding")
def onboarding(body: OnboardingIn, user: StudentUser, db: Db):
    return ok(student_service.onboarding(db, user, body))


@router.get("/student/dashboard")
def student_dashboard(user: StudentUser, db: Db):
    return ok(student_service.dashboard(db, user))


# ---------------------------------------------------------------- /jobs (reading)
@router.get("/jobs")
def list_jobs(request: Request, user: CurrentUser, db: Db):
    query = JobQuery.from_query(request.query_params)
    f = query.model_dump()
    if is_staff(user):
        items, total = jobs_service.list_for_staff(db, user, f, query.page, query.page_size)
    else:
        items, total = jobs_service.list_for_student(db, user, f, query.page, query.page_size)
    return paged(items, total, query.page, query.page_size)


@router.get("/jobs/{job_id}")
def get_job(job_id: int, user: CurrentUser, db: Db):
    return ok(jobs_service.job_detail(db, user, job_id))


@router.post("/jobs/{job_id}/save")
def save_job(job_id: int, user: StudentUser, db: Db):
    return ok({"saved": jobs_service.toggle_save(db, user, job_id)})


# ---------------------------------------------------------------- /applications (student)
@router.post("/applications", status_code=201)
def apply(body: ApplyIn, user: StudentUser, db: Db):
    return ok(apps.application_view(db, apps.apply(db, user, body.job_id)))


@router.get("/applications/me")
def my_applications(request: Request, user: StudentUser, db: Db):
    query = MyAppsQuery.from_query(request.query_params)
    items, total = apps.list_mine(db, user, query.status, query.q, query.page, query.page_size)
    return paged(items, total, query.page, query.page_size)


@router.get("/applications/{application_id}")
def application_detail(application_id: int, user: CurrentUser, db: Db):
    return ok(apps.detail(db, user, application_id))


@router.post("/applications/{application_id}/withdraw")
def withdraw(application_id: int, user: StudentUser, db: Db):
    return ok(apps.application_view(db, apps.withdraw(db, user, application_id)))


# ---------------------------------------------------------------- /offers (student)
@router.get("/offers/me")
def my_offers(user: StudentUser, db: Db):
    return ok(offers_service.list_mine(db, user))


@router.get("/offers/policies")
def offer_policies(user: CurrentUser, db: Db):
    return ok(offers_service.policy_summary(db))


@router.post("/offers/{offer_id}/respond")
def respond(offer_id: int, body: RespondIn, user: StudentUser, db: Db):
    from ..serializers import offer_view
    return ok(offer_view(offers_service.respond(db, user, offer_id, body.decision)))


# ---------------------------------------------------------------- /interviews (list)
@router.get("/interviews")
def list_interviews(request: Request, user: CurrentUser, db: Db):
    query = InterviewQuery.from_query(request.query_params)
    items, total = interviews_service.list_interviews(db, user, query.job_id, query.status, query.page, query.page_size)
    return paged(items, total, query.page, query.page_size)


# ---------------------------------------------------------------- /reminders
@router.get("/reminders")
def list_reminders(user: StudentUser, db: Db):
    return ok(content_service.list_reminders(db, user))


@router.post("/reminders", status_code=201)
def create_reminder(body: ReminderIn, user: StudentUser, db: Db):
    return ok(content_service.save_reminder(db, user, body))


@router.put("/reminders/{reminder_id}")
def update_reminder(reminder_id: int, body: ReminderIn, user: StudentUser, db: Db):
    return ok(content_service.save_reminder(db, user, body, reminder_id))


@router.post("/reminders/{reminder_id}/toggle")
def toggle_reminder(reminder_id: int, user: StudentUser, db: Db):
    return ok(content_service.toggle_reminder(db, user, reminder_id))


@router.delete("/reminders/{reminder_id}")
def delete_reminder(reminder_id: int, user: StudentUser, db: Db):
    content_service.delete_reminder(db, user, reminder_id)
    return ok({"ok": True})
