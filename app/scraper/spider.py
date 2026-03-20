import asyncio
from typing import Dict, Any, List
from datetime import datetime
import re
from scrapling.spiders import Spider, Response, Request
from scrapling.fetchers import AsyncStealthySession, FetcherSession, ProxyRotator
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
    concurrent_requests = 4

    def configure_sessions(self, manager):
        # Configure advanced proxy rotator if available
        rotator = None
        if settings.proxy_url:
            proxy_config = settings.proxy_url
            if settings.proxy_auth:
                proxy_config = {
                    "server": settings.proxy_url,
                    "username": settings.proxy_auth.split(":")[0],
                    "password": settings.proxy_auth.split(":")[1] if ":" in settings.proxy_auth else ""
                }
            rotator = ProxyRotator([proxy_config])

        # 1. Stealthy Session (Browser automation for heavy anti-bot & SPAs)
        # We enforce network_idle=True to wait for JavaScript to finish rendering dynamic content like React elements.
        manager.add("stealth", AsyncStealthySession(
            headless=True,
            solve_cloudflare=True,
            network_idle=True,
            proxy_rotator=rotator if rotator else None,
            block_webrtc=True,
            hide_canvas=True
        ), lazy=True)

        # 2. Fast HTTP Session (Lightweight impersonated HTTP requests for static/less protected sites)
        manager.add("fast", FetcherSession(
            impersonate="chrome",
            proxy_rotator=rotator if rotator else None
        ))

    async def is_blocked(self, response: Response) -> bool:
        """
        Custom block detection overriding the default Scrapling logic to catch Cloudflare challenges
        or generic IP bans before parsing.
        """
        if response.status in {403, 429, 503}:
            return True

        body_text = ""
        try:
            body_text = response.text.lower() if hasattr(response, 'text') else response.body.decode("utf-8", errors="ignore").lower()
        except:
            pass

        if "just a moment" in body_text or "cloudflare" in body_text or "access denied" in body_text:
            return True
        return False

    async def retry_blocked_request(self, request: Request, response: Response) -> Request:
        """
        If a fast HTTP request gets blocked, bump it up to the stealth browser session!
        """
        self.logger.warning(f"[ANTI-BOT] Blocked on {request.url} with session {request.sid}. Retrying with stealth browser...")
        request.sid = "stealth"
        return request

    def parse_iso_date(self, date_str: str) -> str | None:
        """
        Normalizes dates to ISO 8601 string format.
        """
        if not date_str: return None
        # Naive extraction - a real implementation would use dateutil.parser
        try:
            # Often dates come in as 'YYYY-MM-DD' or full datetimes
            match = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
            if match:
                dt = datetime.strptime(match.group(1), '%Y-%m-%d')
                return dt.isoformat()
        except:
            pass
        return date_str # Return raw if unable to normalize

    async def parse(self, response: Response):
        """
        Main parser that distributes parsing based on URL.
        """
        # Route requests based on domain structure directly without external API dependencies.
        # Sites that frequently use "fast" session ID are inherently fast & reliable.
        # Sites using "stealth" sid are utilizing the headless Chromium with NetworkIdle rendering.

        # Route dynamically if this is a starting request!
        if response.request.sid == "default":
            # If the user submitted a base URL, route it efficiently based on known protections.
            if any(domain in response.url for domain in ["berlin-buehnen.de", "rausgegangen.de", "eventbrite.de"]):
                self.logger.info(f"Routing {response.url} through Stealth JS Session")
                yield Request(response.url, callback=self.parse, sid="stealth")
                return
            else:
                self.logger.info(f"Routing {response.url} through Fast HTTP Session")
                yield Request(response.url, callback=self.parse, sid="fast")
                return

        events_found = 0
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

        self.logger.info(f"[DEBUG - Scrapling] Finished CSS parsing for {response.url} (Session: {response.request.sid}) - Events found: {events_found}")

        # Final Fallback to Jina LLM if Scrapling Native fails to find items due to major layout shifts
        if events_found == 0:
            self.logger.warning(f"Zero events parsed organically on {response.url}. Attempting emergency Jina LLM extraction...")
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
            import traceback
            print(f"[DEBUG - Jina] Fallback request failed: {e}")
            traceback.print_exc()

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
                full_link = response.urljoin(link) if link.startswith('/') else link
                event_data = {
                    "name": event_name.strip(),
                    "info": info.strip() if info else None,
                    "location": location.strip() if location else settings.default_location,
                    "date": self.parse_iso_date(date_str),
                    "time": time_str.strip() if time_str else None,
                    "ticket_prices": "Free" if 'free' in str(info).lower() else None,
                    "student_discounts_eligible": student_discount,
                    "link": full_link,
                }

                # Internal Link Traversal Demonstration
                # We yield a Request to dive into the ticket page to get actual prices if it's not marked free.
                if event_data["ticket_prices"] is None and not settings.proxy_url:
                    yield Request(full_link, callback=self.parse_ticket_page, meta={"event_data": event_data}, sid="fast")
                else:
                    yield event_data

    async def parse_ticket_page(self, response: Response):
        """
        Secondary parser to extract specific ticket prices from an event's detail page.
        """
        event_data = response.request.meta["event_data"]
        # Dummy ticket extraction from hypothetical sub-page
        price_node = response.css('.price-tag::text').get()
        if price_node:
            event_data["ticket_prices"] = price_node.strip()
        yield event_data

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
