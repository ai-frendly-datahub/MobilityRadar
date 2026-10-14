from __future__ import annotations

from pathlib import Path

import duckdb

from radar_core.exceptions import StorageError
from radar_core.storage import RadarStorage as _BaseRadarStorage

from .date_storage import cleanup_date_directories, compact_database_for_commit, snapshot_database


class RadarStorage(_BaseRadarStorage):
    """MobilityRadar storage with daily-snapshot helpers."""

    def create_daily_snapshot(self, snapshot_dir: str | None = None) -> Path | None:
        snapshot_root = Path(snapshot_dir) if snapshot_dir else self.db_path.parent / "daily"
        _ = self.conn.execute("CHECKPOINT")
        self.conn.close()
        try:
            _ = compact_database_for_commit(self.db_path)
            return snapshot_database(self.db_path, snapshot_root=snapshot_root)
        finally:
            self.conn = duckdb.connect(str(self.db_path))
            self._ensure_tables()

    def cleanup_old_snapshots(self, keep_days: int = 30) -> int:
        snapshot_root = self.db_path.parent / "daily"
        return cleanup_date_directories(snapshot_root, keep_days=keep_days)


__all__ = ["RadarStorage", "StorageError"]
