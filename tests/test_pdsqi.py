"""PDSQI-9 as this repository reproduces it.

The instrument is published under CC BY 4.0; see NOTICE. These tests hold the
reproduction to what was published, and hold the two adaptations -- the dropped
attribute and the inverted polarity -- to being deliberate rather than drift.
"""

from __future__ import annotations

from tnb.scoring import pdsqi, tneval

NOTE = "S: Klientka popisuje napeti. O: Spolupracujici. A: Uzkost. P: Nacvik dychani."
TRANSCRIPT = "T: Dobry den.\nK: Dobry den, mam trochu strach ze zkousky."


def _answers(**overrides: str) -> dict[str, str]:
    answers = {f"pdsqi.{key}": "4" for key in pdsqi.ATTRIBUTE_KEYS}
    answers["pdsqi.stigmatizing"] = "No"
    answers.update({f"pdsqi.{key}": value for key, value in overrides.items()})
    return answers


# --- what was reproduced ---------------------------------------------------


def test_eight_attributes_remain_and_cited_is_the_one_dropped():
    """A note written from one transcript has no source documents, so the
    citation attribute has nothing to rate."""
    assert len(pdsqi.ATTRIBUTES) == 8
    assert "cited" in pdsqi.DROPPED
    assert "cited" not in pdsqi.ATTRIBUTE_KEYS


def test_every_attribute_keeps_its_published_item_number():
    """So a reader can check any question against the paper. Item 1 is the
    dropped citation question, which is why the numbering starts at 2."""
    assert [a.item for a in pdsqi.ATTRIBUTES] == [2, 3, 4, 5, 6, 7, 8, 9]


def test_the_seven_likert_attributes_have_five_anchors_each():
    for attribute in pdsqi.ATTRIBUTES:
        if attribute.binary:
            continue
        assert len(attribute.anchors) == 5, attribute.key
        assert all(anchor.strip() for anchor in attribute.anchors), attribute.key


def test_stigmatizing_is_binary_as_published():
    """The paper rates seven attributes on a five-point Likert and this one
    yes/no. Putting it on the Likert scale would be a different instrument."""
    binary = [a.key for a in pdsqi.ATTRIBUTES if a.binary]
    assert binary == ["stigmatizing"]


def test_the_two_word_substitutions_are_recorded():
    """The instrument says summary and source notes because it rates a summary
    of earlier notes. Both replacements are named rather than silent."""
    assert pdsqi.ORIGINAL_WORDING["summary"] == "note"
    assert "session transcript" in pdsqi.ORIGINAL_WORDING.values()


def test_every_measure_publishes_the_instruments_limits():
    """Validated on a corpus that excluded psychiatry, and on multi-document
    summaries rather than session notes. Both belong beside every number."""
    for key, measure in pdsqi.MEASURES.items():
        assert "psychiatry" in measure["caveat"], key
        assert "0.575" in measure["caveat"], key
        assert measure["scale"] in ("1-5", "0-1"), key


# --- the transcript boundary -----------------------------------------------


def test_only_two_attributes_need_the_transcript():
    assert set(pdsqi.NEEDS_TRANSCRIPT_KEYS) == {"accurate", "thorough"}
    assert len(pdsqi.NOTE_ONLY_KEYS) == 6


def test_without_a_transcript_those_two_are_not_asked():
    asked = [task.attribute for task in pdsqi.build_tasks(NOTE)]
    assert asked == list(pdsqi.NOTE_ONLY_KEYS)
    assert "accurate" not in asked


def test_a_confidential_transcript_cannot_reach_a_prompt():
    """Enforced by absence, not by care: with transcript=None there is no string
    in scope that a prompt could be built from. This is what lets a real
    client's note be scored without the session leaving the machine."""
    for task in pdsqi.build_tasks(NOTE, transcript=None):
        assert "zkousky" not in task.prompt
        assert "Session transcript" not in task.prompt


def test_with_a_transcript_all_eight_are_asked_and_only_two_carry_it():
    tasks = {task.attribute: task.prompt for task in pdsqi.build_tasks(NOTE, TRANSCRIPT)}
    assert len(tasks) == 8
    carrying = {key for key, prompt in tasks.items() if TRANSCRIPT in prompt}
    assert carrying == {"accurate", "thorough"}


def test_every_attribute_is_asked_in_its_own_call():
    tasks = pdsqi.build_tasks(NOTE, TRANSCRIPT)
    assert len({task.unit for task in tasks}) == 8
    assert all(task.prompt.rstrip().endswith(":") for task in tasks)


