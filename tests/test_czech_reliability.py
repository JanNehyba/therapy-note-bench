"""The agreement statistics, pinned against cases whose answer is known.

Both statistics are hand-written rather than taken from a library, so both are
checked against textbook values. The tests that matter most are the ones about
what the statistics refuse to report: a kappa is None where chance agreement is
already one, and an alpha is None where nothing can disagree. Returning 0.0 in
either place would print "no better than chance" about coders who agreed on
everything.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import czech_reliability as rel  # noqa: E402


def test_perfect_agreement_on_two_values_is_one():
    pairs = [("present", "present")] * 5 + [("absent", "absent")] * 5
    assert rel.cohen_kappa(pairs) == 1.0


def test_total_disagreement_is_negative():
    pairs = [("present", "absent")] * 5 + [("absent", "present")] * 5
    assert rel.cohen_kappa(pairs) == -1.0


def test_the_textbook_kappa_reproduces():
    """The 2x2 case from the standard worked example: a=20, b=5, c=10, d=15.

    Observed 0.70, expected 0.50, kappa 0.40.
    """
    pairs = [("yes", "yes")] * 20 + [("yes", "no")] * 5 + [("no", "yes")] * 10 + [("no", "no")] * 15
    assert rel.cohen_kappa(pairs) == 0.4


def test_kappa_is_none_when_both_coders_used_one_value():
    """Chance agreement is already one, so there is nothing to correct against.

    This is the prevalence collapse the module docstring warns about, in its
    extreme form. Zero here would be a lie about two coders who never differed.
    """
    assert rel.cohen_kappa([("absent", "absent")] * 40) is None


def test_kappa_is_none_below_two_units():
    assert rel.cohen_kappa([("present", "present")]) is None
    assert rel.cohen_kappa([]) is None


def test_alpha_is_one_on_perfect_agreement():
    units = [["present"] * 3 for _ in range(10)] + [["absent"] * 3 for _ in range(10)]
    assert rel.krippendorff_alpha(units) == 1.0


def test_alpha_drops_when_coders_split():
    units = [["present", "absent", "unclear"] for _ in range(10)]
    alpha = rel.krippendorff_alpha(units)
    assert alpha is not None and alpha < 0.0


def test_alpha_uses_a_unit_two_coders_answered_and_ignores_one_answered_alone():
    """A unit with one answer cannot agree or disagree with anything.

    It contributes nothing rather than being counted as agreement, which is the
    same rule the human anchor runs under: an unanswered question leaves the
    denominator.
    """
    with_pair = [["present", "present", ""]] * 6
    alone = [["present", "", ""]] * 40
    assert rel.krippendorff_alpha(with_pair) == rel.krippendorff_alpha(with_pair + alone)


def test_alpha_is_none_when_nothing_can_disagree():
    assert rel.krippendorff_alpha([["present", "", ""]] * 10) is None
    assert rel.krippendorff_alpha([]) is None


def _row(coder, unit, value, category="unsupported", valid=True):
    return {
        "coder": coder,
        "mode": "deductive",
        "system_id": "model-a",
        "session_id": "cz-r-000",
        "unit_index": unit,
        "category": category,
        "value": value,
        "span": "x" if value == "present" else "",
        "span_valid": valid,
    }


def test_a_verdict_nobody_gave_is_counted_as_missing_not_as_absent():
    """The denominator says how many verdicts were expected, and the gap is named."""
    rows = [_row("A", 0, "present"), _row("B", 0, "present"), _row("C", 0, None)]
    entry = rel.measure(rows)["unsupported"]
    assert entry["verdicts_expected"] == 3
    assert entry["verdicts_answered"] == 2
    assert entry["verdicts_missing"] == 1
    assert entry["prevalence"]["absent"] == 0


def test_boundary_agreement_collapses_the_four_values_to_marked_or_not():
    """`unclear` and `absent` are different verdicts and the same non-mark.

    The boundary figure is the one that survives two coders using the codebook
    differently, so it deliberately does not distinguish the three ways of not
    marking a unit.
    """
    rows = []
    for unit in range(10):
        rows += [_row("A", unit, "unclear"), _row("B", unit, "absent")]
    entry = rel.measure(rows)["unsupported"]
    assert entry["pairwise"]["A-B"]["raw_agreement"] == 0.0
    assert entry["boundary"]["A-B"]["raw_agreement"] == 1.0


def test_the_present_rate_is_over_the_verdicts_that_exist():
    rows = []
    for unit in range(4):
        rows += [_row("A", unit, "present" if unit < 1 else "absent")]
    entry = rel.measure(rows)["unsupported"]
    assert entry["present_rate"] == 0.25


def test_a_discarded_span_reaches_the_report_per_coder():
    rows = [_row("A", 0, "present", valid=False), _row("A", 1, "present", valid=True)]
    entry = rel.measure(rows)["unsupported"]
    assert entry["spans"]["A"] == {"present": 2, "discarded": 1, "discard_rate": 0.5}


def test_only_the_requested_mode_is_read(tmp_path):
    """One instrument at a time. Open and deductive rows are different questions."""
    import json

    source = tmp_path / "codes.jsonl"
    source.write_text(
        json.dumps({**_row("A", 0, "present"), "mode": "open"})
        + "\n"
        + json.dumps(_row("A", 1, "present"))
        + "\n",
        encoding="utf-8",
    )
    assert len(rel.load(source, "deductive")) == 1
    assert len(rel.load(source, "open")) == 1


def test_the_caveat_says_agreement_is_not_validity():
    assert "no evidence at all that the category matters" in rel.CAVEAT
