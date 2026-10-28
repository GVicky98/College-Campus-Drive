"""Offers: students view and respond; staff issue and update (placement-policy checks on both)."""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import utcnow
from ..enums import ApplicationStatus, JobStatus, NotificationKind, OfferStatus, PolicyKind, RoleName
from ..errors import Conflict, NotFound, ValidationFailed
from ..models import Application, Company, Department, Offer, PlacementPolicy, Student, User
from ..serializers import offer_view
from . import audit
from .common import like, paginate, student_of
from .eligibility import offer_policy_checks
from .notifications import notify
from .profile import set_placement_status


def list_mine(db: Session, user: User) -> list[dict]:
    student = student_of(db, user)
    rows = db.scalars(select(Offer).where(Offer.student_id == student.id).order_by(Offer.offered_at.desc()))
    return [offer_view(o) for o in rows]


def policy_summary(db: Session) -> list[dict]:
    rows = db.scalars(select(PlacementPolicy).where(
        PlacementPolicy.enabled.is_(True),
        PlacementPolicy.kind.in_([PolicyKind.MAX_OFFERS, PolicyKind.TIER_RESTRICTION, PolicyKind.ACCEPTED_OFFER]),
    ).order_by(PlacementPolicy.id))
    return [{"id": str(p.id), "name": p.name, "description": p.description, "params": p.params, "scope": p.scope} for p in rows]


def respond(db: Session, user: User, offer_id: int, decision: str) -> Offer:
    student = student_of(db, user)
    offer = db.scalar(select(Offer).where(Offer.id == offer_id).with_for_update())
    if not offer or offer.student_id != student.id:
        raise NotFound("Offer not found.")
    if offer.status != OfferStatus.RECEIVED:
        raise Conflict(f"This offer is already {offer.status}.")
    if offer.accept_by < utcnow():
        raise Conflict("The deadline to respond to this offer has passed.")
    if decision == OfferStatus.ACCEPTED:
        failed = [c for c in offer_policy_checks(db, student, offer.company, exclude_offer_id=offer.id) if not c["passed"]]
        if failed:
            audit.deny(db, user, "offer.accepted", f"Offer {offer.id}", failed[0]["detail"])
            raise Conflict(f"You cannot accept this offer: {failed[0]['label']} — {failed[0]['detail']}.")
    offer.status = decision
    set_placement_status(db, student)
    audit.record(db, f"offer.{decision}", f"Offer {offer.id} · {offer.company.name}", actor=user)
    db.commit()
    return offer


# ---------------------------------------------------------------- staff
STAFF_GRAPH = {
    OfferStatus.PENDING: {OfferStatus.RECEIVED, OfferStatus.WITHDRAWN},
    OfferStatus.RECEIVED: {OfferStatus.ACCEPTED, OfferStatus.DECLINED, OfferStatus.WITHDRAWN},
    OfferStatus.ACCEPTED: {OfferStatus.WITHDRAWN},
    OfferStatus.DECLINED: set(),
    OfferStatus.WITHDRAWN: set(),
}


def _staff_query(q=None, status=None, dept=None, company_id=None):
    query = (select(Offer).join(Student, Student.id == Offer.student_id).join(User, User.id == Student.user_id)
             .join(Company, Company.id == Offer.company_id))
    if q:
        query = query.where(or_(User.name.ilike(like(q)), Student.student_code.ilike(like(q)), Company.name.ilike(like(q))))
    if status:
        query = query.where(Offer.status == status)
    if dept:
        query = query.where(Student.department_id == dept)
    if company_id:
        query = query.where(Offer.company_id == company_id)
    return query.order_by(Offer.offered_at.desc(), Offer.id.desc())


