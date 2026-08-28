"""The generation cache: what counts as already done, and what does not.

A full pass is roughly 730 calls per model and several hours, so every question
here is about not repeating work — and, just as important, about not *skipping*
work that was never really done. Nothing here touches the network.
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from tnb import generation
from tnb.config import GenerationPolicy, Provider
from tnb.datasets.base import Session, Turn
from tnb.providers import openai_compatible as einfra
from tnb.tasks import TASKS, soap

PROVIDER = Provider(
    name="einfra",
    base_url="https://example.invalid/v1",
    token_env="EINFRA_API_TOKEN",
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

        def fake_complete(provider, model_id, prompt):
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


def _job(model_id: str = "gemma4", provider: str = "einfra") -> generation.Job:
    return next(iter(generation.build_jobs(provider, [model_id], TASKS["soap"], [SESSION])))


# --- what the cache is keyed on --------------------------------------------


def test_a_second_run_asks_nobody_anything(answers):
    calls = answers([_completion()])
    job = _job()

    assert generation.run_job(job, PROVIDER).status == "generated"
    assert generation.run_job(job, PROVIDER).status == "cached"
    assert len(calls) == 1


def test_adding_a_model_regenerates_only_that_model(answers):
    """The property the whole cache exists for: an twelfth model must not cost
    a re-run of the eleven already measured."""
    calls = answers([_completion()])
    generation.run_job(_job("gemma4"), PROVIDER)
    generation.run_job(_job("glm-5.2"), PROVIDER)

    assert calls == ["gemma4", "glm-5.2"]
    assert generation.run_job(_job("gemma4"), PROVIDER).status == "cached"


def test_a_changed_prompt_is_not_the_same_note(answers):
    """Same model, same session, different prompt: a cache that reused this
    would silently report a note that was never written for this prompt."""
    calls = answers([_completion()])
    job = _job()
    generation.run_job(job, PROVIDER)

    from dataclasses import replace

    reworded = replace(job, prompt=job.prompt + " extra")
    assert generation.run_job(reworded, PROVIDER).status == "generated"
    assert len(calls) == 2


def test_a_changed_token_budget_invalidates_the_cache(answers):
    """max_tokens decides whether a reasoning model writes anything at all, so
    two budgets are two experiments, not one."""
    calls = answers([_completion()])
    job = _job()
    generation.run_job(job, PROVIDER)

    bigger = replace(PROVIDER, generation=GenerationPolicy(max_tokens=8192, concurrency=2))
    assert generation.run_job(job, bigger).status == "generated"
    assert len(calls) == 2


def test_each_icare_section_is_cached_on_its_own(answers):
    """A run that died at section 9 must resume at section 9, not at section 1."""
    calls = answers([_completion("Nil")])
    jobs = list(generation.build_jobs("einfra", ["gemma4"], TASKS["icare"], [SESSION]))
    assert len(jobs) == 17

    for job in jobs[:9]:
        generation.run_job(job, PROVIDER)
    assert len(calls) == 9

    statuses = [generation.run_job(job, PROVIDER).status for job in jobs]
    assert statuses[:9] == ["cached"] * 9
    assert statuses[9:] == ["generated"] * 8


# --- what is not a cache hit -----------------------------------------------


def test_a_failed_call_is_retried_next_run(answers):
    """A 429 that exhausted its retries is not a result. Caching it would put a
    hole in the leaderboard that no later run ever fills."""
    calls = answers([_completion("", ok=False, error="HTTP429"), _completion()])
    job = _job()

    assert generation.run_job(job, PROVIDER).status == "failed"
    assert generation.run_job(job, PROVIDER).status == "generated"
    assert len(calls) == 2


def test_a_failure_is_still_written_down(answers, cache_dir):
    """An error worth reading beats a missing file: the record says which model,
    which session and what the endpoint said."""
    answers([_completion("", ok=False, error="HTTP429: rate limited")])
    job = _job()
    generation.run_job(job, PROVIDER)

    record = json.loads(job.path().read_text(encoding="utf-8"))
    assert record["ok"] is False
    assert record["error"] == "HTTP429: rate limited"


def test_an_answer_without_a_soap_dictionary_is_a_failure(answers):
    """A model that refuses, or explains instead of answering, must not enter
    the cache as a note. It would be scored as one."""
    answers([_completion("I am sorry, I cannot help with that.")])
    outcome = generation.run_job(_job(), PROVIDER)

    assert outcome.status == "failed"
    assert outcome.record["note"] is None
    assert "SOAP dictionary" in outcome.record["error"]


def test_force_regenerates_a_cached_note(answers):
    calls = answers([_completion()])
    job = _job()
    generation.run_job(job, PROVIDER)
    generation.run_job(job, PROVIDER, force=True)
    assert len(calls) == 2


def test_a_corrupt_cache_file_is_a_miss_not_a_crash(answers, cache_dir):
    """An interrupted write must cost one call, not the run."""
    calls = answers([_completion()])
    job = _job()
    job.path().parent.mkdir(parents=True, exist_ok=True)
    job.path().write_text("{ truncated", encoding="utf-8")

    assert generation.run_job(job, PROVIDER).status == "generated"
    assert len(calls) == 1


# --- what the record has to carry ------------------------------------------


def test_the_record_carries_the_versions_the_leaderboard_joins_on(answers):
    """docs/methodology.md: rows are only ever combined when these agree."""
    answers([_completion()])
    record = generation.run_job(_job(), PROVIDER).record

    for field in ("harness_version", "prompt_version", "model", "task", "session_id"):
        assert record[field], f"{field} missing from the generation record"
    assert record["note"] == {"subjective": "s", "objective": "o", "assessment": "a", "plan": "p"}


def test_the_record_says_which_corpus_bytes_it_was_generated_from(answers, monkeypatch):
    monkeypatch.setattr(generation, "checksums", lambda: {"AnnoMI-full.csv": "abc123"})
    answers([_completion()])
    assert generation.run_job(_job(), PROVIDER).record["dataset_checksums"]["AnnoMI-full.csv"]


def test_icare_records_keep_the_section_number_and_the_temporal_flag(answers):
    """Sections 5 and 17 get their own leaderboard column, so the flag has to
    survive from prompt building to the stored answer."""
    answers([_completion("Nil")])
    jobs = list(generation.build_jobs("einfra", ["gemma4"], TASKS["icare"], [SESSION]))
    record = generation.run_job(jobs[4], PROVIDER).record

    assert record["unit"] == "section-05"
    assert record["unit_meta"] == {"section": 5, "temporal": True}


def test_paths_survive_a_model_id_with_a_slash_in_it(answers):
    """Nothing on e-INFRA is namespaced today, but 'meta-llama/Llama-4' would
    otherwise write outside the cache directory."""
    answers([_completion()])
    job = _job("vendor/model:v1")
    generation.run_job(job, PROVIDER)
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

    def fake_complete(provider, model_id, prompt):
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
    jobs = list(
        generation.build_jobs("einfra", [f"m{i}" for i in range(8)], TASKS["soap"], [SESSION])
    )
    outcomes = generation.run_jobs(jobs, PROVIDER)

    assert len(outcomes) == 8
    assert peak <= PROVIDER.generation.concurrency


# --- running out of budget while thinking ----------------------------------

ESCALATING = replace(
    PROVIDER,
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

        def fake_complete(provider, model_id, prompt, *, max_tokens=None):
            seen.append(max_tokens or provider.generation.max_tokens)
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
    something unusable is re-asked TN-Eval's five times, but never at a bigger
    budget: it had plenty and used it to say no."""
    seen = budgets([_completion("I cannot help with that.")])
    assert generation.run_job(_job(), ESCALATING).status == "failed"
    assert seen == [4096] * 5


