"""Charts the assistant can show. The model picks a metric and a style; the numbers always come from here.

Chart shape: {title, subtitle?, type, types[], labels[], series:[{name, values[]}], unit?}
"""
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...enums import EligibilityState, JobStatus, OfferStatus
from ...errors import Forbidden, ValidationFailed
from ...models import Application, Company, Department, Job, Offer, Student, User
from ..applications_service import STATUS_LABEL
from ..common import student_of
from ..eligibility import evaluate
from ..reports_service import placement_report

SINGLE = ["pie", "donut", "bar", "hbar"]
MULTI = ["bar", "stacked", "hbar"]
TREND = ["line", "area", "bar"]
COMPANY_CAP = 20
PLACEMENT_LABEL = {"placed": "Placed", "in_process": "In process", "unplaced": "Unplaced", "opted_out": "Opted out"}

# metric -> (permissions (any), default type, allowed types, title)
STAFF_METRICS = {
    "placement_status": (("students.view", "reports.view"), "pie", SINGLE, "Students by placement status"),
    "students_by_department": (("students.view", "reports.view"), "bar", SINGLE, "Students by department"),
    "cgpa_distribution": (("students.view",), "bar", SINGLE, "CGPA distribution"),
    "placed_vs_unplaced_by_department": (("reports.view",), "stacked", MULTI, "Placed vs not placed, by department"),
    "placement_rate_by_department": (("reports.view",), "bar", ["bar", "hbar", "line"], "Placement rate by department"),
    "offers_by_department": (("reports.view",), "bar", MULTI, "Offers by department"),
    "offers_by_company": (("reports.view",), "bar", MULTI, "Offers by company"),
    "companies_overview": (("reports.view", "companies.manage", "applications.review"), "bar", MULTI, "Jobs, applications and offers by company"),
    "applications_by_stage": (("reports.view", "applications.review"), "donut", SINGLE, "Applications by stage"),
    "placement_funnel": (("reports.view",), "hbar", ["hbar", "bar", "area"], "Placement funnel"),
    "monthly_trend": (("reports.view",), "line", TREND, "Applications and offers per month"),
}
STUDENT_METRICS = {
    "my_applications_by_status": ("donut", SINGLE, "My applications by status"),
    "my_job_eligibility": ("pie", SINGLE, "My eligibility for open jobs"),
}


def _students(db, dept_id=None, year=None):
    q = select(Student)
    if dept_id:
        q = q.where(Student.department_id == dept_id)
    if year:
        q = q.where(Student.graduation_year == year)
    return list(db.scalars(q).unique().all())


def _finish(title, default, allowed, requested, labels, series, unit=None, subtitle=None):
    if not labels or all(not any(s["values"]) for s in series):
        raise ValidationFailed("There is no data to chart for these filters.")
    if len(series) > 1:
        allowed = [t for t in allowed if t not in ("pie", "donut")]
    note = None
    chosen = requested if requested in allowed else (default if default in allowed else allowed[0])
    if requested and requested != chosen:
        note = f"A {requested} chart does not suit this data, so a {chosen} chart is shown. The user can switch between: {', '.join(allowed)}."
    chart = {"title": title, "type": chosen, "types": allowed, "labels": labels, "series": series}
    if unit:
        chart["unit"] = unit
    if subtitle:
        chart["subtitle"] = subtitle
    return chart, note


def _companies(db, cap=COMPANY_CAP):
    rows = []
    for c in db.scalars(select(Company).where(Company.archived_at.is_(None))):
        rows.append({
            "name": c.name,
            "jobs": db.scalar(select(func.count(Job.id)).where(Job.company_id == c.id)) or 0,
            "applications": db.scalar(select(func.count(Application.id)).join(Job).where(Job.company_id == c.id)) or 0,
            "offers": db.scalar(select(func.count(Offer.id)).where(Offer.company_id == c.id)) or 0,
            "accepted": db.scalar(select(func.count(Offer.id)).where(Offer.company_id == c.id, Offer.status == OfferStatus.ACCEPTED)) or 0,
        })
    rows.sort(key=lambda r: (-r["offers"], -r["applications"], -r["jobs"], r["name"]))
    sub = f"Top {cap} of {len(rows)} companies." if len(rows) > cap else f"All {len(rows)} companies."
    return rows[:cap], sub


