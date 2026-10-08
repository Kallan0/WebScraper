# AI Web Scraper

A React + FastAPI MVP based on the implementation plan. It validates a public URL, extracts readable HTML content with Trafilatura and a BeautifulSoup fallback, cleans the text, classifies it with deterministic rules, and calls Groq only for suitable content.

## Run locally (PowerShell)

Prerequisites: Node.js 22 LTS (22.12+) or 24 LTS and [uv](https://docs.astral.sh/uv/getting-started/installation/). uv manages the Python 3.13 environment.

Backend, in one terminal:

~~~powershell
cd backend
Copy-Item .env.example .env
# Edit .env and set GROQ_API_KEY to your own key.
uv sync
uv run fastapi dev
~~~

Frontend, in a second terminal:

~~~powershell
cd frontend
npm ci
npm run dev
~~~

Open http://localhost:5173. API docs: http://127.0.0.1:8000/docs. Health check: http://127.0.0.1:8000/api/health.

The Vite development server proxies /api to the backend. The frontend never receives the Groq key. Production serving requires routing /api to FastAPI separately; the Vite proxy is for local development.

## Configuration

Copy backend/.env.example to backend/.env and supply GROQ_API_KEY. The default GROQ_MODEL is openai/gpt-oss-20b; change it to a model available to your account. See [Groq text generation documentation](https://console.groq.com/docs/text-chat).

MAX_RESPONSE_BYTES defaults to 10 MB of HTML (including markup and embedded scripts). It is separate from the readable-text and model-input limits. Blog/news indexes with meaningful post headlines are summarized as indexes, without fetching or claiming to read the linked articles. Extraction retries with recall and DOM fallbacks when the first result is too short.

MAX_SCRAPED_CHARACTERS defaults to 50,000. MAX_SUMMARY_CHARACTERS defaults to 12,000 to keep individual requests modest. The API reports characters actually sent to the model and whether content was truncated. It makes one summary call per suitable page; chunked whole-document summarization is future work. Provider limits can still vary by account and model.

Without an API key, the backend runs and scraping/classification work, but suitable pages return a useful 503 configuration error rather than a fabricated summary.

## Tests and build

~~~powershell
cd backend
uv run pytest
~~~

~~~powershell
cd frontend
npm test
npm run build
~~~

All automated tests mock webpage or provider requests and consume no Groq quota. uv.lock and frontend/package-lock.json lock installed dependencies.

## API

POST /api/summarize accepts a JSON object with one field:

~~~json
{"url": "https://example.com/article"}
~~~

Success:

~~~json
{
  "success": true,
  "data": {
    "url": "https://example.com/article",
    "title": "Example Article",
    "content_type": "article",
    "characters_processed": 1200,
    "summary": "The key facts from the webpage.",
    "truncated": false
  }
}
~~~

Failures use {"success": false, "error": "Human-readable message"}: 400 for invalid requests or unsafe URLs, 422 for unsupported or insufficient content, 502 for website/provider failures, 503 for a missing key, 504 for timeouts, and 500 for unexpected errors.

## Scope and safeguards

- HTTP/HTTPS only, ports 80/443, no URL credentials.
- DNS results must all be public; local, private, reserved and transition IPs are rejected.
- Connections are pinned to a validated address with the original Host header and TLS server name, using the [HTTPX SNI extension](https://www.python-httpx.org/advanced/extensions/#sni_hostname). Every redirect is validated again; environment proxies are disabled.
- 20-second overall page-fetch limit, five redirects, and a configurable 10 MB response limit.
- Page text is treated as untrusted source material in a server-controlled prompt.
- Static HTML only: no browser rendering, authenticated pages, PDFs, or paywall bypass.
- Classification is heuristic and may mislabel pages. Model summaries should be checked against the source.
- This is a local MVP; authentication, usage limits, caching, history, background queues, and production deployment are outside this iteration.

## Layout

- backend/app/api: API orchestration
- backend/app/services: fetching, extraction, cleaning, classification and Groq adapter
- backend/app/utils: URL and public-destination checks
- backend/tests: pipeline, validation, scraping, API and provider tests
- frontend/src: React interface, API client and workflow tests

## Optional framework skills

To install current FastAPI framework skills for future development, run `uvx library-skills` interactively and select the Codex target. See [Library Skills](https://library-skills.io/).
