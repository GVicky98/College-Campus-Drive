"""Reference data every installation needs: permissions, roles, departments, years, default policies.

Idempotent: running it again only adds what is missing and never overwrites an administrator's edits.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .enums import Degree, PolicyKind, RoleName
from .models import AcademicYear, Course, Department, Permission, PlacementPolicy, Role

PERMISSIONS = [
    # key, module, label, description
    ("students.view", "Students", "View students", "View student records, profiles and academic details"),
    ("students.edit", "Students", "Edit student academics", "Verify CGPA and correct academic details"),
    ("companies.manage", "Placements", "Manage companies", "Add, edit and archive recruiting companies"),
    ("jobs.create", "Placements", "Create jobs", "Create and edit jobs and their eligibility rules"),
    ("drives.publish", "Placements", "Publish drives", "Publish, close, reopen, cancel and archive jobs"),
    ("applications.review", "Placements", "Review applications", "Shortlist applicants, change stages, grant exceptions, schedule interviews"),
    ("offers.manage", "Placements", "Manage offers", "Issue offers and update their status"),
    ("documents.upload", "Documents", "Upload documents", "Upload circulars, brochures and eligibility documents"),
    ("reports.view", "Reports", "View reports", "Placement analytics and CSV exports"),
    ("users.manage", "Administration", "Manage users", "Create, edit, import and deactivate accounts"),
    ("roles.manage", "Administration", "Manage roles", "Edit the role-permission matrix"),
    ("policies.manage", "Administration", "Manage policies", "Configure placement policies"),
    ("audit.view", "Administration", "View audit log", "Read the audit trail"),
]

FACULTY_DEFAULT = [
    "students.view", "students.edit", "companies.manage", "jobs.create", "drives.publish",
    "applications.review", "offers.manage", "documents.upload", "reports.view",
]

ROLES = {
    RoleName.ADMIN: ("System administrator", [p[0] for p in PERMISSIONS]),
    RoleName.FACULTY: ("Faculty / placement officer", FACULTY_DEFAULT),
    RoleName.STUDENT: ("Student (own records only)", []),
}

DEPARTMENTS = [
    ("CSE", "Computer Science & Engineering", "Dr. Lakshmi Narayanan"),
    ("IT", "Information Technology", "Dr. S. Karthikeyan"),
    ("AI&DS", "Artificial Intelligence & Data Science", "Dr. Anita Joseph"),
    ("ECE", "Electronics & Communication", "Dr. Mohan Raj"),
    ("EEE", "Electrical & Electronics", "Dr. R. Sundaram"),
    ("MECH", "Mechanical Engineering", "Dr. Vikram Iyer"),
    ("CIVIL", "Civil Engineering", "Dr. Farah Khan"),
]

YEARS = [("2025-26", 2026, False), ("2026-27", 2027, True), ("2027-28", 2028, False)]

POLICIES = [
    ("Maximum accepted offers", "A student may accept at most this many offers.", PolicyKind.MAX_OFFERS,
     {"maxAcceptedOffers": 2}),
    ("Dream / Super Dream tier rule", "After accepting an offer, a student may only take part in higher-tier drives.",
     PolicyKind.TIER_RESTRICTION, {"allowOnlyHigherTier": True}),
    ("Concurrent application limit", "Maximum number of active applications at one time.",
     PolicyKind.APPLICATION_LIMIT, {"maxActiveApplications": 8}),
    ("Offer acceptance window", "Default number of days a student has to respond to an offer.",
     PolicyKind.ACCEPTED_OFFER, {"acceptanceWindowDays": 14}),
    ("Eligibility exception approval", "Advancing a non-eligible applicant needs a reason and an approver.",
     PolicyKind.EXCEPTION_APPROVAL, {"requireReason": True, "requireApprover": True}),
]


def seed_reference(db: Session) -> None:
    perms = {p.key: p for p in db.scalars(select(Permission))}
    for key, module, label, desc in PERMISSIONS:
        if key not in perms:
            perms[key] = Permission(key=key, module=module, label=label, description=desc)
            db.add(perms[key])
    db.flush()

    for name, (desc, keys) in ROLES.items():
        role = db.scalar(select(Role).where(Role.name == name))
        if not role:  # default grants only when the role is first created
            db.add(Role(name=name, description=desc, permissions=[perms[k] for k in keys]))

    depts = {d.code: d for d in db.scalars(select(Department))}
    for code, name, head in DEPARTMENTS:
        if code not in depts:
            depts[code] = Department(code=code, name=name, head_name=head)
            db.add(depts[code])
    db.flush()

    courses = {c.code for c in db.scalars(select(Course.code))}
    for code, dept in depts.items():
        ccode = f"{code.replace('&', '')}-UG"
        if ccode not in courses:
            db.add(Course(code=ccode, name=f"B.E. {dept.name}", degree=Degree.BE, department_id=dept.id, duration_years=4))

    if not db.scalar(select(AcademicYear.id).limit(1)):
        for label, grad, active in YEARS:
            db.add(AcademicYear(label=label, graduation_year=grad, active=active))

    if not db.scalar(select(PlacementPolicy.id).limit(1)):
        for name, desc, kind, params in POLICIES:
            db.add(PlacementPolicy(name=name, description=desc, kind=kind, params=params, updated_by="system"))
    db.commit()
