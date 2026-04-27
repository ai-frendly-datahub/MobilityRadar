from __future__ import annotations

from pathlib import Path

from mobilityradar.config_loader import load_category_config, load_category_quality_config


def test_load_category_config_preserves_source_metadata_and_domain_scope(tmp_path: Path) -> None:
    categories_dir = tmp_path / "categories"
    categories_dir.mkdir()
    (categories_dir / "mobility.yaml").write_text(
        """
category_name: mobility
display_name: Mobility Radar
domain_scope: mobility
sources:
  - id: seoul_ddareungi_station
    name: 서울 따릉이
    type: javascript
    url: https://www.ddareungi.seoul.kr/station
    enabled: true
    trust_tier: T1_official_platform
    content_type: station_availability
    collection_tier: C3_html_js
    producer_role: municipal_transport_operator
    info_purpose:
      - operational_signal
      - station_availability
    event_model: station_availability_snapshot
    canonical_key_fields:
      - station_id
      - observed_date
    verification_role: official_availability_reference
    config:
      wait_for: .station_list
entities: []
""",
        encoding="utf-8",
    )

    config = load_category_config("mobility", categories_dir=categories_dir)

    source = config.sources[0]
    assert source.id == "seoul_ddareungi_station"
    assert source.trust_tier == "T1_official_platform"
    assert source.content_type == "station_availability"
    assert source.collection_tier == "C3_html_js"
    assert source.producer_role == "municipal_transport_operator"
    assert source.info_purpose == ["operational_signal", "station_availability"]
    assert source.config["domain_scope"] == "mobility"
    assert source.config["event_model"] == "station_availability_snapshot"
    assert source.config["canonical_key_fields"] == ["station_id", "observed_date"]
    assert source.config["verification_role"] == "official_availability_reference"


def test_load_category_quality_config_returns_quality_contract(tmp_path: Path) -> None:
    categories_dir = tmp_path / "categories"
    categories_dir.mkdir()
    (categories_dir / "mobility.yaml").write_text(
        """
category_name: mobility
data_quality:
  quality_outputs:
    tracked_event_models:
      - station_availability_snapshot
source_backlog:
  operational_candidates:
    - id: charger_availability_api
sources: []
entities: []
""",
        encoding="utf-8",
    )

    quality = load_category_quality_config("mobility", categories_dir=categories_dir)

    assert quality["data_quality"] == {
        "quality_outputs": {"tracked_event_models": ["station_availability_snapshot"]}
    }
    assert quality["source_backlog"] == {
        "operational_candidates": [{"id": "charger_availability_api"}]
    }
