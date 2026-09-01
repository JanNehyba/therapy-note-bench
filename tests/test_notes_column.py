"""The Notes column counted notes the figures beside it do not rest on.

A note the judge began and returned with part of the protocol unanswered is left
out of the average -- correctly, because averaging it over a smaller denominator
would publish a measurement of a note nobody finished reading. It was then
counted in the one column a reader checks the average against: eighteen of the
nineteen rows on the published gemini table said 50/50 while their figures came
from between 44 and 49 notes.

Two failures, not one. The cell did not say it, and `coverageVaries` -- which
decides whether the column is drawn at all -- did not look at it, so a table
where every row wrote every note and the scores rested on different numbers of
them hid the column entirely.
"""

from __future__ import annotations

from pathlib import Path

from tests.test_page_runs import _flat, _judges_payload, _row, _run
from tnb import judge, report


def _drawn(tmp_path: Path, *rows) -> str:
    data = report.build(list(rows))
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = _judges_payload()
    return _flat(_run(report.render_page(data), tmp_path, panel="table-host"))


def test_the_column_says_how_many_notes_the_score_rests_on(tmp_path):
    drawn = _drawn(
        tmp_path,
        _row("kimi-k3", judge.DEFAULT_MODEL, 0.55, n_sessions_partial=6),
        _row("gemma4", judge.DEFAULT_MODEL, 0.45, n_sessions_partial=1),
    )

    assert "44 behind the score" in drawn, (
        "the row wrote 50 of 50 notes and its figures come from 44 of them; the column "
        "prints the first number and nothing else"
    )
    assert "49 behind the score" in drawn


def test_the_column_is_drawn_when_that_is_the_only_thing_that_differs(tmp_path):
    """Every row wrote every note. The denominators still differ."""
    drawn = _drawn(
        tmp_path,
        _row("kimi-k3", judge.DEFAULT_MODEL, 0.55, n_sessions_partial=6),
        _row("gemma4", judge.DEFAULT_MODEL, 0.45, n_sessions_partial=0),
    )

    assert "Notes" in drawn, (
        "the column was hidden as uninformative on the one table where the number it "
        "carries is the only thing separating the rows"
    )
    assert "44 behind the score" in drawn


def test_a_table_where_every_row_rests_on_everything_says_nothing(tmp_path):
    """No line where there is no gap: a repeated 50/50 is not worth a second row of text."""
    drawn = _drawn(
        tmp_path,
        _row("kimi-k3", judge.DEFAULT_MODEL, 0.55),
        _row("gemma4", judge.DEFAULT_MODEL, 0.45),
    )
    assert "behind the score" not in drawn, "a gap was announced where there is none"


def test_the_gap_is_not_drawn_as_the_model_s_failure(tmp_path):
    """The counter beside a model's name is read as an accusation.

    A part-answered protocol is the judge's doing. The generation failures carry
    the warning colour; this must not, or a model is marked for something that
    happened after it had written every note it was asked for.
    """
    # Two rows: the column exists only where the rows differ, which is the
    # same rule that hid it before.
    drawn = _drawn(
        tmp_path,
        _row("kimi-k3", judge.DEFAULT_MODEL, 0.55, n_sessions_partial=6),
        _row("gemma4", judge.DEFAULT_MODEL, 0.45),
    )
    where = drawn.index("44 behind the score")
    cell = drawn[max(0, where - 200) : where]
    assert 'class="short"' not in cell, "the judge's unfinished protocol is drawn as a fault"
    assert 'class="pending-mark"' in cell
