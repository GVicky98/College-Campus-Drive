"""The eligibility engine: the ONLY place that decides whether a student may apply to a job.

Every check is {key, label, passed: True | False | None, detail}; None means "cannot tell yet"
(for example, no CGPA on file). The overall state is decided in this order:
  any failed check          -> not_eligible
  any unknown check         -> profile_incomplete
  CGPA not verified         -> needs_verification
  otherwise                 -> eligible
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import utcnow
from ..enums import TIER_RANK, CompanyTier, EligibilityState, JobStatus, OfferStatus, PolicyKind, PolicyScope, SkillKind
from ..models import Company, Job, Offer, PlacementPolicy, Student
from ..serializers import iso


def _check(key: str, label: str, passed, detail: str) -> dict:
    return {"key": key, "label": label, "passed": passed, "detail": detail}


def policy_applies(p: PlacementPolicy, student: Student) -> bool:
    if p.scope == PolicyScope.COLLEGE:
        return True
    if p.scope == PolicyScope.DEPARTMENT:
        return p.scope_value == str(student.department_id)
    if p.scope == PolicyScope.ACADEMIC_YEAR:
        return p.scope_value == str(student.graduation_year)
    return False


def enabled_policies(db: Session, kind: PolicyKind) -> list[PlacementPolicy]:
    return list(db.scalars(
        select(PlacementPolicy).where(PlacementPolicy.kind == kind, PlacementPolicy.enabled.is_(True))
        .order_by(PlacementPolicy.id)
    ))


def accepted_offers(db: Session, student_id: int, exclude_offer_id: int | None = None) -> list[Offer]:
    q = select(Offer).where(Offer.student_id == student_id, Offer.status == OfferStatus.ACCEPTED)
    if exclude_offer_id:
        q = q.where(Offer.id != exclude_offer_id)
    return list(db.scalars(q))


def best_accepted_tier(db: Session, student_id: int, exclude_offer_id: int | None = None) -> int | None:
    offers = accepted_offers(db, student_id, exclude_offer_id)
    if not offers:
        return None
    return max(TIER_RANK[CompanyTier(o.company.tier)] for o in offers)


TIER_LABEL = {0: "Regular", 1: "Dream", 2: "Super Dream"}


def evaluate(db: Session, student: Student, job: Job, *, ignore_open: bool = False) -> dict:
    checks: list[dict] = []
    rule = job.rule
    academic = student.academic

    # 1. department
    dept_ids = [d.id for d in job.departments]
    if not dept_ids:
        checks.append(_check("department", "Department", True, "Open to all departments"))
    else:
        codes = ", ".join(d.code for d in job.departments)
        ok_ = student.department_id in dept_ids
        checks.append(_check("department", "Department", ok_,
                             f"{student.department.code} is eligible" if ok_ else f"Open to {codes} only"))

    # 2. graduation year
    years = list(rule.graduation_years or []) if rule else []
    if not years:
        checks.append(_check("graduationYear", "Graduation year", True, "Open to all batches"))
    else:
        ok_ = student.graduation_year in years
        checks.append(_check("graduationYear", "Graduation year", ok_,
                             f"Batch {student.graduation_year}" + ("" if ok_ else f" (needs {', '.join(map(str, years))})")))

    # 3. CGPA
    min_cgpa = float(rule.min_cgpa) if rule else 0.0
    cgpa = float(academic.cgpa) if academic and academic.cgpa is not None else None
    if cgpa is None:
        checks.append(_check("cgpa", "CGPA", None, f"No CGPA on file (needs {min_cgpa:.2f})"))
    else:
        checks.append(_check("cgpa", "CGPA", cgpa >= min_cgpa, f"{cgpa:.2f} (needs {min_cgpa:.2f} or more)"))

    # 4. arrears
    active = academic.active_arrears if academic else 0
    max_active = rule.max_active_arrears if rule else 0
    checks.append(_check("arrears", "Active arrears", active <= max_active, f"{active} (allowed up to {max_active})"))
    if rule and rule.max_arrear_history is not None:
        hist = academic.arrear_history if academic else 0
        checks.append(_check("arrearHistory", "Arrear history", hist <= rule.max_arrear_history,
                             f"{hist} (allowed up to {rule.max_arrear_history})"))

    # 5. required skills (only when the job lists any)
    required = list(rule.required_skills or []) if rule else []
    if required:
        mine = {s.lower() for s in student.tags(SkillKind.SKILL)}
        missing = [s for s in required if s.lower() not in mine]
        checks.append(_check("skills", "Required skills", not missing,
                             "All required skills listed" if not missing else f"Missing: {', '.join(missing)}"))

    # 6. job open for applications
    if not ignore_open:
        if job.status != JobStatus.PUBLISHED:
            checks.append(_check("open", "Accepting applications", False, f"This job is {job.status}"))
        elif job.deadline <= utcnow():
            checks.append(_check("open", "Accepting applications", False, "The application deadline has passed"))
        else:
            checks.append(_check("open", "Accepting applications", True, f"Apply by {iso(job.deadline)}"))

    # 7. placement policies
    accepted = None
    for p in enabled_policies(db, PolicyKind.MAX_OFFERS):
        if not policy_applies(p, student):
            continue
        limit = int(p.params.get("maxAcceptedOffers", 1))
        accepted = accepted if accepted is not None else len(accepted_offers(db, student.id))
        checks.append(_check(f"policy:{p.id}", p.name, accepted < limit,
                             f"{accepted} accepted offer(s); the limit is {limit}"))
    for p in enabled_policies(db, PolicyKind.TIER_RESTRICTION):
        if not policy_applies(p, student):
            continue
        best = best_accepted_tier(db, student.id)
        if best is None:
            continue
        job_tier = TIER_RANK[CompanyTier(job.company.tier)]
        if best == 2:
            passed, detail = False, "You already accepted a Super Dream offer"
        elif best == 0:
            passed, detail = True, "Your accepted offer is Regular tier"
        else:
            passed = job_tier > best
            detail = f"Accepted a {TIER_LABEL[best]} offer; this job is {TIER_LABEL[job_tier]} tier"
        checks.append(_check(f"policy:{p.id}", p.name, passed, detail))

    # overall state
    failed = [c["label"] for c in checks if c["passed"] is False]
    unknown = [c["label"] for c in checks if c["passed"] is None]
    if failed:
        state, summary = EligibilityState.NOT_ELIGIBLE, "Not eligible: " + ", ".join(failed)
    elif unknown:
        state, summary = EligibilityState.PROFILE_INCOMPLETE, "Complete your profile: " + ", ".join(unknown)
    elif not academic or not academic.cgpa_verified:
        state, summary = EligibilityState.NEEDS_VERIFICATION, "Eligible once the placement cell verifies your CGPA"
    else:
        state, summary = EligibilityState.ELIGIBLE, "You meet every requirement"
    return {"state": state.value, "summary": summary[:400], "checks": checks, "evaluatedAt": iso(utcnow())}


def offer_policy_checks(db: Session, student: Student, company: Company, exclude_offer_id: int | None = None) -> list[dict]:
    """Checks run when an offer is issued or accepted: accepted-offer limit and the tier rule."""
    out = []
    limits = [int(p.params.get("maxAcceptedOffers", 1)) for p in enabled_policies(db, PolicyKind.MAX_OFFERS)
              if p.scope in (PolicyScope.COLLEGE, PolicyScope.DEPARTMENT) and policy_applies(p, student)]
    accepted = len(accepted_offers(db, student.id, exclude_offer_id))
    if limits:
        limit = max(limits)
        out.append({"label": "Accepted-offer limit", "passed": accepted < limit,
                    "detail": f"{accepted} accepted; the limit is {limit}"})
    tier_policies = enabled_policies(db, PolicyKind.TIER_RESTRICTION)
    best = best_accepted_tier(db, student.id, exclude_offer_id)
    if tier_policies and best is not None:
        rank = TIER_RANK[CompanyTier(company.tier)]
        passed = best == 0 or rank > best
        out.append({"label": "Tier rule", "passed": passed,
                    "detail": f"Holds a {TIER_LABEL[best]} offer; this company is {TIER_LABEL[rank]} tier"})
    return out


def count_eligible_students(db: Session, job: Job, *, ignore_open: bool = True) -> int:
    students = db.scalars(select(Student)).unique().all()
    return sum(1 for s in students if evaluate(db, s, job, ignore_open=ignore_open)["state"] != EligibilityState.NOT_ELIGIBLE)


def total_students(db: Session) -> int:
    return db.scalar(select(func.count(Student.id))) or 0