# --- parsing ---------------------------------------------------------------


def test_the_scale_survives_a_round_trip():
    assert [pdsqi.parse_rating(str(n)) for n in range(1, 6)] == [1, 2, 3, 4, 5]


def test_a_refusal_produces_no_number():
    for answer in ("", "0", "6", "-1", "I cannot rate this."):
        assert pdsqi.parse_rating(answer) is None


def test_yes_and_no_are_read_and_anything_else_is_not():
    assert pdsqi.parse_yes_no("Yes") is True
    assert pdsqi.parse_yes_no("no.") is False
    assert pdsqi.parse_yes_no("NO") is False
    for answer in ("", "maybe", "possibly yes", "1"):
        assert pdsqi.parse_yes_no(answer) is None


def test_this_parser_does_not_fabricate_the_middle_that_tneval_does():
    for refusal in ("", "I cannot rate this."):
        assert tneval.parse_likert(refusal) == 3
        assert pdsqi.parse_rating(refusal) is None


# --- scoring ---------------------------------------------------------------


def test_a_full_set_of_answers_leaves_nothing_missing():
    scored, missing = pdsqi.score(_answers(), expected=pdsqi.ATTRIBUTE_KEYS)
    assert missing == []
    assert scored["useful"] == 4.0


def test_stigmatizing_is_reported_inverted_so_higher_is_always_better():
    """Asked as published, and reported as the fraction free of it: one column
    running the other way inside the same table is a trap for a reader."""
    clean, _ = pdsqi.score(_answers(stigmatizing="No"), expected=pdsqi.ATTRIBUTE_KEYS)
    stigma, _ = pdsqi.score(_answers(stigmatizing="Yes"), expected=pdsqi.ATTRIBUTE_KEYS)
    assert clean["stigmatizing"] == 1.0
    assert stigma["stigmatizing"] == 0.0


def test_an_attribute_that_was_never_asked_is_not_recorded_as_missing():
    """A note scored without a transcript did not fail Accurate and Thorough --
    nobody put them to the judge. Counting them as missing would make every
    confidential note look partial."""
    scored, missing = pdsqi.score(_answers(), expected=pdsqi.NOTE_ONLY_KEYS)
    assert missing == []
    assert "accurate" not in scored
    assert set(scored) == set(pdsqi.NOTE_ONLY_KEYS)


def test_an_attribute_that_was_asked_and_refused_is_named_not_zeroed():
    scored, missing = pdsqi.score(
        _answers(useful="I cannot rate this."), expected=pdsqi.ATTRIBUTE_KEYS
    )
    assert missing == ["useful"]
    assert "useful" not in scored


def test_an_unreadable_yes_no_is_missing_and_not_a_clean_note():
    """The failure this guards: treating anything-but-yes as no would mark every
    unanswered note free of stigmatizing language."""
    scored, missing = pdsqi.score(_answers(stigmatizing="perhaps"), expected=pdsqi.ATTRIBUTE_KEYS)
    assert missing == ["stigmatizing"]
    assert "stigmatizing" not in scored


def test_the_instrument_declines_to_name_a_ranking_measure():
    assert pdsqi.RANKING_MEASURE is None


def test_the_dropped_attribute_is_numbered_the_same_way_twice():
    """The module docstring and the comment above `DROPPED` both say which
    PDSQI-9 item is not asked here, and until 2026-08-27 they disagreed: the
    docstring called `Cited` the ninth attribute and the comment called it item
    1. The kept items are 2 to 9, so the comment was right.

    Held on the code, so the prose cannot drift from the numbering again.
    """
    items = sorted(attribute.item for attribute in pdsqi.ATTRIBUTES)
    assert items == list(range(2, 10)), "items 2 to 9 are kept; item 1 is dropped"
    assert pdsqi.DROPPED == ("cited",)
    assert len(pdsqi.ATTRIBUTES) == 8

    doc = pdsqi.__doc__ or ""
    assert "ninth attribute" not in doc, "item 1 is not the ninth attribute"
    assert "first attribute" in doc


def test_the_caveat_names_the_columns_an_empty_note_wins():
    """`test_empty_note` pins which measures reward a note with nothing in it;
    the instrument's caveat, printed under its columns, has to name the same
    three or the columns read as things a note can win."""
    from tnb.scoring.pdsqi import _CAVEAT

    for name in ("accurate", "succinct", "stigmatising"):
        assert name in _CAVEAT, f"the caveat does not name {name}"
    assert "never as things it can win" in _CAVEAT
