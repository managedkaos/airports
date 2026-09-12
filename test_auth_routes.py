from contextlib import asynccontextmanager
from unittest.mock import patch

from httpx2 import ASGITransport, AsyncClient

import app.auth.dependencies as deps
from app.auth.provider import AuthenticatedUser, AuthError, SessionResult
from app.config import settings
from app.main import app

USER = AuthenticatedUser(uid="u1", email="a@b.com", name="Ada", picture="http://pic")


class FakeProvider:
    """In-memory auth provider for route tests."""

    def __init__(self, *, mint="cookie-abc", user=USER, fail=False):
        self.mint = mint
        self.user = user
        self.fail = fail
        self.revoked = []

    def create_session(self, id_token):
        if self.fail:
            raise AuthError("Invalid ID token")
        return SessionResult(cookie_value=self.mint, max_age=3600)

    def verify_session(self, cookie_value):
        return self.user if cookie_value == self.mint else None

    def revoke(self, uid):
        self.revoked.append(uid)


@asynccontextmanager
async def client_with(provider):
    with patch.object(deps, "_provider", provider):
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client,
        ):
            yield client


async def test_session_login_sets_cookie_with_valid_csrf():
    provider = FakeProvider()
    async with client_with(provider) as client:
        client.cookies.set("csrfToken", "tok123")
        resp = await client.post("/auth/session", json={"idToken": "id", "csrfToken": "tok123"})
    assert resp.status_code == 200
    set_cookie = resp.headers["set-cookie"]
    assert settings.SESSION_COOKIE_NAME + "=cookie-abc" in set_cookie
    assert "HttpOnly" in set_cookie


async def test_session_login_rejects_csrf_mismatch():
    provider = FakeProvider()
    async with client_with(provider) as client:
        client.cookies.set("csrfToken", "tok123")
        resp = await client.post("/auth/session", json={"idToken": "id", "csrfToken": "WRONG"})
    assert resp.status_code == 401


async def test_session_login_rejects_missing_csrf_cookie():
    provider = FakeProvider()
    async with client_with(provider) as client:
        resp = await client.post("/auth/session", json={"idToken": "id", "csrfToken": "tok"})
    assert resp.status_code == 401


async def test_session_login_invalid_token_returns_401():
    provider = FakeProvider(fail=True)
    async with client_with(provider) as client:
        client.cookies.set("csrfToken", "tok123")
        resp = await client.post("/auth/session", json={"idToken": "bad", "csrfToken": "tok123"})
    assert resp.status_code == 401


async def test_logout_revokes_and_clears_cookie():
    provider = FakeProvider()
    async with client_with(provider) as client:
        client.cookies.set(settings.SESSION_COOKIE_NAME, "cookie-abc")
        resp = await client.post("/auth/logout")
    assert resp.status_code == 200
    assert provider.revoked == ["u1"]
    assert 'session=""' in resp.headers["set-cookie"] or "session=;" in resp.headers["set-cookie"]


async def test_auth_config_is_public_and_returns_keys():
    provider = FakeProvider()
    async with client_with(provider) as client:
        resp = await client.get("/api/auth-config")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"auth_enabled", "provider", "firebase"}
    assert set(body["firebase"]) == {"apiKey", "authDomain", "projectId"}


async def test_me_authenticated_returns_user():
    provider = FakeProvider()
    async with client_with(provider) as client:
        client.cookies.set(settings.SESSION_COOKIE_NAME, "cookie-abc")
        resp = await client.get("/api/me")
    assert resp.status_code == 200
    assert resp.json() == {"uid": "u1", "email": "a@b.com", "name": "Ada", "picture": "http://pic"}


async def test_me_unauthenticated_returns_401():
    provider = FakeProvider()
    async with client_with(provider) as client:
        resp = await client.get("/api/me")
    assert resp.status_code == 401
