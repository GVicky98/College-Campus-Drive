from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, Numeric, SmallInteger, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base, utcnow
from ..enums import ApplicationStatus, InterviewStatus, OfferStatus
from .academic import Student
from .companies import Company, Job


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (Index("ix_applications_student_status", "student_id", "status"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default=ApplicationStatus.APPLIED)
    current_round: Mapped[str | None] = mapped_column(String(120))
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    student: Mapped[Student] = relationship(lazy="joined")
    job: Mapped[Job] = relationship(lazy="joined")
    history: Mapped[list["ApplicationStatusHistory"]] = relationship(
        cascade="all, delete-orphan", order_by="ApplicationStatusHistory.at", lazy="selectin"
    )
    snapshot: Mapped["EligibilitySnapshot | None"] = relationship(
        cascade="all, delete-orphan", uselist=False, lazy="selectin"
    )
    offer: Mapped["Offer | None"] = relationship(back_populates="application", uselist=False, lazy="selectin")


class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    note: Mapped[str | None] = mapped_column(String(255))
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    changed_by_name: Mapped[str | None] = mapped_column(String(120))


class EligibilitySnapshot(Base):
    """The eligibility result frozen at the moment the student applied."""
    __tablename__ = "application_eligibility_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), unique=True)
    state: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(String(400), default="")
    checks: Mapped[list] = mapped_column(JSON, default=list)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    exception_reason: Mapped[str | None] = mapped_column(String(400))
    exception_approved_by: Mapped[str | None] = mapped_column(String(120))


interview_candidates = Table(
    "interview_candidates",
    Base.metadata,
    Column("interview_id", ForeignKey("interviews.id", ondelete="CASCADE"), primary_key=True),
    Column("application_id", ForeignKey("applications.id", ondelete="CASCADE"), primary_key=True),
)


class Interview(Base):
    __tablename__ = "interviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    round_name: Mapped[str] = mapped_column(String(120))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    duration_mins: Mapped[int] = mapped_column(SmallInteger, default=45)
    location: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(32), default=InterviewStatus.SCHEDULED)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)

    job: Mapped[Job] = relationship(lazy="joined")
    candidates: Mapped[list[Application]] = relationship(secondary=interview_candidates, lazy="selectin")


class Offer(Base):
    __tablename__ = "offers"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), unique=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    ctc_lpa: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    offered_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    accept_by: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(32), default=OfferStatus.RECEIVED)
    policy_checks: Mapped[list] = mapped_column(JSON, default=list)

    application: Mapped[Application] = relationship(back_populates="offer")
    student: Mapped[Student] = relationship(lazy="joined")
    job: Mapped[Job] = relationship(lazy="joined")
    company: Mapped[Company] = relationship(lazy="joined")
