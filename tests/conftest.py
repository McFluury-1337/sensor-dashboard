import os
import tempfile

import pytest
from werkzeug.security import generate_password_hash

import app as app_module
import db

TEST_API_KEY = "test-api-key"
TEST_USERNAME = "admin"
TEST_PASSWORD = "test-password"


@pytest.fixture
def client(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(app_module, "API_KEY", TEST_API_KEY)
    app_module.app.secret_key = "test-secret-key"
    db.init_db()
    db.upsert_user(TEST_USERNAME, generate_password_hash(TEST_PASSWORD))

    app_module.app.testing = True
    with app_module.app.test_client() as test_client:
        yield test_client

    os.remove(path)
