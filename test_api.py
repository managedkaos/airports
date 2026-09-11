from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from httpx2 import ASGITransport, AsyncClient

from app.airports import AIRPORTS
from app.config import settings
from app.main import app


@asynccontextmanager
async def api_client():
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver", follow_redirects=True) as client,
    ):
        yield client


async def test_startup_and_data_without_network():
    with patch("socket.create_connection", side_effect=AssertionError("Unexpected network request")):
        async with api_client() as client:
            health = await client.get("/health")
            assert health.status_code == 200
            assert set(health.json()) == {"status", "timestamp"}
            assert health.json()["status"] == "ok"
            response = await client.get("/api/airports")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    data = response.json()
    assert set(data) == {"results", "count", "generated_at"}
    assert data["count"] == len(AIRPORTS)
    assert [row["code"] for row in data["results"]] == sorted(AIRPORTS)
    instant = datetime.fromisoformat(data["generated_at"])
    for row in data["results"]:
        local = datetime.fromisoformat(row["local_time"])
        assert local.astimezone(UTC) == instant
        assert row["is_weekend"] == (local.weekday() >= 5)
        assert row["timezone"] == AIRPORTS[row["code"]].timezone
        assert set(row) == {
            "code",
            "name",
            "city",
            "country",
            "latitude",
            "longitude",
            "timezone",
            "local_time",
            "is_weekend",
        }


async def test_pages_and_retired_routes():
    async with api_client() as client:
        response = await client.get("/", follow_redirects=False)
        assert response.headers["location"] == "/table"
        for page in ("/table", "/globe"):
            response = await client.get(page)
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            assert "Airports" in response.text
            assert "Traffic Labeler" not in response.text
        for path in ("/api/labels", "/api/legend"):
            assert (await client.get(path)).status_code == 404
        for path in ("/static/js/common.js", "/static/js/table.js", "/static/js/globe.js", "/static/css/styles.css"):
            assert (await client.get(path)).status_code == 200
        assert (await client.get("/openapi.json")).json()["info"]["title"] == "Airports"


@pytest.mark.parametrize("dwell_seconds", [60, 10, 2.5])
async def test_client_configuration(dwell_seconds):
    with patch("app.main.settings", replace(settings, KIOSK_DWELL_SECONDS=dwell_seconds)):
        async with api_client() as client:
            assert (await client.get("/api/config")).json() == {
                "refresh_interval_seconds": 60,
                "kiosk_dwell_seconds": dwell_seconds,
            }
            assert (await client.get("/api/cesium-token")).json() == {"token": settings.CESIUM_ION_TOKEN}
