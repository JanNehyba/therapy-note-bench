"""The iCARE scorer: two automatic metrics, one judge, and one flag.

Nothing here touches the network. BERTScore is the one measure that cannot be
exercised offline, so what is pinned instead is that its absence produces None
rather than a column of zeros — a zero would rank every model equally and look
like a measurement.
"""

from __future__ import annotations

import json

import pytest

from tnb import corpus, judge
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


def test_a_note_with_nothing_in_it_scores_zero_not_a_third():
    """The floor, measured on the real corpus rather than constructed.

    `render_note` builds 17 field titles with "Nil" wherever the model wrote
    nothing, and the expert note is built the same way -- so comparing the two
    rendered strings compared our own scaffolding with itself. A note in which
    the model wrote absolutely nothing scored 0.379 on average and 0.770 on one
    session, above what most real models score.
    """
    empty = scorer.render_note({})
    for session in ihope.load("test"):
        candidate, gold = scorer.comparable_pair(empty, session.reference)
        assert scorer.rouge_l(candidate, gold) == 0.0, session.id


def test_only_the_fields_the_expert_answered_are_compared():
    """A field the expert left blank has nothing to compare against."""
    gold = "Patient particulars : Name sasha ; Clinical identifiers : Nil"
    note = scorer.render_note({"section-01": "Name sasha", "section-02": "Ward 4, bed 12"})

    candidate, reference = scorer.comparable_pair(note, gold)

    assert "sasha" in candidate and "sasha" in reference
    assert "Ward 4" not in candidate, "the expert left field 2 blank"


def test_the_labels_never_reach_the_comparison():
    """Three quarters of the old floor was the 17 field titles matching."""
    gold = "Patient particulars : Name sasha ; Clinical identifiers : Nil"
    candidate, reference = scorer.comparable_pair(scorer.render_note({}), gold)

    for title in icare.SECTION_TITLES:
        assert title not in candidate and title not in reference


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

    for section in scorer.TEMPORAL_MEASURES.values():
        assert scorer.temporal_score(note, gold, section) is None


def test_temporal_counts_only_the_fields_the_expert_filled():
    gold = {5: "Second session", 17: "Nil"}

    assert scorer.temporal_score({5: "Second session", 17: "Nil"}, gold, 5) == 1.0
    assert scorer.temporal_score({5: "Nil", 17: "Next week"}, gold, 5) == 0.0
    assert scorer.temporal_score({5: "x", 17: "Next week"}, gold, 17) is None


def test_looking_back_and_looking_forward_are_never_averaged():
    """Blending them hid the finding this track exists to reproduce.

    Measured over all 16 models: looking back scores 0.97-1.00 and looking
    forward 0.00-0.55. The expert notes fill section 5 in 34 of 40 sessions and
    section 17 in only 11, so an average is weighted three to one toward the
    easy one -- it turned 1.00 and 0.09 into 0.78.
    """
    gold = {5: "Second session", 17: "Next Tuesday"}
    note = {5: "Reviewed last week's homework", 17: "Nil"}

    scores = scorer.aggregate(
        scorer.render_note({f"section-{n:02d}": v for n, v in note.items()}),
        " ; ".join(f"{icare.SECTION_TITLES[n - 1]} : {v}" for n, v in gold.items()),
    )

    assert scores.headline["temporal_past"] == 1.0
    assert scores.headline["temporal_next"] == 0.0
    assert "temporal" not in scores.headline, "the blended column must be gone"


def test_a_written_out_refusal_does_not_count_as_looking_forward():
    """gemma4 wrote this into section 17 in 40 of 40 sessions and scored 1.000."""
    gold = {17: "Next Tuesday at the clinic"}
    refusal = "Date: Nil\nPlace: Nil\nTime: Nil\nAccompanying Person: Nil"

    assert scorer.temporal_score({17: refusal}, gold, 17) == 0.0
    assert scorer.temporal_score({17: "Next Tuesday, clinic"}, gold, 17) == 1.0


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


