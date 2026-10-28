from sqlalchemy import select

from app.models import AuditLog, Department, PlacementPolicy, Role, User

from .conftest import PASSWORD, login

API = "/api/v1"


def uid(db, email):
    return db.scalar(select(User.id).where(User.email == email))


def test_faculty_cannot_use_admin_endpoints(client, faculty):
    assert client.get(f"{API}/users", headers=faculty).status_code == 403
    assert client.get(f"{API}/admin/academic", headers=faculty).status_code == 403
    assert client.get(f"{API}/admin/dashboard", headers=faculty).status_code == 403


def test_create_user_is_invited_and_can_accept(client, admin, db, monkeypatch):
    from app.services import users_service
    tokens = []
    real = users_service.issue_reset_token
    monkeypatch.setattr(users_service, "issue_reset_token", lambda *a, **k: tokens.append(real(*a, **k)) or tokens[-1])
    r = client.post(f"{API}/users", headers=admin, json={"name": "New Prof", "email": "Prof@Campus.demo", "userCode": "FAC300",
                                                       "role": "faculty", "departmentId": 1})
    assert r.status_code == 201, r.text
    assert r.json()["data"]["status"] == "invited" and r.json()["data"]["email"] == "prof@campus.demo"
    dup = client.post(f"{API}/users", headers=admin, json={"name": "X", "email": "prof@campus.demo", "userCode": "FAC301", "role": "faculty"})
    assert dup.status_code == 409
    assert client.post(f"{API}/auth/reset-password", json={"token": tokens[0], "password": "Welcome@2026"}).status_code == 200
    login(client, "prof@campus.demo", "Welcome@2026")


def test_escalation_guards(client, admin, faculty, db):
    me = uid(db, "admin@campus.demo")
    assert client.post(f"{API}/users/{me}/status", headers=admin, json={"status": "inactive"}).status_code == 409
    body = {"name": "Rahul Verma", "email": "admin@campus.demo", "userCode": "ADM001", "role": "faculty"}
    assert client.put(f"{API}/users/{me}", headers=admin, json=body).status_code == 409  # own role
    stu = uid(db, "student@campus.demo")
    s_body = {"name": "Aarav Menon", "email": "student@campus.demo", "userCode": "23CSE101", "role": "faculty", "departmentId": 1}
    assert client.put(f"{API}/users/{stu}", headers=admin, json=s_body).status_code == 409  # student -> staff
    # a faculty member who is given users.manage still cannot touch admin accounts
    faculty_role = db.scalar(select(Role).where(Role.name == "faculty"))
    client.put(f"{API}/admin/roles/faculty/permissions/users.manage", headers=admin, json={"enabled": True})
    db.expire_all()
    r = client.post(f"{API}/users/{me}/status", headers=faculty, json={"status": "inactive"})
    assert r.status_code == 403
    assert faculty_role


def test_deactivation_kills_sessions(client, admin, db):
    h = login(client, "student@campus.demo")
    stu = uid(db, "student@campus.demo")
    assert client.post(f"{API}/users/{stu}/status", headers=admin, json={"status": "inactive"}).json()["data"]["status"] == "inactive"
    assert client.get(f"{API}/auth/me", headers=h).status_code == 401
    r = client.post(f"{API}/auth/login", json={"identifier": "student@campus.demo", "password": PASSWORD})
    assert r.status_code == 403


def test_import_students(client, admin):
    rows = [
        {"studentCode": "24CSE001", "name": "Asha", "email": "asha@campus.demo", "departmentCode": "cse", "graduationYear": "2028", "cgpa": "8.1"},
        {"studentCode": "24CSE001", "name": "Dup", "email": "dup@campus.demo", "departmentCode": "CSE", "graduationYear": "2028"},
        {"studentCode": "24XX002", "name": "Bad", "email": "not-an-email", "departmentCode": "XYZ", "graduationYear": "28"},
    ]
    r = client.post(f"{API}/users/import", headers=admin, json={"rows": rows}).json()["data"]
    assert r["imported"] == 1 and r["total"] == 3
    fields = {(e["row"], e["field"]) for e in r["errors"]}
    assert (3, "studentCode") in fields and {(4, "email"), (4, "departmentCode"), (4, "graduationYear")} <= fields


