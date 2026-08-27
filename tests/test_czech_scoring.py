"""The Czech criteria: their parser, their prompts and their arithmetic.

Nothing here reaches the network and nothing reads `data/czech`. The note used
throughout is invented.
"""

from __future__ import annotations

from tnb.scoring import czech, pdsqi, tneval

NOTE = """\
Subjektivně: Klientka popisuje zvýšené napětí před zkouškou.
Objektivně: V kontaktu spolupracující, afekt přiléhavý.
Hodnocení: Pokračuje práce na zvládání úzkosti.
Plán: Nácvik dýchání, kontrola za dva týdny."""

QUOTING = NOTE + '\nKlientka uvedla: "nechci tam jít".'


def _answers(**overrides: str) -> dict[str, str]:
    """Every criterion answered "no fault", with any of them replaced."""
    answers = {f"czech.{key}": "ne" for key in czech.CRITERION_KEYS}
    answers.update({f"czech.{key}": value for key, value in overrides.items()})
    return answers


# --- the parser ------------------------------------------------------------


def test_czech_and_english_answers_are_both_read():
    """The question is Czech because the criteria are about Czech quotation
    marks and Czech terms, so a Czech answer is the expected case."""
    assert czech.parse_answer("ano") is True
    assert czech.parse_answer("ne") is False
    assert czech.parse_answer("yes") is True
    assert czech.parse_answer("no") is False


def test_punctuation_and_case_around_the_answer_are_tolerated():
    assert czech.parse_answer("Ano.") is True
    assert czech.parse_answer("NE") is False
    assert czech.parse_answer("„ano“") is True


def test_anything_else_is_no_answer_and_not_a_clean_note():
    """The one failure a rubric of absences cannot afford. Reading "not yes" as
    "no" would declare every unanswered note free of every fault."""
    for answer in ("", "   ", "možná", "I cannot tell", "ano i ne", "5"):
        assert czech.parse_answer(answer) is None


def test_the_yes_no_parser_is_pdsqis_and_not_a_third_one():
    """Two identical parsers drift. The only difference here is the language,
    and that is handled by translating two words before delegating."""
    assert pdsqi.parse_yes_no("yes") is True
    assert czech.parse_answer("yes") is pdsqi.parse_yes_no("yes")


def test_this_track_does_not_inherit_tnevals_fabricated_middle():
    for refusal in ("", "I cannot tell"):
        assert tneval.parse_likert(refusal) == 3
        assert czech.parse_answer(refusal) is None


# --- the prompts -----------------------------------------------------------


def test_every_criterion_is_asked_in_its_own_call():
    """One call per criterion, never seven answers in one reply.
    `judge.ANSWER_TOKENS` is inside the judge fingerprint, so raising it to fit
    a longer answer would discard every cached answer of the other tracks."""
    tasks = czech.build_tasks(QUOTING)
    assert len(tasks) == len(czech.CRITERION_KEYS) == 7
    assert len({task.unit for task in tasks}) == 7


def test_a_prompt_carries_its_own_counter_example():
    """Without one, `diacritics` and `nonword` answer the same question and
    their columns correlate for that reason rather than for a real one."""
    prompts = {task.criterion: task.prompt for task in czech.build_tasks(QUOTING)}
    assert "sebepe" in prompts["diacritics"]
    assert "Nepatří sem" in prompts["diacritics"]
    assert "Nepatří sem" in prompts["nonword"]
    assert prompts["diacritics"] != prompts["nonword"]


def test_the_judge_is_never_shown_the_transcript():
    """The confidential sessions reach e-INFRA, because a model has to read one
    to write a note. They must not reach the judge's provider as well, and there
    is nothing to pass: `build_tasks` takes the note and has no other parameter."""
    import inspect

    for task in czech.build_tasks(QUOTING):
        assert "T: " not in task.prompt
    assert list(inspect.signature(czech.build_tasks).parameters) == ["note"]


