"""The Czech language rubric: its parser, its prompts and its arithmetic.

Nothing here reaches the network and nothing reads `data/czech`. The note used
throughout is invented.
"""

from __future__ import annotations

import pytest

from tnb.scoring import czech, tneval

NOTE = """\
Subjektivně: Klientka popisuje zvýšené napětí před zkouškou.
Objektivně: V kontaktu spolupracující, afekt přiléhavý.
Hodnocení: Pokračuje práce na zvládání úzkosti.
Plán: Nácvik dýchání, kontrola za dva týdny."""


def _answers(**overrides: str) -> dict[str, str]:
    """Eight well-formed ratings, with any of them replaced."""
    answers = {f"quality.{key}": "8" for key in czech.DIMENSION_KEYS}
    answers.update({f"quality.{key}": value for key, value in overrides.items()})
    return answers


# --- the parser ------------------------------------------------------------


def test_ten_is_read_as_ten():
    assert czech.parse_rating("10") == 10
    assert czech.is_a_rating("10")


def test_zero_is_a_real_rating_and_not_a_missing_one():
    """0 is the bottom of this scale, not the absence of an answer. Everything
    downstream distinguishes them by None, never by falsiness."""
    assert czech.parse_rating("0") == 0
    assert czech.is_a_rating("0")


def test_the_whole_scale_survives_a_round_trip():
    assert [czech.parse_rating(str(n)) for n in range(11)] == list(range(11))


def test_punctuation_around_the_rating_is_tolerated():
    assert [czech.parse_rating(a) for a in ("  8 ", "[6]", "9.", "*4*")] == [8, 6, 9, 4]


def test_a_refusal_produces_no_number_at_all():
    """Never a fabricated middle of the scale. A judge that wrote prose did not
    rate, and the note is recorded as partial rather than as a 5."""
    for answer in ("", "   ", "I cannot rate this.", "the note is fine", "8/10 overall"):
        assert not czech.is_a_rating(answer)
        assert czech.parse_rating(answer) is None


def test_an_out_of_range_number_is_not_a_rating():
    for answer in ("11", "42", "-1", "100"):
        assert czech.parse_rating(answer) is None


def test_the_tneval_parser_would_have_got_these_wrong():
    """The bug, put back and watched.

    This also pins TN-Eval's behaviour as a documented fact: if anyone ever
    widens `parse_likert` to 0-10 to be helpful, the published TN-Eval numbers
    change meaning and this test fails first.
    """
    # int() succeeds and the value is outside 1-5, so the middle is fabricated.
    assert tneval.parse_likert("10") == 3
    assert tneval.parse_likert("0") == 3
    assert tneval.parse_likert("7") == 3
    # int() fails, and the digit scan finds the leading 1 of "10".
    assert tneval.parse_likert("Rating: 10") == 1
    assert tneval.parse_likert("10/10") == 1
    # Which the rubric's own parser refuses to do.
    assert czech.parse_rating("10") == 10
    assert czech.parse_rating("Rating: 10") is None


# --- the prompts -----------------------------------------------------------


def test_every_dimension_is_asked_in_its_own_call():
    """One call per dimension, never eight ratings in one answer.
    `judge.ANSWER_TOKENS` is inside the judge fingerprint, so raising it to fit
    a longer reply would discard every cached answer of the other two tracks."""
    tasks = czech.build_tasks(NOTE)
    assert len(tasks) == len(czech.DIMENSION_KEYS) == 8
    assert [task.dimension for task in tasks] == list(czech.DIMENSION_KEYS)
    assert len({task.unit for task in tasks}) == 8


def test_a_prompt_names_one_dimension_and_not_the_others():
    tasks = {task.dimension: task.prompt for task in czech.build_tasks(NOTE)}
    assert "Typografie" in tasks["typography"]
    assert "Typografie" not in tasks["spelling"]
    assert "Pravopis" in tasks["spelling"]


def test_the_judge_is_never_shown_the_transcript():
    """The confidential sessions reach e-INFRA, because a model has to read one
    to write a note. They must not reach the judge's provider as well, and the
    rubric is built so there is nothing to pass: `build_tasks` takes the note
    and has no parameter for a transcript."""
    sentence = "Tak povidejte, co vas dneska privadi"
    for task in czech.build_tasks(NOTE + "\n"):
        assert sentence not in task.prompt
        assert "transkript" not in task.prompt.lower() or "nemáš" in task.prompt

    import inspect

    assert "conversation" not in inspect.signature(czech.build_tasks).parameters
    assert "transcript" not in inspect.signature(czech.build_tasks).parameters


