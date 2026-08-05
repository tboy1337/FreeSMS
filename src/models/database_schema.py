"""SQLite schema definitions for the SMS application database."""

import sqlite3


def create_tables(cursor: sqlite3.Cursor) -> None:
    """Create database tables if they don't exist."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_credentials (
            id INTEGER PRIMARY KEY,
            service_name TEXT NOT NULL,
            credentials TEXT NOT NULL,
            is_active INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            country TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS message_history (
            id INTEGER PRIMARY KEY,
            recipient TEXT NOT NULL,
            message TEXT NOT NULL,
            service TEXT NOT NULL,
            status TEXT NOT NULL,
            message_id TEXT,
            sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
            details TEXT
        )
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_messages (
            id INTEGER PRIMARY KEY,
            recipient TEXT NOT NULL,
            message TEXT NOT NULL,
            scheduled_time TEXT NOT NULL,
            service TEXT,
            recurring TEXT,
            recurring_interval TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            last_run TEXT
        )
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS message_templates (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
