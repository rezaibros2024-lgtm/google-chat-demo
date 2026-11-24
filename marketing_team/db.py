"""The three systems of record from the diagram: posts.db, leads.db, sales.db.

Plain SQLite so you can open them in any viewer (DB Browser, TablePlus, Datasette).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from . import config

SCHEMAS: dict[str, str] = {
    "posts": """
        CREATE TABLE IF NOT EXISTS briefs (
            id INTEGER PRIMARY KEY,
            created_at TEXT NOT NULL,
            topic TEXT NOT NULL,
            body TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY,
            created_at TEXT NOT NULL,
            channel TEXT NOT NULL,
            format TEXT NOT NULL,
            hook TEXT NOT NULL,
            body TEXT NOT NULL,
            cta TEXT NOT NULL,
            visual_brief TEXT NOT NULL DEFAULT '',
            hashtags TEXT NOT NULL DEFAULT '',
            -- draft -> pending_approval -> approved -> published | rejected
            status TEXT NOT NULL DEFAULT 'pending_approval',
            review_notes TEXT NOT NULL DEFAULT '',
            published_at TEXT,
            external_id TEXT,
            views INTEGER NOT NULL DEFAULT 0,
            likes INTEGER NOT NULL DEFAULT 0,
            comments INTEGER NOT NULL DEFAULT 0,
            shares INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS inbox (
            id INTEGER PRIMARY KEY,
            created_at TEXT NOT NULL,
            channel TEXT NOT NULL,
            author TEXT NOT NULL,
            text TEXT NOT NULL,
            intent TEXT NOT NULL DEFAULT '',
            draft_reply TEXT NOT NULL DEFAULT '',
            needs_human INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'new'
        );
        CREATE TABLE IF NOT EXISTS learnings (
            id INTEGER PRIMARY KEY,
            created_at TEXT NOT NULL,
            body TEXT NOT NULL
        );
    """,
    "leads": """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY,
            created_at TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL DEFAULT '',
            company TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT '',
            message TEXT NOT NULL DEFAULT '',
            score INTEGER,
            tier TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            next_action TEXT NOT NULL DEFAULT '',
            draft_email TEXT NOT NULL DEFAULT '',
            -- new -> scored -> contacted -> booked -> won | lost
            status TEXT NOT NULL DEFAULT 'new'
        );
    """,
    "sales": """
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY,
            created_at TEXT NOT NULL,
            customer TEXT NOT NULL,
            email TEXT NOT NULL DEFAULT '',
            amount REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'USD',
            product TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT '',
            external_id TEXT UNIQUE
        );
    """,
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db_path(name: str) -> Path:
    return config.DATA_DIR / f"{name}.db"


@contextmanager
def connect(name: str) -> Iterator[sqlite3.Connection]:
    if name not in SCHEMAS:
        raise ValueError(f"unknown database {name!r}")
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path(name))
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMAS[name])
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_all() -> list[Path]:
    for name in SCHEMAS:
        with connect(name):
            pass
    return [db_path(n) for n in SCHEMAS]


def count(name: str, table: str, where: str = "1=1", params: tuple = ()) -> int:
    with connect(name) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", params).fetchone()[0]