def staff_chart(db: Session, user: User, metric: str, chart_type=None, dept_id=None, year=None, dept_code=None):
    perms, default, allowed, title = STAFF_METRICS[metric]
    if not any(user.can(p) for p in perms):
        raise Forbidden("This chart needs a permission you do not have.")
    filt = " ".join(x for x in [f"department {dept_code}" if dept_code else "", f"batch {year}" if year else ""] if x)
    subtitle = f"Filtered to {filt}" if filt else None
    students = _students(db, dept_id, year)
    depts = {d.id: d.code for d in db.scalars(select(Department).order_by(Department.code))}

    if metric == "placement_status":
        c = Counter(s.placement_status for s in students)
        labels = [PLACEMENT_LABEL[k] for k in PLACEMENT_LABEL if c[k]]
        return _finish(title, default, allowed, chart_type, labels, [{"name": "Students", "values": [c[k] for k in PLACEMENT_LABEL if c[k]]}], subtitle=subtitle)
    if metric == "students_by_department":
        c = Counter(depts[s.department_id] for s in students)
        labels = sorted(c)
        return _finish(title, default, allowed, chart_type, labels, [{"name": "Students", "values": [c[k] for k in labels]}], subtitle=subtitle)
    if metric == "cgpa_distribution":
        bands = ["Below 6", "6 – 7", "7 – 8", "8 – 9", "9 and above", "No CGPA yet"]
        c = Counter()
        for s in students:
            g = float(s.academic.cgpa) if s.academic and s.academic.cgpa is not None else None
            c[bands[5] if g is None else bands[0] if g < 6 else bands[1] if g < 7 else bands[2] if g < 8 else bands[3] if g < 9 else bands[4]] += 1
        return _finish(title, default, allowed, chart_type, bands, [{"name": "Students", "values": [c[b] for b in bands]}], subtitle=subtitle)
    if metric in ("placed_vs_unplaced_by_department", "placement_rate_by_department"):
        labels, placed, not_placed, rate = [], [], [], []
        for did, code in depts.items():
            ds = [s for s in students if s.department_id == did]
            if not ds:
                continue
            p = sum(1 for s in ds if s.placement_status == "placed")
            labels.append(code)
            placed.append(p)
            not_placed.append(len(ds) - p)
            rate.append(round(100 * p / len(ds), 1))
        if metric == "placement_rate_by_department":
            return _finish(title, default, allowed, chart_type, labels, [{"name": "Placement %", "values": rate}], unit="%", subtitle=subtitle)
        return _finish(title, default, allowed, chart_type, labels, [{"name": "Placed", "values": placed}, {"name": "Not placed", "values": not_placed}], subtitle=subtitle)

    report = placement_report(db, academic_year=year, dept=dept_id, company_id=None, job_id=None, app_status=None, offer_status=None)
    if metric == "offers_by_department":
        rows = report["offersByDept"]
        return _finish(title, default, allowed, chart_type, [r["dept"] for r in rows],
                       [{"name": "Offers", "values": [r["offers"] for r in rows]}, {"name": "Accepted", "values": [r["accepted"] for r in rows]}], subtitle=subtitle)
    if metric in ("offers_by_company", "companies_overview"):
        rows, sub = _companies(db)
        if metric == "offers_by_company":
            series = [{"name": "Offers", "values": [r["offers"] for r in rows]}, {"name": "Accepted", "values": [r["accepted"] for r in rows]}]
        else:
            series = [{"name": k.title(), "values": [r[k] for r in rows]} for k in ("jobs", "applications", "offers")]
        return _finish(title, default, allowed, chart_type, [r["name"] for r in rows], series, subtitle=sub)
    if metric == "applications_by_stage":
        rows = [r for r in report["statusDist"] if r["count"]]
        return _finish(title, default, allowed, chart_type, [r["label"] for r in rows], [{"name": "Applications", "values": [r["count"] for r in rows]}], subtitle=subtitle)
    if metric == "placement_funnel":
        rows = report["funnel"]
        return _finish(title, default, allowed, chart_type, [r["stage"] for r in rows], [{"name": "Count", "values": [r["value"] for r in rows]}], subtitle=subtitle)
    rows = report["monthly"]
    return _finish(title, default, allowed, chart_type, [r["month"] for r in rows],
                   [{"name": "Applications", "values": [r["applications"] for r in rows]}, {"name": "Offers", "values": [r["offers"] for r in rows]}], subtitle=subtitle)


def student_chart(db: Session, user: User, metric: str, chart_type=None):
    default, allowed, title = STUDENT_METRICS[metric]
    s = student_of(db, user)
    if metric == "my_applications_by_status":
        c = Counter(a.status for a in db.scalars(select(Application).where(Application.student_id == s.id)).unique())
        labels = [k for k in STATUS_LABEL if c[k]]
        return _finish(title, default, allowed, chart_type, [STATUS_LABEL[k] for k in labels], [{"name": "Applications", "values": [c[k] for k in labels]}])
    jobs = db.scalars(select(Job).where(Job.status == JobStatus.PUBLISHED, Job.archived_at.is_(None)).limit(100)).unique().all()
    names = {EligibilityState.ELIGIBLE: "Eligible", EligibilityState.NOT_ELIGIBLE: "Not eligible",
             EligibilityState.PROFILE_INCOMPLETE: "Profile incomplete", EligibilityState.NEEDS_VERIFICATION: "Needs CGPA verification"}
    c = Counter(evaluate(db, s, j)["state"] for j in jobs)
    keys = [k for k in names if c[k]]
    return _finish(title, default, allowed, chart_type, [names[k] for k in keys], [{"name": "Jobs", "values": [c[k] for k in keys]}],
                   subtitle="Computed by the college eligibility rules.")


