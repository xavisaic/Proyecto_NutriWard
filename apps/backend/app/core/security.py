import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings

ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("nutriward-dummy-password")


@dataclass(frozen=True)
class TokenClaims:
    user_id: uuid.UUID
    csrf_token: str


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    return password_hash.verify(password, encoded_hash)


def create_access_token(user_id: uuid.UUID) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    csrf_token = secrets.token_urlsafe(32)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "jti": str(uuid.uuid4()),
        "csrf": csrf_token,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)
    return token, csrf_token


def decode_access_token(token: str) -> TokenClaims:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        user_id = uuid.UUID(payload["sub"])
        csrf_token = payload["csrf"]
        if not isinstance(csrf_token, str) or not csrf_token:
            raise ValueError("Missing CSRF claim")
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid access token") from exc
    return TokenClaims(user_id=user_id, csrf_token=csrf_token)
