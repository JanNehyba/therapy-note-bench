"""The meaning-unit cut, which every per-unit denominator rests on.

The rule is this repository's own -- no published procedure segments a note that
has no speaker labels and no blank lines -- so it is pinned here harder than a
borrowed one would be. The tests that matter most are the ones about what the
rule refuses to do: it never invents a boundary inside a long sentence, and it
never reports an offset it could not verify.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import czech_units  # noqa: E402


def test_a_sentence_is_a_unit():
    units = czech_units.split_section(
        "Klientka popisuje přetížení prací. Uvádí, že se jí nedaří odcházet včas."
    )
    assert len(units) == 2


def test_an_abbreviation_does_not_end_a_sentence():
    """`např.` and its kin carry a full stop that ends nothing.

    Without the protection list every abbreviation would manufacture a unit, and
    the denominator of every per-unit measure would count the note's punctuation
    habits rather than its assertions.
    """
    units = czech_units.split_section(
        "Zanedbává osobní záležitosti, např. dluhy v knihovně a nevyřízenou poštu."
    )
    assert len(units) == 1


def test_a_short_fragment_is_merged_backwards():
    units = czech_units.split_section("Klientka je orientovaná a spolupracující. Ano.")
    assert len(units) == 1
    assert units[0].endswith("Ano.")


def test_a_qualifying_opener_is_merged_backwards():
    """A sentence that only qualifies its predecessor is not a second assertion."""
    units = czech_units.split_section(
        "Klientka popisuje přetížení prací a chronickou únavu. "
        "Zároveň uvádí, že se jí nedaří odcházet ze zaměstnání včas."
    )
    assert len(units) == 1


def test_the_first_unit_of_a_section_is_never_merged_away():
    """There is nothing behind it to merge into, so a short opener survives.

    Recorded as a test rather than left implicit because it is why the reported
    minimum unit length is below `MIN_WORDS` and a reader would otherwise take
    that for a bug.
    """
    units = czech_units.split_section("Ano. Klientka dále popisuje přetížení prací.")
    assert units[0] == "Ano."


def test_a_bullet_is_a_boundary_whatever_the_punctuation_did():
    units = czech_units.split_section(
        "Krátkodobé cíle\n- Dodržovat pracovní dobu po dobu dvou týdnů\n"
        "- Zaznamenávat večerní únavu do deníku"
    )
    assert len(units) == 3


def test_a_long_sentence_is_reported_and_never_split():
    """The rule has no principled way to cut a long sentence, so it does not.

    Inventing a cut would make every denominator depend on a guess. The unit is
    flagged instead, so a reader can see how often the rule gave up.
    """
    long_sentence = "Klientka " + " ".join(["popisuje"] * 80) + " situaci."
    note = {"subjective": long_sentence, "objective": "", "assessment": "", "plan": ""}
    units = czech_units.split_note(note)
    assert len(units) == 1
    assert units[0]["long"] is True


def test_offsets_locate_the_unit_in_its_own_section():
    note = {
        "subjective": "První tvrzení o klientce. Druhé tvrzení o klientce.",
        "objective": "",
        "assessment": "",
        "plan": "",
    }
    units = czech_units.split_note(note)
    text = note["subjective"]
    for unit in units:
        assert unit["offsets_exact"] is True
        assert text[unit["start"] : unit["end"]] == unit["text"]


def test_an_offset_that_could_not_be_verified_says_so():
    """`offsets_exact` is False rather than the offsets being quietly wrong.

    A merge across a line break produces a unit that is not a contiguous slice of
    the section. The span check downstream compares against the unit text, not
    the slice, so this costs nothing there -- but a reader told the offsets were
    exact when they are not would trust the wrong thing.
    """
    note = {
        "subjective": "Krátkodobé cíle\n- Ano.\n- Dodržovat pracovní dobu po dobu dvou týdnů",
        "objective": "",
        "assessment": "",
        "plan": "",
    }
    units = czech_units.split_note(note)
    assert any(not unit["offsets_exact"] for unit in units)


def test_an_empty_section_produces_no_units():
    """No units, not one empty unit. An empty section is an absence."""
    assert czech_units.split_section("") == []
    assert czech_units.split_section("   \n  ") == []


def test_every_unit_carries_its_section_and_a_note_wide_index():
    note = {
        "subjective": "První tvrzení o klientce dnes.",
        "objective": "Druhé tvrzení o klientce dnes.",
        "assessment": "",
        "plan": "Třetí tvrzení o klientce dnes.",
    }
    units = czech_units.split_note(note)
    assert [unit["unit_index"] for unit in units] == list(range(len(units)))
    assert [unit["section"] for unit in units] == ["subjective", "objective", "plan"]


def test_the_rule_and_its_caveat_are_stated_in_the_file():
    """Every figure gets a sentence saying what is behind it.

    The cut is unvalidated, and the file has to say so where the numbers are
    written rather than only in a docstring somebody may not read.
    """
    assert "one assertion" in czech_units.RULE
    assert "unvalidated" in czech_units.CAVEAT
