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

    full = czech_anchor.agreement(_human(), NOTES, _verdicts())
    assert full["unanswered"] == 0
    assert full["rate"] == 1.0


# --- the two judges against each other --------------------------------------


def test_a_note_only_one_judge_answered_leaves_the_rate():
    """The same rule as the human anchor, one counter over. A call e-INFRA never
    answered is not the two judges disagreeing, and counting it as one charges
    them for an outage."""
    first, second = _verdicts(), _verdicts()
    del first[("m", "s2", "register")]

    found = czech_anchor.between_judges(NOTES, {"a": first, "b": second})["criteria"]["register"]

    assert found["compared"] == 2
    assert found["agreed"] == 2
    assert found["unanswered"] == 1
    assert found["rate"] == 1.0


def test_the_two_judges_disagreeing_is_counted_as_a_disagreement():
    first, second = _verdicts(), _verdicts(register=True)

    found = czech_anchor.between_judges(NOTES, {"a": first, "b": second})["criteria"]["register"]

    assert (found["agreed"], found["compared"], found["rate"]) == (0, 3, 0.0)


def test_the_rate_is_stored_with_the_rubric_it_was_measured_under():
    """The defect this block was written for. Five judge-against-judge figures
    were typed into the briefing under `czech-criteria-v1` and printed beside
    the levels `czech-criteria-v2` produces -- 79% where the drawn rubric says
    83%, "a quarter" where it is a third. A rate carries no mark saying which
    instrument made it, so the payload has to carry one."""
    payload = czech_anchor.between_judges(NOTES, {"a": _verdicts(), "b": _verdicts()})

    assert payload["rubric"] == czech.JUDGE_PROMPT_VERSION
    assert payload["judges"] == ["a", "b"]
    assert payload["notes"] == len(NOTES)


def test_one_judge_alone_is_not_an_agreement():
    """Two judges or nothing. A single judge compared with itself agrees on
    everything, and that number would be drawn as if it meant something."""
    assert czech_anchor.between_judges(NOTES, {"a": _verdicts()}) == {}


# --- reading the sheet ------------------------------------------------------


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


# --- and what the briefing does with it -------------------------------------


def _brief():
    import czech_brief

    return czech_brief


def test_the_briefing_prints_the_rate_with_the_notes_behind_it(monkeypatch):
    """Both halves of the figure, because one of them is the denominator. "87%"
    over ten notes and over a hundred are different claims."""
    brief = _brief()
    monkeypatch.setattr(
        brief,
        "_payload",
        lambda _name: {
            "between_judges": {
                "rubric": czech.JUDGE_PROMPT_VERSION,
                "criteria": {"register": {"agreed": 73, "compared": 104, "unanswered": 0}},
            }
        },
    )

    said = brief._judges_agree("register")

    assert "73 of the 104 notes" in said
    assert "70%" in said


def test_a_note_only_one_judge_answered_is_named_beside_the_rate(monkeypatch):
    brief = _brief()
    monkeypatch.setattr(
        brief,
        "_payload",
        lambda _name: {
            "between_judges": {
                "rubric": czech.JUDGE_PROMPT_VERSION,
                "criteria": {"calque": {"agreed": 68, "compared": 102, "unanswered": 2}},
            }
        },
    )

    said = brief._judges_agree("calque")

    assert "68 of the 102" in said
    assert "2 of them" in said
    assert "rather than counted against it" in said


def test_an_agreement_measured_under_another_rubric_is_not_printed(monkeypatch):
    """The whole defect. Five of these were typed into the briefing from
    `czech-criteria-v1` and printed beside `czech-criteria-v2` levels, and no
    number can say which instrument made it. So the payload says, and a
    mismatch drops the figure and names the mismatch instead of drawing it."""
    brief = _brief()
    monkeypatch.setattr(
        brief,
        "_payload",
        lambda _name: {
            "between_judges": {
                "rubric": "czech-criteria-v1",
                "criteria": {"diacritics": {"agreed": 77, "compared": 98, "unanswered": 0}},
            }
        },
    )

    said = brief._judges_agree("diacritics")

    assert "79" not in said and "98" not in said, "a v1 rate must not reach a v2 table"
    assert "czech-criteria-v1" in said and czech.JUDGE_PROMPT_VERSION in said


def test_a_checkout_without_the_payload_says_nothing_rather_than_zero(monkeypatch):
    brief = _brief()
    monkeypatch.setattr(brief, "_payload", lambda _name: {})

    assert brief._judges_agree("diacritics") == ""


def test_the_lowest_agreement_column_is_computed_not_typed():
    """The claim deleted as false was true, and is now derived.

    `c5faf9b` removed "67%, the lowest of the six" on the grounds that calque
    ties with agreement. It does not: under `czech-criteria-v2` calque is 68/102
    and agreement 71/104, which the document itself prints as 67 and 68. The
    ranking is back and computed from the same payload the percentages come
    from, so it can no longer disagree with them.
    """
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import czech_brief

    between = {
        "criteria": {
            "calque": {"agreed": 68, "compared": 102},
            "agreement": {"agreed": 71, "compared": 104},
            "register": {"agreed": 73, "compared": 104},
        }
    }
    assert czech_brief._is_lowest("calque", between)
    assert not czech_brief._is_lowest("agreement", between)
    assert not czech_brief._is_lowest("register", between)


def test_a_tie_at_the_bottom_names_nobody_the_lowest():
    """Where two columns cannot be ordered, calling either one lowest invents it."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import czech_brief

    tied = {
        "criteria": {"a": {"agreed": 68, "compared": 102}, "b": {"agreed": 68, "compared": 102}}
    }
    assert not czech_brief._is_lowest("a", tied)
    assert not czech_brief._is_lowest("b", tied)


def test_the_lowest_needs_something_to_be_lowest_than():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import czech_brief

    assert not czech_brief._is_lowest("a", {"criteria": {"a": {"agreed": 1, "compared": 2}}})
    assert not czech_brief._is_lowest("a", {})
