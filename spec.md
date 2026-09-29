# Scrapling Web Intelligence API — Development Specification

## 1. Purpose

Transform Scrapling from a powerful web-scraping framework into a self-hostable, agent-native web intelligence service that can compete with products such as Jina Reader/Search while preserving Scrapling's strengths in adaptive scraping, browser automation, anti-bot handling, crawling, proxy support, and resilient selectors.

The target product should make web retrieval feel like an API rather than a scraping project.

The core experience should be:

```text
URL
 ↓
Scrapling Web Intelligence API
 ↓
clean Markdown / JSON / structured evidence
```

Longer-term:

```text
query
 ↓
search
 ↓
Scrapling fetch + extraction
 ↓
ranked evidence corpus
 ↓
agent / RAG / LLM
```

The service should remain useful as:

- a hosted API
- a self-hosted service
- an MCP server
- a Python library
- an agent-facing retrieval backend

---

# 2. Product Principles

## 2.1 Zero-config first

The default path must work without requiring users to choose:

- HTTP vs browser
- stealth vs normal fetching
- proxy mode
- parser strategy
- content-cleaning strategy
- retry policy

Expert controls may exist, but the default should be:

```text
give URL → receive useful content
```

---

## 2.2 Automatic escalation

Scrapling should automatically choose the cheapest working acquisition method.

Default escalation policy:

```text
normal HTTP
 ↓
async / retry
 ↓
stealth fetch
 ↓
browser rendering
 ↓
stealth browser
 ↓
proxy-backed browser
```

The escalation engine should learn which strategies work for which domains.

---

## 2.3 LLM-native output

The product should optimize for downstream agents and RAG systems, not raw scraping.

Primary outputs:

- clean Markdown
- clean text
- normalized HTML
- structured JSON
- evidence blocks with provenance
- links
- metadata
- optional extraction schemas

---

## 2.4 Strong source fidelity

Every extracted block should preserve enough provenance to identify where it came from.

Example:

```json
{
  "type": "paragraph",
  "text": "Example text",
  "source_url": "https://example.com",
  "selector": "#main article p:nth-child(3)",
  "char_start": 421,
  "char_end": 533
}
```

This should enable citation-aware agents and auditable research systems.

---

## 2.5 Self-hostable by design

The service should not depend on a proprietary cloud control plane.

Required deployment modes:

- Docker
- Docker Compose
- standalone Python service
- Hugging Face Spaces-compatible container
- generic Linux host
- optional Kubernetes later

---

# 3. Target Architecture

```text
                         ┌──────────────────┐
                         │      Client      │
                         │ Agent / SDK / UI │
                         └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
                         │    API Gateway   │
                         │ auth / limits    │
                         └────────┬─────────┘
                                  │
                     ┌────────────▼────────────┐
                     │    Retrieval Router     │
                     │ strategy="auto"         │
                     └────────────┬────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
 ┌───────▼────────┐      ┌────────▼────────┐      ┌────────▼────────┐
 │ Normal Fetcher │      │ Stealth Fetcher │      │ Browser Fetcher │
 └───────┬────────┘      └────────┬────────┘      └────────┬────────┘
         └────────────────────────┼────────────────────────┘
                                  │
                         ┌────────▼─────────┐
                         │ DOM Normalizer   │
                         └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
                         │ Content Extractor│
                         └────────┬─────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
 ┌───────▼───────┐       ┌────────▼────────┐      ┌────────▼────────┐
 │ Markdown      │       │ Evidence Blocks │      │ Structured JSON │
 └───────────────┘       └─────────────────┘      └─────────────────┘
```

Future services:

```text
/search
/crawl
/extract
/v1/embeddings
/v1/rerank
```

---

# 4. Core API Surface

## 4.1 Reader endpoint

### GET

```http
GET /read?url=https://example.com
```

Optional shorthand:

```http
GET /https://example.com
```

### POST

```http
POST /read
Content-Type: application/json
```

```json
{
  "url": "https://example.com",
  "format": "markdown",
  "strategy": "auto"
}
```

### Response