def _icare_candidate(tmp_path):
    """One iCARE note the judge can be pointed at."""
    import json

    from tnb.datasets.base import Session
    from tnb.scoring import icare_run

    session_dir = tmp_path / "einfra" / "icare" / icare.PROMPT_VERSION / "a-model" / "s1"
    session_dir.mkdir(parents=True)
    for number in range(1, 18):
        (session_dir / f"section-{number:02d}.json").write_text(
            json.dumps({"ok": True, "text": "content", "error": None}),
            encoding="utf-8",
        )

    sessions = [Session(id="s1", source="ihope", turns=(), reference="Patient Particulars : x")]
    return next(iter(icare_run.from_generations(sessions, cache_dir=tmp_path)))


class _RefusingJudge:
    """Answers every question but one, the way a rate-limited endpoint does."""

    def __init__(self, config, refuse_at: int) -> None:
        self.config = config
        self._refuse_at = refuse_at
        self._n = 0

    def count_tokens(self, prompt: str) -> int:
        return len(prompt) // 4

    def ask(self, prompt: str):
        self._n += 1
        if self._n == self._refuse_at:
            return judge.Answer(text="", ok=False, error="HTTP429: rate limit")
        return judge.Answer(text="4", ok=True, output_tokens=1)


def test_a_judge_call_that_failed_leaves_a_record_behind(tmp_path):
    """The iCARE twin used to drop it on the floor.

    A refused TRACE dimension and a dimension the scorer does not produce leave
    the same hole in `scores`, so with nothing on disk there was no way to tell
    a rate limit from a measure that was never asked for. `load_cached` rejects
    an `ok: false` record, so writing it costs nothing and it is re-asked next
    run.
    """
    from tnb.scoring import icare_run

    candidate = _icare_candidate(tmp_path)
    client = _RefusingJudge(_judge_config(), refuse_at=2)

    result = icare_run.score_note(
        candidate,
        client,
        judge.Spend(limit_usd=0.0),
        cache_root=tmp_path / "scores",
    )

    assert result.failed == 1
    assert result.asked == 5

    written = sorted((tmp_path / "scores").rglob("*.json"))
    assert len(written) == 5, "every call is recorded, refusals included"
    refused = [json.loads(p.read_text(encoding="utf-8")) for p in written]
    refused = [r for r in refused if not r["ok"]]
    assert len(refused) == 1
    assert refused[0]["error"] == "HTTP429: rate limit"


def test_a_refused_answer_is_not_read_back_as_an_answer(tmp_path):
    """The record exists to be explained, never to be scored."""
    from tnb.scoring import icare_run

    candidate = _icare_candidate(tmp_path)
    spend = judge.Spend(limit_usd=0.0)
    root = tmp_path / "scores"

    icare_run.score_note(candidate, _RefusingJudge(_judge_config(), 2), spend, cache_root=root)

    # Between the runs: the refusal is on disk. Checking after the second run
    # would find nothing, because a successful re-ask overwrites it -- which is
    # right, and would also have made this test pass with no fix at all.
    refused = [
        p for p in root.rglob("*.json") if not json.loads(p.read_text(encoding="utf-8"))["ok"]
    ]
    assert len(refused) == 1

    second = icare_run.score_note(
        candidate, _RefusingJudge(_judge_config(), 99), spend, cache_root=root
    )

    # Asked again despite the record being there: four came from the cache, the
    # refused one did not.
    assert second.cached == 4
    assert second.asked == 1
    assert second.failed == 0
    assert not [
        p for p in root.rglob("*.json") if not json.loads(p.read_text(encoding="utf-8"))["ok"]
    ]


def _judge_config(**overrides) -> judge.JudgeConfig:
    """A config that names no real project -- nothing here reaches a network."""
    base = {
        "project": "a-project",
        "location": "us-west4",
        "credentials_path": "secrets/none.json",
    }
    return judge.JudgeConfig(**{**base, **overrides})


def test_a_dimension_the_judge_did_not_rate_is_named_not_averaged_over():
    """Judge failures cluster on the notes that are hard to read.

    So dividing TRACE by the four dimensions that came back, rather than
    declaring the note incomplete, biases in one direction: the notes that lost
    a dimension are the ones a smaller denominator flatters most.
    """
    answers = {f"trace.{name}": "4" for name, _ in scorer.TRACE_DIMENSIONS}
    answers.pop("trace.accuracy")

    scores = scorer.aggregate("Patient Particulars : x", "Patient Particulars : x", answers)

    assert "trace" not in scores.headline, "not a mean over the survivors"
    assert scores.incomplete["trace"] == ["accuracy"], "named, so the gap has a reason"
    assert scores.is_complete is False


