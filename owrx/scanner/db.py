import json
import sqlite3
from datetime import datetime


class ScannerDatabase:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                frequency_hz INTEGER NOT NULL,
                bandwidth_hz INTEGER,
                mode TEXT,
                peak_power_db REAL,
                snr_db REAL,
                duration_sec REAL,
                classification TEXT,
                filter_result TEXT,
                bookmark_label TEXT,
                recording_path TEXT,
                transcription TEXT,
                summary TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_detections_timestamp ON detections(timestamp);
            CREATE INDEX IF NOT EXISTS idx_detections_frequency ON detections(frequency_hz);
            CREATE INDEX IF NOT EXISTS idx_detections_classification ON detections(classification);

            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frequency_hz INTEGER NOT NULL,
                label TEXT NOT NULL,
                mode TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                last_heard TEXT
            );

            CREATE TABLE IF NOT EXISTS scan_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                stopped_at TEXT,
                config_json TEXT
            );
        """)
        self.conn.commit()

    def list_tables(self) -> list[str]:
        cur = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [row["name"] for row in cur.fetchall()]

    def log_detection(self, **kwargs) -> int:
        kwargs["timestamp"] = datetime.utcnow().isoformat()
        columns = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" for _ in kwargs)
        cur = self.conn.execute(
            f"INSERT INTO detections ({columns}) VALUES ({placeholders})",
            list(kwargs.values()),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_detection(self, det_id: int) -> dict | None:
        cur = self.conn.execute("SELECT * FROM detections WHERE id = ?", (det_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def update_detection(self, det_id: int, **kwargs):
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        self.conn.execute(
            f"UPDATE detections SET {set_clause} WHERE id = ?",
            list(kwargs.values()) + [det_id],
        )
        self.conn.commit()

    def clear_recording_path(self, det_id: int):
        self.conn.execute(
            "UPDATE detections SET recording_path = NULL WHERE id = ?", (det_id,)
        )
        self.conn.commit()

    def get_recent_detections(
        self, limit: int = 20, filter_result: str | None = None
    ) -> list[dict]:
        if filter_result is not None:
            cur = self.conn.execute(
                "SELECT * FROM detections WHERE filter_result = ? ORDER BY timestamp DESC LIMIT ?",
                (filter_result, limit),
            )
        else:
            cur = self.conn.execute(
                "SELECT * FROM detections ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
        return [dict(row) for row in cur.fetchall()]

    def get_most_active(self, hours: int = 24, limit: int = 10) -> list[dict]:
        since = datetime.utcnow()
        # Compute cutoff by subtracting hours worth of seconds
        from datetime import timedelta

        cutoff = (since - timedelta(hours=hours)).isoformat()
        cur = self.conn.execute(
            """
            SELECT frequency_hz, mode, COUNT(*) as count, MAX(peak_power_db) as max_power
            FROM detections
            WHERE timestamp >= ?
            GROUP BY frequency_hz, mode
            ORDER BY count DESC
            LIMIT ?
            """,
            (cutoff, limit),
        )
        return [dict(row) for row in cur.fetchall()]

    def add_bookmark(
        self,
        frequency_hz: int,
        label: str,
        mode: str | None = None,
        notes: str | None = None,
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO bookmarks (frequency_hz, label, mode, notes, created_at) VALUES (?, ?, ?, ?, ?)",
            (frequency_hz, label, mode, notes, datetime.utcnow().isoformat()),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_bookmark(self, bm_id: int) -> dict | None:
        cur = self.conn.execute("SELECT * FROM bookmarks WHERE id = ?", (bm_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_all_bookmarks(self) -> list[dict]:
        cur = self.conn.execute("SELECT * FROM bookmarks ORDER BY frequency_hz")
        return [dict(row) for row in cur.fetchall()]

    def start_session(self, config: dict) -> int:
        cur = self.conn.execute(
            "INSERT INTO scan_sessions (started_at, config_json) VALUES (?, ?)",
            (datetime.utcnow().isoformat(), json.dumps(config)),
        )
        self.conn.commit()
        return cur.lastrowid

    def stop_session(self, session_id: int):
        self.conn.execute(
            "UPDATE scan_sessions SET stopped_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), session_id),
        )
        self.conn.commit()

    def get_session(self, session_id: int) -> dict | None:
        cur = self.conn.execute(
            "SELECT * FROM scan_sessions WHERE id = ?", (session_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def close(self):
        self.conn.close()
