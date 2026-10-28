"""Small helpers shared by the services."""
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ..errors import NotFound
from ..models import Student, User


def student_of(db: Session, user: User) -> Student:
    s = db.scalar(select(Student).where(Student.user_id == user.id))
    if not s:
        raise NotFound("Student profile not found.")
    return s


def like(text: str) -> str:
    """A LIKE pattern for user text, with % and _ escaped."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def paginate(db: Session, query: Select, page: int, page_size: int) -> tuple[list, int]:
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).unique().all()
    return list(rows), total


def slice_page(items: list, page: int, page_size: int) -> list:
    return items[(page - 1) * page_size: page * page_size]