def list_staff(db: Session, viewer: User, f: dict, page: int, page_size: int):
    mask = viewer.role_name != RoleName.ADMIN
    rows, total = paginate(db, _staff_query(**f), page, page_size)
    items = [offer_view(o, with_student=True, mask=mask) for o in rows]

    all_offers = db.scalars(select(Offer)).all()
    by_dept = []
    for d in db.scalars(select(Department).order_by(Department.code)):
        students = db.scalar(select(func.count(Student.id)).where(Student.department_id == d.id)) or 0
        dept_offers = [o for o in all_offers if o.student.department_id == d.id]
        placed = len({o.student_id for o in dept_offers if o.status == OfferStatus.ACCEPTED})
        if students or dept_offers:
            by_dept.append({"dept": d.code, "offers": len(dept_offers), "placed": placed, "students": students})
    by_company = {}
    for o in all_offers:
        row = by_company.setdefault(o.company.name, {"company": o.company.name, "offers": 0, "accepted": 0})
        row["offers"] += 1
        row["accepted"] += o.status == OfferStatus.ACCEPTED
    waiting = db.scalars(select(Application).where(Application.status == ApplicationStatus.SELECTED,
                                                   ~Application.id.in_(select(Offer.application_id)))
                         .order_by(Application.updated_at).limit(100)).unique().all()
    from .applications_service import application_view
    meta = {
        "byDept": by_dept,
        "byCompany": sorted(by_company.values(), key=lambda r: -r["offers"]),
        "totals": {"offers": len(all_offers), "accepted": sum(o.status == OfferStatus.ACCEPTED for o in all_offers),
                   "placed": len({o.student_id for o in all_offers if o.status == OfferStatus.ACCEPTED})},
        "selectedWithoutOffer": [application_view(db, a, with_student=True, mask=mask) for a in waiting],
    }
    return items, total, meta


def create(db: Session, actor: User, application_id: int, ctc_lpa: float, accept_by) -> Offer:
    from decimal import Decimal
    from .applications_service import add_history
    app = db.scalar(select(Application).where(Application.id == application_id).with_for_update())
    if not app:
        raise NotFound("Application not found.")
    if app.status != ApplicationStatus.SELECTED:
        raise Conflict("Only a selected applicant can receive an offer.")
    if app.offer:
        raise Conflict("This application already has an offer.")
    if app.job.status == JobStatus.CANCELLED:
        raise Conflict("The job was cancelled.")
    if accept_by <= utcnow():
        raise ValidationFailed("The acceptance deadline must be in the future.", field="acceptBy")
    checks = offer_policy_checks(db, app.student, app.job.company)
    failed = [c for c in checks if not c["passed"]]
    if failed:
        audit.deny(db, actor, "offer.create", f"Application {app.id}", failed[0]["detail"])
        raise Conflict(f"Policy check failed: {failed[0]['label']} — {failed[0]['detail']}.")
    offer = Offer(application_id=app.id, student_id=app.student_id, job_id=app.job_id, company_id=app.job.company_id,
                  ctc_lpa=Decimal(str(ctc_lpa)), accept_by=accept_by, status=OfferStatus.RECEIVED, policy_checks=checks)
    db.add(offer)
    app.status = ApplicationStatus.OFFER_RECEIVED
    app.updated_at = utcnow()
    add_history(app, ApplicationStatus.OFFER_RECEIVED, "Official offer issued", actor)
    db.flush()
    set_placement_status(db, app.student)
    notify(db, app.student.user_id, f"Offer received — {app.job.company.name}",
           f"Respond before {accept_by:%d %b %Y}.", NotificationKind.OFFER, "/student/offers")
    audit.record(db, "offer.create", f"Offer {offer.id} · Application {app.id}", actor=actor, reason=f"{ctc_lpa:g} LPA")
    db.commit()
    db.refresh(offer)
    return offer


def set_status_staff(db: Session, actor: User, offer_id: int, status: str, reason: str | None) -> Offer:
    offer = db.scalar(select(Offer).where(Offer.id == offer_id).with_for_update())
    if not offer:
        raise NotFound("Offer not found.")
    current, target = OfferStatus(offer.status), OfferStatus(status)
    if target not in STAFF_GRAPH[current]:
        raise Conflict(f"A {current} offer cannot become {target}.")
    if target == OfferStatus.WITHDRAWN and len((reason or "").strip()) < 3:
        raise ValidationFailed("Give a reason for withdrawing (at least 3 characters).", field="reason")
    if target == OfferStatus.ACCEPTED:  # an offline acceptance may be recorded after the deadline
        failed = [c for c in offer_policy_checks(db, offer.student, offer.company, exclude_offer_id=offer.id) if not c["passed"]]
        if failed:
            raise Conflict(f"Policy check failed: {failed[0]['label']} — {failed[0]['detail']}.")
    offer.status = target
    set_placement_status(db, offer.student)
    body = f"Your offer is now {target}." + (f" Reason: {reason.strip()}" if reason else "")
    notify(db, offer.student.user_id, f"Offer update — {offer.company.name}", body, NotificationKind.OFFER, "/student/offers")
    audit.record(db, f"offer.{target}", f"Offer {offer.id} · {offer.company.name}", actor=actor, reason=reason)
    db.commit()
    return offer
