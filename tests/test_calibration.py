"""Checking the judge against two therapists — and the arithmetic that does it.

The statistics are implemented in this repository rather than imported, so they
are pinned against worked examples here. A calibration figure that is quietly
wrong is worse than no calibration: it is the number the whole leaderboard rests
on.
"""

from __future__ import annotations

import pytest

from tnb.scoring import calibration
from tnb.scoring.calibration import Agreement, Paired, Report, cohens_kappa, spearman

# --- Cohen's kappa -----------------------------------------------------------


def test_perfect_agreement_is_one():
    assert cohens_kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1.0


def test_chance_agreement_is_about_zero():
    """Half the labels match, and half is exactly what chance predicts here."""
    kappa = cohens_kappa([1, 1, 0, 0], [1, 0, 1, 0])
    assert kappa == pytest.approx(0.0, abs=1e-9)


def test_systematic_disagreement_is_negative():
    assert cohens_kappa([1, 1, 0, 0], [0, 0, 1, 1]) < 0


def test_a_worked_example():
    """20 items: 8 both yes, 7 both no, 3 and 2 split the other ways.

    Observed agreement 15/20 = .75. Expected by chance, from the marginals
    (11 and 10 yes): (11/20)(10/20) + (9/20)(10/20) = .5.
    kappa = (.75 - .5) / (1 - .5) = .5
    """
    first = [1] * 8 + [0] * 7 + [1] * 3 + [0] * 2
    second = [1] * 8 + [0] * 7 + [0] * 3 + [1] * 2
    assert cohens_kappa(first, second) == pytest.approx(0.5, abs=1e-9)


def test_two_raters_who_always_said_yes_agreed_completely():
    """Chance correction is undefined here, not zero. Calling it zero would
    report a rater who never made a mistake as no better than guessing."""
    assert cohens_kappa([1, 1, 1], [1, 1, 1]) == 1.0


def test_kappa_of_nothing_is_none_rather_than_a_number():
    assert cohens_kappa([], []) is None


# --- Spearman ----------------------------------------------------------------


def test_a_monotone_relationship_is_one():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)


