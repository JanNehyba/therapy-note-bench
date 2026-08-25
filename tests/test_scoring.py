"""TN-Eval's scoring protocol, and the judge that answers its questions.

Every failure mode pinned here was met for real on the first pilot: a judge
that thought until it had no room to answer, a token that raced itself, and a
note whose sections score differently enough that averaging them the wrong way
changes the ranking. Nothing here touches the network.
"""

from __future__ import annotations

import hashlib
import json

import httpx
import pytest

from tnb import judge
from tnb.scoring import run as scoring
from tnb.scoring import tneval

NOTE = {
    "subjective": "Client reports drinking. She feels guilty about it.",
    "objective": "Client was cooperative.",
    "assessment": "Risky use interacting with low mood.",
    "plan": "Cut down to two drinks. Follow up next week.",
}
CONVERSATION = "\n\ntherapist: How was your week?\nclient: I drank again."


# --- the prompts are TN-Eval's ----------------------------------------------


def test_every_judge_prompt_is_byte_identical_to_tn_evals():
    for name, digest in tneval.UPSTREAM_SHA256.items():
        text = getattr(tneval, name)
        assert hashlib.sha256(text.encode()).hexdigest() == digest, name


def test_the_rubric_is_the_published_one():
    """23 criteria, split 6/5/8/4 across the SOAP sections, as the paper says."""
    assert len(tneval.CHECKBOX_MAPPING) == 23
    assert [len(tneval.rubrics_for(section)) for section in tneval.SOAP_SECTIONS] == [6, 5, 8, 4]


def test_one_note_asks_the_protocol_s_questions():
    tasks = tneval.build_tasks(NOTE, CONVERSATION)
    kinds = {kind: sum(1 for t in tasks if t.kind == kind) for t in tasks for kind in [t.kind]}

    assert kinds["rubric_completeness"] == 23, "one per rubric item"
    assert kinds["likert_completeness"] == 4, "one per SOAP section"
    assert kinds["likert_faithfulness"] == 4
    assert kinds["rubric_conciseness"] == 6, "one per sentence across the four sections"


def test_the_conversation_reaches_only_the_prompts_that_ask_for_it():
    """The Likert prompts embed the transcript; the rubric ones do not. That is
    the whole reason a rubric call costs a tenth of a Likert call."""
    tasks = {t.kind: t for t in tneval.build_tasks(NOTE, CONVERSATION)}
    assert "I drank again" in tasks["likert_faithfulness"].prompt
    assert "I drank again" not in tasks["rubric_completeness"].prompt


def test_a_question_is_cached_under_a_stable_unit():
    tasks = tneval.build_tasks(NOTE, CONVERSATION)
    units = [task.unit for task in tasks]
    assert len(units) == len(set(units)), "two questions would overwrite each other"
    assert "subjective.rubric_completeness.subjective-chief-complaint" in units


# --- TN-Eval's parsers, quirks included -------------------------------------


@pytest.mark.parametrize("answer,expected", [("Yes", 1), ("yes.", 1), ("No", 0), ("", 0), ("?", 0)])
def test_anything_that_is_not_yes_is_a_no(answer, expected):
    """Their parser, reproduced: a judge that will not answer scores the item as
    missing. Improving on that would make our numbers incomparable with theirs."""
    assert tneval.parse_yes_no(answer) == expected


@pytest.mark.parametrize(
    "answer,expected",
    [("4", 4), (" 5 ", 5), ("Rating: 2", 2), ("nonsense", 3), ("9", 3)],
)
def test_an_unparseable_likert_becomes_three(answer, expected):
    assert tneval.parse_likert(answer) == expected


def test_sentences_are_not_split_on_an_abbreviation():
    """Conciseness is a ratio over sentences, so a bad split changes the score."""
    sentences = tneval.split_sentences("Seen by Dr. Novak. Client was calm.")
    assert sentences == ["Seen by Dr. Novak. Client was calm."] or len(sentences) == 2
    assert all(s.strip() for s in sentences)


