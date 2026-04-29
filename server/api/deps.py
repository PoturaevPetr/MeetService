from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from server.auth.jwt import JwtAuthError, decode_access_token

_bearer = HTTPBearer(auto_error=False)


async def jwt_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> uuid.UUID:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        payload = decode_access_token(credentials.credentials)
        return payload["_user_id"]
    except JwtAuthError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
