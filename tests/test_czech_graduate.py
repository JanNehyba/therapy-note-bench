"""The seven gates, and the arithmetic that decides which a category passes.

The thresholds themselves are pinned here as well as in the tool, because a
threshold changed after the results are in is not a threshold. If one of these
tests fails after a run, either the plan changed or somebody moved a goalpost,
and both should be visible in a diff.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import czech_graduate as grad  # noqa: E402


def rows(values, category="cat", coder="A", system="m1", session="s1"):
    return [
        {
            "mode": "deductive",
            "coder": coder,
            "system_id": system,
            "session_id": session,
            "unit_index": index,
            "category": category,
            "value": value,
        }
        for index, value in enumerate(values)
    ]


def test_the_share_is_over_the_units_the_coder_answered():
    out = grad.per_note_share(rows(["present", "absent", "absent", "absent"]))
    assert out["cat"][("m1", "s1")] == 0.25


def test_a_unit_with_no_opportunity_leaves_the_denominator():
    """`not-applicable` is not a mark and not a miss.

    Counting it as absent would let a note score for never giving the category a
    chance -- the shape that made the quotation criterion need a denominator of
    its own.
    """
    out = grad.per_note_share(rows(["present", "not-applicable", "not-applicable"]))
    assert out["cat"][("m1", "s1")] == 1.0


def test_an_unanswered_unit_never_becomes_an_absence():
    out = grad.per_note_share(rows(["present", None, None]))
    assert out["cat"][("m1", "s1")] == 1.0


def test_unclear_counts_in_the_denominator_but_not_as_present():
    """It was answered, so it is measured; it is not a mark, so it is not one."""
    out = grad.per_note_share(rows(["present", "unclear"]))
    assert out["cat"][("m1", "s1")] == 0.5


def test_gate_one_fails_a_category_nearly_everything_has():
    cells = {("m1", "s1"): 0.95, ("m1", "s2"): 0.96}
    out = grad.grade("cat", cells, None, {})
    assert out["gates"]["1_varies"]["passed"] is False


def test_gate_one_fails_a_category_almost_nothing_has():
    cells = {("m1", "s1"): 0.02, ("m1", "s2"): 0.01}
    out = grad.grade("cat", cells, None, {})
    assert out["gates"]["1_varies"]["passed"] is False


def test_gate_two_fails_when_the_variance_belongs_to_the_session():
    """A column whose variance sits in the session orders transcripts."""
    cells = {
        (model, session): value
        for session, value in (("s1", 0.1), ("s2", 0.5), ("s3", 0.9))
        for model in ("m1", "m2", "m3")
    }
    out = grad.grade("cat", cells, None, {})
    assert out["gates"]["2_model_not_session"]["passed"] is False


def test_gate_two_passes_when_the_variance_belongs_to_the_model():
    cells = {
        (model, session): value
        for model, value in (("m1", 0.1), ("m2", 0.5), ("m3", 0.9))
        for session in ("s1", "s2", "s3")
    }
    out = grad.grade("cat", cells, None, {})
    assert out["gates"]["2_model_not_session"]["passed"] is True


def test_gate_three_reads_the_worst_pair_not_the_average():
    """A panel is only as reliable as its weakest agreement."""
    reliability = {
        "boundary": {"A-B": {"kappa": 0.9}, "A-C": {"kappa": 0.2}},
        "pairwise": {"A-B": {"kappa": 0.9}, "A-C": {"kappa": 0.9}},
        "spans": {"A": {"discard_rate": 0.0}},
    }
    out = grad.grade("cat", {("m1", "s1"): 0.5}, reliability, {})
    assert out["gates"]["3_coders_agree"]["value"]["boundary_kappa_min_pair"] == 0.2
    assert out["gates"]["3_coders_agree"]["passed"] is False


def test_gate_four_fails_a_coder_that_invents_its_evidence():
    reliability = {"spans": {"A": {"discard_rate": 0.0}, "B": {"discard_rate": 0.4}}}
    out = grad.grade("cat", {("m1", "s1"): 0.5}, reliability, {})
    assert out["gates"]["4_evidence_is_real"]["value"] == 0.4
    assert out["gates"]["4_evidence_is_real"]["passed"] is False


def test_gate_seven_is_reported_as_not_run_rather_than_passed():
    """No control note exists for these categories, and silence would read as a pass."""
    out = grad.grade("cat", {("m1", "s1"): 0.5}, None, {})
    assert out["gates"]["7_planted_control"]["passed"] is None
    assert "NOT RUN" in out["gates"]["7_planted_control"]["why"]


def test_an_undecided_gate_is_left_out_of_the_count_rather_than_assumed():
    out = grad.grade("cat", {("m1", "s1"): 0.5}, None, {})
    assert out["gates_decided"] < len(out["gates"])


def test_the_length_slope_is_a_slope_and_not_a_correction():
    """Length was chosen by the models, not assigned to them, so subtracting what
    it predicts would remove the result along with the artefact."""
    cells = {("m1", "s1"): 0.1, ("m2", "s1"): 0.2, ("m3", "s1"): 0.3, ("m4", "s1"): 0.4}
    words = {("m1", "s1"): 100, ("m2", "s1"): 200, ("m3", "s1"): 300, ("m4", "s1"): 400}
    assert grad.length_slope(cells, words) == 0.1


def test_the_slope_is_none_when_every_note_is_the_same_length():
    cells = {("m1", "s1"): 0.1, ("m2", "s1"): 0.9, ("m3", "s1"): 0.5, ("m4", "s1"): 0.2}
    words = {key: 400 for key in cells}
    assert grad.length_slope(cells, words) is None


def test_every_threshold_is_in_one_place_so_moving_one_is_visible():
    assert grad.GATES["occurrence_min"] == 0.20
    assert grad.GATES["occurrence_max"] == 0.80
    assert grad.GATES["model_variance_min"] == 0.40
    assert grad.GATES["model_over_session"] == 3.0
    assert grad.GATES["boundary_kappa_min"] == 0.60
    assert grad.GATES["pairwise_kappa_min"] == 0.60
    assert grad.GATES["span_discard_max"] == 0.05
    assert grad.GATES["length_slope_max"] == 0.09


def test_the_caveat_separates_a_possible_number_from_a_meaningful_one():
    assert "not that the number matters" in grad.CAVEAT
    assert "gate 7 was not run" in grad.CAVEAT
