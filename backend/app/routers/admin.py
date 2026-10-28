"""Administrator endpoints: users, roles, policies, academic configuration, audit log, dashboard, settings."""
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Request
from pydantic import EmailStr, Field, StrictBool

from ..deps import AdminUser, Db, require_perm
from ..enums import Degree, PolicyKind, PolicyScope, RoleName, UserStatus
from ..models import User
from ..schemas.common import CamelModel, PageParams, ok, paged
from ..services import admin_service, users_service

router = APIRouter(tags=["admin"])
Perm = lambda *p: Annotated[User, require_perm(*p)]  # noqa: E731


# ---------------------------------------------------------------- schemas
class UserIn(CamelModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr = Field(max_length=190)
    user_code: str = Field(max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9._\-/]*$")
    role: RoleName
    department_id: int | None = None
    graduation_year: int | None = Field(None, ge=2000, le=2100)


class UserQuery(PageParams):
    q: str | None = Field(None, max_length=100)
    role: RoleName | None = None
    status: UserStatus | None = None
    dept: int | None = None


class UserStatusIn(CamelModel):
    status: Literal["active", "inactive"]


class ImportRow(CamelModel):
    student_code: str | None = Field(None, max_length=200)
    name: str | None = Field(None, max_length=500)
    email: str | None = Field(None, max_length=500)
    department_code: str | None = Field(None, max_length=200)
    graduation_year: str | None = Field(None, max_length=20)
    cgpa: str | float | None = None


class ImportIn(CamelModel):
    rows: list[ImportRow] = Field(min_length=1, max_length=500)


class PermissionIn(CamelModel):
    enabled: StrictBool


class PolicyIn(CamelModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field("", max_length=400)
    kind: PolicyKind
    scope: PolicyScope = PolicyScope.COLLEGE
    scope_value: str | None = Field(None, max_length=32)
    params: dict = Field(default_factory=dict, max_length=10)
    enabled: StrictBool = True


class ReasonIn(CamelModel):
    reason: str = Field(min_length=3, max_length=300)


class DepartmentIn(CamelModel):
    code: str = Field(min_length=1, max_length=16, pattern=r"^[A-Za-z0-9&\-]+$")
    name: str = Field(min_length=1, max_length=160)
    head_name: str | None = Field(None, max_length=120)


class CourseIn(CamelModel):
    code: str = Field(min_length=1, max_length=24, pattern=r"^[A-Za-z0-9&\-]+$")
    name: str = Field(min_length=1, max_length=160)
    degree: Degree
    department_id: int
    duration_years: int = Field(4, ge=1, le=8)


class YearIn(CamelModel):
    label: str = Field(pattern=r"^\d{4}-\d{2}$")
    graduation_year: int = Field(ge=2000, le=2100)
    active: StrictBool = False


class AuditQuery(PageParams):
    page_size: int = Field(12, ge=1, le=100)
    actor: str | None = Field(None, max_length=100)
    action: str | None = Field(None, max_length=64)
    resource: str | None = Field(None, max_length=100)
    result: Literal["success", "denied", "failed"] | None = None
    from_: date | None = Field(None, alias="from")
    to: date | None = None


class SettingsIn(CamelModel):
    college_name: str = Field(min_length=1, max_length=160)
    placement_email: EmailStr
    placement_season: str = Field("", max_length=40)
    session_timeout_minutes: int = Field(ge=5, le=1440)
    maintenance_banner: StrictBool = False
    maintenance_message: str = Field("", max_length=300)


# ---------------------------------------------------------------- users
@router.get("/users")
def list_users(request: Request, user: Perm("users.manage"), db: Db):
    q = UserQuery.from_query(request.query_params)
    items, total = users_service.list_users(db, q.q, q.role, q.status, q.dept, q.page, q.page_size)
    return paged(items, total, q.page, q.page_size)


@router.post("/users", status_code=201)
def create_user(body: UserIn, user: Perm("users.manage"), db: Db):
    return ok(users_service.view(users_service.create_user(db, user, body)))


@router.post("/users/import")
def import_users(body: ImportIn, user: Perm("users.manage"), db: Db):
    return ok(users_service.import_students(db, user, body.rows))


@router.put("/users/{user_id}")
def update_user(user_id: int, body: UserIn, user: Perm("users.manage"), db: Db):
    return ok(users_service.view(users_service.update_user(db, user, user_id, body)))


@router.post("/users/{user_id}/status")
def user_status(user_id: int, body: UserStatusIn, user: Perm("users.manage"), db: Db):
    return ok(users_service.view(users_service.set_status(db, user, user_id, body.status)))


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, user: Perm("users.manage"), db: Db):
    return ok({"message": users_service.reset_password(db, user, user_id)})


# ---------------------------------------------------------------- roles
@router.get("/admin/roles")
def roles(user: Perm("roles.manage"), db: Db):
    return ok(users_service.roles_overview(db))


@router.put("/admin/roles/{role}/permissions/{perm}")
def set_permission(role: str, perm: str, body: PermissionIn, user: Perm("roles.manage"), db: Db):
    return ok(users_service.set_permission(db, user, role, perm, body.enabled))


# ---------------------------------------------------------------- policies
@router.get("/admin/policies")
def policies(user: Perm("policies.manage"), db: Db):
    return ok(admin_service.list_policies(db))


@router.post("/admin/policies", status_code=201)
def create_policy(body: PolicyIn, user: Perm("policies.manage"), db: Db):
    from ..serializers import policy_dict
    return ok(policy_dict(admin_service.save_policy(db, user, body)))


@router.put("/admin/policies/{policy_id}")
def update_policy(policy_id: int, body: PolicyIn, user: Perm("policies.manage"), db: Db):
    from ..serializers import policy_dict
    return ok(policy_dict(admin_service.save_policy(db, user, body, policy_id)))


@router.delete("/admin/policies/{policy_id}")
def delete_policy(policy_id: int, body: ReasonIn, user: Perm("policies.manage"), db: Db):
    admin_service.delete_policy(db, user, policy_id, body.reason)
    return ok({"ok": True})


# ---------------------------------------------------------------- academic configuration (administrator role)
@router.get("/admin/academic")
def academic(user: AdminUser, db: Db):
    return ok(admin_service.academic(db))


@router.post("/admin/departments", status_code=201)
def create_department(body: DepartmentIn, user: AdminUser, db: Db):
    admin_service.save_department(db, user, body)
    return ok(admin_service.academic(db))


@router.put("/admin/departments/{dept_id}")
def update_department(dept_id: int, body: DepartmentIn, user: AdminUser, db: Db):
    admin_service.save_department(db, user, body, dept_id)
    return ok(admin_service.academic(db))


@router.delete("/admin/departments/{dept_id}")
def delete_department(dept_id: int, user: AdminUser, db: Db):
    admin_service.delete_department(db, user, dept_id)
    return ok({"ok": True})


@router.post("/admin/courses", status_code=201)
def create_course(body: CourseIn, user: AdminUser, db: Db):
    admin_service.save_course(db, user, body)
    return ok(admin_service.academic(db))


@router.put("/admin/courses/{course_id}")
def update_course(course_id: int, body: CourseIn, user: AdminUser, db: Db):
    admin_service.save_course(db, user, body, course_id)
    return ok(admin_service.academic(db))


@router.delete("/admin/courses/{course_id}")
def delete_course(course_id: int, user: AdminUser, db: Db):
    admin_service.delete_course(db, user, course_id)
    return ok({"ok": True})


@router.post("/admin/academic-years", status_code=201)
def create_year(body: YearIn, user: AdminUser, db: Db):
    admin_service.save_year(db, user, body)
    return ok(admin_service.academic(db)["academicYears"])


@router.put("/admin/academic-years/{year_id}")
def update_year(year_id: int, body: YearIn, user: AdminUser, db: Db):
    admin_service.save_year(db, user, body, year_id)
    return ok(admin_service.academic(db)["academicYears"])


# ---------------------------------------------------------------- audit log, dashboard, settings
@router.get("/admin/audit-logs")
def audit_logs(request: Request, user: Perm("audit.view"), db: Db):
    q = AuditQuery.from_query(request.query_params)
    items, total, actions = admin_service.audit_logs(db, q.actor, q.action, q.resource, q.result, q.from_, q.to, q.page, q.page_size)
    return paged(items, total, q.page, q.page_size, actions=actions)


@router.get("/admin/dashboard")
def admin_dashboard(user: AdminUser, db: Db):
    return ok(admin_service.dashboard(db, user))


@router.get("/admin/settings")
def get_settings(user: AdminUser, db: Db):
    return ok({"settings": admin_service.get_settings_values(db), "status": admin_service.system_status(db)})


@router.put("/admin/settings")
def save_settings(body: SettingsIn, user: AdminUser, db: Db):
    return ok({"settings": admin_service.save_settings(db, user, body), "status": admin_service.system_status(db)})


@router.get("/settings/public")
def public_settings(db: Db):
    """The few harmless settings the browser needs before and after sign-in (college name, banner, idle timeout)."""
    return ok(admin_service.public_settings(db))
