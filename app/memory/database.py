"""
app/memory/database.py
SQLite persistence layer for application history.

Stores full pipeline results, feedback signals, and application status.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiosqlite
from loguru import logger


DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id              TEXT PRIMARY KEY,
    job_title       TEXT NOT NULL,
    company_name    TEXT NOT NULL,
    job_url         TEXT,
    match_score     INTEGER,
    status          TEXT DEFAULT 'pending',
    result_json     TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id  TEXT NOT NULL,
    outcome         TEXT NOT NULL,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (application_id) REFERENCES applications(id)
);

CREATE TABLE IF NOT EXISTS resume_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id  TEXT NOT NULL,
    version_id      TEXT NOT NULL,
    markdown_content TEXT NOT NULL,
    ats_score       INTEGER,
    created_at      TEXT DEFAULT (datetime('now'))
);
"""


class ApplicationDatabase:
    """Async SQLite database for persisting application data."""

    def __init__(self):
        db_path = os.getenv("SQLITE_DB_PATH", "./data/applications.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path

    async def init(self):
        """Initialize database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(DB_SCHEMA)
            await db.commit()
        logger.info(f"[Database] Initialized at {self.db_path}")

    async def save_application(
        self,
        application_id: str,
        job_title: str,
        company_name: str,
        match_score: int,
        result_json: dict,
        job_url: Optional[str] = None,
    ) -> bool:
        """Save a complete pipeline result."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO applications
                        (id, job_title, company_name, job_url, match_score, result_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        application_id,
                        job_title,
                        company_name,
                        job_url,
                        match_score,
                        json.dumps(result_json),
                        datetime.utcnow().isoformat(),
                    ),
                )
                await db.commit()
            logger.info(f"[Database] Saved application {application_id}")
            return True
        except Exception as e:
            logger.error(f"[Database] Failed to save application: {e}")
            return False

    async def get_application(self, application_id: str) -> Optional[dict]:
        """Retrieve a single application by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM applications WHERE id = ?", (application_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    data = dict(row)
                    data["result_json"] = json.loads(data["result_json"] or "{}")
                    return data
        return None

    async def list_applications(self, limit: int = 20) -> list[dict]:
        """List recent applications."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT id, job_title, company_name, job_url, match_score, status, created_at
                FROM applications
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def record_feedback(
        self,
        application_id: str,
        outcome: str,
        notes: Optional[str] = None,
    ) -> bool:
        """Record outcome feedback for an application."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO feedback (application_id, outcome, notes) VALUES (?, ?, ?)",
                    (application_id, outcome, notes),
                )
                await db.execute(
                    "UPDATE applications SET status = ?, updated_at = ? WHERE id = ?",
                    (outcome, datetime.utcnow().isoformat(), application_id),
                )
                await db.commit()
            logger.info(f"[Database] Feedback recorded for {application_id}: {outcome}")
            return True
        except Exception as e:
            logger.error(f"[Database] Failed to record feedback: {e}")
            return False

    async def get_outcome_stats(self) -> dict:
        """Aggregate stats on application outcomes."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT status, COUNT(*) as count FROM applications GROUP BY status"
            ) as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows}
