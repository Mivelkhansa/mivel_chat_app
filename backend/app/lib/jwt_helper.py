# -------------------------
# JWT helpers
# -------------------------
from datetime import datetime, timedelta, timezone

import jwt

from ..config import (
    JWT_ACCESS_EXPIRATION,
    JWT_ACCESS_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_REFRESH_EXPIRATION,
    JWT_REFRESH_SECRET_KEY,
)


def create_access_token(user_id: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "typ": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc)
            + timedelta(seconds=JWT_ACCESS_EXPIRATION),
            "iss": "vally_chat_app",
        },
        JWT_ACCESS_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def create_refresh_token(user_id: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "typ": "refresh",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc)
            + timedelta(seconds=JWT_REFRESH_EXPIRATION),
            "iss": "vally_chat_app",
        },
        JWT_REFRESH_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def verify_access_token(token: str):
    payload = jwt.decode(
        token,
        JWT_ACCESS_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
    )
    if payload.get("typ") != "access":
        raise jwt.InvalidTokenError("Not an access token")
    return payload


def verify_refresh_token(token: str):
    payload = jwt.decode(
        token,
        JWT_REFRESH_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
    )
    if payload.get("typ") != "refresh":
        raise jwt.InvalidTokenError("Not a refresh token")
    return payload
