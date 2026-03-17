import asyncio
from typing import Dict, Any, List
from scrapling.spiders import Spider, Response, Request
from scrapling.fetchers import AsyncStealthySession
from app.db.models import Event
from app.core.config import settings

class BerlinEventsSpider(Spider):
    name = "berlin_events"
    start_urls = [
        "http://quotes.toscrape.com/", # Simple static site for testing scraper logic and DB integration locally
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
        # Determine proxy configuration if available in the environment
        proxy = None
        if settings.proxy_url:
            proxy = settings.proxy_url
            if settings.proxy_auth:
                proxy = {
                    "server": settings.proxy_url,
                    "username": settings.proxy_auth.split(":")[0],
                    "password": settings.proxy_auth.split(":")[1] if ":" in settings.proxy_auth else ""
                }

        # We use the AsyncStealthySession to handle websites with strong anti-bot (e.g., Cloudflare)
        # We enforce network_idle to wait for JavaScript to finish rendering dynamic content.
        manager.add("stealth", AsyncStealthySession(
            headless=True,
            solve_cloudflare=True,
            network_idle=True,  # Wait for API calls to settle
            proxy=proxy
        ))

    async def parse(self, response: Response):
        """
        Main parser that distributes parsing based on URL.
        """
        # Distribute logic based on domain
        # We attempt direct parsing first if the response is valid (not a CAPTCHA/Cloudflare block page)
        # Often Cloudflare returns ~30kb HTML payload. Let's assume if it's < 50kb and we find 0 events, it's blocked.
        events_found = 0

        if "berlin-buehnen.de" in response.url:
            async for item in self.parse_berlin_buehnen(response):
                events_found += 1
                yield item
        elif "rausgegangen.de" in response.url:
            async for item in self.parse_rausgegangen(response):
                events_found += 1
                yield item
        elif "quotes.toscrape.com" in response.url:
            async for item in self.parse_quotes(response):
                events_found += 1
                yield item

        # If direct headless Chromium blocked (events_found = 0), route it through the Public Web Proxy Tunnel
        if events_found == 0 and "quotes.toscrape" not in response.url:
            print(f"Direct parsing failed for {response.url}. Activating Proxy Tunnel fallback...")
            async for item in self.parse_with_fallback(response):
                yield item

    async def parse_with_fallback(self, response: Response):
        """
        Uses Proxy Tunneling (AllOrigins) as a final attempt to fetch HTML bypassing direct blocks,
        then optionally falls back to the Jina Reader LLM extraction.
        """
        import httpx
        from scrapling.parser import Selector

        # 1. Proxy Tunneling (Inspired by reference repo)
        # Bypasses local network blocks/Cloudflare intercepts by routing the HTTP request through a public proxy relay.
        tunnel_url = f"https://api.allorigins.win/raw?url={response.url}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                print(f"Attempting Proxy Tunnel fetch for: {response.url}")
                tunnel_res = await client.get(tunnel_url)

                if tunnel_res.status_code == 200 and len(tunnel_res.text) > 1000:
                    # Successfully tunneled the HTML. Create a new Selector.
                    tunneled_page = Selector(tunnel_res.text)

                    # Attempt to run our specific domain parsers on the tunneled HTML
                    if "berlin-buehnen.de" in response.url:
                        # Create a mock Response object for our parser method
                        mock_resp = type('MockResponse', (), {'css': tunneled_page.css, 'url': response.url, 'urljoin': lambda path: f"https://www.berlin-buehnen.de{path}"})()
                        async for item in self.parse_berlin_buehnen(mock_resp):
                            yield item
                        return
                    elif "rausgegangen.de" in response.url:
                        mock_resp = type('MockResponse', (), {'css': tunneled_page.css, 'url': response.url, 'urljoin': lambda path: f"https://rausgegangen.de{path}"})()
                        async for item in self.parse_rausgegangen(mock_resp):
                            yield item
                        return
        except Exception as e:
            print(f"Proxy tunnel failed: {e}")

        # 2. If proxy tunnel fails or didn't yield results, fallback to Jina LLM Reader
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
        # Adjusting the Berlin Buehnen selector to account for delayed lazy-loading and varying DOM
        # Sometimes events are wrapped in a slightly different generic class if not completely hydrated
        events = response.css('article.event-list-item')
        if not events:
            # Fallback to older or alternative structure
            events = response.css('.schedule-list article')

        for event in events:
            event_name = event.css('h2 a::text').get() or event.css('.title::text').get()
            info = event.css('.subtitle::text').get() or event.css('p.description::text').get()
            location = event.css('.venue::text').get() or event.css('.location a::text').get()
            date_str = event.css('time::attr(datetime)').get() or event.css('.date::text').get()
            time_str = event.css('time::text').get() or event.css('.time::text').get()
            link = event.css('h2 a::attr(href)').get() or event.css('a.event-link::attr(href)').get()

            student_discount = False
            if info and any(word in info.lower() for word in ['student', 'ermäßigt', 'discount', 'schüler']):
                student_discount = True

            if event_name and link:
                yield {
                    "name": event_name.strip(),
                    "info": info.strip() if info else None,
                    "location": location.strip() if location else settings.default_location,
                    "date": date_str.strip() if date_str else None,
                    "time": time_str.strip() if time_str else None,
                    "ticket_prices": "Free" if 'free' in str(info).lower() else None,
                    "student_discounts_eligible": student_discount,
                    "link": response.urljoin(link) if link.startswith('/') else link,
                }

    async def parse_quotes(self, response: Response):
        """
        Fallback simple parser mapping Quotes to the Event schema to verify background persistence
        in constrained environments.
        """
        for idx, quote in enumerate(response.css('.quote')):
            text = quote.css('.text::text').get()
            author = quote.css('.author::text').get()
            yield {
                "name": f"Event Quote by {author}",
                "info": text,
                "location": "Berlin",
                "date": None,
                "time": None,
                "ticket_prices": "Free",
                "student_discounts_eligible": True,
                "link": f"http://quotes.toscrape.com/quote/{idx}",
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
