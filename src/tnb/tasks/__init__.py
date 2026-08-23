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
    ),
    icare.NAME: Task(
        name=icare.NAME,
        prompt_version=icare.PROMPT_VERSION,
        calls_per_session=17,
        load_sessions=icare.load_sessions,
        build_units=_icare_units,
    ),
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
