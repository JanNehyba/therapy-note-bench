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
from tnb.tasks import Task
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


def _record(job: Job, policy: Policy, completion: einfra.Completion, when: str) -> dict:
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
        "prompt_sha256": hashlib.sha256(job.prompt.encode()).hexdigest(),
        "prompt_chars": len(job.prompt),
        "temperature": policy.generation.temperature,
        "max_tokens": policy.generation.max_tokens,
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


def run_job(job: Job, policy: Policy, *, force: bool = False) -> Outcome:
    """Answer one job from cache, or ask the model and file the answer away."""
    if not force:
        cached = load_cached(job, policy)
        if cached is not None:
            return Outcome(job, "cached", cached)

    completion = einfra.complete(policy, job.model_id, job.prompt)
    when = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    record = _record(job, policy, completion, when)
    _write(job.path(), record)
    return Outcome(job, "generated" if record["ok"] else "failed", record)


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