def test_the_prompt_asks_for_a_bare_number():
    for task in czech.build_tasks(NOTE):
        assert task.prompt.rstrip().endswith(":")
        assert "0 do 10" in task.prompt


def test_both_prompt_languages_carry_the_note_and_differ():
    czech_prompt = czech.build_tasks(NOTE, language="cs")[0].prompt
    english_prompt = czech.build_tasks(NOTE, language="en")[0].prompt
    assert NOTE in czech_prompt and NOTE in english_prompt
    assert czech_prompt != english_prompt


def test_the_prompt_language_is_part_of_the_instrument():
    """`judge_prompt_version` is in COMPARABILITY_KEYS, so two languages can
    never end up in one table however a run is invoked."""
    assert czech.judge_prompt_version("cs") != czech.judge_prompt_version("en")
    with pytest.raises(ValueError, match="unknown prompt language"):
        czech.judge_prompt_version("de")
    with pytest.raises(ValueError, match="unknown prompt language"):
        czech.build_tasks(NOTE, language="de")


# --- aggregation -----------------------------------------------------------


def test_eight_ratings_make_a_complete_note():
    scores = czech.aggregate(NOTE, _answers())
    assert scores.is_complete
    assert set(scores.by_criterion) == set(czech.DIMENSION_KEYS)
    assert scores.headline["spelling"] == 8.0


def test_a_dimension_the_judge_refused_is_named_and_not_scored():
    """An absence is not a measurement. It is not a zero, and the seven that
    were answered do not quietly become the note's score."""
    scores = czech.aggregate(NOTE, _answers(typography="I cannot rate this."))

    assert not scores.is_complete
    assert scores.incomplete["quality"] == ["typography"]
    assert "typography" not in scores.headline
    assert "typography" not in scores.by_criterion
    assert scores.sections_used["quality"] == 7


def test_a_missing_answer_is_treated_like_a_refusal():
    answers = _answers()
    del answers["quality.grammar"]
    scores = czech.aggregate(NOTE, answers)
    assert scores.incomplete["quality"] == ["grammar"]


def test_a_zero_rating_is_kept_and_is_not_missing():
    """The failure this guards: `if not rating` would file a legitimate 0 as a
    refusal, and the worst Czech in the run would vanish from the average."""
    scores = czech.aggregate(NOTE, _answers(spelling="0"))
    assert scores.is_complete
    assert scores.headline["spelling"] == 0.0


def test_note_length_is_recorded_even_when_the_judge_failed():
    """Not a judge measure and not a column -- it is the answer to "does this
    model just write longer notes", and it costs nothing to keep."""
    scores = czech.aggregate(NOTE, {})
    assert scores.headline["note_words"] == float(len(NOTE.split()))
    assert scores.incomplete["quality"] == list(czech.DIMENSION_KEYS)


def test_note_length_is_not_one_of_the_published_columns():
    assert "note_words" in czech.INTERNAL_MEASURES
    assert "note_words" not in czech.MEASURES
    assert "note_words" not in czech.JUDGE_MEASURES


# --- what the track claims -------------------------------------------------


def test_the_track_declines_to_name_a_ranking_measure():
    """Weighting spelling against terminology is a linguistic decision, not a
    measurement."""
    assert czech.RANKING_MEASURE is None


def test_every_dimension_is_documented_on_the_same_scale():
    assert set(czech.MEASURES) == set(czech.DIMENSION_KEYS)
    for key, measure in czech.MEASURES.items():
        assert measure["scale"] == "0-10", key
        assert len(measure["definition"]) > 40, key
        assert measure["caveat"], key


def test_every_measure_warns_that_content_is_not_checked():
    """The one thing a reader must not conclude from any of these columns."""
    for key, measure in czech.MEASURES.items():
        assert "true or complete" in measure["caveat"], key


def test_every_judge_measure_is_a_dimension():
    """Unlike iCARE, nothing here is computed from a reference, so every column
    is a judge decision and the two-judge panel is meaningful on all of them."""
    assert set(czech.JUDGE_MEASURES) == set(czech.DIMENSION_KEYS)
