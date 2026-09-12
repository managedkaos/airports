"""Firebase implementation of the :class:`AuthProvider` contract.

Uses the Firebase Admin SDK to verify Google ID tokens and to mint/verify
HTTP-only session cookies. The Admin app is initialized lazily from either
``GOOGLE_APPLICATION_CREDENTIALS`` (a file path) or
``FIREBASE_SERVICE_ACCOUNT_JSON`` (inline JSON), so importing this module never
requires credentials to be present.
"""

from __future__ import annotations

import datetime
import json
import time

from app.auth.provider import AuthenticatedUser, AuthError, AuthProvider, SessionResult
from app.config import Settings

# Only allow minting a session cookie if the user signed in this recently.
_MAX_AUTH_AGE_SECONDS = 5 * 60


class FirebaseAuthProvider(AuthProvider):
    def __init__(self, config: Settings):
        self._config = config
        self._app = None  # Lazily initialized firebase_admin app.

    def _ensure_app(self):
        """Initialize (once) and return the firebase_admin app."""
        if self._app is not None:
            return self._app

        import firebase_admin
        from firebase_admin import credentials

        if self._config.FIREBASE_SERVICE_ACCOUNT_JSON:
            cred = credentials.Certificate(json.loads(self._config.FIREBASE_SERVICE_ACCOUNT_JSON))
        elif self._config.GOOGLE_APPLICATION_CREDENTIALS:
            cred = credentials.Certificate(self._config.GOOGLE_APPLICATION_CREDENTIALS)
        else:
            # Fall back to Application Default Credentials (e.g. GCP runtime).
            cred = credentials.ApplicationDefault()

        # Use a named app so repeated construction in tests/imports is isolated
        # and we do not collide with a default app that may exist.
        app_name = "airports-auth"
        try:
            self._app = firebase_admin.get_app(app_name)
        except ValueError:
            self._app = firebase_admin.initialize_app(cred, name=app_name)
        return self._app

    def create_session(self, id_token: str) -> SessionResult:
        from firebase_admin import auth, exceptions

        app = self._ensure_app()
        expires_in = datetime.timedelta(days=self._config.SESSION_EXPIRES_DAYS)
        try:
            decoded = auth.verify_id_token(id_token, app=app)
            # Guard against stolen ID tokens: require a recent sign-in.
            if time.time() - decoded.get("auth_time", 0) >= _MAX_AUTH_AGE_SECONDS:
                raise AuthError("Recent sign in required")
            cookie_value = auth.create_session_cookie(id_token, expires_in=expires_in, app=app)
        except AuthError:
            raise
        except (auth.InvalidIdTokenError, ValueError) as exc:
            raise AuthError("Invalid ID token") from exc
        except exceptions.FirebaseError as exc:
            raise AuthError("Failed to create a session cookie") from exc

        return SessionResult(cookie_value=cookie_value, max_age=int(expires_in.total_seconds()))

    def verify_session(self, cookie_value: str) -> AuthenticatedUser | None:
        from firebase_admin import auth

        if not cookie_value:
            return None
        app = self._ensure_app()
        try:
            claims = auth.verify_session_cookie(cookie_value, check_revoked=True, app=app)
        except Exception:
            # Any verification failure (invalid, expired, revoked) means no user.
            return None
        return AuthenticatedUser(
            uid=claims.get("uid") or claims.get("sub", ""),
            email=claims.get("email"),
            name=claims.get("name"),
            picture=claims.get("picture"),
        )

    def revoke(self, uid: str) -> None:
        from firebase_admin import auth

        if not uid:
            return
        app = self._ensure_app()
        try:
            auth.revoke_refresh_tokens(uid, app=app)
        except Exception:
            # Logout should succeed even if revocation fails; the cookie is
            # still cleared by the caller.
            return None
