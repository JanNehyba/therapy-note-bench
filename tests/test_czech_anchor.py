"""The human anchor's arithmetic, and the one rule it must not break.

Offline: no judge, no cache, no corpus. The notes here are invented and the
"answers" are dictionaries.
"""

from __future__ import annotations

import sys

from tnb.config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tools"))

import czech_anchor  # noqa: E402

from tnb.scoring import czech  # noqa: E402

NOTE = (
    "Subjektivně: Klientka popisuje napětí.\n\n"
    "Objektivně: V kontaktu spolupracující.\n\n"
    "Hodnocení: Pokračuje práce.\n\n"
    "Plán: Nácvik dýchání."
)
STRAIGHT = NOTE + '\nUvedla: "nechci".'
CZECH_MARKS = NOTE + "\nUvedla: „nechci“."

NOTES = {("m", "s1"): NOTE, ("m", "s2"): STRAIGHT, ("m", "s3"): CZECH_MARKS}


def _human(**by_criterion):
    """One rated note per session, every criterion answered "no fault"."""
    out = {}
    for session in ("s1", "s2", "s3"):
        for key in czech.CRITERION_KEYS:
            out[("m", session, key)] = by_criterion.get(key, False)
    return out


def _verdicts(**by_criterion):
    out = {}
    for session in ("s1", "s2", "s3"):
        for key in czech.CRITERION_KEYS:
            out[("m", session, key)] = by_criterion.get(key, False)
    return out


# --- the rule this file exists for -----------------------------------------


def test_a_question_with_no_answer_is_not_a_disagreement():
    """The first version of this tool scored every missing answer against the
    judge and reported that `gpt-5.6-terra` agreed with the rater on 0 of 140
    questions. It had not been asked them yet. An absence is not a measurement,
    and it is not a bad measurement either."""
    verdicts = _verdicts()
    for session in ("s1", "s2", "s3"):
        del verdicts[("m", session, "diacritics")]

    result = czech_anchor.agreement(_human(), NOTES, verdicts)
    entry = result["criteria"]["diacritics"]

    assert entry["compared"] == 0
    assert entry["unanswered"] == 3
    assert entry["rate"] is None, "no answers is not a rate of zero"


def test_the_overall_rate_is_withheld_while_most_answers_are_missing():
    """ "1.00" printed beside "120 missing" is a number somebody quotes without
    the second half."""
    empty = czech_anchor.agreement(_human(), NOTES, {})
    assert empty["unanswered"] > empty["compared"]
    assert empty["rate"] is None

    # The rater has to be right about the quotation marks too, because that
    # column is read off the note and a fixture cannot talk it round: one of
    # the three notes uses straight marks and one uses Czech ones.
    human = _human()
    human[("m", "s1", "quotes")] = None
    human[("m", "s2", "quotes")] = True
    human[("m", "s3", "quotes")] = False

    full = czech_anchor.agreement(human, NOTES, _verdicts())
    assert full["unanswered"] == 0
    assert full["rate"] == 1.0


# --- the computed column ----------------------------------------------------


def test_the_counted_column_needs_no_judge_answer():
    """`quotes` is read off the note, so it can never be unanswered -- which is
    why it is the only column that still reports when a run is half done."""
    result = czech_anchor.agreement(_human(), NOTES, {})
    quotes = result["criteria"]["quotes"]

    assert quotes["computed"] is True
    assert quotes["unanswered"] == 0
    assert quotes["compared"] == 3


def test_the_person_and_the_count_are_compared_on_the_marks_themselves():
    """One note quotes nothing, one uses straight marks, one uses Czech ones.
    A rater who says so on all three agrees three times."""
    human = _human()
    human[("m", "s1", "quotes")] = None  # nothing quoted: "--"
    human[("m", "s2", "quotes")] = True  # straight marks: "ano"
    human[("m", "s3", "quotes")] = False  # Czech marks: "ne"

    result = czech_anchor.agreement(human, NOTES, {})
    assert result["criteria"]["quotes"]["agreed"] == 3


def test_no_opportunity_on_both_sides_counts_as_agreement():
    """The person wrote `--` and the instrument has no value. They agree that
    the question did not apply, and that is an answer -- the sheet says so."""
    human = _human()
    human[("m", "s1", "quotes")] = None

    result = czech_anchor.agreement(human, NOTES, {})
    assert result["criteria"]["quotes"]["agreed"] >= 1


# --- reading the sheet ------------------------------------------------------


def test_the_sheet_is_read_by_its_own_footer(tmp_path):
    """The note-to-model table at the bottom, not a recomputed sample. A sheet
    drawn from a different draw still lines up with the cache."""
    sheet = tmp_path / "sheet.md"
    sheet.write_text(
        "# a sheet\n\n"
        "## Note 1\n\n| criterion | ano / ne / -- |\n|---|---|\n"
        "| diacritics | ano |\n| calque | ne |\n| quotes | -- |\n\n"
        "## Which note was whose\n\n| note | model | session |\n|---|---|---|\n"
        "| 1 | `a-model` | `cz-r-0000abcd` |\n",
        encoding="utf-8",
    )

    answers = czech_anchor.read_sheet(sheet)
    assert answers[("a-model", "cz-r-0000abcd", "diacritics")] is True
    assert answers[("a-model", "cz-r-0000abcd", "calque")] is False
    assert answers[("a-model", "cz-r-0000abcd", "quotes")] is None


def test_the_method_is_recorded_and_does_not_overclaim():
    """ "One native speaker rated twenty notes" and "a model proposed candidates
    and one native speaker ruled on each" are different claims. Only the second
    is true, and the figure is meaningless without it."""
    assert "language model presented each note" in czech_anchor.METHOD
    assert "decided every answer" in czech_anchor.METHOD
    assert "no human-against-human ceiling" in czech_anchor.CEILING
    assert "not an accuracy" in czech_anchor.CEILING


# --- the two sheets ---------------------------------------------------------


def test_both_sheets_draw_the_same_notes_in_different_orders():
    """The same twenty, so one person's two afternoons cover one sample. A
    different order, because rating a note for typos and then for quality lets
    the typos colour the quality -- free to avoid, so avoided."""
    import czech_pdsqi_sheet
    import czech_rating_sheet

    pairs = [(f"cz-r-{n:08x}", f"model-{n % 4}") for n in range(40)]

    drawn_language = sorted(pairs, key=lambda p: czech_rating_sheet._rank(*p))[:20]
    drawn_quality = sorted(pairs, key=lambda p: czech_pdsqi_sheet._rank(*p))[:20]
    assert set(drawn_language) == set(drawn_quality), "the two sheets rate one sample"

    shown_quality = sorted(drawn_quality, key=lambda p: czech_pdsqi_sheet._order(*p))
    assert shown_quality != drawn_language, "and present it in a different order"


def test_the_draw_is_independent_of_every_score():
    """Judge A had already run when the first sheet was written. Choosing by
    hand -- or by anything downstream of a score -- would let the sample be
    picked to flatter the result."""
    import czech_rating_sheet

    first = czech_rating_sheet._rank("cz-r-0000abcd", "a-model")
    assert first == czech_rating_sheet._rank("cz-r-0000abcd", "a-model"), "reproduces exactly"
    assert first != czech_rating_sheet._rank("cz-r-0000abcd", "b-model")
