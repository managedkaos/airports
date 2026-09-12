"""Authentication HTTP endpoints (session cookie lifecycle + client config)."""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Request, Response, status

from app.auth.dependencies import current_user, get_provider, require_user
from app.auth.provider import AuthError
from app.config import settings

router = APIRouter()

CSRF_COOKIE_NAME = "csrfToken"


def _set_session_cookie(response: Response, value: str, max_age: int) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=value,
        max_age=max_age,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.SESSION_COOKIE_NAME, path="/")


@router.post("/auth/session")
def create_session(
    request: Request,
    response: Response,
    id_token: str = Body(..., embed=True, alias="idToken"),
    csrf_token: str = Body("", embed=True, alias="csrfToken"),
):
    """Verify a Firebase ID token and set an HTTP-only session cookie."""
    # CSRF double-submit: the token in the body must match the cookie set when
    # the login page was served.
    cookie_csrf = request.cookies.get(CSRF_COOKIE_NAME, "")
    if not cookie_csrf or csrf_token != cookie_csrf:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid CSRF token")

    provider = get_provider()
    try:
        result = provider.create_session(id_token)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    _set_session_cookie(response, result.cookie_value, result.max_age)
    return {"status": "success"}


@router.post("/auth/logout")
def logout(request: Request, response: Response):
    """Revoke the user's refresh tokens and clear the session cookie."""
    user = current_user(request)
    if user is not None and user.uid:
        get_provider().revoke(user.uid)
    _clear_session_cookie(response)
    return {"status": "success"}


@router.get("/api/auth-config")
def auth_config():
    """Public: browser-visible auth configuration for the client SDK."""
    return {
        "auth_enabled": settings.AUTH_ENABLED,
        "provider": settings.AUTH_PROVIDER,
        "firebase": {
            "apiKey": settings.FIREBASE_API_KEY,
            "authDomain": settings.FIREBASE_AUTH_DOMAIN,
            "projectId": settings.FIREBASE_PROJECT_ID,
        },
    }


@router.get("/api/me")
def me(request: Request):
    """Current authenticated user's profile claims."""
    user = require_user(request)
    return {"uid": user.uid, "email": user.email, "name": user.name, "picture": user.picture}
