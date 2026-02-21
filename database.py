"""Affinity — Gestion SQLite (événements, périphériques, notifications)."""

import json
import sqlite3
from pathlib import Path

from config import DB_PATH


def init_db() -> None:
    """Initialise la base de données et crée les tables si nécessaire."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        type TEXT,
        severity TEXT DEFAULT 'info',
        title TEXT,
        description TEXT,
        details_json TEXT,
        read INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vid TEXT, pid TEXT, name TEXT,
        approved INTEGER DEFAULT 0,
        first_seen DATETIME,
        last_seen DATETIME,
        connection_count INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        type TEXT, title TEXT, body TEXT,
        read INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS ai_conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        role TEXT, content TEXT
    );
    CREATE TABLE IF NOT EXISTS quarantine (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_path TEXT,
        quarantine_path TEXT,
        quarantine_date DATETIME,
        reason TEXT,
        hash_sha256 TEXT
    );
    """)
    conn.commit()
    conn.close()


def log_event(
    type_: str,
    title: str,
    description: str = "",
    severity: str = "info",
    details: dict | None = None,
) -> None:
    """Enregistre un événement dans l'historique."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO events (type, severity, title, description, details_json) VALUES (?,?,?,?,?)",
        (type_, severity, title, description, json.dumps(details or {})),
    )
    conn.commit()
    conn.close()


def get_recent_events(limit: int = 20) -> list:
    """Retourne les N derniers événements."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
