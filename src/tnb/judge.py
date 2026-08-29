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

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from tnb import google_auth
from tnb.config import REPO_ROOT

CACHE_DIR = REPO_ROOT / "scores"

#: The judge, pinned. Part of every result row's comparability key: changing it
#: starts a new leaderboard rather than rewriting the old one.
DEFAULT_MODEL = "gemini-3.1-pro-preview"

#: The second judge, and why there is one. Both of these models also *write*
#: notes here, so each is marking its own homework; two of them, scoring
#: everything including their own family, turn that from a caveat into a number
#: -- see tnb.scoring.preference.
#:
#: Chosen by measurement over the same 150 notes the humans rated, not by
#: reputation. Krippendorff's alpha on the rubric, every candidate at one
#: setting, against a human-vs-human ceiling of 0.504:
#:
#:     gemini-3.1-pro-preview  0.600      gpt-5.6-terra  0.520
#:     gemini-2.5-pro          0.574      gpt-5.6-sol    0.510
#:     gemini-3.7-flash        0.544
#:     gemini-2.5-flash        0.537
#:     gemini-3.5-flash        0.537
#:
#: Read as bands, not as an order. Of the 21 pairs, 7 are separated by more
#: than `calibration.ALPHA_MARGIN`: this one over five of the other six, and
#: `gemini-2.5-pro` over the two GPT candidates. Nothing else separates -- not
#: the three `flash` models from each other (they span 0.008), and not `sol` at
#: $20 per million output tokens from `terra` at $12 or from `flash` at $2.50.
#: Capability does not predict judge quality on this task, and neither does
#: price.
#:
#: This comment used to say the newest flash was the worst of the three. It was
#: reading three numbers taken at different thinking budgets; at one budget the
#: order reverses, which is what a 0.008 spread should be expected to do.
#:
#: Every candidate agrees with a therapist at least as often as the two
#: therapists agree with each other, but only the two `pro` models clear that
#: ceiling by the margin.
SECOND_JUDGE = "gpt-5.6-terra"

#: Candidates worth measuring against the human annotators before one is chosen.
#: Reputation does not pick a judge here; agreement with two therapists does.
#: Probed live on 2026-08-25 -- every one of these answers a rubric question.
JUDGE_CANDIDATES = (
    "gemini-2.5-pro",
    "gemini-3.1-pro-preview",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gpt-5.6-terra",
    # Added after terra calibrated at 0.520 -- above the human ceiling of 0.504,
    # but the weakest of six and the only one with a *negative* agreement on
    # faithfulness. Worth $17 to find out whether the flagship is better before
    # committing $65 to a full pass with the one that barely cleared.
    "gpt-5.6-sol",
)


#: Which transport a judge model speaks. Derived from the name because that is
#: the one thing about a model that is never ambiguous here, and overridable on
#: the config for the day it is.
def backend_for(model: str) -> str:
    return "openai" if model.startswith("gpt-") else "vertex"


#: `v1beta1` at the `global` endpoint, for every model rather than per model.
#:
#: Found by asking rather than guessing: `us-west4` serves no Gemini 3.x at all,
#: and `v1` does not know them either -- the earlier conclusion that "Gemini 3 is
#: not on this project" was wrong on both counts. 2.5 answers here too, so one
#: path serves every candidate and a judge swap needs no plumbing.
API_VERSION = "v1beta1"
API_LOCATION = "global"

#: Gemini 2.5 Pro cannot be told to stop thinking — a budget of 0 is rejected —
#: and 128 is its minimum. Measured effect: ~480 thinking tokens down to ~51.
#: 2.5 Flash accepts 0. Part of the request digest, so changing it re-scores.
DEFAULT_THINKING_BUDGET = 256

#: Room for the answer itself, which is "Yes", "No" or a single digit.
#:
#: **The default is load-bearing.** It is inside the judge fingerprint, so this
#: number is part of what makes a cached answer reusable: 169,000 answers are
#: keyed on it. Changing it here re-asks all of them. `JudgeConfig.answer_tokens`
#: exists so one run can have more room without doing that -- see the docstring
#: there for what it is for and what it costs.
ANSWER_TOKENS = 32


