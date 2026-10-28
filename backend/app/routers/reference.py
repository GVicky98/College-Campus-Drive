"""/health and /reference/filters (option lists for dropdowns)."""
from fastapi import APIRouter
from sqlalchemy import select, text

from ..deps import CurrentUser, Db
from ..enums import JobStatus, RoleName
from ..models import AcademicYear, Company, Department, Job
from ..schemas.common import ok

router = APIRouter(tags=["reference"])


@router.get("/health")
def health(db: Db):
    db.execute(text("SELECT 1"))
    return ok({"status": "ok"})


@router.get("/reference/filters")
def filters(user: CurrentUser, db: Db):
    years = db.scalars(select(AcademicYear).order_by(AcademicYear.graduation_year)).all()
    depts = db.scalars(select(Department).order_by(Department.code)).all()
    companies = db.scalars(select(Company).where(Company.archived_at.is_(None)).order_by(Company.name)).all()
    q = (select(Job).join(Company).where(Job.archived_at.is_(None), Company.archived_at.is_(None))
         .order_by(Company.name, Job.title))
    if user.role_name == RoleName.STUDENT:
        q = q.where(Job.status == JobStatus.PUBLISHED)
    jobs = db.scalars(q).unique().all()
    return ok({
        "graduationYears": [
            {"value": str(y.graduation_year), "label": f"{y.label} (batch {y.graduation_year})"} for y in years
        ],
        "departments": [{"value": str(d.id), "label": d.code, "name": d.name} for d in depts],
        "companies": [{"value": str(c.id), "label": c.name} for c in companies],
        "jobs": [
            {"value": str(j.id), "label": f"{j.company.name} — {j.title}", "companyId": str(j.company_id),
             "status": j.status}
            for j in jobs
        ],
    })
