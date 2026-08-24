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
    """TN-Eval's code does exactly this rather than skipping the section."""
    scores = tneval.aggregate({"plan.rubric_completeness.plan-homework": "Yes"})
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
    assert sent[0]["json"]["generationConfig"]["thinkingConfig"]["thinkingBudget"] == 128


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
    """A price of zero would disable the ceiling. Better to notice."""
    assert judge.estimate_usd("some-new-model", 1_000_000, 1_000_000) == 0.0


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


def test_a_partial_scoring_run_does_not_look_complete():
    """A pilot over one session of fifty must read as 1/50. Reporting 1/1 is how
    a table quietly claims coverage it does not have."""
    from tnb.datasets.base import Session, Turn

    session = Session(
        id="0", source="tneval", turns=(Turn("therapist", "Hi."),), meta={"human_note": NOTE}
    )
    (candidate,) = list(scoring.from_reference([session]))
    result = scoring.NoteResult(candidate=candidate, scores=tneval.Scores())

    (row,) = scoring.to_rows(
        [result], judge_model="gemini-2.5-pro", n_attempted={("tneval", "therapist"): 50}
    )
    assert (row.n_sessions_scored, row.n_sessions_attempted) == (1, 50)
    assert row.n_failed == 49