def output_ceiling(thinking_budget: int, answer_tokens: int = ANSWER_TOKENS) -> int:
    """The output cap, which must leave room for the answer *after* the thinking.

    Gemini counts thinking tokens against ``maxOutputTokens``. Setting the cap
    to the size of the answer therefore produces exactly the failure this
    project already met on e-INFRA: the model thinks, runs out, and returns
    nothing with ``finishReason: MAX_TOKENS``. Measured on the first pilot: 26%
    of 142 questions came back empty at a cap of 64 against a 128-token thinking
    budget. Unused ceiling is not billed, so this is generous on purpose.
    """
    return thinking_budget + answer_tokens


#: What each provider calls "I ran out of room". Both spellings are checked
#: everywhere rather than per backend, because a judge answer is read by code
#: that does not know which one produced it.
TRUNCATED = frozenset({"MAX_TOKENS", "length"})


def _stopped_early(text: str, finish: str | None) -> str | None:
    """Why an HTTP 200 was not an answer, or None when it was one."""
    if finish in TRUNCATED:
        return f"answer truncated ({finish})"
    if not text:
        return f"empty answer (finish_reason={finish})"
    return None


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
    #: How much room the answer gets after the thinking, and part of the
    #: fingerprint.
    #:
    #: A reasoning judge that spends its whole thinking budget has nothing left
    #: to answer with, and returns `MAX_TOKENS` and no text. Measured on the
    #: Czech criteria at a budget of 2048: 41 of 2,544 questions, and asking
    #: again at temperature 0 reproduces them rather than clearing them.
    #:
    #: Raising it costs a new comparability group for whatever it is raised for,
    #: because it changes the fingerprint -- which is the point of it being here
    #: rather than a module constant. A track that leaves it alone keeps its
    #: cache; a track that raises it re-asks its own questions and nobody
    #: else's.
    answer_tokens: int = ANSWER_TOKENS
    #: The same room, for the backend that has no thinking budget to add it to.
    #: `OPENAI_OUTPUT_CEILING` is pinned at the value its 51,000 cached answers
    #: were produced under and must stay there; this is added on top, so a run
    #: that leaves it at zero is byte-identical and every existing answer still
    #: matches. Measured: 10 of terra's 1,272 Czech answers truncate at the
    #: pinned ceiling.
    extra_answer_room: int = 0
    timeout_s: int = 120
    retries: int = 3
    backoff_s: int = 4
    concurrency: int = 4

    #: Empty means "derive from the model name". Set it only to override.
    backend: str = ""
    #: Reasoning effort, for a backend that has one. Measured on `gpt-5.6-terra`:
    #: a rubric question spends 0 reasoning tokens at every level and answers
    #: identically, but a Likert rating at `none` disagreed with `low`/`medium`/
    #: `high` on two of six questions, so `none` is not safe here. `medium` and
    #: `high` agreed on all six; `medium` is the cheaper of the two.
    effort: str = "medium"

    @property
    def transport(self) -> Backend:
        return BACKENDS[self.backend or backend_for(self.model)]

    @property
    def endpoint(self) -> str:
        return self.transport.endpoint(self)

    def fingerprint(self) -> dict:
        """What about the judge decides an answer, for the cache key.

        Deliberately excludes the project and the location: the same model at
        the same settings is the same judge, wherever it is billed.

        Delegated to the transport because the two have different settings to
        record -- and because the Vertex shape must not move by so much as a
        key. 65 832 answers are cached against it, and `load_cached` rejects any
        record whose fingerprint differs, so a cosmetic change here is a full
        re-judge of the whole corpus.
        """
        return self.transport.fingerprint(self)


