import sqlite3

from werkzeug.security import generate_password_hash

import config

DB_PATH = "sensors.db"

BACKEND = config.get("DB_BACKEND", "sqlite")

DEFAULT_THRESHOLDS = {
    "temperature": (74, 83),
    "pressure": (5.4, 6.2),
    "vibration": (0.7, 1.2),
}

_SQLITE_SQL = {
    "placeholder": "?",
    "create_readings": """
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temperature REAL NOT NULL,
            pressure REAL NOT NULL,
            vibration REAL NOT NULL
        )
    """,
    "create_thresholds": """
        CREATE TABLE IF NOT EXISTS thresholds (
            metric TEXT PRIMARY KEY,
            warn_boundary REAL NOT NULL,
            fault_boundary REAL NOT NULL
        )
    """,
    "create_users": """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    """,
    "insert_ignore_threshold": (
        "INSERT OR IGNORE INTO thresholds (metric, warn_boundary, fault_boundary) VALUES (?, ?, ?)"
    ),
    "upsert_user": """
        INSERT INTO users (username, password_hash) VALUES (?, ?)
        ON CONFLICT(username) DO UPDATE SET password_hash = excluded.password_hash
    """,
}

_MYSQL_SQL = {
    "placeholder": "%s",
    "create_readings": """
        CREATE TABLE IF NOT EXISTS readings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            timestamp VARCHAR(32) NOT NULL,
            temperature DOUBLE NOT NULL,
            pressure DOUBLE NOT NULL,
            vibration DOUBLE NOT NULL
        )
    """,
    "create_thresholds": """
        CREATE TABLE IF NOT EXISTS thresholds (
            metric VARCHAR(32) PRIMARY KEY,
            warn_boundary DOUBLE NOT NULL,
            fault_boundary DOUBLE NOT NULL
        )
    """,
    "create_users": """
        CREATE TABLE IF NOT EXISTS users (
            username VARCHAR(64) PRIMARY KEY,
            password_hash VARCHAR(255) NOT NULL
        )
    """,
    "insert_ignore_threshold": (
        "INSERT IGNORE INTO thresholds (metric, warn_boundary, fault_boundary) VALUES (%s, %s, %s)"
    ),
    "upsert_user": """
        INSERT INTO users (username, password_hash) VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash)
    """,
}


def _sql(key):
    # BACKEND читается заново при каждом вызове (а не один раз при импорте
    # модуля), чтобы monkeypatch.setattr(db, "BACKEND", ...) в тестах реально
    # переключал диалект SQL — как и path=None в остальных функциях этого файла.
    return (_MYSQL_SQL if BACKEND == "mysql" else _SQLITE_SQL)[key]


def get_connection(path=None):
    if BACKEND == "mysql":
        import pymysql

        return pymysql.connect(
            host=config.get("DB_HOST", "localhost"),
            port=int(config.get("DB_PORT", "3306")),
            user=config.get("DB_USER"),
            password=config.get("DB_PASSWORD"),
            database=config.get("DB_NAME"),
            charset="utf8mb4",
            autocommit=False,
        )
    return sqlite3.connect(path if path is not None else DB_PATH)


def _execute(conn, sql, params=()):
    if BACKEND == "mysql":
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor
    return conn.execute(sql, params)


def init_db(path=None):
    conn = get_connection(path)
    _execute(conn, _sql("create_readings"))
    _execute(conn, _sql("create_thresholds"))
    for metric, (warn_boundary, fault_boundary) in DEFAULT_THRESHOLDS.items():
        _execute(conn, _sql("insert_ignore_threshold"), (metric, warn_boundary, fault_boundary))
    _execute(conn, _sql("create_users"))

    user_count = _execute(conn, "SELECT COUNT(*) FROM users").fetchone()[0]
    admin_password = config.get("ADMIN_PASSWORD")
    if user_count == 0 and admin_password:
        admin_username = config.get("ADMIN_USERNAME", "admin")
        p = _sql("placeholder")
        _execute(
            conn,
            f"INSERT INTO users (username, password_hash) VALUES ({p}, {p})",
            (admin_username, generate_password_hash(admin_password)),
        )
    conn.commit()
    conn.close()


def insert_reading(timestamp, temperature, pressure, vibration, path=None):
    conn = get_connection(path)
    p = _sql("placeholder")
    _execute(
        conn,
        f"INSERT INTO readings (timestamp, temperature, pressure, vibration) VALUES ({p}, {p}, {p}, {p})",
        (timestamp, temperature, pressure, vibration),
    )
    conn.commit()
    conn.close()


def get_latest_readings(limit=50, path=None):
    conn = get_connection(path)
    p = _sql("placeholder")
    cursor = _execute(
        conn,
        f"SELECT timestamp, temperature, pressure, vibration FROM readings ORDER BY id DESC LIMIT {p}",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_readings(path=None):
    conn = get_connection(path)
    cursor = _execute(
        conn, "SELECT timestamp, temperature, pressure, vibration FROM readings ORDER BY id ASC"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_readings_in_range(start, end, path=None):
    conn = get_connection(path)
    p = _sql("placeholder")
    cursor = _execute(
        conn,
        f"SELECT timestamp, temperature, pressure, vibration FROM readings "
        f"WHERE timestamp >= {p} AND timestamp <= {p} ORDER BY id ASC",
        (start, end),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_thresholds(path=None):
    conn = get_connection(path)
    cursor = _execute(conn, "SELECT metric, warn_boundary, fault_boundary FROM thresholds")
    rows = cursor.fetchall()
    conn.close()
    return {metric: (warn_boundary, fault_boundary) for metric, warn_boundary, fault_boundary in rows}


def update_threshold(metric, warn_boundary, fault_boundary, path=None):
    conn = get_connection(path)
    p = _sql("placeholder")
    _execute(
        conn,
        f"UPDATE thresholds SET warn_boundary = {p}, fault_boundary = {p} WHERE metric = {p}",
        (warn_boundary, fault_boundary, metric),
    )
    conn.commit()
    conn.close()


def get_user(username, path=None):
    conn = get_connection(path)
    p = _sql("placeholder")
    cursor = _execute(conn, f"SELECT password_hash FROM users WHERE username = {p}", (username,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def upsert_user(username, password_hash, path=None):
    conn = get_connection(path)
    _execute(conn, _sql("upsert_user"), (username, password_hash))
    conn.commit()
    conn.close()