# --- aggregation -------------------------------------------------------------


def test_a_section_score_is_the_fraction_of_its_criteria_found():
    keys = tneval.criteria_keys("plan")  # four of them
    answers = {f"plan.rubric_completeness.{key}": "Yes" for key in keys[:3]}
    answers[f"plan.rubric_completeness.{keys[3]}"] = "No"

    scores = tneval.aggregate(answers)
    assert scores.by_section["plan"]["completeness"] == 0.75


def test_a_section_with_no_sentences_scores_zero_for_conciseness():
    """TN-Eval's own rule, kept -- but only where we can see that it applies.

    A section that really has no sentences scores 0, exactly as their code does.
    Knowing it has none requires the task list; see the test below for what
    happens without it.
    """
    empty = {"subjective": "", "objective": "", "assessment": "", "plan": ""}
    tasks = tneval.build_tasks(empty, CONVERSATION)
    scores = tneval.aggregate({"plan.rubric_completeness.plan-homework": "Yes"}, tasks)

    assert scores.by_section["plan"]["conciseness"] == 0.0


def test_the_headline_averages_sections_not_criteria():
    """Documented choice: an eight-item section is not twice as important as a
    four-item one. by_criterion is kept so anyone can recompute item-weighted."""
    answers = {}
    for key in tneval.criteria_keys("subjective"):  # 6 items, all found
        answers[f"subjective.rubric_completeness.{key}"] = "Yes"
    for key in tneval.criteria_keys("plan"):  # 4 items, none found
        answers[f"plan.rubric_completeness.{key}"] = "No"

    scores = tneval.aggregate(answers)
    assert scores.headline["completeness"] == 0.5
    assert scores.by_criterion, "the per-criterion detail survives"


def test_every_criterion_is_reported_individually():
    keys = tneval.criteria_keys("objective")
    answers = {f"objective.rubric_completeness.{keys[0]}": "Yes"}
    assert tneval.aggregate(answers).by_criterion[keys[0]] == 1.0


# --- the judge client --------------------------------------------------------


def test_the_answer_gets_room_after_the_thinking():
    """The pilot's first run capped output at 64 against a 128-token thinking
    budget and 26% of answers came back empty with finishReason MAX_TOKENS."""
    assert judge.output_ceiling(128) > 128
    assert judge.output_ceiling(128) == 128 + judge.ANSWER_TOKENS


def _config(**overrides) -> judge.JudgeConfig:
    base = {
        "project": "a-project",
        "location": "us-west4",
        "credentials_path": "secrets/none.json",
        "retries": 2,
        "backoff_s": 0,
    }
    return judge.JudgeConfig(**{**base, **overrides})


def _client(monkeypatch, responses) -> tuple[judge.Judge, list]:
    client = judge.Judge(_config())
    monkeypatch.setattr(client, "_token", lambda **_: "test-token")
    sent = []
    queue = list(responses)

    def fake_post(url, **kwargs):
        sent.append(kwargs)
        return queue.pop(0) if queue else responses[-1]

    monkeypatch.setattr(judge.httpx, "post", fake_post)
    return client, sent


def _reply(text="Yes", *, thinking=57, finish="STOP") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": finish}],
            "usageMetadata": {
                "promptTokenCount": 126,
                "candidatesTokenCount": 1,
                "thoughtsTokenCount": thinking,
            },
        },
    )


def test_an_answer_comes_back_with_its_thinking_counted(monkeypatch):
    client, sent = _client(monkeypatch, [_reply()])
    answer = client.ask("is this a chief complaint?")

    assert answer.ok and answer.text == "Yes"
    assert answer.thinking_tokens == 57
    # Read from the constant, not repeated. The budget moved from 128 to 256
    # when 262 of gemini-3.1-pro's answers turned out to be truncated mid-thought,
    # and a hard-coded copy here only says the test was written first.
    budget = sent[0]["json"]["generationConfig"]["thinkingConfig"]["thinkingBudget"]
    assert budget == judge.DEFAULT_THINKING_BUDGET


