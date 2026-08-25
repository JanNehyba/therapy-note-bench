"""Running the judge over notes, and turning its answers into result rows.

Three kinds of note are scored by exactly the same protocol, which is the point
of a reference-free rubric:

- what our models wrote, read from the generation cache;
- the therapist-written note TN-Eval released for each conversation;
- the two 2024/2025 models they ran (Llama 3.1 70B, Mistral Large V2).

The last two are why the leaderboard can say what a *person* scores on its own
scale, and they are the same 150 notes the calibration in phase 4 uses. Scoring
them is not a detour.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from tnb import __version__, generation, judge, results
from tnb.datasets import tneval as tneval_data
from tnb.datasets.base import Session, checksums
from tnb.results import Metrics, Row
from tnb.scoring import tneval
from tnb.tasks import soap

#: TN-Eval's released model notes, keyed as their data files key them. These
#: are 2024/2025 models the paper ran; scoring them puts a dated anchor in the
#: table next to today's models.
REFERENCE_MODELS = {
    "llm_llama31_70B": ("llama-3.1-70b", "llama-3.1-70b (TN-Eval, 2025)"),
    "llm_mistral_large_v2": ("mistral-large-v2", "mistral-large-v2 (TN-Eval, 2025)"),
}


@dataclass(frozen=True)
class Candidate:
    """One note to be scored, and everything needed to file its scores."""

    provider: str
    system_id: str
    system_type: str
    system_label: str
    session_id: str
    note: dict[str, str]
    conversation: str


def _conversation(session: Session) -> str:
    """The transcript the Likert prompts embed, in TN-Eval's own rendering."""
    return soap.render_transcript(session)


def from_generations(sessions: list[Session], *, cache_dir=None) -> Iterator[Candidate]:
    """Every SOAP note our models produced, straight from the generation cache."""
    cache_dir = cache_dir or generation.CACHE_DIR
    by_id = {session.id: session for session in sessions}

    for provider_dir in sorted(p for p in cache_dir.iterdir() if p.is_dir()):
        task_dir = provider_dir / soap.NAME / soap.PROMPT_VERSION
        if not task_dir.exists():
            continue
        for model_dir in sorted(p for p in task_dir.iterdir() if p.is_dir()):
            for session_dir in sorted(p for p in model_dir.iterdir() if p.is_dir()):
                if session_dir.name not in by_id:
                    continue
                record_path = session_dir / "note.json"
                if not record_path.exists():
                    continue
                record = json.loads(record_path.read_text(encoding="utf-8"))
                if not record.get("ok") or not record.get("note"):
                    continue
                yield Candidate(
                    provider=provider_dir.name,
                    system_id=model_dir.name,
                    system_type="model",
                    system_label=model_dir.name,
                    session_id=session_dir.name,
                    note=record["note"],
                    conversation=_conversation(by_id[session_dir.name]),
                )


def from_reference(sessions: list[Session]) -> Iterator[Candidate]:
    """The therapist's note and the two models TN-Eval released, per conversation.

    Scored by the same judge, the same prompts and the same protocol as ours —
    that is the only way the human row means anything next to the model rows.
    """
    for session in sessions:
        conversation = _conversation(session)
        yield Candidate(
            provider="tneval",
            system_id="therapist",
            system_type="reference-human",
            system_label="therapist-written (TN-Eval)",
            session_id=session.id,
            note=session.meta["human_note"],
            conversation=conversation,
        )
        for key, (system_id, label) in REFERENCE_MODELS.items():
            note = (session.meta.get("model_notes") or {}).get(key, {}).get("note")
            if not note:
                continue
            yield Candidate(
                provider="tneval",
                system_id=system_id,
                system_type="reference-model",
                system_label=label,
                session_id=session.id,
                note=note,
                conversation=conversation,
            )


@dataclass
class NoteResult:
    candidate: Candidate
    scores: tneval.Scores
    asked: int = 0
    cached: int = 0
    failed: int = 0


@dataclass
class BudgetExceeded(RuntimeError):
    """Raised instead of spending past ``--max-judge-usd``."""

    spent: float
    limit: float

    def __str__(self) -> str:
        return (
            f"Judge spend would exceed the ceiling: ${self.spent:.2f} of ${self.limit:.2f} "
            "already committed. Raise --max-judge-usd or score fewer notes."
        )


