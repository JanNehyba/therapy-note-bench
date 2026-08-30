"""The arithmetic behind the boxes that close each chapter of the Czech briefing.

Offline. The cells here are dictionaries in the shape `czech_brief._cells`
returns, so nothing is read from `local/` and nothing is asked of a judge.

Each box makes one claim per sentence about two tables read under two judges,
and every one of those claims can be false in a way the sentence cannot show:
a column that is flat is not a column the judges disagree about, and a column
lowest on average is not a column every model is lowest on.
"""

from __future__ import annotations

import sys

from tnb import results
from tnb.config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tools"))

import czech_brief  # noqa: E402

TRACKS = (results.TRACK_CZECH_REAL_PDSQI, results.TRACK_CZECH_TRANSLATED_PDSQI)
JUDGES = ("judge-a", "judge-b")


def _cells(**by_key) -> dict:
    """One cell per (track, judge), each column given as (real, translated)."""
    out: dict = {}
    for index, track in enumerate(TRACKS):
        for judge in JUDGES:
            out[(track, judge)] = {
                key: halves[judge][index] for key, halves in by_key.items() if judge in halves
            }
    return out


def test_a_column_flat_under_both_judges_is_not_a_column_they_disagree_about():
    """The defect this file was opened for. `synthesized` is exactly 5.00 on
    both halves under both judges, and the box said the two judges "do not both
    point the same way" on it -- three lines under its own paragraph saying
    every model scores 5.00 on it in all four tables. They point the same way,
    at nothing."""
    cells = _cells(
        synthesized={"judge-a": (5.0, 5.0), "judge-b": (5.0, 5.0)},
        comprehensible={"judge-a": (4.0, 3.93), "judge-b": (3.9, 3.98)},
        useful={"judge-a": (4.0, 4.0), "judge-b": (4.0, 4.2)},
    )

    found = czech_brief._halves_split(cells, TRACKS, ["synthesized", "comprehensible", "useful"])

    assert found.flat_both == ["synthesized"]
    assert found.split == ["comprehensible"], "one judge each way is the only real split"
    assert found.flat_one == ["useful"], "one judge seeing nothing is not a contradiction"


def test_a_column_both_judges_put_on_one_half_is_on_that_half():
    cells = _cells(
        accurate={"judge-a": (3.0, 4.0), "judge-b": (3.2, 3.9)},
        thorough={"judge-a": (4.0, 3.0), "judge-b": (3.9, 3.2)},
    )

    found = czech_brief._halves_split(cells, TRACKS, ["accurate", "thorough"])

    assert found.ahead_other == ["accurate"]
    assert found.ahead_real == ["thorough"]
    assert not found.split and not found.flat_both and not found.flat_one


def test_a_split_wins_over_a_judge_who_sees_nothing():
    """With three judges a column can be both. Two pointing opposite ways is
    the stronger fact and the one the document reports."""
    cells = _cells(
        useful={"judge-a": (4.0, 4.4), "judge-b": (4.0, 3.6)},
    )
    cells[(TRACKS[0], "judge-c")] = {"useful": 4.0}
    cells[(TRACKS[1], "judge-c")] = {"useful": 4.0}

    found = czech_brief._halves_split(cells, TRACKS, ["useful"])

    assert found.split == ["useful"]
    assert not found.flat_one and not found.flat_both


def test_a_difference_smaller_than_the_printed_digit_is_not_a_difference():
    """Two columns of 5.00 are not the translated half winning by a rounding
    error a reader cannot see in the table."""
    cells = _cells(useful={"judge-a": (5.0, 5.001), "judge-b": (5.0, 4.999)})

    found = czech_brief._halves_split(cells, TRACKS, ["useful"])

    assert found.flat_both == ["useful"]
