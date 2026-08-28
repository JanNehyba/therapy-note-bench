"""The "what it took" table: how many notes, and how many calls they cost.

Offline. Every number here is computed from rows written in this file, which is
the point -- the section exists so the scale of the run cannot be typed into a
sentence and then quietly go stale.
"""

from __future__ import annotations

import sys

from tnb import results
from tnb.config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tools"))

import czech_brief  # noqa: E402


def _row(**over):
    """A minimal scored Czech row."""
    fields = {
        "track": results.TRACK_CZECH_REAL,
        "system_id": "a-model",
        "system_type": "model",
        "system_label": "a-model",
        "provider": "einfra",
        "harness_version": "0.6.0",
        "prompt_version": "czech-soap-v1",
        "judge_model": "gemini-3.1-pro-preview",
        "judge_prompt_version": "czech-criteria-v2",
        "judge_settings": {"model": "gemini-3.1-pro-preview", "thinking_budget": 2048},
        "n_sessions_attempted": 10,
        "n_sessions_generated": 10,
        "n_sessions_scored": 10,
        "metrics": results.Metrics(headline={"diacritics": 1.0}),
    }
    fields.update(over)
    return results.Row(**fields)


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


def test_a_superseded_rubric_does_not_double_the_notes_written():
    """The bug this caught: with two rubric versions and two judges in the
    file, every note was counted four times and the document said 424 notes
    had been written when 212 had. The count is per drawn group, per judge."""
    rows = [
        _row(judge_model=judge, judge_prompt_version=version, scored_at=at)
        for judge in ("gemini-3.1-pro-preview", "gpt-5.6-terra")
        for version, at in (
            ("czech-criteria-v1", "2026-08-28T10:00:00Z"),
            ("czech-criteria-v2", "2026-08-28T12:00:00Z"),
        )
    ]

    assert "10 notes in all" in czech_brief._scale(rows)


def test_the_sentence_about_deepsy_waits_for_the_deepsy_rows():
    """It explains why two rows below cost three times the calls. On a run
    where those rows have not been scored, it is a puzzle instead."""
    without = czech_brief._scale([_row()])
    with_it = czech_brief._scale(
        [
            _row(),
            _row(
                track=results.TRACK_DEEPSY_REAL,
                prompt_version="deepsy-3section-v1",
                judge_prompt_version="czech-criteria-v2",
            ),
        ]
    )

    assert "three answers rather than one" not in without
    assert "three answers rather than one" in with_it
