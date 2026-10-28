from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base, utcnow
from ..enums import NotificationKind, PolicyScope, ProcessingStatus, ReminderKind
from .companies import Company, Job


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(190))
    doc_type: Mapped[str] = mapped_column(String(32))
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    owner_student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"))
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"))
    access_roles: Mapped[list] = mapped_column(JSON, default=list)
    file_name: Mapped[str] = mapped_column(String(255), default="")
    size_kb: Mapped[int] = mapped_column(Integer, default=0)
    storage_key: Mapped[str] = mapped_column(String(255), default="")
    processing: Mapped[str] = mapped_column(String(32), default=ProcessingStatus.QUEUED)
    pages: Mapped[int] = mapped_column(SmallInteger, default=0)
    version: Mapped[int] = mapped_column(SmallInteger, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    uploader: Mapped["User | None"] = relationship(lazy="joined")  # noqa: F821
    company: Mapped[Company | None] = relationship(lazy="joined")
    job: Mapped[Job | None] = relationship(lazy="joined")
    chunks: Mapped[list["DocumentChunk"]] = relationship(cascade="all, delete-orphan", order_by="DocumentChunk.chunk_index")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    page: Mapped[int] = mapped_column(SmallInteger)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)


class Reminder(Base):
    __tablename__ = "reminders"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    remind_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(32), default=ReminderKind.CUSTOM)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    job: Mapped[Job | None] = relationship(lazy="joined")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_created", "user_id", "created_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(String(500), default="")
    kind: Mapped[str] = mapped_column(String(32), default=NotificationKind.SYSTEM)
    link: Mapped[str | None] = mapped_column(String(200))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    email: Mapped[bool] = mapped_column(Boolean, default=True)
    push: Mapped[bool] = mapped_column(Boolean, default=False)
    drive_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    deadline_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    interview_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    offer_updates: Mapped[bool] = mapped_column(Boolean, default=True)


class PlacementPolicy(Base):
    __tablename__ = "placement_policies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(String(400), default="")
    kind: Mapped[str] = mapped_column(String(32))
    scope: Mapped[str] = mapped_column(String(32), default=PolicyScope.COLLEGE)
    scope_value: Mapped[str | None] = mapped_column(String(32))  # department id or graduation year
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    updated_by: Mapped[str] = mapped_column(String(120), default="system")


class SystemSetting(Base):
    """Key/value settings edited on the admin System Settings page."""
    __tablename__ = "system_settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
