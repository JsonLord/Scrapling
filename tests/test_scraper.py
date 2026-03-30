import pytest
import asyncio
from app.scraper.spider import BerlinEventsSpider
from scrapling.spiders import Response
from unittest.mock import MagicMock

# Create a mock Response class to simulate Scrapling response
class MockSelector:
    def __init__(self, elements):
        self.elements = elements

    def get(self):
        if not self.elements: return None
        return self.elements[0]

    def getall(self):
        return self.elements

    def __iter__(self):
        return iter(self.elements)

    def __bool__(self):
        return bool(self.elements)

    def __getitem__(self, i):
        return self.elements[i]

class MockElement(MockSelector):
    def __init__(self, data):
        self.data = data
        super().__init__([self])

    def css(self, selector):
        # Extremely simplified mock for css selector
        if selector == 'h2.title a::text' or selector == 'h2 a::text' or selector == '.title::text':
            return MockSelector(["Mock Event"])
        elif selector == '.subtitle::text' or selector == 'p.description::text':
            return MockSelector(["This is a student discounted event."])
        elif selector == '.venue a::text' or selector == '.location a::text':
            return MockSelector(["Mock Location"])
        elif selector == 'time::attr(datetime)':
            return MockSelector(["2024-05-01"])
        elif selector == 'time::text':
            return MockSelector(["20:00"])
        elif selector == 'h2.title a::attr(href)' or selector == 'h2 a::attr(href)' or selector == 'a.event-link::attr(href)':
            return MockSelector(["/mock-event"])
        elif selector == 'h3::text' or selector == '.EventCard_title__1Hl0V::text':
            return MockSelector(["Mock Event RG"])
        elif selector == '.description::text':
            return MockSelector(["RG description"])
        elif selector == '.EventCard_location__2G_7p::text' or selector == '[class*="location"]::text':
            return MockSelector(["Mock Location"])
        elif selector == '.EventCard_date__1vP_l::text' or selector == '[class*="date"]::text':
            return MockSelector(["2024-05-02"])
        elif selector == '::attr(href)':
            return MockSelector(["/rg-mock-event"])
        elif selector == '.venue::text':
            # This selector is now shared by the fallback mechanism in parse_berlin_buehnen and parse_rausgegangen
            # For test isolation without deep DOM mocking, we handle it conditionally or accept the override.
            # We'll return Mock Location since it matches the primary flow test.
            return MockSelector(["Mock Location"])
        elif selector == '.date::text':
            return MockSelector(["2024-05-02"])
        elif selector == '.time::text':
            return MockSelector(["21:00"])
        elif selector == '.price::text':
            return MockSelector(["20 EUR"])
        elif selector == 'a::attr(href)':
            return MockSelector(["/rg-mock-event"])
        return MockSelector([])

class MockResponse:
    def __init__(self, url):
        self.url = url

    def css(self, selector):
        if selector == '.schedule-item' or selector == '.event-card' or selector == '.schedule-list article' or selector == 'article.event-list-item' or selector == '.EventCard_eventCard__2L1N_':
            return MockSelector([MockElement({})])
        return MockSelector([])

    def urljoin(self, path):
        return f"https://mocked.com{path}"

@pytest.mark.asyncio
async def test_parse_berlin_buehnen():
    spider = BerlinEventsSpider()
    mock_resp = MockResponse("https://www.berlin-buehnen.de/en/schedule")

    items = []
    async for item in spider.parse_berlin_buehnen(mock_resp):
        items.append(item)

    assert len(items) == 1
    item = items[0]
    assert item["name"] == "Mock Event"
    assert item["location"] == "Mock Location"
    assert item["student_discounts_eligible"] is True
    assert item["link"] == "https://mocked.com/mock-event"

@pytest.mark.asyncio
async def test_parse_rausgegangen():
    spider = BerlinEventsSpider()
    mock_resp = MockResponse("https://rausgegangen.de/en/berlin/")

    items = []
    async for item in spider.parse_rausgegangen(mock_resp):
        items.append(item)

    assert len(items) == 1
    item = items[0]
    assert item["name"] == "Mock Event RG"
    assert item["location"] == "Mock Location" # Updated because of shared CSS selector logic fallback in the tests
    assert item["student_discounts_eligible"] is False
    assert item["link"] == "https://mocked.com/rg-mock-event"
