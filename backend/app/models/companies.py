from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base, utcnow
from ..enums import CompanyTier, JobStatus, JobType, RoundMode
from .academic import Department


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    website: Mapped[str] = mapped_column(String(300))
    industry: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    contact_name: Mapped[str] = mapped_column(String(120), default="")
    contact_email: Mapped[str] = mapped_column(String(190), default="")
    contact_phone: Mapped[str | None] = mapped_column(String(40))
    tier: Mapped[str] = mapped_column(String(32), default=CompanyTier.REGULAR)
    brand_color: Mapped[str] = mapped_column(String(9), default="#2563eb")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class HiringDrive(Base):
    __tablename__ = "hiring_drives"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    drive_date: Mapped[datetime | None] = mapped_column(DateTime)
    venue: Mapped[str | None] = mapped_column(String(200))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    events: Mapped[list["DriveEvent"]] = relationship(
        cascade="all, delete-orphan", order_by="DriveEvent.sequence", lazy="selectin"
    )


class DriveEvent(Base):
    """One hiring round of a drive (Online assessment, Technical interview, ...)."""
    __tablename__ = "drive_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    drive_id: Mapped[int] = mapped_column(ForeignKey("hiring_drives.id", ondelete="CASCADE"))
    sequence: Mapped[int] = mapped_column(SmallInteger)
    name: Mapped[str] = mapped_column(String(120))
    mode: Mapped[str] = mapped_column(String(32), default=RoundMode.ONLINE)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime)
    location: Mapped[str | None] = mapped_column(String(200))


job_departments = Table(
    "job_departments",
    Base.metadata,
    Column("job_id", ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True),
    Column("department_id", ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True),
)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_status_deadline", "status", "deadline"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    drive_id: Mapped[int | None] = mapped_column(ForeignKey("hiring_drives.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    domain: Mapped[str] = mapped_column(String(80), default="Software")
    location: Mapped[str] = mapped_column(String(160), default="")
    job_type: Mapped[str] = mapped_column(String(32), default=JobType.FULL_TIME)
    description: Mapped[str] = mapped_column(Text, default="")
    responsibilities: Mapped[list] = mapped_column(JSON, default=list)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    ctc_lpa: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    stipend_per_month: Mapped[int | None] = mapped_column(Integer)
    open_date: Mapped[datetime] = mapped_column(DateTime)
    deadline: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.DRAFT)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    company: Mapped[Company] = relationship(lazy="joined")
    drive: Mapped[HiringDrive | None] = relationship(lazy="joined")
    rule: Mapped["JobEligibilityRule | None"] = relationship(
        back_populates="job", uselist=False, cascade="all, delete-orphan", lazy="joined"
    )
    departments: Mapped[list[Department]] = relationship(secondary=job_departments, lazy="selectin")


class JobEligibilityRule(Base):
    __tablename__ = "job_eligibility_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), unique=True)
    min_cgpa: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=0)
    max_active_arrears: Mapped[int] = mapped_column(SmallInteger, default=0)
    max_arrear_history: Mapped[int | None] = mapped_column(SmallInteger)
    graduation_years: Mapped[list] = mapped_column(JSON, default=list)
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    job: Mapped[Job] = relationship(back_populates="rule")


class SavedJob(Base):
    __tablename__ = "saved_jobs"
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