```json
{
  "url": "https://example.com",
  "final_url": "https://example.com/",
  "title": "Example Domain",
  "content": "...",
  "markdown": "...",
  "text": "...",
  "status": 200,
  "fetch_strategy": "http",
  "cached": false,
  "content_hash": "...",
  "fetched_at": "...",
  "metadata": {},
  "links": [],
  "blocks": []
}
```

---

## 4.2 Crawl endpoint

```http
POST /crawl
```

```json
{
  "url": "https://docs.example.com",
  "max_depth": 3,
  "max_pages": 200,
  "include": ["/docs/**"],
  "exclude": ["/login/**"],
  "format": "markdown"
}
```

Response:

```json
{
  "job_id": "crawl_...",
  "status": "queued"
}
```

Supporting endpoints:

```text
GET /crawl/{job_id}
GET /crawl/{job_id}/pages
GET /crawl/{job_id}/stream
DELETE /crawl/{job_id}
```

---

## 4.3 Structured extraction endpoint

```http
POST /extract
```

```json
{
  "url": "https://example.com/products",
  "schema": {
    "products": [
      {
        "name": "string",
        "price": "number",
        "availability": "string"
      }
    ]
  }
}
```

The preferred extraction sequence is:

```text
DOM selectors
 ↓
JSON-LD / schema.org
 ↓
heuristic extraction
 ↓
small model fallback
```

LLM usage should be optional rather than mandatory.

---

## 4.4 Search endpoint

```http
GET /search?q=best+vector+database
```

Initial implementation should use an upstream search provider or metasearch backend.

Pipeline:

```text
query
 ↓
search provider
 ↓
URLs
 ↓
Scrapling Reader
 ↓
clean documents
 ↓
deduplicate
 ↓
rank
```

Possible response:

```json
{
  "query": "best vector database",
  "results": [
    {
      "rank": 1,
      "title": "...",
      "url": "...",
      "snippet": "...",
      "content": "...",
      "score": 0.91
    }
  ]
}
```

---

# 5. Development Phases

# Phase 0 — Repository Preparation

## Goal

Prepare the current Scrapling repository for service-layer development without disrupting the existing library.

## Tasks

- create a dedicated service package
- define internal interfaces between:
  - fetch layer
  - extraction layer
  - service layer
  - crawl scheduler
- keep existing public Scrapling APIs backwards-compatible
- add service-specific configuration
- add structured logging
- add environment-based configuration
- add health and version endpoints

Suggested layout:

```text
scrapling/
  fetchers/
  parser/
  spiders/
  ...

service/
  api/
  auth/
  cache/
  extraction/
  routing/
  schemas/
  workers/
  config.py
```

## Required endpoints

```text
GET /health
GET /ready
GET /version
```

## Acceptance criteria

- existing Scrapling test suite remains green
- service boots independently
- service imports Scrapling instead of duplicating core logic
- Docker image launches successfully
- health endpoint returns service and version metadata

---

# Phase 1 — Reader v0

## Goal

Ship the first Jina Reader-like capability.

## Tasks

Implement:

```text
POST /read
GET /read
```

Required request options:

- url
- output format
- timeout
- strategy
- include links
- include metadata

Supported output formats:

- markdown
- text
- HTML
- JSON envelope

Implement basic:

- URL validation
- redirect handling
- timeout handling
- response size limits
- content-type validation
- HTTP error normalization

## Acceptance criteria

For common static websites:

- URL fetch succeeds
- title is extracted
- readable Markdown is returned
- boilerplate is reduced
- links are returned
- original/final URL is preserved
- errors use stable JSON schemas

Example:

```bash
curl "http://localhost:8000/read?url=https://example.com"
```

must work without extra configuration.

---

# Phase 2 — Content Cleaning and Markdown Quality

## Goal

Make the output useful for LLMs instead of merely converting DOM to Markdown.

## Implement

### Boilerplate removal

Remove or reduce:

- navigation
- footers
- cookie dialogs
- modal overlays
- ads
- related-content widgets
- sidebars
- duplicated menus
- hidden nodes
- scripts
- styles

### Preserve

- headings
- paragraphs
- lists
- tables
- links
- code blocks
- blockquotes
- meaningful images
- captions

### Add metadata

