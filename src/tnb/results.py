"""Result rows: the append-only record everything else is rendered from.

One row is one (track, system, version set) — a model's whole standing on one
track, under one harness version, one prompt version and one judge. Rows are
appended to ``results/rows.jsonl`` and never rewritten, because a published
number that changes underneath a reader is worse than no number.

Two rules live here rather than in the renderers, so that no table can quietly
break them:

- **Only rows that agree on every field of** :data:`COMPARABILITY_KEYS` **may
  be compared.** There are six, and the count is written down in one place on
  purpose: it was "four" in three documents for as long as the tuple had five
  entries and then six. Changing the judge -- or the judge's settings -- starts
  a new table beside the old one; see
  ``docs/methodology.md#comparability-over-time`` and :func:`comparable_groups`.
- **A metric is never one number.** Both source papers compute per section, so a
  row carries ``headline`` for the table column, ``by_section`` under it, and a
  third level below that -- the 23 rubric criteria for TN-Eval, the five TRACE
  dimensions for iCARE. Storing only the average would throw away a breakdown
  the scoring pass already produced and cannot be recovered afterwards.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from types import MappingProxyType
from typing import NamedTuple

from tnb import __version__, generation
from tnb.config import REPO_ROOT

RESULTS_DIR = REPO_ROOT / "results"
ROWS_PATH = RESULTS_DIR / "rows.jsonl"

#: Rows that are measured and not published, in a gitignored directory.
#:
#: The Czech tracks read ten real sessions with one client. Their scores carry
#: no text and would be safe to commit, but "safe to commit" and "decided to
#: publish" are different sentences and only Jan gets to write the second one.
#: Keeping them in a different file is what makes the separation structural:
#: `report.write` reads `ROWS_PATH`, so the published page cannot draw a Czech
#: row even by accident, whatever is registered in `report.COLUMNS`.
LOCAL_DIR = REPO_ROOT / "local"
LOCAL_ROWS_PATH = LOCAL_DIR / "czech-rows.jsonl"

#: The two tracks. They measure different things on different scales and are
#: never averaged together -- see docs/methodology.md.
TRACK_TNEVAL = "tneval-soap"
TRACK_ICARE = "icare"
#: The same notes as `TRACK_TNEVAL`, asked a different instrument. It is a track
#: rather than a column set because a track is named for what it measures: the
#: rubric counts what a note covers, PDSQI-9 rates how good it is, and one table
#: holding both would invite a reader to average them.
TRACK_PDSQI = "pdsqi-soap"
#: The Czech tracks. Two, not one: ten real sessions with a single client and
#: ten AnnoMI conversations translated into Czech answer different questions,
#: and the whole design rests on their never being averaged. Two tracks put that
#: beyond the reach of a careless `setdefault`.
TRACK_CZECH_REAL = "czech-real"
TRACK_CZECH_TRANSLATED = "czech-translated"
#: The same Czech notes, asked PDSQI-9 instead. The seven criteria ask whether
#: the Czech is any good; they do not ask whether the note is any good, and a
#: flawless sentence about nothing passes all seven. This is the quality half of
#: the question, and it is separate for the same reason `TRACK_PDSQI` is
#: separate from `TRACK_TNEVAL`.
#:
#: **The two halves are not asked the same number of questions.** `accurate` and
#: `thorough` need the session, and the real sessions never leave e-INFRA, so
#: the real half is asked the six attributes that read the note alone. The
#: translated half is AnnoMI, which is public, so it is asked all eight. Two
#: column sets are two instruments and get two tracks; merging them would put a
#: six-attribute mean beside an eight-attribute one under one heading.
TRACK_CZECH_REAL_PDSQI = "czech-real-pdsqi"
TRACK_CZECH_TRANSLATED_PDSQI = "czech-translated-pdsqi"
#: The same models and the same sessions, asked for the note format the Deepsy
#: application actually writes -- three of its eleven sections, the three that
#: have a SOAP counterpart. The point of the track is the comparison: what
#: changes between this and `czech-real` is the shape the model was asked for
#: and nothing else, so a difference between them is a fact about the format.
TRACK_DEEPSY_REAL = "deepsy-real"
TRACK_DEEPSY_TRANSLATED = "deepsy-translated"

TRACKS = (
    TRACK_TNEVAL,
    TRACK_ICARE,
    TRACK_PDSQI,
    TRACK_CZECH_REAL,
    TRACK_CZECH_TRANSLATED,
    TRACK_CZECH_REAL_PDSQI,
    TRACK_CZECH_TRANSLATED_PDSQI,
    TRACK_DEEPSY_REAL,
    TRACK_DEEPSY_TRANSLATED,
)

#: Tracks whose rows are written to `LOCAL_ROWS_PATH` and never to `ROWS_PATH`.
#: A test asserts the committed file holds none of them.
LOCAL_TRACKS = (
    TRACK_CZECH_REAL,
    TRACK_CZECH_TRANSLATED,
    TRACK_CZECH_REAL_PDSQI,
    TRACK_CZECH_TRANSLATED_PDSQI,
    TRACK_DEEPSY_REAL,
    TRACK_DEEPSY_TRANSLATED,
)

#: Everything else. What `tnb report` draws and what the coverage sweep writes.
PUBLISHED_TRACKS = tuple(track for track in TRACKS if track not in LOCAL_TRACKS)

#: Generation tasks are named for what they produce, tracks for what they
#: measure. One task feeds one track, but the names differ because the TN-Eval
#: track is more than its SOAP prompt once scoring lands.
TRACK_BY_TASK = {
    "soap": TRACK_TNEVAL,
    "icare": TRACK_ICARE,
    # The Czech tasks are named for their tracks. `pdsqi-soap` is deliberately
    # absent: it scores the SOAP notes rather than generating any, so it has no
    # directory here to index.
    "czech-real": TRACK_CZECH_REAL,
    "czech-translated": TRACK_CZECH_TRANSLATED,
    "deepsy-real": TRACK_DEEPSY_REAL,
    "deepsy-translated": TRACK_DEEPSY_TRANSLATED,
}

#: What produced the note this row scores.
#:
#: ``model``           a model discovered on a provider -- the leaderboard proper
#: ``reference-human`` a therapist-written note released by TN-Eval
#: ``reference-model`` a note from a model the source paper ran (Llama 3.1 70B, ...)
#: ``published``       a number printed in a paper, produced by another harness
SYSTEM_TYPES = ("model", "reference-human", "reference-model", "published")

#: Rows written before the harness supported more than one provider named the
#: first type after that provider. results/ is append-only, so the old value is
#: translated on the way in rather than edited on disk.
LEGACY_SYSTEM_TYPES = {"einfra-model": "model"}

#: The fields a row must agree on before it may share a table with another.
#: `track` is included because two tracks are never one ranking.
COMPARABILITY_KEYS = (
    "track",
    "harness_version",
    "prompt_version",
    "judge_model",
    "judge_prompt_version",
    # The judge's settings, not only its name. A run at a different thinking
    # budget is a different instrument and starts its own table, exactly as a
    # different judge does.
    "judge_settings",
)

#: The fields that identify a row. Two rows with the same identity are the same
#: measurement re-run; the later one supersedes the earlier when rendering.
#:
#: `provider` is here and deliberately **not** in COMPARABILITY_KEYS: two
#: providers belong in one table -- comparing them is the point -- but they are
#: never the same row. The same model id on two endpoints can be two different
#: builds, and merging them would hide that behind one name.
#: What makes a row a *different row*. Wider than comparability on purpose: two
#: rows that differ only here still belong in one table, because comparing them
#: is the interesting part -- but they must never be averaged into one line.
#:
#: `effort` is here because the same model asked to think harder is a different
#: system. Measured on `gpt-5.6-terra`: on a rubric question effort changes
#: nothing at all, but on a Likert rating `none` gave a different answer to
#: `low`/`medium`/`high` on two of six questions. A table that folded those
#: together would report one number for two instruments.
IDENTITY_KEYS = (*COMPARABILITY_KEYS, "provider", "system_id", "system_type", "effort")


@dataclass(frozen=True)
class Metrics:
    """A score at three levels of detail.

    ``headline`` is what a table column shows. ``by_section`` is the same
    measures per SOAP section (4) or per iCARE section (17). ``detail`` is the
    level below: TN-Eval's 23 rubric criteria, or TRACE's five dimensions.

    Every level is optional. An empty :class:`Metrics` is a legitimate row --
    it says "generated, not yet scored", which is what makes a coverage table
    publishable before the judge has run.
    """

    headline: dict[str, float] = field(default_factory=dict)
    by_section: dict[str, dict[str, float]] = field(default_factory=dict)
    detail: dict[str, float] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not (self.headline or self.by_section or self.detail)


@dataclass(frozen=True)
class Settings:
    """What a model was actually asked, as opposed to what it was configured with.

    Three things vary across this field and every one of them changes the
    output, so a row that omits them cannot be reproduced or fairly compared:

    - **effort** -- `medium` on the GPT-5.6 family, nothing comparable elsewhere.
    - **temperature** -- 0 everywhere except GPT-5.6, which accepts only 1. The
      value here is the one that was *sent*; `temperature_forced` says whether
      the provider refused ours, which is what makes the caveat on the page
      truthful rather than decorative.
    - **max_tokens** -- 4096, escalating to 16384 for a model that spent its
      whole budget thinking. A truncated note scores as an incomplete one.

    A generating model's own reasoning tokens were recorded here and are not any
    more. The figure was never comparable between models: nothing in this
    benchmark sets a thinking budget for a generating model, so each one used
    its provider's default, and those defaults differ by two orders of magnitude
    -- 1620 for `qwen3.8-27b` against 13 for `gpt-5.6-terra`. A column whose
    values are set by whoever deployed the model, published beside columns this
    benchmark controls, invited a comparison it could not support. Historic rows
    keep the field; `from_dict` drops settings keys it does not know, so
    `results/` stays append-only and is not rewritten.
    """

    effort: str = ""
    temperature: float | None = None
    temperature_forced: bool = False
    max_tokens: int | None = None
    #: How long this model's notes are, as a median over the ones it wrote.
    #: Measured rather than configured, and published as
    #: a column because completeness counts coverage: within every one of the
    #: sixteen systems, under both judges, a longer note scores higher (median
    #: Spearman +0.35 and +0.45). Holding the transcript fixed the effect
    #: survives under `gpt-5.6-terra` and not under `gemini-3.1-pro-preview`, so
    #: the page publishes the length and not the correlation -- the fact a
    #: reader can discount for, rather than a claim that turned out to depend on
    #: which judge is asked.
    note_words: int | None = None

    def is_empty(self) -> bool:
        return self.temperature is None and self.max_tokens is None and not self.effort

    @property
    def summary(self) -> str:
        """One line for the row's detail panel. Empty when nothing is known."""
        parts = []
        if self.effort:
            parts.append(f"effort {self.effort}")
        if self.temperature is not None:
            forced = " (forced by the provider)" if self.temperature_forced else ""
            parts.append(f"temperature {self.temperature:g}{forced}")
        if self.max_tokens:
            parts.append(f"max tokens {self.max_tokens}")
        return ", ".join(parts)


