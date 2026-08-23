"""Discovery against the e-INFRA CZ OpenAI-compatible endpoint.

The live ``GET /v1/models`` response is the only authority on what can be
benchmarked. Documentation drifts; aliases move. Everything here exists to turn
that response into a reproducible benchmark set without ever pinning a list.

The endpoint returns almost no useful metadata — of 31 models reported on
2026-08-23, exactly one carried a ``mode`` field — so what a model *is* has to be
established by asking it. See :func:`fingerprint`.
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from dataclasses import dataclass

import httpx

from tnb.config import DiscoveryPolicy, Policy

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


def _post_with_backoff(
    policy: Policy, path: str, payload: dict, *, timeout: float, attempts: int = 5
) -> httpx.Response:
    """POST, retrying on 429. e-INFRA rate-limits per API key, not per model."""
    last: httpx.Response | None = None
    for attempt in range(attempts):
        response = httpx.post(
            f"{policy.base_url.rstrip('/')}{path}",
            headers={"Authorization": f"Bearer {policy.token()}"},
            json=payload,
            timeout=timeout,
        )
        if response.status_code != 429:
            return response
        last = response
        time.sleep(policy.generation.backoff_s * (attempt + 1))
    assert last is not None
    return last


def fetch_models(policy: Policy, *, timeout: float = 30.0) -> list[dict]:
    """Fetch the raw ``/v1/models`` payload. Raises on auth or network failure."""
    response = httpx.get(
        f"{policy.base_url.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {policy.token()}"},
        timeout=timeout,
    )
    if response.status_code == 401:
        raise RuntimeError(
            "e-INFRA rejected the token (401). Check EINFRA_API_TOKEN; keys are "
            "issued per account at https://chat.ai.e-infra.cz -> Account -> API keys."
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


def discover(policy: Policy) -> list[DiscoveredModel]:
    """Fetch and classify in one step."""
    return apply_policy(fetch_models(policy), policy.discovery)


def fingerprint(policy: Policy, model_id: str) -> tuple[str, str]:
    """Ask one model a fixed question and hash the answer.

    Returns ``(hash, excerpt)``, or ``("", reason)`` when the model cannot chat —
    embedding and reranker models answer ``/chat/completions`` with a 404, which
    is a more reliable signal than any pattern match on the name.

    Verified deterministic on 2026-08-23: three consecutive calls to each of six
    models returned byte-identical text.
    """
    response = _post_with_backoff(
        policy,
        "/chat/completions",
        {
            "model": model_id,
            "messages": [{"role": "user", "content": FINGERPRINT_PROMPT}],
            "max_tokens": FINGERPRINT_MAX_TOKENS,
            "temperature": 0,
        },
        timeout=policy.generation.timeout_s,
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
