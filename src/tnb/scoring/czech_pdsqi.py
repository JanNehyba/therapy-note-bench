"""PDSQI-9 asked about the Czech notes: is the note any good, not is the Czech.

The six criteria in `scoring/czech.py` ask whether the Czech is any good. They
do not ask whether the *note* is any good, and they cannot: a flawless Czech
sentence about nothing passes all six. This module is the other half of the
question, and it was in the plan from the start -- including a prediction to be
tested, that `organized` would come back flat here for the same reason it is
flat in English, because the prompt dictates the structure.

Nothing here is a new instrument. `scoring/pdsqi.py` holds the attributes and
the prompt, `scoring/pdsqi_run.py` asks them and counts the answers; this module
supplies the three things that differ and refuses the one thing that must never
happen.

**What differs, and why each is not a detail.**

*The note is shown with its own headings.* `pdsqi.render_note` joins the four
sections under English labels. A Czech note carries Czech ones, and rendering it
under English headings would rate an artefact no model wrote -- `organized` and
`comprehensible` are exactly the attributes a heading language could move. The
joining is part of the prompt by `render_note`'s own docstring, so this carries
its own `JUDGE_PROMPT_VERSION` rather than borrowing one it does not match.

*The prompt itself stays in English, verbatim.* PDSQI-9 is a published
instrument and the repository reproduces published prompts word for word. A
translated instrument is a different instrument with no validation behind it,
and this track already spends its one translation on the generation prompt.
What the judge reads in English is the question; what it reads in Czech is the
note.

*The two halves are asked different numbers of questions.* `accurate` and
`thorough` cannot be answered without the session. The real sessions are
confidential and never leave e-INFRA, so the real half is asked the six
attributes that read the note alone. The translated half is AnnoMI, published
under CC-BY, so it is asked all eight. Six columns and eight columns are two
instruments and get two tracks: putting a six-attribute row beside an
eight-attribute one under one heading would invite exactly the average nobody
should take.

**And the refusal.** `transcripts_may_leave` decides, from the corpus name
alone, whether a transcript may be attached to a candidate at all. A real
session has no path to the judge's provider through this module: not a flag to
set wrongly, a function that returns False and a corpus that is not in the
mapping raising rather than defaulting.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace

from tnb import results
from tnb.datasets.base import Session
from tnb.scoring import pdsqi
from tnb.scoring.run import Candidate
from tnb.tasks import czech as czech_task
from tnb.tasks import deepsy as deepsy_task

#: The presentation, not the instrument. `pdsqi9-note-v1` names a note joined
#: under English headings; these notes are joined under Czech ones. Same
#: questions, same anchors, a different thing on the page in front of the judge.
JUDGE_PROMPT_VERSION = "pdsqi9-note-cs-v1"

#: Which track a corpus's PDSQI rows belong to, and how many attributes it can
#: be asked. Read together: the attribute set is not a preference, it follows
#: from whether the transcript may be shown.
BY_TASK: dict[str, str] = {
    czech_task.NAME_REAL: results.TRACK_CZECH_REAL_PDSQI,
    czech_task.NAME_TRANSLATED: results.TRACK_CZECH_TRANSLATED_PDSQI,
    deepsy_task.NAME_REAL: results.TRACK_DEEPSY_REAL_PDSQI,
    deepsy_task.NAME_TRANSLATED: results.TRACK_DEEPSY_TRANSLATED_PDSQI,
}

#: Which corpus each task reads, and it is the corpus that decides everything
#: about confidentiality. `deepsy-real` is a different note format over the same
#: ten recorded sessions as `czech-real`, so it inherits the same answer, and
#: writing that down here rather than pattern-matching on the name is the point:
#: a task added later has to be classified by somebody rather than by a suffix.
CORPUS_BY_TASK: dict[str, str] = {
    czech_task.NAME_REAL: "real",
    deepsy_task.NAME_REAL: "real",
    czech_task.NAME_TRANSLATED: "translated",
    deepsy_task.NAME_TRANSLATED: "translated",
}

#: How a task's notes are assembled. A SOAP note is one file and a Deepsy note
#: is three, and the reader that knows the difference already exists for each.
ASSEMBLER_BY_TASK: dict[str, str] = {
    czech_task.NAME_REAL: "czech",
    czech_task.NAME_TRANSLATED: "czech",
    deepsy_task.NAME_REAL: "deepsy",
    deepsy_task.NAME_TRANSLATED: "deepsy",
}


def transcripts_may_leave(task_name: str) -> bool:
    """Whether this corpus's transcripts may reach the judge's provider.

    `czech-real` is ten recorded sessions with one client. They are
    de-identified before any model reads them and they still never leave the
    infrastructure that holds them: a model on e-INFRA writes the note, and what
    goes to Google or OpenAI is the note. That is the narrowed promise in
    `docs/methodology.md`, and it is enforced here rather than remembered.

    `czech-translated` is AnnoMI, published under CC-BY, translated into Czech
    for this track. There is nothing confidential to protect and the two
    attributes that need a session can be asked.

    An unknown corpus raises. A corpus this function has not been told about is
    a corpus nobody has decided this question for, and defaulting either way
    would decide it silently.
    """
    corpus = CORPUS_BY_TASK.get(task_name)
    if corpus == "real":
        return False
    if corpus == "translated":
        return True
    raise ValueError(
        f"{task_name!r} is not a Czech corpus. Whether its transcripts may be "
        "sent to the judge's provider is not a question this module can guess at."
    )


def attribute_keys(task_name: str) -> tuple[str, ...]:
    """The attributes this corpus is asked, in the instrument's own order."""
    if transcripts_may_leave(task_name):
        return pdsqi.ATTRIBUTE_KEYS
    return pdsqi.NOTE_ONLY_KEYS