def config_from_env(**overrides) -> JudgeConfig:
    """Build a config from ``.env``, with an error that says what is missing.

    Only what the chosen backend actually needs: asking for a Vertex project in
    order to run a GPT judge would be a confusing way to fail.
    """
    model = overrides.get("model", DEFAULT_MODEL)
    backend = overrides.get("backend") or backend_for(model)
    required = BACKENDS[backend].required_env

    missing = [name for name in required if not os.environ.get(name, "").strip()]
    if missing:
        raise RuntimeError(
            f"The {backend} judge needs {', '.join(missing)} in .env. "
            "See .env.example; the service-account key belongs in secrets/, which is "
            "gitignored."
        )

    return JudgeConfig(
        project=os.environ.get("VERTEX_PROJECT", "").strip(),
        location=os.environ.get("VERTEX_LOCATION", "").strip(),
        credentials_path=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip(),
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


# --- transports ---------------------------------------------------------------
#
# Everything above and below this block is shared: the retry loop, the 401
# refresh, the spend ceiling, the answer cache, and every prompt. Only three
# things differ between a Vertex judge and an OpenAI one -- where to post, what
# shape to post, and how to read the reply -- so only those three live here.


class Backend:
    """Where to post, what to post, how to read the reply."""

    name = ""
    #: Environment variables without which this transport cannot run at all.
    required_env: tuple[str, ...] = ()

    def endpoint(self, config: JudgeConfig) -> str:
        raise NotImplementedError

    def token(self, config: JudgeConfig, *, force_refresh: bool = False) -> str:
        raise NotImplementedError

    def payload(self, config: JudgeConfig, prompt: str) -> dict:
        raise NotImplementedError

    def parse(self, body: dict, latency: float) -> Answer:
        raise NotImplementedError

    def fingerprint(self, config: JudgeConfig) -> dict:
        raise NotImplementedError

    def count_tokens(self, config: JudgeConfig, prompt: str) -> int:
        """How large a prompt is, for the budget check before spending."""
        raise NotImplementedError


class VertexBackend(Backend):
    """Gemini through Vertex's native endpoint.

    Native rather than Vertex's OpenAI-compatible route on purpose: only the
    native one takes `thinkingConfig.thinkingBudget`, and capping the thinking
    budget is what took a rubric answer from 480 reasoning tokens to 51.
    `reasoning_effort` on the compatible endpoint did not.
    """

    name = "vertex"
    required_env = ("VERTEX_PROJECT", "VERTEX_LOCATION", "GOOGLE_APPLICATION_CREDENTIALS")

    def endpoint(self, config: JudgeConfig) -> str:
        host = (
            "aiplatform.googleapis.com"
            if API_LOCATION == "global"
            else f"{API_LOCATION}-aiplatform.googleapis.com"
        )
        return (
            f"https://{host}/{API_VERSION}/projects/{config.project}"
            f"/locations/{API_LOCATION}/publishers/google/models/"
            f"{config.model}:generateContent"
        )

    def token(self, config: JudgeConfig, *, force_refresh: bool = False) -> str:
        return google_auth.token(force_refresh=force_refresh, path=config.credentials_path)

    def payload(self, config: JudgeConfig, prompt: str) -> dict:
        return {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": output_ceiling(config.thinking_budget, config.answer_tokens),
                "thinkingConfig": {"thinkingBudget": config.thinking_budget},
            },
        }

    def parse(self, body: dict, latency: float) -> Answer:
        usage = body.get("usageMetadata") or {}
        candidates = body.get("candidates") or [{}]
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts).strip()
        finish = candidates[0].get("finishReason")

        cut_off = finish in TRUNCATED
        return Answer(
            text=text,
            # An empty answer is a failure even at HTTP 200, and so is one that
            # stopped at the cap. Both are the model spending its output budget
            # on thinking; the difference is only whether a fragment leaked out
            # before it ran out. Scoring either would record a "No" that nobody
            # said -- `parse_yes_no` reads anything that is not a yes as a no,
            # which is TN-Eval's own parser and stays that way.
            ok=bool(text) and not cut_off,
            input_tokens=int(usage.get("promptTokenCount", 0)),
            output_tokens=int(usage.get("candidatesTokenCount", 0)),
            thinking_tokens=int(usage.get("thoughtsTokenCount", 0)),
            latency_s=latency,
            finish_reason=finish,
            error=_stopped_early(text, finish),
        )

    def fingerprint(self, config: JudgeConfig) -> dict:
        """Frozen. 65 832 cached answers are keyed on exactly these four keys.

        Adding a field -- even `backend`, even `effort` -- would invalidate
        every one of them, because `load_cached` rejects a record whose
        fingerprint differs. Anything new belongs in the OpenAI shape, which has
        no history to protect.
        """
        return {
            "model": config.model,
            "thinking_budget": config.thinking_budget,
            "max_output_tokens": output_ceiling(config.thinking_budget, config.answer_tokens),
            "temperature": 0,
        }

    def count_tokens(self, config: JudgeConfig, prompt: str) -> int:
        response = httpx.post(
            self.endpoint(config).replace(":generateContent", ":countTokens"),
            headers={"Authorization": f"Bearer {self.token(config)}"},
            json={"contents": [{"role": "user", "parts": [{"text": prompt}]}]},
            timeout=config.timeout_s,
        )
        response.raise_for_status()
        return int(response.json().get("totalTokens", 0))


