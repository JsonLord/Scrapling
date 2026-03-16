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

---

# Hugging Face Deployment & API Configuration

## 1. Deployment Configuration

### Target Space
- **Profile:** `harvesthealth`
- **Space:** `magentic-ui`
- **Full Identifier:** `harvesthealth/magentic-ui`
- **Frontend Port:** `7860` (mandatory for all Hugging Face Spaces)

### Deployment Method
- **Docker SDK** — The application is built around FastAPI and Scrapling (which requires Playwright/Chromium dependencies).

### HF Token
- The environment variable **`$HF_TOKEN` will always be provided at execution time**.
- Never hardcode the token. Always read it from the environment.
- All monitoring and log‑streaming commands rely on `$HF_TOKEN`.

### Required Files
- `Dockerfile` (Using Docker SDK, non-root user, exposing 7860)
- `README.md` with Hugging Face YAML frontmatter:
  ```yaml
  ---
  title: Event Scraper
  sdk: docker
  app_port: 7860
  ---
  ```
- `.hfignore` to exclude unnecessary files

---

## 2. API Exposure and Documentation

### Mandatory Endpoints

- **`/health`**
  - Returns HTTP 200 when the app is ready.
  - Required for Hugging Face to transition the Space from *starting* → *running*.

- **`/api-docs`**
  - Documents **all** available API endpoints using OpenAPI (Swagger UI).
  - Must be reachable at: `https://harvesthealth-magentic-ui.hf.space/api-docs`

### Functional Endpoints

### `/api/v1/events`
- **Method:** GET
- **Purpose:** Retrieve a paginated list of parsed events. Can filter by dates, location, or discounts.
- **Request Parameters:** `start_date`, `end_date`, `location`, `has_student_discount` (bool), `limit`, `offset`
- **Response Example:**
  ```json
  [
    {
      "id": 1,
      "name": "Sample Berlin Event",
      "info": "Mock info",
      "location": "Berlin",
      "date": "2024-05-01T20:00:00",
      "time": "20:00",
      "ticket_prices": "15 EUR",
      "student_discounts_eligible": true,
      "link": "https://example.com/event"
    }
  ]
  ```

### `/api/v1/settings`
- **Method:** GET
- **Purpose:** Retrieve global application configuration (default location and active URLs).
- **Response Example:**
  ```json
  {
    "default_location": "Berlin",
    "target_urls": ["https://www.berlin-buehnen.de/en/schedule"]
  }
  ```

### `/api/v1/settings`
- **Method:** PUT
- **Purpose:** Update global configuration (UI settings page).
- **Request Example:**
  ```json
  {
    "default_location": "Munich",
    "target_urls": ["https://example.com/events"]
  }
  ```
- **Response Example:** (Same as request)

### `/api/v1/jobs/crawl`
- **Method:** POST
- **Purpose:** Manually trigger the scraping pipeline for a specific URL or a full crawl.
- **Request Example:**
  ```json
  {
    "target_url": "https://example.com"
  }
  ```
- **Response Example:**
  ```json
  {
    "job_id": "manual-crawl-20240501120000",
    "status": "started"
  }
  ```

---

## 3. Deployment Workflow

### Standard Deployment Command
After any code change, run:

```bash
hf upload harvesthealth/magentic-ui --repo-type=space
```

This command must be executed **after updating and committing Agent.md**.

### Continuous Deployment Rule
After **every** relevant edit (logic, dependencies, API changes):
- Update `Agent.md`
- Redeploy using the upload command
- Re-run all test cases
- Confirm `/health` and `/api-docs` are functional

---

## 4. Monitoring and Logs

### Build Logs (SSE)
```bash
curl -N \
  -H "Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/api/spaces/harvesthealth/magentic-ui/logs/build"
```

### Run Logs (SSE)
```bash
curl -N \
  -H "Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/api/spaces/harvesthealth/magentic-ui/logs/run"
```

---

## 5. Test Run Cases (Mandatory After Every Deployment)

### 1. Health Check
```
GET https://harvesthealth-magentic-ui.hf.space/health
Expected: HTTP 200, body: {"status": "healthy"}
```

### 2. API Docs Check
```
GET https://harvesthealth-magentic-ui.hf.space/api-docs
Expected: HTTP 200, Swagger UI loading properly
```

### 3. Functional Endpoint Tests
- **Events:** `GET /api/v1/events` -> HTTP 200, valid JSON array.
- **Settings GET:** `GET /api/v1/settings` -> HTTP 200, valid JSON object with `default_location` and `target_urls`.
- **Settings PUT:** `PUT /api/v1/settings` -> HTTP 200, valid JSON reflecting requested changes.
- **Trigger Crawl:** `POST /api/v1/jobs/crawl` with empty payload -> HTTP 200, returns `job_id` and `status: started`.
