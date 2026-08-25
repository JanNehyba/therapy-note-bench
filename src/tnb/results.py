"""Result rows: the append-only record everything else is rendered from.

One row is one (track, system, version set) — a model's whole standing on one
track, under one harness version, one prompt version and one judge. Rows are
appended to ``results/rows.jsonl`` and never rewritten, because a published
number that changes underneath a reader is worse than no number.

Two rules live here rather than in the renderers, so that no table can quietly
break them:

- **Only rows that agree on all four version fields may be compared.** Changing
  the judge starts a new table beside the old one; see
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
from collections import defaultdict
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import NamedTuple

from tnb import __version__, generation
from tnb.config import REPO_ROOT

RESULTS_DIR = REPO_ROOT / "results"
ROWS_PATH = RESULTS_DIR / "rows.jsonl"

#: The two tracks. They measure different things on different scales and are
#: never averaged together -- see docs/methodology.md.
TRACK_TNEVAL = "tneval-soap"
TRACK_ICARE = "icare"
TRACKS = (TRACK_TNEVAL, TRACK_ICARE)

#: Generation tasks are named for what they produce, tracks for what they
#: measure. One task feeds one track, but the names differ because the TN-Eval
#: track is more than its SOAP prompt once scoring lands.
TRACK_BY_TASK = {"soap": TRACK_TNEVAL, "icare": TRACK_ICARE}

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
    """

    effort: str = ""
    temperature: float | None = None
    temperature_forced: bool = False
    max_tokens: int | None = None

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
    #: Calls that never reached the model -- rate limits, backend errors,
    #: timeouts. Separate from `failure_reasons` because they say nothing about
    #: the model and, unlike a bad note, re-running fixes them.
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
        return tuple(getattr(self, key) for key in COMPARABILITY_KEYS)

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


#: Long hex runs in a provider's error body -- e-INFRA's 429 quotes a hash of
#: the API key that hit the limit. results/ is committed and published, so the
#: reason is kept and the identifier is not.
_SECRET_LOOKING = re.compile(r"[0-9a-f]{16,}", re.IGNORECASE)


#: Errors that say nothing about the model, because the model never answered.
#:
#: A 429 is e-INFRA's rate limiter; a 5xx is its backend; a timeout is the
#: network. Counting any of them as a failure of the *model* is the same libel
#: as the one `to_rows` already guards against -- glm-5 was published as "39/40,
#: 1 unusable" when what actually happened is that a shared academic endpoint
#: refused a fourth parallel request. Retrying is the fix and it costs one call,
#: so these are reported separately and marked as re-runnable rather than folded
#: into a score.
INFRASTRUCTURE_ERRORS = (
    "HTTP408",
    "HTTP425",
    "HTTP429",
    "HTTP500",
    "HTTP502",
    "HTTP503",
    "HTTP504",
    "ConnectTimeout",
    "ReadTimeout",
    "ConnectError",
    "RemoteProtocolError",
    "TransportError",
    "PoolTimeout",
)


def is_infrastructure_failure(error: str | None) -> bool:
    """Whether a call failed before the model had any say in it."""
    text = (error or "").strip()
    return any(text.startswith(prefix) for prefix in INFRASTRUCTURE_ERRORS)


def normalise_reason(error: str | None) -> str:
    """Turn a provider's error into something safe and countable.

    Raw bodies carry request ids, key hashes and resets timestamps, which makes
    every failure look unique and puts identifiers in a public file. This keeps
    the part that explains the failure and drops the part that identifies the
    caller.
    """
    text = (error or "unknown error").strip()
    text = _SECRET_LOOKING.sub("...", text)
    text = " ".join(text.split())
    return text[:120]


def index_generations(cache_dir: Path | None = None, *, run_id: str = "") -> list[Row]:
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


def unreached_by_system(
    track: str, cache_dir: Path | None = None
) -> dict[tuple[str, str], Unreached]:
    """Per system, what the endpoint refused -- read from the coverage rows.

    Derived from `index_generations` rather than re-walking the cache, so a
    scored row and a coverage row can never disagree about whose failure a
    missing note was. `_coverage_row` already separates the two; this carries
    that separation into the rows that get published with scores on them.
    """
    found: dict[tuple[str, str], Unreached] = {}
    for row in index_generations(cache_dir):
        if row.track != track:
            continue
        sessions = row.n_sessions_attempted - row.n_sessions_generated - row.n_failed
        if sessions or row.unreached_reasons:
            found[(row.provider, row.system_id)] = Unreached(sessions, row.unreached_reasons)
    return found


def settings_by_system(cache_dir: Path | None = None) -> dict[tuple[str, str], Settings]:
    """How each (provider, system) was generated, from the records on disk.

    The scored rows need this as much as the coverage rows do, and reading it
    from one place means a scored row and a coverage row for the same model can
    never disagree about how it was asked.

    Keyed on (provider, system_id) rather than including the task: a model is
    configured per provider, not per track, and a settings block that differed
    between a model's SOAP row and its iCARE row would be describing the
    harness rather than the model.
    """
    return {
        (row.provider, row.system_id): row.settings
        for row in index_generations(cache_dir)
        if not row.settings.is_empty()
    }


def _settings_from(observed: set[tuple], budgets: set[int]) -> Settings:
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
    if len(observed) != 1:
        return Settings()
    effort, temperature, forced = next(iter(observed))
    return Settings(
        effort=effort or "",
        temperature=temperature,
        temperature_forced=forced,
        max_tokens=max(budgets) if budgets else None,
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
            elif is_infrastructure_failure(record.get("error")):
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
        settings=_settings_from(observed, budgets),
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
