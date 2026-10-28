"""Fictional demo data for local development. Every name, company record and number here is made up.

Accounts (all share SEED_DEMO_PASSWORD):
  admin@campus.demo        administrator
  faculty@campus.demo      placement officer
  student@campus.demo      onboarded student with applications, an offer and an interview
  newstudent@campus.demo   student who still has to complete onboarding
"""
import random
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import utcnow
from .enums import (
    ApplicationStatus, InterviewStatus, JobStatus, JobType, NotificationKind, OfferStatus, ReminderKind, RoleName,
    RoundMode, SkillKind, UserStatus,
)
from .models import (
    AcademicRecord, Application, ApplicationStatusHistory, Company, Department, DriveEvent, EligibilitySnapshot,
    FacultyProfile, HiringDrive, Interview, Job, JobEligibilityRule, Notification, Offer, Reminder, Role, Student, User,
)
from .security import hash_password, unusable_password
from .services.eligibility import evaluate
from .services.profile import compute_completion, set_placement_status, set_tags

COMPANIES = [
    # name, tier, industry, website, colour
    ("TCS", "regular", "IT Services", "https://www.tcs.com", "#1d4ed8"),
    ("Zoho", "dream", "Software Products", "https://www.zoho.com", "#dc2626"),
    ("Infosys", "regular", "IT Services", "https://www.infosys.com", "#0369a1"),
    ("Wipro", "regular", "IT Services", "https://www.wipro.com", "#7c3aed"),
    ("Accenture", "regular", "Consulting", "https://www.accenture.com", "#a21caf"),
    ("Bosch", "dream", "Engineering & Automotive", "https://www.bosch.com", "#b91c1c"),
    ("L&T", "regular", "Construction & Engineering", "https://www.larsentoubro.com", "#ca8a04"),
    ("Freshworks", "super_dream", "SaaS", "https://www.freshworks.com", "#059669"),
]

# company, title, ctc, min cgpa, departments (None = all), status, deadline offset (days), skills
JOBS = [
    ("TCS", "Ninja Developer", 3.6, 6.0, None, JobStatus.CLOSED, -20, ["Java", "SQL"]),
    ("TCS", "Digital Engineer", 7.0, 7.0, ["CSE", "IT", "AI&DS", "ECE"], JobStatus.PUBLISHED, 6, ["Python", "Data Structures"]),
    ("TCS", "Prime Engineer", 9.0, 8.0, ["CSE", "IT", "AI&DS"], JobStatus.PUBLISHED, 12, ["Java", "Algorithms"]),
    ("Zoho", "Software Developer", 8.4, 7.0, ["CSE", "IT", "AI&DS"], JobStatus.PUBLISHED, 4, ["Java", "C++"]),
    ("Infosys", "Systems Engineer", 3.6, 6.0, None, JobStatus.PUBLISHED, 9, ["Python"]),
    ("Infosys", "Specialist Programmer", 9.5, 7.5, ["CSE", "IT", "AI&DS"], JobStatus.PUBLISHED, 15, ["Data Structures"]),
    ("Wipro", "Turbo Hiring", 6.5, 7.0, ["CSE", "IT", "ECE", "EEE"], JobStatus.PUBLISHED, 3, ["Java"]),
    ("Accenture", "Associate Software Engineer", 4.5, 6.5, None, JobStatus.PUBLISHED, 20, ["SQL"]),
    ("Accenture", "Advanced App Engineering Analyst", 6.5, 7.0, None, JobStatus.DRAFT, 30, ["Cloud"]),
    ("Bosch", "Embedded Software Engineer", 7.5, 7.0, ["ECE", "EEE", "CSE"], JobStatus.PUBLISHED, 10, ["C", "Embedded C"]),
    ("L&T", "Graduate Engineer Trainee", 5.0, 6.5, ["MECH", "CIVIL", "EEE"], JobStatus.PUBLISHED, 8, ["AutoCAD"]),
    ("Freshworks", "Software Development Engineer", 14.0, 8.0, ["CSE", "IT", "AI&DS"], JobStatus.PUBLISHED, 18, ["React", "Python"]),
]

