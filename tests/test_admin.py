from conftest import TEST_PASSWORD, TEST_USERNAME

import db


def test_admin_without_login_redirects_to_login(client):
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_with_wrong_password_does_not_grant_access(client):
    client.post("/login", data={"username": TEST_USERNAME, "password": "wrong-password"})

    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_with_correct_password_grants_access(client):
    login_response = client.post(
        "/login", data={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    assert login_response.status_code in (200, 302)

    response = client.get("/admin")
    assert response.status_code == 200


def test_manual_reading_requires_login(client):
    response = client.post(
        "/admin/readings",
        data={"temperature": "70", "pressure": "5.0", "vibration": "0.5"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_manual_reading_form_inserts_row_when_logged_in(client):
    client.post("/login", data={"username": TEST_USERNAME, "password": TEST_PASSWORD})

    client.post(
        "/admin/readings",
        data={"temperature": "70", "pressure": "5.0", "vibration": "0.5"},
    )

    rows = db.get_latest_readings(1)
    assert len(rows) == 1
    assert rows[0][1] == 70.0


def test_thresholds_form_updates_thresholds_when_logged_in(client):
    client.post("/login", data={"username": TEST_USERNAME, "password": TEST_PASSWORD})

    client.post(
        "/admin/thresholds",
        data={
            "temperature_warn": "70", "temperature_fault": "90",
            "pressure_warn": "5.0", "pressure_fault": "7.0",
            "vibration_warn": "0.6", "vibration_fault": "1.3",
        },
    )

    thresholds = db.get_thresholds()
    assert thresholds["temperature"] == (70.0, 90.0)


def test_thresholds_form_rejects_warn_above_fault(client):
    client.post("/login", data={"username": TEST_USERNAME, "password": TEST_PASSWORD})
    before = db.get_thresholds()

    client.post(
        "/admin/thresholds",
        data={
            "temperature_warn": "90", "temperature_fault": "70",
            "pressure_warn": "5.0", "pressure_fault": "7.0",
            "vibration_warn": "0.6", "vibration_fault": "1.3",
        },
    )

    after = db.get_thresholds()
    assert after["temperature"] == before["temperature"]


def test_admin_password_is_stored_as_hash_not_plaintext(client):
    stored_hash = db.get_user(TEST_USERNAME)
    assert stored_hash is not None
    assert stored_hash != TEST_PASSWORD
    assert stored_hash.startswith(("pbkdf2:", "scrypt:"))
