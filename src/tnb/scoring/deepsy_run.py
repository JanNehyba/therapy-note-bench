"""Read the Deepsy sections back out of the cache as one note each.

Everything else about scoring this track is `czech_run`'s: the same seven
criteria, the same parser, the same treatment of an unanswered question. The
instrument does not change because the format did -- if it did, a difference
between this table and the Czech one would be a difference between two
instruments and the comparison would say nothing.

What differs is assembly. The application makes three calls per session and so
does this, so a note lives in three files rather than one, and a session is only
a candidate when all three of them parsed. **Two of three is not a note**: the
criteria are proportions over a whole note, and a model that answered `data` and
`plan` but not `clinical_hypotheses` would otherwise be scored on two thirds of
the text and printed beside models scored on all of it.

That is stricter than the Czech track needs to be, and deliberately: there a
missing note is one note, here it would be a silently shorter one.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

from tnb import generation
from tnb.datasets.base import Session
from tnb.scoring.run import Candidate
from tnb.tasks import deepsy as task


def from_generations(
    sessions: list[Session], *, task_name: str, cache_dir=None
) -> Iterator[Candidate]:
    """Every complete Deepsy note our models produced.

    `task_name` is `deepsy-real` or `deepsy-translated`. A session appears once,
    carrying the union of its three sections' keys, which is what
    `deepsy.render_note` expects and what the criteria are asked about.
    """
    cache_dir = cache_dir or generation.CACHE_DIR
    wanted = {session.id for session in sessions}

    for provider_dir in sorted(p for p in cache_dir.iterdir() if p.is_dir()):
        task_dir = provider_dir / task_name / task.PROMPT_VERSION
        if not task_dir.exists():
            continue
        for model_dir in sorted(p for p in task_dir.iterdir() if p.is_dir()):
            for session_dir in sorted(p for p in model_dir.iterdir() if p.is_dir()):
                if session_dir.name not in wanted:
                    continue
                note = _assemble(session_dir)
                if note is None:
                    continue
                yield Candidate(
                    provider=provider_dir.name,
                    system_id=model_dir.name,
                    system_type="model",
                    system_label=model_dir.name,
                    session_id=session_dir.name,
                    note=note,
                    # As on the Czech track: the field exists because `Candidate`
                    # is shared, and `czech.build_tasks` has nowhere to put it.
                    conversation="",
                )


def _assemble(session_dir) -> dict[str, str] | None:
    """The three sections as one note, or None if any of them is missing.

    A section that never parsed was written with `ok: false` by `generation`,
    so this reads the same verdict the generator reached rather than parsing
    again and possibly disagreeing with it.
    """
    note: dict[str, str] = {}
    for section in task.SECTIONS:
        path = session_dir / f"{section}.json"
        if not path.exists():
            return None
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        if not record.get("ok") or not record.get("note"):
            return None
        note.update(record["note"])

    expected = {key for section in task.SECTIONS for key in task.KEYS[section]}
    return note if set(note) == expected else None
