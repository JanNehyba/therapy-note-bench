"""Ask the six Czech criteria about the notes, and file the answers away.

The same shape as `scoring/pdsqi_run.py`, over a different corpus and a
different instrument. Two things differ from every runner before it, and both
are forced by the design rather than chosen.

**The track is a parameter, not a constant.** `run`, `icare_run` and
`pdsqi_run` each hard-code the one track they serve. This one serves two --
`czech-real` and `czech-translated` -- because ten real sessions with one client
and ten translated AnnoMI conversations answer different questions and must
never be averaged. `results.COMPARABILITY_KEYS` keeps them apart once they are
rows; passing the track keeps them apart before that.

**Nothing here ever holds a transcript.** `czech.build_tasks` takes a note and
has no other parameter, so a confidential session cannot reach the judge's
provider even by mistake -- there is no argument it could arrive through. The
model reads the transcript on e-INFRA; what leaves is the note the model wrote.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from tnb import __version__, generation, judge, results
from tnb.datasets.base import Session, checksums
from tnb.scoring import czech
from tnb.scoring.run import BudgetExceeded, Candidate
from tnb.tasks import czech as task


@dataclass
class NoteResult:
    """One note's answers, and what it cost to get them."""

    candidate: Candidate
    scored: dict[str, float] = field(default_factory=dict)
    #: Criteria that were asked and not answered. Named, never counted clean:
    #: a judge that ran out of room is not a note without the fault.
    missing: list[str] = field(default_factory=list)
    asked: int = 0
    cached: int = 0
    failed: int = 0
    #: A note with no content at all. Not scored -- every criterion asks about
    #: the absence of a fault, so it would pass all six -- and not dropped
    #: either, or a model that wrote nothing would lose its worst note.
    empty: bool = False

    @property
    def is_complete(self) -> bool:
        return bool(self.scored) and not self.missing


def from_generations(
    sessions: list[Session], *, task_name: str, cache_dir=None
) -> Iterator[Candidate]:
    """Every Czech note our models produced, straight from the generation cache.

    `task_name` is `czech-real` or `czech-translated`. The two corpora live in
    two generation directories precisely so this can read one without the other.
    """
    cache_dir = cache_dir or generation.CACHE_DIR
    by_id = {session.id: session for session in sessions}

    for provider_dir in sorted(p for p in cache_dir.iterdir() if p.is_dir()):
        task_dir = provider_dir / task_name / task.PROMPT_VERSION
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
                    # Never read by this module. The field exists because
                    # `Candidate` is shared; `czech.build_tasks` has nowhere to
                    # put it, which is the point.
                    conversation="",
                )


