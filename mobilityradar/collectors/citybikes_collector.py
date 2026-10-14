from __future__ import annotations

from datetime import UTC, datetime

import requests

from ..models import Article, Source

_NETWORKS_TIMEOUT = 45
_DEFAULT_HEADERS = {
    "User-Agent": "MobilityRadar/0.1 (+https://github.com/ai-frendly-datahub/MobilityRadar; public-rss)",
    "Accept": "application/json",
}


def _source_config(source: Source) -> dict[str, object]:
    config = source.config if isinstance(source.config, dict) else {}
    options = getattr(source, "options", None)
    if isinstance(options, dict):
        merged = dict(options)
        merged.update(config)
        return merged
    return config


def collect_citybikes(source: Source, *, category: str, limit: int, timeout: int) -> list[Article]:
    """Collect bike-sharing snapshots from the CityBikes public API.

    A failed request raises. This function does not invent station rows.
    """
    response = requests.get(
        source.url,
        timeout=max(timeout, _NETWORKS_TIMEOUT),
        headers=_DEFAULT_HEADERS,
        verify=True,
    )
    response.raise_for_status()

    payload = response.json()
    if isinstance(payload, dict) and isinstance(payload.get("network"), dict):
        article = _network_status_article(payload["network"], source=source, category=category)
        return [article] if article is not None else []

    raw_networks = payload.get("networks", []) if isinstance(payload, dict) else []

    if not isinstance(raw_networks, list):
        return []

    focus_cities = _parse_focus_cities(source)
    networks = _rank_networks(raw_networks, focus_cities)
    if focus_cities:
        networks = [
            network
            for network in networks
            if str((network.get("location") or {}).get("city") or "").strip().lower()
            in focus_cities
        ]

    effective_limit = _resolve_limit(limit, _source_config(source).get("limit"))

    articles: list[Article] = []
    for network in networks:
        if len(articles) >= effective_limit:
            break

        article = _network_to_article(network=network, source=source, category=category)
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
    value = _source_config(source).get("focus_cities")
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


def _network_status_article(
    network: dict[str, object], *, source: Source, category: str
) -> Article | None:
    """One availability row from a live CityBikes network payload."""
    article = _network_to_article(network, source=source, category=category)
    if article is None:
        return None

    stations = network.get("stations")
    if not isinstance(stations, list):
        return article

    free_bikes = 0
    empty_slots = 0
    station_count = 0
    latest_stamp: datetime | None = None
    for station in stations:
        if not isinstance(station, dict):
            continue
        station_count += 1
        free_raw = station.get("free_bikes")
        empty_raw = station.get("empty_slots")
        if isinstance(free_raw, int):
            free_bikes += free_raw
        if isinstance(empty_raw, int):
            empty_slots += empty_raw
        raw_ts = station.get("timestamp")
        if isinstance(raw_ts, str) and raw_ts.strip():
            raw_stamp = raw_ts.strip()
            if raw_stamp.endswith("Z") and ("+" in raw_stamp or "-" in raw_stamp[10:]):
                raw_stamp = raw_stamp[:-1]
            elif raw_stamp.endswith("Z"):
                raw_stamp = raw_stamp[:-1] + "+00:00"
            try:
                parsed = datetime.fromisoformat(raw_stamp)
            except ValueError:
                parsed = None
            if parsed is not None and (latest_stamp is None or parsed > latest_stamp):
                latest_stamp = parsed

    if station_count:
        article.summary = (
            f"{article.summary} Stations: {station_count}. "
            f"Free bikes: {free_bikes}. Empty slots: {empty_slots}."
        )
        if latest_stamp is not None:
            article.published = latest_stamp
    return article


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
        (
            f"Bike-share network in {city}, {country}."
            if country
            else f"Bike-share network in {city}."
        ),
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