def test_an_empty_answer_is_a_failure_not_a_no(monkeypatch):
    """Scoring it would silently record a 'No' that nobody said."""
    client, _ = _client(monkeypatch, [_reply(text="", finish="MAX_TOKENS")])
    answer = client.ask("q")

    assert not answer.ok
    assert "MAX_TOKENS" in answer.error


def test_a_401_mid_run_mints_a_new_token_and_asks_again(monkeypatch):
    """Two threads refreshing at once produced exactly this on the pilot."""
    client, _ = _client(monkeypatch, [httpx.Response(401, text="expired"), _reply()])
    refreshes = []
    monkeypatch.setattr(client, "_token", lambda **kw: refreshes.append(kw) or "t")

    assert client.ask("q", sleep=lambda _: None).ok
    assert refreshes[-1].get("force_refresh") is True


def test_a_bad_request_is_not_retried(monkeypatch):
    client, sent = _client(monkeypatch, [httpx.Response(400, text="bad model")])
    answer = client.ask("q", sleep=lambda _: None)

    assert len(sent) == 1
    assert not answer.ok and "HTTP400" in answer.error


def test_quota_errors_are_retried(monkeypatch):
    client, sent = _client(monkeypatch, [httpx.Response(429, text="quota"), _reply()])
    assert client.ask("q", sleep=lambda _: None).ok
    assert len(sent) == 2


# --- money -------------------------------------------------------------------


def test_the_ceiling_stops_the_run_before_it_is_crossed():
    spend = judge.Spend(limit_usd=0.01)
    spend.input_tokens, spend.output_tokens = 10_000, 10_000
    assert spend.would_exceed("gemini-2.5-pro", 2_000)


def test_thinking_is_billed_as_output():
    """It never reaches us, and it is most of what a judge call costs."""
    spend = judge.Spend(limit_usd=100)
    spend.record(
        "gemini-2.5-pro", judge.Answer(text="Yes", ok=True, output_tokens=1, thinking_tokens=57)
    )
    assert spend.output_tokens == 58


def test_an_unknown_judge_model_is_not_silently_free():
    """A price of zero would disable the ceiling. Better to notice.

    This test asserted `== 0.0`, which is the behaviour its own docstring calls
    a problem: the ceiling was off for every model missing from the price table,
    and the run reported a total of $0.00 while spending real money. That was
    all five 3.x judge candidates and all three GPT ones.
    """
    with pytest.raises(judge.UnpricedModel, match="some-new-model"):
        judge.estimate_usd("some-new-model", 1_000_000, 1_000_000)


def test_a_priced_model_still_costs_what_it_costs():
    assert judge.estimate_usd("gpt-5.6-terra", 1_000_000, 0) == pytest.approx(2.00)
    assert judge.estimate_usd("gpt-5.6-terra", 0, 1_000_000) == pytest.approx(12.00)


def test_the_ceiling_refuses_to_run_an_unpriced_judge():
    """Refusing is the point: a guard that stops guarding is worse than none."""
    spend = judge.Spend(limit_usd=10.0)

    with pytest.raises(judge.UnpricedModel, match="cannot be enforced"):
        spend.would_exceed("some-new-model", 1000)


def test_no_ceiling_is_an_explicit_choice_not_an_accident():
    """`--max-judge-usd 0` runs an unpriced model, having said so out loud."""
    spend = judge.Spend(limit_usd=0.0)

    assert spend.would_exceed("some-new-model", 1_000_000) is False


def test_the_ceiling_still_stops_a_priced_judge():
    spend = judge.Spend(limit_usd=0.01)
    spend.input_tokens = 10_000_000

    assert spend.would_exceed("gpt-5.6-terra", 1000) is True


def test_an_unpriced_run_reports_no_total_rather_than_zero():
    """A number that looks measured, and is not, is the worse of the two."""
    spend = judge.Spend(limit_usd=0.0)
    spend.input_tokens = 1_000_000

    assert spend.usd("some-new-model") is None
    assert spend.usd("gpt-5.6-terra") == pytest.approx(2.00)


