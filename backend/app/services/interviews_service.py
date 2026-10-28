"""Interviews: listing (students see their own rounds). Scheduling rules live in interviews_admin.py."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import ensure_permission
from ..enums import RoleName
from ..models import Application, Interview, User, interview_candidates
from ..serializers import company_dict, interview_dict, job_dict
from .common import paginate, student_of


def interview_view(i: Interview, *, staff: bool) -> dict:
    return {
        "interview": interview_dict(i),
        "job": job_dict(i.job),
        "company": company_dict(i.job.company),
        "candidates": [
            {"applicationId": str(a.id), "name": a.student.user.name, "studentCode": a.student.student_code or "",
             "status": a.status}
            for a in i.candidates
        ] if staff else [],
    }


def list_interviews(db: Session, user: User, job_id: int | None, status: str | None, page: int, page_size: int):
    q = select(Interview)
    staff = user.role_name != RoleName.STUDENT
    if staff:
        ensure_permission(db, user, "applications.review")
    else:
        sid = student_of(db, user).id
        q = q.where(Interview.id.in_(
            select(interview_candidates.c.interview_id).join(Application, Application.id == interview_candidates.c.application_id)
            .where(Application.student_id == sid)))
    if job_id:
        q = q.where(Interview.job_id == job_id)
    if status:
        q = q.where(Interview.status == status)
    rows, total = paginate(db, q.order_by(Interview.scheduled_at, Interview.id), page, page_size)
    return [interview_view(i, staff=staff) for i in rows], total
