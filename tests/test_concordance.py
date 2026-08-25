"""Reading two judges' tables together: what that can and cannot say."""

from __future__ import annotations

import pytest

from tnb import results
from tnb.results import Metrics, Row
from tnb.scoring import concordance

MEASURES = ["completeness", "conciseness", "faithfulness"]


def _row(system: str, judge_model: str, **headline) -> Row:
    return Row(
        track=results.TRACK_TNEVAL,
        system_id=system,
        system_type="model",
        provider="einfra",
        prompt_version="tneval-soap-v1",
        judge_model=judge_model,
        judge_prompt_version="tneval-rubric-v1",
        n_sessions_attempted=50,
        n_sessions_generated=50,
        n_sessions_scored=50,
        metrics=Metrics(headline=dict(headline)),
    )


def _panel(scores: dict[str, dict[str, dict[str, float]]]) -> list[Row]:
    return [
        _row(system, judge_model, **values)
        for judge_model, systems in scores.items()
        for system, values in systems.items()
    ]


A = "gemini-3.1-pro-preview"
B = "gpt-5.6-terra"


def _flat(value: float) -> dict[str, float]:
    return {"completeness": value, "conciseness": value, "faithfulness": value}


def test_two_judges_that_rank_identically_show_nobody_moving():
    rows = _panel(
        {
            A: {"x": _flat(0.9), "y": _flat(0.5), "z": _flat(0.1)},
            # Stricter across the board, same order. A uniform offset is a
            # difference in strictness, not in judgement.
            B: {"x": _flat(0.7), "y": _flat(0.3), "z": _flat(0.05)},
        }
    )

    result = concordance.compare(rows, results.TRACK_TNEVAL, MEASURES)

    assert all(measure.rho == pytest.approx(1.0) for measure in result.measures)
    assert all(measure.moved == 0 for measure in result.measures)
    assert all(measure.furthest is None for measure in result.measures)


def test_the_system_that_moved_furthest_is_named_with_both_positions():
    """A rho alone cannot separate "one system moved six places" from
    "everybody moved one", and those support different claims."""
    # x > y > z under one judge, z > x > y under the other: z moves two places
    # and the other two move one each, so the furthest is not a tie.
    rows = _panel(
        {
            A: {"x": _flat(0.9), "y": _flat(0.5), "z": _flat(0.1)},
            B: {"x": _flat(0.5), "y": _flat(0.1), "z": _flat(0.9)},
        }
    )

    result = concordance.compare(rows, results.TRACK_TNEVAL, MEASURES)
    completeness = next(m for m in result.measures if m.measure == "completeness")

    assert completeness.moved == 3
    assert completeness.stable == 0
    assert completeness.furthest == ("z", 3, 1)


def test_a_system_better_on_everything_under_both_judges_dominates():
    """The one claim that survives any weighting a reader might apply, which is
    why it is the only claim this page makes about who is better."""
    rows = _panel(
        {A: {"good": _flat(0.9), "bad": _flat(0.1)}, B: {"good": _flat(0.8), "bad": _flat(0.2)}}
    )

    result = concordance.compare(rows, results.TRACK_TNEVAL, MEASURES)

    assert [(d.system, d.beats) for d in result.dominance] == [("good", ["bad"])]
    assert result.undominated == ["good"]


def test_a_system_the_two_judges_disagree_about_dominates_nobody():
    """Better under one judge and worse under the other is not better."""
    rows = _panel(
        {
            A: {"one": _flat(0.9), "two": _flat(0.1)},
            B: {"one": _flat(0.1), "two": _flat(0.9)},
        }
    )

    result = concordance.compare(rows, results.TRACK_TNEVAL, MEASURES)

    assert result.dominance == []
    assert result.undominated == ["one", "two"]


def test_winning_on_two_measures_and_losing_on_the_third_is_not_dominance():
    """Calling that a win means weighting the measures, and weighting them is a
    clinical decision rather than a measurement."""
    rows = _panel(
        {
            A: {
                "thorough": {"completeness": 0.9, "conciseness": 0.9, "faithfulness": 3.0},
                "careful": {"completeness": 0.5, "conciseness": 0.5, "faithfulness": 5.0},
            },
            B: {
                "thorough": {"completeness": 0.8, "conciseness": 0.8, "faithfulness": 3.2},
                "careful": {"completeness": 0.4, "conciseness": 0.4, "faithfulness": 4.9},
            },
        }
    )

    result = concordance.compare(rows, results.TRACK_TNEVAL, MEASURES)

    assert result.dominance == []
    assert result.undominated == ["careful", "thorough"]


def test_a_measure_missing_for_one_system_blocks_the_claim_rather_than_helping_it():
    """An absent number is not a low one -- the same rule as everywhere else."""
    rows = _panel({A: {"whole": _flat(0.9)}, B: {"whole": _flat(0.8)}})
    rows += [
        _row("partial", A, completeness=0.1, conciseness=0.1),
        _row("partial", B, completeness=0.2, conciseness=0.2),
    ]

    result = concordance.compare(rows, results.TRACK_TNEVAL, MEASURES)

    assert result.dominance == [], "faithfulness is unknown for `partial`"
    assert sorted(result.undominated) == ["partial", "whole"]


