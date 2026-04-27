from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from mobilityradar.models import Article, CategoryConfig, Source
from mobilityradar.reporter import generate_report


def test_generate_report_includes_mobility_quality_panel(tmp_path: Path) -> None:
    category = CategoryConfig(
        category_name="mobility",
        display_name="Mobility Radar",
        sources=[Source(name="Seoul Bike", type="citybikes", url="https://example.com")],
        entities=[],
    )
    article = Article(
        title="101. Test Station station availability - Seoul Bike",
        link="https://example.com/station-1",
        summary="Station availability snapshot",
        published=datetime(2026, 4, 13, tzinfo=UTC),
        source="Seoul Bike",
        category="mobility",
        matched_entities={"SourceSignal": ["station_availability_snapshot"]},
    )
    quality_report = {
        "generated_at": "2026-04-13T00:00:00+00:00",
        "summary": {
            "operational_depth_event_count": 1,
            "availability_snapshot_event_count": 1,
            "station_canonical_key_present_count": 1,
            "charger_canonical_key_present_count": 0,
            "event_required_field_gap_count": 1,
            "daily_review_item_count": 1,
        },
        "events": [
            {
                "event_model": "station_availability_snapshot",
                "source": "Seoul Bike",
                "canonical_key": "seoul-bike:station-1:test-station:seoul",
                "availability_status": "bikes_available",
            }
        ],
        "daily_review_items": [
            {
                "reason": "missing_required_fields",
                "event_model": "charger_availability_snapshot",
                "source": "EV Monitor",
                "required_field_gaps": ["charger_id"],
            }
        ],
    }

    output_path = tmp_path / "mobility_report.html"
    result = generate_report(
        category=category,
        articles=[article],
        output_path=output_path,
        stats={"sources": 1, "matched": 1},
        quality_report=quality_report,
    )

    html = result.read_text(encoding="utf-8")
    assert "Mobility Quality" in html
    assert "station_availability_snapshot" in html
    assert "seoul-bike:station-1:test-station:seoul" in html
    assert "missing_required_fields" in html

    dated_html = next(
        tmp_path.glob("mobility_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].html")
    )
    dated_text = dated_html.read_text(encoding="utf-8")
    assert "Mobility Quality" in dated_text
    assert "missing_required_fields" in dated_text

    summary_path = next(
        tmp_path.glob("mobility_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_summary.json")
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["ontology"]["repo"] == "MobilityRadar"
    assert summary["ontology"]["ontology_version"] == "0.1.0"
    assert "mobility.station_availability_snapshot" in summary["ontology"]["event_model_ids"]
