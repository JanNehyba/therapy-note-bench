"""Running the iCARE scorer over what the models generated.

The TN-Eval equivalent is :mod:`tnb.scoring.run`, and this deliberately does not
extend it. That module is hard-wired to SOAP in two places -- it reads only
``generations/*/soap/`` and it stamps ``track=TRACK_TNEVAL`` on every row it
builds -- and the two tracks differ in more than a directory name:

- a SOAP candidate is one note, an iCARE candidate is 17 section files that have
  to be assembled into the one labelled string the expert note is written as;
- SOAP asks 54 questions per note, iCARE asks 5;
- SOAP is reference-free, iCARE compares against an expert note, so a session
  whose gold note is missing cannot be scored at all rather than merely scoring
  badly.

What *is* shared is everything that costs money or correctness: the judge
client, the answer cache, the spend ceiling and the retry policy all come from
:mod:`tnb.judge`, and the aggregation rules come from
:mod:`tnb.scoring.icare`.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from tnb import generation, judge, results
from tnb.datasets import ihope
from tnb.datasets.base import Session, checksums
from tnb.results import Metrics, Row
from tnb.scoring import icare as scorer
from tnb.tasks import icare

#: Minimum answered dimensions before a note is published from cache. All five
#: or nothing: with only five questions there is no meaningful partial credit,
#: and `scorer.aggregate` refuses to average a subset anyway.
REQUIRED_DIMENSIONS = len(scorer.TRACE_DIMENSIONS)


@dataclass(frozen=True)
class Candidate:
    """One assembled note to be scored, and where to file its scores."""

    provider: str
    system_id: str
    system_type: str
    system_label: str
    session_id: str
    note: str
    reference: str
    conversation: str


@dataclass
class NoteResult:
    candidate: Candidate
    scores: scorer.Scores
    cached: int = 0


@dataclass
class SystemAggregate:
    """Every note one system wrote, averaged into the row the table shows."""

    notes: list[NoteResult] = field(default_factory=list)

    @property
    def complete(self) -> list[NoteResult]:
        """Notes the judge answered in full. The headline averages these only."""
        return [note for note in self.notes if note.scores.is_complete]

    @property
    def n_partial(self) -> int:
        return len(self.notes) - len(self.complete)

    def metrics(self) -> Metrics:
        usable = self.complete
        headline = _mean_of_dicts([note.scores.headline for note in usable])
        detail = _mean_of_dicts([note.scores.by_criterion for note in self.notes])
        return Metrics(
            headline=headline,
            by_section={"trace": detail} if detail else {},
            detail=detail,
        )


def _mean_of_dicts(dicts: list[dict[str, float]]) -> dict[str, float]:
    totals: dict[str, list[float]] = {}
    for entry in dicts:
        for key, value in entry.items():
            totals.setdefault(key, []).append(value)
    return {key: round(sum(values) / len(values), 4) for key, values in totals.items()}


def render_conversation(session: Session) -> str:
    """The transcript, in the rendering the generation prompts already use."""
    return icare.render_dialog(session)


def from_generations(
    sessions: list[Session], *, cache_dir: Path | None = None
) -> Iterator[Candidate]:
    """Every iCARE note our models produced, assembled from its 17 sections.

    A session whose expert note is missing is skipped rather than scored: every
    measure on this track compares against that note, so there is nothing to
    compare to. A section file that failed to generate is rendered as "Nil",
    which is the same thing a model saying nothing would produce -- the
    generation coverage row is where a failure is reported, not here.
    """
    cache_dir = cache_dir or generation.CACHE_DIR
    by_id = {session.id: session for session in sessions}
    if not cache_dir.exists():
        return

    for provider_dir in sorted(p for p in cache_dir.iterdir() if p.is_dir()):
        task_dir = provider_dir / icare.NAME / icare.PROMPT_VERSION
        if not task_dir.exists():
            continue
        for model_dir in sorted(p for p in task_dir.iterdir() if p.is_dir()):
            for session_dir in sorted(p for p in model_dir.iterdir() if p.is_dir()):
                session = by_id.get(session_dir.name)
                if session is None or not (session.reference or "").strip():
                    continue

                sections: dict[str, str] = {}
                for unit_path in session_dir.glob("*.json"):
                    try:
                        record = json.loads(unit_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        continue
                    if record.get("ok"):
                        sections[unit_path.stem] = record.get("text", "")
                if not sections:
                    continue

                yield Candidate(
                    provider=provider_dir.name,
                    system_id=model_dir.name,
                    system_type="model",
                    system_label=model_dir.name,
                    session_id=session_dir.name,
                    note=scorer.render_note(sections),
                    reference=session.reference,
                    conversation=render_conversation(session),
                )


def score_note(
    candidate: Candidate,
    client: judge.Judge,
    spend: judge.Spend,
    *,
    force: bool = False,
    cache_root: Path | None = None,
    bert: float | None = None,
) -> NoteResult:
    """Ask the five TRACE questions about one note, reusing cached answers."""
    tasks = scorer.build_trace_tasks(candidate.note, candidate.conversation)
    fingerprint = client.config.fingerprint()
    answers: dict[str, str] = {}
    cached = 0

    for task in tasks:
        path = judge.cache_path(
            client.config.model,
            scorer.JUDGE_PROMPT_VERSION,
            candidate.provider,
            candidate.system_id,
            candidate.session_id,
            task.unit,
            root=cache_root,
        )
        if not force:
            record = judge.load_cached(path, fingerprint)
            if record is not None:
                answers[task.unit] = record["answer"]
                cached += 1
                continue

        if spend.would_exceed(client.config.model, client.count_tokens(task.prompt)):
            raise BudgetExceeded(client.config.model, spend)

        answer = client.ask(task.prompt)
        spend.record(client.config.model, answer)
        if not answer.ok:
            continue
        answers[task.unit] = answer.text
        judge.write_cached(
            path,
            {
                "answer": answer.text,
                "ok": True,
                "judge_fingerprint": fingerprint,
                "unit": task.unit,
                "input_tokens": answer.input_tokens,
                "output_tokens": answer.output_tokens,
                "thinking_tokens": answer.thinking_tokens,
            },
        )

    return NoteResult(
        candidate=candidate,
        scores=scorer.aggregate(candidate.note, candidate.reference, answers, bert=bert),
        cached=cached,
    )


class BudgetExceeded(RuntimeError):
    """The spending ceiling would be crossed by the next call."""

    def __init__(self, model: str, spend: judge.Spend) -> None:
        total = spend.usd(model)
        super().__init__(
            f"Stopping: the next judge call would cross --max-judge-usd. "
            f"Spent so far: {'unknown' if total is None else f'${total:.2f}'} "
            f"over {spend.calls} call(s). Answers already cached are kept."
        )


def load_sessions(limit: int | None = None) -> list[Session]:
    """The 40 held-out iHOPE sessions the models wrote notes for."""
    return ihope.load("test", limit=limit)


def to_rows(
    scored: list[NoteResult],
    *,
    judge_model: str,
    n_generated: dict[tuple[str, str], int] | None = None,
    n_attempted: dict[tuple[str, str], int] | int | None = None,
    settings: dict[tuple[str, str], results.Settings] | None = None,
    run_id: str = "",
) -> list[Row]:
    """One row per (provider, system), on the iCARE track.

    The three counts mean the same as they do on the TN-Eval track and are kept
    just as separate: attempted is the corpus, generated is what the model
    produced that the protocol could read, scored is what the judge has
    finished. Conflating them is what once published a model as "17/50 (33
    unusable)" for notes it had written perfectly.
    """
    import datetime as dt

    from tnb import __version__

    groups: dict[tuple[str, str], SystemAggregate] = {}
    labels: dict[tuple[str, str], Candidate] = {}
    for note in scored:
        key = (note.candidate.provider, note.candidate.system_id)
        groups.setdefault(key, SystemAggregate()).notes.append(note)
        labels[key] = note.candidate

    now = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for key, aggregate in sorted(groups.items()):
        candidate = labels[key]
        generated = (n_generated or {}).get(key, len(aggregate.notes))
        if isinstance(n_attempted, dict):
            attempted = n_attempted.get(key, generated)
        else:
            attempted = n_attempted or generated

        rows.append(
            Row(
                track=results.TRACK_ICARE,
                system_id=candidate.system_id,
                system_type=candidate.system_type,
                system_label=candidate.system_label,
                provider=candidate.provider,
                settings=(settings or {}).get(key, results.Settings()),
                harness_version=__version__,
                prompt_version=icare.PROMPT_VERSION,
                judge_model=judge_model,
                judge_prompt_version=scorer.JUDGE_PROMPT_VERSION,
                n_sessions_attempted=attempted,
                n_sessions_generated=generated,
                n_sessions_scored=len(aggregate.notes),
                n_failed=max(0, attempted - generated),
                metrics=aggregate.metrics(),
                metrics_note=(
                    "TRACE is a re-implementation with no human anchor -- the authors "
                    "never published their ratings. See docs/limitations.md"
                ),
                dataset_checksums=checksums(),
                scored_at=now,
                run_id=run_id,
            )
        )
    return rows
