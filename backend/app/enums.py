"""Every enumerated value used by the app. Stored as VARCHAR in the database."""
from enum import StrEnum


class RoleName(StrEnum):
    ADMIN = "admin"
    FACULTY = "faculty"
    STUDENT = "student"


class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    INVITED = "invited"


class Degree(StrEnum):
    BE = "B.E."
    BTECH = "B.Tech"
    ME = "M.E."
    MTECH = "M.Tech"
    MBA = "MBA"
    MCA = "MCA"


class PlacementStatus(StrEnum):
    UNPLACED = "unplaced"
    IN_PROCESS = "in_process"
    PLACED = "placed"
    OPTED_OUT = "opted_out"


class SkillKind(StrEnum):
    SKILL = "skill"
    INTEREST = "interest"
    PREFERRED_ROLE = "preferred_role"


class ApplicationStatus(StrEnum):
    APPLIED = "applied"
    SHORTLISTED = "shortlisted"
    INTERVIEW = "interview"
    SELECTED = "selected"
    OFFER_RECEIVED = "offer_received"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


ACTIVE_APPLICATION_STATUSES = (
    ApplicationStatus.APPLIED,
    ApplicationStatus.SHORTLISTED,
    ApplicationStatus.INTERVIEW,
    ApplicationStatus.SELECTED,
)


class EligibilityState(StrEnum):
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    PROFILE_INCOMPLETE = "profile_incomplete"
    NEEDS_VERIFICATION = "needs_verification"


class InterviewStatus(StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class OfferStatus(StrEnum):
    PENDING = "pending"
    RECEIVED = "received"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"


class CompanyTier(StrEnum):
    REGULAR = "regular"
    DREAM = "dream"
    SUPER_DREAM = "super_dream"


TIER_RANK = {CompanyTier.REGULAR: 0, CompanyTier.DREAM: 1, CompanyTier.SUPER_DREAM: 2}


class JobStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class JobType(StrEnum):
    FULL_TIME = "Full-time"
    INTERNSHIP = "Internship"
    INTERNSHIP_PPO = "Internship + PPO"


class RoundMode(StrEnum):
    ONLINE = "Online"
    ON_CAMPUS = "On-campus"
    VIRTUAL = "Virtual"


class DocumentType(StrEnum):
    RESUME = "resume"
    CERTIFICATE = "certificate"
    BROCHURE = "brochure"
    CIRCULAR = "circular"
    ELIGIBILITY = "eligibility"


PERSONAL_DOCUMENT_TYPES = (DocumentType.RESUME, DocumentType.CERTIFICATE)


class ProcessingStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class ReminderKind(StrEnum):
    DRIVE = "drive"
    DEADLINE = "deadline"
    INTERVIEW = "interview"
    CUSTOM = "custom"


class NotificationKind(StrEnum):
    DRIVE = "drive"
    DEADLINE = "deadline"
    INTERVIEW = "interview"
    OFFER = "offer"
    SYSTEM = "system"
    APPLICATION = "application"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class PolicyKind(StrEnum):
    MAX_OFFERS = "max_offers"
    TIER_RESTRICTION = "tier_restriction"
    APPLICATION_LIMIT = "application_limit"
    ACCEPTED_OFFER = "accepted_offer"
    EXCEPTION_APPROVAL = "exception_approval"


class PolicyScope(StrEnum):
    COLLEGE = "college"
    DEPARTMENT = "department"
    ACADEMIC_YEAR = "academic_year"


class AuditResult(StrEnum):
    SUCCESS = "success"
    DENIED = "denied"
    FAILED = "failed"


class ActionState(StrEnum):
    AWAITING = "awaiting_confirmation"
    EXECUTING = "executing"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