def test_every_judge_candidate_has_a_price():
    """A candidate that cannot be costed cannot be run under a ceiling."""
    missing = [m for m in judge.JUDGE_CANDIDATES if m not in judge.PRICES_USD_PER_MTOK]

    assert not missing, f"judge candidates with no price: {missing}"


# --- the cache ---------------------------------------------------------------


def test_a_changed_thinking_budget_invalidates_a_cached_answer(tmp_path):
    path = judge.cache_path(
        "gemini-2.5-pro", "v1", "tneval", "therapist", "0", "a.b", root=tmp_path
    )
    judge.write_cached(
        path, {"ok": True, "answer": "Yes", "judge_fingerprint": _config().fingerprint()}
    )

    assert judge.load_cached(path, _config().fingerprint()) is not None
    assert judge.load_cached(path, _config(thinking_budget=512).fingerprint()) is None


def test_a_failed_answer_is_never_a_cache_hit(tmp_path):
    path = judge.cache_path(
        "gemini-2.5-pro", "v1", "tneval", "therapist", "0", "a.b", root=tmp_path
    )
    judge.write_cached(
        path, {"ok": False, "answer": "", "judge_fingerprint": _config().fingerprint()}
    )
    assert judge.load_cached(path, _config().fingerprint()) is None


# --- what gets scored --------------------------------------------------------


def test_the_reference_systems_are_the_therapist_and_two_dated_models():
    from tnb.datasets.base import Session, Turn

    session = Session(
        id="0",
        source="tneval",
        turns=(Turn("therapist", "Hello."),),
        meta={
            "human_note": NOTE,
            "model_notes": {
                "llm_llama31_70B": {"note": NOTE},
                "llm_mistral_large_v2": {"note": NOTE},
            },
        },
    )
    candidates = list(scoring.from_reference([session]))

    assert [c.system_type for c in candidates] == [
        "reference-human",
        "reference-model",
        "reference-model",
    ]
    assert candidates[0].system_id == "therapist"


def test_rows_carry_the_judge_that_produced_them(tmp_path):
    from tnb.datasets.base import Session, Turn

    session = Session(
        id="0", source="tneval", turns=(Turn("therapist", "Hi."),), meta={"human_note": NOTE}
    )
    (candidate,) = list(scoring.from_reference([session]))
    result = scoring.NoteResult(
        candidate=candidate,
        scores=tneval.Scores(
            headline={"completeness": 0.5}, by_section={"plan": {"completeness": 0.5}}
        ),
    )

    (row,) = scoring.to_rows([result], judge_model="gemini-2.5-pro")
    assert row.judge_model == "gemini-2.5-pro"
    assert row.judge_prompt_version == tneval.JUDGE_PROMPT_VERSION
    assert row.system_type == "reference-human"
    assert row.metrics.headline["completeness"] == 0.5


def test_a_scored_row_is_json_round_trippable():
    from tnb import results

    row = results.Row(
        track=results.TRACK_TNEVAL,
        system_id="therapist",
        system_type="reference-human",
        provider="tneval",
        judge_model="gemini-2.5-pro",
        judge_prompt_version=tneval.JUDGE_PROMPT_VERSION,
        n_sessions_attempted=50,
    )
    assert results.from_dict(json.loads(json.dumps(row.to_dict()))) == row


def _one_result():
    from tnb.datasets.base import Session, Turn

    session = Session(
        id="0", source="tneval", turns=(Turn("therapist", "Hi."),), meta={"human_note": NOTE}
    )
    (candidate,) = list(scoring.from_reference([session]))
    return candidate, scoring.NoteResult(candidate=candidate, scores=tneval.Scores())


