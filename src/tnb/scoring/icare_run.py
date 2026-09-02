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

import datetime as dt
import json
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
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
    asked: int = 0
    #: Judge calls that came back unusable. Counted rather than inferred: a
    #: dimension the judge refused and a dimension the scorer does not produce
    #: leave the same hole in `scores`, and only one of them is a failure.
    failed: int = 0


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
        # `by_section` is left empty on purpose, and that is not the same as
        # having nothing to say. `Metrics` documents the field as the same
        # measures per section -- 4 for SOAP, 17 for iCARE -- and this track has
        # no per-section scores: ROUGE-L and BERTScore are computed over the
        # whole note against the whole expert note, and TRACE is five ratings of
        # the note, not of a section.
        #
        # It used to carry `{"trace": detail}`: one key that is not a section,
        # holding the same five values `detail` holds one line below. The page
        # then drew a BY SECTION table whose only row was labelled `trace` and
        # whose every cell was an em-dash, because those five keys are not the
        # five column keys -- an expansion that looked truncated and was.
        return Metrics(headline=headline, detail=detail)


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
    compare to.

    **A note is skipped when any of its 17 sections never reached the model.**
    Rendering the gap as "Nil" -- which is what this did -- scores the model as
    though it had chosen to leave the field blank, and a rate limit is not a
    choice. glm-5 lost one section to e-INFRA refusing a fourth parallel
    request, and that would have counted against its temporal and ROUGE-L
    scores as an empty field.

    A section the *model* failed to write is a different case and is not skipped:
    an empty answer or an unparseable one is the model's own doing, and "Nil" is
    the honest rendering of it.
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
                unreached = False
                for unit_path in session_dir.glob("*.json"):
                    try:
                        record = json.loads(unit_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        continue
                    if record.get("ok"):
                        sections[unit_path.stem] = record.get("text", "")
                    elif not results.is_the_models_fault(record.get("error")):
                        # A section we cut off at our own ceiling counts here
                        # too: a note scored without it measures the ceiling.
                        unreached = True
                if not sections or unreached:
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
    asked = 0
    failed = 0

    for task in tasks:
        path = judge.cache_path(
            client.config.model,
            scorer.JUDGE_PROMPT_VERSION,
            candidate.provider,
            candidate.system_id,
            candidate.session_id,
            task.unit,
            fingerprint=fingerprint,
            root=cache_root,
        )
        if not force:
            record = judge.load_cached(path, fingerprint, task.prompt, accepts=task.accepts)
            if record is not None:
                answers[task.unit] = record["answer"]
                cached += 1
                continue

        if spend.would_exceed(client.config.model, client.count_tokens(task.prompt)):
            raise BudgetExceeded(client.config.model, spend)

        answer = client.ask(task.prompt)
        spend.record(client.config.model, answer)
        asked += 1

        # Written whether or not it worked, exactly as the TN-Eval path does.
        # A refusal used to be dropped on the floor here: the note came back
        # scored on four of five TRACE dimensions with nothing on disk saying
        # the fifth had ever been asked, so the gap was indistinguishable from
        # a dimension the scorer does not produce. `load_cached` rejects an
        # `ok: false` record, so keeping it costs nothing and it is re-asked on
        # the next run.
        judge.write_cached(
            path,
            {
                "judge_model": client.config.model,
                "judge_prompt_version": scorer.JUDGE_PROMPT_VERSION,
                "judge_fingerprint": fingerprint,
                "provider": candidate.provider,
                "system_id": candidate.system_id,
                "session_id": candidate.session_id,
                "unit": task.unit,
                "kind": task.kind,
                "section": task.section,
                "prompt_chars": len(task.prompt),
                "prompt_sha256": judge.prompt_digest(task.prompt),
                "answer": answer.text,
                "ok": answer.ok,
                # Recorded because it was not, and the question "did the
                # judge run out of room" then had to be reconstructed from
                # the token counts. The provider has parsed it all along.
                "finish_reason": answer.finish_reason,
                "error": answer.error,
                "input_tokens": answer.input_tokens,
                "output_tokens": answer.output_tokens,
                "thinking_tokens": answer.thinking_tokens,
                "latency_s": round(answer.latency_s, 3),
                "scored_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            allow_reinstrument=force,
        )

        if answer.ok:
            answers[task.unit] = answer.text
        else:
            failed += 1

    return NoteResult(
        candidate=candidate,
        scores=scorer.aggregate(candidate.note, candidate.reference, answers, bert=bert),
        cached=cached,
        asked=asked,
        failed=failed,
    )


def score_many(
    candidates: list[Candidate],
    client: judge.Judge,
    spend: judge.Spend,
    *,
    force: bool = False,
    cache_root: Path | None = None,
    bert: list[float] | None = None,
    on_note: Callable[[NoteResult], None] | None = None,
) -> list[NoteResult]:
    """Score every note, several at a time.

    The TN-Eval path has always done this; this one did not, and at five
    questions per note against a transcript-sized prompt it managed 0.3 answers
    a second -- five hours for two judges over 640 notes. The work is entirely
    network wait, so the pool is the whole fix.

    Results come back in the order they were submitted, not the order they
    finished, so a run is reproducible however the threads interleave. The
    spending ceiling and the answer cache are already thread-safe; `Spend` takes
    a lock and each answer writes its own file.
    """
    results_by_index: dict[int, NoteResult] = {}
    stopped: BudgetExceeded | None = None

    def one(index: int, candidate: Candidate) -> NoteResult:
        return score_note(
            candidate,
            client,
            spend,
            force=force,
            cache_root=cache_root,
            bert=None if bert is None else bert[index],
        )

    with ThreadPoolExecutor(max_workers=max(1, client.config.concurrency)) as pool:
        futures = {
            pool.submit(one, index, candidate): index for index, candidate in enumerate(candidates)
        }
        for future, index in futures.items():
            try:
                results_by_index[index] = future.result()
            except BudgetExceeded as error:
                # The ceiling, not a fault. Answers already written stay cached,
                # so resuming costs nothing -- but the caller has to be told,
                # because a truncated run still writes rows.
                stopped = error
                continue
            if on_note is not None:
                on_note(results_by_index[index])

    # Every other exception is raised, not swallowed. The first version of this
    # discarded the futures, so anything but a budget stop -- a 429 on
    # `count_tokens`, which has no retry loop; an UnpricedModel; a timeout --
    # deleted that note from the average with no traceback, no stderr and no
    # exit code. The notes that vanish are the long ones, which are both the
    # slowest to count and the likeliest to time out.
    # A budget stop raises even when some notes were scored. Returning the
    # partial set let the caller append rows whose averages rest on whichever
    # notes the pool happened to reach -- candidates are ordered by system, so
    # the models sorted first got full coverage and the ones sorted last got
    # none, published side by side with nothing marking the difference. Nothing
    # is lost by refusing: every answer already paid for is in the cache.
    if stopped is not None:
        raise stopped
    return [results_by_index[i] for i in sorted(results_by_index)]


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
    judge_settings: dict | None = None,
    n_generated: dict[tuple[str, str], int] | None = None,
    n_attempted: dict[tuple[str, str], int] | int | None = None,
    n_unreached: dict[tuple[str, str], results.Unreached] | None = None,
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

        # A note the endpoint never answered is missing, but it is not the
        # model's doing. `_coverage_row` has separated the two since glm-5 was
        # published as "39/40 (1 unusable)" over a rate limit; the scored rows
        # never got the same treatment, so the accusation survived here.
        # Bounded by what is actually missing: the coverage index is read from
        # the whole cache and the candidate list may be a slice of it.
        unreached = (n_unreached or {}).get(key)
        missing = max(0, attempted - generated)
        blameless = min(missing, unreached.sessions if unreached else 0)

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
                judge_settings=dict(judge_settings or {}),
                judge_prompt_version=scorer.JUDGE_PROMPT_VERSION,
                n_sessions_attempted=attempted,
                n_sessions_generated=generated,
                n_sessions_scored=len(aggregate.notes),
                n_sessions_partial=aggregate.n_partial,
                n_failed=missing - blameless,
                # The other half of the same separation. Without this every
                # scored row carried a count of unusable notes and an empty
                # `failure_reasons`, so the README printed "42/50 (8 unusable)"
                # and the page "8 note(s) missing, with no recorded reason" --
                # while the reason sat on the coverage row, which `report`
                # drops for any system that has a scored row.
                failure_reasons=dict(unreached.failure_reasons) if unreached else {},
                unreached_reasons=dict(unreached.reasons) if unreached else {},
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
