import time
from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from app.auth.firebase_provider import FirebaseAuthProvider
from app.auth.provider import AuthError
from app.config import settings


@pytest.fixture
def provider(monkeypatch):
    config = replace(
        settings,
        AUTH_ENABLED=True,
        AUTH_PROVIDER="firebase",
        SESSION_EXPIRES_DAYS=5,
    )
    prov = FirebaseAuthProvider(config)
    # Bypass real Firebase app initialization.
    monkeypatch.setattr(prov, "_ensure_app", lambda: object())
    return prov


def _fake_auth_module(monkeypatch, **attrs):
    """Install a fake firebase_admin.auth used by lazy imports in the provider."""
    fake_auth = MagicMock()
    fake_auth.InvalidIdTokenError = type("InvalidIdTokenError", (Exception,), {})
    fake_exceptions = MagicMock()
    fake_exceptions.FirebaseError = type("FirebaseError", (Exception,), {})
    for name, value in attrs.items():
        setattr(fake_auth, name, value)
    import firebase_admin

    monkeypatch.setattr(firebase_admin, "auth", fake_auth, raising=False)
    monkeypatch.setattr(firebase_admin, "exceptions", fake_exceptions, raising=False)
    return fake_auth, fake_exceptions


def test_create_session_success(provider, monkeypatch):
    fake_auth, _ = _fake_auth_module(
        monkeypatch,
        verify_id_token=MagicMock(return_value={"auth_time": time.time(), "uid": "u1"}),
        create_session_cookie=MagicMock(return_value="cookie-value"),
    )
    result = provider.create_session("valid-id-token")
    assert result.cookie_value == "cookie-value"
    assert result.max_age == 5 * 24 * 60 * 60
    fake_auth.create_session_cookie.assert_called_once()


def test_create_session_rejects_stale_auth_time(provider, monkeypatch):
    fake_auth, _ = _fake_auth_module(
        monkeypatch,
        verify_id_token=MagicMock(return_value={"auth_time": time.time() - 3600, "uid": "u1"}),
        create_session_cookie=MagicMock(return_value="cookie-value"),
    )
    with pytest.raises(AuthError, match="Recent sign in required"):
        provider.create_session("old-id-token")
    fake_auth.create_session_cookie.assert_not_called()


def test_create_session_invalid_token(provider, monkeypatch):
    fake_auth, _ = _fake_auth_module(monkeypatch)
    fake_auth.verify_id_token = MagicMock(side_effect=fake_auth.InvalidIdTokenError("bad"))
    with pytest.raises(AuthError, match="Invalid ID token"):
        provider.create_session("bad-token")


def test_verify_session_valid(provider, monkeypatch):
    claims = {"uid": "u1", "email": "a@b.com", "name": "Ada", "picture": "http://pic"}
    _fake_auth_module(monkeypatch, verify_session_cookie=MagicMock(return_value=claims))
    user = provider.verify_session("cookie")
    assert user is not None
    assert (user.uid, user.email, user.name, user.picture) == ("u1", "a@b.com", "Ada", "http://pic")


def test_verify_session_invalid_returns_none(provider, monkeypatch):
    _fake_auth_module(monkeypatch, verify_session_cookie=MagicMock(side_effect=Exception("revoked")))
    assert provider.verify_session("cookie") is None


def test_verify_session_empty_cookie_returns_none(provider):
    assert provider.verify_session("") is None


def test_revoke_calls_revoke_refresh_tokens(provider, monkeypatch):
    fake_auth, _ = _fake_auth_module(monkeypatch, revoke_refresh_tokens=MagicMock())
    provider.revoke("u1")
    fake_auth.revoke_refresh_tokens.assert_called_once()
    assert fake_auth.revoke_refresh_tokens.call_args.args[0] == "u1"