FIRST = ["Diya", "Rohan", "Ananya", "Karthik", "Sneha", "Vikram", "Ishita", "Arjun", "Kavya", "Nikhil", "Pooja", "Siddharth"]
LAST = ["Sharma", "Iyer", "Reddy", "Pillai", "Das", "Kumar", "Joshi", "Rao", "Gupta", "Nair", "Menon", "Bose"]
SKILLS = ["Python", "Java", "SQL", "React", "C++", "Data Structures", "Machine Learning", "Embedded C", "AutoCAD", "Cloud"]


def _role(db, name):
    return db.scalar(select(Role).where(Role.name == name))


def _dept(db, code):
    return db.scalar(select(Department).where(Department.code == code))


def _user(db, code, name, email, role, dept, password, status=UserStatus.ACTIVE, onboarded=True):
    u = User(user_code=code, name=name, email=email, role=_role(db, role), department_id=dept.id if dept else None,
             status=status, onboarding_complete=onboarded,
             password_hash=hash_password(password) if status == UserStatus.ACTIVE else unusable_password())
    db.add(u)
    db.flush()
    return u


def _student(db, user, code, dept, cgpa, verified, skills, interests=(), roles=(), phone=None, onboarded=True):
    s = Student(user_id=user.id, student_code=code if onboarded else None, department_id=dept.id,
                degree="B.E." if onboarded else "", current_year=4, graduation_year=2027, phone=phone,
                portfolio_url=f"https://github.com/{code.lower()}" if onboarded and phone else None,
                resume_file=f"{code}_resume.pdf" if onboarded and phone else None)
    s.academic = AcademicRecord(cgpa=Decimal(str(cgpa)) if cgpa else None, cgpa_verified=verified)
    db.add(s)
    db.flush()
    db.refresh(s)
    set_tags(s, SkillKind.SKILL, list(skills))
    set_tags(s, SkillKind.INTEREST, list(interests))
    set_tags(s, SkillKind.PREFERRED_ROLE, list(roles))
    db.flush()
    s.profile_completion = compute_completion(s)
    return s


def _apply(db, student, job, status, when, actor_name="Placement Cell"):
    app = Application(student_id=student.id, job_id=job.id, status=ApplicationStatus.APPLIED, applied_at=when, updated_at=when)
    result = evaluate(db, student, job, ignore_open=True)
    app.snapshot = EligibilitySnapshot(state=result["state"], summary=result["summary"], checks=result["checks"], evaluated_at=when)
    app.history.append(ApplicationStatusHistory(status=ApplicationStatus.APPLIED, at=when, note="Application submitted",
                                                changed_by=student.user_id, changed_by_name=student.user.name))
    path = [ApplicationStatus.SHORTLISTED, ApplicationStatus.INTERVIEW, ApplicationStatus.SELECTED, ApplicationStatus.OFFER_RECEIVED]
    t = when
    if status == ApplicationStatus.REJECTED:
        t += timedelta(days=2)
        app.history.append(ApplicationStatusHistory(status=status, at=t, note="Not taken forward", changed_by_name=actor_name))
    else:
        steps = path[: path.index(status) + 1] if status in path else []
        for step in steps:
            t += timedelta(days=2)
            app.history.append(ApplicationStatusHistory(status=step, at=t, note=f"Moved to {step.replace('_', ' ')}",
                                                        changed_by_name=actor_name))
    app.status = status
    app.updated_at = t
    db.add(app)
    db.flush()
    return app


