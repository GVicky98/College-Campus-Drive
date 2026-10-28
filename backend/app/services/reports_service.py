"""Faculty dashboard and the placement report (aggregates only — no individual student data)."""
from collections import Counter
from datetime import timedelta

from sqlalchemy import false, func, select
from sqlalchemy.orm import Session

from ..database import utcnow
from ..enums import ApplicationStatus, EligibilityState, InterviewStatus, JobStatus, OfferStatus
from ..models import Application, ApplicationStatusHistory, Company, Department, Interview, Job, Offer, Student, User
from ..serializers import iso, job_view, sid
from . import audit
from .applications_service import STATUS_LABEL
from .eligibility import evaluate
from .review_service import to_csv

STATUSES = list(STATUS_LABEL)


def _students(db: Session, dept=None, year=None) -> list[Student]:
    q = select(Student)
    if dept:
        q = q.where(Student.department_id == dept)
    if year:
        q = q.where(Student.graduation_year == year)
    return list(db.scalars(q).unique().all())


def _eligible_for_any(db: Session, student: Student, jobs: list[Job]) -> bool:
    return any(evaluate(db, student, j)["state"] == EligibilityState.ELIGIBLE for j in jobs)


def faculty_dashboard(db: Session, dept=None, year=None, company_id=None, days=None) -> dict:
    now = utcnow()
    students = _students(db, dept, year)
    sids = {s.id for s in students}
    app_q = select(Application).where(Application.student_id.in_(sids) if sids else false())
    if company_id:
        app_q = app_q.join(Job).where(Job.company_id == company_id)
    if days:
        app_q = app_q.where(Application.applied_at >= now - timedelta(days=days))
    apps = list(db.scalars(app_q).unique().all())
    status_count = Counter(a.status for a in apps)
    open_jobs = list(db.scalars(select(Job).where(Job.status == JobStatus.PUBLISHED, Job.deadline > now,
                                                  Job.archived_at.is_(None))).unique().all())
    offers = [o for o in db.scalars(select(Offer)).all() if o.student_id in sids and (not company_id or o.company_id == company_id)]

    dept_chart = []
    for d in db.scalars(select(Department).order_by(Department.code)):
        ds = [s for s in students if s.department_id == d.id]
        if ds:
            placed = sum(1 for s in ds if s.placement_status == "placed")
            dept_chart.append({"dept": d.code, "placed": placed, "notPlaced": len(ds) - placed, "students": len(ds)})

    upcoming_drives = [j for j in open_jobs + list(db.scalars(select(Job).where(Job.status == JobStatus.CLOSED)).unique())
                       if j.drive and j.drive.drive_date and j.drive.drive_date > now]
    upcoming_drives.sort(key=lambda j: j.drive.drive_date)
    interviews = db.scalars(select(Interview).where(Interview.status == InterviewStatus.SCHEDULED, Interview.scheduled_at > now)
                            .order_by(Interview.scheduled_at).limit(5)).unique().all()
    recent = sorted(apps, key=lambda a: a.applied_at, reverse=True)[:6]
    history = db.scalars(select(ApplicationStatusHistory).where(ApplicationStatusHistory.status != ApplicationStatus.APPLIED)
                         .order_by(ApplicationStatusHistory.at.desc()).limit(30)).all()
    app_by_id = {a.id: a for a in apps}
    activity = []
    for h in history:
        a = app_by_id.get(h.application_id)
        if a:
            activity.append({"at": iso(h.at), "status": h.status, "student": a.student.user.name, "job": a.job.title,
                             "company": a.job.company.name, "applicationId": sid(a.id)})
        if len(activity) == 6:
            break
    total_companies = 1 if company_id else db.scalar(select(func.count(Company.id)).where(Company.archived_at.is_(None))) or 0
    return {
        "metrics": {
            "totalCompanies": total_companies,
            "activeJobs": len([j for j in open_jobs if not company_id or j.company_id == company_id]),
            "totalApplications": len(apps),
            "eligibleStudents": sum(1 for s in students if _eligible_for_any(db, s, open_jobs)),
            "shortlisted": status_count[ApplicationStatus.SHORTLISTED],
            "selected": status_count[ApplicationStatus.SELECTED] + status_count[ApplicationStatus.OFFER_RECEIVED],
            "offers": len(offers),
        },
        "deptChart": dept_chart,
        "statusDist": [{"status": s, "label": STATUS_LABEL[s], "count": status_count[s]} for s in STATUSES],
        "upcomingDrives": [job_view(j, applicantCount=db.scalar(select(func.count(Application.id)).where(Application.job_id == j.id)) or 0)
                           for j in upcoming_drives[:5]],
        "nearingDeadline": [job_view(j) for j in sorted(open_jobs, key=lambda j: j.deadline) if j.deadline <= now + timedelta(days=6)],
        "upcomingInterviews": [{"id": sid(i.id), "round": i.round_name, "at": iso(i.scheduled_at), "job": i.job.title,
                                "company": i.job.company.name, "candidates": len(i.candidates), "notified": i.notified}
                               for i in interviews],
        "recentApplications": [{"applicationId": sid(a.id), "student": a.student.user.name, "studentCode": a.student.student_code,
                                "job": a.job.title, "company": a.job.company.name, "status": a.status, "at": iso(a.applied_at)}
                               for a in recent],
        "activity": activity,
        "graduationYears": sorted({s.graduation_year for s in db.scalars(select(Student)).unique()}),
    }