@dataclass(frozen=True)
class Row:
    """One system's standing on one track, under one set of versions."""

    track: str
    system_id: str
    system_type: str
    n_sessions_attempted: int

    system_label: str = ""
    #: Which endpoint served this model. Part of its identity, not a footnote.
    provider: str = ""

    harness_version: str = __version__
    prompt_version: str = ""
    #: None until a judge has run. Part of the comparability key either way: a
    #: coverage row and a scored row are not the same measurement.
    judge_model: str | None = None
    judge_prompt_version: str | None = None
    #: The judge's own settings, as the answer cache fingerprints them. Two
    #: thinking budgets are two instruments -- measured on this benchmark,
    #: raising Gemini's from 128 to 256 moved completeness by +0.017 on every
    #: system and changed the conciseness top three -- and until this was
    #: recorded, `judge_model` alone said they were the same judge and the
    #: leaderboard would have put them in one table.
    judge_settings: dict = field(default_factory=dict)

    #: Sessions with a complete set of usable generations. Lower than
    #: `n_sessions_attempted` when a model would not produce a note -- which is
    #: not the same thing as producing a bad one, so it gets its own column.
    n_sessions_generated: int = 0
    n_sessions_scored: int = 0
    #: Notes the judge touched but did not finish, and which the headline
    #: therefore excludes. Both aggregates computed this and neither could write
    #: it down, so `n_sessions_scored` was published as the headline's
    #: denominator when it is the count of notes the judge *started*.
    n_sessions_partial: int = 0
    n_failed: int = 0
    failure_reasons: dict[str, int] = field(default_factory=dict)
    #: Calls whose missing answer is not the model's doing -- rate limits,
    #: backend errors, timeouts, and our own token ceiling. Separate from
    #: `failure_reasons` because they say nothing about the model and, unlike a
    #: bad note, re-running or raising the ceiling fixes them.
    unreached_reasons: dict[str, int] = field(default_factory=dict)

    #: How the model was asked, taken from the generation records rather than
    #: from what the config requested -- so it says what happened. Part of the
    #: identity via `effort`; the rest is shown in the row's detail.
    #:
    #: A leaderboard row that does not say how the model was configured cannot
    #: be reproduced. This benchmark already applies that rule to
    #: `prompt_version`, `judge_model` and `harness_version`; generation
    #: settings were the gap.
    settings: Settings = field(default_factory=lambda: Settings())

    metrics: Metrics = field(default_factory=Metrics)
    #: Caveats that must travel with the numbers, e.g. that TRACE has no human
    #: anchor. Rendered next to the score, not buried in a footnote nobody reads.
    metrics_note: str = ""
    #: For `published` rows: the paper and table the number was printed in.
    source: str = ""

    dataset_checksums: dict[str, str] = field(default_factory=dict)
    generated_at: str = ""
    scored_at: str | None = None
    run_id: str = ""

    def __post_init__(self) -> None:
        if self.system_type in LEGACY_SYSTEM_TYPES:
            object.__setattr__(self, "system_type", LEGACY_SYSTEM_TYPES[self.system_type])
        if self.track not in TRACKS:
            raise ValueError(f"Unknown track {self.track!r}. Known: {', '.join(TRACKS)}.")
        if self.system_type not in SYSTEM_TYPES:
            raise ValueError(
                f"Unknown system_type {self.system_type!r}. Known: {', '.join(SYSTEM_TYPES)}."
            )
        # Not a refusal, because `results/` is append-only and every historic
        # row has to stay loadable. Repairing here instead means no renderer can
        # reach the old text, whichever way a row was built.
        object.__setattr__(self, "failure_reasons", canonical_reasons(self.failure_reasons))
        object.__setattr__(self, "unreached_reasons", canonical_reasons(self.unreached_reasons))

    @property
    def effort(self) -> str:
        """The reasoning effort this row was generated under, or "" for none.

        Read from `settings` so there is one home for the value, and exposed as
        an attribute because `IDENTITY_KEYS` reads identity fields by name.
        """
        return self.settings.effort

    @property
    def row_id(self) -> str:
        """Stable digest of the identity fields, for superseding and diffing."""
        identity = json.dumps(
            {key: getattr(self, key) for key in IDENTITY_KEYS},
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(identity.encode()).hexdigest()[:16]

    @property
    def label(self) -> str:
        return self.system_label or self.system_id

    @property
    def is_scored(self) -> bool:
        return not self.metrics.is_empty()

    def comparability_key(self) -> tuple:
        # Serialised where a field is a mapping: the key has to be hashable and
        # to order the same way whichever run wrote the row.
        return tuple(
            json.dumps(value, sort_keys=True)
            if isinstance(value := getattr(self, key), dict)
            else value
            for key in COMPARABILITY_KEYS
        )

    def to_dict(self) -> dict:
        return {"row_id": self.row_id, **asdict(self)}


#: Measures that were once stored under another name. `results/` is append-only,
#: so a rename cannot be applied to what is already on disk -- it has to be
#: applied on the way in. Without this, rows written before the rename keep the
#: old key, the view looks the measure up under the new one, and the table
#: prints a dash over a number that is right there in the file.
LEGACY_MEASURE_NAMES = {"likert_faithfulness": "faithfulness"}


def _rename_legacy(values: dict) -> dict:
    """Map any superseded measure name to the one the views read.

    A row that already carries the new name keeps its own value; the legacy key
    is dropped either way, so every row leaves this function with one name per
    measure whatever version wrote it.
    """
    renamed = {}
    for key, value in values.items():
        target = LEGACY_MEASURE_NAMES.get(key, key)
        renamed.setdefault(target, value)
    return renamed


def from_dict(payload: dict) -> Row:
    """Rebuild a row, ignoring the derived fields and any newer unknown ones.

    Unknown keys are dropped rather than refused: `results/` is append-only, so
    a file written by a later version of the harness has to stay readable by an
    earlier one instead of crashing it.
    """
    metrics_raw = payload.get("metrics") or {}
    # Both are rebuilt below from their own nested payloads, so they must not
    # also arrive through the flat spread -- that is two values for one keyword.
    known = {f for f in Row.__dataclass_fields__ if f not in ("metrics", "settings")}
    return Row(
        **{key: value for key, value in payload.items() if key in known},
        settings=Settings(
            **{
                key: value
                for key, value in (payload.get("settings") or {}).items()
                if key in Settings.__dataclass_fields__
            }
        ),
        metrics=Metrics(
            headline=_rename_legacy(metrics_raw.get("headline") or {}),
            by_section={
                section: _rename_legacy(values)
                for section, values in (metrics_raw.get("by_section") or {}).items()
            },
            detail=dict(metrics_raw.get("detail") or {}),
        ),
    )


def append(rows: list[Row], path: Path | None = None) -> Path:
    """Append rows to ``results/rows.jsonl``. Never rewrites, never reorders."""
    path = path or ROWS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
    return path


def unrecorded(candidates: list[Row], existing: list[Row] | None = None) -> list[Row]:
    """The candidates that say something `results/` does not already record.

    `tnb report` re-reads `generations/` on every run, which is right: the page
    used to report iCARE as "3/3" for two days after 7 480 sections had been
    written, because indexing was a second command somebody had to remember.
    Re-reading cannot be stale by construction.

    Appending the result unconditionally is a different thing, and it was
    wrong. Coverage changes only when notes are generated, so a reporting
    command run five times in an afternoon wrote five identical copies of every
    coverage row into a file that is append-only and therefore keeps all of
    them. 96 of them arrived in one afternoon this way, carrying no measurement
    anybody made.

    Compared on the body rather than on `row_id`, which digests the identity
    fields only -- two coverage rows for the same system share it whatever their
    counts say, so it cannot tell "already recorded" from "changed". `run_id` is
    excluded because it is stamped with the day the report ran and would make
    every row look new tomorrow.
    """
    known = load() if existing is None else existing

    def body(row: Row) -> dict:
        return {k: v for k, v in row.to_dict().items() if k not in ("run_id", "row_id")}

    latest: dict[str, dict] = {}
    for row in known:
        latest[row.row_id] = body(row)
    return [row for row in candidates if latest.get(row.row_id) != body(row)]


def load(path: Path | None = None) -> list[Row]:
    """Read every row ever written, oldest first."""
    path = path or ROWS_PATH
    if not path.exists():
        return []
    return [
        from_dict(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def latest(rows: list[Row]) -> list[Row]:
    """Keep the last row written for each identity.

    A re-run supersedes its predecessor in the *rendering*, while both stay in
    the file. That is what append-only buys: the table shows today's number and
    the history is still there to explain it.
    """
    by_identity: dict[str, Row] = {}
    for row in rows:
        by_identity[row.row_id] = row
    return list(by_identity.values())


def comparable_groups(rows: list[Row]) -> dict[tuple, list[Row]]:
    """Split rows into the sets that may share a table.

    Nothing else in this repository decides what may be compared. A renderer
    that iterated over all rows would silently put two judges in one ranking,
    which is the failure mode docs/methodology.md exists to prevent.
    """
    groups: dict[tuple, list[Row]] = defaultdict(list)
    for row in rows:
        groups[row.comparability_key()].append(row)
    return dict(groups)


def scored(rows: list[Row], **overrides) -> list[Row]:
    """Helper for the scoring pass: same rows, now carrying a judge and scores."""
    return [replace(row, **overrides) for row in rows]


# --- coverage rows from the generation cache -------------------------------


# Masking a provider's error by shape used to live here: a hex-run pattern for
# the key hash e-INFRA quotes in a 429, a resource-path pattern for the project
# id Vertex quotes in a 404, and an exact pass over our own configured values.
#
# All three are gone because none is reachable any more, and dead safety
# machinery is worse than none -- it reads as a protection. A provider's body no
# longer reaches `Completion.error` at all (see `openai_compatible.http_reason`),
# so `normalise_reason` recognises a value this repository wrote rather than
# sanitising one somebody else did. What those patterns bought for things shaped
# like credentials now holds for every kind of content, including the prose they
# were never shaped for.


#: Errors that say nothing about the model, because the model never answered.
#:
#: A 429 is e-INFRA's rate limiter; a 5xx is its backend; a timeout is the
#: network. Counting any of them as a failure of the *model* is the same libel
#: as the one `to_rows` already guards against -- glm-5 was published as "39/40,
#: 1 unusable" when what actually happened is that a shared academic endpoint
#: refused a fourth parallel request. Retrying is the fix and it costs one call,
#: so these are reported separately and marked as re-runnable rather than folded
#: into a score.
#:
#: The transport half is derived from `httpx` rather than listed by hand. The
#: hand-written list named twelve and caught six: `ReadError` -- a connection
#: reset part-way through a response, which is what a busy shared endpoint
#: does -- was missing, and `TransportError` was in it as an abstract base
#: that is never raised, so it matched nothing at all. Every error string is
#: `type(error).__name__: ...`, so asking the class hierarchy is exact and
#: stays right when httpx adds one.
_OUR_OWN_FAULT = frozenset(
    {
        # We sent something malformed. Naming that "the endpoint refused"
        # would file our own bug under somebody else's failure.
        "LocalProtocolError",
        # A bad base URL. A config error, and it does not go away on a retry.
        "UnsupportedProtocol",
    }
)


def _transport_errors() -> tuple[str, ...]:
    import httpx

    def walk(cls):
        yield cls.__name__
        for sub in cls.__subclasses__():
            yield from walk(sub)

    return tuple(sorted(set(walk(httpx.TransportError)) - _OUR_OWN_FAULT))


INFRASTRUCTURE_ERRORS = (
    # e-INFRA's rate limiter, its backend, and the gateways in front of both.
    "HTTP408",
    "HTTP425",
    "HTTP429",
    "HTTP500",
    "HTTP502",
    "HTTP503",
    "HTTP504",
) + _transport_errors()


#: What we did to the call, rather than what the model or the endpoint did.
#: A generation that stopped on `length` has already had its one escalation to
#: `escalate_max_tokens`; past that we cut it off, and we do not know what it
#: would have written.
OUR_OWN_LIMITS = ("truncated at max_tokens",)


def is_infrastructure_failure(error: str | None) -> bool:
    """Whether a call failed before the model had any say in it."""
    text = (error or "").strip()
    return any(text.startswith(prefix) for prefix in INFRASTRUCTURE_ERRORS)


def is_our_own_ceiling(error: str | None) -> bool:
    """Whether the harness stopped the call rather than the model failing it."""
    text = (error or "").strip()
    return any(text.startswith(prefix) for prefix in OUR_OWN_LIMITS)


def is_the_models_fault(error: str | None) -> bool:
    """Whether a missing note may be charged to the model.

    The counter it feeds is published as "N unusable" beside a model's name, so
    the question it answers is an accusation and the default has to be no.
    `generation` already argues that a note cut off at our ceiling "would
    measure our token budget, not the model" -- and the counter one column over
    was measuring exactly that. Measured in `generations/`: one call, in
    `qwen3.5-int4`'s iCARE session 146. (An earlier version of this docstring
    said fourteen. `results/` holds fourteen rows that name the truncation and
    each of them counts one call -- the same coverage row, re-appended by
    fourteen `tnb report` runs.)
    """
    return not is_infrastructure_failure(error) and not is_our_own_ceiling(error)


#: The reasons that are neither an HTTP status nor a transport failure: things
#: this harness decided about an answer it did get.
#:
#: `truncated at max_tokens=` keeps its number. The number is a budget we set,
#: not anything a provider wrote, and `OUR_OWN_LIMITS` matches the prefix -- so
#: dropping it would buy nothing and break `is_our_own_ceiling`.
HARNESS_REASONS = (
    "truncated at max_tokens",
    "empty content",
    "answer did not contain a SOAP dictionary",
    # The same failure under a name that fits every task rather than only SOAP.
    # The older phrase stays: results/ is append-only and rows already carry it.
    "answer was not a note",
    "unreadable cache file",
)

#: What an unrecognised failure becomes. It does **not** contain the input:
#: that is the whole difference between a vocabulary and a filter.
UNRECOGNISED = "unrecognised failure"

_HTTP_REASON = re.compile(r"^HTTP(\d{3})")
_TRUNCATED = re.compile(r"^truncated at max_tokens=(\d+)$")


def reason_vocabulary() -> tuple[str, ...]:
    """Every fixed reason a row may carry, for documentation and for tests.

    Not the whole range: `HTTP<code>` and `truncated at max_tokens=<budget>`
    carry a number this repository chose. `normalise_reason` is the authority --
    a string it returns unchanged is in the vocabulary.
    """
    from tnb.providers.openai_compatible import http_reason

    return (
        tuple(http_reason(status) for status in sorted(_HTTP_PHRASES()))
        + _transport_errors()
        + (
            "empty content",
            "answer did not contain a SOAP dictionary",
            "answer was not a note",
            "unreadable cache file",
        )
        + (UNRECOGNISED,)
    )


def _HTTP_PHRASES() -> dict:
    from tnb.providers.openai_compatible import HTTP_PHRASES

    return HTTP_PHRASES


def normalise_reason(error: str | None) -> str:
    """Map a failure onto the closed set of things a committed row may say.

    An allow-list, not a scrubber, and the difference is the point. A scrubber
    has to anticipate every bad shape; this has to recognise every good one, and
    the good ones are finite because `openai_compatible.http_reason` made them
    so. Anything unrecognised becomes `UNRECOGNISED` **without its input**, so
    the range of this function is a compile-time constant.

    Why it changed. The previous version masked three shapes -- our own secret
    values, cloud resource paths, long hex runs -- and its docstring reasoned
    carefully that a secret bisected by the provider's 200-character cut could
    not survive the 120 kept here. That reasoning was correct and it answered
    the wrong question. Masking is shaped for things that look like credentials.
    Request *content* looks like prose, so none of the three passes touched it,
    and three rows in the committed `results/rows.jsonl` carry a verbatim 429
    body from e-INFRA to prove it. The Czech track reads real clinical sessions
    and e-INFRA is LiteLLM-fronted, which echoes an over-long request back in
    the body of its refusal.

    It is also a repairer. `results/` is append-only, so rows already on disk
    keep whatever they were written with; `Row.__post_init__` brings every one
    of them through here on the way in, the same way `LEGACY_SYSTEM_TYPES`
    translates an old system type rather than editing the file. Nothing that
    renders a row can reach the old text.

    Two prefixes are load-bearing and survive deliberately: `HTTP<code>`, which
    `is_infrastructure_failure` reads to keep an endpoint's refusal from being
    charged to the model, and `truncated at max_tokens`, which
    `is_our_own_ceiling` reads for the same reason about our own budget.
    """
    text = " ".join((error or "").split())
    if not text:
        return UNRECOGNISED

    status = _HTTP_REASON.match(text)
    if status:
        from tnb.providers.openai_compatible import http_reason

        return http_reason(int(status.group(1)))

    truncated = _TRUNCATED.match(text)
    if truncated:
        return f"truncated at max_tokens={truncated.group(1)}"

    for reason in HARNESS_REASONS:
        if text == reason or text.startswith(f"{reason}="):
            return text if text == reason else UNRECOGNISED

    for name in _transport_errors():
        if text == name or text.startswith(f"{name}:"):
            return name

    return UNRECOGNISED


def canonical_reasons(reasons: Mapping[str, int] | None) -> dict[str, int]:
    """Every key through `normalise_reason`, with counts merged where two meet.

    Two different 429 bodies are one reason once the body is gone, and their
    counts have to add rather than one of them winning.
    """
    merged: dict[str, int] = {}
    for reason, count in (reasons or {}).items():
        key = normalise_reason(reason)
        merged[key] = merged.get(key, 0) + int(count)
    return merged


def index_generations(
    cache_dir: Path | None = None, *, run_id: str = "", include_local: bool = False
) -> list[Row]:
    """Turn what is in ``generations/`` into one coverage row per model and track.

    These rows carry no metrics. They exist so the leaderboard can be published
    -- and its layout debugged -- before a single judge call is paid for, and so
    that a model which lost sessions to its output format is visible as exactly
    that rather than as a low score.
    """
    cache_dir = cache_dir or generation.CACHE_DIR
    if not cache_dir.exists():
        return []

    rows: list[Row] = []
    for provider_dir in sorted(p for p in cache_dir.iterdir() if p.is_dir()):
        for task_dir in sorted(p for p in provider_dir.iterdir() if p.is_dir()):
            track = TRACK_BY_TASK.get(task_dir.name)
            # The Czech tracks are measured and not published, so their
            # coverage rows belong in `LOCAL_ROWS_PATH` and never here. Skipped
            # rather than filtered afterwards: `cmd_report` appends whatever
            # this returns, and a filter one caller away is a filter somebody
            # forgets.
            #
            # `include_local` is for a caller that wants the reasons rather than
            # the rows -- `unreached_by_system`, which the local scorers need so
            # that a model with no note carries WHY it has none. e-INFRA
            # answered `glm-5.3-flash` with "there are no healthy deployments
            # for this model" sixty times; without this the Deepsy table simply
            # would not have contained it, which reads as "not run".
            if track in LOCAL_TRACKS and not include_local:
                continue
            if track is None:
                continue
            for version_dir in sorted(p for p in task_dir.iterdir() if p.is_dir()):
                for model_dir in sorted(p for p in version_dir.iterdir() if p.is_dir()):
                    row = _coverage_row(
                        track, provider_dir.name, version_dir.name, model_dir, run_id
                    )
                    if row is not None:
                        rows.append(row)
    return rows


class Unreached(NamedTuple):
    """What one system lost to the endpoint rather than to itself."""

    #: Sessions with no usable note because a call was never answered.
    sessions: int
    #: Why, counted per refused call. Sums higher than `sessions` on the iCARE
    #: track, where one session is seventeen separate calls.
    reasons: dict[str, int]

    #: And the other half: what the model itself failed to produce, and why.
    #: Carried here because a scored row needs both and reading them from two
    #: walks of the cache is how the two came to disagree. Without it every
    #: scored row published `n_failed` with `failure_reasons: {}` -- the
    #: accusation with no reason beside it, which is the defect this pair of
    #: fields was introduced to fix, one counter over.
    failed: int = 0
    #: A read-only mapping rather than `{}`: a mutable default on a NamedTuple
    #: is one object shared by every instance that takes it.
    failure_reasons: Mapping[str, int] = MappingProxyType({})


def unreached_by_system(
    track: str, cache_dir: Path | None = None
) -> dict[tuple[str, str], Unreached]:
    """Per system, what never got written -- read from the coverage rows.

    Derived from `index_generations` rather than re-walking the cache, so a
    scored row and a coverage row can never disagree about whose failure a
    missing note was. `_coverage_row` already separates the two; this carries
    that separation into the rows that get published with scores on them.
    """
    found: dict[tuple[str, str], Unreached] = {}
    for row in index_generations(cache_dir, include_local=track in LOCAL_TRACKS):
        if row.track != track:
            continue
        sessions = row.n_sessions_attempted - row.n_sessions_generated - row.n_failed
        if sessions or row.unreached_reasons or row.n_failed or row.failure_reasons:
            found[(row.provider, row.system_id)] = Unreached(
                sessions, row.unreached_reasons, row.n_failed, row.failure_reasons
            )
    return found


def settings_by_system(
    cache_dir: Path | None = None, track: str | None = None
) -> dict[tuple[str, str], Settings]:
    """How each (provider, system) was generated on one track, from the records.

    The scored rows need this as much as the coverage rows do, and reading it
    from one place means a scored row and a coverage row for the same model can
    never disagree about how it was asked.

    **`track` is not optional in practice.** The key is (provider, system_id),
    which is right for `temperature` and `effort` -- a model is configured per
    provider -- and wrong for the other two fields the block carries.
    `note_words` is *measured* from that track's notes, and `max_tokens`
    records whether the escalation to 16384 fired on that track. Both differ
    between a model's SOAP run and its iCARE run, and not because of the
    harness.

    Without the filter this walked both tracks into one mapping and let the
    later write win. `index_generations` visits task directories in sorted
    order, `icare` sorts before `soap`, so **every iCARE row published the SOAP
    track's reasoning figure** -- `google_gemini-3.7-flash` shown as 687 tokens
    where its iCARE notes averaged 390, `gpt-5.6-terra` as 13 where iCARE was
    41, ten of ten rows wrong -- and four rows printed "max tokens 4096" for
    notes written under a 16384 ceiling.

    `None` keeps the old behaviour and is kept only for a caller that genuinely
    wants every track at once. Nothing in this repository does.
    """
    return {
        (row.provider, row.system_id): row.settings
        for row in index_generations(cache_dir)
        if not row.settings.is_empty() and (track is None or row.track == track)
    }


def _settings_from(
    observed: set[tuple],
    budgets: set[int],
    words: list[int] | None = None,
) -> Settings:
    """One `Settings` for a model's notes, or nothing if they disagree.

    A model whose notes were written under two different settings has no single
    answer, and inventing one -- picking the first, or the most common -- would
    put a number on the page that describes only some of the notes behind it.
    Better to say nothing, which the row's detail renders as "not recorded",
    than to say something that is true of half the evidence.

    In practice this stays empty only for a cache written before these fields
    existed. The escalation budget is the expected reason for two `max_tokens`,
    so the *largest* is reported: it is the ceiling the model was allowed, which
    is what a reader needs in order to know whether a note could be truncated.
    """
    # Median, not mean: one note that repeats the transcript back is real and
    # should not move the figure a reader compares across models.
    length = round(statistics.median(words)) if words else None
    if len(observed) != 1:
        return Settings(note_words=length)
    effort, temperature, forced = next(iter(observed))
    return Settings(
        effort=effort or "",
        temperature=temperature,
        temperature_forced=forced,
        max_tokens=max(budgets) if budgets else None,
        note_words=length,
    )


def _coverage_row(
    track: str, provider: str, prompt_version: str, model_dir: Path, run_id: str
) -> Row | None:
    sessions = sorted(p for p in model_dir.iterdir() if p.is_dir())
    if not sessions:
        return None

    complete = 0
    failures: dict[str, int] = defaultdict(int)
    # Kept apart from `failures` on purpose: one is about the model, the other
    # about the endpoint, and a reader comparing scores needs to know which.
    unreached: dict[str, int] = defaultdict(int)
    checksums: dict[str, str] = {}
    newest = ""
    # Read from the records rather than from today's `models.yaml`: the row must
    # say how the note was written, not how the config would write it now.
    observed: set[tuple] = set()
    budgets: set[int] = set()
    words: list[int] = []
    unreached_sessions = 0

    for session_dir in sessions:
        units = sorted(session_dir.glob("*.json"))
        session_ok = bool(units)
        session_unreached = False
        for unit_path in units:
            try:
                record = json.loads(unit_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                failures["unreadable cache file"] += 1
                session_ok = False
                continue
            if record.get("ok"):
                checksums = checksums or dict(record.get("dataset_checksums") or {})
                newest = max(newest, record.get("generated_at") or "")
                observed.add(
                    (
                        record.get("effort", ""),
                        record.get("temperature"),
                        bool(record.get("temperature_forced")),
                    )
                )
                if record.get("max_tokens"):
                    budgets.add(int(record["max_tokens"]))
                # The note itself, not the reply that carried it: `text` holds
                # the model's whole answer including any scaffolding it wrote
                # around the note, and the rubric only ever sees the note.
                note = record.get("note")
                if isinstance(note, dict):
                    words.append(len(" ".join(str(v) for v in note.values()).split()))
                elif isinstance(note, str) and note:
                    words.append(len(note.split()))
            elif not is_the_models_fault(record.get("error")):
                # Counted apart and NOT charged to the model. Splitting the
                # reasons without splitting the count left glm-5 published as
                # "39/40 (1 unusable)" over a rate limit -- the reason sat in
                # the unreached panel while the count still said the model
                # failed, and the README printed the accusation with no reason
                # at all beside it.
                unreached[normalise_reason(record.get("error"))] += 1
                session_ok = False
                session_unreached = True
            else:
                failures[normalise_reason(record.get("error"))] += 1
                session_ok = False
        complete += session_ok
        # Not generated -- there is no usable note -- but not the model's doing
        # either, so it leaves `n_failed` below rather than joining it.
        unreached_sessions += session_unreached

    return Row(
        track=track,
        system_id=model_dir.name,
        system_type="model",
        provider=provider,
        prompt_version=prompt_version,
        settings=_settings_from(observed, budgets, words),
        n_sessions_attempted=len(sessions),
        n_sessions_generated=complete,
        # What the *model* failed to produce. A call the endpoint never
        # answered is in `unreached_reasons` and is nobody's failure.
        n_failed=len(sessions) - complete - unreached_sessions,
        failure_reasons=dict(sorted(failures.items())),
        unreached_reasons=dict(sorted(unreached.items())),
        dataset_checksums=checksums,
        generated_at=newest,
        run_id=run_id,
    )
