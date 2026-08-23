"""The generation cache: what counts as already done, and what does not.

A full pass is roughly 730 calls per model and several hours, so every question
here is about not repeating work — and, just as important, about not *skipping*
work that was never really done. Nothing here touches the network.
"""

from __future__ import annotations

import json

import pytest

from tnb import generation
from tnb.config import GenerationPolicy, Policy
from tnb.datasets.base import Session, Turn
from tnb.providers import einfra
from tnb.tasks import TASKS

POLICY = Policy(
    base_url="https://example.invalid/v1",
    generation=GenerationPolicy(temperature=0.0, max_tokens=4096, concurrency=2),
)

SESSION = Session(
    id="7",
    source="tneval",
    turns=(Turn("therapist", "How was your week?"), Turn("client", "Rough.")),
)

NOTE = '{"Subjective": "s", "Objective": "o", "Assessment": "a", "Plan": "p"}'


@pytest.fixture(autouse=True)
def cache_dir(tmp_path, monkeypatch):
    """Never write into the real generations/ directory from a test."""
    monkeypatch.setattr(generation, "CACHE_DIR", tmp_path / "generations")
    return tmp_path / "generations"


@pytest.fixture
def answers(monkeypatch):
    """Serve a fixed sequence of completions and count the calls."""
    calls: list[str] = []

    def serve(sequence):
        queue = list(sequence)

        def fake_complete(policy, model_id, prompt):
            calls.append(model_id)
            return queue.pop(0) if queue else sequence[-1]

        monkeypatch.setattr(einfra, "complete", fake_complete)
        return calls

    return serve


def _completion(
    text: str = NOTE, *, ok: bool = True, error: str | None = None, max_tokens: int = 4096
):
    return einfra.Completion(
        model="gemma4",
        text=text,
        ok=ok,
        max_tokens=max_tokens,
        error=error,
        finish_reason="stop",
    )


def _job(model_id: str = "gemma4") -> generation.Job:
    return next(iter(generation.build_jobs([model_id], TASKS["soap"], [SESSION])))


# --- what the cache is keyed on --------------------------------------------


def test_a_second_run_asks_nobody_anything(answers):
    calls = answers([_completion()])
    job = _job()

    assert generation.run_job(job, POLICY).status == "generated"
    assert generation.run_job(job, POLICY).status == "cached"
    assert len(calls) == 1


def test_adding_a_model_regenerates_only_that_model(answers):
    """The property the whole cache exists for: an twelfth model must not cost
    a re-run of the eleven already measured."""
    calls = answers([_completion()])
    generation.run_job(_job("gemma4"), POLICY)
    generation.run_job(_job("glm-5.2"), POLICY)

    assert calls == ["gemma4", "glm-5.2"]
    assert generation.run_job(_job("gemma4"), POLICY).status == "cached"


def test_a_changed_prompt_is_not_the_same_note(answers):
    """Same model, same session, different prompt: a cache that reused this
    would silently report a note that was never written for this prompt."""
    calls = answers([_completion()])
    job = _job()
    generation.run_job(job, POLICY)

    from dataclasses import replace

    reworded = replace(job, prompt=job.prompt + " extra")
    assert generation.run_job(reworded, POLICY).status == "generated"
    assert len(calls) == 2


def test_a_changed_token_budget_invalidates_the_cache(answers):
    """max_tokens decides whether a reasoning model writes anything at all, so
    two budgets are two experiments, not one."""
    calls = answers([_completion()])
    job = _job()
    generation.run_job(job, POLICY)

    bigger = Policy(
        base_url=POLICY.base_url, generation=GenerationPolicy(max_tokens=8192, concurrency=2)
    )
    assert generation.run_job(job, bigger).status == "generated"
    assert len(calls) == 2


