"""Companies: list, detail, create/update and soft archive."""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import utcnow
from ..enums import ApplicationStatus, JobStatus, OfferStatus
from ..errors import Conflict, NotFound
from ..models import Application, Company, Interview, Job, Offer, User
from ..serializers import company_dict, job_dict
from . import audit
from .common import like, paginate

COMPANY_VIEW_PERMS = ("companies.manage", "jobs.create", "applications.review", "students.view")


def _counts(db: Session, company_id: int) -> dict:
    jobs = db.scalar(select(func.count(Job.id)).where(Job.company_id == company_id)) or 0
    active = db.scalar(select(func.count(Job.id)).where(Job.company_id == company_id, Job.status == JobStatus.PUBLISHED)) or 0
    offers = db.scalar(select(func.count(Offer.id)).where(Offer.company_id == company_id)) or 0
    return {"jobCount": jobs, "activeJobs": active, "offers": offers}


def list_companies(db: Session, q, industry, tier, archived, page, page_size):
    query = select(Company)
    if q:
        query = query.where(or_(Company.name.ilike(like(q)), Company.industry.ilike(like(q))))
    if industry:
        query = query.where(Company.industry == industry)
    if tier:
        query = query.where(Company.tier == tier)
    archived = archived or "exclude"
    if archived == "exclude":
        query = query.where(Company.archived_at.is_(None))
    elif archived == "only":
        query = query.where(Company.archived_at.is_not(None))
    rows, total = paginate(db, query.order_by(Company.name), page, page_size)
    industries = sorted(set(db.scalars(select(Company.industry).where(Company.archived_at.is_(None)))))
    return [{"company": company_dict(c), **_counts(db, c.id)} for c in rows], total, industries


def get_company(db: Session, company_id: int) -> Company:
    c = db.get(Company, company_id)
    if not c:
        raise NotFound("Company not found.")
    return c


def detail(db: Session, company_id: int) -> dict:
    c = get_company(db, company_id)
    jobs = db.scalars(select(Job).where(Job.company_id == c.id).order_by(Job.deadline.desc())).unique().all()
    out = []
    for j in jobs:
        apps = db.scalars(select(Application.status).where(Application.job_id == j.id)).all()
        out.append({
            "job": job_dict(j),
            "applicants": len(apps),
            "selected": sum(1 for s in apps if s in (ApplicationStatus.SELECTED, ApplicationStatus.OFFER_RECEIVED)),
            "offers": db.scalar(select(func.count(Offer.id)).where(Offer.job_id == j.id)) or 0,
        })
    interviews = db.scalar(select(func.count(Interview.id)).join(Job).where(Job.company_id == c.id)) or 0
    return {"company": company_dict(c), "jobs": out, "interviews": interviews,
            "acceptedOffers": db.scalar(select(func.count(Offer.id)).where(Offer.company_id == c.id, Offer.status == OfferStatus.ACCEPTED)) or 0}


def save(db: Session, user: User, body, company_id: int | None = None) -> Company:
    c = get_company(db, company_id) if company_id else Company()
    if company_id and c.archived_at:
        raise Conflict("Restore this company before editing it.")
    clash = db.scalar(select(Company.id).where(func.lower(Company.name) == body.name.lower(), Company.id != (company_id or 0)))
    if clash:
        raise Conflict("A company with this name already exists.")
    before = company_dict(c) if company_id else None
    c.name, c.website, c.industry = body.name, body.website, body.industry
    c.description, c.contact_name, c.contact_email = body.description, body.contact_name, body.contact_email
    c.contact_phone = body.contact_phone or None
    c.tier = body.tier
    if body.color:
        c.brand_color = body.color
    db.add(c)
    db.flush()
    if before:
        changed = [k for k, v in company_dict(c).items() if before.get(k) != v and k not in ("createdAt",)]
        if changed:
            audit.record(db, "company.update", f"Company {c.id} · {c.name}", actor=user, reason="Changed: " + ", ".join(changed))
    else:
        audit.record(db, "company.create", f"Company {c.id} · {c.name}", actor=user)
    db.commit()
    return c


def archive(db: Session, user: User, company_id: int, archived: bool) -> Company:
    c = get_company(db, company_id)
    if archived and not c.archived_at:
        published = db.scalar(select(func.count(Job.id)).where(Job.company_id == c.id, Job.status == JobStatus.PUBLISHED))
        if published:
            raise Conflict("This company has published jobs. Close or cancel them before archiving.")
        c.archived_at = utcnow()
        audit.record(db, "company.archive", f"Company {c.id} · {c.name}", actor=user)
    elif not archived and c.archived_at:
        c.archived_at = None
        audit.record(db, "company.unarchive", f"Company {c.id} · {c.name}", actor=user)
    db.commit()
    return c
