"""Password hashing, password policy, JWT tokens and one-time reset tokens."""
import base64
import hashlib
import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from .config import get_settings
from .database import utcnow
from .errors import ValidationFailed

# ---------------------------------------------------------------- passwords (scrypt, per-hash salt)
_N, _R, _P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return "scrypt${}${}${}${}${}".format(
        _N, _R, _P, base64.b64encode(salt).decode(), base64.b64encode(digest).decode()
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, digest = stored.split("$")
        if algo != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(
            password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def unusable_password() -> str:
    """For invited accounts: a hash no password can match."""
    return "!" + secrets.token_hex(24)


# Compared against when the user does not exist, so timing never reveals whether an account exists.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def check_password_policy(password: str, email: str = "", user_code: str = "") -> None:
    problems = []
    if not 8 <= len(password) <= 128:
        problems.append("Use 8 to 128 characters.")
    if not re.search(r"[A-Z]", password):
        problems.append("Add at least one upper-case letter.")
    if not re.search(r"\d", password):
        problems.append("Add at least one digit.")
    lowered = password.lower()
    for fragment in (email.split("@")[0], user_code):
        if fragment and len(fragment) >= 4 and fragment.lower() in lowered:
            problems.append("Do not include your e-mail name or user ID.")
            break
    if problems:
        raise ValidationFailed(problems[0], details={"password": problems})


# ---------------------------------------------------------------- JWT
ALGORITHM = "HS256"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: int, role: str) -> tuple[str, int]:
    s = get_settings()
    expires = s.access_token_minutes * 60
    payload = {"sub": str(user_id), "role": role, "type": "access", "iat": _now(), "exp": _now() + timedelta(seconds=expires)}
    return jwt.encode(payload, s.jwt_secret_key, algorithm=ALGORITHM), expires


def create_refresh_token(user_id: int, remember: bool) -> tuple[str, str, datetime, str]:
    """Returns (token, jti, expires_at naive UTC, csrf value)."""
    s = get_settings()
    lifetime = timedelta(days=s.refresh_token_days) if remember else timedelta(hours=12)
    jti = uuid.uuid4().hex
    csrf = secrets.token_urlsafe(24)
    exp = _now() + lifetime
    payload = {
        "sub": str(user_id), "type": "refresh", "jti": jti, "csrf": csrf,
        "remember": remember, "iat": _now(), "exp": exp,
    }
    token = jwt.encode(payload, s.jwt_secret_key, algorithm=ALGORITHM)
    return token, jti, exp.replace(tzinfo=None), csrf


def decode_token(token: str, expected_type: str) -> dict | None:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    return payload


# ---------------------------------------------------------------- one-time tokens (reset / invite)
def new_one_time_token() -> tuple[str, str]:
    """Returns (raw token for the link, SHA-256 hash to store)."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def is_locked(locked_until: datetime | None) -> bool:
    return bool(locked_until and locked_until > utcnow())