def score_note(
    candidate: Candidate,
    client: judge.Judge,
    spend: judge.Spend,
    *,
    force: bool = False,
    cache_root=None,
    render=task.render_note,
    judge_prompt_version: str = czech.JUDGE_PROMPT_VERSION,
) -> NoteResult:
    """Ask one note's criteria, reusing whatever was asked before.

    `render` is a parameter because the Deepsy track scores the same six
    criteria over a note with different sections. The instrument does not
    change; what it is shown does, and a renderer hard-coded here would have
    meant a second copy of this function to change one line of it.
    """
    fingerprint = client.config.fingerprint()
    note = render(candidate.note)
    tasks = czech.build_tasks(note)
    answers: dict[str, str] = {}
    result = NoteResult(candidate=candidate, empty=not czech.has_content(note))

    for question in tasks:
        path = judge.cache_path(
            client.config.model,
            judge_prompt_version,
            candidate.provider,
            candidate.system_id,
            candidate.session_id,
            question.unit,
            fingerprint=fingerprint,
            root=cache_root,
        )

        record = None if force else judge.load_cached(path, fingerprint, question.prompt)
        if record is not None:
            answers[question.unit] = record["answer"]
            result.cached += 1
            continue

        if spend.would_exceed(client.config.model, len(question.prompt) // 4):
            raise BudgetExceeded(spend.usd(client.config.model), spend.limit_usd)

        answer = client.ask(question.prompt)
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
                "unit": question.unit,
                "criterion": question.criterion,
                "prompt_chars": len(question.prompt),
                # The question, so a re-generated note is not published carrying
                # the judgement of the text it replaced.
                "prompt_sha256": judge.prompt_digest(question.prompt),
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
            answers[question.unit] = answer.text
        else:
            result.failed += 1

    scores = czech.aggregate(note, answers)
    result.scored = dict(scores.by_criterion)
    result.missing = list(scores.incomplete.get("czech", []))
    return result


def from_cache(
    candidates: list[Candidate],
    client: judge.Judge,
    *,
    cache_root=None,
    render=task.render_note,
    judge_prompt_version: str = czech.JUDGE_PROMPT_VERSION,
) -> list[NoteResult]:
    """Score every note whose answers are already on disk, asking nothing.

    The same route `tnb score --cache-only` has had since the TN-Eval track
    existed, and the Czech track went without it for a reason that is worth
    writing down: it was never needed to *publish* early, because the Czech run
    is short. It is needed to **rebuild a row without re-asking a question**.

    A result row records more than its numbers -- which instrument produced
    them, how many notes were scored, and what the measures mean. When one of
    those descriptions is corrected in code, the rows already written keep the
    old one, and `results/` is append-only, so the only honest repair is to
    derive the rows again and append them. Doing that through a normal run
    would put ~1,700 questions back in front of a judge to change a sentence.

    **A note answered only in part is kept, and this differs from `run.py`'s
    version on purpose.** That one skips it, because it exists to publish a
    run while the run is still going and a half-answered note there is one
    the judge has not finished with. This one exists to rebuild a run that
    already ended, so it has to reach the same numbers a live run reached --
    and a live run does not drop such a note either. `czech.aggregate`
    returns None for a criterion with no answer, the mean is taken over the
    criteria that have one, and the criterion that does not is named in
    `missing` rather than counted as passed. Dropping the whole note instead
    would drop five answers to avoid reporting one gap, and it moved four
    notes on each half the first time this was written.
    """
    fingerprint = client.config.fingerprint()
    scored: list[NoteResult] = []

    for candidate in candidates:
        note = render(candidate.note)
        result = NoteResult(candidate=candidate, empty=not czech.has_content(note))
        tasks = czech.build_tasks(note)
        answers: dict[str, str] = {}
        for question in tasks:
            record = judge.load_cached(
                judge.cache_path(
                    client.config.model,
                    judge_prompt_version,
                    candidate.provider,
                    candidate.system_id,
                    candidate.session_id,
                    question.unit,
                    fingerprint=fingerprint,
                    root=cache_root,
                ),
                fingerprint,
                # The question, so a re-generated note is not published carrying
                # the judgement of the text it replaced.
                question.prompt,
            )
            if record is not None:
                answers[question.unit] = record["answer"]
        result.cached = len(answers)
        scores = czech.aggregate(note, answers)
        result.scored = dict(scores.by_criterion)
        result.missing = list(scores.incomplete.get("czech", []))
        scored.append(result)
    return scored


def score_many(
    candidates: list[Candidate],
    client: judge.Judge,
    spend: judge.Spend,
    *,
    force: bool = False,
    cache_root=None,
    render=task.render_note,
    judge_prompt_version: str = czech.JUDGE_PROMPT_VERSION,
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


@dataclass
class SystemAggregate:
    """Every note one system was scored on, and the mean of the complete ones."""

    notes: list[NoteResult] = field(default_factory=list)
    #: How a note is turned into text, for the length column. The Deepsy track
    #: has different sections, and counting its words with the SOAP renderer
    #: would count the wrong headings.
    render: object = task.render_note

    @property
    def complete(self) -> list[NoteResult]:
        return [note for note in self.notes if note.is_complete]

    @property
    def n_partial(self) -> int:
        return len(self.notes) - len(self.complete)

    @property
    def n_empty(self) -> int:
        return sum(1 for note in self.notes if note.empty)

    def metrics(self) -> results.Metrics:
        """The share of notes free of each fault, column by column.

        **A note counts in the columns it answered, not only in the columns of
        notes that answered everything.** Each column already carries its own
        denominator beside it -- quotation marks are only asked of a note that
        quotes something -- so per-column denominators are what this track was
        built on, and this extends that rule rather than departing from it.

        It replaces a worse rule, and the difference was measured before it was
        changed. Requiring every criterion meant one unanswered question threw
        the note out of all seven columns the instrument then had, including the five
        it had answered
        cleanly. On the real half that removed 18 of 104 notes; `gpt-oss-120b`
        published a mean over five of its ten.

        **What it cost was measured, and it is not what it looked like.** The
        deleted notes are the longer ones -- median 658 words against 468 --
        and length predicts faults: among notes that did count, the shorter
        half scores 0.694 free of fault and the longer half 0.430. That reads
        like a one-directional inflation, and it was written down as one here
        before it was checked.

        Checking it against the rows says otherwise. Over 76 model-by-criterion
        values on the real half, the repair moves the mean by +0.011 -- 31 up,
        19 down -- so the deletion was not shifting the table in one direction.
        What it was doing is worse-behaved and easier to miss: individual cells
        move by as much as 0.20, a fifth of the scale, on means over ten notes.
        `gpt-oss-120b` rises from 0.00 to 0.20 on `untranslated`, so the rule
        that was supposed to be flattering it was in fact holding it down.

        The repair is right because deleting an answered measurement is wrong
        and because the noise it added is large, not because it was biased in a
        direction anybody had established.

        The loss also concentrates by criterion. `diacritics` went unanswered on
        8.7% of notes and `nonword` on 4.8%, while `untranslated` and `register`
        lost none -- so those two columns were being shrunk by failures that had
        nothing to do with them.

        `n_sessions_partial` still counts notes that answered less than
        everything, so the gap stays visible; it is no longer also a deletion.

        **And why `__version__` did not move for it.** The rule says to bump
        whenever a measure's definition changes, and by that rule this earns
        one. It was tried and reverted: `harness_version` is global, so 0.7.0
        put "measured by harness 0.6.0, whose columns may not mean what the
        newer tables' columns mean" on the *published English* tables, where
        nothing had changed. A true statement about the Czech columns became a
        false one about the English ones, on the page people actually read.

        What makes that safe to leave is that no Czech number is published and
        the old rows are superseded rather than compared: `results.latest`
        draws the newest row per identity, the earlier ones stay in the
        append-only local record, and nothing draws them beside these. If the
        Czech track is ever published, this needs a bump and `report.py` needs
        to say which measures a version redefined instead of warning about all
        of them.
        """
        if not self.notes:
            return results.Metrics()

        headline = {}
        detail = {}
        for key in czech.CRITERION_KEYS:
            values = [note.scored[key] for note in self.notes if key in note.scored]
            if values:
                headline[key] = round(sum(values) / len(values), 4)
                detail[f"{key}.notes"] = len(values)

        words = [czech.note_words(self.render(note.candidate.note)) for note in self.notes]
        if words:
            detail["note_words"] = round(sum(words) / len(words), 1)
        return results.Metrics(headline=headline, detail=detail)


def to_rows(
    scored: list[NoteResult],
    *,
    track: str,
    judge_model: str,
    judge_settings: dict | None = None,
    n_generated: dict | None = None,
    n_attempted: dict | int | None = None,
    n_unreached: dict | None = None,
    settings: dict | None = None,
    run_id: str = "",
    prompt_version: str = task.PROMPT_VERSION,
    judge_prompt_version: str = czech.JUDGE_PROMPT_VERSION,
    render=task.render_note,
    metrics_note: str | None = None,
) -> list[results.Row]:
    """One row per (provider, system), on the track it was scored for.

    The counting rules are `scoring/run.to_rows`'s, for the same reasons: a note
    the endpoint never answered is not the model's failure, and a count of
    unusable notes travels with the reason it was unusable.
    """
    allowed = (
        results.TRACK_CZECH_REAL,
        results.TRACK_CZECH_TRANSLATED,
        results.TRACK_DEEPSY_REAL,
        results.TRACK_DEEPSY_TRANSLATED,
    )
    if track not in allowed:
        raise ValueError(f"{track!r} is not scored by the Czech criteria.")

    groups: dict[tuple[str, str], SystemAggregate] = {}
    labels: dict[tuple[str, str], Candidate] = {}
    for note in scored:
        key = (note.candidate.provider, note.candidate.system_id)
        groups.setdefault(key, SystemAggregate(render=render)).notes.append(note)
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
                metrics_note=(
                    "Six yes/no criteria about the Czech, asked of the note alone. "
                    "This instrument is this repository's own and no human has rated "
                    "these notes on it, so there is no agreement figure and no ceiling "
                    "to read one against. The generation prompt is a translation of "
                    "TN-Eval's, not a reproduction."
                ),
                dataset_checksums=checksums(),
                scored_at=now,
                run_id=run_id,
            )
        )
    return rows