def measures(task_name: str) -> dict[str, dict[str, str]]:
    """`pdsqi.MEASURES`, narrowed to what this corpus is actually asked.

    Declaring a column that is never filled would leave an empty heading on the
    page, which reads as a model that failed rather than as a question nobody
    was allowed to ask.
    """
    keys = attribute_keys(task_name)
    return {key: value for key, value in pdsqi.MEASURES.items() if key in keys}


def metrics_note(task_name: str) -> str:
    """What these rows say about themselves, corpus by corpus."""
    shared = (
        "PDSQI-9, adapted: see docs/landscape.md. The instrument and its prompt are "
        "reproduced in English; the notes it rates are in Czech and are shown with "
        "the Czech headings the models wrote. Physicians agree with each other on "
        "this instrument at Krippendorff's alpha 0.575, and no human has rated these "
        "notes on it, so there is no agreement figure for this track."
    )
    if transcripts_may_leave(task_name):
        return shared + (
            " All eight attributes are asked: these transcripts are AnnoMI, "
            "translated, and may be shown to the judge."
        )
    return shared + (
        " Six of the eight attributes are asked. `accurate` and `thorough` need the "
        "session, and these sessions are confidential and are never sent to the "
        "judge's provider -- the two columns are absent because the question could "
        "not be put, which is not the same as a note that failed them."
    )


def from_generations(
    sessions: list[Session], *, task_name: str, cache_dir=None
) -> Iterator[Candidate]:
    """The Czech notes as candidates, carrying a transcript only where allowed.

    One reader of the generation cache, not two: `czech_run.from_generations`
    already walks it and yields candidates with an empty `conversation`, which
    is the safe default. This attaches the session text afterwards, and only
    for the corpus `transcripts_may_leave` permits.
    """
    from tnb.scoring import czech_run, deepsy_run

    # Which reader, decided from the same table the track and the confidentiality
    # answer come from. A SOAP note is one file per session and a Deepsy note is
    # three that are assembled or refused as a whole, and asking the SOAP reader
    # for a Deepsy note yields nothing at all -- silently, which is why this is a
    # lookup that raises rather than a default.
    kind = ASSEMBLER_BY_TASK.get(task_name)
    if kind is None:
        raise ValueError(f"{task_name!r} has no note assembler registered.")
    read = czech_run.from_generations if kind == "czech" else deepsy_run.from_generations

    if not transcripts_may_leave(task_name):
        yield from read(sessions, task_name=task_name, cache_dir=cache_dir)
        return

    by_id = {session.id: session for session in sessions}
    for candidate in read(sessions, task_name=task_name, cache_dir=cache_dir):
        session = by_id.get(candidate.session_id)
        if session is None:
            continue
        yield replace(candidate, conversation=czech_task.render_transcript(session))