- title
- description
- author
- publish date
- language
- canonical URL
- OpenGraph metadata
- JSON-LD metadata

## Add quality tests

Create a benchmark set with:

- news article
- docs page
- blog
- ecommerce page
- forum
- Wikipedia-like page
- SPA
- table-heavy page
- code documentation

## Acceptance criteria

- generated Markdown is semantically readable
- navigation and cookie text do not dominate output
- code blocks survive
- tables survive in usable form
- headings remain hierarchical
- benchmark snapshots remain stable across releases

---

# Phase 3 — Automatic Fetch Strategy

## Goal

Remove the need for users to select Scrapling fetchers manually.

## Add

```python
strategy="auto"
```

## Strategy signals

Inspect:

- HTTP status
- content length
- JS shell detection
- CAPTCHA markers
- Cloudflare markers
- DOM completeness
- repeated redirect loops
- expected-content heuristics
- challenge pages

## Escalation

```text
Fetcher
 ↓
retry
 ↓
StealthyFetcher
 ↓
DynamicFetcher
 ↓
stealth browser
 ↓
proxy browser
```

The router must avoid expensive escalation unless necessary.

## Domain memory

Persist successful strategy by domain:

```text
example.com → normal
site-a.com → dynamic
site-b.com → stealth
site-c.com → stealth + proxy
```

Track:

- success count
- failure count
- last working strategy
- median latency
- block rate

## Acceptance criteria

- one `/read` request can transparently escalate
- chosen strategy is returned in response metadata
- repeated requests benefit from domain memory
- browser use falls when simpler methods work
- failed escalations produce useful error information

---

# Phase 4 — Caching Layer

## Goal

Make repeated agent usage cheap and fast.

## Cache identity

Base cache key on:

```text
canonical URL
+
render strategy
+
content format
+
extraction options
```

## Support

- TTL
- stale-while-revalidate
- ETag
- Last-Modified
- content hashing
- forced refresh
- cache bypass

## Backends

Initial:

- filesystem
- SQLite

Production-ready:

- Redis

Optional later:

- S3-compatible object storage

## Acceptance criteria

- identical requests hit cache
- cache state is visible in response
- conditional revalidation works
- cache can be disabled
- cache corruption fails safely
- repeated calls show meaningful latency reduction

---

# Phase 5 — Evidence and Provenance Blocks

## Goal

Make Scrapling especially useful for research agents and citation-aware systems.

## Block schema

```json
{
  "id": "block_123",
  "type": "paragraph",
  "text": "...",
  "source_url": "...",
  "selector": "...",
  "xpath": "...",
  "char_start": 120,
  "char_end": 244,
  "heading_path": [
    "Documentation",
    "Authentication"
  ]
}
```

Optional:

- bounding box
- screenshot reference
- DOM node hash
- timestamp
- content hash

## Acceptance criteria

- blocks map back to source DOM
- block ordering matches readable page order
- headings establish context
- duplicate blocks are removed
- clients can cite exact source blocks

---

# Phase 6 — Crawl-as-a-Service

## Goal

Expose Scrapling spiders as remote asynchronous jobs.

## Implement

```text
POST /crawl
GET /crawl/{id}
GET /crawl/{id}/pages
GET /crawl/{id}/stream
DELETE /crawl/{id}
```

## Capabilities

- max depth
- max pages
- domain allowlist
- include patterns
- exclude patterns
- concurrency
- per-domain throttling
- pause
- resume
- cancel
- crawl state persistence

## Streaming

Support server-sent events or newline-delimited JSON for:

- page fetched
- page extracted
- page failed
- retry
- crawl progress
- crawl complete

## Acceptance criteria

- crawls survive process restart
- duplicate URLs are avoided
- pause/resume works
- per-domain limits work
- result pages can be streamed as they finish

---

# Phase 7 — Structured Extraction API

## Goal

Allow agents to request typed data instead of raw text.

## Pipeline

1. schema.org / JSON-LD
2. HTML semantics
3. deterministic selectors
4. heuristics
5. optional small-model extraction

## Requirements

- JSON Schema-compatible requests
- response validation
- confidence field
- per-field provenance
- partial extraction allowed
- deterministic mode
- LLM fallback mode

## Example output