def test_a_reversed_relationship_is_minus_one():
    assert spearman([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)


def test_ties_are_ranked_by_their_average():
    """Likert ratings are full of ties; ranking them wrongly would inflate the
    correlation the calibration reports."""
    assert spearman([1, 1, 2, 2], [1, 1, 2, 2]) == pytest.approx(1.0)


def test_a_rater_with_no_variation_correlates_with_nothing():
    """A therapist who scored everything 4 carries no rank information. None is
    honest; 0.0 would look like a measured disagreement."""
    assert spearman([4, 4, 4, 4], [1, 2, 3, 4]) is None


# --- what the report says ----------------------------------------------------


def _agreement(
    name, judge, humans, statistic="Cohen's kappa", n=100, alpha=None, alpha_humans=None
) -> Agreement:
    """One measure's agreement.

    ``alpha`` defaults to the judge figure so a test that only cares about the
    natural statistic reads the same as before. The verdict, though, is computed
    from the alpha alone -- see `test_the_verdict_is_refused_without_a_comparable_statistic`.
    """
    return Agreement(
        name=name,
        n=n,
        judge_vs_human=[judge, judge],
        human_vs_human=humans,
        statistic=statistic,
        alpha_judge_vs_human=[judge if alpha is None else alpha],
        alpha_human_vs_human=humans if alpha_humans is None else alpha_humans,
        alpha_level="nominal" if statistic == "Cohen's kappa" else "ordinal",
    )


def test_a_judge_at_the_human_ceiling_is_recognised():
    """Two therapists disagree with each other about these notes. A judge that
    agrees as often as they do has done as well as the task allows."""
    assert _agreement("rubric_completeness", 0.62, 0.60).reaches_ceiling is True
    assert _agreement("rubric_completeness", 0.30, 0.60).reaches_ceiling is False


def test_the_verdict_is_refused_without_a_comparable_statistic():
    """No alpha, no claim.

    The two per-measure statistics are a kappa and a Spearman rho. Comparing them
    is what this property used to do, and the sentence it produced was the stated
    reason for ranking on the rubric. With nothing comparable to read, the honest
    output is no verdict.
    """
    bare = Report(
        judge_model="x",
        judge_prompt_version="v1",
        notes=150,
        agreements=[
            Agreement("rubric_completeness", 100, [0.90], 0.5, "Cohen's kappa"),
            Agreement("likert_completeness", 100, [0.30], 0.2, "Spearman rho"),
        ],
    )

    assert bare.rubric_beats_likert is None


def test_the_verdict_follows_the_alpha_and_not_the_raw_statistic():
    """A kappa that would win the raw comparison must not win the real one."""
    report = Report(
        judge_model="x",
        judge_prompt_version="v1",
        notes=150,
        agreements=[
            _agreement("rubric_completeness", 0.90, 0.5, alpha=0.20),
            _agreement("likert_completeness", 0.30, 0.2, "Spearman rho", alpha=0.60),
        ],
    )

    assert report.rubric_beats_likert is False


def test_the_report_notices_tn_evals_finding():
    report = Report(
        judge_model="gemini-2.5-pro",
        judge_prompt_version="v1",
        notes=150,
        agreements=[
            _agreement("rubric_completeness", 0.59, 0.62),
            _agreement("likert_completeness", 0.31, -0.21, "Spearman rho"),
        ],
    )
    assert report.rubric_beats_likert is True


def test_the_report_would_say_so_if_the_finding_did_not_hold():
    report = Report(
        judge_model="x",
        judge_prompt_version="v1",
        notes=150,
        agreements=[
            _agreement("rubric_completeness", 0.10, 0.62),
            _agreement("likert_completeness", 0.80, -0.21, "Spearman rho"),
        ],
    )
    assert report.rubric_beats_likert is False
    assert "NOT reproduce" in calibration.render_markdown(report) or "not reproduce" in (
        calibration.render_markdown(report)
    )


def test_the_published_block_always_shows_the_human_ceiling():
    """Publishing 'judge 0.31' without 'therapists -0.21' beside it would read
    as a bad judge when it is a bad scale."""
    report = Report(
        judge_model="gemini-2.5-pro",
        judge_prompt_version="v1",
        notes=150,
        agreements=[_agreement("likert_completeness", 0.31, -0.21, "Spearman rho")],
    )
    markdown = calibration.render_markdown(report)

    assert "0.31" in markdown and "-0.21" in markdown
    assert "ceiling" in markdown


def test_an_uncalibrated_judge_says_so_rather_than_showing_nothing():
    report = Report(judge_model="x", judge_prompt_version="v1", notes=0, agreements=[])
    assert "Not yet measured" in calibration.render_markdown(report)


# --- pairing -----------------------------------------------------------------


def test_pairing_keeps_each_annotator_separate():
    """Averaging the two therapists before comparing would hide how much they
    disagree, which is the number that makes the judge's score readable."""
    paired = Paired()
    paired.add(1.0, [1.0, 0.0])
    paired.add(0.0, [0.0, 0.0])

    assert paired.judge == [1.0, 0.0]
    assert paired.humans == [[1.0, 0.0], [0.0, 0.0]]
    assert len(paired) == 2


def test_scoring_a_binary_measure_uses_kappa_and_a_scale_uses_spearman():
    paired = Paired()
    for judge_value, humans in [(1, [1, 1]), (0, [0, 1]), (1, [1, 0]), (0, [0, 0])]:
        paired.add(float(judge_value), [float(h) for h in humans])

    assert calibration.score_agreement("rubric_x", paired, binary=True).statistic == "Cohen's kappa"
    assert calibration.score_agreement("likert_x", paired, binary=False).statistic == "Spearman rho"


def test_a_judge_that_never_discriminated_measured_nothing():
    """It answered "no" to everything. That is not chance-level agreement.

    Live in docs/calibration.json before this: the judge answered "no" to
    assessment-goals on all 150 notes and was published at 0.000, which reads as
    "measured it and agreed no better than chance". Krippendorff's alpha on the
    same data gives -0.15; only kappa manufactured the zero, because observed
    equals expected when one rater makes no distinctions.

    `spearman` already refuses this and says why. Now both do.
    """
    assert cohens_kappa([0] * 8, [1, 0, 1, 0, 1, 0, 1, 0]) is None
    assert cohens_kappa([1, 0, 1, 0], [0] * 4) is None
    assert cohens_kappa([1] * 4, [0] * 4) is None


def test_two_raters_who_agreed_on_everything_still_score_one():
    """The one degenerate case that is a real answer, and it is kept."""
    assert cohens_kappa([1, 1, 1], [1, 1, 1]) == 1.0


def test_a_normal_disagreement_is_untouched():
    assert cohens_kappa([1, 1, 0, 0], [1, 0, 1, 0]) == pytest.approx(0.0, abs=1e-9)


def test_a_dropped_criterion_is_not_a_dropped_note(monkeypatch):
    """The panel published "149 notes" the morning two answers were skipped.

    `notes` was `len(rubric) // 23` -- rubric pairs over criteria. It read
    exactly 150 until the guard against scoring a judge's refusal as a "no"
    removed two pairs of 3450, and integer division turned that into two lost
    notes. Two criteria were lost; the notes they belong to are still in the
    analysis with 22 criteria each. The two published files disagreed, 149
    against 150, because they divided different judges' pair counts.
    """
    rubric = Paired()
    # Three notes' worth of criteria, one short: exactly what the division
    # tripped on.
    for _ in range(3 * 23 - 1):
        rubric.add(1.0, [1.0, 1.0])

    seen = {("s1", "therapist"), ("s1", "llama-3.1-70b"), ("s2", "therapist")}
    monkeypatch.setattr(
        calibration,
        "collect",
        lambda *args, **kwargs: {
            "rubric_completeness": rubric,
            "_per_criterion": {},
            "_settings": __import__("collections").Counter(),
            "_notes": seen,
        },
    )

    report = calibration.calibrate([], "a-judge")

    assert len(rubric) // 23 == 2, "the derivation this replaced loses a note"
    assert report.notes == 3, "the notes are counted, not divided out"
