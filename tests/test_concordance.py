"""Reading two judges' tables together: what that can and cannot say."""

from __future__ import annotations

import pytest

from tnb import results
from tnb.results import Metrics, Row
from tnb.scoring import concordance

#: Each measure with the decimals the leaderboard prints it to -- the same
#: shape `report.COLUMNS` holds, because the panel's claims are made in the
#: units the reader sees. Faithfulness prints two, which is where the old fixed
#: tolerance failed.
MEASURES = [("completeness", 3), ("conciseness", 3), ("faithfulness", 2)]


def _row(system: str, judge_model: str, **headline) -> Row:
    return Row(
        track=results.TRACK_TNEVAL,
        system_id=system,
        system_type="model",
        provider="einfra",
        prompt_version="tneval-soap-v1",
        judge_model=judge_model,
        judge_prompt_version="tneval-rubric-v1",
        # A judged group that does not record its judge's settings is withdrawn
        # rather than drawn, so a fixture without one is not a table.
        judge_settings={"model": judge_model},
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


def test_a_trade_off_between_two_columns_is_reported_as_a_trade_off():
    """The reason the ranking column is not "quality", stated as a measurement.

    A model that answers every question satisfies more criteria and invents
    more. Where the two columns behave that way, collapsing them into one
    number means deciding which matters, and that is a clinical decision.

    **This test asserted the opposite until 2026-09-01**, and the assertion was
    the bug. Its fixture builds a perfect inverse relation -- exactly the
    trade-off the docstring describes -- and then required `agrees` to be
    False, because the test was written against a rule that read a negative
    correlation as no correlation. The page printed "not related" over -0.472.
    A trade-off is a relation; what it is not is agreement about direction, and
    that is a different property.
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
    assert tension.agrees is True, "a perfect inverse relation is a relation"
    assert tension.inverse is True
    sentence = concordance.describe(result)
    assert "orders faithfulness in reverse" in sentence, sentence
    assert "trade-off" in sentence


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
        [("rouge_l", 3), ("trace", 2)],
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
        rows, results.TRACK_ICARE, [("rouge_l", 3), ("trace", 2)], judge_measures=("trace",)
    )

    tension = next(t for t in result.tensions if {t.first, t.second} == {"rouge_l", "trace"})
    assert all(rho == pytest.approx(-1.0) for rho in tension.rho_by_judge.values())
    # ROUGE-L predicting the judge's rating perfectly in reverse is the source
    # paper's finding at its strongest, not the absence of one.
    assert tension.agrees is True
    assert tension.inverse is True


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
        concordance.compare(rows, results.TRACK_ICARE, [("trace", 2)], judge_measures=("trace",))
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


def test_two_systems_that_print_the_same_number_are_not_ranked_against_each_other():
    """The rule is "tied iff they print the same", not a fixed tolerance.

    The tolerance was 0.0005, chosen for a three-decimal column. Faithfulness
    prints two, where half a digit is ten times that: `glm-5` 4.96 and
    `gpt-5.6-sol` 4.955 both print **4.96** and were ranked against each other
    by a digit the table does not show. Fifteen such pairs stood across the
    published tables.
    """
    rows = _panel(
        {
            A: {"glm-5": _flat(4.96), "sol": _flat(4.955)},
            B: {"glm-5": _flat(4.955), "sol": _flat(4.96)},
        }
    )

    result = concordance.compare(rows, results.TRACK_TNEVAL, MEASURES)

    faith = next(m for m in result.measures if m.measure == "faithfulness")
    assert faith.moved == 0, "both judges print 4.96 for both systems"
    assert faith.furthest is None


def test_raising_the_tolerance_would_not_have_been_the_fix():
    """A three-decimal column fails the same way. 0.9742 and 0.9735 are 0.0007
    apart -- above any tolerance small enough to be honest -- and both print
    0.974."""
    rows = _panel(
        {
            A: {"x": _flat(0.9742), "y": _flat(0.9735)},
            B: {"x": _flat(0.9735), "y": _flat(0.9742)},
        }
    )

    result = concordance.compare(rows, results.TRACK_TNEVAL, MEASURES)

    assert all(m.moved == 0 for m in result.measures)


def test_a_difference_the_table_does_show_is_still_a_difference():
    """The guard must not swallow the movement it exists to report."""
    rows = _panel(
        {
            A: {"x": _flat(0.900), "y": _flat(0.800)},
            B: {"x": _flat(0.800), "y": _flat(0.900)},
        }
    )

    result = concordance.compare(rows, results.TRACK_TNEVAL, MEASURES)

    assert all(m.moved == 2 for m in result.measures)


def test_beaten_outright_is_decided_on_the_stored_figures():
    """Third rule for this comparison, and the first that errs in the safe direction.

    It was a tolerance, then the printed digits, and is now the stored values.
    The printed rule was chosen so a reader could check the claim by eye, which
    is a good reason that does not survive what rounding does *here*: dominance
    needs "at least as good on every measure", so rounding a narrow **loss**
    into a tie removes an obstacle and lets the claim through. Rounding
    manufactured dominance rather than withholding it.

    It fired twice on the published rows. `gemini-3.1-pro-preview` beat
    `glm-5.2` outright on a 0.0029 faithfulness gap in `glm-5.2`'s favour that
    printed 4.97 against 4.97; and on the iCARE track the summary named
    `gpt-5.6-sol` as beating six when `qwen3.8-27b` also beat six and one of
    `gpt-5.6-sol`'s six was a rounded loss.

    So a lead too small to print is a lead. `y` leads `x` everywhere by 0.0007
    and the table shows it nowhere -- and the page says, where the count is
    defined, that two rows printing the same number need not tie.
    """
    rows = _panel(
        {
            A: {"x": _flat(0.9735), "y": _flat(0.9742)},
            B: {"x": _flat(0.9735), "y": _flat(0.9742)},
        }
    )

    result = concordance.compare(rows, results.TRACK_TNEVAL, MEASURES)

    assert [(d.system, d.beats) for d in result.dominance] == [("y", ["x"])]
    assert result.undominated == ["y"]


def test_rounding_a_loss_into_a_tie_cannot_grant_dominance():
    """The direction, stated as its own case rather than left implicit.

    `x` is far ahead on one measure and behind on another by less than that
    column prints. Under the printed rule the second became a tie, the obstacle
    vanished and `x` dominated. It must not.
    """
    rows = _panel(
        {
            A: {
                "x": {**_flat(0.5), "faithfulness": 4.9716},
                "y": {**_flat(0.1), "faithfulness": 4.9745},
            },
            B: {
                "x": {**_flat(0.5), "faithfulness": 4.9716},
                "y": {**_flat(0.1), "faithfulness": 4.9745},
            },
        }
    )

    result = concordance.compare(rows, results.TRACK_TNEVAL, MEASURES)

    assert result.dominance == [], (
        "a loss smaller than the printed precision was rounded into a tie and let "
        "a dominance claim through"
    )


def _ceiling_panel() -> list[Row]:
    """Eighteen systems at the ceiling on one measure, one just below it.

    `organized` on the PDSQI track, in miniature. Completeness varies and can
    be ranked; conciseness gives nine of ten systems the identical 5.000.
    """
    names = [f"m{n:02d}" for n in range(10)]
    # The judges disagree about the measures that *can* be ranked, and cannot
    # disagree about the one that cannot -- which is the whole trap. The
    # ceiling column then has the highest correlation of the three, so a
    # `describe` that ranks by correlation alone picks it as the headline. That
    # is what the page did.
    shuffled = [0, 2, 1, 4, 3, 6, 5, 8, 7, 9]
    scores: dict[str, dict[str, dict[str, float]]] = {A: {}, B: {}}
    for index, name in enumerate(names):
        scores[A][name] = {
            "completeness": 0.9 - index * 0.05,
            "conciseness": 5.0 if index else 4.98,
            "faithfulness": 4.9 - index * 0.03,
        }
        scores[B][name] = {
            "completeness": 0.8 - shuffled[index] * 0.04,
            "conciseness": 5.0 if index else 4.90,
            "faithfulness": 4.7 - shuffled[index] * 0.02,
        }
    return _panel(scores)


def test_a_measure_most_systems_tie_on_gets_no_agreement_figure():
    """`organized` gave 5.00 to eighteen of nineteen systems under both judges.

    Spearman over that is +1.000 and the page published "the two judges agree on
    the shape of the ranking on organized" -- a claim decided entirely by the
    one system that was not at the ceiling. The `judge_measures` filter already
    in this module was written against the same defect arriving the other way
    round, where the correlation was a tautology rather than a coin.
    """
    comparison = concordance.compare(
        _ceiling_panel(), results.TRACK_TNEVAL, MEASURES, judge_a=A, judge_b=B
    )

    assert comparison is not None
    found = {m.measure: m for m in comparison.measures}
    assert found["conciseness"].tied == 9, "nine of ten print the same number"
    assert not found["conciseness"].rankable
    assert found["completeness"].rankable and found["completeness"].tied == 1
    assert found["conciseness"].rho > found["completeness"].rho, (
        "the trap: the measure that cannot order the systems correlates best"
    )

    sentence = concordance.describe(comparison)
    assert "shape of the ranking on conciseness" not in sentence, (
        "a measure that cannot order the systems was published as agreement about their order"
    )
    assert "No agreement figure is given for conciseness (9 of 10 share one value)" in sentence
    assert "shape of the ranking on completeness" in sentence, (
        "the measures that do rank the systems are still reported"
    )


def test_the_rankability_of_every_measure_reaches_the_page():
    """A reader who wants to check the exclusion needs the count, not the prose."""
    comparison = concordance.compare(
        _ceiling_panel(), results.TRACK_TNEVAL, MEASURES, judge_a=A, judge_b=B
    )
    published = concordance.to_json(comparison)

    assert published is not None
    by_measure = {m["measure"]: m for m in published["measures"]}
    assert by_measure["conciseness"]["tied"] == 9
    assert by_measure["conciseness"]["rankable"] is False
    assert by_measure["completeness"]["rankable"] is True


def test_a_measure_split_evenly_is_still_ranked():
    """Half is the line, and half is on the ranked side of it.

    Otherwise a two-way split -- a real, if coarse, ordering -- would be thrown
    away with the ceilings.
    """
    scores: dict[str, dict[str, dict[str, float]]] = {A: {}, B: {}}
    for index in range(10):
        high = index < 5
        scores[A][f"m{index:02d}"] = {
            "completeness": 0.9 - index * 0.05,
            "conciseness": 5.0 if high else 4.0,
            "faithfulness": 4.9 - index * 0.03,
        }
        scores[B][f"m{index:02d}"] = {
            "completeness": 0.8 - index * 0.04,
            "conciseness": 5.0 if high else 4.0,
            "faithfulness": 4.7 - index * 0.02,
        }

    comparison = concordance.compare(
        _panel(scores), results.TRACK_TNEVAL, MEASURES, judge_a=A, judge_b=B
    )

    assert comparison is not None
    found = {m.measure: m for m in comparison.measures}
    assert found["conciseness"].tied == 5
    assert found["conciseness"].rankable, "five of ten is not most of them"
