"""Krippendorff's alpha, checked against arithmetic rather than against memory.

The reference values here are computed by hand from the definition and shown in
the docstrings, because a citation from memory is not a check: the first pass at
this implementation was compared against a half-remembered published example,
disagreed with it, and was in fact correct — the recalled dataset was the wrong
one. Hand arithmetic from the formula cannot drift.

    Do = (1/n) Sum_c Sum_k o_ck d(c,k)
    De = (1/(n(n-1))) Sum_c Sum_k n_c n_k d(c,k)
    alpha = 1 - Do/De
"""

from __future__ import annotations

import pytest

from tnb.scoring.calibration import krippendorff_alpha


def test_seven_units_with_one_disagreement():
    """Worked by hand from the definition.

    Units [2,2] [1,1] [3,3] [3,4] [4,4] [1,1] [2,2]: N=7, one unit disagrees.
    Do = 1/7 = 0.142857. Marginals are 4, 4, 3, 3 over n=14, so
    De = (14^2 - (16+16+9+9)) / (14*13) = 146/182, and

        alpha = 1 - (1/7) / (146/182) = 1 - 13/73 = 60/73

    which is exact, so the test asserts the fraction rather than a rounding of it.
    """
    units = [[2, 2], [1, 1], [3, 3], [3, 4], [4, 4], [1, 1], [2, 2]]

    assert krippendorff_alpha(units, ordinal=False) == pytest.approx(60 / 73)


def test_perfect_agreement_is_one():
    units = [[1, 1], [2, 2], [3, 3], [1, 1]]

    assert krippendorff_alpha(units, ordinal=False) == 1.0


def test_systematic_disagreement_goes_below_zero():
    """Worse than chance is a real answer, not a floor at zero."""
    units = [[1, 2], [2, 1], [1, 2], [2, 1]]

    assert krippendorff_alpha(units, ordinal=False) < 0


def test_the_ordinal_form_forgives_a_near_miss():
    """Two raters one step apart agree more than two raters four steps apart.

    Nominal cannot see this -- every disagreement is total -- which is exactly
    why the Likert measures are scored ordinally and the rubric nominally.
    """
    near = [[1, 2], [2, 3], [3, 4], [4, 5], [5, 4], [1, 1]]
    far = [[1, 5], [5, 1], [2, 4], [4, 2], [1, 5], [5, 1]]

    assert krippendorff_alpha(near, ordinal=True) > krippendorff_alpha(far, ordinal=True)
    assert krippendorff_alpha(near, ordinal=True) > krippendorff_alpha(near, ordinal=False)


def test_nothing_to_measure_returns_none_rather_than_a_number():
    """A corpus with no variation has no chance-corrected agreement to report."""
    assert krippendorff_alpha([], ordinal=False) is None
    assert krippendorff_alpha([[1, 1]], ordinal=False) is None
    assert krippendorff_alpha([[1, 1], [1, 1], [1, 1]], ordinal=False) is None


def test_a_unit_rated_once_is_ignored_not_counted_as_agreement():
    """One rater is not agreement with anybody."""
    with_singleton = [[1, 1], [2, 2], [3, 3], [1, 2], [4]]
    without = [[1, 1], [2, 2], [3, 3], [1, 2]]

    assert krippendorff_alpha(with_singleton, ordinal=False) == krippendorff_alpha(
        without, ordinal=False
    )


def test_the_claim_needs_one_statistic_on_both_sides():
    """The defect this replaced: a Cohen's kappa compared against a Spearman rho.

    `rubric_beats_likert` is the repository's stated reason for ranking on the
    rubric rather than on the 1-5 scales. It must read the alpha, which is
    defined for both, and never the per-measure statistic, which is a kappa on
    one side and a correlation on the other.
    """
    from tnb.scoring.calibration import Agreement, Report

    rubric = Agreement(
        name="rubric_completeness",
        n=100,
        judge_vs_human=[0.90],  # a kappa that would win any raw comparison
        human_vs_human=0.5,
        statistic="Cohen's kappa",
        alpha_judge_vs_human=[0.20],  # but the comparable statistic says otherwise
        alpha_human_vs_human=0.5,
        alpha_level="nominal",
    )
    likert = Agreement(
        name="likert_completeness",
        n=100,
        judge_vs_human=[0.30],
        human_vs_human=0.2,
        statistic="Spearman rho",
        alpha_judge_vs_human=[0.60],
        alpha_human_vs_human=0.2,
        alpha_level="ordinal",
    )
    report = Report(
        judge_model="test",
        judge_prompt_version="v1",
        notes=100,
        agreements=[rubric, likert],
    )

    assert report.rubric_beats_likert is False


def test_two_instruments_too_close_to_separate_are_not_called():
    """A margin, so a rounding difference does not become a published finding."""
    from tnb.scoring.calibration import Agreement, Report

    def agreement(name: str, alpha: float) -> Agreement:
        return Agreement(
            name=name,
            n=100,
            judge_vs_human=[alpha],
            human_vs_human=0.4,
            statistic="x",
            alpha_judge_vs_human=[alpha],
            alpha_human_vs_human=0.4,
        )

    report = Report(
        judge_model="test",
        judge_prompt_version="v1",
        notes=100,
        agreements=[
            agreement("rubric_completeness", 0.51),
            agreement("likert_completeness", 0.49),
        ],
    )

    assert report.rubric_beats_likert is None