def test_role_matrix_rules(client, admin, faculty):
    m = client.get(f"{API}/admin/roles", headers=admin).json()["data"]
    assert "reports.view" in m["matrix"]["faculty"] and m["matrix"]["student"] == []
    assert client.put(f"{API}/admin/roles/student/permissions/reports.view", headers=admin, json={"enabled": True}).status_code == 409
    assert client.put(f"{API}/admin/roles/admin/permissions/roles.manage", headers=admin, json={"enabled": False}).status_code == 409
    assert client.put(f"{API}/admin/roles/faculty/permissions/roles.manage", headers=admin, json={"enabled": True}).status_code == 409
    r = client.put(f"{API}/admin/roles/faculty/permissions/reports.view", headers=admin, json={"enabled": False})
    assert "reports.view" not in r.json()["data"]
    assert client.get(f"{API}/reports/placement", headers=faculty).status_code == 403  # applies at once


def test_policies_crud(client, admin, db):
    body = {"name": "CSE offer cap", "kind": "max_offers", "scope": "department", "scopeValue": "1", "params": {"maxAcceptedOffers": 1}}
    r = client.post(f"{API}/admin/policies", headers=admin, json=body)
    assert r.status_code == 201, r.text
    pid = r.json()["data"]["id"]
    assert client.post(f"{API}/admin/policies", headers=admin, json={**body, "params": {"maxAcceptedOffers": 50}}).status_code in (409, 422)
    assert client.put(f"{API}/admin/policies/{pid}", headers=admin, json={**body, "kind": "application_limit"}).status_code == 409
    upd = client.put(f"{API}/admin/policies/{pid}", headers=admin, json={**body, "enabled": False})
    assert upd.json()["data"]["enabled"] is False
    assert client.request("DELETE", f"{API}/admin/policies/{pid}", headers=admin, json={}).status_code == 422
    assert client.request("DELETE", f"{API}/admin/policies/{pid}", headers=admin, json={"reason": "Not needed"}).status_code == 200
    assert db.scalar(select(AuditLog).where(AuditLog.action == "policy.delete"))
    assert not db.get(PlacementPolicy, int(pid))


def test_academic_config(client, admin, db):
    cse = db.scalar(select(Department.id).where(Department.code == "CSE"))
    assert client.delete(f"{API}/admin/departments/{cse}", headers=admin).status_code == 409
    r = client.post(f"{API}/admin/departments", headers=admin, json={"code": "BIO", "name": "Biotechnology"})
    bio = next(d for d in r.json()["data"]["departments"] if d["code"] == "BIO")
    assert client.delete(f"{API}/admin/departments/{bio['id']}", headers=admin).status_code == 200
    years = client.post(f"{API}/admin/academic-years", headers=admin, json={"label": "2028-29", "graduationYear": 2029, "active": True}).json()["data"]
    assert [y["label"] for y in years if y["active"]] == ["2028-29"]
    assert client.post(f"{API}/admin/academic-years", headers=admin, json={"label": "2030-35", "graduationYear": 2035}).status_code == 422


def test_audit_log_and_dashboard(client, admin):
    client.post(f"{API}/auth/login", json={"identifier": "student@campus.demo", "password": "Wrong123"})
    r = client.get(f"{API}/admin/audit-logs", headers=admin, params={"result": "denied"}).json()
    assert r["data"] and all(e["result"] == "denied" for e in r["data"])
    assert "auth" in r["meta"]["actions"] and "ipAddress" not in r["data"][0]
    d = client.get(f"{API}/admin/dashboard", headers=admin).json()["data"]
    assert d["metrics"]["totalUsers"] >= 17 and d["activity"] and d["alerts"]


def test_audit_log_is_append_only(db):
    import pytest
    entry = db.scalar(select(AuditLog).limit(1)) or AuditLog(actor_name="x", actor_role="system", action="x")
    if not entry.id:
        db.add(entry)
        db.commit()
    entry.reason = "tamper"
    with pytest.raises(PermissionError):
        db.commit()
    db.rollback()


def test_settings(client, admin, student):
    s = client.get(f"{API}/admin/settings", headers=admin).json()["data"]
    assert s["status"]["assistant"]["available"] is False and "settings" in s
    body = {**s["settings"], "collegeName": "Riverside College", "maintenanceBanner": True, "maintenanceMessage": "Down at 6 pm"}
    assert client.put(f"{API}/admin/settings", headers=admin, json=body).json()["data"]["settings"]["collegeName"] == "Riverside College"
    pub = client.get(f"{API}/settings/public", headers=student).json()["data"]
    assert pub["maintenanceBanner"] is True and "placementEmail" not in pub
    assert client.put(f"{API}/admin/settings", headers=admin, json={**body, "sessionTimeoutMinutes": 1}).status_code == 422
