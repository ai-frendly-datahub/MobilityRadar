from __future__ import annotations

from mobilityradar.models import Article, Source
from mobilityradar.relevance import apply_source_context_entities, filter_relevant_articles


def _article(
    *,
    title: str,
    source: str = "Electrek",
    category: str = "mobility",
    matched_entities: dict[str, list[str]] | None = None,
) -> Article:
    return Article(
        title=title,
        link=f"https://example.com/{title.replace(' ', '-')}",
        summary=title,
        published=None,
        source=source,
        category=category,
        matched_entities=matched_entities or {},
    )


def test_apply_source_context_entities_adds_operational_signal() -> None:
    article = _article(
        title="charger status",
        source="환경부 전기차 충전소",
        matched_entities={},
    )
    source = Source(
        name="환경부 전기차 충전소",
        type="javascript",
        url="https://www.ev.or.kr/evmonitor",
        content_type="charger_availability",
        info_purpose=["mobility", "operational_signal", "charger_availability"],
        config={"domain_scope": "mobility", "event_model": "charger_availability_snapshot"},
    )

    classified = apply_source_context_entities([article], [source])

    assert classified[0].matched_entities["SourceSignal"] == [
        "charger_availability",
        "charger_availability_snapshot",
        "operational_signal",
    ]


def test_filter_relevant_articles_excludes_coffee_and_broad_noise() -> None:
    sources = [
        Source(
            name="Electrek",
            type="rss",
            url="https://electrek.co/feed/",
            config={"domain_scope": "mobility"},
        ),
        Source(
            name="서울 교통정보",
            type="javascript",
            url="https://topis.seoul.go.kr/refRoom/openRefRoom_2.do",
            content_type="transport_service_notice",
            info_purpose=["mobility", "operational_signal", "transport_service_notice"],
            config={"domain_scope": "mobility", "event_model": "transport_service_notice"},
        ),
        Source(
            name="Perfect Daily Grind",
            type="rss",
            url="https://perfectdailygrind.com/feed/",
            config={"domain_scope": "coffee"},
        ),
    ]
    articles = [
        _article(
            title="EV charging stations expand",
            matched_entities={"VehicleType": ["ev"], "ChargingInfra": ["charging"]},
        ),
        _article(title="Energy market roundup", matched_entities={}),
        _article(
            title="TOPIS traffic status",
            source="서울 교통정보",
            matched_entities={},
        ),
        _article(
            title="Coffee harvest improves",
            source="Perfect Daily Grind",
            matched_entities={"VehicleType": ["ev"]},
        ),
        _article(title="Access Denied", source="서울 교통정보", matched_entities={}),
    ]

    filtered = filter_relevant_articles(articles, sources)

    assert [article.title for article in filtered] == [
        "EV charging stations expand",
        "TOPIS traffic status",
    ]
