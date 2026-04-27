from __future__ import annotations

from collections.abc import Iterable

from .models import Article, Source


OPERATIONAL_EVENT_MODELS = {
    "charger_availability_snapshot",
    "fare_payment_policy_change",
    "station_availability_snapshot",
    "transport_service_notice",
}
OPERATIONAL_CONTENT_TYPES = {
    "charger_availability",
    "fare_payment_policy",
    "station_availability",
    "transport_service_notice",
}
OPERATIONAL_PURPOSES = {
    "bike_share_inventory",
    "charger_availability",
    "charging_station_inventory",
    "fare_or_payment_policy",
    "operational_signal",
    "station_availability",
    "transport_service_notice",
}
STRONG_ENTITY_NAMES = {
    "ChargingInfra",
    "EVModel",
    "Manufacturer",
    "Regulation",
    "VehicleType",
}
MOBILITY_HINT_TERMS = {
    "autonomous",
    "bev",
    "bike-share",
    "charging",
    "charging station",
    "e-bike",
    "e-scooter",
    "electric scooter",
    "electric vehicle",
    "ev ",
    "evs",
    "fare",
    "fast charging",
    "robotaxi",
    "self-driving",
    "station",
    "transit",
    "transport",
    "transportation",
    "전기차",
    "교통",
    "따릉이",
    "모빌리티",
    "자율주행",
    "자전거",
    "충전",
    "충전소",
}
INVALID_PAGE_TERMS = {
    "404",
    "access denied",
    "not found",
    "page not found",
    "request blocked",
    "service unavailable",
    "요청하신 페이지가 존재하지 않습니다",
    "페이지를 찾을 수 없습니다",
}


def apply_source_context_entities(
    articles: Iterable[Article],
    sources: Iterable[Source],
) -> list[Article]:
    source_map = {source.name: source for source in sources if source.enabled}
    classified: list[Article] = []
    for article in articles:
        source = source_map.get(article.source)
        if source is not None:
            tags = _source_context_tags(source)
            if tags:
                existing = article.matched_entities.get("SourceSignal", [])
                existing_values = existing if isinstance(existing, list) else [existing]
                merged = sorted({str(value) for value in existing_values} | set(tags))
                article.matched_entities["SourceSignal"] = merged
        classified.append(article)
    return classified


def filter_relevant_articles(
    articles: Iterable[Article],
    sources: Iterable[Source],
) -> list[Article]:
    source_map = {source.name: source for source in sources if source.enabled}
    filtered: list[Article] = []
    for article in articles:
        if article.category != "mobility":
            filtered.append(article)
            continue

        source = source_map.get(article.source)
        if source is None or _domain_scope(source) != "mobility" or _is_invalid_page(article):
            continue
        if _source_context_tags(source) or _has_strong_mobility_signal(article):
            filtered.append(article)
    return filtered


def _has_strong_mobility_signal(article: Article) -> bool:
    entities = set(article.matched_entities)
    if entities & {"ChargingInfra", "EVModel", "Regulation", "VehicleType"}:
        return True
    if "Manufacturer" in entities:
        haystack = f"{article.title} {article.summary}".lower()
        return any(term in haystack for term in MOBILITY_HINT_TERMS)
    if "Service" in entities:
        haystack = f"{article.title} {article.summary}".lower()
        return any(term in haystack for term in MOBILITY_HINT_TERMS)
    return False


def _is_invalid_page(article: Article) -> bool:
    title = (article.title or "").strip().lower()
    summary = (article.summary or "").strip().lower()
    return any(term in title or term in summary for term in INVALID_PAGE_TERMS)


def _source_context_tags(source: Source) -> list[str]:
    if _domain_scope(source) != "mobility":
        return []

    tags = {tag for tag in source.info_purpose if tag in OPERATIONAL_PURPOSES}
    content_type = source.content_type.lower()
    raw_event_model = source.config.get("event_model")
    event_model = raw_event_model.strip() if isinstance(raw_event_model, str) else ""

    if event_model in OPERATIONAL_EVENT_MODELS:
        tags.add(event_model)
    if content_type in OPERATIONAL_CONTENT_TYPES:
        tags.add(content_type)
    return sorted(tags)


def _domain_scope(source: Source) -> str:
    raw = source.config.get("domain_scope")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return ""
