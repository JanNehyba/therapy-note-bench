"""The chat client, exercised against a fake endpoint.

A generation run is thousands of calls over several hours against a shared
academic service, so the behaviour that matters is what happens when a call goes
wrong: 429 because the key is rate-limited, a 5xx, a dropped connection, or a
reasoning model that thinks until it runs out of budget and returns nothing.
Nothing here touches the network.
"""

from __future__ import annotations

import httpx
import pytest

from tnb.config import GenerationPolicy, Provider
from tnb.providers import openai_compatible as einfra

PROVIDER = Provider(
    name="einfra",
    base_url="https://example.invalid/v1",
    token_env="EINFRA_API_TOKEN",
    generation=GenerationPolicy(
        temperature=0.0, max_tokens=4096, concurrency=2, retries=3, backoff_s=6
    ),
)


@pytest.fixture(autouse=True)
def token(monkeypatch):
    monkeypatch.setenv("EINFRA_API_TOKEN", "test-token")


@pytest.fixture
def no_waiting(monkeypatch):
    """Record the backoff instead of serving it."""
    waits: list[float] = []
    monkeypatch.setattr(einfra.time, "sleep", waits.append)
    return waits


def _reply(status: int = 200, **message) -> httpx.Response:
    if status != 200:
        return httpx.Response(status, text="rate limited")
    body = {
        "choices": [{"message": message or {"content": "a note"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 3},
    }
    return httpx.Response(status, json=body)


def _serve(monkeypatch, responses):
    """Answer each POST with the next item; an exception item is raised."""
    calls: list[dict] = []
    queue = list(responses)

    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        item = queue.pop(0) if queue else responses[-1]
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(einfra.httpx, "post", fake_post)
    return calls


def test_a_note_comes_back_with_its_usage(monkeypatch):
    calls = _serve(monkeypatch, [_reply(content="  a note  ")])
    result = einfra.complete(PROVIDER, "gemma4", "write a note")

    assert result.ok and result.text == "a note"
    assert result.usage == {"prompt_tokens": 10, "completion_tokens": 3}
    assert result.finish_reason == "stop"
    assert calls[0]["url"] == "https://example.invalid/v1/chat/completions"


def test_the_request_is_one_user_message_at_the_policy_settings(monkeypatch):
    """Both source papers prompt with a single user turn and no system message;
    a system message would make our generations theirs no longer."""
    calls = _serve(monkeypatch, [_reply()])
    einfra.complete(PROVIDER, "gemma4", "write a note")

    payload = calls[0]["json"]
    assert payload["messages"] == [{"role": "user", "content": "write a note"}]
    assert payload["temperature"] == 0.0
    assert payload["max_tokens"] == 4096
    assert "system" not in str(payload["messages"])


def test_429_is_retried_with_growing_backoff(monkeypatch, no_waiting):
    """e-INFRA rate-limits per API key, so 429 is routine rather than fatal."""
    _serve(monkeypatch, [_reply(429), _reply(429), _reply(content="a note")])
    result = einfra.complete(PROVIDER, "gemma4", "write a note")

    assert result.ok
    assert no_waiting == [6, 12]


def test_a_server_error_is_retried_too(monkeypatch, no_waiting):
    _serve(monkeypatch, [_reply(503), _reply(content="a note")])
    assert einfra.complete(PROVIDER, "gemma4", "write a note").ok


def test_a_dropped_connection_is_retried_and_then_reported(monkeypatch, no_waiting):
    """One reset at call 4000 must cost a retry, not the run."""
    boom = httpx.ConnectError("connection reset")
    _serve(monkeypatch, [boom, _reply(content="a note")])
    assert einfra.complete(PROVIDER, "gemma4", "write a note").ok

    _serve(monkeypatch, [boom, boom, boom, boom])
    failed = einfra.complete(PROVIDER, "gemma4", "write a note")
    assert not failed.ok
    assert "ConnectError" in failed.error


def test_giving_up_on_429_is_recorded_as_a_failure_not_an_empty_note(monkeypatch, no_waiting):
    """A note that was never generated must not enter the cache as a blank."""
    _serve(monkeypatch, [_reply(429)])
    result = einfra.complete(PROVIDER, "gemma4", "write a note")

    assert not result.ok
    assert result.error.startswith("HTTP429")
    assert result.text == ""


def test_a_rejected_request_is_not_retried(monkeypatch, no_waiting):
    """400 means the request is wrong. Asking again four times only wastes quota."""
    calls = _serve(monkeypatch, [httpx.Response(400, text="bad model")])
    result = einfra.complete(PROVIDER, "gemma4", "write a note")

    assert len(calls) == 1
    assert not result.ok and "HTTP400" in result.error


def test_a_reasoning_model_that_ran_out_of_budget_is_distinguishable(monkeypatch):
    """Empty content with a long chain of thought is a truncated generation, not
    a refusal and not a bad model. The record has to say which it was."""
    _serve(monkeypatch, [_reply(content="", reasoning_content="thinking " * 500)])
    result = einfra.complete(PROVIDER, "deepseek-v4-flash-thinking", "write a note")

    assert not result.ok
    assert result.error == "empty content"
    assert result.reasoning_chars > 0


def test_an_answer_cut_off_at_the_budget_is_not_an_answer(monkeypatch):
    """`finish_reason` was parsed here and never read.

    Sixteen iCARE sections stopped mid-sentence at the token budget and were
    filed as complete, because `ok` asked only whether any text came back. The
    escalation `generation.py` already has is gated on `ok`, so the one thing
    built to handle this never fired -- and what a truncated section measures
    is our budget, not the model.
    """
    body = {
        "choices": [
            {
                "message": {"content": "The client reported feeling anxious about"},
                "finish_reason": "length",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 512},
    }
    _serve(monkeypatch, [httpx.Response(200, json=body)])

    result = einfra.complete(PROVIDER, "glm-5", "write section 6")

    assert result.ok is False
    assert result.finish_reason == "length"
    assert "truncated" in result.error
    assert result.text, "the fragment is kept, so the record can be explained"