def score_note(
    candidate: Candidate,
    client: judge.Judge,
    spend: judge.Spend,
    *,
    force: bool = False,
    cache_root=None,
    on_answer=None,
) -> NoteResult:
    """Ask every question one note needs, reusing whatever was asked before."""
    fingerprint = client.config.fingerprint()
    answers: dict[str, str] = {}
    result = NoteResult(candidate=candidate, scores=tneval.Scores())

    tasks = tneval.build_tasks(candidate.note, candidate.conversation)
    for task in tasks:
        path = judge.cache_path(
            client.config.model,
            tneval.JUDGE_PROMPT_VERSION,
            candidate.provider,
            candidate.system_id,
            candidate.session_id,
            task.unit,
            root=cache_root,
        )

        record = None if force else judge.load_cached(path, fingerprint)
        if record is not None:
            answers[task.unit] = record["answer"]
            result.cached += 1
            continue

        if spend.would_exceed(client.config.model, len(task.prompt) // 4):
            raise BudgetExceeded(spend.usd(client.config.model), spend.limit_usd)

        answer = client.ask(task.prompt)
        spend.record(client.config.model, answer)
        result.asked += 1

        judge.write_cached(
            path,
            {
                "judge_model": client.config.model,
                "judge_prompt_version": tneval.JUDGE_PROMPT_VERSION,
                "judge_fingerprint": fingerprint,
                "provider": candidate.provider,
                "system_id": candidate.system_id,
                "session_id": candidate.session_id,
                "unit": task.unit,
                "kind": task.kind,
                "section": task.section,
                "prompt_chars": len(task.prompt),
                "answer": answer.text,
                "ok": answer.ok,
                "error": answer.error,
                "input_tokens": answer.input_tokens,
                "output_tokens": answer.output_tokens,
                "thinking_tokens": answer.thinking_tokens,
                "latency_s": round(answer.latency_s, 3),
                "scored_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )

        if answer.ok:
            answers[task.unit] = answer.text
        else:
            result.failed += 1

        if on_answer is not None:
            on_answer(task, answer)

    result.scores = tneval.aggregate(answers, tasks)
    return result


def from_cache(
    candidates: list[Candidate],
    client: judge.Judge,
    *,
    cache_root=None,
    min_answers: int = 20,
) -> list[NoteResult]:
    """Score every note whose answers are already on disk, asking nothing.

    A scoring run over 542 notes takes hours, and holding every number back
    until the last one lands means the page says "not yet scored" about work
    that finished long ago. This publishes what is measured, whenever it is
    asked, and a note whose questions are still being answered is left out
    rather than averaged over the handful that came back.
    """
    fingerprint = client.config.fingerprint()
    scored: list[NoteResult] = []

    for candidate in candidates:
        answers: dict[str, str] = {}
        tasks = tneval.build_tasks(candidate.note, candidate.conversation)
        for task in tasks:
            record = judge.load_cached(
                judge.cache_path(
                    client.config.model,
                    tneval.JUDGE_PROMPT_VERSION,
                    candidate.provider,
                    candidate.system_id,
                    candidate.session_id,
                    task.unit,
                    root=cache_root,
                ),
                fingerprint,
            )
            if record is not None:
                answers[task.unit] = record["answer"]

        # A note answered only in part would score low for want of questions,
        # not for want of content.
        if len(answers) < max(min_answers, len(tasks) * 0.9):
            continue

        scored.append(
            NoteResult(
                candidate=candidate,
                scores=tneval.aggregate(answers, tasks),
                cached=len(answers),
            )
        )
    return scored


def score_many(
    candidates: list[Candidate],
    client: judge.Judge,
    spend: judge.Spend,
    *,
    force: bool = False,
    cache_root=None,
    on_note=None,
) -> list[NoteResult]:
    """Score notes concurrently. Vertex tolerates more parallelism than e-INFRA.

    A budget stop cancels the rest rather than finishing the batch: the ceiling
    is a ceiling.
    """
    scored: list[NoteResult] = []
    stopped: BudgetExceeded | None = None

    def work(candidate: Candidate) -> NoteResult | None:
        if stopped is not None:
            return None
        return score_note(candidate, client, spend, force=force, cache_root=cache_root)

    with ThreadPoolExecutor(max_workers=max(1, client.config.concurrency)) as pool:
        for future in [pool.submit(work, candidate) for candidate in candidates]:
            try:
                result = future.result()
            except BudgetExceeded as error:
                stopped = error
                continue
            if result is None:
                continue
            scored.append(result)
            if on_note is not None:
                on_note(result)

    if stopped is not None and not scored:
        raise stopped
    return scored


# --- rows --------------------------------------------------------------------


@dataclass
class SystemAggregate:
    """Every note one system wrote, averaged into the row the table shows."""

    notes: list[NoteResult] = field(default_factory=list)

    @property
    def complete(self) -> list[NoteResult]:
        """Notes the judge answered in full.

        The headline averages these and nothing else. A note scored over three
        of four sections is a different measurement from one scored over four,
        and mixing them produces a figure whose denominator varies per model --
        with the variation driven by which judge calls happened to fail, which
        is not a property of the note.
        """
        return [note for note in self.notes if note.scores.is_complete]

    @property
    def n_partial(self) -> int:
        """Notes left out of the headline because the judging is incomplete."""
        return len(self.notes) - len(self.complete)

    def metrics(self) -> Metrics:
        usable = self.complete
        headline = _mean_of_dicts([note.scores.headline for note in usable])
        # Sections keep every note that has them: a section the judge finished
        # is a real measurement even when a sibling section failed, and dropping
        # it would lose detail the headline is right to exclude.
        by_section = {
            section: _mean_of_dicts(
                [
                    note.scores.by_section[section]
                    for note in self.notes
                    if section in note.scores.by_section
                ]
            )
            for section in tneval.SOAP_SECTIONS
        }
        detail = _mean_of_dicts([note.scores.by_criterion for note in self.notes])
        return Metrics(
            headline=headline,
            by_section={k: v for k, v in by_section.items() if v},
            detail=detail,
        )


def _mean_of_dicts(dicts: list[dict[str, float]]) -> dict[str, float]:
    totals: dict[str, list[float]] = {}
    for entry in dicts:
        for key, value in entry.items():
            totals.setdefault(key, []).append(value)
    return {key: round(sum(values) / len(values), 4) for key, values in totals.items()}


def to_rows(
    scored: list[NoteResult],
    *,
    judge_model: str,
    n_generated: dict[tuple[str, str], int] | None = None,
    n_attempted: dict[tuple[str, str], int] | int | None = None,
    settings: dict[tuple[str, str], results.Settings] | None = None,
    run_id: str = "",
) -> list[Row]:
    """One row per (provider, system), carrying the versions the table joins on.

    Three counts, three meanings, kept apart because conflating them libels a
    model. ``n_sessions_attempted`` is the corpus. ``n_sessions_generated`` is
    how many notes the model wrote that the protocol could read.
    ``n_sessions_scored`` is how many of those the judge has finished, which
    moves while a scoring run is in progress. ``n_failed`` counts generation
    failures only.

    The version this replaces set generated to the number *scored* and failed to
    the remainder, so a model half-way through judging was published as having
    written unusable notes -- gemma4 appeared as "17/50 (33 unusable)" having
    written all fifty perfectly.

    ``settings`` says how each system's notes were written -- effort,
    temperature, token budget -- read from the generation records rather than
    from the config, so the row states what happened. A system with no entry
    gets an empty block, which the page renders as "not recorded" rather than
    as a claim.

    ``n_attempted`` may be one number for every system or a mapping per system.
    The mapping exists because "the corpus" is not the same for everybody: a
    reference model was only ever asked for the sessions TN-Eval published a
    note for, and charging it with the rest is the same libel by another route.
    """
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
                track=results.TRACK_TNEVAL,
                system_id=candidate.system_id,
                system_type=candidate.system_type,
                system_label=candidate.system_label,
                provider=candidate.provider,
                harness_version=__version__,
                prompt_version=soap.PROMPT_VERSION,
                judge_model=judge_model,
                judge_prompt_version=tneval.JUDGE_PROMPT_VERSION,
                settings=(settings or {}).get(key, results.Settings()),
                n_sessions_attempted=attempted,
                n_sessions_generated=generated,
                n_sessions_scored=len(aggregate.notes),
                n_failed=max(0, attempted - generated),
                metrics=aggregate.metrics(),
                metrics_note=(
                    "faithfulness is a Likert rating; TN-Eval measured weak human "
                    "agreement on it -- see docs/limitations.md"
                ),
                dataset_checksums=checksums(),
                scored_at=now,
                run_id=run_id,
            )
        )
    return rows


def load_sessions(limit: int | None = None) -> list[Session]:
    return tneval_data.load(limit=limit)
