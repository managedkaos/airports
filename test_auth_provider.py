from dataclasses import replace

import pytest

from app.auth.provider import (
    AuthenticatedUser,
    NullAuthProvider,
    SessionResult,
    get_auth_provider,
)
from app.config import settings


def test_factory_returns_null_provider_when_auth_disabled():
    provider = get_auth_provider(replace(settings, AUTH_ENABLED=False))
    assert isinstance(provider, NullAuthProvider)


def test_null_provider_treats_everyone_as_authenticated():
    provider = NullAuthProvider()
    user = provider.verify_session("anything")
    assert isinstance(user, AuthenticatedUser)
    assert user.uid == "anonymous"
    assert isinstance(provider.create_session("token"), SessionResult)
    assert provider.revoke("anonymous") is None


def test_factory_selects_firebase_provider(monkeypatch):
    created = {}

    class FakeFirebaseProvider:
        def __init__(self, config):
            created["config"] = config

    # Patch the concrete class before the factory imports it.
    import app.auth.firebase_provider as fb

    monkeypatch.setattr(fb, "FirebaseAuthProvider", FakeFirebaseProvider)
    config = replace(settings, AUTH_ENABLED=True, AUTH_PROVIDER="firebase")
    provider = get_auth_provider(config)
    assert isinstance(provider, FakeFirebaseProvider)
    assert created["config"] is config


def test_factory_raises_on_unknown_provider():
    config = replace(settings, AUTH_ENABLED=True, AUTH_PROVIDER="nope")
    with pytest.raises(ValueError, match="Unknown AUTH_PROVIDER"):
        get_auth_provider(config)
