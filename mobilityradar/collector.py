from __future__ import annotations

import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, List, Mapping, Tuple, cast

import feedparser
import requests

from .collectors.citybikes_collector import collect_citybikes
from .models import Article, Source

_DEFAULT_HEADERS = {
    "User-Agent": "MobilityRadar/1.0 (+https://github.com/zzragida/ai-frendly-datahub)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


def collect_sources(
    sources: List[Source],
    *,
    category: str,
    limit_per_source: int = 30,
    timeout: int = 15,
) -> Tuple[List[Article], List[str]]:
    """Fetch items from all configured sources, returning articles and errors."""
    articles: List[Article] = []
    errors: List[str] = []

    for source in sources:
        try:
            articles.extend(_collect_single(source, category=category, limit=limit_per_source, timeout=timeout))
        except Exception as exc:  # noqa: BLE001 - surface errors to the caller
            errors.append(f"{source.name}: {exc}")

    return articles, errors


def _collect_single(
    source: Source,
    *,
    category: str,
    limit: int,
    timeout: int,
) -> List[Article]:
    source_type = source.type.lower()
    if source_type == "citybikes":
        return collect_citybikes(source, category=category, limit=limit, timeout=timeout)
    if source_type != "rss":
        raise ValueError(f"Unsupported source type '{source.type}'. Supported: 'rss', 'citybikes'.")

    response = requests.get(source.url, timeout=timeout, headers=_DEFAULT_HEADERS)
    response.raise_for_status()

    feed = feedparser.parse(response.content)
    items: List[Article] = []

    for raw_entry in feed.entries[:limit]:
        entry = cast(Mapping[str, Any], raw_entry)
        published = _extract_datetime(entry)
        summary = entry.get("summary", "") or entry.get("description", "") or ""

        items.append(
            Article(
                title=str(entry.get("title") or "").strip() or "(no title)",
                link=str(entry.get("link") or "").strip(),
                summary=str(summary).strip(),
                published=published,
                source=source.name,
                category=category,
            )
        )

    return items


def _extract_datetime(entry: Mapping[str, Any]) -> datetime | None:
    """Parse a feed entry date into a timezone-aware datetime."""
    published_parsed = entry.get("published_parsed")
    if published_parsed:
        return datetime.fromtimestamp(time.mktime(cast(time.struct_time, published_parsed)), tz=timezone.utc)

    updated_parsed = entry.get("updated_parsed")
    if updated_parsed:
        return datetime.fromtimestamp(time.mktime(cast(time.struct_time, updated_parsed)), tz=timezone.utc)

    for key in ("published", "updated", "date"):
        raw = entry.get(key)
        if raw:
            try:
                dt = parsedate_to_datetime(str(raw))
                if dt and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                continue
    return None
