"""Authored source references are distinct from evidence retrieved by the judge."""

from __future__ import annotations

import re

from .schema import Case, Note, Span, digest, plain

REFERENCE = re.compile(r"\[evidence:([A-Za-z0-9_.-]+):([A-Za-z0-9_.-]+)\]")
CANDIDATE = re.compile(r"\[evidence:[^\]\r\n]*(?:\]|$)", re.M)


def extract(note: Note, case: Case) -> list[dict]:
    """Recognize the documented [evidence:source:turn] grammar, preserving invalid targets."""
    targets = {(s.id, t.id) for s in case.sources for t in s.turns}
    references = []
    for match in CANDIDATE.finditer(note.text):
        target = REFERENCE.fullmatch(match[0])
        source_id, unit_id = target.groups() if target else ("", "")
        references.append(
            {
                "id": digest((note.revision, match.start(), match.end())),
                "source_id": source_id,
                "unit_id": unit_id,
                "span": plain(Span("note", match.start(), match.end(), match[0])),
                "syntax_valid": target is not None,
                "valid": (source_id, unit_id) in targets,
            }
        )
    return references