def test_the_prompt_asks_for_one_word():
    for task in czech.build_tasks(QUOTING):
        assert task.prompt.rstrip().endswith(":")
        assert "ano" in task.prompt and "ne" in task.prompt


# --- a criterion with nothing to judge -------------------------------------


def test_a_note_that_quotes_nothing_is_not_asked_about_quotation_marks():
    """It cannot have the wrong ones. Counting it as clean would let a model
    score on this column for never citing the client -- the same vacuity as an
    empty note, smaller."""
    asked = [task.criterion for task in czech.build_tasks(NOTE)]
    assert "quotes" not in asked
    assert len(asked) == 6

    assert "quotes" in [task.criterion for task in czech.build_tasks(QUOTING)]


def test_the_opportunity_is_decided_from_the_string_not_by_asking():
    """A judge call would spend money to be less certain than `in` already is."""
    assert not czech.has_quotes(NOTE)
    assert czech.has_quotes(QUOTING)
    assert czech.has_quotes("řekla „ano“")


def test_a_criterion_with_no_opportunity_is_absent_and_not_clean():
    scores = czech.aggregate(NOTE, _answers())
    assert "quotes" not in scores.headline
    assert scores.is_complete, "absent is not the same as unanswered"


# --- the empty note --------------------------------------------------------


def test_an_empty_note_is_not_asked_a_single_question():
    """All seven criteria ask about the absence of a fault, so an empty note
    passes all seven. PDSQI met the same shape on three of eight attributes;
    here it is seven of seven, because nothing else scores an empty note."""
    for empty in ("", "   ", "\n\n"):
        assert czech.build_tasks(empty) == []
        assert not czech.has_content(empty)


def test_an_empty_note_is_partial_and_does_not_vanish():
    """The half that is easy to get wrong. It must not be scored, and it must
    not be dropped either -- a model that wrote nothing would have its worst
    note disappear from the mean instead of counting."""
    scores = czech.aggregate("", {})
    assert not scores.is_complete
    assert scores.incomplete["czech"] == list(czech.CRITERION_KEYS)
    assert scores.headline == {"note_words": 0.0}


# --- aggregation -----------------------------------------------------------


def test_a_clean_note_scores_one_on_every_criterion_it_was_asked():
    scores = czech.aggregate(QUOTING, _answers())
    assert scores.is_complete
    assert set(scores.by_criterion) == set(czech.CRITERION_KEYS)
    assert all(value == 1.0 for value in scores.by_criterion.values())


def test_a_fault_found_scores_zero_so_higher_is_always_better():
    """The judge is asked whether the fault is present; the column reports its
    absence, so this table reads the same way as every other one."""
    scores = czech.aggregate(QUOTING, _answers(diacritics="ano"))
    assert scores.headline["diacritics"] == 0.0
    assert scores.headline["register"] == 1.0


def test_a_criterion_the_judge_refused_is_named_and_not_scored():
    """An absence is not a measurement, and here it is not a pass either."""
    scores = czech.aggregate(QUOTING, _answers(register="nevím"))

    assert not scores.is_complete
    assert scores.incomplete["czech"] == ["register"]
    assert "register" not in scores.headline
    assert scores.sections_used["czech"] == 6


def test_a_missing_answer_is_treated_like_a_refusal():
    answers = _answers()
    del answers["czech.agreement"]
    scores = czech.aggregate(QUOTING, answers)
    assert scores.incomplete["czech"] == ["agreement"]


def test_note_length_is_recorded_but_is_not_a_column():
    """The answer to "does this model just write longer notes", which is the
    first objection to any of these numbers."""
    scores = czech.aggregate(NOTE, _answers())
    # The headings do not count. `render_note` writes them whether or not the
    # section has anything under it, so counting them would report an empty note
    # as four words long.
    assert scores.headline["note_words"] == float(len(NOTE.split()) - 4)
    assert "note_words" in czech.INTERNAL_MEASURES
    assert "note_words" not in czech.MEASURES
    assert "note_words" not in czech.JUDGE_MEASURES


