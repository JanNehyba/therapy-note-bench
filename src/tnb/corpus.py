"""What the corpora actually contain, measured rather than described.

A benchmark that reports how well models fill a form owes its reader one fact
before any score: **how much of that form the human experts filled in.** On the
iHOPE side the answer is 60% — the rest of every gold note is `Nil`, because a
published counselling video has no hospital id and no referring clinician.

Sections where the experts wrote `Nil` almost every time cannot separate a good
model from a bad one; a model scores on them by staying quiet. Sections the
experts filled in every time are where the track carries signal. The page shows
both, so nobody reads a high iCARE score as "writes a good clinical note".

The profile is computed from the fetched corpus when it is present and cached to
``docs/corpus-profile.json``, so the published page keeps the figures even where
the corpus is not downloaded — a run in CI, or a reader with no token.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from tnb.config import REPO_ROOT
from tnb.datasets.base import CACHE_DIR
from tnb.tasks import icare

PROFILE_PATH = REPO_ROOT / "docs" / "corpus-profile.json"

#: A gold note joins its 17 fields with this, and labels each one.
FIELD_SEPARATOR = " ; "

#: What the experts wrote when the transcript did not say. The protocol asks for
#: exactly this word, and models are asked for it too.
EMPTY_MARKERS = {"nil", "", "none", "na", "n/a"}


@dataclass(frozen=True)
class SectionFill:
    """How often the experts had anything to write in one field."""

    number: int
    title: str
    filled: int
    total: int
    temporal: bool

    @property
    def rate(self) -> float:
        return self.filled / self.total if self.total else 0.0


def _normalise(text: str) -> str:
    return "".join(char for char in text.lower() if char.isalnum())


def _match_section(label: str) -> int | None:
    """Map a gold note's own label onto one of the 17 fields.

    The labels are hand-written and vary between notes -- extra spaces, dropped
    parentheses -- so this compares on letters only. An ambiguous label is
    counted for nobody: "Psychotherapy type" and "Psychotherapy technique" share
    a long prefix, and a loose match silently credited one field with the
    other's answers.
    """
    key = _normalise(label)
    if not key:
        return None

    titles = [_normalise(title) for title in icare.SECTION_TITLES]
    if key in titles:
        return titles.index(key) + 1

    candidates = [
        index
        for index, title in enumerate(titles, start=1)
        if key.startswith(title) or title.startswith(key)
    ]
    return candidates[0] if len(candidates) == 1 else None


def profile_ihope(path: Path | None = None) -> list[SectionFill] | None:
    """Count, per section, how many expert notes actually say something.

    Returns None when the corpus has not been fetched -- the caller falls back
    to the cached profile rather than publishing zeros.
    """
    path = path or CACHE_DIR / "ihope_test.json"
    if not path.exists():
        return None

    from tnb.datasets import ihope

    sessions = json.loads(path.read_text(encoding="utf-8"))
    filled = dict.fromkeys(range(1, 18), 0)

    for entry in sessions:
        for part in (entry.get("summary") or "").split(FIELD_SEPARATOR):
            label, separator, value = part.partition(":")
            if not separator:
                continue
            number = _match_section(label)
            if number is None:
                continue
            if value.strip().lower() not in EMPTY_MARKERS:
                filled[number] += 1

    # Every note is asked every field. A note that omits the label entirely did
    # not answer it either, so the denominator is the corpus -- counting only
    # the notes that happen to mention a field flattered the sparse ones badly:
    # crisis markers read as 3 of 23 rather than 3 of 40.
    total = dict.fromkeys(range(1, 18), len(sessions))

    return [
        SectionFill(
            number=number,
            title=icare.SECTION_TITLES[number - 1],
            filled=filled[number],
            total=total[number],
            temporal=number in ihope.TEMPORAL_SECTIONS,
        )
        for number in range(1, 18)
    ]


def _lengths(values: list[int]) -> dict:
    """Median and range. Median rather than mean: a 4000-word outlier is real."""
    if not values:
        return {}
    ordered = sorted(values)
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    return {"median": round(median), "min": ordered[0], "max": ordered[-1], "n": len(ordered)}


def profile_datasets() -> dict:
    """Size and shape of both corpora, so a reader knows what was measured on.

    Lengths are in words of transcript, because that is what a model has to read
    and roughly what a session's substance amounts to. Both are missing rather
    than zero when the corpus has not been fetched.
    """
    profile: dict = {}

    tneval_path = CACHE_DIR / "AnnoMI-full.csv"
    if tneval_path.exists():
        from tnb.datasets import tneval

        try:
            sessions = tneval.load()
        except RuntimeError:
            sessions = []
        if sessions:
            profile["tneval"] = {
                "sessions": len(sessions),
                "words": _lengths([session.word_count for session in sessions]),
                "turns": _lengths([len(session.turns) for session in sessions]),
                "note_words": _lengths(
                    [
                        sum(len(text.split()) for text in session.meta["human_note"].values())
                        for session in sessions
                    ]
                ),
            }

    ihope_path = CACHE_DIR / "ihope_test.json"
    if ihope_path.exists():
        from tnb.datasets import ihope

        sessions = ihope.load("test")
        profile["icare"] = {
            "sessions": len(sessions),
            "words": _lengths([session.word_count for session in sessions]),
            "turns": _lengths([len(session.turns) for session in sessions]),
            "note_words": _lengths(
                [len((session.reference or "").split()) for session in sessions]
            ),
        }

    return profile


def build(path: Path | None = None) -> dict | None:
    """The profile as the page consumes it, or None if there is nothing to say."""
    sections = profile_ihope(path)
    if not sections or not any(section.total for section in sections):
        return None

    filled = sum(section.filled for section in sections)
    total = sum(section.total for section in sections)
    return {
        "datasets": profile_datasets(),
        "sessions": max(section.total for section in sections),
        "fields_filled": filled,
        "fields_total": total,
        "fill_rate": round(filled / total, 4) if total else 0.0,
        "sections": [
            {
                "number": section.number,
                "title": section.title,
                "filled": section.filled,
                "total": section.total,
                "rate": round(section.rate, 4),
                "temporal": section.temporal,
            }
            for section in sections
        ],
    }


def load_or_build(docs_dir: Path | None = None) -> dict | None:
    """Recompute from the corpus if it is here; otherwise reuse what was published."""
    path = (docs_dir or PROFILE_PATH.parent) / PROFILE_PATH.name
    fresh = build()
    if fresh is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(fresh, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return fresh
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None