def test_the_escalation_budget_is_part_of_the_cache_key(budgets):
    """A note written on the second attempt must still be a hit next run, and
    changing the escalation budget must not be silently mixed in."""
    budgets([_completion()])
    job = _job()
    generation.run_job(job, ESCALATING)

    assert generation.run_job(job, ESCALATING).status == "cached"
    assert generation.run_job(job, PROVIDER).status == "generated"


# --- TN-Eval's repair loop -------------------------------------------------


@pytest.fixture
def prompts(monkeypatch):
    """Record the exact prompt each call was given."""
    sent: list[str] = []

    def serve(sequence):
        queue = list(sequence)

        def fake_complete(provider, model_id, prompt, *, max_tokens=None):
            sent.append(prompt)
            return queue.pop(0) if queue else sequence[-1]

        monkeypatch.setattr(einfra, "complete", fake_complete)
        return sent

    return serve


NESTED = '{"Subjective": "s", "Objective": "o", "Assessment": "a", "Plan": {"Goals": ["x"]}}'


def test_a_nested_plan_is_re_asked_with_tn_evals_repair_sentence(prompts):
    """gpt-oss-120b writes a good note with Plan as a sub-dictionary. TN-Eval's
    parser slices to the first closing brace, so it truncates -- and their
    protocol is to append the repair sentence and ask again, which is what a
    model needs here. A cleverer parser would measure a different extraction
    than their published numbers did."""
    sent = prompts([_completion(NESTED), _completion()])
    outcome = generation.run_job(_job("gpt-oss-120b"), PROVIDER)

    assert outcome.status == "generated"
    assert len(sent) == 2
    assert sent[1] == sent[0] + soap.REPAIR_SENTENCE
    assert outcome.record["parse_attempt"] == 2


def test_the_repair_loop_stops_where_tn_eval_stops(prompts):
    sent = prompts([_completion(NESTED)])
    assert generation.run_job(_job(), PROVIDER).status == "failed"
    assert len(sent) == soap.PARSE_ATTEMPTS


