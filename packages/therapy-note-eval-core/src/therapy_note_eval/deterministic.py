"""Checks of explicit, mechanically decidable note requirements."""

from .schema import MeasurementSpec, Note


def checks(note: Note) -> dict[str, bool | None]:
    # Only explicitly requested exact headings are mandatory. Do not infer a
    # jurisdiction's documentation requirements from SOAP/DAP/BIRP labels.
    headings = {
        line.strip().lstrip("# ").strip("*: ").casefold() for line in note.text.splitlines()
    }
    return {
        "word_limit": len(note.text.split()) <= note.spec.word_limit,
        "required_headings": all(h.casefold() in headings for h in note.spec.required_headings)
        if note.spec.required_headings
        else None,
    }


def violations(note: Note, items: tuple[MeasurementSpec, ...]) -> dict[str, list[str]]:
    outcomes = checks(note)
    return {
        m.id: [k for k in m.deterministic_checks if outcomes[k] is False]
        for m in items
        if any(outcomes[k] is False for k in m.deterministic_checks)
    }
