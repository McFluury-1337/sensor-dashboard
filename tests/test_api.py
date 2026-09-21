from conftest import TEST_API_KEY

VALID_PAYLOAD = {"temperature": 70.5, "pressure": 5.0, "vibration": 0.5}


def test_valid_post_returns_201_and_reading_is_saved(client):
    response = client.post(
        "/api/readings", json=VALID_PAYLOAD, headers={"X-API-Key": TEST_API_KEY}
    )
    assert response.status_code == 201

    saved = client.get("/api/readings?limit=1").get_json()
    assert len(saved) == 1
    assert saved[0]["temperature"] == 70.5
    assert saved[0]["pressure"] == 5.0
    assert saved[0]["vibration"] == 0.5


def test_post_without_key_returns_401(client):
    response = client.post("/api/readings", json=VALID_PAYLOAD)
    assert response.status_code == 401


def test_post_with_wrong_key_returns_401(client):
    response = client.post(
        "/api/readings", json=VALID_PAYLOAD, headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 401


def test_post_with_text_instead_of_number_returns_400(client):
    payload = {"temperature": "hot", "pressure": 5.0, "vibration": 0.5}
    response = client.post(
        "/api/readings", json=payload, headers={"X-API-Key": TEST_API_KEY}
    )
    assert response.status_code == 400


def test_post_with_negative_pressure_returns_400(client):
    payload = {"temperature": 70.5, "pressure": -1.0, "vibration": 0.5}
    response = client.post(
        "/api/readings", json=payload, headers={"X-API-Key": TEST_API_KEY}
    )
    assert response.status_code == 400


def test_post_with_missing_field_returns_400(client):
    payload = {"temperature": 70.5, "pressure": 5.0}
    response = client.post(
        "/api/readings", json=payload, headers={"X-API-Key": TEST_API_KEY}
    )
    assert response.status_code == 400


def test_get_readings_works_without_key(client):
    client.post("/api/readings", json=VALID_PAYLOAD, headers={"X-API-Key": TEST_API_KEY})
    response = client.get("/api/readings?limit=5")
    assert response.status_code == 200
    assert len(response.get_json()) == 1
