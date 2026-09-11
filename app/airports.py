import re
from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.models import Airport, AirportsResponse


@dataclass(frozen=True)
class AirportInfo:
    code: str
    name: str
    city: str
    country: str
    latitude: float
    longitude: float
    timezone: str


# Airport catalog: add entries here; both views and the kiosk tour use this dataset.
AIRPORT_CATALOG: tuple[AirportInfo, ...] = (
    AirportInfo(
        code="BOG",
        name="El Dorado International Airport",
        city="Bogotá",
        country="Colombia",
        latitude=4.7016,
        longitude=-74.1469,
        timezone="America/Bogota",
    ),
    AirportInfo(
        code="EZE",
        name="Ministro Pistarini International Airport",
        city="Buenos Aires",
        country="Argentina",
        latitude=-34.8222,
        longitude=-58.5358,
        timezone="America/Argentina/Buenos_Aires",
    ),
    AirportInfo(
        code="GRU",
        name="São Paulo/Guarulhos International Airport",
        city="São Paulo",
        country="Brazil",
        latitude=-23.4356,
        longitude=-46.4731,
        timezone="America/Sao_Paulo",
    ),
    AirportInfo(
        code="ICN",
        name="Incheon International Airport",
        city="Seoul / Incheon",
        country="South Korea",
        latitude=37.4602,
        longitude=126.4407,
        timezone="Asia/Seoul",
    ),
    AirportInfo(
        code="JFK",
        name="John F. Kennedy International Airport",
        city="New York",
        country="United States",
        latitude=40.6413,
        longitude=-73.7781,
        timezone="America/New_York",
    ),
    AirportInfo(
        code="LAX",
        name="Los Angeles International Airport",
        city="Los Angeles",
        country="United States",
        latitude=33.9416,
        longitude=-118.4085,
        timezone="America/Los_Angeles",
    ),
    AirportInfo(
        code="LHR",
        name="Heathrow Airport",
        city="London",
        country="United Kingdom",
        latitude=51.4700,
        longitude=-0.4543,
        timezone="Europe/London",
    ),
    AirportInfo(
        code="MIA",
        name="Miami International Airport",
        city="Miami",
        country="United States",
        latitude=25.7959,
        longitude=-80.2870,
        timezone="America/New_York",
    ),
    AirportInfo(
        code="MRS",
        name="Marseille Provence Airport",
        city="Marseille",
        country="France",
        latitude=43.4393,
        longitude=5.2214,
        timezone="Europe/Paris",
    ),
    AirportInfo(
        code="ORD",
        name="O'Hare International Airport",
        city="Chicago",
        country="United States",
        latitude=41.9742,
        longitude=-87.9073,
        timezone="America/Chicago",
    ),
    AirportInfo(
        code="SCL",
        name="Arturo Merino Benítez International Airport",
        city="Santiago",
        country="Chile",
        latitude=-33.3930,
        longitude=-70.7858,
        timezone="America/Santiago",
    ),
    AirportInfo(
        code="SYD",
        name="Sydney Kingsford Smith Airport",
        city="Sydney",
        country="Australia",
        latitude=-33.9399,
        longitude=151.1753,
        timezone="Australia/Sydney",
    ),
)


def validate_catalog(catalog: tuple[AirportInfo, ...]) -> dict[str, AirportInfo]:
    airports = {}
    for airport in catalog:
        if not re.fullmatch(r"[A-Z]{3}", airport.code):
            raise ValueError(f"Invalid airport code: {airport.code}")
        if airport.code in airports:
            raise ValueError(f"Duplicate airport code: {airport.code}")
        if not all(value.strip() for value in (airport.name, airport.city, airport.country)):
            raise ValueError(f"Missing metadata for {airport.code}")
        if not (-90 <= airport.latitude <= 90 and -180 <= airport.longitude <= 180):
            raise ValueError(f"Invalid coordinates for {airport.code}")
        ZoneInfo(airport.timezone)
        airports[airport.code] = airport
    return airports


AIRPORTS = validate_catalog(AIRPORT_CATALOG)


def get_airport(code: str) -> AirportInfo | None:
    """Look up an airport by code, ignoring case and surrounding whitespace."""
    return AIRPORTS.get(code.upper().strip())


def get_airports(now: datetime | None = None) -> AirportsResponse:
    """Calculate every airport's local time from the same aware instant."""
    instant = now if now is not None else datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("An aware datetime is required")
    results = []
    for code, airport in sorted(AIRPORTS.items()):
        local = instant.astimezone(ZoneInfo(airport.timezone))
        results.append(
            Airport(
                code=code,
                name=airport.name,
                city=airport.city,
                country=airport.country,
                latitude=airport.latitude,
                longitude=airport.longitude,
                timezone=airport.timezone,
                local_time=local,
                is_weekend=local.weekday() >= 5,
            )
        )
    return AirportsResponse(results=results, count=len(results), generated_at=instant.astimezone(UTC))
