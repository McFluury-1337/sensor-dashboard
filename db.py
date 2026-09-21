import sqlite3

DB_PATH = "sensors.db"

DEFAULT_THRESHOLDS = {
    "temperature": (74, 83),
    "pressure": (5.4, 6.2),
    "vibration": (0.7, 1.2),
}


def get_connection(path=DB_PATH):
    return sqlite3.connect(path)


def init_db(path=DB_PATH):
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
    conn.commit()
    conn.close()


def insert_reading(timestamp, temperature, pressure, vibration, path=DB_PATH):
    conn = get_connection(path)
    conn.execute(
        "INSERT INTO readings (timestamp, temperature, pressure, vibration) VALUES (?, ?, ?, ?)",
        (timestamp, temperature, pressure, vibration),
    )
    conn.commit()
    conn.close()


def get_latest_readings(limit=50, path=DB_PATH):
    conn = get_connection(path)
    cursor = conn.execute(
        "SELECT timestamp, temperature, pressure, vibration FROM readings ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_readings(path=DB_PATH):
    conn = get_connection(path)
    cursor = conn.execute(
        "SELECT timestamp, temperature, pressure, vibration FROM readings ORDER BY id ASC"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_thresholds(path=DB_PATH):
    conn = get_connection(path)
    cursor = conn.execute("SELECT metric, warn_boundary, fault_boundary FROM thresholds")
    rows = cursor.fetchall()
    conn.close()
    return {metric: (warn_boundary, fault_boundary) for metric, warn_boundary, fault_boundary in rows}
