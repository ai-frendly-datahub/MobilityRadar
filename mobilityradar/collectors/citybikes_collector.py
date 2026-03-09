from __future__ import annotations
from typing import Optional

from datetime import datetime, timezone

import requests

from ..models import Article, Source

_NETWORKS_TIMEOUT = 20
_DEFAULT_HEADERS = {"User-Agent": "MobilityRadar/1.0 (+https://github.com/zzragida/ai-frendly-datahub)"}


def collect_citybikes(source: Source, *, category: str, limit: int, timeout: int) -> list[Article]:
    """Collect bike-sharing network snapshots from the CityBikes public API."""
    response = requests.get(source.url, timeout=max(timeout, _NETWORKS_TIMEOUT), headers=_DEFAULT_HEADERS)
    response.raise_for_status()

    payload = response.json()
    raw_networks = payload.get("networks", []) if isinstance(payload, dict) else []

    if not isinstance(raw_networks, list):
        return []

    focus_cities = _parse_focus_cities(source)
    networks = _rank_networks(raw_networks, focus_cities)

    effective_limit = _resolve_limit(limit, source.options.get("limit"))

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
    value = source.options.get("focus_cities")
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


def _network_to_article(network: dict[str, object], *, source: Source, category: str) -> Optional[Article]:
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
        f"Bike-share network in {city}, {country}." if country else f"Bike-share network in {city}.",
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
        published=datetime.now(timezone.utc),
        source=source.name,
        category=category,
    )
