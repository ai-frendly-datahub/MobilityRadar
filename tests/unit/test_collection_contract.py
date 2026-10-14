from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
import yaml

from main import ensure_collection_not_empty, run
from mobilityradar.collector import (
    MOBILITY_RADAR_USER_AGENT,
    RSS_TIMEOUT_SECONDS,
    _create_session,
    collect_sources,
)
from mobilityradar.config_loader import load_category_config
from mobilityradar.exceptions import EmptyCollectionError
from mobilityradar.models import Source
from mobilityradar.raw_logger import RawLogger

_FIXTURE = Path("tests/fixtures/challenge_feed.xml").read_bytes()


@pytest.fixture
def health_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    path = str(tmp_path / "crawl_health.duckdb")
    monkeypatch.setenv("RADAR_CRAWL_HEALTH_DB_PATH", path)
    return path


def test_coverage_config_uses_relative_paths() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    setup_cfg = Path("setup.cfg").read_text(encoding="utf-8")
    assert "relative_files = true" in pyproject
    assert "relative_files = True" in setup_cfg


def test_session_uses_identifying_user_agent_timeout_and_tls(health_db: str) -> None:
    session = _create_session()
    try:
        assert session.headers["User-Agent"] == MOBILITY_RADAR_USER_AGENT
        assert session.headers["User-Agent"].startswith("MobilityRadar/0.1")
        assert "Mozilla" not in session.headers["User-Agent"]
        assert session.verify is True
    finally:
        session.close()

    recorded: dict[str, object] = {}

    def _get(*_args: object, **kwargs: object) -> Mock:
        recorded.update(kwargs)
        response = Mock()
        response.raise_for_status.return_value = None
        response.content = _FIXTURE
        return response

    source = Source(name="Example News RSS", type="rss", url="https://example.com/feed.xml")
    with patch("mobilityradar.collector.requests.Session.get", side_effect=_get):
        articles, errors = collect_sources(
            [source], category="mobility", max_workers=1, health_db_path=health_db
        )

    assert errors == []
    assert [article.title for article in articles] == ["MobilityRadar release notes"]
    assert recorded["timeout"] == RSS_TIMEOUT_SECONDS == 45
    assert recorded["verify"] is True
    headers = recorded["headers"]
    assert isinstance(headers, dict)
    assert str(headers["User-Agent"]).startswith("MobilityRadar/0.1")


def test_collector_failure_returns_empty_list_without_sample_data(health_db: str) -> None:
    source = Source(name="down", type="rss", url="https://example.com/feed.xml")
    with patch(
        "mobilityradar.collector.requests.Session.get",
        side_effect=requests.exceptions.ConnectionError("down"),
    ):
        articles, errors = collect_sources(
            [source], category="mobility", max_workers=1, health_db_path=health_db
        )

    assert articles == []
    assert errors
    blob = " ".join(errors).lower()
    assert "sample" not in blob
    assert "fake" not in blob


def test_missing_secret_warns_once_and_records_names_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], health_db: str
) -> None:
    source = Source(
        name="Keyed API",
        type="rss",
        url="https://example.com/feed.xml",
        config={"required_env": ["MOBILITYRADAR_TEST_TOKEN", "MOBILITYRADAR_TEST_SECRET"]},
    )
    logger = RawLogger(tmp_path)
    with patch.dict(
        os.environ,
        {
            "MOBILITYRADAR_TEST_TOKEN": "",
            "MOBILITYRADAR_TEST_SECRET": "",
            "DECOY_SECRET": "super-secret-value",
        },
        clear=False,
    ):
        articles, errors = collect_sources(
            [source],
            category="mobility",
            raw_logger=logger,
            max_workers=1,
            health_db_path=health_db,
        )

    assert articles == []
    assert any("skipped_missing_env MOBILITYRADAR_TEST_TOKEN" in error for error in errors)
    warning = capsys.readouterr().out
    assert warning.count("::warning title=MobilityRadar missing secret::") == 1
    assert "MOBILITYRADAR_TEST_TOKEN" in warning
    assert "MOBILITYRADAR_TEST_SECRET" in warning
    assert "super-secret-value" not in warning
    skip_files = list(tmp_path.rglob("*.skip.json"))
    assert len(skip_files) == 1
    text = skip_files[0].read_text(encoding="utf-8")
    assert "MOBILITYRADAR_TEST_TOKEN" in text
    assert "MOBILITYRADAR_TEST_SECRET" in text
    assert "super-secret-value" not in text
    assert skip_files[0].name == "Keyed API.skip.json"


def test_invalid_required_env_is_not_written(tmp_path: Path, health_db: str) -> None:
    source = Source(
        name="bad-config",
        type="rss",
        url="https://example.com/feed.xml",
        config={"required_env": "actual-secret-value"},
    )
    logger = RawLogger(tmp_path)
    _articles, errors = collect_sources(
        [source],
        category="mobility",
        raw_logger=logger,
        max_workers=1,
        health_db_path=health_db,
    )
    assert errors
    assert "actual-secret-value" not in errors[0]
    assert "environment variable name" in errors[0]
    assert list(tmp_path.rglob("*.skip.json")) == []


