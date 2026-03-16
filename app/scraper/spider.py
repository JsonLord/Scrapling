import asyncio
from typing import Dict, Any, List
from scrapling.spiders import Spider, Response, Request
from scrapling.fetchers import StealthySession
from app.db.models import Event
from app.core.config import settings

class BerlinEventsSpider(Spider):
    name = "berlin_events"
    start_urls = [
        "https://www.berlin-buehnen.de/en/schedule",
        "https://rausgegangen.de/en/berlin/",
        "https://www.berliner-ensemble.de/spielplan",
        "https://improfabrik.de/",
        "https://www.oper-in-berlin.de/en/",
        "https://www.eventbrite.de/d/germany--berlin/events/"
    ]

    # Scrapling Spider configuration
    concurrent_requests = 5

    def configure_sessions(self, manager):
        # We will use the StealthySession to handle websites with strong anti-bot (e.g., Cloudflare)
        # We run it headless for production.
        manager.add("stealth", StealthySession(headless=True, solve_cloudflare=True))

    async def parse(self, response: Response):
        """
        Main parser that distributes parsing based on URL.
        """
        # Distribute logic based on domain
        if "berlin-buehnen.de" in response.url:
            async for item in self.parse_berlin_buehnen(response):
                yield item
        elif "rausgegangen.de" in response.url:
            async for item in self.parse_rausgegangen(response):
                yield item
        else:
            # Fallback logic utilizing Jina Reader API
            async for item in self.parse_with_jina(response):
                yield item

    async def parse_with_jina(self, response: Response):
        """
        Fallback parser that utilizes the Jina Reader API to extract structured data
        from an unknown website layout using an LLM prompt.
        """
        import json
        import httpx
        from app.core.config import settings

        api_key = settings.jina_api_key
        if not api_key:
            # If no API key is provided, we can't do the fallback
            return

        jina_url = "https://r.jina.ai/" + response.url
        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Return-Format": "json"
        }

        prompt = (
            "Extract a list of events from this page. For each event, provide a JSON object with keys: "
            "'name', 'info' (short description), 'location', 'date' (YYYY-MM-DD), 'time' (HH:MM), "
            "'ticket_prices', 'student_discounts_eligible' (boolean), and 'link'."
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(jina_url, headers=headers, json={"url": response.url, "prompt": prompt})

                if res.status_code == 200:
                    data = res.json()
                    # The response from Jina often contains a text block that needs parsing
                    # We assume it returns an array of JSON objects based on the prompt
                    if "data" in data and "text" in data["data"]:
                        text_response = data["data"]["text"]
                        try:
                            # Try to extract JSON from the text response
                            # A real implementation would need more robust regex or JSON-extraction logic
                            import re
                            json_match = re.search(r'\[.*\]', text_response, re.DOTALL)
                            if json_match:
                                events = json.loads(json_match.group(0))
                                for event in events:
                                    if event.get("name"):
                                        yield event
                        except json.JSONDecodeError:
                            print(f"Failed to decode Jina response for {response.url}")
        except Exception as e:
            print(f"Jina fallback request failed: {e}")

    async def parse_berlin_buehnen(self, response: Response):
        """
        Parses events from berlin-buehnen.de/schedule
        """
        # Note: This is a conceptual implementation of the selector based on the expected structure
        # of the site. In a real scenario, this is iteratively adjusted.
        events = response.css('.schedule-item') # adjust the CSS selector as needed
        for event in events:
            # Extract basic data points
            event_name = event.css('.event-title::text').get()
            info = event.css('.event-description::text').get()
            location = event.css('.event-location::text').get()
            date_str = event.css('.event-date::text').get()
            time_str = event.css('.event-time::text').get()
            ticket_prices = event.css('.event-price::text').get()
            link = event.css('a.event-link::attr(href)').get()

            # Semantic parsing/heuristics: check if student discount is likely based on text
            # E.g., 'ermäßigt', 'student', 'studentenrabatt'
            student_discount = False
            if info and any(word in info.lower() for word in ['student', 'ermäßigt', 'discount']):
                student_discount = True

            if event_name and link:
                yield {
                    "name": event_name.strip(),
                    "info": info.strip() if info else None,
                    "location": location.strip() if location else settings.default_location,
                    "date": date_str.strip() if date_str else None,  # Needs datetime parsing
                    "time": time_str.strip() if time_str else None,
                    "ticket_prices": ticket_prices.strip() if ticket_prices else None,
                    "student_discounts_eligible": student_discount,
                    "link": response.urljoin(link) if link.startswith('/') else link,
                }

    async def parse_rausgegangen(self, response: Response):
        """
        Parses events from rausgegangen.de
        """
        events = response.css('.event-card') # conceptual selector
        for event in events:
            event_name = event.css('h3::text').get()
            info = event.css('.description::text').get()
            location = event.css('.venue::text').get()
            date_str = event.css('.date::text').get()
            time_str = event.css('.time::text').get()
            ticket_prices = event.css('.price::text').get()
            link = event.css('a::attr(href)').get()

            if event_name and link:
                yield {
                    "name": event_name.strip(),
                    "info": info.strip() if info else None,
                    "location": location.strip() if location else settings.default_location,
                    "date": date_str.strip() if date_str else None,
                    "time": time_str.strip() if time_str else None,
                    "ticket_prices": ticket_prices.strip() if ticket_prices else None,
                    "student_discounts_eligible": False,
                    "link": response.urljoin(link) if link.startswith('/') else link,
                }


def run_scraper(target_urls: List[str] = None):
    """
    Entry point to run the scraper synchronously or start the asyncio loop.
    Returns the scraped items.
    """
    spider = BerlinEventsSpider()
    if target_urls:
        spider.start_urls = target_urls

    result = spider.start()

    # Normally you'd want to pipe these results straight to your DB.
    # We return the list of items parsed.
    return result.items
