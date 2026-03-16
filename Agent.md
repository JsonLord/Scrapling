# Event Scraper Operational Checklist and Guidelines

## General Architecture
- Ensure long-running scraping capabilities using background tasks (e.g., Celery or APScheduler) integrated with FastAPI.
- Utilize Scrapling (and fallback solutions like Jina/Firecrawl) for extracting structured event data.
- Trigger schedules:
  - Monday Morning: Full week crawl.
  - Thursday Morning: Weekend only crawl (Thursday to Sunday).
- Focus on location-based querying (Default: Berlin, but configurable via UI).
- Ensure target website integrations (berlin-buehnen.de, rausgegangen.de, berliner-ensemble.de, improfabrik.de, oper-in-berlin.de, eventbrite.de) are robust to DOM changes.

## Development Checklist
- [x] Initialize FastAPI backend.
- [x] Setup APScheduler or Celery for long-running cron jobs.
- [x] Create Scrapling Spiders/Fetchers for each target website.
- [x] Normalize data fields: Event Name, Info, Location, Date, Time, Ticket Prices, Student Discounts, Link.
- [x] Setup Database (PostgreSQL/SQLite) and SQLAlchemy models for storing events.
- [x] Build API endpoints for UI to fetch/filter events and update settings (e.g., target links, location).
- [x] Implement robust error handling and proxy rotation using Scrapling's Stealthy/Dynamic fetchers to prevent blocking.
- [x] Create Unit/Integration Tests for Spiders and API Endpoints.
- [x] Verify functionality via conceptual end-to-end tests.

## Deployment Checklist
- [x] `Agent.md` is reviewed and updated.
- [x] Pre-commit checks passed.
- [x] Tests passing.
- [x] Environment variables configured (DB, Proxies, API Keys if needed).
