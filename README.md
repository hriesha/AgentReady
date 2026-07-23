# AgentReady

Audits an ecommerce product catalog for AI shopping agent readiness: how likely each product is to be surfaced, understood, and recommended by AI shopping assistants such as ChatGPT shopping, Gemini, and Rufus.

For each SKU, AgentReady:

- scores attribute completeness against a weighted rubric of agent-relevant attributes
- simulates realistic shopping-agent queries and tests whether the product's current data would satisfy them
- ranks the specific gaps that suppress visibility, ordered by revenue at risk
- rewrites weak attributes into clean structured values, using only information already present in the product data

## Live demo

https://shopagentready.vercel.app serves a saved audit of the bundled sample catalog. The first load can take up to a minute if the backend is waking from sleep. Live audits run locally, see below.

## The readiness rubric

Every SKU is scored against a canonical schema of 18 attributes. Each attribute has a weight reflecting how heavily AI shopping agents rely on it when deciding whether to surface and recommend a product.

| Attribute | Weight | Why agents need it |
|---|---|---|
| title | 10 | primary match target |
| price | 10 | agents filter on budget constraints |
| availability | 9 | agents drop unavailable items |
| category | 8 | filters the candidate set |
| usage_scenario | 8 | context match, "for a high-traffic hallway" style queries |
| material | 7 | common "what is it made of" query |
| dimensions | 7 | "will it fit" queries |
| key_features | 7 | outcome-based matching |
| description | 6 | fallback reasoning source |
| certifications | 6 | trust signals that break ties |
| shipping_info | 6 | agents estimate delivery |
| brand | 5 | trust and disambiguation |
| weight | 5 | "lightweight" queries |
| target_audience | 5 | "for a minimalist apartment" style matching |
| color | 4 | filter attribute |
| care_instructions | 4 | "machine washable" filters |
| warranty | 4 | recourse and trust signal |
| currency | 3 | required to interpret price |

Each attribute scores 1.0 when present and specific, 0.5 when present but vague (filler wording like "high quality, durable", placeholders, empty-ish values, unstructured or unit-less measurements), and 0.0 when missing. The completeness score is the weighted sum scaled to 0 to 100. This score is fully deterministic and never requires an LLM call.

## Setup

1. Create a free API key at https://aistudio.google.com with a Google account. The Gemini API free tier needs no credit card and no billing account. Do not enable billing on the Google Cloud project behind the key.
2. Copy `.env.example` to `.env` and paste your key into `LLM_API_KEY`. Never commit `.env`.

Note: on the free tier, API inputs may be used by the provider to improve their models. Do not upload sensitive or proprietary catalogs.

## Run locally

Copy `.env.example` to `.env` first (see Setup). Then either:

- `docker compose up` runs both services, the app is at http://localhost:5173
- `make dev` runs the API (port 8000) and the web dev server (port 5173) directly; requires Python 3.11+ with a `.venv` at the repo root holding `api/requirements.txt`, and Node 18+ with `npm install` run in `web/`

`make test` runs the backend tests. No test makes a live LLM call.

## Deploy for free

Both hosts have free tiers with no payment method. Deploy the backend first, then the frontend, then connect them.

1. Backend on Render: create a free account at render.com, choose New, then Blueprint, and select this repository. `render.yaml` configures the service. The free plan sleeps when idle and cold-starts on the next request, which is fine for a demo.
2. Frontend on Vercel: create a free account at vercel.com, import this repository, and set the Root Directory to `web`. Vercel detects Vite automatically. Add an environment variable `VITE_API_BASE_URL` set to your Render service URL (for example `https://agentready-api.onrender.com`).
3. Connect them: in the Render dashboard set `WEB_ORIGIN` to your Vercel URL (for example `https://agentready.vercel.app`) so CORS allows the frontend.

The blueprint ships with `DEMO_MODE=true`, so the public site serves the saved demo audit and needs no API key. To run live audits on the public site instead, set `DEMO_MODE=false` and fill in `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` in the Render dashboard, using the same values as your local `.env`.

## Demo mode

With `DEMO_MODE=true` the app serves a precomputed audit of the bundled sample catalog from a committed JSON fixture. The dashboard, SKU detail views, query simulations, and CSV exports all work with zero live LLM calls, so the public URL always works, never hits a rate limit, and can never incur cost. Uploading is disabled in this mode with a short note; live audits run locally.