class OpenAIBackend(Backend):
    """GPT through the ordinary chat-completions endpoint.

    Three quirks of the reasoning family, each established by sending the
    request rather than by reading the documentation: it wants
    `max_completion_tokens`, it rejects the `temperature` *field* rather than
    just the value, and it has `reasoning_effort` where Vertex has a thinking
    budget.
    """

    name = "openai"
    required_env = ("OPENAI_API_KEY",)
    base_url = "https://api.openai.com/v1"

    def endpoint(self, config: JudgeConfig) -> str:
        return f"{self.base_url}/chat/completions"

    def token(self, config: JudgeConfig, *, force_refresh: bool = False) -> str:
        # A static key; `force_refresh` is meaningless and a 401 here is a wrong
        # key rather than an expired one.
        value = os.environ.get("OPENAI_API_KEY", "").strip()
        if not value:
            raise RuntimeError("OPENAI_API_KEY is not set. See .env.example.")
        return value

    def payload(self, config: JudgeConfig, prompt: str) -> dict:
        body = {
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}],
            # Room for the reasoning as well as the answer, the same reason the
            # Vertex ceiling exists. Measured on terra: a Likert question spends
            # up to ~170 reasoning tokens at medium, a rubric question spends 0.
            "max_completion_tokens": OPENAI_OUTPUT_CEILING + config.extra_answer_room,
        }
        if config.effort:
            body["reasoning_effort"] = config.effort
        return body

    def parse(self, body: dict, latency: float) -> Answer:
        usage = body.get("usage") or {}
        choices = body.get("choices") or [{}]
        message = choices[0].get("message") or {}
        text = (message.get("content") or "").strip()
        finish = choices[0].get("finish_reason")
        details = usage.get("completion_tokens_details") or {}
        thinking = int(details.get("reasoning_tokens", 0))

        return Answer(
            text=text,
            # Same rule as the Vertex parser above.
            ok=bool(text) and finish not in TRUNCATED,
            input_tokens=int(usage.get("prompt_tokens", 0)),
            # Reported completion tokens already include the reasoning, so the
            # two are separated here to match the Vertex shape -- `Spend` adds
            # them back together and would otherwise count thinking twice.
            output_tokens=max(0, int(usage.get("completion_tokens", 0)) - thinking),
            thinking_tokens=thinking,
            latency_s=latency,
            finish_reason=finish,
            error=_stopped_early(text, finish),
        )

    def fingerprint(self, config: JudgeConfig) -> dict:
        """Effort is in here because it changes the answer.

        Measured on terra over six Likert questions: `none` disagreed with
        `low`/`medium`/`high` on two of them. Two efforts are two judges and
        must not share a cache entry.
        """
        return {
            "backend": self.name,
            "model": config.model,
            "effort": config.effort,
            "max_output_tokens": OPENAI_OUTPUT_CEILING + config.extra_answer_room,
        }

    def count_tokens(self, config: JudgeConfig, prompt: str) -> int:
        """Estimated, not asked: this API has no counting endpoint.

        Four characters per token is the usual rule of thumb and it only feeds
        the pre-spend projection, which is deliberately an over-estimate.
        """
        return len(prompt) // 4


#: Extra output room for a reasoning model that has no thinking budget to cap.
#: Measured on terra at effort `medium`: 0 reasoning tokens on a rubric
#: question, up to ~170 on a Likert one.
REASONING_HEADROOM = 512

#: What an OpenAI judge is allowed to emit, thinking included. A fixed number
#: rather than one derived from `thinking_budget`, because the two are unrelated
#: mechanisms and tying them together made a Vertex change invalidate an OpenAI
#: cache: raising Gemini's budget from 128 to 256 would have thrown away terra's
#: 51 000 answers, not one of which was ever truncated.
#:
#: Pinned at the value the existing cache was produced under -- output_ceiling(128)
#: plus the headroom -- so decoupling it changes no fingerprint today.
OPENAI_OUTPUT_CEILING = 160 + REASONING_HEADROOM

