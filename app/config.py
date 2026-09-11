import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    CESIUM_ION_TOKEN: str = os.getenv("CESIUM_ION_TOKEN", "")
    KIOSK_DWELL_SECONDS: float = float(os.getenv("KIOSK_DWELL_SECONDS", "60"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))


settings = Settings()