def test_a_partial_scoring_run_does_not_look_complete():
    """A pilot over one session of fifty must read as 1 of 50 judged, not as
    full coverage."""
    candidate, result = _one_result()

    (row,) = scoring.to_rows(
        [result],
        judge_model="gemini-2.5-pro",
        n_generated={("tneval", "therapist"): 50},
        n_attempted=50,
    )
    assert row.n_sessions_scored == 1
    assert row.n_sessions_attempted == 50


def test_notes_the_judge_has_not_read_are_not_generation_failures():
    """The defect this replaces: gemma4 wrote all fifty notes and the README
    published "17/50 (33 unusable)" because the judge was 17 in. Judging
    progress and generation coverage are different facts."""
    candidate, result = _one_result()

    (row,) = scoring.to_rows(
        [result],
        judge_model="gemini-2.5-pro",
        n_generated={("tneval", "therapist"): 50},
        n_attempted=50,
    )
    assert row.n_sessions_generated == 50, "every note was written"
    assert row.n_sessions_scored == 1, "one has been judged"
    assert row.n_failed == 0, "nothing failed to generate"


def test_a_model_that_really_lost_notes_still_reports_them():
    """gpt-oss-120b's eight unreadable notes are a real generation failure and
    must survive the fix that stopped inventing fake ones."""
    candidate, result = _one_result()

    (row,) = scoring.to_rows(
        [result],
        judge_model="gemini-2.5-pro",
        n_generated={("tneval", "therapist"): 42},
        n_attempted=50,
    )
    assert (row.n_sessions_generated, row.n_failed) == (42, 8)


# --- what the corpus actually contains --------------------------------------


def test_a_gold_note_field_is_matched_to_exactly_one_section(tmp_path):
    """ "Psychotherapy type" and "Psychotherapy technique" share a long prefix.
    A loose match credited one field with the other's answers, and the profile
    reported 41 of 58 for a 40-session corpus."""
    from tnb import corpus

    assert corpus._match_section("Psychotherapy Type") == 10
    assert corpus._match_section("Psychotherapy Technique ") == 11
    assert corpus._match_section("Psychotherapy") is None, "ambiguous counts for nobody"


def test_nil_is_read_as_an_empty_field(tmp_path):
    """The protocol asks for "Nil" when the transcript does not say, so a note
    full of Nil is a note full of blanks -- and the page has to show that."""
    from tnb import corpus

    note = " ; ".join(
        [
            "Patient Particulars: Name tim; sex- male",
            "Clinical Identifiers: Nil",
            "Crisis Markers: nil",
            "Action Plan : ",
        ]
    )
    path = tmp_path / "ihope_test.json"
    path.write_text(json.dumps([{"id": "1", "summary": note, "dialogue": ""}]), encoding="utf-8")

    profile = {section.number: section for section in corpus.profile_ihope(path)}
    assert profile[1].filled == 1
    assert profile[2].filled == 0 and profile[2].total == 1
    assert profile[8].filled == 0, "lower-case nil counts as empty too"
    assert profile[16].filled == 0, "so does an empty value"


def test_no_corpus_means_no_profile_rather_than_zeros(tmp_path):
    """Publishing 0% filled because the corpus was never downloaded would be a
    claim about the data instead of a statement about this machine."""
    from tnb import corpus

    assert corpus.profile_ihope(tmp_path / "absent.json") is None


# --- a zero that was never measured -----------------------------------------


def test_a_section_whose_conciseness_was_never_asked_is_not_scored_zero():
    """TN-Eval's zero is for a section with no sentences in it. A section whose
    answers simply have not arrived is absent, and scoring it 0.0 makes an
    unfinished run look like a model that wrote nothing but padding."""
    tasks = tneval.build_tasks(NOTE, CONVERSATION)
    # Every completeness question answered, so the section is scored at all;
    # only the conciseness answers are missing, which is what this is about.
    answers = {f"plan.rubric_completeness.{key}": "Yes" for key in tneval.criteria_keys("plan")}

    scored = tneval.aggregate(answers, tasks)
    assert "completeness" in scored.by_section["plan"]
    assert "conciseness" not in scored.by_section["plan"]