BACKENDS: dict[str, Backend] = {"vertex": VertexBackend(), "openai": OpenAIBackend()}


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
        """The bearer token, from the one credential the process shares.

        Generation needs the same credential now that Gemini writes notes as
        well as judging them, and two objects refreshing independently is the
        race this already met once -- an HTTP 401 on 2 of 142 questions.
        """
        return self.config.transport.token(self.config, force_refresh=force_refresh)

    def _payload(self, prompt: str) -> dict:
        return self.config.transport.payload(self.config, prompt)

    def count_tokens(self, prompt: str) -> int:
        """How large a prompt is, for the budget check before spending."""
        return self.config.transport.count_tokens(self.config, prompt)

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
            return self.config.transport.parse(response.json(), time.monotonic() - started)

        return Answer(text="", ok=False, latency_s=time.monotonic() - started, error=last_error)

    @staticmethod
    def _parse(body: dict, latency: float) -> Answer:
        """Kept as the Vertex parser so existing callers and tests still work."""
        return BACKENDS["vertex"].parse(body, latency)


# --- what a judge call costs -------------------------------------------------

#: Vertex list price per million tokens for the models this judge can use, as
#: published on 2026-08-24. Used only to enforce ``--max-judge-usd`` and to
#: report what a run cost; the authority on what was actually billed is the
#: cloud console, and the pilot prints both so they can be compared.
PRICES_USD_PER_MTOK = {
    # Vertex, checked 2026-08-24.
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "gemini-3.1-pro-preview": {"input": 1.25, "output": 10.00},
    "gemini-3.7-flash": {"input": 0.30, "output": 2.50},
    "gemini-3.5-flash": {"input": 0.30, "output": 2.50},
    # OpenAI, from developers.openai.com/api/docs/pricing on 2026-08-25, the
    # short-context tier -- every prompt this judge sends is far under the long
    # context threshold. Sol's is promotional pricing, stated as holding at
    # least until 2026-11-21, so it is the one most likely to move.
    "gpt-5.6-luna": {"input": 0.20, "output": 1.20},
    "gpt-5.6-terra": {"input": 2.00, "output": 12.00},
    "gpt-5.6-sol": {"input": 4.00, "output": 20.00},
}


class UnpricedModel(RuntimeError):
    """A judge whose price is unknown, asked to run under a spending ceiling."""


def estimate_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Cost of one call. Thinking tokens are output tokens and are billed as such.

    Raises on a model with no entry above rather than returning zero.

    Returning zero is what this did, and it silently **disabled the ceiling for
    every model not in the table** -- which was all five of the 3.x judge
    candidates and all three GPT ones, the exact set for which real money is now
    at stake. A guard that quietly stops guarding is worse than no guard,
    because the run reports a total of $0.00 and everyone believes it.

    Prices go stale, so this is not the authority on what was billed; the
    provider's console is. It is the authority on when to stop.
    """
    prices = PRICES_USD_PER_MTOK.get(model)
    if prices is None:
        raise UnpricedModel(
            f"No price is recorded for judge model {model!r}, so a spending ceiling "
            f"cannot be enforced. Add it to judge.PRICES_USD_PER_MTOK, or pass "
            f"--max-judge-usd 0 to run without a ceiling deliberately."
        )
    return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000


@dataclass
class Spend:
    """Running total for one scoring run, and the ceiling it must not cross.

    Threads share one of these. Whether ``+=`` on an attribute can lose an
    update was tested rather than assumed: 8 threads and 240 000 increments,
    with the switch interval forced to a nanosecond, lost nothing on CPython
    3.13 -- the GIL makes that store effectively atomic. It is not a language
    guarantee, though, and a free-threaded build removes it, so the lock is here
    anyway. It is taken once per API call that already takes seconds.
    """

    limit_usd: float
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record(self, model: str, answer: Answer) -> None:
        with self._lock:
            self.calls += 1
            self.input_tokens += answer.input_tokens
            # Thinking is billed as output even though it never reaches us.
            self.output_tokens += answer.output_tokens + answer.thinking_tokens

    def usd(self, model: str) -> float | None:
        """What this run has cost so far, or None when the model has no price.

        None rather than 0.0: a run whose cost is unknown must not print a
        number that looks like a measurement.
        """
        try:
            return estimate_usd(model, self.input_tokens, self.output_tokens)
        except UnpricedModel:
            return None

    def would_exceed(self, model: str, next_input_tokens: int) -> bool:
        """Check before spending, not after.

        The next call's output is unknown, so it is assumed to be the full
        output budget plus the thinking budget — the most it can be.

        A ceiling of 0 means "no ceiling", which is the only way to run an
        unpriced model: the caller has said so explicitly rather than finding
        out afterwards.
        """
        if self.limit_usd <= 0:
            return False
        spent = self.usd(model)
        if spent is None:
            raise UnpricedModel(
                f"Judge model {model!r} has no recorded price, so --max-judge-usd "
                f"cannot be enforced. Add it to judge.PRICES_USD_PER_MTOK, or pass "
                f"--max-judge-usd 0 to run without a ceiling deliberately."
            )
        projected = spent + estimate_usd(
            model, next_input_tokens, output_ceiling(DEFAULT_THINKING_BUDGET)
        )
        return projected > self.limit_usd


def _slug_model(model: str) -> str:
    """The directory one judge's answers live under."""
    from tnb.generation import _slug

    return _slug(model)


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


