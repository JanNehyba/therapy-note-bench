"""Talking to an OpenAI-compatible endpoint: discovery, identity, generation.

Nothing here knows which provider it is speaking to. A :class:`~tnb.config.Provider`
carries the base URL, the credentials and the discovery rules, so a second
backend is a stanza in ``models.yaml`` rather than a second module.

The live ``GET /v1/models`` response is the only authority on what can be
benchmarked. Documentation drifts; aliases move. Everything here exists to turn
that response into a reproducible benchmark set without ever pinning a list.

Endpoints return almost no useful metadata — of the 31 models e-INFRA reported on
2026-08-23, exactly one carried a ``mode`` field — so what a model *is* has to be
established by asking it. See :func:`fingerprint`. That check matters twice over
once there are several providers: the same model id on two endpoints can be two
different builds, and only the answer tells you.
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from tnb.config import DiscoveryPolicy, Provider

#: Stylistically free prompt with a short answer. Two ids that return a
#: byte-identical answer at temperature 0 are the same model behind two names.
#: A factual prompt does not work: every model answers "list the first eight
#: primes" identically, which says nothing about identity.
FINGERPRINT_PROMPT = "In exactly one sentence, describe what a lighthouse does at night."

#: Reasoning models spend their budget on thinking before writing anything, so a
#: small cap returns empty content and looks like a broken model.
FINGERPRINT_MAX_TOKENS = 600


@dataclass(frozen=True)
class DiscoveredModel:
    """One model as the endpoint reported it, plus why we kept or dropped it."""

    id: str
    raw: dict
    excluded_by: str | None = None

    @property
    def included(self) -> bool:
        return self.excluded_by is None


def looks_like_alias(model_id: str) -> bool:
    """Heuristic for unversioned names such as ``glm``, ``kimi``, ``coder``.

    A name with no version marker is unusable in a leaderboard even when it is
    not a duplicate: whatever it points at today, it will point somewhere else
    after the next deployment, so a row carrying that label would compare two
    different models across runs. Concrete ids always carry a digit
    (``glm-5.2``, ``gemma4``, ``gpt-oss-120b``).

    This is a heuristic about *names*. :func:`fingerprint` is the check that
    establishes actual identity.
    """
    return not any(char.isdigit() for char in model_id)


#: Statuses worth asking again about. 429 is routine — providers rate-limit per
#: API key, not per model — and the 5xx family is an endpoint having a moment,
#: not a verdict on the request.
RETRIABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


def _post_with_backoff(
    provider: Provider,
    path: str,
    payload: dict,
    *,
    timeout: float,
    attempts: int = 5,
    sleep: Callable[[float], None] | None = None,
) -> httpx.Response:
    """POST, retrying on 429, on 5xx and on a dropped connection.

    Waits grow as ``backoff_s * attempt``. A generation run makes thousands of
    calls over hours, so a transient failure has to cost one retry rather than
    the run: without this, one dropped connection at call 4000 loses the lot.
    """
    wait = sleep or time.sleep
    last: httpx.Response | None = None
    last_error: httpx.TransportError | None = None

    for attempt in range(attempts):
        if attempt:
            wait(provider.generation.backoff_s * attempt)
        try:
            response = httpx.post(
                f"{provider.base_url.rstrip('/')}{path}",
                headers={"Authorization": f"Bearer {provider.token()}"},
                json=payload,
                timeout=timeout,
            )
        except httpx.TransportError as error:  # timeouts, resets, DNS
            last_error = error
            continue

        if response.status_code not in RETRIABLE_STATUS:
            return response
        last = response

    if last is not None:
        return last
    assert last_error is not None
    raise last_error


def fetch_models(provider: Provider, *, timeout: float = 30.0) -> list[dict]:
    """Fetch the raw ``/v1/models`` payload. Raises on auth or network failure."""
    response = httpx.get(
        f"{provider.base_url.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {provider.token()}"},
        timeout=timeout,
    )
    if response.status_code == 401:
        raise RuntimeError(
            f"{provider.name} rejected the token (401). Check {provider.token_env}."
            + (f" {provider.token_help}" if provider.token_help else "")
        )
    response.raise_for_status()
    return list(response.json().get("data", []))


def apply_policy(raw_models: list[dict], discovery: DiscoveryPolicy) -> list[DiscoveredModel]:
    """Classify every reported model as included or excluded, and say why.

    Exclusions are recorded rather than silently dropped: a run record that says
    which models were skipped, and on what rule, is the difference between
    "nothing was deployed" and "we filtered it out".
    """
    results: list[DiscoveredModel] = []
    for entry in raw_models:
        model_id = entry.get("id", "")
        if not model_id:
            continue

        reason: str | None = None
        for pattern in discovery.exclude:
            if pattern.search(model_id):
                reason = f"exclude:{pattern.pattern}"
                break

        if reason is None and model_id in discovery.aliases:
            reason = f"alias:{discovery.aliases[model_id]}"
        if reason is None and discovery.exclude_aliases and looks_like_alias(model_id):
            reason = "alias:unversioned"

        results.append(DiscoveredModel(id=model_id, raw=entry, excluded_by=reason))

    return sorted(results, key=lambda model: model.id.lower())


def discover(provider: Provider) -> list[DiscoveredModel]:
    """Fetch and classify in one step."""
    return apply_policy(fetch_models(provider), provider.discovery)


def fingerprint(provider: Provider, model_id: str) -> tuple[str, str]:
    """Ask one model a fixed question and hash the answer.

    Returns ``(hash, excerpt)``, or ``("", reason)`` when the model cannot chat —
    embedding and reranker models answer ``/chat/completions`` with a 404, which
    is a more reliable signal than any pattern match on the name.

    Verified deterministic on 2026-08-23: three consecutive calls to each of six
    models returned byte-identical text.
    """
    response = _post_with_backoff(
        provider,
        "/chat/completions",
        {
            "model": model_id,
            "messages": [{"role": "user", "content": FINGERPRINT_PROMPT}],
            "max_tokens": FINGERPRINT_MAX_TOKENS,
            "temperature": 0,
        },
        timeout=provider.generation.timeout_s,
    )
    if response.status_code != 200:
        return "", f"HTTP{response.status_code}"

    message = response.json()["choices"][0]["message"]
    text = (message.get("content") or message.get("reasoning_content") or "").strip()
    if not text:
        return "", "empty response"
    return hashlib.sha1(text.encode()).hexdigest()[:8], text.replace("\n", " ")[:70]


def group_by_fingerprint(fingerprints: dict[str, str]) -> dict[str, list[str]]:
    """Group ids that returned identical text, canonical id first.

    The canonical id is the versioned one: a leaderboard row must name a model
    that will still mean the same thing next month.
    """
    groups: dict[str, list[str]] = defaultdict(list)
    for model_id, digest in fingerprints.items():
        if digest:
            groups[digest].append(model_id)

    resolved: dict[str, list[str]] = {}
    for members in groups.values():
        if len(members) < 2:
            continue
        canonical = sorted(members, key=lambda m: (looks_like_alias(m), -len(m), m))[0]
        resolved[canonical] = sorted(m for m in members if m != canonical)
    return resolved


@dataclass(frozen=True)
class Completion:
    """One answer from one model, with enough context to explain a bad one.

    ``text`` is the message content and nothing else. When a reasoning model
    spends its whole budget thinking, content comes back empty while
    ``reasoning_chars`` is large — that is a truncated run, not a refusal, and
    the two have to stay distinguishable in the record.
    """

    model: str
    text: str
    ok: bool
    #: The budget this call was actually given, which is not always the one in
    #: models.yaml -- see the escalation in :mod:`tnb.generation`.
    max_tokens: int = 0
    finish_reason: str | None = None
    usage: dict | None = None
    reasoning_chars: int = 0
    attempts: int = 1
    latency_s: float = 0.0
    error: str | None = None


def complete(
    provider: Provider, model_id: str, prompt: str, *, max_tokens: int | None = None
) -> Completion:
    """Send one prompt as a single user message and return what came back.

    Both source papers prompt this way — one user turn, no system message — so
    the harness does too. Generation parameters come from ``models.yaml``;
    ``max_tokens`` overrides the budget for a second attempt at a call that ran
    out of it while thinking.
    """
    budget = max_tokens or provider.generation.max_tokens
    started = time.monotonic()
    try:
        response = _post_with_backoff(
            provider,
            "/chat/completions",
            {
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": budget,
                "temperature": provider.generation.temperature,
            },
            timeout=provider.generation.timeout_s,
            attempts=provider.generation.retries + 1,
        )
    except httpx.TransportError as error:
        return Completion(
            model=model_id,
            text="",
            ok=False,
            max_tokens=budget,
            error=f"{type(error).__name__}: {error}",
            attempts=provider.generation.retries + 1,
            latency_s=time.monotonic() - started,
        )

    latency = time.monotonic() - started
    if response.status_code != 200:
        return Completion(
            model=model_id,
            text="",
            ok=False,
            max_tokens=budget,
            error=f"HTTP{response.status_code}: {response.text[:200]}",
            latency_s=latency,
        )

    payload = response.json()
    choice = (payload.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    text = (message.get("content") or "").strip()
    reasoning = message.get("reasoning_content") or ""

    return Completion(
        model=model_id,
        text=text,
        ok=bool(text),
        max_tokens=budget,
        finish_reason=choice.get("finish_reason"),
        usage=payload.get("usage"),
        reasoning_chars=len(reasoning),
        latency_s=latency,
        error=None if text else "empty content",
    )
