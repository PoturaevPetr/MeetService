"""Верификация JWT в том же формате, что ChatService (python-jose HS256, sub, type=access)."""

from __future__ import annotations

import uuid
from typing import Any

from jose import JWTError, jwt

from server.settings import settings


class JwtAuthError(Exception):
    pass


def decode_access_token(token: str) -> dict[str, Any]:
    if not settings.JWT_SECRET_KEY.strip():
        raise JwtAuthError("JWT_SECRET_KEY is not configured")
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as e:
        raise JwtAuthError(str(e)) from e

    if payload.get("type") != "access":
        raise JwtAuthError("Invalid token type")

    sub = payload.get("sub")
    if not sub:
        raise JwtAuthError("Missing sub")

    try:
        user_id = uuid.UUID(str(sub))
    except ValueError as e:
        raise JwtAuthError("Invalid user id in token") from e

    payload["_user_id"] = user_id
    return payload


def get_user_id_from_access_token(token: str) -> uuid.UUID:
    payload = decode_access_token(token)
    return payload["_user_id"]
