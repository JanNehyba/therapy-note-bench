"""The judge: Gemini on Vertex AI, asked tens of thousands of small questions.

Scoring one note is roughly 60 calls — 23 rubric criteria, one per sentence for
conciseness, twelve Likert ratings — so the whole benchmark is on the order of
40 000. Three things follow from that number, and this module exists for them:

**Thinking is the cost.** A yes/no answer is one token; Gemini 2.5 Pro spends
around 480 tokens deciding it, and the OpenAI-compatible endpoint's
``reasoning_effort`` does not reliably reduce that — measured on 2026-08-24,
``low`` produced *more* thinking than the default. The native endpoint's
``thinkingConfig.thinkingBudget`` does: at 128 the same question cost 51
thinking tokens, a tenfold difference. That is why this talks to the native API
rather than reusing :mod:`tnb.providers.openai_compatible`.

**Nothing is asked twice.** Every answer is cached under
``scores/<judge>/<judge_prompt_version>/<provider>/<system>/<session>/<unit>.json``,
so a run that stops at question 20 000 resumes there, and re-scoring one model
never re-scores the other ten.

**The ceiling is real.** ``--max-judge-usd`` is checked against measured token
counts before each call and the run stops rather than exceeding it.

The project id and the service-account key live in ``.env`` and ``secrets/``,
both gitignored. Neither appears in this repository, in a result row, or on the
published page — a result carries the judge *model*, which is what
reproducibility needs.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from tnb.config import REPO_ROOT

CACHE_DIR = REPO_ROOT / "scores"

#: The judge, pinned. Part of every result row's comparability key: changing it
#: starts a new leaderboard rather than rewriting the old one.
DEFAULT_MODEL = "gemini-2.5-pro"

#: Gemini 2.5 Pro cannot be told to stop thinking — a budget of 0 is rejected —
#: and 128 is its minimum. Measured effect: ~480 thinking tokens down to ~51.
#: 2.5 Flash accepts 0. Part of the request digest, so changing it re-scores.
DEFAULT_THINKING_BUDGET = 128

#: Room for the answer itself, which is "Yes", "No" or a single digit.
ANSWER_TOKENS = 32


def output_ceiling(thinking_budget: int) -> int:
    """The output cap, which must leave room for the answer *after* the thinking.

    Gemini counts thinking tokens against ``maxOutputTokens``. Setting the cap
    to the size of the answer therefore produces exactly the failure this
    project already met on e-INFRA: the model thinks, runs out, and returns
    nothing with ``finishReason: MAX_TOKENS``. Measured on the first pilot: 26%
    of 142 questions came back empty at a cap of 64 against a 128-token thinking
    budget. Unused ceiling is not billed, so this is generous on purpose.
    """
    return thinking_budget + ANSWER_TOKENS


SCOPES = ("https://www.googleapis.com/auth/cloud-platform",)

#: Retriable: quota, backend hiccups, and a token that expired mid-run.
RETRIABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})


@dataclass(frozen=True)
class JudgeConfig:
    """Where the judge runs and how it is billed.

    Read from the environment rather than from ``models.yaml`` because it names
    a private cloud project. ``models.yaml`` is public; ``.env`` is not.
    """

    project: str
    location: str
    credentials_path: str
    model: str = DEFAULT_MODEL
    thinking_budget: int = DEFAULT_THINKING_BUDGET
    timeout_s: int = 120
    retries: int = 3
    backoff_s: int = 4
    concurrency: int = 4

    @property
    def endpoint(self) -> str:
        return (
            f"https://{self.location}-aiplatform.googleapis.com/v1/projects/"
            f"{self.project}/locations/{self.location}/publishers/google/models/"
            f"{self.model}:generateContent"
        )

    def fingerprint(self) -> dict:
        """What about the judge decides an answer, for the cache key.

        Deliberately excludes the project and the location: the same model at
        the same settings is the same judge, wherever it is billed.
        """
        return {
            "model": self.model,
            "thinking_budget": self.thinking_budget,
            "max_output_tokens": output_ceiling(self.thinking_budget),
            "temperature": 0,
        }


def config_from_env(**overrides) -> JudgeConfig:
    """Build a config from ``.env``, with an error that says what is missing."""
    missing = [
        name
        for name in ("VERTEX_PROJECT", "VERTEX_LOCATION", "GOOGLE_APPLICATION_CREDENTIALS")
        if not os.environ.get(name, "").strip()
    ]
    if missing:
        raise RuntimeError(
            f"The judge needs {', '.join(missing)} in .env. "
            "See .env.example; the service-account key belongs in secrets/, which is "
            "gitignored."
        )

    return JudgeConfig(
        project=os.environ["VERTEX_PROJECT"].strip(),
        location=os.environ["VERTEX_LOCATION"].strip(),
        credentials_path=os.environ["GOOGLE_APPLICATION_CREDENTIALS"].strip(),
        **overrides,
    )


@dataclass
class Answer:
    """One judge reply, with what it cost."""

    text: str
    ok: bool
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    latency_s: float = 0.0
    finish_reason: str | None = None
    error: str | None = None


class Judge:
    """A Vertex client that mints its own token and refreshes it when it expires.

    Kept as a class rather than free functions only because the access token has
    to be held somewhere: it lives about an hour, and a scoring run is longer.
    """

    def __init__(self, config: JudgeConfig):
        self.config = config
        self._credentials = None
        # Threads share one credential. Without the lock two of them refresh at
        # once and one reads a half-updated token, which the pilot met as an
        # HTTP 401 on 2 of 142 questions.
        self._lock = threading.Lock()

    def _token(self, *, force_refresh: bool = False) -> str:
        # Imported here so that `tnb models`, generation and the report never
        # need google-auth installed: it is the `judge` extra, not a core one.
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        with self._lock:
            if self._credentials is None:
                self._credentials = service_account.Credentials.from_service_account_file(
                    self.config.credentials_path, scopes=list(SCOPES)
                )
            if force_refresh or not self._credentials.valid:
                self._credentials.refresh(Request())
            return self._credentials.token

    def _payload(self, prompt: str) -> dict:
        return {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": output_ceiling(self.config.thinking_budget),
                "thinkingConfig": {"thinkingBudget": self.config.thinking_budget},
            },
        }

    def count_tokens(self, prompt: str) -> int:
        """Ask Vertex how large a prompt is, for the budget check before spending."""
        url = self.config.endpoint.replace(":generateContent", ":countTokens")
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {self._token()}"},
            json={"contents": [{"role": "user", "parts": [{"text": prompt}]}]},
            timeout=self.config.timeout_s,
        )
        response.raise_for_status()
        return int(response.json().get("totalTokens", 0))

    def ask(self, prompt: str, *, sleep=time.sleep) -> Answer:
        """One question. Retries quota and backend errors, reports the rest."""
        started = time.monotonic()
        last_error = "no attempt made"
        refresh_token = False

        for attempt in range(self.config.retries + 1):
            if attempt:
                sleep(self.config.backoff_s * attempt)
            try:
                response = httpx.post(
                    self.config.endpoint,
                    headers={"Authorization": f"Bearer {self._token(force_refresh=refresh_token)}"},
                    json=self._payload(prompt),
                    timeout=self.config.timeout_s,
                )
            except httpx.TransportError as error:
                last_error = f"{type(error).__name__}: {error}"
                continue

            # A 401 mid-run is an expired or raced token, not a bad key: mint a
            # fresh one and ask again. A genuinely wrong key fails every attempt
            # and says so.
            if response.status_code == 401:
                refresh_token = True
                last_error = f"HTTP401: {response.text[:160]}"
                continue
            if response.status_code in RETRIABLE_STATUS:
                last_error = f"HTTP{response.status_code}: {response.text[:160]}"
                continue
            if response.status_code != 200:
                return Answer(
                    text="",
                    ok=False,
                    latency_s=time.monotonic() - started,
                    error=f"HTTP{response.status_code}: {response.text[:160]}",
                )
            return self._parse(response.json(), time.monotonic() - started)

        return Answer(text="", ok=False, latency_s=time.monotonic() - started, error=last_error)

    @staticmethod
    def _parse(body: dict, latency: float) -> Answer:
        usage = body.get("usageMetadata") or {}
        candidates = body.get("candidates") or [{}]
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts).strip()
        finish = candidates[0].get("finishReason")

        return Answer(
            text=text,
            # An empty answer is a failure even at HTTP 200. It is usually the
            # model spending its whole output budget on thinking, and scoring it
            # would silently record a "No" that nobody said.
            ok=bool(text),
            input_tokens=int(usage.get("promptTokenCount", 0)),
            output_tokens=int(usage.get("candidatesTokenCount", 0)),
            thinking_tokens=int(usage.get("thoughtsTokenCount", 0)),
            latency_s=latency,
            finish_reason=finish,
            error=None if text else f"empty answer (finishReason={finish})",
        )


# --- what a judge call costs -------------------------------------------------

#: Vertex list price per million tokens for the models this judge can use, as
#: published on 2026-08-24. Used only to enforce ``--max-judge-usd`` and to
#: report what a run cost; the authority on what was actually billed is the
#: cloud console, and the pilot prints both so they can be compared.
PRICES_USD_PER_MTOK = {
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
}


def estimate_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Cost of one call. Thinking tokens are output tokens and are billed as such."""
    prices = PRICES_USD_PER_MTOK.get(model)
    if prices is None:
        return 0.0
    return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000


