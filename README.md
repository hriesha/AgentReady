# AgentReady

Audits an ecommerce product catalog for AI shopping agent readiness: how likely each product is to be surfaced, understood, and recommended by AI shopping assistants such as ChatGPT shopping, Gemini, and Rufus.

For each SKU, AgentReady:

- scores attribute completeness against a weighted rubric of agent-relevant attributes
- simulates realistic shopping-agent queries and tests whether the product's current data would satisfy them
- ranks the specific gaps that suppress visibility, ordered by revenue at risk
- rewrites weak attributes into clean structured values, using only information already present in the product data

## Status

Under construction. Sections below fill in as each part of the build lands.

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

To be documented: `docker compose up` and `make dev`.

## Deploy for free

To be documented: frontend on Vercel, backend on Render or Railway, all on free tiers with no payment method.

## Demo mode

To be documented: with `DEMO_MODE=true` the app serves a precomputed audit of the bundled sample catalog and makes zero live LLM calls.
