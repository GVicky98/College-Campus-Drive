"""Turn database rows into the JSON shapes the Vue app uses.

Conventions: camelCase keys, IDs as strings, datetimes as ISO-8601 UTC strings ending in "Z",
keys whose value is None are left out.
"""
from datetime import datetime
from decimal import Decimal

from .enums import RoleName, SkillKind
from .models import (
    Application, Company, Document, Interview, Job, Notification, Offer, PlacementPolicy, Reminder, Student, User,
)


def sid(value) -> str | None:
    return None if value is None else str(value)


def iso(value: datetime | None) -> str | None:
    return None if value is None else value.replace(microsecond=0).isoformat() + "Z"


def num(value) -> float | None:
    if value is None:
        return None
    return float(value) if isinstance(value, Decimal) else value


def clean(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def mask_phone(phone: str | None) -> str | None:
    if not phone:
        return phone
    digits = [i for i, c in enumerate(phone) if c.isdigit()]
    keep = set(digits[-2:])
    return "".join("•" if c.isdigit() and i not in keep else c for i, c in enumerate(phone))


# ---------------------------------------------------------------- people
def user_dict(u: User) -> dict:
    return clean({
        "id": sid(u.id),
        "userCode": u.user_code,
        "name": u.name,
        "email": u.email,
        "role": u.role_name,
        "departmentId": sid(u.department_id),
        "status": u.status,
        "createdAt": iso(u.created_at),
        "lastLoginAt": iso(u.last_login_at),
        "onboardingComplete": u.onboarding_complete if u.role_name == RoleName.STUDENT else None,
    })


def student_dict(s: Student, *, mask: bool = False) -> dict:
    a = s.academic
    return clean({
        "id": sid(s.id),
        "userId": sid(s.user_id),
        "studentCode": s.student_code or "",
        "name": s.user.name,
        "email": s.user.email,
        "phone": mask_phone(s.phone) if mask else s.phone,
        "departmentId": sid(s.department_id),
        "departmentCode": s.department.code if s.department else None,
        "degree": s.degree,
        "currentYear": s.current_year,
        "graduationYear": s.graduation_year,
        "academic": clean({
            "cgpa": num(a.cgpa) if a else None,
            "cgpaVerified": bool(a and a.cgpa_verified),
            "activeArrears": a.active_arrears if a else 0,
            "arrearHistory": a.arrear_history if a else 0,
        }),
        "skills": s.tags(SkillKind.SKILL),
        "interests": s.tags(SkillKind.INTEREST),
        "preferredRoles": s.tags(SkillKind.PREFERRED_ROLE),
        "resumeFile": s.resume_file,
        "portfolioUrl": s.portfolio_url,
        "profileCompletion": s.profile_completion,
        "placementStatus": s.placement_status,
    })


# ---------------------------------------------------------------- companies & jobs
def company_dict(c: Company) -> dict:
    return clean({
        "id": sid(c.id),
        "name": c.name,
        "website": c.website,
        "industry": c.industry,
        "description": c.description,
        "contactName": c.contact_name,
        "contactEmail": c.contact_email,
        "contactPhone": c.contact_phone,
        "tier": c.tier,
        "color": c.brand_color,
        "createdAt": iso(c.created_at),
        "archivedAt": iso(c.archived_at),
    })


def job_dict(j: Job) -> dict:
    r = j.rule
    drive = j.drive
    return clean({
        "id": sid(j.id),
        "companyId": sid(j.company_id),
        "title": j.title,
        "domain": j.domain,
        "location": j.location,
        "type": j.job_type,
        "description": j.description,
        "responsibilities": list(j.responsibilities or []),
        "skills": list(j.skills or []),
        "eligibility": clean({
            "minCgpa": num(r.min_cgpa) if r else 0,
            "maxActiveArrears": r.max_active_arrears if r else 0,
            "maxArrearHistory": r.max_arrear_history if r else None,
            "departmentIds": [sid(d.id) for d in j.departments],
            "graduationYears": list(r.graduation_years or []) if r else [],
            "requiredSkills": list(r.required_skills or []) if r else [],
        }),
        "rounds": [
            clean({"id": sid(e.id), "name": e.name, "mode": e.mode, "date": iso(e.scheduled_at), "location": e.location})
            for e in (drive.events if drive else [])
        ],
        "ctcLpa": num(j.ctc_lpa),
        "stipendPerMonth": j.stipend_per_month,
        "openDate": iso(j.open_date),
        "deadline": iso(j.deadline),
        "driveDate": iso(drive.drive_date) if drive else None,
        "status": j.status,
        "publishedAt": iso(j.published_at),
        "archivedAt": iso(j.archived_at),
        "createdBy": sid(j.created_by),
        "updatedAt": iso(j.updated_at),
    })


def job_view(j: Job, **extra) -> dict:
    """A job with its company and the department codes it is open to (+ optional extras)."""
    view = {
        "job": job_dict(j),
        "company": company_dict(j.company),
        "eligibleDepartments": [d.code for d in j.departments],
    }
    view.update({k: v for k, v in extra.items() if v is not None})
    return view


# ---------------------------------------------------------------- applications, interviews, offers
def snapshot_dict(app: Application) -> dict | None:
    s = app.snapshot
    if not s:
        return None
    return clean({
        "state": s.state,
        "summary": s.summary,
        "checks": s.checks or [],
        "evaluatedAt": iso(s.evaluated_at),
        "exceptionGranted": {"reason": s.exception_reason, "approvedBy": s.exception_approved_by or ""}
        if s.exception_reason else None,
    })


def application_dict(a: Application) -> dict:
    return clean({
        "id": sid(a.id),
        "studentId": sid(a.student_id),
        "jobId": sid(a.job_id),
        "status": a.status,
        "appliedAt": iso(a.applied_at),
        "updatedAt": iso(a.updated_at),
        "history": [
            clean({"status": h.status, "at": iso(h.at), "note": h.note, "by": h.changed_by_name or "System"})
            for h in a.history
        ],
        "eligibilitySnapshot": snapshot_dict(a),
        "currentRound": a.current_round,
    })


def interview_dict(i: Interview) -> dict:
    return {
        "id": sid(i.id),
        "jobId": sid(i.job_id),
        "applicationIds": [sid(a.id) for a in i.candidates],
        "round": i.round_name,
        "at": iso(i.scheduled_at),
        "durationMins": i.duration_mins,
        "location": i.location,
        "status": i.status,
        "notified": i.notified,
    }


def offer_dict(o: Offer) -> dict:
    return {
        "id": sid(o.id),
        "studentId": sid(o.student_id),
        "jobId": sid(o.job_id),
        "applicationId": sid(o.application_id),
        "companyId": sid(o.company_id),
        "ctcLpa": num(o.ctc_lpa),
        "offeredAt": iso(o.offered_at),
        "acceptBy": iso(o.accept_by),
        "status": o.status,
        "policyChecks": o.policy_checks or [],
    }


def student_brief(s: Student, *, mask: bool = True) -> dict:
    return student_dict(s, mask=mask)


def offer_view(o: Offer, *, with_student: bool = False, mask: bool = True) -> dict:
    view = {"offer": offer_dict(o), "job": job_dict(o.job), "company": company_dict(o.company)}
    if with_student:
        view["student"] = student_brief(o.student, mask=mask)
    return view


# ---------------------------------------------------------------- content
def notification_dict(n: Notification) -> dict:
    return clean({
        "id": sid(n.id), "userId": sid(n.user_id), "title": n.title, "body": n.body, "kind": n.kind,
        "at": iso(n.created_at), "read": n.is_read, "link": n.link,
    })


def reminder_dict(r: Reminder) -> dict:
    return clean({
        "id": sid(r.id), "studentId": sid(r.student_id), "title": r.title, "at": iso(r.remind_at),
        "jobId": sid(r.job_id), "kind": r.kind, "done": r.done,
    })


def policy_dict(p: PlacementPolicy) -> dict:
    return clean({
        "id": sid(p.id), "name": p.name, "description": p.description, "kind": p.kind, "scope": p.scope,
        "scopeValue": p.scope_value, "params": p.params or {}, "enabled": p.enabled,
        "updatedAt": iso(p.updated_at), "updatedBy": p.updated_by,
    })


def document_dict(d: Document, *, with_excerpts: bool = False) -> dict:
    out = clean({
        "id": sid(d.id),
        "title": d.title,
        "type": d.doc_type,
        "fileName": d.file_name,
        "uploadedAt": iso(d.created_at),
        "updatedAt": iso(d.updated_at),
        "uploadedBy": d.uploader.name if d.uploader else "System",
        "ownerStudentId": sid(d.owner_student_id),
        "companyId": sid(d.company_id),
        "companyName": d.company.name if d.company else None,
        "jobId": sid(d.job_id),
        "jobTitle": d.job.title if d.job else None,
        "access": list(d.access_roles or []),
        "sizeKb": d.size_kb,
        "processing": d.processing,
        "pages": d.pages,
        "version": d.version,
    })
    if with_excerpts:
        seen, excerpts = set(), []
        for c in d.chunks:
            if c.page not in seen:
                seen.add(c.page)
                excerpts.append({"page": c.page, "text": c.text[:600]})
        out["extractedExcerpts"] = excerpts[:20]
    return out