```json
{
  "data": {
    "name": "Example product",
    "price": 49.99
  },
  "confidence": 0.92,
  "sources": {
    "name": "block_23",
    "price": "block_26"
  }
}
```

## Acceptance criteria

- structured data validates against requested schema
- provenance maps values to page evidence
- extraction works without LLMs for common schemas
- model fallback can be enabled explicitly

---

# Phase 8 — Search API

## Goal

Turn Scrapling from URL retrieval into query-based web retrieval.

## Initial architecture

Do not build an independent global search index.

Use:

- upstream search provider
- metasearch service
- configurable provider adapter

Then enrich results using Scrapling.

```text
query
 ↓
provider
 ↓
URLs
 ↓
Reader
 ↓
deduplication
 ↓
ranking
 ↓
results
```

## Add

- result count
- language
- region
- safe-search options
- time range
- domain allowlist
- domain blocklist
- timeout budget

## Acceptance criteria

- query returns ranked URLs
- top results can include extracted content
- failed page fetches do not break full search
- search provider can be swapped
- duplicate domains/pages can be collapsed

---

# Phase 9 — Reranking

## Goal

Improve search and crawl result quality.

## Endpoint

```http
POST /v1/rerank
```

Request:

```json
{
  "query": "...",
  "documents": [
    "...",
    "..."
  ],
  "top_n": 10
}
```

## Implementation

Use pluggable open models.

The service should allow:

- local model
- remote OpenAI-compatible model
- external reranking provider

## Acceptance criteria

- search endpoint can optionally rerank
- crawl corpus can be ranked against a query
- reranking can be disabled
- model adapter is replaceable

---

# Phase 10 — Embeddings

## Goal

Provide a compatible retrieval building block.

## Endpoint

```http
POST /v1/embeddings
```

Prefer an OpenAI-compatible schema where practical.

## Requirements

- pluggable embedding backend
- batching
- model metadata
- dimensions metadata
- normalized outputs
- rate limiting

## Acceptance criteria

- endpoint works with common vector-store clients
- embeddings can be generated from Reader output
- model implementation is not coupled to Scrapling fetching

---

# Phase 11 — Authentication and Rate Limiting

## Goal

Make the system safe for remote use.

## Add

- API keys
- hashed key storage
- per-key rate limits
- request quotas
- endpoint-specific limits
- usage logs
- key disable/revoke support

## Example

```http
Authorization: Bearer sk_scrapling_...
```

## Acceptance criteria

- anonymous access can be disabled
- invalid keys receive stable 401 responses
- rate limits return 429
- keys can have different quotas
- logs never expose full keys

---

# Phase 12 — Usage Metering

## Goal

Support hosted or shared deployments.

Track:

- requests
- pages
- successful fetches
- browser fetches
- proxy fetches
- bandwidth
- cache hits
- model tokens
- crawl pages
- compute time

Do not build billing first.

First build accurate usage accounting.

## Acceptance criteria

- every request receives a request ID
- usage is attributable to API key
- admin endpoint can summarize usage
- expensive browser/proxy operations are separately measurable

---

# Phase 13 — SDKs and Developer Experience

## Goal

Make adoption easier than using the raw API.

## Python

```python
from scrapling_client import Scrapling

client = Scrapling(api_key="...")

page = client.read("https://example.com")
print(page.markdown)
```

## JavaScript

```javascript
const page = await scrapling.read("https://example.com");
```

## Deliver

- Python SDK
- TypeScript SDK
- OpenAPI spec
- curl examples
- Postman-compatible collection
- examples for LangChain/LlamaIndex-style integrations where appropriate

## Acceptance criteria

A new user should be able to complete a Reader request within five minutes.

---

# Phase 14 — MCP Service

## Goal

Expose the service directly to agent systems.

## Tools

Recommended tools:

```text
read_url
crawl_site
search_web
extract_structured
get_crawl_status
get_page_blocks
```

Responses should be compact and agent-friendly.

Avoid returning huge raw HTML by default.

## Acceptance criteria

- MCP server can call the same internal service layer
- MCP does not duplicate scraper logic
- outputs include provenance
- large results are paginated or chunked

---

# Phase 15 — Observability

