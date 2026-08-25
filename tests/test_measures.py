"""Every number that is produced is displayed, and every number says its scale.

These exist because of a bug nothing caught. `aggregate` stored a measure under
``likert_faithfulness`` while the headline and the table column called it
``faithfulness``. Python does not mind a key that never matches, the browser
renders it as an em dash, and the suite stayed green: a value was computed,
written to disk, and silently dropped between the scorer and the reader.

So these tests do not check a number. They check the joins — that the names a
scorer writes and the names a view reads are the same set, that nothing on the
page is a bare figure with no stated range, and that what the table says it is
ordered by is what it is actually ordered by.
"""

from __future__ import annotations

import pytest

from tnb import report, results
from tnb.scoring import tneval


def _tneval_scores(note: dict, transcript: str) -> tneval.Scores:
    """Every question the protocol asks, answered, and scored the way a run does.

    The tasks are passed to `aggregate` as well as used to build the answers.
    Without them conciseness has no denominator -- the note text is what says
    how many sentence questions there should have been -- and the scorer now
    declines to publish a mean over however many happened to arrive.
    """
    tasks = tneval.build_tasks(note, transcript)
    answers = {task.unit: ("Yes" if task.kind.startswith("rubric") else "4") for task in tasks}
    return tneval.aggregate(answers, tasks)


NOTE = {
    "subjective": "The client reports drinking most evenings. She feels guilty about it.",
    "objective": "Cooperative and oriented. Speech normal.",
    "assessment": "Alcohol use at a risky level. Motivation is ambivalent.",
    "plan": "Agreed to cut down to three evenings. Review at the next session.",
}


def test_every_measure_a_scorer_produces_is_either_displayed_or_declared_internal():
    """The join that would have caught the original bug.

    A key written into ``by_section`` must be a column on the page or on the
    scorer's explicit internal list. A third possibility -- produced, stored, and
    read by nobody -- is the bug, and this is the assertion that names it.
    """
    scores = _tneval_scores(NOTE, "therapist: hello")
    produced = {key for values in scores.by_section.values() for key in values}
    produced |= set(scores.headline)

    displayed = {key for key, _ in report.COLUMNS[results.TRACK_TNEVAL]}
    accounted = displayed | set(tneval.INTERNAL_MEASURES)

    assert produced <= accounted, (
        f"produced but never read: {sorted(produced - accounted)} -- either put it on "
        f"the page or add it to tneval.INTERNAL_MEASURES so the omission is on purpose"
    )


def test_every_displayed_column_is_actually_produced():
    """The other direction: a column with no producer renders as a dash forever."""
    scores = _tneval_scores(NOTE, "therapist: hello")
    produced = set(scores.headline)
    displayed = {key for key, _ in report.COLUMNS[results.TRACK_TNEVAL]}

    assert displayed <= produced, f"columns nothing computes: {sorted(displayed - produced)}"


def test_faithfulness_is_named_the_same_in_the_headline_and_in_every_section():
    """The original defect, stated directly."""
    scores = _tneval_scores(NOTE, "therapist: hello")

    assert "faithfulness" in scores.headline
    for section, values in scores.by_section.items():
        assert "faithfulness" in values, f"{section} has no faithfulness under that name"
    assert not any("likert_faithfulness" in values for values in scores.by_section.values()), (
        "one number must not be stored under two names: results/ is append-only"
    )


@pytest.mark.parametrize("track", sorted(report.COLUMNS))
def test_every_column_states_its_range_and_what_it_counts(track):
    """No bare number. A reader seeing 0.65 beside 4.98 must be told why."""
    for key, _digits in report.COLUMNS[track]:
        meta = report.column_meta(track, key)
        assert meta["scale"], f"{track}.{key} has no scale"
        assert "-" in meta["scale"], f"{track}.{key} scale {meta['scale']!r} is not a range"
        assert len(meta["definition"]) > 40, f"{track}.{key} has no usable definition"


def test_a_column_with_no_documented_scale_fails_loudly():
    """The failure mode must be an error, not a blank that ships to the page."""
    with pytest.raises(KeyError, match="no entry in the measure table"):
        report.column_meta(results.TRACK_TNEVAL, "a_measure_nobody_documented")


@pytest.mark.parametrize("track", sorted(report.COLUMNS))
def test_the_table_is_ordered_by_the_measure_it_says_it_is_ordered_by(track):
    """One declaration, not three. The claim and the sort read the same constant."""
    declared = report.RANKING_MEASURES[track]
    if declared is None:
        return  # iCARE declines to rank; the sort falls back and claims nothing

    flagged = [key for key, _ in report.COLUMNS[track] if report.column_meta(track, key)["ranking"]]
    assert flagged == [declared]

    def row(system_id: str, value: float) -> results.Row:
        return results.Row(
            track=track,
            system_id=system_id,
            system_type="model",
            n_sessions_attempted=1,
            metrics=results.Metrics(headline={declared: value}),
        )

    better, worse = row("better", 0.9), row("worse", 0.1)
    ordered = sorted([worse, better], key=lambda row: report._sort_key(row, track))
    assert [row.system_id for row in ordered] == ["better", "worse"]


def test_the_icare_track_does_not_claim_a_ranking():
    """Its columns disagree on purpose; naming one the ranking would hide that."""
    assert report.RANKING_MEASURES[results.TRACK_ICARE] is None
    assert not any(
        report.column_meta(results.TRACK_ICARE, key)["ranking"]
        for key, _ in report.COLUMNS[results.TRACK_ICARE]
    )


def test_a_row_written_under_the_old_measure_name_is_repaired_on_read():
    """`results/` is append-only, so a rename has to happen on the way in.

    Without this the 41 rows already on disk keep the old key while the view
    looks up the new one, and the page prints a dash over a number in the file.
    """
    legacy = {
        "track": results.TRACK_TNEVAL,
        "system_id": "written-before-the-rename",
        "system_type": "model",
        "n_sessions_attempted": 1,
        "metrics": {
            "headline": {"likert_faithfulness": 4.5},
            "by_section": {"plan": {"completeness": 0.5, "likert_faithfulness": 5.0}},
        },
    }

    row = results.from_dict(legacy)

    assert row.metrics.headline == {"faithfulness": 4.5}
    assert row.metrics.by_section["plan"] == {"completeness": 0.5, "faithfulness": 5.0}


def test_a_row_written_after_the_rename_is_left_alone():
    """The repair must not overwrite a value a newer row already carries."""
    current = {
        "track": results.TRACK_TNEVAL,
        "system_id": "written-after",
        "system_type": "model",
        "n_sessions_attempted": 1,
        "metrics": {"by_section": {"plan": {"faithfulness": 4.0}}},
    }

    row = results.from_dict(current)

    assert row.metrics.by_section["plan"] == {"faithfulness": 4.0}


def test_conciseness_is_not_published_when_its_denominator_is_unknown():
    """How many sentence questions there should have been is a fact about the note.

    Without the note text there is no denominator, and the mean of whatever
    answers arrived is not conciseness: one "yes" of four sentences read as a
    perfect 1.00 with nothing marking it. Not knowing the denominator is not the
    same as the denominator being the numerator's length.
    """
    tasks = tneval.build_tasks(NOTE, "therapist: hello")
    answers = {task.unit: ("Yes" if task.kind.startswith("rubric") else "4") for task in tasks}

    with_note = tneval.aggregate(answers, tasks)
    without = tneval.aggregate(answers)

    assert with_note.headline["conciseness"] == 1.0
    assert "conciseness" not in without.headline
    assert without.headline["completeness"] == 1.0, "completeness needs no note text"
