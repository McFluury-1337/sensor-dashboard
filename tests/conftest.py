import os
import tempfile

import pytest

import app as app_module
import db

TEST_API_KEY = "test-api-key"


@pytest.fixture
def client(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(app_module, "API_KEY", TEST_API_KEY)
    db.init_db()

    app_module.app.testing = True
    with app_module.app.test_client() as test_client:
        yield test_client

    os.remove(path)