def test_each_icare_section_is_cached_on_its_own(answers):
    """A run that died at section 9 must resume at section 9, not at section 1."""
    calls = answers([_completion("Nil")])
    jobs = list(generation.build_jobs(["gemma4"], TASKS["icare"], [SESSION]))
    assert len(jobs) == 17

    for job in jobs[:9]:
        generation.run_job(job, POLICY)
    assert len(calls) == 9

    statuses = [generation.run_job(job, POLICY).status for job in jobs]
    assert statuses[:9] == ["cached"] * 9
    assert statuses[9:] == ["generated"] * 8


# --- what is not a cache hit -----------------------------------------------


def test_a_failed_call_is_retried_next_run(answers):
    """A 429 that exhausted its retries is not a result. Caching it would put a
    hole in the leaderboard that no later run ever fills."""
    calls = answers([_completion("", ok=False, error="HTTP429"), _completion()])
    job = _job()

    assert generation.run_job(job, POLICY).status == "failed"
    assert generation.run_job(job, POLICY).status == "generated"
    assert len(calls) == 2


def test_a_failure_is_still_written_down(answers, cache_dir):
    """An error worth reading beats a missing file: the record says which model,
    which session and what the endpoint said."""
    answers([_completion("", ok=False, error="HTTP429: rate limited")])
    job = _job()
    generation.run_job(job, POLICY)

    record = json.loads(job.path().read_text(encoding="utf-8"))
    assert record["ok"] is False
    assert record["error"] == "HTTP429: rate limited"


def test_an_answer_without_a_soap_dictionary_is_a_failure(answers):
    """A model that refuses, or explains instead of answering, must not enter
    the cache as a note. It would be scored as one."""
    answers([_completion("I am sorry, I cannot help with that.")])
    outcome = generation.run_job(_job(), POLICY)

    assert outcome.status == "failed"
    assert outcome.record["note"] is None
    assert "SOAP dictionary" in outcome.record["error"]


def test_force_regenerates_a_cached_note(answers):
    calls = answers([_completion()])
    job = _job()
    generation.run_job(job, POLICY)
    generation.run_job(job, POLICY, force=True)
    assert len(calls) == 2


def test_a_corrupt_cache_file_is_a_miss_not_a_crash(answers, cache_dir):
    """An interrupted write must cost one call, not the run."""
    calls = answers([_completion()])
    job = _job()
    job.path().parent.mkdir(parents=True, exist_ok=True)
    job.path().write_text("{ truncated", encoding="utf-8")

    assert generation.run_job(job, POLICY).status == "generated"
    assert len(calls) == 1


# --- what the record has to carry ------------------------------------------


def test_the_record_carries_the_versions_the_leaderboard_joins_on(answers):
    """docs/methodology.md: rows are only ever combined when these agree."""
    answers([_completion()])
    record = generation.run_job(_job(), POLICY).record

    for field in ("harness_version", "prompt_version", "model", "task", "session_id"):
        assert record[field], f"{field} missing from the generation record"
    assert record["note"] == {"subjective": "s", "objective": "o", "assessment": "a", "plan": "p"}


def test_the_record_says_which_corpus_bytes_it_was_generated_from(answers, monkeypatch):
    monkeypatch.setattr(generation, "checksums", lambda: {"AnnoMI-full.csv": "abc123"})
    answers([_completion()])
    assert generation.run_job(_job(), POLICY).record["dataset_checksums"]["AnnoMI-full.csv"]


def test_icare_records_keep_the_section_number_and_the_temporal_flag(answers):
    """Sections 5 and 17 get their own leaderboard column, so the flag has to
    survive from prompt building to the stored answer."""
    answers([_completion("Nil")])
    jobs = list(generation.build_jobs(["gemma4"], TASKS["icare"], [SESSION]))
    record = generation.run_job(jobs[4], POLICY).record

    assert record["unit"] == "section-05"
    assert record["unit_meta"] == {"section": 5, "temporal": True}


def test_paths_survive_a_model_id_with_a_slash_in_it(answers):
    """Nothing on e-INFRA is namespaced today, but 'meta-llama/Llama-4' would
    otherwise write outside the cache directory."""
    answers([_completion()])
    job = _job("vendor/model:v1")
    generation.run_job(job, POLICY)
    assert job.path().exists()
    assert job.path().parent.name == "7"


# --- running many ----------------------------------------------------------


def test_the_pool_never_exceeds_the_configured_concurrency(monkeypatch):
    """e-INFRA rate-limits per API key: six concurrent requests drew 429 on a
    third of calls, so the limit is over all models at once, not per model."""
    import threading

    live = 0
    peak = 0
    lock = threading.Lock()

    def fake_complete(policy, model_id, prompt):
        nonlocal live, peak
        with lock:
            live += 1
            peak = max(peak, live)
        try:
            return _completion()
        finally:
            with lock:
                live -= 1

    monkeypatch.setattr(einfra, "complete", fake_complete)
    jobs = list(generation.build_jobs([f"m{i}" for i in range(8)], TASKS["soap"], [SESSION]))
    outcomes = generation.run_jobs(jobs, POLICY)

    assert len(outcomes) == 8
    assert peak <= POLICY.generation.concurrency


# --- running out of budget while thinking ----------------------------------

ESCALATING = Policy(
    base_url="https://example.invalid/v1",
    generation=GenerationPolicy(max_tokens=4096, escalate_max_tokens=16384, concurrency=2),
)


def _truncated(reasoning_chars: int = 20820, max_tokens: int = 4096):
    return einfra.Completion(
        model="deepseek-v4-flash-thinking",
        text="",
        ok=False,
        max_tokens=max_tokens,
        finish_reason="length",
        reasoning_chars=reasoning_chars,
        error="empty content",
    )


@pytest.fixture
def budgets(monkeypatch):
    """Record the token budget each call was given."""
    seen: list[int] = []

    def serve(sequence):
        queue = list(sequence)

        def fake_complete(policy, model_id, prompt, *, max_tokens=None):
            seen.append(max_tokens or policy.generation.max_tokens)
            return queue.pop(0) if queue else sequence[-1]

        monkeypatch.setattr(einfra, "complete", fake_complete)
        return seen

    return serve


def test_a_model_that_thought_until_it_ran_out_gets_one_bigger_try(budgets):
    """Observed on the live endpoint: 4096 tokens spent entirely on reasoning,
    no content. Scoring that as a zero would measure our budget, not the model."""
    seen = budgets([_truncated(), _completion(max_tokens=16384)])
    outcome = generation.run_job(_job("deepseek-v4-flash-thinking"), ESCALATING)

    assert seen == [4096, 16384]
    assert outcome.status == "generated"
    assert outcome.record["escalated"] is True
    assert outcome.record["max_tokens"] == 16384


def test_the_bigger_try_happens_once_and_then_stops(budgets):
    seen = budgets([_truncated(), _truncated(max_tokens=16384)])
    outcome = generation.run_job(_job("deepseek-v4-flash-thinking"), ESCALATING)

    assert seen == [4096, 16384]
    assert outcome.status == "failed"


def test_a_refusal_is_not_retried_with_a_bigger_budget(budgets):
    """Only `length` means the budget was the problem. A model that answered
    something unusable would just answer it again, more expensively."""
    seen = budgets([_completion("I cannot help with that.")])
    assert generation.run_job(_job(), ESCALATING).status == "failed"
    assert seen == [4096]


def test_the_escalation_budget_is_part_of_the_cache_key(budgets):
    """A note written on the second attempt must still be a hit next run, and
    changing the escalation budget must not be silently mixed in."""
    budgets([_completion()])
    job = _job()
    generation.run_job(job, ESCALATING)

    assert generation.run_job(job, ESCALATING).status == "cached"
    assert generation.run_job(job, POLICY).status == "generated"