## Add

Metrics:

- requests/sec
- latency p50/p95/p99
- success rate
- block rate
- cache hit ratio
- browser escalation ratio
- proxy escalation ratio
- bytes downloaded
- extraction latency
- crawl throughput

Logging:

- structured JSON
- request ID
- domain
- fetch strategy
- retry count
- cache result
- status

Tracing:

- API
- fetch
- browser
- parse
- extraction
- rerank

## Acceptance criteria

Production issues should be diagnosable without reproducing every request locally.

---

# Phase 16 — Safety and Abuse Controls

## Goal

Prevent accidental or abusive crawling patterns.

## Add

- SSRF protection
- block private/local network targets by default
- configurable internal-network allowlist
- DNS rebinding protection
- maximum redirect count
- maximum response size
- maximum crawl pages
- maximum crawl duration
- per-domain concurrency
- configurable robots.txt behavior
- user-agent configuration
- proxy policy
- request timeout ceilings

## Acceptance criteria

Requests to localhost, metadata endpoints, and RFC1918 networks are rejected by default unless explicitly permitted.

---

# Phase 17 — Deployment Profiles

## Minimal

```text
API
+
Scrapling
+
SQLite cache
```

## Standard

```text
API
+
Scrapling
+
Redis
+
worker
```

## Large deployment

```text
gateway
+
API replicas
+
worker pool
+
Redis
+
Postgres
+
object storage
+
browser workers
```

## Acceptance criteria

The same API contracts remain stable across deployment modes.

---

# 6. Automatic Fetch Router Specification

The router is one of the core differentiators.

## Request

```python
fetch(url, strategy="auto")
```

## Candidate strategies

```text
http
async_http
stealth_http
browser
stealth_browser
proxy_browser
```

## Router scoring

Each domain strategy may maintain:

```json
{
  "strategy": "browser",
  "success_rate": 0.96,
  "median_latency_ms": 1800,
  "cost_score": 3,
  "last_success": "...",
  "last_failure": "..."
}
```

The router should prefer:

1. previous working strategy
2. lower-cost strategy
3. lower-latency strategy
4. higher-success strategy

Never escalate directly to the most expensive path unless prior evidence strongly supports it.

---

# 7. Content Quality Benchmark

Create a permanent benchmark corpus.

Suggested targets:

```text
static HTML article
documentation site
GitHub page
Wikipedia article
ecommerce product
ecommerce listing
forum thread
news page
JavaScript SPA
Cloudflare-protected page
table-heavy page
code-heavy documentation
infinite-scroll page
```

Measure:

- successful retrieval
- readable content ratio
- boilerplate ratio
- heading preservation
- link preservation
- table preservation
- code preservation
- extraction latency
- browser escalation rate
- token count reduction
- duplicate content rate

---

# 8. Performance Targets

Initial targets:

## Reader

Cached:

```text
p50 < 100 ms
```

Normal HTML:

```text
p50 < 1 second
```

Browser-rendered:

```text
p50 < 5 seconds
```

These are directional goals rather than hard guarantees.

## Crawl

The crawler should respect the target site's latency and throttling signals rather than maximizing raw concurrency.

---

# 9. Response Format Standardization

All endpoints should return stable envelopes.

Success:

```json
{
  "ok": true,
  "request_id": "...",
  "data": {}
}
```

Error:

```json
{
  "ok": false,
  "request_id": "...",
  "error": {
    "code": "FETCH_FAILED",
    "message": "...",
    "retryable": true
  }
}
```

Recommended error codes:

```text
INVALID_URL
URL_BLOCKED
FETCH_TIMEOUT
FETCH_FAILED
BOT_CHALLENGE
BROWSER_FAILED
CONTENT_TOO_LARGE
UNSUPPORTED_CONTENT
EXTRACTION_FAILED
RATE_LIMITED
AUTH_FAILED
CRAWL_LIMIT_REACHED
INTERNAL_ERROR
```

---

# 10. Configuration

Environment variables should cover:

