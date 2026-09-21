import pymysql
import pytest
from werkzeug.security import generate_password_hash

import db

TEST_DB = dict(
    host="localhost",
    port=3306,
    user="sensor_test",
    password="sensor_test_pw",
    database="sensor_dashboard_test",
)


def _mysql_available():
    try:
        conn = pymysql.connect(**TEST_DB)
        conn.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _mysql_available(), reason="локальная MySQL/MariaDB для теста не поднята"
)


@pytest.fixture
def mysql_db(monkeypatch):
    monkeypatch.setattr(db, "BACKEND", "mysql")
    monkeypatch.setenv("DB_HOST", TEST_DB["host"])
    monkeypatch.setenv("DB_PORT", str(TEST_DB["port"]))
    monkeypatch.setenv("DB_USER", TEST_DB["user"])
    monkeypatch.setenv("DB_PASSWORD", TEST_DB["password"])
    monkeypatch.setenv("DB_NAME", TEST_DB["database"])

    conn = pymysql.connect(**TEST_DB)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS readings")
    cursor.execute("DROP TABLE IF EXISTS thresholds")
    cursor.execute("DROP TABLE IF EXISTS users")
    conn.commit()
    conn.close()

    yield


def test_init_db_creates_tables_and_seeds_thresholds(mysql_db):
    db.init_db()

    thresholds = db.get_thresholds()
    assert thresholds["temperature"] == (74, 83)
    assert thresholds["pressure"] == (5.4, 6.2)
    assert thresholds["vibration"] == (0.7, 1.2)


def test_insert_and_get_latest_readings(mysql_db):
    db.init_db()

    db.insert_reading("2026-09-22T00:00:00", 70.0, 5.0, 0.5)
    db.insert_reading("2026-09-22T00:01:00", 80.0, 5.5, 0.9)

    rows = db.get_latest_readings(1)
    assert len(rows) == 1
    assert rows[0][1] == 80.0

    all_rows = db.get_all_readings()
    assert len(all_rows) == 2
    assert all_rows[0][1] == 70.0


def test_update_threshold_persists(mysql_db):
    db.init_db()

    db.update_threshold("pressure", 5.1, 6.3)

    assert db.get_thresholds()["pressure"] == (5.1, 6.3)


def test_upsert_user_and_get_user(mysql_db):
    db.init_db()

    password_hash = generate_password_hash("hunter2")
    db.upsert_user("admin", password_hash)
    assert db.get_user("admin") == password_hash

    new_hash = generate_password_hash("new-password")
    db.upsert_user("admin", new_hash)
    assert db.get_user("admin") == new_hash


def test_init_db_is_idempotent(mysql_db):
    db.init_db()
    db.update_threshold("temperature", 60, 90)
    db.init_db()

    # повторный init_db не должен затирать уже изменённый порог
    assert db.get_thresholds()["temperature"] == (60, 90)
