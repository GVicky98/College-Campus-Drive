"""/auth: sign-in, refresh (rotating httpOnly cookie + double-submit CSRF), sign-out, passwords."""
from fastapi import APIRouter, Depends, Request, Response
from pydantic import EmailStr, Field, StrictBool

from ..config import get_settings
from ..deps import CurrentUser, Db
from ..errors import Unauthenticated
from ..ratelimit import limit_by_ip
from ..schemas.common import CamelModel, ok
from ..security import decode_token
from ..serializers import user_dict
from ..services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token_cookie"
CSRF_COOKIE = "csrf_refresh_token"
REFRESH_PATH = "/api/v1/auth"


class LoginIn(CamelModel):
    identifier: str = Field(min_length=1, max_length=190)
    password: str = Field(min_length=1, max_length=128)
    remember: StrictBool = False


class ChangePasswordIn(CamelModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)


class ForgotIn(CamelModel):
    email: EmailStr


class ResetIn(CamelModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=1, max_length=128)


def _set_session_cookies(response: Response, user, remember: bool) -> None:
    s = get_settings()
    token, _jti, expires_at, csrf = auth_service.new_refresh(user, remember)
    max_age = s.refresh_token_days * 86400 if remember else None  # None = session cookie
    common = {"secure": s.cookie_secure, "samesite": s.cookie_samesite.lower(), "max_age": max_age}
    response.set_cookie(REFRESH_COOKIE, token, httponly=True, path=REFRESH_PATH, **common)
    # Readable by JavaScript (path "/" so document.cookie exposes it); echoed back in X-CSRF-TOKEN.
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, path="/", **common)


def _clear_cookies(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)
    response.delete_cookie(CSRF_COOKIE, path="/")


def _refresh_payload(request: Request) -> dict | None:
    """The decoded refresh token, only if the CSRF header matches the token's CSRF value."""
    token = request.cookies.get(REFRESH_COOKIE)
    payload = decode_token(token, "refresh") if token else None
    if not payload or request.headers.get("X-CSRF-TOKEN") != payload.get("csrf"):
        return None
    return payload


@router.post("/login", dependencies=[Depends(limit_by_ip("login", get_settings().login_rate_limit))])
def login(body: LoginIn, response: Response, db: Db):
    user = auth_service.login(db, body.identifier, body.password)
    _set_session_cookies(response, user, body.remember)
    return ok(auth_service.session_payload(user))


@router.post("/refresh", dependencies=[Depends(limit_by_ip("refresh", "60/minute"))])
def refresh(request: Request, response: Response, db: Db):
    payload = _refresh_payload(request)
    if not payload:
        raise Unauthenticated("Your session has ended. Please sign in again.")
    user = auth_service.refresh(db, payload)
    db.commit()
    _set_session_cookies(response, user, bool(payload.get("remember")))
    return ok(auth_service.session_payload(user))


@router.post("/logout")
def logout(request: Request, response: Response, db: Db):
    payload = _refresh_payload(request)
    if payload:
        auth_service.revoke(db, payload)
        db.commit()
    _clear_cookies(response)
    return ok({"ok": True})


@router.get("/me")
def me(user: CurrentUser):
    return ok({"user": user_dict(user), "permissions": user.permission_keys})


@router.post("/change-password", dependencies=[Depends(limit_by_ip("change-password", "10/minute"))])
def change_password(body: ChangePasswordIn, user: CurrentUser, response: Response, db: Db):
    auth_service.change_password(db, user, body.current_password, body.new_password)
    _set_session_cookies(response, user, remember=False)  # the old refresh token is now dead; issue a new one
    return ok({"ok": True})


@router.post("/forgot-password", dependencies=[Depends(limit_by_ip("forgot", "5/minute"))])
def forgot_password(body: ForgotIn, db: Db):
    return ok({"message": auth_service.forgot_password(db, body.email)})


@router.post("/reset-password", dependencies=[Depends(limit_by_ip("reset", "10/minute"))])
def reset_password(body: ResetIn, db: Db):
    auth_service.reset_password(db, body.token, body.password)
    return ok({"ok": True})
