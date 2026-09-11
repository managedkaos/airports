from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.airports import get_airports
from app.config import settings
from app.models import AirportsResponse

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app = FastAPI(
    title="Airports",
    description="Airport locations, local times, and weekend status",
    version="2.0.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/table")


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


@app.get("/api/airports", response_model=AirportsResponse)
async def airports(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return get_airports()


@app.get("/api/config")
async def get_client_config():
    return {"refresh_interval_seconds": 60, "kiosk_dwell_seconds": settings.KIOSK_DWELL_SECONDS}


@app.get("/api/cesium-token")
async def get_cesium_token():
    return {"token": settings.CESIUM_ION_TOKEN}


@app.get("/table", include_in_schema=False)
async def table_page():
    return FileResponse(STATIC_DIR / "table.html")


@app.get("/globe", include_in_schema=False)
async def globe_page():
    return FileResponse(STATIC_DIR / "globe.html")
