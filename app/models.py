from datetime import datetime

from pydantic import BaseModel


class Airport(BaseModel):
    code: str
    name: str
    city: str
    country: str
    latitude: float
    longitude: float
    timezone: str
    local_time: datetime
    is_weekend: bool


class AirportsResponse(BaseModel):
    results: list[Airport]
    count: int
    generated_at: datetime
