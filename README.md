# Airports

Airports shows airport locations, current local date and time, time zones, and
Weekend/Weekday status in a searchable table and an interactive 3D globe.
It runs as a standalone FastAPI application: airport data and time calculations
require no external service. The globe loads CesiumJS and OpenStreetMap imagery
over the internet.

## Features

- Table with airport code, city/country, airport name, local date/time, IANA time
  zone and UTC offset, and Weekend/Weekday status.
- Search by code, airport name, city, or country; sort by code or city.
- Globe with airport markers, detail drawer, region shortcuts, zoom, and an
  automatic kiosk tour through every airport in code order.
- Refresh on page load, every 60 seconds, when returning to the tab, or manually.
  Failed refreshes retain the displayed values with an explicit last-updated warning.
- Local times calculated from one server UTC instant with Python `zoneinfo`.
  Daylight-saving changes use installed time-zone rules. Weekend means Saturday
  or Sunday at the airport, not the browser or server location; holidays and
  country-specific working calendars are not modeled.

## Run locally

Requires Python 3.12+ and `uv` (or `pip`). From the project directory:

```bash
uv venv "$HOME/Envs/airports" --python 3.12
uv pip install --python "$HOME/Envs/airports/bin/python" -r requirements-development.txt
make run
```

The Makefile defaults to `http://localhost:8181/table` and
`http://localhost:8181/globe`. `/` redirects to the table.
To use a project-local environment instead:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-development.txt
make run VENV="$PWD/.venv"
make test VENV="$PWD/.venv"
make lint VENV="$PWD/.venv"
```

`make test` runs the Python tests; `make lint` checks Python formatting and lint.
`make format` applies Python formatting and lint fixes. With Node.js installed,
run frontend behavior tests using `node --test test_frontend.cjs`.

## Airport catalog

The initial catalog contains BOG, EZE, GRU, ICN, JFK, LAX, LHR, MIA, MRS, ORD,
SCL, and SYD. All data lives in `app/airports.py`, in `AIRPORT_CATALOG`.

### Add an airport

1. Confirm its three-letter IATA code, full name, city, country, decimal latitude
   and longitude, and IANA time zone. Use a regional zone such as
   `Asia/Tokyo`, not an abbreviation or fixed UTC offset, so seasonal rules work.
2. Add an `AirportInfo` entry inside the catalog tuple. For example:

   ```python
   AirportInfo(
       code="HND",
       name="Tokyo Haneda Airport",
       city="Tokyo",
       country="Japan",
       latitude=35.5494,
       longitude=139.7798,
       timezone="Asia/Tokyo",
   ),
   ```

3. Run `make test` and `make lint`. Startup validates uppercase three-letter
   codes, uniqueness, nonblank names/cities/countries, coordinate bounds, and
   resolvable time zones. Invalid entries stop startup with an error.
4. Restart the server (or rebuild the container) and refresh the browser.
   The airport appears in the table, globe, count, and kiosk tour automatically;
   no JavaScript edits or hard-coded count changes are needed.

Use negative latitude for south and negative longitude for west. Keep the system
clock and installed time-zone database current. The `tzdata` dependency supplies
a portable fallback on systems without an OS time-zone database.

## Configuration

| Setting | Default | Purpose |
|---------|---------|---------|
| `KIOSK_DWELL_SECONDS` | `60` | Pause after each kiosk camera flight, in seconds |
| `CESIUM_ION_TOKEN` | empty | Optional browser-visible Cesium token; OSM imagery needs no token |
| Makefile `PORT` | `8181` | Local server port or published container port |
| Makefile `VENV` | `~/Envs/airports` | Python environment containing application and development dependencies |
| Makefile `IMAGE_NAME` / `IMAGE_TAG` | `airports` / `latest` | Container image name and tag |

```bash
make run PORT=8080 KIOSK_DWELL_SECONDS=10
```

Kiosk flights take 1.5 seconds, then pause for the configured dwell time. The
browser uses 60 seconds if client configuration is unavailable or the dwell
value is invalid. Selecting an airport, closing its drawer, using region/zoom
controls, or cancelling a tour flight stops the tour. Restart and refresh after
changing configuration. Configure variables in the shell; `.env` files are not
automatically loaded.

## Docker

The public Python base image is the `local` target. `make build` runs Python
checks and builds that target:

```bash
make build
make docker-run
```

Equivalent explicit build and run commands:

```bash
docker build --target local -t airports:latest .
docker run --rm -p 8181:8000 -e KIOSK_DWELL_SECONDS=60 airports:latest
```

The container listens on port 8000 and checks `/health`. The separate `ci` stage
retains its internal Rocky Linux registry base; building without `--target local`
selects that stage and requires access to the internal registry.

## Application endpoints

- `GET /api/airports`: uncached snapshot with `results`, `count`, and UTC
  `generated_at`. Each result contains `code`, `name`, `city`, `country`,
  `latitude`, `longitude`, `timezone`, offset-aware `local_time`, and `is_weekend`.
- `GET /health`: application `status` and UTC `timestamp`.
- `GET /api/config`: refresh interval and kiosk dwell time.
- `GET /api/cesium-token`: optional browser-visible Cesium token.
- `GET /table`, `GET /globe`: application views.
- `GET /docs`: interactive API documentation.

The former `/api/labels` and `/api/legend` endpoints have been removed.
There is no upstream connection, prediction model, or server-side data cache.
