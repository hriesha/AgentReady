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

To be documented: the canonical attribute schema, the per-attribute weights, and how the 0 to 100 completeness score is computed.

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
