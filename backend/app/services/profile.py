"""Student profile helpers: completion percentage, skill tags and placement status."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..enums import OfferStatus, PlacementStatus, SkillKind
from ..models import Application, Offer, Student, StudentSkill


def compute_completion(s: Student) -> int:
    """Nine equally weighted items, as a whole percentage."""
    a = s.academic
    items = [
        bool(s.phone),
        bool(a and a.cgpa is not None),
        len(s.tags(SkillKind.SKILL)) >= 3,
        len(s.tags(SkillKind.INTEREST)) >= 1,
        len(s.tags(SkillKind.PREFERRED_ROLE)) >= 1,
        bool(s.resume_file),
        bool(s.portfolio_url),
        bool(s.degree),
        bool(s.student_code),
    ]
    return round(100 * sum(items) / len(items))


def missing_items(s: Student) -> list[str]:
    a = s.academic
    checks = [
        (bool(s.phone), "phone number"),
        (bool(a and a.cgpa is not None), "CGPA"),
        (len(s.tags(SkillKind.SKILL)) >= 3, "at least 3 skills"),
        (len(s.tags(SkillKind.INTEREST)) >= 1, "interests"),
        (len(s.tags(SkillKind.PREFERRED_ROLE)) >= 1, "preferred roles"),
        (bool(s.resume_file), "resume"),
        (bool(s.portfolio_url), "portfolio link"),
    ]
    return [label for ok, label in checks if not ok]


def set_tags(s: Student, kind: SkillKind, names: list[str]) -> None:
    """Replace one kind of tag, de-duplicated case-insensitively, order kept."""
    seen, clean = set(), []
    for n in names:
        n = n.strip()
        if n and n.lower() not in seen:
            seen.add(n.lower())
            clean.append(n[:80])
    keep = [t for t in s.skills if t.kind != kind]
    s.skills[:] = keep + [StudentSkill(kind=kind, name=n) for n in clean]


def set_placement_status(db: Session, s: Student) -> None:
    """placed if any accepted offer; else in_process if any application; else unplaced. opted_out is never changed."""
    if s.placement_status == PlacementStatus.OPTED_OUT:
        return
    db.flush()
    if db.scalar(select(func.count(Offer.id)).where(Offer.student_id == s.id, Offer.status == OfferStatus.ACCEPTED)):
        s.placement_status = PlacementStatus.PLACED
    elif db.scalar(select(func.count(Application.id)).where(Application.student_id == s.id)):
        s.placement_status = PlacementStatus.IN_PROCESS
    else:
        s.placement_status = PlacementStatus.UNPLACED
