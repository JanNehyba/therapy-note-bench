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
IDENTITY_KEYS = (*COMPARABILITY_KEYS, "provider", "system_id", "system_type")


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
    n_failed: int = 0
    failure_reasons: dict[str, int] = field(default_factory=dict)

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
    known = {f for f in Row.__dataclass_fields__ if f != "metrics"}
    return Row(
        **{key: value for key, value in payload.items() if key in known},
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


def _coverage_row(
    track: str, provider: str, prompt_version: str, model_dir: Path, run_id: str
) -> Row | None:
    sessions = sorted(p for p in model_dir.iterdir() if p.is_dir())
    if not sessions:
        return None

    complete = 0
    failures: dict[str, int] = defaultdict(int)
    checksums: dict[str, str] = {}
    newest = ""

    for session_dir in sessions:
        units = sorted(session_dir.glob("*.json"))
        session_ok = bool(units)
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
            else:
                failures[normalise_reason(record.get("error"))] += 1
                session_ok = False
        complete += session_ok

    return Row(
        track=track,
        system_id=model_dir.name,
        system_type="model",
        provider=provider,
        prompt_version=prompt_version,
        n_sessions_attempted=len(sessions),
        n_sessions_generated=complete,
        n_failed=len(sessions) - complete,
        failure_reasons=dict(sorted(failures.items())),
        dataset_checksums=checksums,
        generated_at=newest,
        run_id=run_id,
    )