# --- what the track claims -------------------------------------------------


def test_the_track_declines_to_name_a_ranking_measure():
    assert czech.RANKING_MEASURE is None


def test_every_criterion_is_documented_as_a_proportion():
    assert set(czech.MEASURES) == set(czech.CRITERION_KEYS)
    for key, measure in czech.MEASURES.items():
        assert measure["scale"] == "0-1", key
        assert len(measure["definition"]) > 40, key
        assert "free of" in measure["definition"], key


def test_every_measure_warns_that_content_is_not_checked():
    for key, measure in czech.MEASURES.items():
        assert "true or complete" in measure["caveat"], key


def test_no_criterion_asks_about_anything_the_prompt_dictates():
    """The half of flatness that no wording can fix. A column is flat for good
    when the task prescribes the answer -- every model writes into the same
    four-part template, so a question about structure separates nobody. Each of
    these words named a PDSQI attribute that came back at 5.00 for all sixteen."""
    banned = ("struktur", "uspořád", "organiz", "sekc", "nadpis")
    for criterion in czech.CRITERIA:
        asked = (criterion.question + criterion.guidance).lower()
        assert not any(word in asked for word in banned), criterion.key


# --- the generation prompt -------------------------------------------------


def test_the_note_headings_are_czech_so_the_note_does_not_fail_its_own_prompt():
    """English headings would put English words into every note, and
    `untranslated` asks whether an English term was left in English. A model
    would lose a criterion for obeying its instructions."""
    from tnb.tasks import czech as task

    rendered = task.render_note({key: "text" for key in task.SECTIONS})
    assert "Subjektivně" in rendered
    assert "Subjective" not in rendered
    assert set(task.SECTION_LABELS) == set(task.SECTIONS)


def test_the_czech_prompt_asks_for_czech_and_names_the_speakers():
    """A model that has to infer what `K:` stands for is being measured on
    something this benchmark is not asking about."""
    from tnb.datasets.base import Session, Turn
    from tnb.tasks import czech as task

    session = Session(id="cz-t-0", source="czech-translated", turns=(Turn("client", "dobrý den"),))
    prompt = task.build_prompt(session)
    assert "Piš česky" in prompt
    assert "Klient: dobrý den" in prompt
    assert "SOAP" in prompt


def test_a_note_that_does_not_parse_is_none_and_not_four_empty_sections():
    """`scoring/czech.py` treats an empty note deliberately, and a refusal has
    to stay distinguishable from one."""
    from tnb.tasks import czech as task

    assert task.parse_note("promiňte, to neumím") is None
    assert task.parse_note('{"Subjektivně": "a"}') is None, "four sections or nothing"
    assert task.parse_note('{"Subjektivně":"","Objektivně":"","Hodnocení":"","Plán":""}') == {
        key: "" for key in task.SECTIONS
    }


def test_a_judge_that_deliberated_and_then_answered_is_read():
    """Measured on the corpus: a judge sometimes leaks its reasoning into the
    answer and answers anyway, on the final line, where the prompt asked for it.
    Refusing would throw away an answer that is there."""
    assert czech.parse_answer('" - wait, no.\n\n    I will output "ne".\nne') is False
    assert czech.parse_answer("Uvazuji...\nano") is True


def test_only_the_last_line_counts_and_not_anywhere_in_the_text():
    """The narrowing that keeps this from becoming TN-Eval's digit scan, which
    reads "4 (Patient says 2" as 2. Anywhere is a guess; the last line is where
    the answer was asked for."""
    assert czech.parse_answer("ne, ale zaroven ano") is None
    assert czech.parse_answer("The note contains no error, so the answer is no") is None
    assert czech.parse_answer("ano\nnevim") is None
