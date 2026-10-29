"""Published instants stay UTC when the crawler runs with TZ=Asia/Seoul.

feedparser ``*_parsed`` values are UTC. ``time.mktime`` would treat them as
local time and store 2026-10-28 15:00 UTC as 06:00 UTC.
"""

from __future__ import annotations

import textwrap
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Self
from zoneinfo import ZoneInfo

import pytest

from mobilityradar.collector import _extract_datetime, _extract_published
from mobilityradar.config_loader import load_category_config
from mobilityradar.models import Article, Source
from mobilityradar.raw_logger import RawLogger
from mobilityradar.storage import RadarStorage

_FIFTEEN_UTC = time.struct_time((2026, 10, 28, 15, 0, 0, 2, 301, 0))
_KST = ZoneInfo("Asia/Seoul")


class _LateUtc(datetime):
    """2026-10-28 15:30 UTC is 2026-10-29 00:30 in Asia/Seoul."""

    @classmethod
    def now(cls, tz: object = None) -> Self:
        moment = datetime(2026, 10, 28, 15, 30, tzinfo=UTC)
        clock = moment.replace(tzinfo=None) if tz is None else moment
        return cls(
            clock.year,
            clock.month,
            clock.day,
            clock.hour,
            clock.minute,
            clock.second,
            tzinfo=clock.tzinfo,
        )


def _seoul(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TZ", "Asia/Seoul")
    time.tzset()


def _restore_tz(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.undo()
    time.tzset()


def test_feedparser_struct_stores_1500_utc_under_seoul(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _seoul(monkeypatch)
    try:
        parsed = _extract_datetime({"published_parsed": _FIFTEEN_UTC})
        updated = _extract_datetime({"updated_parsed": _FIFTEEN_UTC})
        assert parsed == datetime(2026, 10, 28, 15, 0, tzinfo=UTC)
        assert updated == datetime(2026, 10, 28, 15, 0, tzinfo=UTC)

        storage = RadarStorage(tmp_path / "radar.duckdb")
        try:
            storage.upsert_articles(
                [
                    Article(
                        title="게시 시각",
                        link="https://example.com/published-utc",
                        summary="요약",
                        published=parsed,
                        source="Example",
                        category="mobility",
                    )
                ]
            )
            row = storage.conn.execute("SELECT published FROM articles").fetchone()
        finally:
            storage.close()

        assert row is not None
        stored = row[0]
        assert isinstance(stored, datetime)
        assert stored.tzinfo is None
        assert stored == datetime(2026, 10, 28, 15, 0, tzinfo=UTC).replace(tzinfo=None)
    finally:
        _restore_tz(monkeypatch)


def test_offset_string_keeps_its_offset(monkeypatch: pytest.MonkeyPatch) -> None:
    _seoul(monkeypatch)
    try:
        parsed, raw = _extract_published({"published": "Thu, 29 Oct 2026 09:00:00 +0900"})
        assert raw == "Thu, 29 Oct 2026 09:00:00 +0900"
        assert parsed is not None
        assert parsed.utcoffset() == timedelta(hours=9)
        assert parsed.astimezone(UTC) == datetime(2026, 10, 29, 0, 0, tzinfo=UTC)
    finally:
        _restore_tz(monkeypatch)


def test_zoneless_string_uses_source_then_host_default() -> None:
    korean = Source(name="인벤", type="rss", url="https://news.example.kr/rss")
    parsed, raw = _extract_published({"published": "2026-10-28 18:00:00"}, korean)
    assert raw == "2026-10-28 18:00:00"
    assert parsed == datetime(2026, 10, 28, 18, 0, tzinfo=_KST)

    explicit = Source(
        name="Example",
        type="rss",
        url="https://example.com/feed",
        default_timezone="Asia/Seoul",
    )
    overridden, _ = _extract_published({"published": "2026-10-28 18:00:00"}, explicit)
    assert overridden == datetime(2026, 10, 28, 18, 0, tzinfo=_KST)

    configured = Source(
        name="Example",
        type="rss",
        url="https://news.example.com/rss",
        config={"default_timezone": "Asia/Seoul"},
    )
    from_config, _ = _extract_published({"published": "2026-10-28 18:00:00"}, configured)
    assert from_config == datetime(2026, 10, 28, 18, 0, tzinfo=_KST)

    other = Source(name="Example", type="rss", url="https://example.com/feed")
    utc_parsed, _ = _extract_published({"published": "2026-10-28 15:00:00"}, other)
    assert utc_parsed == datetime(2026, 10, 28, 15, 0, tzinfo=UTC)


def test_category_yaml_default_timezone_reaches_the_source(tmp_path: Path) -> None:
    (tmp_path / "mobility.yaml").write_text(
        textwrap.dedent("""
            category_name: mobility
            display_name: Mobility
            sources:
              - name: Example
                type: rss
                url: https://example.com/feed
                default_timezone: Asia/Seoul
            """),
        encoding="utf-8",
    )
    loaded = load_category_config("mobility", categories_dir=tmp_path)
    assert loaded.sources[0].default_timezone == "Asia/Seoul"


def test_raw_and_daily_partition_use_kst_collection_date(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mobilityradar.date_storage import snapshot_database

    monkeypatch.setattr("mobilityradar.raw_logger.datetime", _LateUtc)
    monkeypatch.setattr("mobilityradar.date_storage.datetime", _LateUtc)

    output = RawLogger(tmp_path / "raw").log(
        [
            Article(
                title="야간 수집",
                link="https://example.com/kst-partition",
                summary="요약",
                published=datetime(2026, 10, 28, 15, 0, tzinfo=UTC),
                source="Example",
                category="mobility",
            )
        ],
        source_name="Example",
    )
    assert output.parent.name == "2026-10-29"

    db_file = tmp_path / "radar_data.duckdb"
    db_file.write_text("fake-db")
    snapshot = snapshot_database(db_file)
    assert snapshot is not None
    assert snapshot.name == "2026-10-29.duckdb"
