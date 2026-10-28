"""Management commands.

    python -m app.cli seed-reference
    python -m app.cli seed-demo
    python -m app.cli create-user --role admin --email you@college.edu --name "Your Name" --code ADM001
    python -m app.cli assistant-purge
    python -m app.cli assistant-check [--ping]
"""
import argparse
import getpass
import sys

from sqlalchemy import func, select

from .config import get_settings
from .database import SessionLocal


def seed_reference(_args):
    from .seed import seed_reference as run
    with SessionLocal() as db:
        run(db)
    print("Reference data is in place.")


def seed_demo(_args):
    from .seed import seed_reference as ref
    from .security import check_password_policy
    from .seed_demo import seed_demo as run

    s = get_settings()
    if s.is_production:
        sys.exit("seed-demo is refused in production.")
    if not s.seed_demo_password:
        sys.exit("Set SEED_DEMO_PASSWORD in backend/.env first.")
    check_password_policy(s.seed_demo_password)
    with SessionLocal() as db:
        ref(db)
        print("Demo data created." if run(db, s.seed_demo_password) else "Demo data already exists; nothing changed.")


def create_user(args):
    from .enums import RoleName, UserStatus
    from .errors import ValidationFailed
    from .models import Department, FacultyProfile, Role, User
    from .security import check_password_policy, hash_password

    if args.role == RoleName.STUDENT:
        sys.exit("Create students from the admin screens (they need academic details).")
    with SessionLocal() as db:
        if db.scalar(select(User).where(func.lower(User.email) == args.email.lower())):
            sys.exit("A user with that e-mail already exists.")
        dept = None
        if args.department:
            dept = db.scalar(select(Department).where(Department.code == args.department.upper()))
            if not dept:
                sys.exit(f"Unknown department {args.department}.")
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Repeat password: "):
            sys.exit("Passwords do not match.")
        try:
            check_password_policy(password, args.email, args.code)
        except ValidationFailed as e:
            sys.exit(e.message)
        role = db.scalar(select(Role).where(Role.name == args.role))
        if not role:
            sys.exit("Run seed-reference first.")
        user = User(user_code=args.code, name=args.name, email=args.email.lower(), role=role,
                    department_id=dept.id if dept else None, status=UserStatus.ACTIVE, onboarding_complete=True,
                    password_hash=hash_password(password))
        db.add(user)
        db.flush()
        if args.role == RoleName.FACULTY:
            db.add(FacultyProfile(user_id=user.id, department_id=user.department_id))
        db.commit()
        print(f"Created {args.role} {args.email}.")


def assistant_purge(_args):
    from .services.assistant.conversations import purge_archived
    with SessionLocal() as db:
        print(f"Purged {purge_archived(db, get_settings().assistant_retention_days)} conversation(s).")


def assistant_check(args):
    from .services.assistant.checks import run_check
    run_check(ping=args.ping)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed-reference").set_defaults(func=seed_reference)
    sub.add_parser("seed-demo").set_defaults(func=seed_demo)
    cu = sub.add_parser("create-user")
    cu.add_argument("--role", required=True, choices=["admin", "faculty"])
    cu.add_argument("--email", required=True)
    cu.add_argument("--name", required=True)
    cu.add_argument("--code", required=True)
    cu.add_argument("--department")
    cu.set_defaults(func=create_user)
    sub.add_parser("assistant-purge").set_defaults(func=assistant_purge)
    ac = sub.add_parser("assistant-check")
    ac.add_argument("--ping", action="store_true")
    ac.set_defaults(func=assistant_check)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
