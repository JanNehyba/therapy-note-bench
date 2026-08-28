"""Score the SOAP notes on PDSQI-9, and file the answers away.

The same shape as `scoring/run.py`, over the same notes, asking a different
instrument. It is a different instrument and not a different corpus, so nothing
about the notes or the candidates changes -- only the questions.

**These rows do not join the rubric's table and cannot.** They carry
`results.TRACK_PDSQI` and `pdsqi.JUDGE_PROMPT_VERSION`, two of the six fields
`results.COMPARABILITY_KEYS` requires agreement on, so they form their own
comparability group twice over. That is the point: a note's coverage of a
23-item checklist and its quality on a validated instrument are two
measurements, and averaging them would be inventing a third.

**Two attributes need the transcript and six do not.** That falls out of the
instrument -- `accurate` and `thorough` cannot be judged without the session --
and it is carried here rather than smoothed over: a note scored without a
transcript is recorded as having been asked six questions, not as having failed
two.

**The note's presentation is a parameter, because the Czech track reuses this
runner.** A Czech note carries Czech headings, and showing it under English ones
would rate an artefact no model wrote -- `organized` and `comprehensible` are
exactly the attributes a heading language could move. `render_note`'s docstring
says the joining is part of the prompt, so a different joining travels with a
different `judge_prompt_version` rather than quietly sharing one.
"""

from __future__ import annotations

import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from tnb import __version__, judge, results
from tnb.datasets.base import checksums
from tnb.scoring import pdsqi
from tnb.scoring.run import BudgetExceeded, Candidate
from tnb.tasks import soap


@dataclass
class NoteResult:
    """One note's PDSQI answers, and what it cost to get them."""

    candidate: Candidate
    scored: dict[str, float] = field(default_factory=dict)
    #: Attributes that were asked and not answered. Named, never scored zero:
    #: a judge that ran out of room is not a note that lacks the quality.
    missing: list[str] = field(default_factory=list)
    asked: int = 0
    cached: int = 0
    failed: int = 0

    @property
    def is_complete(self) -> bool:
        return bool(self.scored) and not self.missing


def score_note(
    candidate: Candidate,
    client: judge.Judge,
    spend: judge.Spend,
    *,
    force: bool = False,
    cache_root=None,
    with_transcript: bool = True,
    render=pdsqi.render_note,
    judge_prompt_version: str = pdsqi.JUDGE_PROMPT_VERSION,
) -> NoteResult:
    """Ask one note's eight questions, reusing whatever was asked before."""
    fingerprint = client.config.fingerprint()
    note = render(candidate.note)
    transcript = candidate.conversation if with_transcript else None
    tasks = pdsqi.build_tasks(note, transcript)
    answers: dict[str, str] = {}
    result = NoteResult(candidate=candidate)

    for task in tasks:
        path = judge.cache_path(
            client.config.model,
            judge_prompt_version,
            candidate.provider,
            candidate.system_id,
            candidate.session_id,
            task.unit,
            root=cache_root,
        )

        record = None if force else judge.load_cached(path, fingerprint, task.prompt)
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
                "judge_prompt_version": judge_prompt_version,
                "judge_fingerprint": fingerprint,
                "provider": candidate.provider,
                "system_id": candidate.system_id,
                "session_id": candidate.session_id,
                "unit": task.unit,
                "attribute": task.attribute,
                "prompt_chars": len(task.prompt),
                "prompt_sha256": judge.prompt_digest(task.prompt),
                "answer": answer.text,
                "ok": answer.ok,
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
            result.failed += 1

    expected = tuple(task.attribute for task in tasks)
    result.scored, result.missing = pdsqi.score(answers, expected=expected)
    return result


def score_many(
    candidates: list[Candidate],
    client: judge.Judge,
    spend: judge.Spend,
    *,
    force: bool = False,
    cache_root=None,
    with_transcript: bool = True,
    render=pdsqi.render_note,
    judge_prompt_version: str = pdsqi.JUDGE_PROMPT_VERSION,
    on_note=None,
) -> list[NoteResult]:
    """Score notes concurrently, stopping rather than crossing the ceiling."""
    scored: list[NoteResult] = []
    stopped: BudgetExceeded | None = None

    def work(candidate: Candidate) -> NoteResult | None:
        if stopped is not None:
            return None
        return score_note(
            candidate,
            client,
            spend,
            force=force,
            cache_root=cache_root,
            with_transcript=with_transcript,
            render=render,
            judge_prompt_version=judge_prompt_version,
        )

    with ThreadPoolExecutor(max_workers=max(1, client.config.concurrency)) as pool:
        for future in [pool.submit(work, candidate) for candidate in candidates]:
            try:
                result = future.result()
            except BudgetExceeded as error:
                stopped = stopped or error
                continue
            if result is None:
                continue
            scored.append(result)
            if on_note is not None:
                on_note(result)

    if stopped is not None and not scored:
        raise stopped
    return scored