def prompt_digest(prompt: str) -> str:
    """Hash of the exact question that was asked.

    The answer cache is keyed on (judge, prompt version, provider, system,
    session, unit) and the fingerprint covers the judge's settings -- nothing
    in either mentions **the note**. So re-generating a note and re-scoring it
    silently reused the judgement of the text it replaced, and the row would
    have carried a score for a note that no longer exists. The generation cache
    has hashed its request from the start; this side never did.
    """
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def load_cached(path: Path, fingerprint: dict, prompt: str | None = None) -> dict | None:
    """A previous answer, if it was produced by the same judge at the same
    settings, about the same text."""
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
    # A record with no digest predates this check. Treated as unknown rather
    # than as wrong: rejecting them would re-ask 169 036 answers to catch the
    # handful of notes that actually changed, and the ones that did change are
    # dealt with directly instead.
    stored = record.get("prompt_sha256")
    if prompt is not None and stored is not None and stored != prompt_digest(prompt):
        return None
    return record


class Reinstrumented(RuntimeError):
    """An answer from one instrument was about to overwrite another's."""


def write_cached(path: Path, record: dict, *, allow_reinstrument: bool = False) -> None:
    """Store one answer, refusing to overwrite an answer from a different judge.

    **This guard exists because the thing it prevents happened.** A scoring run
    started without `--thinking-budget` took the default 256 where the stored
    answers were asked at 2048. `load_cached` correctly rejected all 1 272 of
    them -- a different budget is a different instrument, which is why
    `judge_settings` is one of `results.COMPARABILITY_KEYS` -- so the run re-asked
    every question, and this function then overwrote 943 good answers with
    answers from an instrument nobody wanted. `scores/` is gitignored, so there
    was nothing to restore from; they had to be asked again.

    Re-instrumenting on purpose is a real thing to want and stays possible, but
    it has to be said out loud. Deciding to measure with a new budget starts a
    new table by the project's own rules, and a decision that large should not
    be reachable by leaving a flag off.

    The comparison is on the fingerprint alone. Re-asking the same question of
    the same instrument -- what `--force` does, and what a truncated answer
    causes on the next run -- overwrites freely, because that is the same
    instrument answering again.
    """
    if not allow_reinstrument and path.exists():
        try:
            stored = json.loads(path.read_text(encoding="utf-8")).get("judge_fingerprint")
        except (OSError, json.JSONDecodeError):
            stored = None
        fresh = record.get("judge_fingerprint")
        if stored is not None and fresh is not None and stored != fresh:
            raise Reinstrumented(
                f"{path} holds an answer from a different judge instrument.\n"
                f"  stored: {json.dumps(stored, sort_keys=True)}\n"
                f"  asking: {json.dumps(fresh, sort_keys=True)}\n"
                "A different budget or model is a different instrument and starts a "
                "new table. Re-run with the settings the cache was built at, or pass "
                "--reinstrument to replace it deliberately."
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
