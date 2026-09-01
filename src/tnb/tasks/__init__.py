"""The two generation tasks, behind one interface the runner can iterate.

A *unit* is one call to one model: a whole SOAP note for the TN-Eval track, one
of 17 sections for the iCARE track. Units are what the cache is keyed on, so a
session whose section 9 timed out resumes at section 9 rather than at section 1.

Neither task's prompt is written here. Both are reproduced from their sources —
see :mod:`tnb.tasks.soap` and :mod:`tnb.tasks.icare`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache

from tnb.datasets.base import Session
from tnb.tasks import icare, soap


@dataclass(frozen=True)
class Unit:
    """One prompt, and everything needed to file its answer away."""

    task: str
    prompt_version: str
    session_id: str
    #: 'note' for a whole SOAP note, 'section-01'..'section-17' for iCARE.
    unit: str
    prompt: str
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Task:
    name: str
    prompt_version: str
    #: Number of model calls per session, for estimating a run before starting it.
    calls_per_session: int
    load_sessions: Callable[[int | None], list[Session]]
    build_units: Callable[[Session], list[Unit]]
    #: How a reply becomes a note, or ``None`` when the task has no structure to
    #: check. **Required, and deliberately not defaulted.**
    #:
    #: It used to be a dict in :mod:`tnb.generation` keyed on the task name, and
    #: a task absent from that dict was not an error -- it was a task whose
    #: replies were never checked, so a reply that was not a note was stored as
    #: a success and the repair loop never ran. Two tasks shipped that way.
    #: Here the field cannot be omitted: leaving it out is a TypeError when the
    #: module is imported, not a silence three hundred calls into a run.
    #:
    #: Takes the answer and the unit, because a task whose sections each name
    #: their own keys has its reply checked against the ones that section asked
    #: for. ``None`` is a real answer, given by `icare`: its sections are prose
    #: and there is nothing to fail to parse.
    parse: Callable[[str, str], dict | None] | None

    #: Providers this task's sessions may be sent to, or ``None`` for any.
    #:
    #: **A corpus of confidential clinical sessions may be read only by the
    #: infrastructure it is allowed to reach.** This is not advice and not a
    #: flag: `cmd_generate` refuses to build a job for a provider outside this
    #: set, so the restriction holds whatever a command line says or omits.
    #:
    #: It exists because omitting `--providers` once sent every session of a
    #: confidential corpus to two external providers -- 150 calls, every one
    #: answered. The prompt carries the transcript, so a default meaning
    #: "every provider with a token" was one forgotten flag away from a
    #: disclosure, and the published methodology said in the same breath that
    #: those transcripts never leave.
    #:
    #: No task here sets it today. That is a fact about the corpora currently
    #: read, not a reason to drop the guard: a task that needs it would
    #: otherwise have to remember to bring its own.
    confined_to: tuple[str, ...] | None = None
    #: Appended and re-asked when an answer arrives but cannot be parsed, as
    #: many times as :attr:`parse_attempts`. TN-Eval do this; iCARE do not, and
    #: neither does this harness on its own initiative.
    repair_suffix: str = ""
    parse_attempts: int = 1


def _soap_units(session: Session) -> list[Unit]:
    return [
        Unit(
            task=soap.NAME,
            prompt_version=soap.PROMPT_VERSION,
            session_id=session.id,
            unit="note",
            prompt=soap.build_prompt(session),
        )
    ]


@cache
def _instructions() -> tuple[str, ...]:
    """Fetched once per process; the file itself is cached in ``data/``."""
    return tuple(icare.load_instructions())


def _icare_units(session: Session) -> list[Unit]:
    return [
        Unit(
            task=icare.NAME,
            prompt_version=icare.PROMPT_VERSION,
            session_id=session.id,
            unit=section.unit,
            prompt=section.prompt,
            meta={"section": section.number, "temporal": section.is_temporal},
        )
        for section in icare.build_prompts(session, list(_instructions()))
    ]


TASKS: dict[str, Task] = {
    soap.NAME: Task(
        name=soap.NAME,
        prompt_version=soap.PROMPT_VERSION,
        calls_per_session=1,
        load_sessions=soap.load_sessions,
        build_units=_soap_units,
        parse=lambda text, unit: soap.parse_note(text),
        repair_suffix=soap.REPAIR_SENTENCE,
        parse_attempts=soap.PARSE_ATTEMPTS,
    ),
    icare.NAME: Task(
        name=icare.NAME,
        prompt_version=icare.PROMPT_VERSION,
        calls_per_session=17,
        load_sessions=icare.load_sessions,
        build_units=_icare_units,
        # Prose, not a structure. A section that came back as a refusal is
        # rendered "Nil" by `icare_run`, which is the honest reading of a
        # field the model declined to fill; a section the infrastructure lost
        # is skipped there instead. Neither is a parse.
        parse=None,
    ),
    # Two tasks over one prompt, because `results.TRACK_BY_TASK` maps a
    # generation directory to a track and one task could not tell the real
    # sessions from the translated ones.
}


def resolve(names: str | None) -> list[Task]:
    """Turn a comma-separated ``--tasks`` value into tasks, or all of them."""
    if not names:
        return list(TASKS.values())

    chosen = []
    for name in (part.strip() for part in names.split(",") if part.strip()):
        if name not in TASKS:
            raise RuntimeError(f"Unknown task '{name}'. Known tasks: {', '.join(TASKS)}.")
        chosen.append(TASKS[name])
    return chosen
