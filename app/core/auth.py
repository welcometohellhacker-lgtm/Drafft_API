"""
Firebase Auth middleware.

Routes that depend on `get_current_user` will:
  - In production (ENABLE_AUTH=true): verify the Firebase ID token sent as
    `Authorization: Bearer <token>` and return the decoded token dict.
  - In local dev (ENABLE_AUTH=false): skip verification and return a
    synthetic token with uid="dev-user" so the rest of the code works
    without a real Firebase token.
"""
from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from firebase_admin import auth

from app.core.config import settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if not settings.enable_auth:
        return {"uid": "dev-user", "email": "dev@local"}

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        decoded = auth.verify_id_token(credentials.credentials)
        return decoded
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as exc:
        logger.warning("Token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