def test_a_section_with_no_sentences_still_scores_zero():
    """Their rule, reproduced: an empty note segment has nothing to be concise
    about and scores 0 rather than being skipped."""
    empty = {"subjective": "", "objective": "", "assessment": "", "plan": ""}
    tasks = tneval.build_tasks(empty, CONVERSATION)
    scored = tneval.aggregate({"plan.rubric_completeness.plan-homework": "No"}, tasks)

    assert scored.by_section["plan"]["conciseness"] == 0.0


def test_without_the_task_list_no_conciseness_is_invented():
    """A caller that cannot know what was asked gets no conciseness at all.

    This asserted `== 0.0`, which is the fabrication rather than the rule. A
    zero says "the model wrote nothing but padding"; absence says "nobody
    measured this". Without the task list the two are indistinguishable, and
    guessing the first one published a measurement nobody took.

    The saturation analysis is the caller that cannot pass tasks -- the note
    text is not in the answer cache -- and it reads completeness only, so
    nothing downstream loses a number it was using.
    """
    scored = tneval.aggregate({"plan.rubric_completeness.plan-homework": "Yes"})

    assert "conciseness" not in scored.by_section.get("plan", {})
    assert "conciseness" in scored.missing
    assert scored.is_complete is False


def test_completeness_divides_by_the_criteria_asked_not_by_the_answers_returned():
    """Two of six answered, both Yes, is not a perfect section.

    Dividing by the answers that came back turns a partly-failed judge run into
    a top score, and judge failures are not random -- they cluster on the notes
    that are hard to read, so the bias runs one way. The section is omitted and
    named instead, the same policy conciseness already had.
    """
    tasks = tneval.build_tasks(NOTE, CONVERSATION)
    keys = list(tneval.criteria_keys("subjective"))
    answers = {f"subjective.rubric_completeness.{key}": "Yes" for key in keys[:2]}

    scored = tneval.aggregate(answers, tasks)

    assert "completeness" not in scored.by_section.get("subjective", {})
    assert scored.incomplete["subjective"] == keys[2:]
    assert scored.is_complete is False


def test_a_fully_answered_section_still_scores_normally():
    """The guard must not cost anything when the judge answered everything."""
    tasks = tneval.build_tasks(NOTE, CONVERSATION)
    keys = list(tneval.criteria_keys("subjective"))
    answers = {f"subjective.rubric_completeness.{key}": "Yes" for key in keys}
    answers[f"subjective.rubric_completeness.{keys[0]}"] = "No"

    scored = tneval.aggregate(answers, tasks)

    assert scored.by_section["subjective"]["completeness"] == pytest.approx(
        (len(keys) - 1) / len(keys)
    )
    assert not scored.incomplete


def test_the_headline_records_how_many_sections_it_averaged():
    """A three-section mean and a four-section mean print the same.

    Without the count there is nothing on the row, in the JSON or on the page
    that distinguishes them, so a model whose judging partly failed is compared
    against one whose did not as though the two figures were alike.
    """
    tasks = tneval.build_tasks(NOTE, CONVERSATION)
    answers = {
        f"{section}.rubric_completeness.{key}": "Yes"
        for section in ("subjective", "objective", "assessment")
        for key in tneval.criteria_keys(section)
    }

    scored = tneval.aggregate(answers, tasks)

    assert scored.sections_used["completeness"] == 3
    assert scored.is_complete is False


def _full() -> tneval.Scores:
    """A note the judge answered completely, so it joins the headline."""
    return tneval.aggregate(
        {
            f"{section}.rubric_completeness.{key}": "Yes"
            for section in tneval.SOAP_SECTIONS
            for key in tneval.criteria_keys(section)
        }
    )


def _candidate(session_id: str, provider: str = "einfra") -> scoring.Candidate:
    return scoring.Candidate(
        provider=provider,
        system_id="a-model",
        system_type="model",
        system_label="a-model",
        session_id=session_id,
        note={},
        conversation="",
    )


