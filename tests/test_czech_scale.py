"""What a note cost to ask for: one call, or one call per section.

The briefing used to print a table of notes and calls per track, and this file
covered it. That table is gone -- the "three views of one question" chapter
counts the notes and the calls where a reader has a reason to care, which is
when deciding whether a whole view is worth keeping -- and what survives of it
is `czech_brief._calls`, the one number in it that is not one per note.

Offline. Both figures are read off the task definition rather than typed, which
is the point: a fourth Deepsy section would make the sentence in that chapter
wrong, and nothing else in the repository would say so.
"""

from __future__ import annotations

import sys

from tnb import results
from tnb.config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tools"))

import czech_brief  # noqa: E402


def test_a_deepsy_note_costs_one_call_per_section():
    """220 notes are 660 calls because each section is asked for separately.
    Read off the task rather than typed: a fourth section would make the
    sentence in this document wrong and nothing would say so."""
    assert czech_brief._calls(results.TRACK_CZECH_REAL, 220) == "220"
    assert czech_brief._calls(results.TRACK_DEEPSY_REAL, 220) == "660"


def test_a_track_that_generated_nothing_says_so():
    """PDSQI rates notes the Czech tracks wrote. A zero there would read as "no
    calls were needed", and a number as "these notes were written twice"."""
    assert "&mdash;" in czech_brief._calls(results.TRACK_CZECH_REAL_PDSQI, 220)