```text
SCRAPLING_HOST
SCRAPLING_PORT
SCRAPLING_LOG_LEVEL
SCRAPLING_CACHE_BACKEND
SCRAPLING_CACHE_TTL
SCRAPLING_REDIS_URL
SCRAPLING_DATABASE_URL
SCRAPLING_MAX_RESPONSE_MB
SCRAPLING_MAX_REDIRECTS
SCRAPLING_DEFAULT_TIMEOUT
SCRAPLING_BROWSER_ENABLED
SCRAPLING_PROXY_URL
SCRAPLING_ALLOW_PRIVATE_NETWORKS
SCRAPLING_AUTH_ENABLED
```

All settings should also be available through typed Python configuration.

---

# 11. Testing Strategy

Each phase must introduce tests.

## Unit tests

- URL validation
- router decisions
- cache key generation
- extraction
- Markdown conversion
- provenance mapping
- authentication
- rate limiting

## Integration tests

- normal HTML
- redirects
- browser rendering
- challenge detection
- crawl
- cache
- extraction
- search provider adapter

## Regression tests

Store representative HTML fixtures and expected outputs.

## Live smoke tests

Use a small curated set of stable public URLs.

Do not make the full CI suite dependent on external live websites.

---

# 12. Recommended Implementation Order

The critical order is:

```text
0. repository/service preparation
1. Reader API
2. content cleaning
3. automatic fetch routing
4. caching
5. evidence/provenance
6. crawl API
7. structured extraction
8. search
9. reranking
10. embeddings
11. authentication/rate limits
12. usage metering
13. SDKs
14. MCP expansion
15. observability
16. safety hardening
17. deployment scaling
```

Do not start with embeddings or independent search indexing.

The first product milestone should be a dependable Reader service.

---

# 13. Milestones

## Milestone A — Reader MVP

Deliver:

- `/read`
- Markdown
- metadata
- links
- Docker
- OpenAPI
- tests

This is the first externally usable release.

---

## Milestone B — Smart Reader

Deliver:

- content cleanup
- automatic fetch escalation
- domain strategy memory
- cache
- evidence blocks

This is the first credible Jina Reader competitor.

---

## Milestone C — Agent Retrieval Platform

Deliver:

- crawl API
- extraction API
- MCP improvements
- provenance
- streaming results

This makes Scrapling a strong agent-facing web backend.

---

## Milestone D — Search Foundation

Deliver:

- `/search`
- provider adapters
- result enrichment
- reranking
- optional embeddings

This makes Scrapling competitive with a broader web retrieval platform rather than only a Reader API.

---

## Milestone E — Production Service

Deliver:

- authentication
- quotas
- metering
- observability
- abuse controls
- multi-worker architecture
- hosted deployment profile

---

# 14. Competitive Differentiators to Preserve

Scrapling should not simply copy Jina.

The target differentiation is:

```text
adaptive selectors
+
anti-bot-aware acquisition
+
automatic HTTP/browser escalation
+
persistent domain strategy memory
+
agent-native evidence blocks
+
structured extraction
+
self-hostability
+
full crawl control
```

Potential positioning:

> A self-hostable web intelligence layer for autonomous agents.

Or:

> Turn any public website into structured, traceable agent context.

---

# 15. Explicit Non-Goals for Early Versions

Do not initially build:

- a global search index
- a proprietary embedding model
- a proprietary reranker
- full billing infrastructure
- enterprise dashboard
- Kubernetes operator
- distributed browser cluster
- complex GUI

These can be added after Reader, Crawl, and Search APIs prove reliable.

---

# 16. Definition of Done for the First Competitive Release

The project can reasonably describe itself as a Jina Reader competitor when the following works reliably:

```bash
curl "https://service.example/read?url=https://example.com"
```

and the service:

1. selects the correct fetch strategy automatically
2. handles static and JavaScript-heavy sites
3. escalates around common bot challenges
4. returns clean Markdown
5. removes most boilerplate
6. returns metadata and links
7. caches repeated requests
8. exposes evidence/provenance blocks
9. provides stable errors
10. supports API authentication
11. ships with Docker and OpenAPI
12. provides MCP access
13. has regression and live smoke tests
14. exposes metrics for fetch strategy and failures

At that point the next major expansion should be:

```text
/crawl
→ /extract
→ /search
```

rather than adding more scraper-level features.
