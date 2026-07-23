"""LLM provider: the only module that talks to the model endpoint.

Everything about the endpoint comes from environment variables, and this
file must stay free of vendor names in identifiers, comments, and strings.
Calls are throttled client side to stay under the free tier request rate,
back off exponentially on rate limits and transient server errors, and are
cached by prompt so repeated questions cost no extra requests. When the
limit cannot be respected, a typed error is raised so the pipeline can
degrade gracefully instead of failing the run. There is no paid fallback.
"""

import hashlib
import json
import logging
import re
import threading
import time
from collections import deque
from functools import lru_cache

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger("app.llm")

MAX_ATTEMPTS = 4
BACKOFF_DELAYS = (1.0, 2.0, 4.0, 8.0)
RATE_WINDOW_SECONDS = 60.0
REQUEST_TIMEOUT_SECONDS = 60.0

JSON_ONLY_INSTRUCTION = (
    "Respond with valid JSON only. No prose, no code fences, no explanations."
)
JSON_RETRY_REMINDER = "Return only valid JSON."


class LLMError(Exception):
    """Base error for all provider failures."""


class LLMNotConfigured(LLMError):
    """Endpoint settings are absent, no call was attempted."""


class LLMRateLimited(LLMError):
    """Rate limited or unreachable after all backoff attempts. The pipeline
    catches this to degrade gracefully, it must never trigger a paid path."""


class LLMBadResponse(LLMError):
    """The endpoint answered with an unusable body."""


class RateLimiter:
    """Client-side cap on outbound requests per minute.

    Keeps a sliding window of send times. acquire() blocks until sending
    one more request stays under the cap. Thread safe so concurrent SKU
    audits share one budget.
    """

    def __init__(self, max_rpm: int, clock=time.monotonic, sleep=time.sleep):
        self.max_rpm = max(1, int(max_rpm))
        self._clock = clock
        self._sleep = sleep
        self._sent: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = self._clock()
                while self._sent and now - self._sent[0] >= RATE_WINDOW_SECONDS:
                    self._sent.popleft()
                if len(self._sent) < self.max_rpm:
                    self._sent.append(now)
                    return
                wait = RATE_WINDOW_SECONDS - (now - self._sent[0])
            self._sleep(max(wait, 0.05))


_FENCE_RE = re.compile(r"^```[a-zA-Z0-9_-]*\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def strip_code_fences(text: str) -> str:
    stripped = text.strip()
    match = _FENCE_RE.match(stripped)
    return match.group(1).strip() if match else stripped


def _is_valid_json(text: str) -> bool:
    try:
        json.loads(text)
    except (ValueError, TypeError):
        return False
    return True


class LLMProvider:
    """Single entry point for model calls: complete(system, user, json_mode)."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
        clock=time.monotonic,
        sleep=time.sleep,
    ):
        settings = settings or get_settings()
        self._api_key = settings.llm_api_key.get_secret_value()
        self._base_url = settings.llm_base_url.rstrip("/")
        self._model = settings.llm_model
        self._client = client or httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS)
        self._sleep = sleep
        self._limiter = RateLimiter(settings.llm_max_rpm, clock=clock, sleep=sleep)
        self._cache: dict[str, str] = {}
        self._lock = threading.Lock()
        self._usage = {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0}

    def usage(self) -> dict:
        """Request and token counters for this provider instance. Logged
        server side only, never surfaced in API responses or the UI."""
        with self._lock:
            return dict(self._usage)

    def complete(self, system: str, user: str, json_mode: bool = False) -> str:
        if not (self._api_key and self._base_url and self._model):
            raise LLMNotConfigured(
                "LLM endpoint is not configured, set LLM_API_KEY, LLM_BASE_URL and LLM_MODEL"
            )
        cache_key = self._cache_key(system, user, json_mode)
        with self._lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        if json_mode:
            system = f"{system}\n\n{JSON_ONLY_INSTRUCTION}"
        text = self._request(system, user)
        if json_mode:
            text = strip_code_fences(text)
            if not _is_valid_json(text):
                retry_user = f"{user}\n\n{JSON_RETRY_REMINDER}"
                text = strip_code_fences(self._request(system, retry_user))
                if not _is_valid_json(text):
                    raise LLMBadResponse("model did not return valid JSON")
        with self._lock:
            self._cache[cache_key] = text
        return text

    @staticmethod
    def _cache_key(system: str, user: str, json_mode: bool) -> str:
        payload = json.dumps([system, user, json_mode], ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _request(self, system: str, user: str) -> str:
        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        for attempt in range(MAX_ATTEMPTS):
            self._limiter.acquire()
            with self._lock:
                self._usage["requests"] += 1
            try:
                response = self._client.post(url, json=payload, headers=headers)
            except httpx.HTTPError as error:
                if attempt == MAX_ATTEMPTS - 1:
                    raise LLMRateLimited("endpoint unreachable after retries") from error
                self._sleep(BACKOFF_DELAYS[attempt])
                continue
            if response.status_code == 200:
                return self._extract(response)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == MAX_ATTEMPTS - 1:
                    raise LLMRateLimited(
                        f"rate limited after {MAX_ATTEMPTS} attempts, degrading"
                    )
                self._sleep(BACKOFF_DELAYS[attempt])
                continue
            raise LLMError(f"request failed with status {response.status_code}")
        raise LLMRateLimited("request attempts exhausted")

    def _extract(self, response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError as error:
            raise LLMBadResponse("response body is not JSON") from error
        usage = data.get("usage") or {}
        with self._lock:
            self._usage["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
            self._usage["completion_tokens"] += int(usage.get("completion_tokens") or 0)
            counters = dict(self._usage)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise LLMBadResponse("unexpected response shape") from error
        if not isinstance(content, str):
            raise LLMBadResponse("response has no text content")
        logger.debug(
            "llm usage: %d requests, %d prompt tokens, %d completion tokens",
            counters["requests"],
            counters["prompt_tokens"],
            counters["completion_tokens"],
        )
        return content


@lru_cache
def get_provider() -> LLMProvider:
    """Shared provider so all pipeline calls share one throttle and cache."""
    return LLMProvider()
