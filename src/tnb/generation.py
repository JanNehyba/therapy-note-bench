"""Generating notes, and never generating the same note twice.

One *unit* is one call: a whole SOAP note, or one of iCARE's 17 sections. Each
unit's answer is written to its own file under::

    generations/<provider>/<task>/<prompt_version>/<model>/<session>/<unit>.json

The provider comes first because a model id is only unique within one endpoint.
Two providers serving `qwen3.5-122b` may be serving two different builds -- a
different quantisation, different weights -- and letting them share a path would
silently overwrite one benchmark with another.

Every unit is its own file and every file is written once, so adding a twelfth
model to the benchmark re-generates that model and nothing else, and a run
interrupted at section 9 of session 30 resumes there. That is
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
from tnb.config import REPO_ROOT, Provider
from tnb.datasets.base import Session, checksums
from tnb.providers import openai_compatible as client
from tnb.tasks import TASKS, Task

CACHE_DIR = REPO_ROOT / "generations"

#: What a reply that is not a note is recorded as. One fixed phrase rather than
#: one naming the unit: `results.HARNESS_REASONS` is a closed set, written that
#: way after a provider's error body reached the published page, and a phrase
#: with a value interpolated into it can never be in a closed set. The unit is
#: already a field on the record, so naming it here would add nothing.
NOT_A_NOTE = "answer was not a note"

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def check_cache_layout(cache_dir: Path | None = None) -> None:
    """Refuse to run against a cache written before providers had their own level.

    Without this the harness would find nothing at the new paths, decide that
    8000 notes are missing, and cheerfully re-generate all of them. The fix is a
    move, not a re-run, so it says so.
    """
    cache_dir = cache_dir or CACHE_DIR
    if not cache_dir.exists():
        return

    stray = sorted(
        path.name for path in cache_dir.iterdir() if path.is_dir() and path.name in TASKS
    )
    if stray:
        moves = " ".join(f"{cache_dir.name}/{name}" for name in stray)
        raise RuntimeError(
            f"{cache_dir.name}/ still has the pre-provider layout ({', '.join(stray)}). "
            f"Notes are now filed under {cache_dir.name}/<provider>/. Move them rather "
            f"than re-generating: mkdir -p {cache_dir.name}/einfra && mv {moves} "
            f"{cache_dir.name}/einfra/"
        )


def _slug(value: str) -> str:
    """Make a model id or session id safe as a directory name on any platform."""
    return _UNSAFE.sub("_", value)


def request_digest(model_id: str, prompt: str, provider: Provider) -> str:
    """Hash everything that decides what comes back.

    Not just the prompt: two runs with different token budgets are not the same
    experiment, and the same model id on two providers is not the same model.
    A cache that ignored either would quietly mix them.

    Two things here are deliberately shaped so that adding them changed no
    existing key, and 8 030 already-generated notes stayed valid:

    - ``temperature`` is the one that will actually be **sent**, not the one
      configured. For every provider that accepts our value the two are equal,
      so nothing moved; for OpenAI, which refuses anything but 1, the key now
      records the 1 that happens instead of the 0 that does not.
    - ``effort`` is present **only when the provider has one**. A provider with
      no such control contributes no key, which is both truthful -- there is
      nothing to record -- and what keeps every existing digest identical.
      Where an effort does exist it is part of the key, so the same model at
      two efforts is two caches and can never be served one from the other.
    """
    payload: dict[str, object] = {
        "provider": provider.name,
        "model": model_id,
        "prompt": prompt,
        "temperature": provider.generation.effective_temperature,
        "max_tokens": provider.generation.max_tokens,
        # The escalation budget belongs to the key even for the many calls
        # that never use it: it describes the procedure, so a note written
        # on the second attempt is still a hit on the next run.
        "escalate_max_tokens": provider.generation.escalate_max_tokens,
    }
    if provider.generation.effort:
        payload["effort"] = provider.generation.effort

    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


@dataclass(frozen=True)
class Job:
    """One unit for one model on one provider: the smallest cacheable thing."""

    provider: str
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
            / _slug(self.provider)
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


def build_jobs(
    provider: str, model_ids: Iterable[str], task: Task, sessions: list[Session]
) -> Iterator[Job]:
    """Every call the given models owe for the given sessions, in a stable order."""
    units_by_session = [(session, task.build_units(session)) for session in sessions]
    for model_id in model_ids:
        for _session, units in units_by_session:
            for unit in units:
                yield Job(
                    provider=provider,
                    model_id=model_id,
                    task=unit.task,
                    prompt_version=unit.prompt_version,
                    session_id=unit.session_id,
                    unit=unit.unit,
                    prompt=unit.prompt,
                    unit_meta=unit.meta,
                )


def load_cached(job: Job, provider: Provider) -> dict | None:
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
    # Judged by today's rules, not by the ones in force when it was written.
    # 16 sections stopped mid-sentence at the token budget and were stored as
    # `ok: true` because nothing read `finish_reason` yet. Deleting them would
    # lose the evidence; rejecting them here re-asks each one on the next run,
    # and this time the escalation fires.
    if record.get("finish_reason") == "length":
        return None
    if record.get("request_sha256") != request_digest(job.model_id, job.prompt, provider):
        return None
    return record


def _record(
    job: Job, provider: Provider, completion: client.Completion, when: str, prompt: str
) -> dict:
    record = {
        "harness_version": __version__,
        "provider": job.provider,
        "base_url": provider.base_url,
        "model": job.model_id,
        "task": job.task,
        "prompt_version": job.prompt_version,
        "session_id": job.session_id,
        "unit": job.unit,
        "unit_meta": job.unit_meta,
        "generated_at": when,
        "request_sha256": request_digest(job.model_id, job.prompt, provider),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "prompt_chars": len(prompt),
        # What was used, not what was asked for -- see `effective_temperature`.
        "temperature": provider.generation.effective_temperature,
        "temperature_forced": not provider.generation.dialect.send_temperature,
        "effort": provider.generation.effort,
        "max_tokens": completion.max_tokens or provider.generation.max_tokens,
        "escalated": completion.max_tokens > provider.generation.max_tokens,
        "ok": completion.ok,
        "error": completion.error,
        # What the provider actually said. `generations/` is gitignored, and
        # this is the only place it is kept: `error` above carries a phrase this
        # repository chose, so nothing a provider wrote can reach a committed
        # file. Debugging loses nothing; it just has to look here.
        "error_body": completion.error_body,
        "finish_reason": completion.finish_reason,
        "usage": completion.usage,
        "reasoning_chars": completion.reasoning_chars,
        "latency_s": round(completion.latency_s, 3),
        "text": completion.text,
        "dataset_checksums": checksums(),
    }

    # Parsed here rather than at scoring time so that a note which never parsed
    # is visible in the cache instead of surfacing as a zero later. A task that
    # asks for the same sections in another language brings its own reader and
    # fails the same way.
    # Asked of the task rather than looked up here. A table in this module was
    # a table a task could be missing from, and a task missing from it was one
    # whose replies were never checked -- stored as a success, never repaired.
    # `Task.parse` is required, so a task that has no structure to check says
    # so out loud.
    task = TASKS.get(job.task)
    if task is not None and task.parse is not None:
        record["note"] = task.parse(completion.text, job.unit) if completion.text else None
        if record["note"] is None:
            record["ok"] = False
            record["error"] = record["error"] or NOT_A_NOTE
    return record


def _write(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def _now() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _needs_a_bigger_budget(record: dict, completion: client.Completion, provider: Provider) -> bool:
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
    return provider.generation.escalate_max_tokens > completion.max_tokens


def _ask(job: Job, provider: Provider, prompt: str) -> tuple[client.Completion, dict]:
    """One question, plus the second chance for a model that thought too long."""
    completion = client.complete(provider, job.model_id, prompt)
    record = _record(job, provider, completion, _now(), prompt)

    if _needs_a_bigger_budget(record, completion, provider):
        completion = client.complete(
            provider,
            job.model_id,
            prompt,
            max_tokens=provider.generation.escalate_max_tokens,
        )
        record = _record(job, provider, completion, _now(), prompt)
    return completion, record


def run_job(job: Job, provider: Provider, *, force: bool = False) -> Outcome:
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
        cached = load_cached(job, provider)
        if cached is not None:
            return Outcome(job, "cached", cached)

    task = TASKS.get(job.task)
    suffix = task.repair_suffix if task else ""
    attempts = task.parse_attempts if task and suffix else 1

    for attempt in range(attempts):
        completion, record = _ask(job, provider, job.prompt + suffix * attempt)
        record["parse_attempt"] = attempt + 1
        if record["ok"] or not _is_a_parse_failure(completion, record):
            break

    _write(job.path(), record)
    return Outcome(job, "generated" if record["ok"] else "failed", record)


def _is_a_parse_failure(completion: client.Completion, record: dict) -> bool:
    """Did an answer arrive that simply was not shaped like a note?

    True only when the model said something usable-looking and the parser could
    not find a note in it. An empty answer, a 429 or a dropped connection is a
    different problem and re-asking with a repair sentence would not help.
    """
    return completion.ok and not record["ok"]


def run_jobs(
    jobs: list[Job],
    provider: Provider,
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
    with ThreadPoolExecutor(max_workers=max(1, provider.generation.concurrency)) as pool:
        for outcome in pool.map(lambda job: run_job(job, provider, force=force), jobs):
            outcomes.append(outcome)
            if on_done is not None:
                on_done(outcome)
    return outcomes
