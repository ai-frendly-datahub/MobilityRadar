from __future__ import annotations

import json
import hashlib
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import Article, CategoryConfig, Source


TRACKED_EVENT_MODEL_ORDER = [
    "station_availability_snapshot",
    "charger_availability_snapshot",
    "transport_service_notice",
    "fare_payment_policy_change",
]
TRACKED_EVENT_MODELS = set(TRACKED_EVENT_MODEL_ORDER)
SUMMARY_LABELS = [
    "Station ID",
    "Station name",
    "Network",
    "Location",
    "Free bikes",
    "Empty slots",
    "Availability status",
    "Observed at",
    "Charger ID",
]


def build_quality_report(
    *,
    category: CategoryConfig,
    articles: Iterable[Article],
    errors: Iterable[str] | None = None,
    quality_config: Mapping[str, object] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    generated = _as_utc(generated_at or datetime.now(UTC))
    articles_list = list(articles)
    errors_list = [str(error) for error in (errors or [])]
    quality = _dict(quality_config or {}, "data_quality")
    freshness_sla = _dict(quality, "freshness_sla")
    tracked_event_models = _tracked_event_models(quality)

    event_rows = _build_event_rows(articles_list, category.sources, tracked_event_models)
    source_rows = [
        _build_source_row(
            source=source,
            articles=articles_list,
            event_rows=event_rows,
            errors=errors_list,
            freshness_sla=freshness_sla,
            tracked_event_models=tracked_event_models,
            generated_at=generated,
        )
        for source in category.sources
    ]

    status_counts = Counter(str(row["status"]) for row in source_rows)
    event_counts = Counter(str(row["event_model"]) for row in event_rows)
    summary = {
        "total_sources": len(source_rows),
        "enabled_sources": sum(1 for row in source_rows if row["enabled"]),
        "tracked_sources": sum(1 for row in source_rows if row["tracked"]),
        "fresh_sources": status_counts.get("fresh", 0),
        "stale_sources": status_counts.get("stale", 0),
        "missing_sources": status_counts.get("missing", 0),
        "missing_event_sources": status_counts.get("missing_event", 0),
        "unknown_event_date_sources": status_counts.get("unknown_event_date", 0),
        "not_tracked_sources": status_counts.get("not_tracked", 0),
        "skipped_disabled_sources": status_counts.get("skipped_disabled", 0),
        "collection_error_count": len(errors_list),
    }
    for event_model in TRACKED_EVENT_MODEL_ORDER:
        summary[f"{event_model}_events"] = event_counts.get(event_model, 0)
    summary.update(_event_quality_summary(event_rows, source_rows))
    summary["disabled_official_source_count"] = sum(
        1 for row in source_rows if _is_official_source_row(row) and not row.get("enabled")
    )
    summary["tracked_event_model_gap_count"] = len(
        _tracked_event_model_gaps(event_rows, source_rows)
    )
    summary["operational_candidate_count"] = len(_operational_candidates(quality_config))
    daily_review_items = _daily_review_items(event_rows, source_rows)
    summary["daily_review_item_count"] = len(daily_review_items)

    return {
        "category": category.category_name,
        "generated_at": generated.isoformat(),
        "scope_note": (
            "Operational station, charger, transport notice, and fare/payment "
            "sources are tracked separately from broad EV/media/community context. "
            "Coffee split-candidate sources are excluded by domain_scope."
        ),
        "summary": summary,
        "sources": source_rows,
        "events": event_rows,
        "daily_review_items": daily_review_items,
        "source_backlog": (quality_config or {}).get("source_backlog", {}),
        "errors": errors_list,
    }


def write_quality_report(
    report: Mapping[str, object],
    *,
    output_dir: Path,
    category_name: str,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = _parse_datetime(str(report.get("generated_at") or "")) or datetime.now(UTC)
    date_stamp = _as_utc(generated_at).strftime("%Y%m%d")
    latest_path = output_dir / f"{category_name}_quality.json"
    dated_path = output_dir / f"{category_name}_{date_stamp}_quality.json"
    encoded = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    latest_path.write_text(encoded + "\n", encoding="utf-8")
    dated_path.write_text(encoded + "\n", encoding="utf-8")
    return {"latest": latest_path, "dated": dated_path}


def _build_event_rows(
    articles: list[Article],
    sources: list[Source],
    tracked_event_models: set[str],
) -> list[dict[str, Any]]:
    source_map = {source.name: source for source in sources}
    rows: list[dict[str, Any]] = []
    for article in articles:
        source = source_map.get(article.source)
        if source is None or not source.enabled:
            continue
        event_model = _source_event_model(source)
        if event_model not in tracked_event_models:
            continue
        event_at = (
            _as_utc(article.published or article.collected_at)
            if (article.published or article.collected_at)
            else None
        )
        event_row = _event_row(
            article=article,
            source=source,
            event_model=event_model,
            event_at=event_at,
        )
        rows.append(event_row)
    return rows


def _event_row(
    *,
    article: Article,
    source: Source,
    event_model: str,
    event_at: datetime | None,
) -> dict[str, Any]:
    station_id = _first_non_empty(
        _summary_value(article.summary, "Station ID"),
        _fragment_value(article.link, "station-"),
    )
    station_name = _summary_value(article.summary, "Station name")
    availability_status = _summary_value(article.summary, "Availability status")
    observed_at = _summary_value(article.summary, "Observed at")
    network = _summary_value(article.summary, "Network")
    location = _summary_value(article.summary, "Location")
    free_bikes = _summary_value(article.summary, "Free bikes")
    empty_slots = _summary_value(article.summary, "Empty slots")
    operator = _operator(source, network)
    charger_id = _first_non_empty(
        _summary_value(article.summary, "Charger ID"),
        _first_match(article.summary, r"\bcharger[_\s-]*id[:\s#-]+([A-Za-z0-9_.:-]+)"),
    )
    connector_type = _first_match(
        article.summary,
        r"\b(CCS|CHAdeMO|NACS|Type\s*1|Type\s*2|AC|DC)\b",
    )
    payment_program = _payment_program(article)
    route_or_service = _route_or_service(article)
    source_url = article.link
    district = _district(location)
    canonical_key = _canonical_key(
        event_model=event_model,
        station_id=station_id,
        station_name=station_name,
        district=district,
        operator=operator,
        charger_id=charger_id,
        connector_type=connector_type,
        payment_program=payment_program,
        effective_date=_event_date_text(event_at),
    )
    row: dict[str, Any] = {
        "source": article.source,
        "domain_scope": source.config.get("domain_scope", ""),
        "event_model": event_model,
        "title": article.title,
        "url": article.link,
        "event_at": event_at.isoformat() if event_at else None,
        "observed_at": observed_at if observed_at and observed_at != "unknown" else None,
        "station_id": station_id,
        "station_name": station_name,
        "district": district,
        "operator": operator,
        "availability_status": availability_status,
        "free_bikes": _int_value(free_bikes),
        "empty_slots": _int_value(empty_slots),
        "charger_id": charger_id,
        "connector_type": connector_type,
        "status": availability_status if event_model == "charger_availability_snapshot" else None,
        "payment_program": payment_program,
        "route_or_service": route_or_service,
        "source_url": source_url,
        "canonical_key": canonical_key,
        "canonical_key_status": "complete" if canonical_key else "missing",
        "event_key": _event_key(event_model, canonical_key, article.link, event_at),
        "vehicle_type": _matches(article, "VehicleType"),
        "charging_infra": _matches(article, "ChargingInfra"),
        "regulation": _matches(article, "Regulation"),
        "service": _matches(article, "Service"),
        "ev_model": _matches(article, "EVModel"),
        "manufacturer": _matches(article, "Manufacturer"),
        "source_signal": _matches(article, "SourceSignal"),
    }
    row["required_field_gaps"] = _required_field_gaps(row, event_model)
    return row


def _build_source_row(
    *,
    source: Source,
    articles: list[Article],
    event_rows: list[dict[str, Any]],
    errors: list[str],
    freshness_sla: Mapping[str, object],
    tracked_event_models: set[str],
    generated_at: datetime,
) -> dict[str, Any]:
    source_articles = [article for article in articles if article.source == source.name]
    source_errors = [error for error in errors if error.startswith(f"{source.name}:")]
    event_model = _source_event_model(source)
    source_event_rows = [
        row
        for row in event_rows
        if row["source"] == source.name and row["event_model"] == event_model
    ]
    latest_event = _latest_event(source_event_rows)
    latest_event_at = _parse_datetime(str(latest_event.get("event_at") or "")) if latest_event else None
    sla_days = _source_sla_days(source, event_model, freshness_sla)
    age_days = _age_days(generated_at, latest_event_at) if latest_event_at else None
    status = _source_status(
        source=source,
        event_model=event_model,
        tracked_event_models=tracked_event_models,
        article_count=len(source_articles),
        event_count=len(source_event_rows),
        latest_event_at=latest_event_at,
        sla_days=sla_days,
        age_days=age_days,
    )

    return {
        "source": source.name,
        "source_type": source.type,
        "enabled": source.enabled,
        "trust_tier": source.trust_tier,
        "content_type": source.content_type,
        "collection_tier": source.collection_tier,
        "producer_role": source.producer_role,
        "info_purpose": source.info_purpose,
        "notes": source.notes,
        "domain_scope": source.config.get("domain_scope", ""),
        "tracked": event_model in tracked_event_models,
        "event_model": event_model,
        "freshness_sla_days": sla_days,
        "status": status,
        "article_count": len(source_articles),
        "event_count": len(source_event_rows),
        "latest_event_at": latest_event_at.isoformat() if latest_event_at else None,
        "age_days": round(age_days, 2) if age_days is not None else None,
        "latest_title": str(latest_event.get("title", "")) if latest_event else "",
        "latest_url": str(latest_event.get("url", "")) if latest_event else "",
        "latest_source_signal": latest_event.get("source_signal", []) if latest_event else [],
        "latest_canonical_key": latest_event.get("canonical_key") if latest_event else "",
        "latest_required_field_gaps": latest_event.get("required_field_gaps", [])
        if latest_event
        else [],
        "errors": source_errors,
    }


def _source_status(
    *,
    source: Source,
    event_model: str,
    tracked_event_models: set[str],
    article_count: int,
    event_count: int,
    latest_event_at: datetime | None,
    sla_days: float | None,
    age_days: float | None,
) -> str:
    if not source.enabled:
        return "skipped_disabled"
    if event_model not in tracked_event_models:
        return "not_tracked"
    if article_count == 0:
        return "missing"
    if event_count == 0:
        return "missing_event"
    if latest_event_at is None or age_days is None:
        return "unknown_event_date"
    if sla_days is not None and age_days > sla_days:
        return "stale"
    return "fresh"


def _tracked_event_models(quality: Mapping[str, object]) -> set[str]:
    outputs = _dict(quality, "quality_outputs")
    raw = outputs.get("tracked_event_models")
    if isinstance(raw, list):
        values = {str(item).strip() for item in raw if str(item).strip()}
        return values & TRACKED_EVENT_MODELS or set(TRACKED_EVENT_MODELS)
    return set(TRACKED_EVENT_MODELS)


def _source_event_model(source: Source) -> str:
    raw = source.config.get("event_model")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    content_type = source.content_type.lower()
    if content_type == "station_availability":
        return "station_availability_snapshot"
    if content_type == "charger_availability":
        return "charger_availability_snapshot"
    if content_type == "transport_service_notice":
        return "transport_service_notice"
    if content_type == "fare_payment_policy":
        return "fare_payment_policy_change"
    return ""


def _source_sla_days(
    source: Source,
    event_model: str,
    freshness_sla: Mapping[str, object],
) -> float | None:
    raw_source_sla = source.config.get("freshness_sla_days")
    parsed_source_sla = _as_float(raw_source_sla)
    if parsed_source_sla is not None:
        return parsed_source_sla

    suffixed_days = _as_float(freshness_sla.get(f"{event_model}_days"))
    if suffixed_days is not None:
        return suffixed_days

    suffixed_hours = _as_float(freshness_sla.get(f"{event_model}_hours"))
    if suffixed_hours is not None:
        return suffixed_hours / 24
    return None


def _latest_event(event_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    dated: list[tuple[datetime, dict[str, Any]]] = []
    undated: list[dict[str, Any]] = []
    for row in event_rows:
        event_at = _parse_datetime(str(row.get("event_at") or ""))
        if event_at is not None:
            dated.append((event_at, row))
        else:
            undated.append(row)
    if dated:
        return max(dated, key=lambda item: item[0])[1]
    return undated[0] if undated else None


def _event_quality_summary(
    event_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    availability_events = [
        row
        for row in event_rows
        if row.get("event_model")
        in {"station_availability_snapshot", "charger_availability_snapshot"}
    ]
    station_events = [
        row for row in event_rows if row.get("event_model") == "station_availability_snapshot"
    ]
    charger_events = [
        row for row in event_rows if row.get("event_model") == "charger_availability_snapshot"
    ]
    return {
        "mobility_domain_scope_source_count": sum(
            1 for row in source_rows if row.get("domain_scope") == "mobility"
        ),
        "non_mobility_domain_scope_source_count": sum(
            1
            for row in source_rows
            if row.get("enabled") and row.get("domain_scope") not in {"", "mobility"}
        ),
        "coffee_split_candidate_event_count": sum(
            1 for row in event_rows if row.get("domain_scope") == "coffee"
        ),
        "operational_depth_event_count": len(event_rows),
        "availability_snapshot_event_count": len(availability_events),
        "station_canonical_key_present_count": sum(
            1 for row in station_events if row.get("canonical_key")
        ),
        "charger_canonical_key_present_count": sum(
            1 for row in charger_events if row.get("canonical_key")
        ),
        "missing_canonical_key_count": sum(
            1 for row in event_rows if not row.get("canonical_key")
        ),
        "availability_status_present_count": sum(
            1 for row in availability_events if row.get("availability_status") or row.get("status")
        ),
        "event_required_field_gap_count": sum(
            len(row.get("required_field_gaps", [])) for row in event_rows
        ),
    }


def _daily_review_items(
    event_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    review_items: list[dict[str, Any]] = []
    for row in event_rows:
        gaps = row.get("required_field_gaps")
        if isinstance(gaps, list) and gaps:
            review_items.append(
                {
                    "reason": "missing_required_fields",
                    "event_model": row.get("event_model"),
                    "source": row.get("source"),
                    "title": row.get("title"),
                    "event_key": row.get("event_key"),
                    "required_field_gaps": gaps,
                }
            )
        if row.get("canonical_key_status") == "missing":
            review_items.append(
                {
                    "reason": "missing_canonical_key",
                    "event_model": row.get("event_model"),
                    "source": row.get("source"),
                    "title": row.get("title"),
                    "event_key": row.get("event_key"),
                }
            )
        if row.get("domain_scope") not in {"", "mobility"}:
            review_items.append(
                {
                    "reason": "non_mobility_domain_scope",
                    "event_model": row.get("event_model"),
                    "source": row.get("source"),
                    "domain_scope": row.get("domain_scope"),
                    "event_key": row.get("event_key"),
                }
            )

    for row in source_rows:
        if row.get("enabled") and row.get("domain_scope") not in {"", "mobility"}:
            review_items.append(
                {
                    "reason": "source_scope_not_mobility",
                    "source": row.get("source"),
                    "domain_scope": row.get("domain_scope"),
                    "status": row.get("status"),
                }
            )
        if _is_official_source_row(row) and not row.get("enabled") and row.get("tracked"):
            review_items.append(
                {
                    "reason": "disabled_official_source",
                    "event_model": row.get("event_model"),
                    "source": row.get("source"),
                    "detail": row.get("notes") or row.get("content_type") or "",
                }
            )

    for event_model, sources in _tracked_event_model_gaps(event_rows, source_rows):
        review_items.append(
            {
                "reason": "tracked_event_model_without_live_signal",
                "event_model": event_model,
                "source": ", ".join(sources[:3]),
                "detail": "no observed operational rows for tracked model",
            }
        )
    return review_items[:50]


def _tracked_event_model_gaps(
    event_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
) -> list[tuple[str, list[str]]]:
    observed_models = {str(row.get("event_model") or "") for row in event_rows}
    missing: list[tuple[str, list[str]]] = []
    tracked_models = sorted(
        {
            str(row.get("event_model") or "")
            for row in source_rows
            if row.get("enabled") and row.get("tracked") and str(row.get("event_model") or "")
        }
    )
    for event_model in tracked_models:
        if event_model in observed_models:
            continue
        missing.append(
            (
                event_model,
                [
                    str(row.get("source") or "")
                    for row in source_rows
                    if row.get("enabled") and row.get("event_model") == event_model
                ],
            )
        )
    return missing


def _is_official_source_row(row: Mapping[str, Any]) -> bool:
    trust_tier = str(row.get("trust_tier") or "").lower()
    return trust_tier.startswith("t1")


def _operational_candidates(quality_config: Mapping[str, object] | None) -> list[Mapping[str, object]]:
    backlog = (
        quality_config.get("source_backlog")
        if isinstance(quality_config, Mapping)
        else {}
    )
    if not isinstance(backlog, Mapping):
        return []
    candidates = backlog.get("operational_candidates")
    if not isinstance(candidates, list):
        return []
    return [item for item in candidates if isinstance(item, Mapping)]


def _required_field_gaps(row: Mapping[str, Any], event_model: str) -> list[str]:
    required_by_model = {
        "station_availability_snapshot": [
            "station_id",
            "station_name",
            "availability_status",
        ],
        "charger_availability_snapshot": ["station_id", "charger_id", "status"],
        "transport_service_notice": ["operator", "route_or_service", "source_url"],
        "fare_payment_policy_change": ["operator", "payment_program", "source_url"],
    }
    gaps: list[str] = []
    for field_name in required_by_model.get(event_model, []):
        value = row.get(field_name)
        if value is None or value == "" or value == []:
            gaps.append(field_name)
    return gaps


def _canonical_key(
    *,
    event_model: str,
    station_id: str,
    station_name: str,
    district: str,
    operator: str,
    charger_id: str,
    connector_type: str,
    payment_program: str,
    effective_date: str,
) -> str:
    if event_model == "station_availability_snapshot":
        parts = [operator, station_id, station_name, district]
        required_count = 2
    elif event_model == "charger_availability_snapshot":
        parts = [operator, station_id, charger_id, connector_type]
        required_count = 3
    elif event_model == "fare_payment_policy_change":
        parts = [operator, payment_program, effective_date]
        required_count = 2
    else:
        return ""
    if not all(parts[:required_count]):
        return ""
    return ":".join(_slug(part) for part in parts if part)


def _event_key(
    event_model: str,
    canonical_key: str,
    url: str,
    event_at: datetime | None,
) -> str:
    date_part = _event_date_text(event_at) or "undated"
    if canonical_key:
        return f"{event_model}:{canonical_key}:{date_part}"
    return f"{event_model}:url:{_digest(url)}:{date_part}"


def _operator(source: Source, network: str) -> str:
    if network:
        return network
    if source.producer_role:
        return source.producer_role
    return source.name


def _payment_program(article: Article) -> str:
    haystack = f"{article.title} {article.summary}".lower()
    for term in ("tap-to-pay", "contactless", "t-money", "tmoney", "fare", "payment", "pass"):
        if term in haystack:
            return term
    return ""


def _route_or_service(article: Article) -> str:
    service_matches = _matches(article, "Service")
    if service_matches:
        return service_matches[0]
    title = article.title.strip()
    return title[:120] if title else ""


def _district(location: str) -> str:
    if not location:
        return ""
    return location.split(",", 1)[0].strip()


def _event_date_text(event_at: datetime | None) -> str:
    return event_at.date().isoformat() if event_at is not None else ""


def _summary_value(summary: str, label: str) -> str:
    text = summary or ""
    marker = f"{label}:"
    start = text.find(marker)
    if start < 0:
        return ""
    value_start = start + len(marker)
    next_positions = [
        pos
        for other_label in SUMMARY_LABELS
        if other_label != label
        for pos in [text.find(f" {other_label}:", value_start)]
        if pos >= 0
    ]
    value_end = min(next_positions) if next_positions else len(text)
    return text[value_start:value_end].strip().rstrip(".").strip()


def _fragment_value(url: str, prefix: str) -> str:
    marker = f"#{prefix}"
    if marker not in url:
        return ""
    return url.split(marker, 1)[1].strip()


def _first_match(text: str, pattern: str) -> str:
    match = re.search(pattern, text or "", flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _first_non_empty(*values: str) -> str:
    for value in values:
        if value:
            return value
    return ""


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


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower())
    slug = normalized.strip("-")
    if slug:
        return slug
    return f"u-{_digest(value)}"


def _digest(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def _matches(article: Article, key: str) -> list[str]:
    values = article.matched_entities.get(key, [])
    if isinstance(values, list):
        return [str(value) for value in values]
    return []


def _dict(mapping: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else {}


def _as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _age_days(generated_at: datetime, event_at: datetime) -> float:
    return max(0.0, (_as_utc(generated_at) - _as_utc(event_at)).total_seconds() / 86400)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _parse_datetime(value: str) -> datetime | None:
    if not value or value == "None":
        return None
    try:
        return _as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        return None
