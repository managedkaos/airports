"""Shared FastAPI auth dependencies and the process-wide provider accessor."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.auth.provider import AuthenticatedUser, AuthProvider, get_auth_provider
from app.config import settings

_provider: AuthProvider | None = None


def get_provider() -> AuthProvider:
    """Return the process-wide auth provider, building it once from settings."""
    global _provider
    if _provider is None:
        _provider = get_auth_provider(settings)
    return _provider


def reset_provider() -> None:
    """Drop the cached provider so the next call rebuilds it (used in tests)."""
    global _provider
    _provider = None


def current_user(request: Request) -> AuthenticatedUser | None:
    """Resolve the user from the session cookie, or ``None`` if unauthenticated."""
    provider = get_provider()
    cookie_value = request.cookies.get(settings.SESSION_COOKIE_NAME, "")
    return provider.verify_session(cookie_value)


def require_user(request: Request) -> AuthenticatedUser:
    """Dependency that yields the authenticated user or raises 401."""
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user
