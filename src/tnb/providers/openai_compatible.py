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
import os
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
                f"{provider.url.rstrip('/')}{path}",
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


def catalogue_url(provider: Provider) -> str:
    """Where to ask what this provider serves.

    ``<base_url>/models`` unless the provider says otherwise. Vertex's
    OpenAI-compatible endpoint answers chat completions only -- ``/models``
    there returns a 404 HTML page -- so it names the publisher catalogue, with
    ``{project}`` and ``{location}`` filled from the environment so no account
    identifier is ever written into a tracked file.
    """
    configured = provider.discovery.catalogue_url
    if not configured:
        return f"{provider.url.rstrip('/')}/models"
    return configured.format(
        project=os.environ.get("VERTEX_PROJECT", ""),
        location=os.environ.get("VERTEX_LOCATION", ""),
    )


def fetch_models(provider: Provider, *, timeout: float = 30.0) -> list[dict]:
    """Fetch the raw catalogue. Raises on auth or network failure.

    Entries are normalised to the OpenAI shape -- an ``id`` key -- so everything
    downstream sees one format whatever the provider reported.
    """
    response = httpx.get(
        catalogue_url(provider),
        headers={"Authorization": f"Bearer {provider.token()}"},
        timeout=timeout,
    )
    if response.status_code == 401:
        raise RuntimeError(
            f"{provider.name} rejected the token (401). Check {provider.token_env}."
            + (f" {provider.token_help}" if provider.token_help else "")
        )
    response.raise_for_status()

    discovery = provider.discovery
    entries = list(response.json().get(discovery.catalogue_key, []))
    if discovery.catalogue_id_field == "id" and not discovery.model_prefix:
        return entries

    normalised = []
    for entry in entries:
        raw_id = str(entry.get(discovery.catalogue_id_field, ""))
        if not raw_id:
            continue
        # Vertex reports `publishers/google/models/gemini-2.5-pro`; the chat
        # endpoint wants `google/gemini-2.5-pro`. Only the last segment is the
        # model, and the prefix the endpoint expects is configured, not guessed.
        normalised.append({**entry, "id": discovery.model_prefix + raw_id.rsplit("/", 1)[-1]})
    return normalised


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
        # An include list, where one is given, is the whole rule: everything it
        # does not name is out. Recorded as a reason like any other exclusion,
        # so a run record still shows what the endpoint offered.
        if discovery.include and not any(p.search(model_id) for p in discovery.include):
            reason = "not on the include list"
        for pattern in discovery.exclude:
            if reason is None and pattern.search(model_id):
                reason = f"exclude:{pattern.pattern}"
                break

        if reason is None and model_id in discovery.aliases:
            reason = f"alias:{discovery.aliases[model_id]}"
        # An explicit include list has already said which ids are wanted, so the
        # unversioned-name heuristic is not applied on top of it: it drops any id
        # without a digit, which is right for a deployment that invents aliases
        # and wrong for a catalogue whose real names happen to look like them.
        if (
            reason is None
            and discovery.exclude_aliases
            and not discovery.include
            and looks_like_alias(model_id)
        ):
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
    #: What this repository says went wrong. One of a closed set -- see
    #: `http_reason` -- so that nothing a provider wrote can travel from here
    #: into `results/rows.jsonl`, which is committed and published.
    error: str | None = None
    #: What the provider actually said, kept for debugging. Written only into
    #: the generation record under the gitignored `generations/`, never into a
    #: row, a page or a log line.
    error_body: str = ""


def build_request(provider: Provider, model_id: str, prompt: str, budget: int) -> dict:
    """The request body, spelled the way this provider wants it.

    Separate from :func:`complete` so a dialect can be checked without a network
    call -- which is the only way to test it, since the failures it prevents are
    400s from a live endpoint.
    """
    dialect = provider.generation.dialect
    body: dict = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        dialect.max_tokens_field: budget,
    }
    # Omitted, not defaulted: a provider that rejects any temperature but its own
    # rejects the field even when the value matches, and sending nothing is the
    # only thing it accepts.
    if dialect.send_temperature:
        body["temperature"] = provider.generation.temperature
    if dialect.effort_field and provider.generation.effort:
        body[dialect.effort_field] = provider.generation.effort
    return body


#: How much of a non-200 body is kept **in the generation record**, which lives
#: under the gitignored `generations/`. It no longer reaches `Completion.error`.
#:
#: An earlier version of this comment argued the cut was safe because
#: `normalise_reason` masks secrets and keeps fewer characters than this, so a
#: bisected secret could not survive. That reasoning was sound and it answered
#: the wrong question. Masking is shaped for things that look like credentials;
#: request *content* looks like prose, so nothing touched it. e-INFRA is
#: LiteLLM-fronted and a 400 or 413 on an over-long prompt echoes the request,
#: and three rows in the committed `results/rows.jsonl` carry a verbatim 429
#: body to prove the path is live rather than theoretical.
#:
#: So the body is kept where it is useful and cannot travel, and `error` carries
#: a phrase this repository wrote instead.
ERROR_BODY_CHARS = 200

#: What `error` says for a status code. A closed set, so `Completion.error` is
#: always a value the harness chose and never one a provider sent.
#:
#: The `HTTP<code>` prefix is load-bearing and must survive any edit here:
#: `results.INFRASTRUCTURE_ERRORS` matches on it to decide that a call failed
#: before the model had any say, which is what stops a run charging the
#: endpoint's refusal to the model as a failure.
HTTP_PHRASES: dict[int, str] = {
    400: "bad request",
    401: "unauthorized",
    403: "forbidden",
    404: "model not found",
    408: "gateway timeout",
    409: "conflict",
    413: "request too large",
    422: "unprocessable request",
    425: "too early",
    429: "rate limited",
    500: "backend error",
    502: "backend error",
    503: "backend error",
    504: "backend error",
}

#: For a status nobody has seen yet. Still says nothing the provider wrote.
UNKNOWN_HTTP_PHRASE = "refused"


def http_reason(status: int) -> str:
    """The one thing `error` may say about a non-200, whatever came back."""
    return f"HTTP{status}: {HTTP_PHRASES.get(status, UNKNOWN_HTTP_PHRASE)}"


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
            build_request(provider, model_id, prompt, budget),
            timeout=provider.generation.timeout_s,
            attempts=provider.generation.retries + 1,
        )
    except httpx.TransportError as error:
        return Completion(
            model=model_id,
            text="",
            ok=False,
            max_tokens=budget,
            error=type(error).__name__,
            error_body=f"{type(error).__name__}: {error}"[:ERROR_BODY_CHARS],
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
            error=http_reason(response.status_code),
            error_body=response.text[:ERROR_BODY_CHARS],
            latency_s=latency,
        )

    payload = response.json()
    choice = (payload.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    text = (message.get("content") or "").strip()
    reasoning = message.get("reasoning_content") or ""
    finish = choice.get("finish_reason")

    # A sentence that stops mid-word is not an answer. `finish_reason` was
    # parsed and recorded here and never once read, so 16 iCARE sections cut
    # off at the budget were filed as complete: the escalation `generation.py`
    # already has is gated on `ok`, so the one thing built to handle this never
    # fired. What that measures is our token budget, not the model.
    truncated = finish == "length"

    return Completion(
        model=model_id,
        text=text,
        ok=bool(text) and not truncated,
        max_tokens=budget,
        finish_reason=finish,
        usage=payload.get("usage"),
        reasoning_chars=len(reasoning),
        latency_s=latency,
        error=(
            None
            if text and not truncated
            else f"truncated at max_tokens={budget}"
            if truncated
            else "empty content"
        ),
    )