def from_cache(
    candidates: list[Candidate],
    client: judge.Judge,
    *,
    cache_root=None,
    with_transcript: bool = True,
    render=pdsqi.render_note,
    judge_prompt_version: str = pdsqi.JUDGE_PROMPT_VERSION,
) -> list[NoteResult]:
    """Score whatever is already answered on disk, asking the judge nothing.

    `run.from_cache` publishes a note that is missing up to a tenth of its sixty
    questions. Eight is not sixty: one unanswered attribute out of eight is an
    eighth of the instrument, and a mean over the remaining seven would be a
    different measurement under the same column heading. So there is no
    threshold here -- a note is complete or it is counted as partial, and
    `SystemAggregate.metrics` averages only the complete ones.
    """
    fingerprint = client.config.fingerprint()
    scored: list[NoteResult] = []

    for candidate in candidates:
        note = render(candidate.note)
        transcript = candidate.conversation if with_transcript else None
        tasks = pdsqi.build_tasks(note, transcript)

        answers: dict[str, str] = {}
        for task in tasks:
            record = judge.load_cached(
                judge.cache_path(
                    client.config.model,
                    judge_prompt_version,
                    candidate.provider,
                    candidate.system_id,
                    candidate.session_id,
                    task.unit,
                    root=cache_root,
                ),
                fingerprint,
                # The question, so a re-generated note is not published carrying
                # the judgement of the text it replaced.
                task.prompt,
            )
            if record is not None:
                answers[task.unit] = record["answer"]

        if not answers:
            continue

        result = NoteResult(candidate=candidate, cached=len(answers))
        expected = tuple(task.attribute for task in tasks)
        result.scored, result.missing = pdsqi.score(answers, expected=expected)
        scored.append(result)

    return scored


@dataclass
class SystemAggregate:
    """Every note one system was scored on, and the mean of the complete ones."""

    notes: list[NoteResult] = field(default_factory=list)

    @property
    def complete(self) -> list[NoteResult]:
        return [note for note in self.notes if note.is_complete]

    @property
    def n_partial(self) -> int:
        return len(self.notes) - len(self.complete)

    def metrics(self) -> results.Metrics:
        """Averaged over the notes the judge finished, and over nothing else.

        A note with one attribute unanswered is left out entirely rather than
        averaged over seven: the missing attribute is not evenly distributed --
        a judge runs out of room on the long, dense notes -- so dropping it
        from a denominator is biased in a direction nobody chose.
        """
        complete = self.complete
        if not complete:
            return results.Metrics()

        headline = {}
        for attribute in pdsqi.ATTRIBUTES:
            values = [
                note.scored[attribute.key] for note in complete if attribute.key in note.scored
            ]
            if len(values) == len(complete):
                headline[attribute.key] = round(sum(values) / len(values), 4)
        return results.Metrics(headline=headline)


#: What the rows say about themselves on the SOAP track. The Czech tracks pass
#: their own, because "no human has rated these notes" is true of both but the
#: rest is not: those notes are in Czech, and two of the eight attributes are
#: not asked of the real half at all.
METRICS_NOTE = (
    "PDSQI-9, adapted: see docs/landscape.md. Physicians agree with each "
    "other on this instrument at Krippendorff's alpha 0.575, which is the "
    "ceiling these columns are read against -- no human has rated these "
    "notes on it."
)


def to_rows(
    scored: list[NoteResult],
    *,
    judge_model: str,
    judge_settings: dict | None = None,
    n_generated: dict | None = None,
    n_attempted: dict | int | None = None,
    n_unreached: dict | None = None,
    settings: dict | None = None,
    run_id: str = "",
    track: str = results.TRACK_PDSQI,
    prompt_version: str = soap.PROMPT_VERSION,
    judge_prompt_version: str = pdsqi.JUDGE_PROMPT_VERSION,
    metrics_note: str = METRICS_NOTE,
) -> list[results.Row]:
    """One row per (provider, system), on its own comparability group.

    The counting rules are `scoring/run.to_rows`'s, for the same reasons: a
    note the endpoint never answered is not the model's failure, and a count of
    unusable notes travels with the reason it was unusable.

    `track` and the two version fields are parameters because the same
    instrument is asked of three corpora. They are four of the six fields
    `results.COMPARABILITY_KEYS` compares, so passing them wrongly would merge
    tables that must not merge -- which is why the Czech caller passes all four
    together rather than inheriting any.
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

        unreached = (n_unreached or {}).get(key)
        missing = max(0, attempted - generated)
        blameless = min(missing, unreached.sessions if unreached else 0)
        rows.append(
            results.Row(
                track=track,
                system_id=candidate.system_id,
                system_type=candidate.system_type,
                system_label=candidate.system_label,
                provider=candidate.provider,
                harness_version=__version__,
                prompt_version=prompt_version,
                judge_model=judge_model,
                judge_settings=dict(judge_settings or {}),
                judge_prompt_version=judge_prompt_version,
                settings=(settings or {}).get(key, results.Settings()),
                n_sessions_attempted=attempted,
                n_sessions_generated=generated,
                n_sessions_scored=len(aggregate.notes),
                n_sessions_partial=aggregate.n_partial,
                n_failed=missing - blameless,
                failure_reasons=dict(unreached.failure_reasons) if unreached else {},
                unreached_reasons=dict(unreached.reasons) if unreached else {},
                metrics=aggregate.metrics(),
                metrics_note=metrics_note,
                dataset_checksums=checksums(),
                scored_at=now,
                run_id=run_id,
            )
        )
    return rows