def test_a_note_the_judge_never_rated_at_all_is_incomplete():
    """Zero of five used to pass as complete.

    The branch read `elif ratings`, so a note with no ratings fell through both
    arms: nothing was written to `headline`, nothing to `incomplete`, and the
    note joined its system's average contributing nothing to TRACE while
    counting in the denominator.
    """
    scores = scorer.aggregate("Patient Particulars : x", "Patient Particulars : x", {})

    assert scores.is_complete is False
    assert len(scores.incomplete["trace"]) == len(scorer.TRACE_DIMENSIONS)


def test_a_temporal_measure_with_no_gold_answer_is_absent_not_zero():
    """The experts left section 17 blank in 29 of 40 notes.

    With no gold answer there is nothing to be right or wrong about, so the
    measure is omitted. Scoring it as 0.0 would report every model failing a
    question nobody asked.
    """
    gold = "Patient Particulars : x"  # neither temporal section answered
    scores = scorer.aggregate(gold, gold, {})

    assert "temporal_past" not in scores.headline
    assert "temporal_next" not in scores.headline


def test_the_headline_averages_complete_notes_and_the_detail_averages_all():
    """The twin of a rule the TN-Eval aggregate is tested on and this one was not.

    A note the judge could not finish still says something about the criteria it
    *did* answer, so `by_criterion` keeps it. The headline does not: an average
    over notes measured on different subsets of the dimensions is not a number
    about the model.
    """
    from tnb.scoring import icare_run

    def note(trace: dict[str, str]):
        candidate = icare_run.Candidate(
            provider="einfra",
            system_id="a-model",
            system_type="model",
            system_label="a-model",
            session_id="1",
            conversation="",
            note={},
            reference="Patient Particulars : x",
        )
        scores = scorer.aggregate("Patient Particulars : x", "Patient Particulars : x", trace)
        return icare_run.NoteResult(candidate=candidate, scores=scores)

    full = {f"trace.{name}": "5" for name, _ in scorer.TRACE_DIMENSIONS}
    short = dict(full)
    short.pop("trace.accuracy")
    short["trace.comprehensiveness"] = "1"

    aggregate = icare_run.SystemAggregate(notes=[note(full), note(short)])

    assert len(aggregate.complete) == 1
    assert aggregate.n_partial == 1

    metrics = aggregate.metrics()
    assert metrics.headline["trace"] == 5.0, "the complete note only"
    assert metrics.detail["comprehensiveness"] == 3.0, "both notes, (5 + 1) / 2"


class _ExplodingJudge(_RefusingJudge):
    """Raises on one note, the way a 429 on `count_tokens` does -- no retry loop."""

    def __init__(self, config, boom_on: str) -> None:
        super().__init__(config, refuse_at=0)
        self._boom_on = boom_on

    def count_tokens(self, prompt: str) -> int:
        if self._boom_on in prompt:
            raise RuntimeError("HTTP429: rate limit")
        return len(prompt) // 4


def _many_candidates(tmp_path, session_ids):
    from tnb.datasets.base import Session
    from tnb.scoring import icare_run

    sessions = []
    for session_id in session_ids:
        session_dir = tmp_path / "einfra" / "icare" / icare.PROMPT_VERSION / "a-model" / session_id
        session_dir.mkdir(parents=True)
        for number in range(1, 18):
            (session_dir / f"section-{number:02d}.json").write_text(
                json.dumps({"ok": True, "text": f"content for {session_id}", "error": None}),
                encoding="utf-8",
            )
        sessions.append(
            Session(
                id=session_id,
                source="ihope",
                turns=(),
                reference=f"Patient Particulars : {session_id}",
            )
        )
    return list(icare_run.from_generations(sessions, cache_dir=tmp_path))


