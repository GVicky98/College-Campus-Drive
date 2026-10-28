from app.models import AuditLog, User
from sqlalchemy import select

from .conftest import PASSWORD, login

API = "/api/v1"


def test_login_returns_token_and_sets_cookies(client):
    r = client.post(f"{API}/auth/login", json={"identifier": "student@campus.demo", "password": PASSWORD})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["user"]["role"] == "student"
    assert data["permissions"] == []
    assert "refresh_token_cookie" in r.cookies and "csrf_refresh_token" in r.cookies


def test_login_by_user_code_case_insensitive(client):
    r = client.post(f"{API}/auth/login", json={"identifier": "fac101", "password": PASSWORD})
    assert r.status_code == 200
    assert "reports.view" in r.json()["data"]["permissions"]


def test_bad_password_is_generic_401(client):
    r = client.post(f"{API}/auth/login", json={"identifier": "student@campus.demo", "password": "Wrong123"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"
    unknown = client.post(f"{API}/auth/login", json={"identifier": "nobody@x.com", "password": "Wrong123"})
    assert unknown.json()["error"]["message"] == r.json()["error"]["message"]


def test_lockout_after_five_failures(client, db):
    for _ in range(5):
        client.post(f"{API}/auth/login", json={"identifier": "student@campus.demo", "password": "Wrong123"})
    r = client.post(f"{API}/auth/login", json={"identifier": "student@campus.demo", "password": PASSWORD})
    assert r.status_code == 401
    assert db.scalar(select(AuditLog).where(AuditLog.action == "auth.lockout"))


def test_invited_account_cannot_sign_in(client):
    r = client.post(f"{API}/auth/login", json={"identifier": "latha.menon@campus.demo", "password": PASSWORD})
    assert r.status_code == 401  # invited accounts have an unusable password


def test_unknown_fields_rejected(client):
    r = client.post(f"{API}/auth/login", json={"identifier": "a", "password": "b", "role": "admin"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_me_requires_token(client, student):
    assert client.get(f"{API}/auth/me").status_code == 401
    r = client.get(f"{API}/auth/me", headers=student)
    assert r.json()["data"]["user"]["email"] == "student@campus.demo"


def test_refresh_rotates_and_needs_csrf(client):
    client.post(f"{API}/auth/login", json={"identifier": "student@campus.demo", "password": PASSWORD})
    old_refresh = client.cookies.get("refresh_token_cookie")
    csrf = client.cookies.get("csrf_refresh_token")
    assert client.post(f"{API}/auth/refresh").status_code == 401  # no CSRF header
    r = client.post(f"{API}/auth/refresh", headers={"X-CSRF-TOKEN": csrf})
    assert r.status_code == 200 and r.json()["data"]["accessToken"]
    # replaying the old (now revoked) refresh token fails
    client.cookies.set("refresh_token_cookie", old_refresh, path="/api/v1/auth")
    client.cookies.set("csrf_refresh_token", csrf, path="/")
    assert client.post(f"{API}/auth/refresh", headers={"X-CSRF-TOKEN": csrf}).status_code == 401


def test_change_password_policy_and_success(client, student):
    weak = client.post(f"{API}/auth/change-password", headers=student,
                       json={"currentPassword": PASSWORD, "newPassword": "weak"})
    assert weak.status_code == 422 and "password" in weak.json()["error"]["details"]
    wrong = client.post(f"{API}/auth/change-password", headers=student,
                        json={"currentPassword": "Nope1234", "newPassword": "Better@2026"})
    assert wrong.status_code == 401
    good = client.post(f"{API}/auth/change-password", headers=student,
                       json={"currentPassword": PASSWORD, "newPassword": "Better@2026"})
    assert good.status_code == 200
    login(client, "student@campus.demo", "Better@2026")


def test_forgot_and_reset_password(client, db, monkeypatch):
    from app.services import auth_service
    captured = {}
    real = auth_service.issue_reset_token

    def spy(*a, **k):
        captured["raw"] = real(*a, **k)
        return captured["raw"]

    monkeypatch.setattr(auth_service, "issue_reset_token", spy)
    r = client.post(f"{API}/auth/forgot-password", json={"email": "student@campus.demo"})
    same = client.post(f"{API}/auth/forgot-password", json={"email": "ghost@campus.demo"})
    assert r.json() == same.json()
    ok = client.post(f"{API}/auth/reset-password", json={"token": captured["raw"], "password": "Fresh@2026"})
    assert ok.status_code == 200
    again = client.post(f"{API}/auth/reset-password", json={"token": captured["raw"], "password": "Fresh@2026"})
    assert again.status_code == 422
    login(client, "student@campus.demo", "Fresh@2026")


def test_inactive_user_token_rejected(client, db, student):
    u = db.scalar(select(User).where(User.email == "student@campus.demo"))
    u.status = "inactive"
    db.commit()
    assert client.get(f"{API}/auth/me", headers=student).status_code == 401


def test_reference_filters(client, faculty, student):
    staff = client.get(f"{API}/reference/filters", headers=faculty).json()["data"]
    mine = client.get(f"{API}/reference/filters", headers=student).json()["data"]
    assert {d["label"] for d in staff["departments"]} >= {"CSE", "IT"}
    assert len(staff["jobs"]) > len(mine["jobs"])  # students only see published jobs


def test_security_headers(client):
    r = client.get(f"{API}/health")
    assert r.json() == {"data": {"status": "ok"}}
    assert r.headers["X-Frame-Options"] == "DENY"


def test_notifications_scoped_to_owner(client, student, faculty):
    mine = client.get(f"{API}/notifications", headers=student).json()["data"]
    assert mine and all(n["userId"] == mine[0]["userId"] for n in mine)
    other = client.post(f"{API}/notifications/{mine[0]['id']}/read", headers=faculty)
    assert other.status_code == 404
    assert client.post(f"{API}/notifications/{mine[0]['id']}/read", headers=student).json()["data"]["read"] is True
    prefs = client.get(f"{API}/notifications/preferences", headers=student).json()["data"]
    prefs["push"] = True
    assert client.put(f"{API}/notifications/preferences", headers=student, json=prefs).json()["data"]["push"] is True
