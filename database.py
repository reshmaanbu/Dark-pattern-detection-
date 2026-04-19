"""
database.py - SQLite database helpers.
"""

import sqlite3
import os
from datetime import datetime


def get_conn(db_path):
    # Auto-create the database folder if it doesn't exist
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    """Create tables if they don't exist."""
    conn = get_conn(db_path)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            score INTEGER NOT NULL,
            patterns TEXT,
            analyzed_at TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            vote TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_result(db_path, url, score, patterns_json):
    conn = get_conn(db_path)
    conn.execute(
        "INSERT INTO results (url, score, patterns, analyzed_at) VALUES (?, ?, ?, ?)",
        (url, score, patterns_json, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def get_history(db_path, limit=100):
    conn = get_conn(db_path)
    rows = conn.execute(
        "SELECT * FROM results ORDER BY analyzed_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return rows


def save_feedback(db_path, url, vote):
    conn = get_conn(db_path)
    conn.execute(
        "INSERT INTO feedback (url, vote, created_at) VALUES (?, ?, ?)",
        (url, vote, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()
