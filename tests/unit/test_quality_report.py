from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from mobilityradar.models import Article, CategoryConfig, Source
from mobilityradar.quality_report import build_quality_report, write_quality_report


def _article(
    *,
    source: str,
    title: str,
    published: datetime | None,
    matched_entities: dict[str, list[str]] | None = None,
) -> Article:
    return Article(
        title=title,
        link=f"https://example.com/{source}/{title}".replace(" ", "-"),
        summary=title,
        published=published,
        source=source,
        category="mobility",
        matched_entities=matched_entities or {},
    )


def test_build_quality_report_tracks_mobility_source_statuses() -> None:
    now = datetime(2026, 4, 13, tzinfo=UTC)
    category = CategoryConfig(
        category_name="mobility",
        display_name="Mobility",
        sources=[
            Source(
                name="서울 따릉이",
                type="javascript",
                url="https://www.ddareungi.seoul.kr/station",
                content_type="station_availability",
                config={"domain_scope": "mobility", "event_model": "station_availability_snapshot"},
            ),
            Source(
                name="환경부 전기차 충전소",
                type="javascript",
                url="https://www.ev.or.kr/evmonitor",
                enabled=False,
                trust_tier="T1_official_platform",
                content_type="charger_availability",
                notes="official API candidate pending",
                config={"domain_scope": "mobility", "event_model": "charger_availability_snapshot"},
            ),
            Source(
                name="서울 교통정보",
                type="javascript",
                url="https://topis.seoul.go.kr/refRoom/openRefRoom_2.do",
                content_type="transport_service_notice",
                config={"domain_scope": "mobility", "event_model": "transport_service_notice"},
            ),
            Source(name="Electrek", type="rss", url="https://electrek.co/feed/"),
        ],
        entities=[],
    )
    articles = [
        _article(
            source="환경부 전기차 충전소",
            title="charger status",
            published=now - timedelta(hours=12),
            matched_entities={"SourceSignal": ["charger_availability_snapshot"]},
        ),
        _article(
            source="서울 교통정보",
            title="transport notice",
            published=now - timedelta(days=4),
            matched_entities={"SourceSignal": ["transport_service_notice"]},
        ),
    ]

    report = build_quality_report(
        category=category,
        articles=articles,
        quality_config={
            "data_quality": {
                "quality_outputs": {
                    "tracked_event_models": [
                        "station_availability_snapshot",
                        "charger_availability_snapshot",
                        "transport_service_notice",
                    ]
                },
                "freshness_sla": {
                    "station_availability_snapshot_hours": 24,
                    "charger_availability_snapshot_hours": 24,
                    "transport_service_notice_days": 3,
                },
            },
            "source_backlog": {
                "operational_candidates": [
                    {"id": "charger_availability_api"},
                    {"id": "tmoney_fare_notice_feed"},
                ]
            },
        },
        generated_at=now,
    )

    summary = report["summary"]
    assert summary["tracked_sources"] == 3
    assert summary["fresh_sources"] == 0
    assert summary["stale_sources"] == 1
    assert summary["missing_sources"] == 1
    assert summary["not_tracked_sources"] == 1
    assert summary["charger_availability_snapshot_events"] == 0
    assert summary["transport_service_notice_events"] == 1
    assert summary["disabled_official_source_count"] == 1
    assert summary["tracked_event_model_gap_count"] == 1
    assert summary["operational_candidate_count"] == 2
    assert any(
        item["reason"] == "disabled_official_source"
        and item["event_model"] == "charger_availability_snapshot"
        for item in report["daily_review_items"]
    )
    assert any(
        item["reason"] == "tracked_event_model_without_live_signal"
        and item["event_model"] == "station_availability_snapshot"
        for item in report["daily_review_items"]
    )


def test_build_quality_report_extracts_station_key_and_review_gaps() -> None:
    now = datetime(2026, 4, 13, 0, 30, tzinfo=UTC)
    category = CategoryConfig(
        category_name="mobility",
        display_name="Mobility",
        sources=[
            Source(
                name="Seoul Bike",
                type="citybikes",
                url="https://api.citybik.es/v2/networks/seoul-bike",
                content_type="station_availability",
                producer_role="municipal_transport_operator",
                config={"domain_scope": "mobility", "event_model": "station_availability_snapshot"},
            ),
            Source(
                name="EV Monitor",
                type="javascript",
                url="https://example.com/charger",
                content_type="charger_availability",
                producer_role="national_environment_authority",
                config={"domain_scope": "mobility", "event_model": "charger_availability_snapshot"},
            ),
        ],
        entities=[],
    )
    articles = [
        _article(
            source="Seoul Bike",
            title="101. Test Station station availability - Seoul Bike",
            published=now,
            matched_entities={"SourceSignal": ["station_availability_snapshot"]},
        ),
        _article(
            source="EV Monitor",
            title="charger status",
            published=now,
            matched_entities={"SourceSignal": ["charger_availability_snapshot"]},
        ),
    ]
    articles[0].summary = (
        "Station ID: station-1. "
        "Station name: 101. Test Station. "
        "Network: Seoul Bike. "
        "Location: Seoul, KR. "
        "Free bikes: 3. "
        "Empty slots: 7. "
        "Availability status: bikes_and_docks_available. "
        "Observed at: 2026-04-13T00:01:02+00:00."
    )

    report = build_quality_report(
        category=category,
        articles=articles,
        quality_config={
            "data_quality": {
                "quality_outputs": {
                    "tracked_event_models": [
                        "station_availability_snapshot",
                        "charger_availability_snapshot",
                    ]
                }
            }
        },
        generated_at=now,
    )

    summary = report["summary"]
    station_event = report["events"][0]
    charger_event = report["events"][1]
    assert summary["operational_depth_event_count"] == 2
    assert summary["availability_snapshot_event_count"] == 2
    assert summary["station_canonical_key_present_count"] == 1
    assert summary["charger_canonical_key_present_count"] == 0
    assert summary["event_required_field_gap_count"] == 3
    assert station_event["station_id"] == "station-1"
    assert station_event["station_name"] == "101. Test Station"
    assert station_event["availability_status"] == "bikes_and_docks_available"
    assert station_event["canonical_key"] == "seoul-bike:station-1:101-test-station:seoul"
    assert station_event["free_bikes"] == 3
    assert station_event["empty_slots"] == 7
    assert charger_event["required_field_gaps"] == ["station_id", "charger_id", "status"]
    assert any(
        item["reason"] == "missing_required_fields"
        and item["event_model"] == "charger_availability_snapshot"
        for item in report["daily_review_items"]
    )


def test_write_quality_report_writes_latest_and_dated_json(tmp_path) -> None:
    report = {
        "category": "mobility",
        "generated_at": "2026-04-13T00:00:00+00:00",
        "summary": {},
        "sources": [],
        "events": [],
    }

    paths = write_quality_report(report, output_dir=tmp_path, category_name="mobility")

    assert paths["latest"].name == "mobility_quality.json"
    assert paths["dated"].name == "mobility_20260413_quality.json"
    assert json.loads(paths["latest"].read_text(encoding="utf-8"))["category"] == "mobility"
