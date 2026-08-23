"""Generating notes, and never generating the same note twice.

One *unit* is one call: a whole SOAP note, or one of iCARE's 17 sections. Each
unit's answer is written to its own file under::

    generations/<task>/<prompt_version>/<model>/<session>/<unit>.json

so adding a twelfth model to the benchmark re-generates that model and nothing
else, and a run interrupted at section 9 of session 30 resumes there. That is
the whole reason this exists: a full pass is roughly 730 calls per model and
several hours at the concurrency a shared academic endpoint tolerates.

A cached answer is reused only if the request that produced it is *identical*
-- same prompt, same model, same temperature and token budget. The hash of the
request is stored with the answer and checked on the way back in, because
"content-addressed" is only true if something actually compares the content.
Changing ``max_tokens`` in models.yaml therefore invalidates the cache, which is
correct: it changes what the models produce.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from collections.abc import Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from tnb import __version__
from tnb.config import REPO_ROOT, Policy
from tnb.datasets.base import Session, checksums
from tnb.providers import einfra
from tnb.tasks import TASKS, Task
from tnb.tasks import soap as soap_task

CACHE_DIR = REPO_ROOT / "generations"

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def _slug(value: str) -> str:
    """Make a model id or session id safe as a directory name on any platform."""
    return _UNSAFE.sub("_", value)


def request_digest(model_id: str, prompt: str, policy: Policy) -> str:
    """Hash everything that decides what comes back.

    Not just the prompt: two runs with different token budgets are not the same
    experiment, and a cache that ignored that would quietly mix them.
    """
    payload = json.dumps(
        {
            "model": model_id,
            "prompt": prompt,
            "temperature": policy.generation.temperature,
            "max_tokens": policy.generation.max_tokens,
            # The escalation budget belongs to the key even for the many calls
            # that never use it: it describes the procedure, so a note written
            # on the second attempt is still a hit on the next run.
            "escalate_max_tokens": policy.generation.escalate_max_tokens,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class Job:
    """One unit for one model: the smallest thing that can be cached or retried."""

    model_id: str
    task: str
    prompt_version: str
    session_id: str
    unit: str
    prompt: str
    unit_meta: dict = field(default_factory=dict)

    def path(self) -> Path:
        return (
            CACHE_DIR
            / _slug(self.task)
            / _slug(self.prompt_version)
            / _slug(self.model_id)
            / _slug(self.session_id)
            / f"{_slug(self.unit)}.json"
        )


@dataclass
class Outcome:
    """What happened to one job in one run."""

    job: Job
    status: str  # 'cached' | 'generated' | 'failed'
    record: dict


def build_jobs(model_ids: Iterable[str], task: Task, sessions: list[Session]) -> Iterator[Job]:
    """Every call the given models owe for the given sessions, in a stable order."""
    units_by_session = [(session, task.build_units(session)) for session in sessions]
    for model_id in model_ids:
        for _session, units in units_by_session:
            for unit in units:
                yield Job(
                    model_id=model_id,
                    task=unit.task,
                    prompt_version=unit.prompt_version,
                    session_id=unit.session_id,
                    unit=unit.unit,
                    prompt=unit.prompt,
                    unit_meta=unit.meta,
                )


def load_cached(job: Job, policy: Policy) -> dict | None:
    """Return a previous answer, or None if there is nothing usable.

    A failed generation is stored -- an error worth reading is better than a
    silent gap -- but it is never a cache hit, so the next run retries it.
    """
    path = job.path()
    if not path.exists():
        return None

    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    if not record.get("ok"):
        return None
    if record.get("request_sha256") != request_digest(job.model_id, job.prompt, policy):
        return None
    return record


def _record(
    job: Job, policy: Policy, completion: einfra.Completion, when: str, prompt: str
) -> dict:
    record = {
        "harness_version": __version__,
        "provider": policy.provider,
        "base_url": policy.base_url,
        "model": job.model_id,
        "task": job.task,
        "prompt_version": job.prompt_version,
        "session_id": job.session_id,
        "unit": job.unit,
        "unit_meta": job.unit_meta,
        "generated_at": when,
        "request_sha256": request_digest(job.model_id, job.prompt, policy),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "prompt_chars": len(prompt),
        "temperature": policy.generation.temperature,
        "max_tokens": completion.max_tokens or policy.generation.max_tokens,
        "escalated": completion.max_tokens > policy.generation.max_tokens,
        "ok": completion.ok,
        "error": completion.error,
        "finish_reason": completion.finish_reason,
        "usage": completion.usage,
        "reasoning_chars": completion.reasoning_chars,
        "latency_s": round(completion.latency_s, 3),
        "text": completion.text,
        "dataset_checksums": checksums(),
    }

    if job.task == soap_task.NAME:
        # Parsed here rather than at scoring time so that a note which never
        # parsed is visible in the cache instead of surfacing as a zero later.
        record["note"] = soap_task.parse_note(completion.text) if completion.text else None
        if record["note"] is None:
            record["ok"] = False
            record["error"] = record["error"] or "answer did not contain a SOAP dictionary"
    return record


def _write(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def _now() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _needs_a_bigger_budget(record: dict, completion: einfra.Completion, policy: Policy) -> bool:
    """Was this a model thinking until it ran out, rather than a model failing?

    Observed on 2026-08-23: deepseek-v4-flash-thinking spent all 4096 tokens on
    20k characters of reasoning for one iCARE section and returned no content.
    Scoring that as a zero would measure our token budget, not the model. A call
    that stopped on `length` without a usable answer gets exactly one more try
    at ``escalate_max_tokens``; anything else -- a refusal, a 429, a note that
    parsed -- is left alone.
    """
    if record["ok"] or completion.finish_reason != "length":
        return False
    return policy.generation.escalate_max_tokens > completion.max_tokens


def _ask(job: Job, policy: Policy, prompt: str) -> tuple[einfra.Completion, dict]:
    """One question, plus the second chance for a model that thought too long."""
    completion = einfra.complete(policy, job.model_id, prompt)
    record = _record(job, policy, completion, _now(), prompt)

    if _needs_a_bigger_budget(record, completion, policy):
        completion = einfra.complete(
            policy,
            job.model_id,
            prompt,
            max_tokens=policy.generation.escalate_max_tokens,
        )
        record = _record(job, policy, completion, _now(), prompt)
    return completion, record


def run_job(job: Job, policy: Policy, *, force: bool = False) -> Outcome:
    """Answer one job from cache, or ask the model and file the answer away.

    A SOAP answer that arrives but cannot be parsed is re-asked with TN-Eval's
    repair sentence appended, up to their five attempts. This is their protocol,
    not our idea, and it is what a model needs when it writes a perfectly good
    note with a nested Plan: their parser slices from the first brace to the
    first closing brace, so nesting truncates the JSON. Fixing that by writing a
    cleverer parser would measure a different extraction than their numbers did.

    Only a parse failure is re-asked -- an answer arrived and was not a note,
    a refusal included, which is what TN-Eval's loop retries. A 429, a dropped
    connection or an empty answer is a different problem, and a repair sentence
    would not help it.
    """
    if not force:
        cached = load_cached(job, policy)
        if cached is not None:
            return Outcome(job, "cached", cached)

    task = TASKS.get(job.task)
    suffix = task.repair_suffix if task else ""
    attempts = task.parse_attempts if task and suffix else 1

    for attempt in range(attempts):
        completion, record = _ask(job, policy, job.prompt + suffix * attempt)
        record["parse_attempt"] = attempt + 1
        if record["ok"] or not _is_a_parse_failure(completion, record):
            break

    _write(job.path(), record)
    return Outcome(job, "generated" if record["ok"] else "failed", record)


def _is_a_parse_failure(completion: einfra.Completion, record: dict) -> bool:
    """Did an answer arrive that simply was not shaped like a note?

    True only when the model said something usable-looking and the parser could
    not find a note in it. An empty answer, a 429 or a dropped connection is a
    different problem and re-asking with a repair sentence would not help.
    """
    return completion.ok and not record["ok"]


def run_jobs(
    jobs: list[Job],
    policy: Policy,
    *,
    force: bool = False,
    on_done=None,
) -> list[Outcome]:
    """Run every job at the endpoint's tolerated concurrency.

    The limit is per API key, not per model, so this is one pool over all jobs
    rather than one pool per model. Results come back in submission order, which
    keeps a run's summary readable.
    """
    outcomes: list[Outcome] = []
    with ThreadPoolExecutor(max_workers=max(1, policy.generation.concurrency)) as pool:
        for outcome in pool.map(lambda job: run_job(job, policy, force=force), jobs):
            outcomes.append(outcome)
            if on_done is not None:
                on_done(outcome)
    return outcomes