def seed_demo(db: Session, password: str) -> bool:
    """Returns False when demo data already exists."""
    if db.scalar(select(User).where(User.email == "admin@campus.demo")):
        return False
    rnd = random.Random(42)
    now = utcnow()
    cse, it, ece, eee = _dept(db, "CSE"), _dept(db, "IT"), _dept(db, "ECE"), _dept(db, "EEE")

    # ---- staff
    _user(db, "ADM001", "Rahul Verma", "admin@campus.demo", RoleName.ADMIN, None, password)
    fac = _user(db, "FAC101", "Dr. Priya Raman", "faculty@campus.demo", RoleName.FACULTY, cse, password)
    db.add(FacultyProfile(user_id=fac.id, department_id=cse.id, designation="Placement Officer"))
    f2 = _user(db, "FAC102", "Prof. Manoj Bhat", "manoj.bhat@campus.demo", RoleName.FACULTY, ece, password)
    db.add(FacultyProfile(user_id=f2.id, department_id=ece.id, designation="Faculty Coordinator"))
    f3 = _user(db, "FAC105", "Dr. Latha Menon", "latha.menon@campus.demo", RoleName.FACULTY, eee, password,
               status=UserStatus.INVITED)
    db.add(FacultyProfile(user_id=f3.id, department_id=eee.id, designation="Faculty Coordinator"))

    # ---- companies and jobs
    companies = {}
    for name, tier, industry, site, color in COMPANIES:
        c = Company(name=name, tier=tier, industry=industry, website=site, brand_color=color,
                    description=f"{name} is a fictional demo recruiter in {industry}.",
                    contact_name=f"{name} Campus Team", contact_email=f"campus@{name.lower().replace('&', '')}.example")
        db.add(c)
        companies[name] = c
    db.flush()

    jobs = []
    for cname, title, ctc, min_cgpa, depts, status, offset, skills in JOBS:
        c = companies[cname]
        deadline = (now + timedelta(days=offset)).replace(hour=18, minute=0, second=0, microsecond=0)
        drive_date = deadline + timedelta(days=5)
        drive = HiringDrive(company_id=c.id, name=f"{title} — campus drive", drive_date=drive_date, created_by=fac.id)
        for i, (rname, mode) in enumerate([("Online Assessment", RoundMode.ONLINE), ("Technical Interview", RoundMode.ON_CAMPUS),
                                           ("HR Interview", RoundMode.ON_CAMPUS)], start=1):
            drive.events.append(DriveEvent(sequence=i, name=rname, mode=mode,
                                           scheduled_at=drive_date + timedelta(hours=2 * (i - 1)), location="Main Block"))
        job = Job(company_id=c.id, drive=drive, title=title, domain="Software" if cname not in ("L&T", "Bosch") else "Core",
                  location="Chennai", job_type=JobType.FULL_TIME,
                  description=f"Join {cname} as a {title}. This is a fictional role for the demo.",
                  responsibilities=["Build and test software", "Work with the team on delivery", "Learn the company stack"],
                  skills=skills, ctc_lpa=Decimal(str(ctc)), open_date=now - timedelta(days=25), deadline=deadline,
                  status=status, published_at=now - timedelta(days=24) if status != JobStatus.DRAFT else None,
                  created_by=fac.id)
        job.rule = JobEligibilityRule(min_cgpa=Decimal(str(min_cgpa)), max_active_arrears=0, graduation_years=[2027],
                                      required_skills=[])
        job.departments = [_dept(db, d) for d in depts] if depts else []
        db.add(job)
        jobs.append(job)
    db.flush()
    by_title = {j.title: j for j in jobs}

    # ---- the main demo student
    su = _user(db, "23CSE101", "Aarav Menon", "student@campus.demo", RoleName.STUDENT, cse, password)
    aarav = _student(db, su, "23CSE101", cse, 8.42, True,
                     ["React", "TypeScript", "Python", "SQL", "Data Structures", "Java"],
                     ["Web development", "Cloud"], ["Software Engineer", "Full-stack Developer"], phone="+91 98400 12345")
    nu = _user(db, "NEW002", "Meera Nair", "newstudent@campus.demo", RoleName.STUDENT, it, password, onboarded=False)
    _student(db, nu, "NEW002", it, None, False, [], onboarded=False)

    ninja = _apply(db, aarav, by_title["Ninja Developer"], ApplicationStatus.OFFER_RECEIVED, now - timedelta(days=24))
    _apply(db, aarav, by_title["Digital Engineer"], ApplicationStatus.INTERVIEW, now - timedelta(days=10))
    _apply(db, aarav, by_title["Software Developer"], ApplicationStatus.SHORTLISTED, now - timedelta(days=6))
    _apply(db, aarav, by_title["Systems Engineer"], ApplicationStatus.APPLIED, now - timedelta(days=2))
    db.add(Offer(application_id=ninja.id, student_id=aarav.id, job_id=ninja.job_id, company_id=companies["TCS"].id,
                 ctc_lpa=Decimal("3.6"), offered_at=now - timedelta(days=3), accept_by=now + timedelta(days=7),
                 status=OfferStatus.RECEIVED,
                 policy_checks=[{"label": "Accepted-offer limit", "passed": True, "detail": "0 accepted; the limit is 2"}]))
    digital = db.scalar(select(Application).where(Application.student_id == aarav.id,
                                                  Application.job_id == by_title["Digital Engineer"].id))
    iv = Interview(job_id=digital.job_id, round_name="Technical Interview", scheduled_at=(now + timedelta(days=2)).replace(
        hour=10, minute=0, second=0, microsecond=0), duration_mins=45, location="Seminar Hall 2", notified=True)
    iv.candidates.append(digital)
    db.add(iv)
    db.add_all([
        Notification(user_id=su.id, title="Offer received — TCS", body="Respond to your Ninja Developer offer within 7 days.",
                     kind=NotificationKind.OFFER, link="/student/offers", created_at=now - timedelta(days=3)),
        Notification(user_id=su.id, title="Interview scheduled — TCS", body="Technical Interview in 2 days at Seminar Hall 2.",
                     kind=NotificationKind.INTERVIEW, link="/student/applications", created_at=now - timedelta(days=1)),
        Notification(user_id=su.id, title="Zoho deadline approaching", body="Zoho Software Developer closes in 4 days.",
                     kind=NotificationKind.DEADLINE, link="/student/jobs", created_at=now - timedelta(hours=5)),
        Reminder(student_id=aarav.id, title="Revise DBMS before the TCS interview", remind_at=now + timedelta(days=1),
                 job_id=digital.job_id, kind=ReminderKind.INTERVIEW),
        Notification(user_id=nu.id, title="Welcome to Campus Assistant", body="Complete your profile to see eligible jobs.",
                     kind=NotificationKind.SYSTEM, link="/student/onboarding"),
        Notification(user_id=fac.id, title="New applications", body="Several students applied to open drives this week.",
                     kind=NotificationKind.APPLICATION, link="/faculty/applications"),
    ])

    # ---- 12 more students with random records
    depts = [cse, it, _dept(db, "AI&DS"), ece, eee, _dept(db, "MECH")]
    others = []
    for i in range(12):
        dept = depts[i % len(depts)]
        name = f"{FIRST[i]} {LAST[i]}"
        code = f"23{dept.code.replace('&', '')[:4]}{110 + i}"
        u = _user(db, code, name, f"{FIRST[i].lower()}.{i}@campus.demo", RoleName.STUDENT, dept, password)
        cgpa = round(rnd.uniform(6.2, 9.4), 2)
        s = _student(db, u, code, dept, cgpa, rnd.random() < 0.85, rnd.sample(SKILLS, 4), ["Technology"], ["Engineer"],
                     phone=f"+91 9{rnd.randint(100000000, 999999999)}")
        others.append(s)

    published = [j for j in jobs if j.status == JobStatus.PUBLISHED]
    for s in others[:6]:
        for job in rnd.sample(published, 2):
            if evaluate(db, s, job, ignore_open=True)["state"] == "not_eligible":
                continue
            _apply(db, s, job, rnd.choice([ApplicationStatus.APPLIED, ApplicationStatus.SHORTLISTED,
                                           ApplicationStatus.INTERVIEW, ApplicationStatus.REJECTED]),
                   now - timedelta(days=rnd.randint(2, 15)))

    # historical accepted offers from the closed TCS Ninja drive
    for s in others[6:10]:
        app = _apply(db, s, by_title["Ninja Developer"], ApplicationStatus.OFFER_RECEIVED, now - timedelta(days=40))
        db.add(Offer(application_id=app.id, student_id=s.id, job_id=app.job_id, company_id=companies["TCS"].id,
                     ctc_lpa=Decimal("3.6"), offered_at=now - timedelta(days=30), accept_by=now - timedelta(days=16),
                     status=OfferStatus.ACCEPTED, policy_checks=[]))

    db.flush()
    for s in [aarav, *others]:
        set_placement_status(db, s)
    db.commit()
    return True
