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

        # Add basic debugging to track the DOM payload
        text_content = ""
        try:
            text_content = response.text if hasattr(response, 'text') else str(response.body)
            print(f"[DEBUG - Direct] {response.url} returned HTML length: {len(text_content)} bytes")
        except Exception:
            print(f"[DEBUG - Direct] {response.url} failed to read text/body.")

        if "berlin-buehnen.de" in response.url:
            async for item in self.parse_berlin_buehnen(response):
                events_found += 1
                yield item
        elif "rausgegangen.de" in response.url:
            async for item in self.parse_rausgegangen(response):
                events_found += 1
                yield item
        elif "berliner-ensemble.de" in response.url:
            async for item in self.parse_berliner_ensemble(response):
                events_found += 1
                yield item
        elif "oper-in-berlin.de" in response.url:
            async for item in self.parse_oper_berlin(response):
                events_found += 1
                yield item
        elif "improfabrik.de" in response.url:
            async for item in self.parse_improfabrik(response):
                events_found += 1
                yield item
        elif "eventbrite.de" in response.url:
            async for item in self.parse_eventbrite(response):
                events_found += 1
                yield item
        elif "quotes.toscrape.com" in response.url:
            async for item in self.parse_quotes(response):
                events_found += 1
                yield item

        print(f"[DEBUG - Direct] Finished CSS parsing for {response.url} - Events found: {events_found}")

        # If direct headless Chromium blocked (events_found = 0), route it through the Public Web Proxy Tunnel
        if events_found == 0 and "quotes.toscrape" not in response.url:
            print(f"[DEBUG - Fallback] Direct parsing failed for {response.url}. Activating Proxy Tunnel fallback...")
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
                print(f"[DEBUG - Tunnel] Fetching: {tunnel_url}")
                tunnel_res = await client.get(tunnel_url)

                if tunnel_res.status_code == 200 and len(tunnel_res.text) > 1000:
                    print(f"[DEBUG - Tunnel] Success: Fetched {len(tunnel_res.text)} bytes for {response.url}")
                    # Successfully tunneled the HTML. Create a new Selector.
                    tunneled_page = Selector(tunnel_res.text)

                    # Attempt to run our specific domain parsers on the tunneled HTML
                    if "berlin-buehnen.de" in response.url:
                        # Create a Tunneled Response object to mimic Scrapling's Response API for the parsers
                        tunneled_resp = type('TunneledResponse', (), {'css': tunneled_page.css, 'url': response.url, 'urljoin': lambda self, path: f"https://www.berlin-buehnen.de{path}"})()
                        async for item in self.parse_berlin_buehnen(tunneled_resp):
                            yield item
                        return
                    elif "rausgegangen.de" in response.url:
                        tunneled_resp = type('TunneledResponse', (), {'css': tunneled_page.css, 'url': response.url, 'urljoin': lambda self, path: f"https://rausgegangen.de{path}"})()
                        async for item in self.parse_rausgegangen(tunneled_resp):
                            yield item
                        return
                    elif "berliner-ensemble.de" in response.url:
                        tunneled_resp = type('TunneledResponse', (), {'css': tunneled_page.css, 'url': response.url, 'urljoin': lambda self, path: f"https://www.berliner-ensemble.de{path}"})()
                        async for item in self.parse_berliner_ensemble(tunneled_resp):
                            yield item
                        return
                    elif "oper-in-berlin.de" in response.url:
                        tunneled_resp = type('TunneledResponse', (), {'css': tunneled_page.css, 'url': response.url, 'urljoin': lambda self, path: f"https://www.oper-in-berlin.de{path}"})()
                        async for item in self.parse_oper_berlin(tunneled_resp):
                            yield item
                        return
                    elif "improfabrik.de" in response.url:
                        tunneled_resp = type('TunneledResponse', (), {'css': tunneled_page.css, 'url': response.url, 'urljoin': lambda self, path: f"https://improfabrik.de{path}"})()
                        async for item in self.parse_improfabrik(tunneled_resp):
                            yield item
                        return
                    elif "eventbrite.de" in response.url:
                        tunneled_resp = type('TunneledResponse', (), {'css': tunneled_page.css, 'url': response.url, 'urljoin': lambda self, path: f"https://www.eventbrite.de{path}"})()
                        async for item in self.parse_eventbrite(tunneled_resp):
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
            print(f"Skipping Jina Reader fallback for {response.url}: JINA_API_KEY environment variable not set.")
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

    async def parse_improfabrik(self, response: Response):
        """
        Parses events from improfabrik.de
        """
        events = response.css('.mec-event-article') or response.css('article.mec-event-item')
        for event in events:
            event_name = event.css('.mec-event-title a::text').get() or event.css('h4 a::text').get()
            date_str = event.css('.mec-event-date::text').get() or event.css('.mec-start-date-label::text').get()
            time_str = event.css('.mec-event-time::text').get() or event.css('.mec-time-details::text').get()
            link = event.css('.mec-event-title a::attr(href)').get() or event.css('h4 a::attr(href)').get()

            if event_name and link:
                yield {
                    "name": event_name.strip(),
                    "info": event.css('.mec-event-description::text').get(),
                    "location": event.css('.mec-event-location::text').get() or "Improfabrik Berlin",
                    "date": date_str.strip() if date_str else None,
                    "time": time_str.strip() if time_str else None,
                    "ticket_prices": None,
                    "student_discounts_eligible": True,
                    "link": response.urljoin(link) if link.startswith('/') else link,
                }

    async def parse_eventbrite(self, response: Response):
        """
        Parses events from eventbrite.de
        """
        events = response.css('.discover-search-desktop-card') or response.css('div[data-testid="search-results-list"] article')
        for event in events:
            event_name = event.css('h3::text').get() or event.css('h2[data-testid="event-card-title"]::text').get()
            location = event.css('.event-card__subtitle::text').get() or event.css('[data-testid="event-card-location"]::text').get()
            date_str = event.css('.event-card__date::text').get() or event.css('p.Typography_body-md-bold__487rx::text').get()
            ticket_prices = event.css('[data-testid="event-card-price"]::text').get()
            link = event.css('a.event-card-link::attr(href)').get() or event.css('a::attr(href)').get()

            if event_name and link:
                yield {
                    "name": event_name.strip(),
                    "info": None,
                    "location": location.strip() if location else "Berlin",
                    "date": date_str.strip() if date_str else None,
                    "time": None,
                    "ticket_prices": ticket_prices.strip() if ticket_prices else None,
                    "student_discounts_eligible": False,
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
        events = response.css('.EventCard_eventCard__2L1N_')
        if not events:
            events = response.css('a[class*="EventCard"]')

        for event in events:
            event_name = event.css('h3::text').get() or event.css('.EventCard_title__1Hl0V::text').get()
            location = event.css('.EventCard_location__2G_7p::text').get() or event.css('[class*="location"]::text').get()
            date_str = event.css('.EventCard_date__1vP_l::text').get() or event.css('[class*="date"]::text').get()
            link = event.css('::attr(href)').get()
            if not link and event.name == 'a':
                link = event.attrib.get('href')

            if event_name and link:
                yield {
                    "name": event_name.strip(),
                    "info": None,
                    "location": location.strip() if location else "Berlin",
                    "date": date_str.strip() if date_str else None,
                    "time": None,
                    "ticket_prices": None,
                    "student_discounts_eligible": False,
                    "link": response.urljoin(link) if link.startswith('/') else link,
                }

    async def parse_berliner_ensemble(self, response: Response):
        """
        Parses events from berliner-ensemble.de/spielplan
        """
        events = response.css('.view-content .views-row')
        for event in events:
            event_name = event.css('.title a::text').get() or event.css('.field-name-title a::text').get()
            date_str = event.css('.date-display-single::attr(content)').get()
            time_str = event.css('.date-display-single::text').get()
            link = event.css('.title a::attr(href)').get()

            if event_name and link:
                yield {
                    "name": event_name.strip(),
                    "info": event.css('.field-name-field-subtitle::text').get(),
                    "location": "Berliner Ensemble",
                    "date": date_str.strip() if date_str else None,
                    "time": time_str.strip() if time_str else None,
                    "ticket_prices": None,
                    "student_discounts_eligible": True,
                    "link": response.urljoin(link) if link.startswith('/') else link,
                }

    async def parse_oper_berlin(self, response: Response):
        """
        Parses events from oper-in-berlin.de
        """
        events = response.css('.event-item') or response.css('.spielplan-item')
        for event in events:
            event_name = event.css('h2 a::text').get() or event.css('.title::text').get()
            date_str = event.css('time::attr(datetime)').get()
            link = event.css('h2 a::attr(href)').get() or event.css('a.link::attr(href)').get()

            if event_name and link:
                yield {
                    "name": event_name.strip(),
                    "info": event.css('.subtitle::text').get(),
                    "location": event.css('.location::text').get() or "Oper in Berlin",
                    "date": date_str.strip() if date_str else None,
                    "time": event.css('.time::text').get(),
                    "ticket_prices": None,
                    "student_discounts_eligible": True,
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