@dataclass
class Spend:
    """Running total for one scoring run, and the ceiling it must not cross."""

    limit_usd: float
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0

    def record(self, model: str, answer: Answer) -> None:
        self.calls += 1
        self.input_tokens += answer.input_tokens
        # Thinking is billed as output even though it never reaches us.
        self.output_tokens += answer.output_tokens + answer.thinking_tokens

    def usd(self, model: str) -> float:
        return estimate_usd(model, self.input_tokens, self.output_tokens)

    def would_exceed(self, model: str, next_input_tokens: int) -> bool:
        """Check before spending, not after.

        The next call's output is unknown, so it is assumed to be the full
        output budget plus the thinking budget — the most it can be.
        """
        projected = self.usd(model) + estimate_usd(
            model, next_input_tokens, output_ceiling(DEFAULT_THINKING_BUDGET)
        )
        return projected > self.limit_usd


def cache_path(
    judge_model: str,
    judge_prompt_version: str,
    provider: str,
    system_id: str,
    session_id: str,
    unit: str,
    *,
    root: Path | None = None,
) -> Path:
    """Where one answer lives. Mirrors the generation cache, for the same reason."""
    from tnb.generation import _slug

    return (
        (root or CACHE_DIR)
        / _slug(judge_model)
        / _slug(judge_prompt_version)
        / _slug(provider)
        / _slug(system_id)
        / _slug(session_id)
        / f"{_slug(unit)}.json"
    )


def load_cached(path: Path, fingerprint: dict) -> dict | None:
    """A previous answer, if it was produced by the same judge at the same settings."""
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not record.get("ok"):
        return None
    if record.get("judge_fingerprint") != fingerprint:
        return None
    return record


def write_cached(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
