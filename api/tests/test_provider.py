"""LLM provider: throttle, backoff, JSON mode, caching. No network calls,
all HTTP goes through a mock transport."""

import json

import httpx
import pytest

from app.config import Settings
from app.llm.provider import (
    LLMBadResponse,
    LLMError,
    LLMNotConfigured,
    LLMProvider,
    LLMRateLimited,
    RateLimiter,
    strip_code_fences,
)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class FakeSleep:
    def __init__(self, clock):
        self.calls = []
        self._clock = clock

    def __call__(self, seconds):
        self.calls.append(seconds)
        self._clock.now += seconds


def make_settings(**overrides):
    values = dict(
        llm_api_key="test-key",
        llm_base_url="https://llm.test/v1",
        llm_model="test-model",
        llm_max_rpm=1000,
    )
    values.update(overrides)
    return Settings(_env_file=None, **values)


def chat_response(content, prompt_tokens=10, completion_tokens=5):
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": content}}],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
        },
    )


def make_provider(handler, **settings_overrides):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    clock = FakeClock()
    sleep = FakeSleep(clock)
    provider = LLMProvider(
        settings=make_settings(**settings_overrides),
        client=client,
        clock=clock,
        sleep=sleep,
    )
    return provider, sleep


def test_complete_returns_content_and_sends_auth():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return chat_response("hello")

    provider, _ = make_provider(handler)
    result = provider.complete("system text", "user text")
    assert result == "hello"
    assert seen["url"] == "https://llm.test/v1/chat/completions"
    assert seen["auth"] == "Bearer test-key"
    assert seen["body"]["model"] == "test-model"
    assert [m["role"] for m in seen["body"]["messages"]] == ["system", "user"]


@pytest.mark.parametrize(
    "raw, expected",
    [
        ('```json\n{"a": 1}\n```', '{"a": 1}'),
        ('```\n{"a": 1}\n```', '{"a": 1}'),
        ('  {"a": 1}  ', '{"a": 1}'),
        ("plain text", "plain text"),
    ],
)
def test_strip_code_fences(raw, expected):
    assert strip_code_fences(raw) == expected


def test_json_mode_strips_fences_and_validates():
    provider, _ = make_provider(lambda request: chat_response('```json\n{"a": 1}\n```'))
    assert provider.complete("s", "u", json_mode=True) == '{"a": 1}'


def test_json_mode_retries_once_then_succeeds():
    responses = [chat_response("not json"), chat_response('{"a": 1}')]

    def handler(request):
        return responses.pop(0)

    provider, _ = make_provider(handler)
    assert provider.complete("s", "u", json_mode=True) == '{"a": 1}'
    assert provider.usage()["requests"] == 2


def test_json_mode_raises_after_second_bad_response():
    provider, _ = make_provider(lambda request: chat_response("still not json"))
    with pytest.raises(LLMBadResponse):
        provider.complete("s", "u", json_mode=True)


def test_backoff_on_429_then_success():
    statuses = [429, 429]

    def handler(request):
        if statuses:
            return httpx.Response(statuses.pop(0), json={})
        return chat_response("recovered")

    provider, sleep = make_provider(handler)
    assert provider.complete("s", "u") == "recovered"
    assert sleep.calls == [1.0, 2.0]


def test_retry_after_header_extends_backoff():
    responses = [httpx.Response(429, headers={"retry-after": "30"}, json={})]

    def handler(request):
        if responses:
            return responses.pop(0)
        return chat_response("ok")

    provider, sleep = make_provider(handler)
    assert provider.complete("s", "u") == "ok"
    assert sleep.calls == [30.0]


def test_retry_hint_in_body_extends_backoff():
    responses = [
        httpx.Response(
            429,
            json={"error": {"message": "Quota exceeded. Please retry in 45.44s."}},
        )
    ]

    def handler(request):
        if responses:
            return responses.pop(0)
        return chat_response("ok")

    provider, sleep = make_provider(handler)
    assert provider.complete("s", "u") == "ok"
    assert sleep.calls == [45.44]


def test_retry_wait_is_capped():
    responses = [httpx.Response(429, headers={"retry-after": "600"}, json={})]

    def handler(request):
        if responses:
            return responses.pop(0)
        return chat_response("ok")

    provider, sleep = make_provider(handler)
    assert provider.complete("s", "u") == "ok"
    assert sleep.calls == [70.0]


def test_rate_limited_after_exhausted_attempts():
    provider, sleep = make_provider(lambda request: httpx.Response(429, json={}))
    with pytest.raises(LLMRateLimited):
        provider.complete("s", "u")
    assert sleep.calls == [1.0, 2.0, 4.0]
    assert provider.usage()["requests"] == 4


def test_server_errors_retry_like_rate_limits():
    responses = [httpx.Response(500, json={})]

    def handler(request):
        if responses:
            return responses.pop(0)
        return chat_response("ok")

    provider, sleep = make_provider(handler)
    assert provider.complete("s", "u") == "ok"
    assert sleep.calls == [1.0]


def test_client_errors_fail_fast_without_retry():
    provider, sleep = make_provider(lambda request: httpx.Response(400, json={}))
    with pytest.raises(LLMError) as excinfo:
        provider.complete("s", "u")
    assert not isinstance(excinfo.value, LLMRateLimited)
    assert sleep.calls == []
    assert provider.usage()["requests"] == 1


def test_cache_avoids_duplicate_requests():
    count = {"n": 0}

    def handler(request):
        count["n"] += 1
        return chat_response("cached answer")

    provider, _ = make_provider(handler)
    assert provider.complete("s", "u") == "cached answer"
    assert provider.complete("s", "u") == "cached answer"
    assert count["n"] == 1
    assert provider.complete("s", "different") == "cached answer"
    assert count["n"] == 2


def test_usage_counts_tokens():
    provider, _ = make_provider(
        lambda request: chat_response("ok", prompt_tokens=100, completion_tokens=40)
    )
    provider.complete("s", "u")
    usage = provider.usage()
    assert usage == {"requests": 1, "prompt_tokens": 100, "completion_tokens": 40}


def test_missing_configuration_raises_before_any_call():
    provider, _ = make_provider(lambda request: chat_response("ok"), llm_api_key="")
    with pytest.raises(LLMNotConfigured):
        provider.complete("s", "u")
    assert provider.usage()["requests"] == 0


def test_unexpected_response_shape_raises():
    provider, _ = make_provider(lambda request: httpx.Response(200, json={"weird": True}))
    with pytest.raises(LLMBadResponse):
        provider.complete("s", "u")


def test_rate_limiter_blocks_at_cap():
    clock = FakeClock()
    sleep = FakeSleep(clock)
    limiter = RateLimiter(max_rpm=2, clock=clock, sleep=sleep)
    limiter.acquire()
    limiter.acquire()
    assert sleep.calls == []
    limiter.acquire()
    assert sleep.calls == [60.0]


def test_rate_limiter_window_slides():
    clock = FakeClock()
    sleep = FakeSleep(clock)
    limiter = RateLimiter(max_rpm=2, clock=clock, sleep=sleep)
    limiter.acquire()
    clock.now = 61.0
    limiter.acquire()
    limiter.acquire()
    assert sleep.calls == []
