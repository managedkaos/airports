from datetime import UTC, datetime
from pathlib import Path
from secrets import token_urlsafe

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.airports import get_airports
from app.auth.dependencies import current_user
from app.auth.routes import CSRF_COOKIE_NAME
from app.auth.routes import router as auth_router
from app.config import settings
from app.models import AirportsResponse

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app = FastAPI(
    title="Airports",
    description="Airport locations, local times, and weekend status",
    version="2.0.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(auth_router)

# Paths reachable without authentication.
_PUBLIC_EXACT = {"/health", "/login", "/api/auth-config", "/favicon.ico", "/openapi.json"}
_PUBLIC_PREFIXES = ("/auth/", "/static/", "/docs", "/redoc")


def _is_public(path: str) -> bool:
    return path in _PUBLIC_EXACT or path.startswith(_PUBLIC_PREFIXES)


@app.middleware("http")
async def enforce_auth(request: Request, call_next):
    """Gate the whole app: redirect pages to /login and 401 the API when
    unauthenticated. Honors AUTH_ENABLED and the public path allowlist."""
    path = request.url.path
    if not settings.AUTH_ENABLED or _is_public(path):
        return await call_next(request)

    if current_user(request) is not None:
        return await call_next(request)

    if path.startswith("/api/"):
        return JSONResponse({"detail": "Authentication required"}, status_code=401)
    return RedirectResponse(url="/login", status_code=302)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/table")


@app.get("/login", include_in_schema=False)
async def login_page():
    """Public login landing page. Sets a CSRF token cookie for the sign-in POST."""
    response = FileResponse(STATIC_DIR / "login.html")
    # Double-submit CSRF token: readable by JS (not HttpOnly) so the client can
    # echo it back in the /auth/session request body.
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token_urlsafe(32),
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return response


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
