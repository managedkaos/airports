from dataclasses import replace
from datetime import UTC, datetime
from zoneinfo import ZoneInfoNotFoundError

import pytest

from app.airports import AIRPORT_CATALOG, AIRPORTS, get_airport, get_airports, validate_catalog


def test_catalog_and_lookup():
    assert {"BOG", "EZE", "GRU", "ICN", "JFK", "LAX", "LHR", "MIA", "MRS", "ORD", "SCL", "SYD"} <= AIRPORTS.keys()
    assert get_airport(" jfk ") == AIRPORTS["JFK"]
    assert get_airport("unknown") is None
    assert validate_catalog(AIRPORT_CATALOG) == AIRPORTS


@pytest.mark.parametrize(
    "changes",
    [
        {"code": "bad"},
        {"code": "ABCD"},
        {"name": " "},
        {"city": ""},
        {"country": ""},
        {"latitude": 91},
        {"longitude": -181},
        {"latitude": float("nan")},
    ],
)
def test_invalid_catalog_metadata(changes):
    with pytest.raises(ValueError):
        validate_catalog((replace(AIRPORT_CATALOG[0], **changes),))


def test_duplicate_codes_and_invalid_timezone():
    with pytest.raises(ValueError, match="Duplicate"):
        validate_catalog((AIRPORT_CATALOG[0], AIRPORT_CATALOG[0]))
    with pytest.raises(ZoneInfoNotFoundError):
        validate_catalog((replace(AIRPORT_CATALOG[0], timezone="Invalid/Zone"),))


@pytest.mark.parametrize(
    ("instant", "code", "local_time", "weekend"),
    [
        ("2026-09-12T03:59:00+00:00", "JFK", "2026-09-11T23:59:00-04:00", False),
        ("2026-09-12T04:00:00+00:00", "JFK", "2026-09-12T00:00:00-04:00", True),
        ("2026-09-14T03:59:00+00:00", "JFK", "2026-09-13T23:59:00-04:00", True),
        ("2026-09-14T04:00:00+00:00", "JFK", "2026-09-14T00:00:00-04:00", False),
        ("2026-03-08T06:59:00+00:00", "JFK", "2026-03-08T01:59:00-05:00", True),
        ("2026-03-08T07:00:00+00:00", "JFK", "2026-03-08T03:00:00-04:00", True),
        ("2026-11-01T05:30:00+00:00", "JFK", "2026-11-01T01:30:00-04:00", True),
        ("2026-11-01T06:30:00+00:00", "JFK", "2026-11-01T01:30:00-05:00", True),
        ("2026-04-04T15:59:00+00:00", "SYD", "2026-04-05T02:59:00+11:00", True),
        ("2026-04-04T16:00:00+00:00", "SYD", "2026-04-05T02:00:00+10:00", True),
        ("2026-01-01T00:00:00+00:00", "BOG", "2025-12-31T19:00:00-05:00", False),
    ],
)
def test_local_time_boundaries(instant, code, local_time, weekend):
    result = next(row for row in get_airports(datetime.fromisoformat(instant)).results if row.code == code)
    assert result.local_time.isoformat() == local_time
    assert result.is_weekend is weekend


def test_single_instant_different_local_dates():
    instant = datetime(2026, 9, 11, 23, 30, tzinfo=UTC)
    response = get_airports(instant)
    assert response.generated_at == instant
    assert all(row.local_time.astimezone(UTC) == instant for row in response.results)
    rows = {row.code: row for row in response.results}
    assert rows["JFK"].is_weekend is False
    assert rows["SYD"].is_weekend is True
    assert rows["JFK"].local_time.date() != rows["SYD"].local_time.date()


def test_naive_datetime_rejected():
    with pytest.raises(ValueError, match="aware"):
        get_airports(datetime(2026, 1, 1))


def test_catalog_extension(monkeypatch):
    airport = replace(AIRPORT_CATALOG[0], code="TST", name="Test Airport", timezone="Asia/Kathmandu")
    expanded = validate_catalog((*AIRPORT_CATALOG, airport))
    monkeypatch.setattr("app.airports.AIRPORTS", expanded)
    response = get_airports(datetime(2026, 1, 1, tzinfo=UTC))
    assert response.count == len(AIRPORT_CATALOG) + 1
    result = next(row for row in response.results if row.code == "TST")
    assert result.local_time.isoformat() == "2026-01-01T05:45:00+05:45"
