from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import quote

import requests

from ..models import Article, Source


_NETWORKS_TIMEOUT = 20
_DEFAULT_HEADERS = {
    "User-Agent": "MobilityRadar/1.0 (+https://github.com/zzragida/ai-frendly-datahub)"
}


def collect_citybikes(source: Source, *, category: str, limit: int, timeout: int) -> list[Article]:
    """Collect bike-sharing network snapshots from the CityBikes public API."""
    response = requests.get(
        source.url, timeout=max(timeout, _NETWORKS_TIMEOUT), headers=_DEFAULT_HEADERS
    )
    response.raise_for_status()

    payload = response.json()
    if isinstance(payload, dict) and isinstance(payload.get("network"), dict):
        return _collect_station_snapshots(
            network=payload["network"],
            source=source,
            category=category,
            limit=limit,
        )

    raw_networks = payload.get("networks", []) if isinstance(payload, dict) else []

    if not isinstance(raw_networks, list):
        return []

    focus_cities = _parse_focus_cities(source)
    networks = _rank_networks(raw_networks, focus_cities)

    effective_limit = _resolve_limit(limit, source.config.get("limit"))

    articles: list[Article] = []
    for network in networks:
        if len(articles) >= effective_limit:
            break

        article = _network_to_article(network=network, source=source, category=category)
        if article is not None:
            articles.append(article)

    return articles


def _collect_station_snapshots(
    *,
    network: dict[str, object],
    source: Source,
    category: str,
    limit: int,
) -> list[Article]:
    stations_raw = network.get("stations")
    if not isinstance(stations_raw, list):
        return []

    effective_limit = _resolve_limit(limit, source.config.get("limit"))
    articles: list[Article] = []
    for station_raw in stations_raw:
        if len(articles) >= effective_limit:
            break
        if not isinstance(station_raw, dict):
            continue

        article = _station_to_article(
            station=station_raw,
            network=network,
            source=source,
            category=category,
        )
        if article is not None:
            articles.append(article)
    return articles


def _resolve_limit(default_limit: int, value: object) -> int:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str):
        try:
            parsed = int(value)
            if parsed > 0:
                return parsed
        except ValueError:
            return default_limit
    return default_limit


def _parse_focus_cities(source: Source) -> set[str]:
    value = source.config.get("focus_cities")
    if not isinstance(value, list):
        return set()
    return {str(city).strip().lower() for city in value if str(city).strip()}


def _rank_networks(raw_networks: list[object], focus_cities: set[str]) -> list[dict[str, object]]:
    ranked: list[tuple[int, dict[str, object]]] = []
    for idx, network_raw in enumerate(raw_networks):
        if not isinstance(network_raw, dict):
            continue

        location = network_raw.get("location")
        if not isinstance(location, dict):
            continue

        city = str(location.get("city") or "").strip()
        if not city:
            continue

        priority = 0 if city.lower() in focus_cities else 1
        ranked.append((priority * 10_000 + idx, network_raw))

    ranked.sort(key=lambda pair: pair[0])
    return [network for _, network in ranked]


def _station_to_article(
    station: dict[str, object],
    *,
    network: dict[str, object],
    source: Source,
    category: str,
) -> Article | None:
    station_id = str(station.get("id") or "").strip()
    station_name = str(station.get("name") or "").strip()
    if not station_id or not station_name:
        return None

    network_name = str(network.get("name") or "").strip() or "CityBikes Network"
    location = network.get("location")
    city = ""
    country = ""
    if isinstance(location, dict):
        city = str(location.get("city") or "").strip()
        country = str(location.get("country") or "").strip()

    free_bikes = station.get("free_bikes")
    empty_slots = station.get("empty_slots")
    status = _station_status(free_bikes=free_bikes, empty_slots=empty_slots)
    observed_at = _parse_station_timestamp(station.get("timestamp"))
    link = f"{source.url.rstrip('/')}#station-{quote(station_id, safe='')}"

    summary = (
        f"Station ID: {station_id}. "
        f"Station name: {station_name}. "
        f"Network: {network_name}. "
        f"Location: {city}, {country}. "
        f"Free bikes: {_display_value(free_bikes)}. "
        f"Empty slots: {_display_value(empty_slots)}. "
        f"Availability status: {status}. "
        f"Observed at: {observed_at.isoformat() if observed_at else 'unknown'}."
    )

    return Article(
        title=f"{station_name} station availability - {network_name}",
        link=link,
        summary=summary,
        published=observed_at or datetime.now(UTC),
        source=source.name,
        category=category,
    )


def _station_status(*, free_bikes: object, empty_slots: object) -> str:
    free_count = _int_value(free_bikes)
    empty_count = _int_value(empty_slots)
    if free_count is None and empty_count is None:
        return "unknown"
    if free_count and empty_count:
        return "bikes_and_docks_available"
    if free_count:
        return "bikes_available"
    if empty_count:
        return "docks_available"
    return "no_capacity_reported"


def _parse_station_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _int_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _display_value(value: object) -> str:
    parsed = _int_value(value)
    return str(parsed) if parsed is not None else "unknown"


def _network_to_article(
    network: dict[str, object], *, source: Source, category: str
) -> Article | None:
    network_id = str(network.get("id") or "").strip()
    network_name = str(network.get("name") or "").strip() or "CityBikes Network"

    location_raw = network.get("location")
    if not isinstance(location_raw, dict):
        return None

    city = str(location_raw.get("city") or "").strip()
    country = str(location_raw.get("country") or "").strip()
    latitude = location_raw.get("latitude")
    longitude = location_raw.get("longitude")

    href = str(network.get("href") or "").strip()
    if href.startswith("/v2/"):
        link = f"https://api.citybik.es{href}"
    elif href:
        link = href
    elif network_id:
        link = f"https://api.citybik.es/v2/networks/{network_id}"
    else:
        return None

    company_raw = network.get("company")
    companies: list[str] = []
    if isinstance(company_raw, list):
        companies = [str(item).strip() for item in company_raw if str(item).strip()]
    elif isinstance(company_raw, str) and company_raw.strip():
        companies = [company_raw.strip()]

    summary_parts = [
        f"Bike-share network in {city}, {country}."
        if country
        else f"Bike-share network in {city}.",
        f"Coordinates: {latitude}, {longitude}.",
    ]
    if companies:
        summary_parts.append(f"Operator: {', '.join(companies)}.")
    summary_parts.append("Data source: CityBikes public API.")

    title_city = f"{city} ({country})" if country else city
    return Article(
        title=f"{title_city} bike-share status - {network_name}",
        link=link,
        summary=" ".join(summary_parts),
        published=datetime.now(UTC),
        source=source.name,
        category=category,
    )
