import pytest
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient

from app.main import app
from app import db


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    """Use a temporary database for each test."""
    db_path = str(tmp_path / "test.db")
    with patch.dict("os.environ", {"DB_PATH": db_path}):
        import asyncio
        asyncio.get_event_loop().run_until_complete(db.init_db())
        yield


client = TestClient(app)


class TestListReviews:
    def test_empty_list(self):
        resp = client.get("/api/reviews")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetReview:
    def test_not_found(self):
        resp = client.get("/api/reviews/nonexistent")
        assert resp.status_code == 404


class TestCreateReview:
    def test_missing_github_token(self):
        with patch.dict("os.environ", {"GITHUB_TOKEN": ""}, clear=False):
            resp = client.post("/api/reviews", json={"owner": "test", "repo": "test", "pr_number": 1})
            assert resp.status_code == 400
