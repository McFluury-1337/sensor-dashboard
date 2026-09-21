import sqlite3

DB_PATH = "sensors.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
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
    conn.commit()
    conn.close()


def insert_reading(timestamp, temperature, pressure, vibration):
    conn = get_connection()
    conn.execute(
        "INSERT INTO readings (timestamp, temperature, pressure, vibration) VALUES (?, ?, ?, ?)",
        (timestamp, temperature, pressure, vibration),
    )
    conn.commit()
    conn.close()


def get_latest_readings(limit=50):
    conn = get_connection()
    cursor = conn.execute(
        "SELECT timestamp, temperature, pressure, vibration FROM readings ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows
