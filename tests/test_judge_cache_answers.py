"""A cached reply that is not an answer is asked again, not reused.

Offline. Every record here is written in this file.

The incident: under gemini-3.1-pro-preview, 35 of 39 696 cached rubric answers
were the judge echoing the prompt's own instruction -- `Format Output:** Just
"Yes" or "No".` -- because it had spent its room thinking. The provider set no
`finish_reason`, the harness cached them as `ok`, `is_an_answer` found the word
"yes" in them, and 29 were published as criteria the note met. Re-running
`tnb score` over all 19 systems asked nothing, because the cache decided that a
record was an answer on `ok` alone. Now it asks the question's own test.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tnb import judge
from tnb.config import REPO_ROOT
from tnb.scoring import icare, pdsqi, tneval

FINGERPRINT = {"model": "a-judge", "thinking_budget": 256, "max_output_tokens": 288}
PROMPT = "Does the note record the presenting problem? Just Yes or No."
ECHO = 'Format Output:** Just "Yes" or "No".'


def _cache(tmp_path: Path, answer: str) -> Path:
    path = tmp_path / "answer.json"
    judge.write_cached(
        path,
        {
            "judge_fingerprint": FINGERPRINT,
            "prompt_sha256": judge.prompt_digest(PROMPT),
            "answer": answer,
            "ok": True,
            "finish_reason": None,
        },
    )
    return path


def test_an_echo_of_the_prompt_is_not_served(tmp_path):
    """The exact record from the incident: `ok`, right instrument, right note,
    and a reply the aggregator would throw away."""
    path = _cache(tmp_path, ECHO)
    assert judge.load_cached(path, FINGERPRINT, PROMPT, accepts=tneval.is_an_answer) is None


def test_a_real_answer_is_still_served(tmp_path):
    path = _cache(tmp_path, "Yes")
    found = judge.load_cached(path, FINGERPRINT, PROMPT, accepts=tneval.is_an_answer)
    assert found is not None and found["answer"] == "Yes"


def test_a_caller_that_names_no_test_gets_the_old_behaviour(tmp_path):
    """The cache stays instrument-agnostic: it knows what an answer is only
    when the question tells it. Callers that read records for other reasons --
    the calibration walk, the digest backfill -- are unchanged."""
    path = _cache(tmp_path, ECHO)
    assert judge.load_cached(path, FINGERPRINT, PROMPT) is not None


def test_every_question_knows_what_counts_as_its_answer():
    """Each task type hands the cache the test its own aggregator applies."""
    rubric = tneval.JudgeTask(kind="rubric_completeness", section="subjective", prompt="?")
    likert = tneval.JudgeTask(kind="likert_faithfulness", section="subjective", prompt="?")
    assert rubric.accepts("Yes") and not rubric.accepts("4") and not rubric.accepts(ECHO)
    assert likert.accepts("4") and not likert.accepts("Yes")

    binary = pdsqi.PdsqiTask(attribute="stigmatizing", prompt="?")
    rated = pdsqi.PdsqiTask(attribute="accurate", prompt="?")
    assert binary.accepts("No") and not binary.accepts("4") and not binary.accepts(ECHO)
    assert rated.accepts("4") and not rated.accepts("No")

    trace = icare.TraceTask(dimension="accuracy", prompt="?")
    assert trace.accepts("[3]") and not trace.accepts("and performance anxiety,")


def test_every_runner_hands_the_cache_the_test():
    """Found rather than listed, as `test_judge_cache_guard` does for the write
    side: a scorer added later that reads the cache without naming what an
    answer is would be found by a wrong number rather than by a test."""
    runners = sorted((REPO_ROOT / "src" / "tnb" / "scoring").glob("*run.py"))
    assert len(runners) >= 3, f"only {len(runners)} scorer(s) found -- the glob stopped matching"
    missing = []
    for path in runners:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call) or getattr(node.func, "attr", None) != "load_cached":
                continue
            if not any(word.arg == "accepts" for word in node.keywords):
                missing.append(f"{path.stem}:{node.lineno}")
    assert not missing, f"load_cached called without `accepts=` in: {missing}"


def test_an_echo_scores_as_a_missing_criterion_not_a_met_one():
    """The number this protects, stated once at the aggregator too: the echo
    used to parse as Yes and count in the numerator of completeness."""
    answers = {
        f"{section}.rubric_completeness.{key}": "No"
        for section in tneval.SOAP_SECTIONS
        for key in tneval.criteria_keys(section)
    }
    answers["subjective.rubric_completeness.subjective-symptoms"] = ECHO

    scores = tneval.aggregate(answers)

    assert scores.incomplete["subjective"] == ["subjective-symptoms"]
    assert "subjective-symptoms" not in scores.by_criterion
    assert scores.is_complete is False