def test_a_note_that_parses_first_time_is_asked_once(prompts):
    sent = prompts([_completion()])
    assert generation.run_job(_job(), PROVIDER).record["parse_attempt"] == 1
    assert len(sent) == 1


def test_an_endpoint_failure_is_not_re_asked_with_a_repair_sentence(prompts):
    """A 429 that exhausted its retries did not misunderstand the format."""
    sent = prompts([_completion("", ok=False, error="HTTP429")])
    assert generation.run_job(_job(), PROVIDER).status == "failed"
    assert len(sent) == 1


def test_icare_sections_are_never_re_asked(prompts):
    """iCARE has no repair loop; inventing one would be our protocol, not theirs."""
    sent = prompts([_completion("Nil")])
    jobs = list(generation.build_jobs("einfra", ["gemma4"], TASKS["icare"], [SESSION]))
    generation.run_job(jobs[0], PROVIDER)
    assert len(sent) == 1


def test_a_truncated_answer_gets_the_bigger_budget_too(budgets):
    """Escalation used to require an *empty* answer.

    A model that produced half a sentence and stopped at `length` looked
    successful, so `_needs_a_bigger_budget` returned early on `record["ok"]`
    and the second chance never happened. Half an answer and no answer are the
    same event -- the budget ran out -- and both deserve it.
    """
    half = einfra.Completion(
        model="glm-5",
        text="The client reported feeling anxious about",
        ok=False,
        max_tokens=4096,
        finish_reason="length",
        error="truncated at max_tokens=4096",
    )
    finished = einfra.Completion(
        model="glm-5", text="a whole section", ok=True, max_tokens=16384, finish_reason="stop"
    )
    seen = budgets([half, finished])

    completion, record = generation._ask(_job(), ESCALATING, "write section 6")

    assert seen == [4096, 16384], "asked again at the bigger budget"
    assert completion.ok
    # `record["ok"]` is about whether the *task's* parser could read the answer,
    # which is a separate question from whether the call finished. This test is
    # about the second one.
    assert record["finish_reason"] == "stop"


def test_a_record_stored_before_the_truncation_rule_is_not_a_cache_hit(tmp_path, monkeypatch):
    """The cache holds what the endpoint said; today's rules decide if it counts.

    16 sections were written as `ok: true` while stopping mid-sentence at the
    budget, because nothing read `finish_reason` at the time. Deleting them
    would lose the evidence of what happened; rejecting them at the read
    boundary re-asks each one, and this time the escalation fires.
    """
    monkeypatch.setattr(generation, "CACHE_DIR", tmp_path)
    job = _job()
    path = job.path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "ok": True,
                "text": "The client reported feeling anxious about",
                "finish_reason": "length",
                "request_sha256": generation.request_digest(job.model_id, job.prompt, PROVIDER),
            }
        ),
        encoding="utf-8",
    )

    assert generation.load_cached(job, PROVIDER) is None
    assert path.exists(), "kept, so the failure can still be explained"


# --- the registry that lets a task fall through -----------------------------


def test_every_task_whose_output_is_structured_is_parsed_at_generation():
    """The parser table is a dict, and a task that is not in it is not an
    error -- it is a task whose replies are never checked.

    That is how the Deepsy sections shipped: they asked for JSON, matched
    nothing, and were stored `ok: true` with no note, so the repair suffix
    never fired and `PARSE_ATTEMPTS` was dead. The missing line was the
    symptom; the absence of this check was the defect.

    `icare` is deliberately absent and stays absent: its sections are prose,
    there is no structure to fail to parse, and it has its own careful
    handling in `icare_run` for a section the infrastructure lost. So the test
    asks the question that actually matters -- does the task's own module
    define a parser? -- rather than counting entries.
    """
    import importlib

    from tnb import generation
    from tnb.config import GenerationPolicy, Provider
    from tnb.providers.openai_compatible import Completion
    from tnb.tasks import TASKS

    provider = Provider(
        name="einfra",
        base_url="https://example.invalid/v1",
        token_env="EINFRA_API_TOKEN",
        generation=GenerationPolicy(temperature=0.0, max_tokens=4096, concurrency=2),
    )

    for name, task in sorted(TASKS.items()):
        module = importlib.import_module(f"tnb.tasks.{name.split('-')[0]}")
        if not hasattr(module, "parse_note"):
            continue

        unit = task.build_units.__name__  # only to make a failure readable
        job = generation.Job(
            provider="einfra",
            model_id="m",
            task=name,
            prompt_version=task.prompt_version,
            session_id="s",
            # A unit name the Deepsy parser will recognise; ignored by the rest.
            unit="data" if name.startswith("deepsy") else "note",
            prompt="...",
        )
        record = generation._record(
            job, provider, Completion(model="m", text="I cannot do that.", ok=True), "now", "..."
        )
        assert record["ok"] is False, (
            f"{name} defines parse_note ({unit}) and generation accepted a reply that "
            "is not a note. Add it to the parser table, or its replies are never checked."
        )
        assert record["note"] is None, name