def _complete_scores(value: str = "Yes") -> tneval.Scores:
    """A note where every question the protocol asks came back."""
    tasks = tneval.build_tasks(NOTE, CONVERSATION)
    answers = {}
    for task in tasks:
        answers[task.unit] = value if task.kind.startswith("rubric") else "5"
    return tneval.aggregate(answers, tasks)


def test_a_partly_judged_note_is_left_out_of_the_systems_headline():
    """One level up, the same rule: the average is over complete notes only."""
    complete = _complete_scores()
    partial = tneval.aggregate(
        {
            f"{section}.rubric_completeness.{key}": "No"
            for section in ("subjective", "objective")
            for key in tneval.criteria_keys(section)
        }
    )
    aggregate = scoring.SystemAggregate(
        notes=[
            scoring.NoteResult(candidate=_candidate("s1"), scores=complete, cached=1),
            scoring.NoteResult(candidate=_candidate("s2"), scores=partial, cached=1),
        ]
    )

    assert complete.is_complete is True, "the fixture must actually be complete"
    assert aggregate.n_partial == 1
    # 1.0 from the complete note alone; averaging the 0.0 in would read as a
    # model that failed rather than a note the judge did not finish.
    assert aggregate.metrics().headline["completeness"] == pytest.approx(1.0)


def test_a_note_missing_a_whole_measure_is_not_complete():
    """The hole this closes: a note with completeness and nothing else.

    It had no conciseness key at all, so a check that walked only the measures
    present found nothing wrong and called it complete. It then joined its
    system's headline contributing completeness alone -- shrinking the
    denominator for the two measures it did not have, in a way that is not
    random, because judge failures cluster on hard notes.
    """
    tasks = tneval.build_tasks(NOTE, CONVERSATION)
    only_completeness = {task.unit: "Yes" for task in tasks if task.kind == "rubric_completeness"}

    scored = tneval.aggregate(only_completeness, tasks)

    assert scored.missing == ("conciseness", "faithfulness")
    assert scored.is_complete is False


def test_a_reference_model_is_not_charged_for_notes_nobody_asked_it_for():
    """TN-Eval published notes for some sessions, not all.

    Passing one corpus size for every system makes the missing ones read as
    generation failures. A reference model was never asked, so its denominator
    is what it was asked for.
    """
    scored = [
        scoring.NoteResult(candidate=_candidate("s1", provider="tneval"), scores=_full(), cached=1)
    ]
    key = ("tneval", "a-model")

    rows = scoring.to_rows(scored, judge_model="j", n_generated={key: 12}, n_attempted={key: 12})

    assert rows[0].n_sessions_generated == 12
    assert rows[0].n_sessions_attempted == 12
    assert rows[0].n_failed == 0


def test_scoring_a_slice_does_not_report_the_rest_as_unwritten():
    """`--notes 20` over 50 sessions must not publish "20/50 (30 unusable)".

    The counts are taken from the full candidate list before the slice, so a
    flag that limits *this run* cannot become a claim about *the model*. This
    asserts the contract `to_rows` is given, which is where the CLI now takes
    its numbers from.
    """
    key = ("einfra", "a-model")
    # Judged two of fifty so far; wrote all fifty.
    scored = [
        scoring.NoteResult(candidate=_candidate(f"s{i}"), scores=_full(), cached=1)
        for i in range(2)
    ]

    rows = scoring.to_rows(scored, judge_model="j", n_generated={key: 50}, n_attempted={key: 50})

    assert rows[0].n_sessions_generated == 50
    assert rows[0].n_sessions_scored == 2
    assert rows[0].n_failed == 0


def test_a_real_generation_failure_is_still_counted():
    """The guard must not hide the thing it is guarding the shape of."""
    key = ("einfra", "a-model")
    scored = [scoring.NoteResult(candidate=_candidate("s1"), scores=_full(), cached=1)]

    rows = scoring.to_rows(scored, judge_model="j", n_generated={key: 42}, n_attempted={key: 50})

    assert rows[0].n_failed == 8