def test_disabled_sources_are_not_active(health_db: str) -> None:
    source = Source(
        name="Paused",
        type="rss",
        url="https://example.com/feed.xml",
        enabled=False,
    )
    with patch(
        "mobilityradar.collector.requests.Session.get", side_effect=AssertionError("fetched")
    ):
        articles, errors = collect_sources(
            [source], category="mobility", max_workers=1, health_db_path=health_db
        )
    assert articles == []
    assert errors == []


def test_ensure_collection_not_empty_rejects_zero_articles() -> None:
    with pytest.raises(EmptyCollectionError):
        ensure_collection_not_empty(collected_count=0, enabled_source_count=2)


def test_ensure_collection_not_empty_allows_items_or_no_enabled_sources() -> None:
    ensure_collection_not_empty(collected_count=1, enabled_source_count=2)
    ensure_collection_not_empty(collected_count=0, enabled_source_count=0)


def test_run_fails_when_active_sources_collect_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RADAR_CRAWL_HEALTH_DB_PATH", str(tmp_path / "crawl_health.duckdb"))
    config_path = tmp_path / "config.yaml"
    categories_dir = tmp_path / "categories"
    categories_dir.mkdir()
    config_path.write_text(
        yaml.safe_dump(
            {
                "database_path": str(tmp_path / "data" / "radar_data.duckdb"),
                "report_dir": str(tmp_path / "reports"),
                "raw_data_dir": str(tmp_path / "data" / "raw"),
                "search_db_path": str(tmp_path / "data" / "search_index.db"),
            }
        ),
        encoding="utf-8",
    )
    (categories_dir / "test_cat.yaml").write_text(
        yaml.safe_dump(
            {
                "category_name": "test_cat",
                "display_name": "Test",
                "sources": [
                    {"name": "Empty", "type": "rss", "url": "https://example.com/feed.xml"}
                ],
                "entities": [],
            }
        ),
        encoding="utf-8",
    )
    empty_feed = (
        b"""<?xml version="1.0"?><rss version="2.0"><channel><title>Empty</title></channel></rss>"""
    )
    response = Mock()
    response.raise_for_status.return_value = None
    response.content = empty_feed
    with (
        patch("mobilityradar.collector.requests.Session.get", return_value=response),
        pytest.raises(EmptyCollectionError),
    ):
        run(
            category="test_cat",
            config_path=config_path,
            categories_dir=categories_dir,
            per_source_limit=5,
            recent_days=7,
            timeout=5,
        )


def test_load_category_keeps_disabled_source_out_of_collection(
    tmp_path: Path, health_db: str
) -> None:
    categories_dir = tmp_path / "categories"
    categories_dir.mkdir()
    (categories_dir / "mobility.yaml").write_text(
        yaml.safe_dump(
            {
                "category_name": "mobility",
                "display_name": "Mobility",
                "sources": [
                    {
                        "name": "Paused",
                        "type": "rss",
                        "url": "https://example.com/feed.xml",
                        "enabled": False,
                    }
                ],
                "entities": [],
            }
        ),
        encoding="utf-8",
    )
    loaded = load_category_config("mobility", categories_dir=categories_dir)
    assert loaded.sources[0].enabled is False
    with patch(
        "mobilityradar.collector.requests.Session.get", side_effect=AssertionError("fetched")
    ):
        articles, errors = collect_sources(
            loaded.sources, category="mobility", max_workers=1, health_db_path=health_db
        )
    assert articles == []
    assert errors == []


def test_citybikes_seoul_summarizes_live_station_counts(health_db: str) -> None:
    payload = {
        "network": {
            "id": "seoul-bike",
            "name": "Seoul Bike",
            "href": "/v2/networks/seoul-bike",
            "company": ["Seoul"],
            "location": {
                "city": "Seoul",
                "country": "KR",
                "latitude": 37.56,
                "longitude": 126.97,
            },
            "stations": [
                {
                    "name": "Station A",
                    "free_bikes": 4,
                    "empty_slots": 2,
                    "timestamp": "2026-03-13T12:00:00+00:00",
                },
                {
                    "name": "Station B",
                    "free_bikes": 1,
                    "empty_slots": 3,
                    "timestamp": "2026-03-13T11:00:00+00:00",
                },
            ],
        }
    }
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    source = Source(
        name="CityBikes Seoul",
        type="citybikes",
        url="https://api.citybik.es/v2/networks/seoul-bike",
        config={"focus_cities": ["Seoul"]},
    )
    with patch("mobilityradar.collectors.citybikes_collector.requests.get", return_value=response):
        articles, errors = collect_sources(
            [source], category="mobility", max_workers=1, health_db_path=health_db
        )

    assert errors == []
    assert len(articles) == 1
    assert "Stations: 2" in articles[0].summary
    assert "Free bikes: 5" in articles[0].summary
    assert "Empty slots: 5" in articles[0].summary
    assert articles[0].link == "https://api.citybik.es/v2/networks/seoul-bike"
    assert "sample" not in articles[0].summary.lower()
    encoded = json.dumps(articles[0].summary)
    assert "super-secret" not in encoded
