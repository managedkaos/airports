import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    CESIUM_ION_TOKEN: str = os.getenv("CESIUM_ION_TOKEN", "")
    KIOSK_DWELL_SECONDS: float = float(os.getenv("KIOSK_DWELL_SECONDS", "60"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Authentication
    AUTH_ENABLED: bool = _env_bool("AUTH_ENABLED", True)
    AUTH_PROVIDER: str = os.getenv("AUTH_PROVIDER", "firebase")

    # Firebase server credentials (Admin SDK): supply one of these.
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    FIREBASE_SERVICE_ACCOUNT_JSON: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")

    # Firebase browser config (public, non-secret).
    FIREBASE_API_KEY: str = os.getenv("FIREBASE_API_KEY", "")
    FIREBASE_AUTH_DOMAIN: str = os.getenv("FIREBASE_AUTH_DOMAIN", "")
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")

    # Session cookie policy.
    SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "session")
    SESSION_EXPIRES_DAYS: float = float(os.getenv("SESSION_EXPIRES_DAYS", "5"))
    SESSION_COOKIE_SECURE: bool = _env_bool("SESSION_COOKIE_SECURE", True)


settings = Settings()
