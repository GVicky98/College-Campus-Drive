from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base, utcnow
from ..enums import PlacementStatus, SkillKind


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    head_name: Mapped[str | None] = mapped_column(String(120))


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    degree: Mapped[str] = mapped_column(String(16))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    duration_years: Mapped[int] = mapped_column(SmallInteger, default=4)


class AcademicYear(Base):
    __tablename__ = "academic_years"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(16), unique=True)  # e.g. "2026-27"
    graduation_year: Mapped[int] = mapped_column(SmallInteger, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False)


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    student_code: Mapped[str | None] = mapped_column(String(32), unique=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    degree: Mapped[str] = mapped_column(String(16), default="")
    current_year: Mapped[int] = mapped_column(SmallInteger, default=4)
    graduation_year: Mapped[int] = mapped_column(SmallInteger)
    resume_file: Mapped[str | None] = mapped_column(String(255))
    portfolio_url: Mapped[str | None] = mapped_column(String(300))
    placement_status: Mapped[str] = mapped_column(String(32), default=PlacementStatus.UNPLACED)
    profile_completion: Mapped[int] = mapped_column(SmallInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="student", lazy="joined")  # noqa: F821
    department: Mapped[Department] = relationship(lazy="joined")
    academic: Mapped["AcademicRecord | None"] = relationship(
        back_populates="student", uselist=False, cascade="all, delete-orphan", lazy="joined"
    )
    skills: Mapped[list["StudentSkill"]] = relationship(cascade="all, delete-orphan", lazy="selectin")

    def tags(self, kind: SkillKind) -> list[str]:
        return [s.name for s in self.skills if s.kind == kind]


class AcademicRecord(Base):
    __tablename__ = "academic_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), unique=True)
    cgpa: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    cgpa_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    active_arrears: Mapped[int] = mapped_column(SmallInteger, default=0)
    arrear_history: Mapped[int] = mapped_column(SmallInteger, default=0)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    student: Mapped[Student] = relationship(back_populates="academic")


class StudentSkill(Base):
    __tablename__ = "student_skills"
    __table_args__ = (UniqueConstraint("student_id", "kind", "name", name="uq_student_skills_student_kind_name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(80))
