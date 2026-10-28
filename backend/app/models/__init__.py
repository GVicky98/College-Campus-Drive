"""Import every model so Base.metadata knows all tables (needed by Alembic and the seeders)."""
from .academic import AcademicRecord, AcademicYear, Course, Department, Student, StudentSkill
from .applications import Application, ApplicationStatusHistory, EligibilitySnapshot, Interview, Offer, interview_candidates
from .companies import Company, DriveEvent, HiringDrive, Job, JobEligibilityRule, SavedJob, job_departments
from .content import Document, DocumentChunk, Notification, NotificationPreference, PlacementPolicy, Reminder, SystemSetting
from .system import AssistantAction, AuditLog, Conversation, Message
from .users import FacultyProfile, PasswordResetToken, Permission, RevokedToken, Role, User, role_permissions

__all__ = [
    "AcademicRecord", "AcademicYear", "Course", "Department", "Student", "StudentSkill",
    "Application", "ApplicationStatusHistory", "EligibilitySnapshot", "Interview", "Offer", "interview_candidates",
    "Company", "DriveEvent", "HiringDrive", "Job", "JobEligibilityRule", "SavedJob", "job_departments",
    "Document", "DocumentChunk", "Notification", "NotificationPreference", "PlacementPolicy", "Reminder", "SystemSetting",
    "AssistantAction", "AuditLog", "Conversation", "Message",
    "FacultyProfile", "PasswordResetToken", "Permission", "RevokedToken", "Role", "User", "role_permissions",
]
