"""The iCARE scorer: two automatic metrics, one judge, and one flag.

Nothing here touches the network. BERTScore is the one measure that cannot be
exercised offline, so what is pinned instead is that its absence produces None
rather than a column of zeros — a zero would rank every model equally and look
like a measurement.
"""

from __future__ import annotations

import pytest

from tnb import corpus
from tnb.datasets import ihope
from tnb.scoring import icare as scorer
from tnb.tasks import icare

GOLD = (
    "Patient Particulars : Name sasha; sex female ; "
    "Clinical Identifiers : Nil ; "
    "Referral Information : Nil ; "
    "Therapist Information : Nil ; "
    "Session Details : Second session, reviewed last week's homework ; "
    "Presenting Complaints : Low mood and drinking most evenings"
)


# --- splitting a note into its 17 fields --------------------------------------


def test_a_real_gold_note_splits_into_all_seventeen_fields():
    """Not a fixture: the actual corpus, because the labels are hand-written."""
    session = ihope.load("test", limit=1)[0]

    found = scorer.split_sections(session.reference)

    assert set(found) == set(range(1, 18)), sorted(set(range(1, 18)) - set(found))


def test_no_label_in_the_corpus_goes_unmatched():
    """The real invariant. Measured over all 40 notes: 524 labelled parts, zero
    that `_match_section` could not place.

    An unmatched label would be a silent zero for that field -- the model would
    be compared against a section the scorer failed to find rather than against
    one the expert left out.
    """
    unmatched: list[tuple[str, str]] = []
    parts = 0
    for session in ihope.load("test"):
        for part in session.reference.split(corpus.FIELD_SEPARATOR):
            label, separator, _value = part.partition(":")
            if not separator:
                continue
            parts += 1
            if corpus._match_section(label) is None:
                unmatched.append((session.id, label.strip()[:60]))

    assert parts > 500, "the corpus shrank; recheck before trusting this"
    assert not unmatched, f"labels the scorer could not place: {unmatched}"


def test_the_expert_notes_do_not_all_carry_all_seventeen_fields():
    """A fact about the corpus, pinned so it cannot be mistaken for a bug.

    Measured on the 40 held-out notes: 22 carry all 17 labels and 18 carry
    between 7 and 12. The sparsest fields are Clinical identifiers, Assessments
    and Reflections by the therapist, each present in 22 of 40.

    This is why `temporal_score` takes its denominator from what the expert
    answered rather than from what the form asks: a model cannot be marked down
    for leaving blank a field the expert never filled in either.
    """
    sizes = [len(scorer.split_sections(s.reference)) for s in ihope.load("test")]

    assert len(sizes) == 40
    assert sum(1 for n in sizes if n == 17) == 22
    assert min(sizes) >= 7, "a note this sparse would be worth re-reading"


def test_nil_is_an_answer_and_not_content():
    sections = scorer.split_sections(GOLD)

    assert scorer.is_filled(sections[1]) is True
    assert scorer.is_filled(sections[2]) is False  # "Nil"


def test_an_ambiguous_label_is_credited_to_nobody():
    """`_match_section` refuses rather than guessing; this is that, end to end."""
    assert corpus._match_section("Psychotherapy") is None


# --- ROUGE-L ------------------------------------------------------------------


def test_a_note_identical_to_the_expert_note_scores_one():
    assert scorer.rouge_l(GOLD, GOLD) == pytest.approx(1.0)


def test_a_note_with_nothing_in_common_scores_zero():
    assert scorer.rouge_l("aardvark zebra", "quantum trombone") == 0.0


def test_an_empty_note_scores_zero_rather_than_raising():
    assert scorer.rouge_l("", GOLD) == 0.0
    assert scorer.rouge_l(GOLD, "") == 0.0


def test_it_is_an_f_measure_not_recall():
    """Recall alone rewards a note that repeats the whole transcript.

    At least one model in this benchmark does exactly that when it cannot decide
    what to leave out, so padding must cost something.
    """
    reference = "the client reported low mood"
    exact = scorer.rouge_l(reference, reference)
    padded = scorer.rouge_l(reference + " " + "filler " * 200, reference)

    assert padded < exact
    assert padded < 0.5


def test_word_order_matters():
    """A subsequence, not a bag of words."""
    forward = scorer.rouge_l("a b c d", "a b c d")
    scrambled = scorer.rouge_l("d c b a", "a b c d")

    assert scrambled < forward


# --- temporal -----------------------------------------------------------------


def test_temporal_reads_only_the_two_time_bearing_sections():
    assert ihope.TEMPORAL_SECTIONS == (5, 17)


def test_a_model_is_not_marked_down_for_a_blank_the_expert_left_blank():
    """The denominator is what the expert answered, not what was asked."""
    gold = {5: "Nil", 17: "Nil"}
    note = {5: "Nil", 17: "Nil"}

    assert scorer.temporal_score(note, gold) is None


def test_temporal_counts_only_the_fields_the_expert_filled():
    gold = {5: "Second session", 17: "Nil"}

    assert scorer.temporal_score({5: "Second session", 17: "Nil"}, gold) == 1.0
    assert scorer.temporal_score({5: "Nil", 17: "Next week"}, gold) == 0.0


# --- TRACE --------------------------------------------------------------------


def test_five_dimensions_are_asked_about_one_note():
    tasks = scorer.build_trace_tasks("a note", "a transcript")

    assert len(tasks) == 5
    assert [t.dimension for t in tasks] == [name for name, _ in scorer.TRACE_DIMENSIONS]
    assert len({t.unit for t in tasks}) == 5, "two questions would overwrite each other"


