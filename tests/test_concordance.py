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


def test_a_measure_no_judge_decides_is_left_out_of_the_agreement():
    """On the iCARE track four of five columns are computed from the note and
    the expert note alone, so they are byte-identical under every judge.
    Reporting "the judges agree perfectly on ROUGE-L" would dress a tautology
    as a finding, and a reader has no way to tell it from a real one."""
    automatic = 0.42
    rows = _panel(
        {
            A: {
                "x": {"rouge_l": automatic, "trace": 5.0},
                "y": {"rouge_l": automatic, "trace": 3.0},
            },
            B: {
                "x": {"rouge_l": automatic, "trace": 3.0},
                "y": {"rouge_l": automatic, "trace": 5.0},
            },
        }
    )
    for row in rows:
        object.__setattr__(row, "track", results.TRACK_ICARE)

    result = concordance.compare(
        rows,
        results.TRACK_ICARE,
        ["rouge_l", "trace"],
        judge_measures=("trace",),
    )

    assert [m.measure for m in result.measures] == ["trace"]
    assert result.judge_measures == ("trace",)


def test_the_columns_are_still_compared_with_each_other_across_all_of_them():
    """A tension is a question about the columns, not about the judges, so an
    automatic metric belongs in it -- and on the iCARE track "does ROUGE-L
    predict the judge's rating" is the source paper's own finding."""
    rows = _panel(
        {
            A: {
                "x": {"rouge_l": 0.9, "trace": 1.0},
                "y": {"rouge_l": 0.5, "trace": 3.0},
                "z": {"rouge_l": 0.1, "trace": 5.0},
            },
            B: {
                "x": {"rouge_l": 0.9, "trace": 1.0},
                "y": {"rouge_l": 0.5, "trace": 3.0},
                "z": {"rouge_l": 0.1, "trace": 5.0},
            },
        }
    )
    for row in rows:
        object.__setattr__(row, "track", results.TRACK_ICARE)

    result = concordance.compare(
        rows, results.TRACK_ICARE, ["rouge_l", "trace"], judge_measures=("trace",)
    )

    tension = next(t for t in result.tensions if {t.first, t.second} == {"rouge_l", "trace"})
    assert all(rho == pytest.approx(-1.0) for rho in tension.rho_by_judge.values())
    assert tension.agrees is False


def test_one_judged_measure_is_not_described_as_the_best_and_the_worst():
    """The iCARE track has exactly one: TRACE. Naming it twice reads as two
    findings and is one."""
    rows = _panel(
        {
            A: {"x": {"trace": 5.0}, "y": {"trace": 3.0}, "z": {"trace": 1.0}},
            B: {"x": {"trace": 4.0}, "y": {"trace": 3.5}, "z": {"trace": 1.0}},
        }
    )
    for row in rows:
        object.__setattr__(row, "track", results.TRACK_ICARE)

    sentence = concordance.describe(
        concordance.compare(rows, results.TRACK_ICARE, ["trace"], judge_measures=("trace",))
    )

    assert sentence.count("trace") == 1
    assert "agree least" not in sentence


def test_two_harness_versions_of_one_system_are_refused_rather_than_merged():
    """`results/` is append-only, so a system re-scored under a redefined
    measure is in the file twice. A dictionary keyed on the system keeps
    whichever came last, which would compare one judge's new ROUGE-L with the
    other's old one and publish the difference as a disagreement.

    Measured on the live file when this was written: 148 rows after `latest()`
    and 100 after the harness filter, with every iCARE system doubled.
    """
    rows = _panel({A: {"x": _flat(0.9)}, B: {"x": _flat(0.5)}})
    stale = _row("x", A, completeness=0.1, conciseness=0.1, faithfulness=1.0)
    object.__setattr__(stale, "harness_version", "0.1.0")

    with pytest.raises(ValueError, match="appears twice"):
        concordance.compare([*rows, stale], results.TRACK_TNEVAL, MEASURES)


def test_the_report_hands_it_only_the_rows_a_table_would_draw():
    """The resolution lives in one place and everything reading rows uses it."""
    from tnb import report

    rows = _panel({A: {"x": _flat(0.9), "y": _flat(0.5)}, B: {"x": _flat(0.8), "y": _flat(0.4)}})
    stale = [_row(s, j, **_flat(0.01)) for s in ("x", "y") for j in (A, B)]
    for row in stale:
        object.__setattr__(row, "harness_version", "0.1.0")

    drawn = report.current_rows([*rows, *stale])
    result = concordance.compare(drawn, results.TRACK_TNEVAL, MEASURES)

    assert result is not None
    assert result.n_systems == 2


def test_both_judges_rank_the_same_field():
    """A position out of nineteen and a position out of sixteen are not
    comparable, and a judge part-way through a run has the smaller table -- so
    ranking each judge's whole set would report the most movement exactly when
    a reader is most likely to be watching."""
    rows = _panel(
        {
            A: {"x": _flat(0.9), "y": _flat(0.5), "z": _flat(0.1)},
            # Same order for the two they share, plus one this judge alone has
            # and which sits between them.
            B: {"x": _flat(0.9), "extra": _flat(0.7), "y": _flat(0.5)},
        }
    )

    result = concordance.compare(rows, results.TRACK_TNEVAL, MEASURES)

    assert result.n_systems == 2, "x and y"
    completeness = next(m for m in result.measures if m.measure == "completeness")
    assert completeness.moved == 0, "`extra` must not push `y` down a place"
