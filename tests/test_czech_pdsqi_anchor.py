"""The PDSQI human anchor: three numbers where a rate alone would mislead.

PDSQI is a 1-5 scale, so "how often two raters picked the same integer" counts
4-against-5 as badly as 1-against-5. The tests pin all three reported figures and,
more importantly, pin what happens to a question the judge never answered.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import czech_pdsqi_anchor as anchor  # noqa: E402


def key(attribute="useful", system="model-a", session="cz-r-000"):
    return (system, session, attribute)


def test_identical_ratings_agree_exactly():
    human = {key("useful"): 5, key("organized"): 4}
    theirs = {key("useful"): 5, key("organized"): 4}
    out = anchor.agreement(human, theirs)
    assert out["exact"] == 2
    assert out["compared"] == 2
    assert out["mean_signed_difference"] == 0.0


def test_the_signed_difference_says_which_way_the_gap_runs():
    """The number that carries the finding.

    A rate alone would say "they disagreed twice". The sign says the judge was
    higher both times, which is a different fact and the one worth having.
    """
    human = {key("useful"): 3, key("organized"): 4}
    theirs = {key("useful"): 5, key("organized"): 5}
    out = anchor.agreement(human, theirs)
    assert out["mean_signed_difference"] == 1.5
    assert out["judge_higher"] == 2
    assert out["judge_lower"] == 0


def test_a_near_miss_and_a_total_miss_are_told_apart():
    human = {key("useful"): 4, key("organized"): 1}
    theirs = {key("useful"): 5, key("organized"): 5}
    out = anchor.agreement(human, theirs)
    assert out["exact"] == 0
    assert out["within_one"] == 1


def test_a_question_the_judge_did_not_answer_leaves_the_denominator():
    """Never a disagreement, never an agreement.

    Counting it against the judge would punish a cache miss; counting it for the
    judge would invent a measurement nobody made.
    """
    human = {key("useful"): 5, key("organized"): 5}
    theirs = {key("useful"): 5, key("organized"): None}
    out = anchor.agreement(human, theirs)
    assert out["compared"] == 1
    assert out["unanswered"] == 1
    assert out["exact_rate"] == 1.0


def test_a_question_missing_from_the_judge_entirely_is_also_unanswered():
    human = {key("useful"): 5, key("organized"): 5}
    out = anchor.agreement(human, {key("useful"): 5})
    assert out["unanswered"] == 1
    assert out["compared"] == 1


def test_nothing_comparable_reports_no_rate_rather_than_zero():
    out = anchor.agreement({key("useful"): 5}, {key("useful"): None})
    assert out["compared"] == 0
    assert "exact_rate" not in out


def test_figures_are_reported_per_attribute_as_well_as_overall():
    human = {key("useful"): 3, key("organized"): 5}
    theirs = {key("useful"): 5, key("organized"): 5}
    out = anchor.agreement(human, theirs)
    assert out["attributes"]["useful"]["mean_signed_difference"] == 2.0
    assert out["attributes"]["organized"]["mean_signed_difference"] == 0.0


def test_the_questions_asked_are_read_back_not_divided_away(tmp_path):
    """The sheet is half finished, and that is a fact about the instrument.

    Dividing by the number of answers rather than the number of questions would
    turn "he stopped after five notes because the questions did not fit" into a
    complete measurement.
    """
    path = tmp_path / "answers.json"
    path.write_text(
        json.dumps(
            {
                "answers": [{"system": "m", "session": "s", "attribute": "useful", "rating": 5}],
                "of": 30,
            }
        ),
        encoding="utf-8",
    )
    human, asked = anchor.read_answers(path)
    assert asked == 30
    assert len(human) == 1


def test_the_attributes_come_from_the_form_rather_than_being_retyped():
    """Retyping them here would let the form and this reader drift apart."""
    assert anchor.asked_attributes() == ("useful", "organized", "synthesized")


def test_the_ceiling_refuses_to_be_read_as_an_accuracy():
    assert "not an accuracy" in anchor.CEILING
    assert "one rater" in anchor.CEILING