def _report_data(db: Session, academic_year=None, dept=None, company_id=None, job_id=None, app_status=None, offer_status=None):
    students = _students(db, dept, academic_year)
    sids = {s.id for s in students}
    app_q = select(Application).join(Job)
    if company_id:
        app_q = app_q.where(Job.company_id == company_id)
    if job_id:
        app_q = app_q.where(Application.job_id == job_id)
    if app_status:
        app_q = app_q.where(Application.status == app_status)
    apps = [a for a in db.scalars(app_q).unique().all() if a.student_id in sids]
    off_q = select(Offer)
    if company_id:
        off_q = off_q.where(Offer.company_id == company_id)
    if job_id:
        off_q = off_q.where(Offer.job_id == job_id)
    if offer_status:
        off_q = off_q.where(Offer.status == offer_status)
    offers = [o for o in db.scalars(off_q).all() if o.student_id in sids]
    return students, apps, offers


def placement_report(db: Session, **f) -> dict:
    students, apps, offers = _report_data(db, **f)
    jobs = list(db.scalars(select(Job).where(Job.status == JobStatus.PUBLISHED, Job.archived_at.is_(None))).unique().all())
    if f.get("company_id"):
        jobs = [j for j in jobs if j.company_id == f["company_id"]]
    if f.get("job_id"):
        jobs = [j for j in jobs if j.id == f["job_id"]]
    eligible_ids = {s.id for s in students if _eligible_for_any(db, s, jobs)}
    applied_ids = {a.student_id for a in apps}
    accepted = [o for o in offers if o.status == OfferStatus.ACCEPTED]
    placed_ids = {o.student_id for o in accepted}

    by_dept, elig_vs_applied = [], []
    for d in db.scalars(select(Department).order_by(Department.code)):
        ds = {s.id for s in students if s.department_id == d.id}
        if not ds:
            continue
        do = [o for o in offers if o.student_id in ds]
        by_dept.append({"dept": d.code, "offers": len(do), "accepted": sum(o.status == OfferStatus.ACCEPTED for o in do),
                        "placedStudents": len(placed_ids & ds), "students": len(ds)})
        elig_vs_applied.append({"dept": d.code, "eligible": len(eligible_ids & ds), "applied": len(applied_ids & ds)})
    by_company = {}
    for o in offers:
        r = by_company.setdefault(o.company.name, {"company": o.company.name, "offers": 0, "accepted": 0})
        r["offers"] += 1
        r["accepted"] += o.status == OfferStatus.ACCEPTED

    app_ids = {a.id for a in apps}
    # Distinct applications that ever reached a stage, from the status history.
    reached = {(h.status, h.application_id) for h in db.scalars(select(ApplicationStatusHistory)).all()
               if h.application_id in app_ids}
    ever = lambda stage: sum(1 for st, _ in reached if st == stage)  # noqa: E731

    months = []
    now = utcnow()
    for back in range(11, -1, -1):
        y, m = now.year, now.month - back
        while m <= 0:
            m += 12
            y -= 1
        label = f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m - 1]} {str(y)[2:]}"
        months.append({"month": label,
                       "applications": sum(1 for a in apps if (a.applied_at.year, a.applied_at.month) == (y, m)),
                       "offers": sum(1 for o in offers if (o.offered_at.year, o.offered_at.month) == (y, m))})
    status_count = Counter(a.status for a in apps)
    total = len(students)
    return {
        "kpis": {
            "totalStudents": total, "eligibleStudents": len(eligible_ids), "appliedStudents": len(applied_ids),
            "uniqueStudentsPlaced": len(placed_ids), "totalOffers": len(offers), "acceptedOffers": len(accepted),
            "placementPct": round(100 * len(placed_ids) / total, 1) if total else 0,
        },
        "offersByDept": by_dept,
        "companyOffers": sorted(by_company.values(), key=lambda r: -r["offers"]),
        "eligibleVsApplied": elig_vs_applied,
        "funnel": [
            {"stage": "Eligible students", "value": len(eligible_ids)},
            {"stage": "Applied", "value": len(apps)},
            {"stage": "Shortlisted", "value": ever(ApplicationStatus.SHORTLISTED)},
            {"stage": "Interviewed", "value": ever(ApplicationStatus.INTERVIEW)},
            {"stage": "Selected", "value": ever(ApplicationStatus.SELECTED)},
            {"stage": "Offers", "value": len(offers)},
        ],
        "monthly": months,
        "statusDist": [{"status": s, "label": STATUS_LABEL[s], "count": status_count[s]} for s in STATUSES],
    }


def export_placement_csv(db: Session, actor: User, **f) -> str:
    _students_, _apps, offers = _report_data(db, **f)
    offers = sorted(offers, key=lambda o: o.offered_at, reverse=True)[:5000]
    rows = [[o.student.student_code or "", o.student.user.name, o.student.department.code, o.company.name, o.job.title,
             f"{float(o.ctc_lpa):g}", o.status, f"{o.offered_at:%Y-%m-%d}"] for o in offers]
    audit.record(db, "report.export", "Placement CSV", actor=actor, reason=f"Placement offers CSV ({len(rows)} rows)")
    db.commit()
    return to_csv(["Student ID", "Name", "Department", "Company", "Job", "Package (LPA)", "Offer status", "Offer date"], rows)