def test_a_note_that_raised_takes_the_whole_run_down(tmp_path):
    """`score_many` had no test on either track, and its first version was mine.

    It submitted the futures and never called `.result()`, so anything but a
    budget stop -- a 429 on `count_tokens`, which has no retry loop, or a
    timeout -- deleted that note from the average with no traceback, no stderr
    and no exit code. The notes that vanish are the long ones: both the slowest
    to count and the likeliest to time out, so the loss is not random.
    """
    from tnb.scoring import icare_run

    candidates = _many_candidates(tmp_path, ["s1", "s2", "s3"])
    client = _ExplodingJudge(_judge_config(), boom_on="content for s2")

    with pytest.raises(RuntimeError, match="429"):
        icare_run.score_many(
            candidates, client, judge.Spend(limit_usd=0.0), cache_root=tmp_path / "scores"
        )


def test_results_come_back_in_the_order_they_were_submitted(tmp_path):
    """However the threads interleave. A run has to be reproducible."""
    from tnb.scoring import icare_run

    candidates = _many_candidates(tmp_path, ["s1", "s2", "s3"])
    scored = icare_run.score_many(
        candidates,
        _RefusingJudge(_judge_config(), refuse_at=0),
        judge.Spend(limit_usd=0.0),
        cache_root=tmp_path / "scores",
    )

    assert [note.candidate.session_id for note in scored] == [
        candidate.session_id for candidate in candidates
    ]


def test_the_temporal_denominators_in_the_column_text_match_the_corpus():
    """Those two columns publish fractions of 34 and of 11, not of 40.

    A `temporal_next` of 0.09 is one session out of eleven, which is a much
    weaker statement than the same figure over the corpus, and the only place
    the reader is told is the column definition on the page. The numbers there
    are written out in prose, so they can go stale without anything failing --
    unless this asks the corpus.
    """
    profile = corpus.profile_ihope()
    if profile is None:
        pytest.skip("iHOPE not fetched; the profile cannot be measured here")

    answered = {section.number: section.filled for section in profile}

    for measure, number in scorer.TEMPORAL_MEASURES.items():
        text = scorer.MEASURES[measure]["definition"]
        assert f"{answered[number]} sessions" in text, (
            f"{measure} says {text!r} but the experts answered section {number} "
            f"in {answered[number]} of the sessions"
        )


def test_bertscore_is_cached_on_the_pair_it_measures(tmp_path, monkeypatch):
    """It depends on the two strings and on nothing else -- not the judge, not
    the run -- and it was recomputed from scratch every time, loading
    roberta-large and spending about half an hour on 640 pairs before the first
    judge question was asked."""
    calls = []

    def fake_score(candidates, references, **_kwargs):
        calls.append(list(candidates))
        return None, None, [0.5 + 0.1 * i for i in range(len(candidates))]

    monkeypatch.setitem(
        __import__("sys").modules, "bert_score", type("m", (), {"score": fake_score})
    )
    cache = tmp_path / "bertscore.json"

    first = scorer.bertscore(["a note", "another"], ["gold", "gold two"], cache=cache)
    second = scorer.bertscore(["a note", "another"], ["gold", "gold two"], cache=cache)

    assert first == second
    assert len(calls) == 1, "the second run computed nothing"


def test_a_pair_that_changed_is_recomputed_and_the_rest_is_not(tmp_path, monkeypatch):
    """A re-generated note must not keep its predecessor's score, and the
    fifteen models that did not change must not pay for the one that did."""
    calls = []

    def fake_score(candidates, references, **_kwargs):
        calls.append(list(candidates))
        return None, None, [0.9] * len(candidates)

    monkeypatch.setitem(
        __import__("sys").modules, "bert_score", type("m", (), {"score": fake_score})
    )
    cache = tmp_path / "bertscore.json"

    scorer.bertscore(["first", "second"], ["gold", "gold"], cache=cache)
    scorer.bertscore(["first", "second, re-generated"], ["gold", "gold"], cache=cache)

    assert calls[1] == ["second, re-generated"], "only the changed one"


def test_a_missing_dependency_is_still_reported_as_absent(tmp_path, monkeypatch):
    """None rather than zero. A column of zeros would rank every model equally
    and look like a measurement."""
    import builtins

    real_import = builtins.__import__

    def refuse(name, *args, **kwargs):
        if name == "bert_score":
            raise ImportError("not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(__import__("sys").modules, "bert_score", raising=False)
    monkeypatch.setattr(builtins, "__import__", refuse)

    assert scorer.bertscore(["a"], ["b"], cache=tmp_path / "x.json") is None