def test_the_panel_is_named_rather_than_whichever_two_are_present():
    """`results/` also holds a full pass by a judge that was tried and not
    chosen. Picking a pair out of three by iteration order would be a choice
    made silently."""
    rows = _panel(
        {
            A: {"x": _flat(0.9), "y": _flat(0.5)},
            B: {"x": _flat(0.8), "y": _flat(0.4)},
            "gemini-2.5-pro": {"x": _flat(0.1), "y": _flat(0.99)},
        }
    )

    result = concordance.compare(rows, results.TRACK_TNEVAL, MEASURES)

    assert {result.judge_a, result.judge_b} == {A, B}
    assert all(measure.rho == pytest.approx(1.0) for measure in result.measures), (
        "the third judge is not in it"
    )


def test_one_judge_missing_reports_nothing():
    rows = _panel({A: {"x": _flat(0.9), "y": _flat(0.5)}})

    assert concordance.compare(rows, results.TRACK_TNEVAL, MEASURES) is None


def test_scores_that_print_the_same_are_not_ranked_against_each_other():
    """The table shows three decimals. Ordering two systems by the fourth
    invents a difference the reader cannot see and cannot check."""
    rows = _panel(
        {
            A: {"x": _flat(0.5000), "y": _flat(0.50002)},
            B: {"x": _flat(0.50002), "y": _flat(0.5000)},
        }
    )

    result = concordance.compare(rows, results.TRACK_TNEVAL, MEASURES)

    assert all(measure.moved == 0 for measure in result.measures)
    assert result.dominance == [], "neither is better than the other"


def test_the_summary_says_what_the_tables_cannot_do():
    rows = _panel(
        {
            A: {"x": _flat(0.9), "y": _flat(0.5), "z": _flat(0.1)},
            B: {"x": _flat(0.5), "y": _flat(0.1), "z": _flat(0.9)},
        }
    )

    sentence = concordance.describe(concordance.compare(rows, results.TRACK_TNEVAL, MEASURES))

    assert "ninth" in sentence and "tenth" in sentence
    assert "beaten outright by nobody" in sentence


def test_two_measures_that_do_not_predict_each_other_are_reported_as_such():
    """The reason the ranking column is not "quality", stated as a measurement.

    A model that answers every question satisfies more criteria and invents
    more. Where the two columns behave that way, collapsing them into one
    number means deciding which matters, and that is a clinical decision.
    """
    rows = _panel(
        {
            A: {
                "eager": {"completeness": 0.9, "conciseness": 0.5, "faithfulness": 3.0},
                "careful": {"completeness": 0.5, "conciseness": 0.5, "faithfulness": 5.0},
                "middling": {"completeness": 0.7, "conciseness": 0.5, "faithfulness": 4.0},
            },
            B: {
                "eager": {"completeness": 0.8, "conciseness": 0.5, "faithfulness": 3.1},
                "careful": {"completeness": 0.4, "conciseness": 0.5, "faithfulness": 4.9},
                "middling": {"completeness": 0.6, "conciseness": 0.5, "faithfulness": 4.0},
            },
        }
    )

    result = concordance.compare(
        rows, results.TRACK_TNEVAL, MEASURES, ranking_measure="completeness"
    )
    tension = next(
        t for t in result.tensions if {t.first, t.second} == {"completeness", "faithfulness"}
    )

    assert all(rho == pytest.approx(-1.0) for rho in tension.rho_by_judge.values())
    assert tension.agrees is False
    assert "faithfulness" in concordance.describe(result)


def test_a_tension_the_two_judges_read_differently_is_not_resolved_for_the_reader():
    """Picking the judge that tells the better story is the one thing this
    repository exists not to do. Measured live: completeness and faithfulness
    correlate +0.72 under one judge and +0.04 under the other."""
    rows = _panel(
        {
            A: {
                "x": {"completeness": 0.9, "conciseness": 0.5, "faithfulness": 5.0},
                "y": {"completeness": 0.5, "conciseness": 0.5, "faithfulness": 3.0},
                "z": {"completeness": 0.1, "conciseness": 0.5, "faithfulness": 1.0},
            },
            B: {
                "x": {"completeness": 0.9, "conciseness": 0.5, "faithfulness": 1.0},
                "y": {"completeness": 0.5, "conciseness": 0.5, "faithfulness": 3.0},
                "z": {"completeness": 0.1, "conciseness": 0.5, "faithfulness": 5.0},
            },
        }
    )

    result = concordance.compare(
        rows, results.TRACK_TNEVAL, MEASURES, ranking_measure="completeness"
    )
    sentence = concordance.describe(result)

    assert "different things to the two judges" in sentence
    assert "neither reading is this benchmark's answer" in sentence


def test_measures_that_do_agree_are_not_reported_as_a_tension():
    """A panel that flagged every pair would say nothing by saying everything."""
    rows = _panel(
        {
            A: {"x": _flat(0.9), "y": _flat(0.5), "z": _flat(0.1)},
            B: {"x": _flat(0.8), "y": _flat(0.4), "z": _flat(0.05)},
        }
    )

    result = concordance.compare(
        rows, results.TRACK_TNEVAL, MEASURES, ranking_measure="completeness"
    )

    assert all(t.agrees for t in result.tensions)
    assert "Ordering by" not in concordance.describe(result)
