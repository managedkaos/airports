from contextlib import asynccontextmanager
from dataclasses import replace
from unittest.mock import patch

from httpx2 import ASGITransport, AsyncClient

import app.auth.dependencies as deps
import app.main as main_module
from app.auth.provider import AuthenticatedUser
from app.config import settings
from app.main import app

USER = AuthenticatedUser(uid="u1", email="a@b.com", name="Ada", picture="http://pic")
MINT = "valid-cookie"


class FakeProvider:
    def create_session(self, id_token):
        raise NotImplementedError

    def verify_session(self, cookie_value):
        return USER if cookie_value == MINT else None

    def revoke(self, uid):
        pass


@asynccontextmanager
async def client(auth_enabled=True):
    cfg = replace(settings, AUTH_ENABLED=auth_enabled)
    deps.reset_provider()
    with (
        patch.object(main_module, "settings", cfg),
        patch.object(deps, "settings", cfg),
        patch.object(deps, "_provider", FakeProvider()),
    ):
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c,
        ):
            yield c
    deps.reset_provider()


def _auth_cookie(c):
    c.cookies.set(settings.SESSION_COOKIE_NAME, MINT)


async def test_unauthenticated_page_redirects_to_login():
    async with client() as c:
        for page in ("/", "/table", "/globe"):
            resp = await c.get(page, follow_redirects=False)
            assert resp.status_code == 302
            assert resp.headers["location"] == "/login"


async def test_unauthenticated_api_returns_401():
    async with client() as c:
        for path in ("/api/airports", "/api/config", "/api/cesium-token", "/api/me"):
            resp = await c.get(path)
            assert resp.status_code == 401


async def test_authenticated_access_succeeds():
    async with client() as c:
        _auth_cookie(c)
        assert (await c.get("/table")).status_code == 200
        assert (await c.get("/globe")).status_code == 200
        assert (await c.get("/api/airports")).status_code == 200
        assert (await c.get("/api/config")).status_code == 200


async def test_public_routes_always_reachable():
    async with client() as c:
        assert (await c.get("/health")).status_code == 200
        assert (await c.get("/api/auth-config")).status_code == 200
        assert (await c.get("/login", follow_redirects=False)).status_code == 200
        assert (await c.get("/static/js/common.js")).status_code == 200


async def test_auth_disabled_opens_everything():
    async with client(auth_enabled=False) as c:
        assert (await c.get("/table")).status_code == 200
        assert (await c.get("/api/airports")).status_code == 200
        resp = await c.get("/", follow_redirects=False)
        assert resp.status_code == 307 and resp.headers["location"] == "/table"
