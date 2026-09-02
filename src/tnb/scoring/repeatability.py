"""The same questions asked of the same judge twice, and what came back.

A repeat is not a re-score and publishes nothing: the answers land in their own
cache directory (``tnb score --repeat-into`` and its two siblings), and this
module reads that directory beside the published one and counts, per judge and
per instrument, how many of the questions both runs answered came back with the
same parsed answer.

"The same" is the parsed value, not the wording. The number a leaderboard
averages is the parsed answer -- a yes however it is spelled, a rating however
it is decorated -- so that is the level a claim of repeatability has to hold
at. A question one of the two runs did not answer is counted separately and
never as agreement: an unanswered question cannot agree, and folding it into
the same/different count would let a judge that sometimes does not answer
pass for one that always does.

The notes are the first N candidates the scoring commands themselves would
take, in their order, so the same notes reach both judges and the choice is
reproducible from the generation cache alone -- no list to keep in step.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from tnb import judge, results
from tnb.scoring import pdsqi, tneval


@dataclass(frozen=True)
class TrackRepeat:
    """One instrument's questions, asked of one judge twice."""

    track: str
    notes: int
    same: int
    questions: int
    #: Asked in at least one of the two runs and answered in neither, or
    #: answered in only one. A number of its own because it is a different
    #: finding: a judge that will not answer is not a judge that disagrees.
    unanswered: int


@dataclass(frozen=True)
class JudgeRepeat:
    """Every instrument's questions, asked of one judge twice."""

    judge_model: str
    tracks: list[TrackRepeat]

    @property
    def same(self) -> int:
        return sum(track.same for track in self.tracks)

    @property
    def questions(self) -> int:
        return sum(track.questions for track in self.tracks)


def _soap_questions(candidates) -> Iterator[tuple]:
    """Every rubric question the first N notes need, with its parser."""
    for candidate in candidates:
        for task in tneval.build_tasks(candidate.note, candidate.conversation):
            parse = tneval.parse_likert if task.is_likert else tneval.parse_yes_no
            yield candidate, task, parse, tneval.JUDGE_PROMPT_VERSION


def _pdsqi_questions(candidates) -> Iterator[tuple]:
    """Every PDSQI-9 attribute the same notes need, with its parser."""
    for candidate in candidates:
        # `cmd_score_pdsqi`'s own rendering, so the questions compared are the
        # questions the published rows were computed from.
        note = pdsqi.render_note(candidate.note)
        for task in pdsqi.build_tasks(note, candidate.conversation):
            parse = (
                pdsqi.parse_yes_no
                if task.attribute in pdsqi._BINARY_ATTRIBUTES
                else pdsqi.parse_rating
            )
            yield candidate, task, parse, pdsqi.JUDGE_PROMPT_VERSION


def _icare_questions(candidates) -> Iterator[tuple]:
    """Every TRACE question the first N iCARE notes need, with its parser."""
    from tnb.scoring import icare as icare_scorer

    for candidate in candidates:
        for task in icare_scorer.build_trace_tasks(candidate.note, candidate.conversation):
            yield candidate, task, icare_scorer.parse_likert, icare_scorer.JUDGE_PROMPT_VERSION


def _count(
    questions: Iterator[tuple],
    judge_model: str,
    fingerprint: dict,
    *,
    published_root: Path,
    repeat_root: Path,
) -> tuple[int, int, int]:
    """(same, both answered, unanswered in at least one run)."""

    def answer_at(root: Path, candidate, task, parse, prompt_version):
        record = judge.load_cached(
            judge.cache_path(
                judge_model,
                prompt_version,
                candidate.provider,
                candidate.system_id,
                candidate.session_id,
                task.unit,
                fingerprint=fingerprint,
                root=root,
            ),
            fingerprint,
            task.prompt,
            accepts=task.accepts,
        )
        return None if record is None else parse(record["answer"])

    same = both = unanswered = 0
    for candidate, task, parse, prompt_version in questions:
        first = answer_at(published_root, candidate, task, parse, prompt_version)
        again = answer_at(repeat_root, candidate, task, parse, prompt_version)
        if first is None or again is None:
            unanswered += 1
            continue
        both += 1
        same += first == again
    return same, both, unanswered


def measure(
    judge_model: str,
    *,
    fingerprint: dict,
    notes: int = 5,
    repeat_root: Path,
    published_root: Path | None = None,
) -> JudgeRepeat:
    """Ask nothing; read what the two runs answered, and count.

    Both runs must have used the same settings, which is what ``fingerprint``
    pins: a repeat at another thinking budget measures the budget, and that
    measurement already exists (see `docs/limitations.md`).
    """
    from tnb.scoring import icare_run, run

    published_root = Path(published_root) if published_root else judge.CACHE_DIR
    sessions = run.load_sessions()
    # The SOAP and PDSQI candidates are the same notes: PDSQI rates the notes
    # the rubric scored, so one walk serves both instruments.
    soap = list(run.from_generations(sessions))[:notes]
    icare_notes = list(icare_run.from_generations(icare_run.load_sessions()))[:notes]

    counted = []
    for track, walker, candidates in (
        (results.TRACK_TNEVAL, _soap_questions, soap),
        (results.TRACK_PDSQI, _pdsqi_questions, soap),
        (results.TRACK_ICARE, _icare_questions, icare_notes),
    ):
        same, both, unanswered = _count(
            walker(candidates),
            judge_model,
            fingerprint,
            published_root=published_root,
            repeat_root=repeat_root,
        )
        counted.append(
            TrackRepeat(
                track=track,
                notes=len(candidates),
                same=same,
                questions=both,
                unanswered=unanswered,
            )
        )
    return JudgeRepeat(judge_model=judge_model, tracks=counted)


def to_json(repeats: list[JudgeRepeat], *, notes: int, repeat_root: str) -> dict:
    """The shape the methods page reads."""
    from tnb import report

    return {
        "notes": notes,
        # Named for the provenance line: the answers behind this panel live
        # there, and nowhere the published tables are computed from.
        "repeat_root": repeat_root,
        "judges": [
            {
                "judge_model": repeat.judge_model,
                "same": repeat.same,
                "questions": repeat.questions,
                "tracks": [
                    {
                        "track": track.track,
                        "label": report.TRACK_TITLES.get(track.track, track.track),
                        "notes": track.notes,
                        "same": track.same,
                        "questions": track.questions,
                        "unanswered": track.unanswered,
                    }
                    for track in repeat.tracks
                ],
            }
            for repeat in repeats
        ],
    }