def test_the_transcript_and_the_note_both_reach_the_prompt():
    task = scorer.build_trace_tasks("THE NOTE", "THE TRANSCRIPT")[0]

    assert "THE NOTE" in task.prompt
    assert "THE TRANSCRIPT" in task.prompt


def test_trace_is_the_mean_of_the_five():
    answers = {f"trace.{name}": "4" for name, _ in scorer.TRACE_DIMENSIONS}
    answers["trace.accuracy"] = "2"

    scores = scorer.aggregate("a note", GOLD, answers)

    assert scores.headline["trace"] == pytest.approx((4 + 4 + 2 + 4 + 4) / 5)
    assert scores.by_criterion["accuracy"] == 2.0


def test_a_note_missing_a_dimension_is_named_rather_than_averaged():
    """Judge failures cluster on hard notes, so dividing by the survivors is biased."""
    answers = {f"trace.{name}": "5" for name, _ in scorer.TRACE_DIMENSIONS[:3]}

    scores = scorer.aggregate("a note", GOLD, answers)

    assert "trace" not in scores.headline
    assert scores.incomplete["trace"] == ["comprehensiveness", "expression"]
    assert scores.is_complete is False


# --- BERTScore ----------------------------------------------------------------


def test_bertscore_is_none_when_the_extra_is_absent(monkeypatch):
    """None, never zero: a column of zeros ranks every model equally."""
    import builtins

    real_import = builtins.__import__

    def no_bert(name, *args, **kwargs):
        if name == "bert_score":
            raise ImportError("not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_bert)

    assert scorer.bertscore(["a note"], ["a reference"]) is None


def test_an_absent_bertscore_leaves_the_column_out_rather_than_zeroing_it():
    scores = scorer.aggregate("a note", GOLD, bert=None)

    assert "bertscore" not in scores.headline
    assert "rouge_l" in scores.headline


# --- putting a note back together ---------------------------------------------


def test_generated_sections_render_in_the_shape_the_expert_note_uses():
    """17 units in, one labelled string out -- otherwise it is a shape mismatch."""
    rendered = scorer.render_note({"section-01": "Name sasha", "section-06": "Low mood"})

    found = scorer.split_sections(rendered)
    assert set(found) == set(range(1, 18))
    assert found[1] == "Name sasha"
    assert scorer.is_filled(found[1])
    assert not scorer.is_filled(found[2]), "an unwritten section renders as Nil"


def test_a_rendered_note_uses_the_corpus_separator():
    assert corpus.FIELD_SEPARATOR.strip() in scorer.render_note({"section-01": "x"})


def test_every_section_title_survives_the_round_trip():
    """The renderer's labels must be the ones the matcher recognises."""
    rendered = scorer.render_note({f"section-{n:02d}": f"value {n}" for n in range(1, 18)})
    found = scorer.split_sections(rendered)

    assert len(found) == len(icare.SECTION_TITLES) == 17
    assert all(found[n] == f"value {n}" for n in range(1, 18))


# --- the track's own contract -------------------------------------------------


def test_the_track_declines_to_name_a_ranking_measure():
    """Its columns disagree on purpose; ranking on one would hide that."""
    assert scorer.RANKING_MEASURE is None


def test_every_measure_the_page_shows_is_documented_here():
    from tnb import report, results

    displayed = {key for key, _ in report.COLUMNS[results.TRACK_ICARE]}

    assert displayed <= set(scorer.MEASURES)


def test_trace_says_it_has_no_human_anchor_wherever_it_appears():
    """A CLAUDE.md invariant, asserted rather than promised."""
    assert "no human anchor" in scorer.MEASURES["trace"]["caveat"]


def test_a_section_the_endpoint_refused_does_not_score_as_a_blank_field(tmp_path):
    """The same misattribution one level down from the coverage row.

    A section rendered as "Nil" scores as a field the model chose to leave
    empty. A rate limit is not a choice: glm-5 lost one section to e-INFRA
    refusing a fourth parallel request, and that would have counted against its
    temporal and ROUGE-L scores.
    """
    import json

    from tnb.datasets.base import Session
    from tnb.scoring import icare_run

    session_dir = tmp_path / "einfra" / "icare" / icare.PROMPT_VERSION / "a-model" / "s1"
    session_dir.mkdir(parents=True)
    for number in range(1, 18):
        failed = number == 3
        (session_dir / f"section-{number:02d}.json").write_text(
            json.dumps(
                {
                    "ok": not failed,
                    "text": "" if failed else "content",
                    "error": "HTTP429: rate limit" if failed else None,
                }
            ),
            encoding="utf-8",
        )

    sessions = [Session(id="s1", source="ihope", turns=(), reference="Patient Particulars : x")]
    assert list(icare_run.from_generations(sessions, cache_dir=tmp_path)) == []


def test_a_section_the_model_failed_to_write_is_still_scored(tmp_path):
    """Its own empty answer is the model's doing, and "Nil" is honest for that."""
    import json

    from tnb.datasets.base import Session
    from tnb.scoring import icare_run

    session_dir = tmp_path / "einfra" / "icare" / icare.PROMPT_VERSION / "a-model" / "s1"
    session_dir.mkdir(parents=True)
    for number in range(1, 18):
        failed = number == 3
        (session_dir / f"section-{number:02d}.json").write_text(
            json.dumps(
                {
                    "ok": not failed,
                    "text": "" if failed else "content",
                    "error": "empty content" if failed else None,
                }
            ),
            encoding="utf-8",
        )

    sessions = [Session(id="s1", source="ihope", turns=(), reference="Patient Particulars : x")]
    assert len(list(icare_run.from_generations(sessions, cache_dir=tmp_path))) == 1
