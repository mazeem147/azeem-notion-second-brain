"""
db.py — SQLite helpers shared across pages.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "brain.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS diary_entries (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT NOT NULL,
                content     TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS media_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT,
                title       TEXT,
                media_type  TEXT,
                rating      INTEGER,
                reaction    TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id         TEXT PRIMARY KEY,
                title      TEXT NOT NULL DEFAULT 'New chat',
                messages   TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

    # Add rating column if it was created before this migration
    with get_conn() as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(media_logs)").fetchall()]
        if "rating" not in cols:
            conn.execute("ALTER TABLE media_logs ADD COLUMN rating INTEGER")
            conn.commit()
