import sqlite3

from werkzeug.security import generate_password_hash

import config

DB_PATH = "sensors.db"

DEFAULT_THRESHOLDS = {
    "temperature": (74, 83),
    "pressure": (5.4, 6.2),
    "vibration": (0.7, 1.2),
}


def get_connection(path=None):
    return sqlite3.connect(path if path is not None else DB_PATH)


def init_db(path=None):
    conn = get_connection(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temperature REAL NOT NULL,
            pressure REAL NOT NULL,
            vibration REAL NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS thresholds (
            metric TEXT PRIMARY KEY,
            warn_boundary REAL NOT NULL,
            fault_boundary REAL NOT NULL
        )
        """
    )
    for metric, (warn_boundary, fault_boundary) in DEFAULT_THRESHOLDS.items():
        conn.execute(
            "INSERT OR IGNORE INTO thresholds (metric, warn_boundary, fault_boundary) VALUES (?, ?, ?)",
            (metric, warn_boundary, fault_boundary),
        )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
        """
    )
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    admin_password = config.get("ADMIN_PASSWORD")
    if user_count == 0 and admin_password:
        admin_username = config.get("ADMIN_USERNAME", "admin")
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (admin_username, generate_password_hash(admin_password)),
        )
    conn.commit()
    conn.close()


def insert_reading(timestamp, temperature, pressure, vibration, path=None):
    conn = get_connection(path)
    conn.execute(
        "INSERT INTO readings (timestamp, temperature, pressure, vibration) VALUES (?, ?, ?, ?)",
        (timestamp, temperature, pressure, vibration),
    )
    conn.commit()
    conn.close()


def get_latest_readings(limit=50, path=None):
    conn = get_connection(path)
    cursor = conn.execute(
        "SELECT timestamp, temperature, pressure, vibration FROM readings ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_readings(path=None):
    conn = get_connection(path)
    cursor = conn.execute(
        "SELECT timestamp, temperature, pressure, vibration FROM readings ORDER BY id ASC"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_thresholds(path=None):
    conn = get_connection(path)
    cursor = conn.execute("SELECT metric, warn_boundary, fault_boundary FROM thresholds")
    rows = cursor.fetchall()
    conn.close()
    return {metric: (warn_boundary, fault_boundary) for metric, warn_boundary, fault_boundary in rows}


def update_threshold(metric, warn_boundary, fault_boundary, path=None):
    conn = get_connection(path)
    conn.execute(
        "UPDATE thresholds SET warn_boundary = ?, fault_boundary = ? WHERE metric = ?",
        (warn_boundary, fault_boundary, metric),
    )
    conn.commit()
    conn.close()


def get_user(username, path=None):
    conn = get_connection(path)
    cursor = conn.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def upsert_user(username, password_hash, path=None):
    conn = get_connection(path)
    conn.execute(
        """
        INSERT INTO users (username, password_hash) VALUES (?, ?)
        ON CONFLICT(username) DO UPDATE SET password_hash = excluded.password_hash
        """,
        (username, password_hash),
    )
    conn.commit()
    conn.close()
