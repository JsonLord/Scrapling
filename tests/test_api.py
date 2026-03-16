import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Event Scraper API is running."}

# We mock get_db because these unit tests shouldn't require an actual async db backend to pass
from unittest.mock import AsyncMock
from fastapi import Depends
from app.db.database import get_db

async def override_get_db():
    # Provide a fully mocked session that returns mock data
    mock_session = AsyncMock()

    class MockResult:
        def __init__(self, items):
            self.items = items
        def scalars(self):
            class MockScalars:
                def __init__(self, items):
                    self.items = items
                def all(self):
                    return self.items
                def first(self):
                    return self.items[0] if self.items else None
            return MockScalars(self.items)

    class MockEvent:
        id = 1
        name = "Sample Berlin Event"
        info = "Mock info"
        location = "Berlin"
        date = "2024-05-01T20:00:00" # Needs a proper datetime string for pydantic
        time = "20:00"
        ticket_prices = "15 EUR"
        student_discounts_eligible = True
        link = "https://mock.com"
        scraped_at = "2024-05-01T20:00:00"

    class MockSettings:
        id = 1
        default_location = "Berlin"

    class MockURL:
        url = "https://example.com/mock"

    async def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        if 'events' in stmt_str:
            return MockResult([MockEvent()])
        elif 'system_settings' in stmt_str:
            return MockResult([MockSettings()])
        elif 'target_urls' in stmt_str:
            # We must be careful about exact string matches in testing SQLAlchemy mock strings
            if 'target_urls.url' in stmt_str and 'target_urls.id' not in stmt_str:
                return MockResult([MockURL.url])
            else:
                return MockResult([MockURL()])
        return MockResult([])

    mock_session.execute = mock_execute

    yield mock_session

app.dependency_overrides[get_db] = override_get_db

def test_get_events():
    response = client.get("/api/v1/events")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["name"] == "Sample Berlin Event"

def test_get_settings():
    response = client.get("/api/v1/settings")
    assert response.status_code == 200
    data = response.json()
    assert "default_location" in data
    assert data["default_location"] == "Berlin"
    assert "https://example.com/mock" in data["target_urls"]

def test_update_settings():
    payload = {
        "default_location": "Munich",
        "target_urls": ["https://example.com/events"]
    }
    response = client.put("/api/v1/settings", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["default_location"] == "Munich"
    assert "https://example.com/events" in data["target_urls"]

def test_trigger_manual_crawl():
    response = client.post("/api/v1/jobs/crawl", json={"target_url": "https://example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert "job_id" in data
