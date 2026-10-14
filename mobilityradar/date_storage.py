from __future__ import annotations

import logging
import shutil
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


def snapshot_database(
    db_path: Path,
    *,
    snapshot_date: date | None = None,
    snapshot_root: Path | None = None,
) -> Path | None:
    if not db_path.exists():
        return None

    if snapshot_date is None:
        snapshot_date = datetime.now(UTC).date()

    if snapshot_root is None:
        snapshot_root = db_path.parent / "daily"

    snapshot_root.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_root / f"{snapshot_date.isoformat()}.duckdb"

    shutil.copy2(db_path, snapshot_path)
    return snapshot_path


def cleanup_date_directories(base_dir: Path, *, keep_days: int, today: date | None = None) -> int:
    if today is None:
        today = datetime.now(UTC).date()

    cutoff = today - timedelta(days=keep_days)
    removed = 0

    if not base_dir.exists():
        return 0

    for item in base_dir.iterdir():
        if not item.is_dir():
            continue

        try:
            stamp: date | None = None
            if len(item.name) == 10 and item.name.count("-") == 2:
                stamp = date.fromisoformat(item.name)
        except ValueError:
            continue

        if stamp and stamp < cutoff:
            shutil.rmtree(item)
            removed += 1

    return removed


def cleanup_dated_reports(report_dir: Path, *, keep_days: int, today: date | None = None) -> int:
    if today is None:
        today = datetime.now(UTC).date()

    cutoff = today - timedelta(days=keep_days)
    removed = 0

    if not report_dir.exists():
        return 0

    for item in report_dir.glob("*_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].html"):
        try:
            date_str = item.stem.split("_")[-1]
            if len(date_str) == 8:
                stamp = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=UTC).date()
                if stamp < cutoff:
                    item.unlink()
                    removed += 1
        except (ValueError, IndexError):
            continue

    return removed


def cleanup_daily_snapshots(daily_dir: Path, *, keep_days: int, today: date | None = None) -> int:
    if keep_days < 0 or not daily_dir.exists():
        return 0
    cutoff = (today or datetime.now(UTC).date()) - timedelta(days=keep_days)
    removed = 0
    for item in daily_dir.iterdir():
        if not item.is_file() or not item.name.endswith(".duckdb"):
            continue
        try:
            stamp = date.fromisoformat(item.stem)
        except ValueError:
            continue
        if stamp < cutoff:
            item.unlink()
            removed += 1
    return removed


def compact_database_for_commit(database_path: Path) -> dict[str, object]:
    """Shrink ``database_path`` before a snapshot copy or git add.

    ``radar_core.db_compact.compact_duckdb_file`` reads ``RADAR_DUCKDB_MAX_BYTES``
    and ``RADAR_DUCKDB_COMPACT`` (default budget 90 MiB). A compaction failure
    leaves the file already on disk in place.
    """
    bytes_now = database_path.stat().st_size if database_path.exists() else 0
    fallback: dict[str, object] = {
        "compacted": False,
        "reason": "missing" if not database_path.exists() else "skipped",
        "bytes": bytes_now,
        "bytes_before": bytes_now,
        "rows_deleted": 0,
    }
    if not database_path.exists():
        return fallback
    try:
        from radar_core.db_compact import compact_duckdb_file
    except ImportError as exc:
        logger.warning("duckdb_compact_unavailable path=%s error=%s", database_path, exc)
        fallback["reason"] = "unavailable"
        return fallback
    try:
        result = compact_duckdb_file(database_path)
    except Exception as exc:
        logger.warning("duckdb_compact_failed path=%s error=%s", database_path, exc)
        fallback["reason"] = "failed"
        fallback["bytes"] = database_path.stat().st_size if database_path.exists() else 0
        return fallback
    if isinstance(result, dict):
        logger.info(
            "duckdb_compact path=%s reason=%s bytes_before=%s bytes=%s rows_deleted=%s",
            database_path,
            result.get("reason"),
            result.get("bytes_before"),
            result.get("bytes"),
            result.get("rows_deleted"),
        )
        return result
    fallback["reason"] = "invalid_result"
    return fallback


def apply_date_storage_policy(
    *,
    database_path: Path,
    raw_data_dir: Path,
    report_dir: Path,
    keep_raw_days: int,
    keep_report_days: int,
    snapshot_db: bool,
    keep_daily_days: int = 30,
) -> dict[str, object]:
    """Apply date-based storage policy: compact, snapshot, cleanup raw data and reports."""
    compact = compact_database_for_commit(database_path)
    snapshot_path = snapshot_database(database_path) if snapshot_db else None
    raw_removed = cleanup_date_directories(raw_data_dir, keep_days=keep_raw_days)
    report_removed = cleanup_dated_reports(report_dir, keep_days=keep_report_days)
    daily_removed = cleanup_daily_snapshots(
        database_path.parent / "daily", keep_days=keep_daily_days
    )
    return {
        "snapshot_path": str(snapshot_path) if snapshot_path is not None else None,
        "raw_removed": raw_removed,
        "report_removed": report_removed,
        "daily_removed": daily_removed,
        "compact": compact,
    }
