"""Provider-agnostic authentication contract.

The application talks only to :class:`AuthProvider`. Concrete providers
(Firebase today, another OIDC/Google-compatible provider tomorrow) implement the
same three operations, so routes and middleware never depend on a specific
vendor. ``get_auth_provider`` selects the implementation from configuration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.config import Settings, settings


class AuthError(Exception):
    """Raised when a session cannot be created from the supplied credentials."""


@dataclass(frozen=True)
class AuthenticatedUser:
    """The identity extracted from a verified session."""

    uid: str
    email: str | None = None
    name: str | None = None
    picture: str | None = None


@dataclass(frozen=True)
class SessionResult:
    """A minted session cookie and its lifetime, in seconds."""

    cookie_value: str
    max_age: int


class AuthProvider(ABC):
    """The operations every auth backend must support."""

    @abstractmethod
    def create_session(self, id_token: str) -> SessionResult:
        """Verify an ID token and mint a session cookie.

        Raises :class:`AuthError` if the token is invalid or too old.
        """

    @abstractmethod
    def verify_session(self, cookie_value: str) -> AuthenticatedUser | None:
        """Return the user for a valid session cookie, or ``None``."""

    @abstractmethod
    def revoke(self, uid: str) -> None:
        """Revoke a user's sessions (used on logout)."""


class NullAuthProvider(AuthProvider):
    """No-op provider used when ``AUTH_ENABLED`` is false.

    Every request is treated as an anonymous but authenticated user, preserving
    the app's original open behavior for local development and tests.
    """

    ANONYMOUS = AuthenticatedUser(uid="anonymous", email=None, name="Anonymous", picture=None)

    def create_session(self, id_token: str) -> SessionResult:
        return SessionResult(cookie_value="anonymous", max_age=0)

    def verify_session(self, cookie_value: str) -> AuthenticatedUser | None:
        return self.ANONYMOUS

    def revoke(self, uid: str) -> None:
        return None


def get_auth_provider(config: Settings | None = None) -> AuthProvider:
    """Select the auth provider based on configuration.

    Returns :class:`NullAuthProvider` when auth is disabled. Otherwise selects a
    concrete provider by ``AUTH_PROVIDER``. Raises ``ValueError`` for unknown
    provider names.
    """

    config = config or settings
    if not config.AUTH_ENABLED:
        return NullAuthProvider()

    provider = config.AUTH_PROVIDER.strip().lower()
    if provider == "firebase":
        # Imported lazily so the firebase-admin dependency is only required when
        # the Firebase provider is actually selected.
        from app.auth.firebase_provider import FirebaseAuthProvider

        return FirebaseAuthProvider(config)

    raise ValueError(f"Unknown AUTH_PROVIDER: {config.AUTH_PROVIDER!r}")
