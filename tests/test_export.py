import db


def test_export_requires_start_and_end_params(client):
    response = client.get("/api/readings/export.csv")
    assert response.status_code == 400


def test_export_requires_end_when_start_given(client):
    response = client.get("/api/readings/export.csv?start=2026-09-01")
    assert response.status_code == 400


def test_export_invalid_date_format_returns_400(client):
    response = client.get("/api/readings/export.csv?start=not-a-date&end=2026-09-23")
    assert response.status_code == 400


def test_export_returns_csv_with_readings_in_range(client):
    db.insert_reading("2026-09-10T12:00:00", 70.0, 5.0, 0.5)
    db.insert_reading("2026-09-15T12:00:00", 75.0, 5.5, 0.6)

    response = client.get("/api/readings/export.csv?start=2026-09-01&end=2026-09-23")

    assert response.status_code == 200
    assert response.content_type.startswith("text/csv")

    body = response.get_data(as_text=True)
    lines = body.strip().splitlines()
    assert lines[0] == "timestamp,temperature,pressure,vibration"
    assert len(lines) == 3
    assert "70.0" in lines[1]
    assert "75.0" in lines[2]


def test_export_excludes_readings_outside_range(client):
    db.insert_reading("2026-08-01T12:00:00", 60.0, 4.0, 0.3)
    db.insert_reading("2026-09-10T12:00:00", 70.0, 5.0, 0.5)
    db.insert_reading("2026-10-01T12:00:00", 90.0, 7.0, 1.5)

    response = client.get("/api/readings/export.csv?start=2026-09-01&end=2026-09-30")

    body = response.get_data(as_text=True)
    lines = body.strip().splitlines()
    assert len(lines) == 2
    assert "70.0" in lines[1]


def test_export_has_attachment_content_disposition(client):
    response = client.get("/api/readings/export.csv?start=2026-09-01&end=2026-09-23")
    assert "attachment" in response.headers.get("Content-Disposition", "")
