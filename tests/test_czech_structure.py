"""The surface census, and the two places it refuses to produce a number.

The census exists to rule features out cheaply, so the tests are mostly about it
declining: a variance split it cannot identify, and an overlap between sections
where one of them is empty. Both would be easy to return as zero, and both would
then read as a measurement of something nobody measured.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import czech_structure as structure  # noqa: E402

NOTE = {
    "subjective": "Klientka popisuje přetížení prací. Uvádí chronickou únavu.",
    "objective": "Tempo řeči je přiměřené. Udržuje oční kontakt.",
    "assessment": "Stav odpovídá dlouhodobému přetížení prací.",
    "plan": "- Dodržovat pracovní dobu\n- Zaznamenávat únavu",
}


def test_a_bullet_list_is_found():
    out = structure.features(NOTE)
    assert out["bullets"] == 2
    assert out["has_bullet"] == 1.0


def test_quotation_styles_are_counted_apart():
    """Style is a per-model fingerprint, and a straight double quote inside a
    JSON string has to be escaped by the model -- so it is suppressed for a
    reason that has nothing to do with how the model writes."""
    note = {**NOTE, "subjective": "Uvádí, že je „ve vleku“ a že 'nestíhá'."}
    out = structure.features(note)
    assert out["quotes"]["czech"] >= 1
    assert out["quotes"]["single"] >= 1


def test_an_assertion_the_transcript_cannot_support_is_flagged():
    """The real transcripts carry no paralinguistic annotation at all, so a note
    reporting speech or eye contact is reporting something the input did not
    contain. Whether that is the model's fault or the prompt's is not this
    file's question."""
    out = structure.features(NOTE)
    assert out["unsupported_modality"] >= 2
    assert out["has_unsupported_modality"] == 1.0


def test_a_near_empty_section_is_counted():
    out = structure.features({**NOTE, "plan": "-"})
    assert out["near_empty_sections"] == 1


def test_overlap_between_two_written_sections_is_a_number():
    out = structure.features(NOTE)
    assert 0.0 < out["subjective_assessment_overlap"] <= 1.0


def test_overlap_with_an_empty_section_is_none_rather_than_zero_or_one():
    """Two empty sections do not repeat each other perfectly, and an empty
    section does not repeat nothing. Both readings would measure an absence."""
    out = structure.features({**NOTE, "assessment": ""})
    assert out["subjective_assessment_overlap"] is None


def test_deepsy_shaped_notes_get_no_soap_only_measures():
    """A Deepsy note has eleven sections and no subjective. The measures that
    need one are absent rather than zero -- the whole point of the rule."""
    out = structure.features({"data": "Text jedna.", "plan": "Text dvě."})
    assert "subjective_share" not in out
    assert "unsupported_modality" not in out


def test_the_variance_split_sums_to_one():
    cells = {
        (model, session): float(hash((model, session)) % 7)
        for model in ("m1", "m2", "m3")
        for session in ("s1", "s2", "s3")
    }
    split = structure.variance_split(cells)
    assert split is not None
    # The shares are rounded to four places, so they sum to one to within that.
    assert abs(split["model"] + split["session"] + split["residual"] - 1.0) < 1e-3


def test_a_feature_that_belongs_to_the_model_says_so():
    """Every model wrote from every session, which is what makes this readable:
    a feature whose variance sits in the session orders transcripts, not models."""
    cells = {
        (model, session): value
        for model, value in (("m1", 1.0), ("m2", 5.0), ("m3", 9.0))
        for session in ("s1", "s2", "s3")
    }
    split = structure.variance_split(cells)
    assert split["model"] > 0.99


def test_a_feature_that_belongs_to_the_session_says_so():
    cells = {
        (model, session): value
        for session, value in (("s1", 1.0), ("s2", 5.0), ("s3", 9.0))
        for model in ("m1", "m2", "m3")
    }
    split = structure.variance_split(cells)
    assert split["session"] > 0.99


def test_a_grid_too_thin_to_decompose_returns_none_rather_than_zero():
    """Zero would read as "nothing belongs to the model", which is a different
    claim from "this cannot be decomposed"."""
    assert structure.variance_split({("m1", "s1"): 1.0, ("m1", "s2"): 2.0}) is None
    assert structure.variance_split({}) is None


def test_a_feature_that_never_varies_returns_none():
    cells = {
        (model, session): 1.0 for model in ("m1", "m2", "m3") for session in ("s1", "s2", "s3")
    }
    assert structure.variance_split(cells) is None


def test_the_caveat_says_this_is_a_screen_and_not_a_finding():
    assert "never as a finding" in structure.CAVEAT
    assert "false-positive rate" in structure.CAVEAT
