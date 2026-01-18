"""Supabase authentication middleware for FastAPI."""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Optional
import httpx

from app.core.config import settings


# HTTP Bearer token extractor
security = HTTPBearer(auto_error=False)


class AuthUser:
    """Represents an authenticated user from Supabase."""
    def __init__(self, user_id: str, email: Optional[str] = None):
        self.id = user_id
        self.email = email


async def verify_supabase_token(token: str) -> dict:
    """
    Verify a Supabase JWT token.

    Supabase JWTs are signed with the JWT secret from your project settings.
    """
    if not settings.SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase JWT secret not configured"
        )

    try:
        # Decode and verify the JWT
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[AuthUser]:
    """
    Get the current authenticated user from the JWT token.

    Returns None if no token is provided (allows anonymous access).
    Raises HTTPException if token is invalid.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = await verify_supabase_token(token)

    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: no user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthUser(user_id=user_id, email=email)


async def require_auth(
    user: Optional[AuthUser] = Depends(get_current_user)
) -> AuthUser:
    """
    Require authentication - raises 401 if not authenticated.

    Use this dependency for protected endpoints.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def optional_auth(
    user: Optional[AuthUser] = Depends(get_current_user)
) -> Optional[AuthUser]:
    """
    Optional authentication - returns None if not authenticated.

    Use this for endpoints that work with or without auth.
    """
    return user
