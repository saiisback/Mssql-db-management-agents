"""Audit log writer. One SQLite table, one row per agent action."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Any

_lock = threading.Lock()
_initialized = False


def init(sqlite_path: str) -> None:
    global _initialized
    with _lock:
        if _initialized:
            return
        with sqlite3.connect(sqlite_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_key TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_ticket ON audit_log(ticket_key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at)")
        _initialized = True


def write(
    sqlite_path: str,
    ticket_key: str,
    agent: str,
    action: str,
    status: str,
    payload: dict[str, Any] | None = None,
) -> None:
    init(sqlite_path)
    with _lock, sqlite3.connect(sqlite_path) as conn:
        conn.execute(
            "INSERT INTO audit_log (ticket_key, agent, action, status, payload_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ticket_key, agent, action, status,
             json.dumps(payload, default=str) if payload else None,
             time.time()),
        )
