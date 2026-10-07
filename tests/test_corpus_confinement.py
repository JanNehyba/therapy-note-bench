"""A confidential corpus may only be sent where it is allowed to go.

Offline. Nothing here calls a provider.

The generation prompt carries the transcript, so a default meaning "every
provider with a token" would make one omitted `--providers` flag a disclosure.
A flag somebody remembers is not a safeguard. The task carries the restriction
and `cmd_generate` cannot build a job that breaks it.

**The judge is the other side of the same transcript.** Its prompt carries the
session too. `judge.Judge` is built for named tasks and refuses to exist for a
confined corpus on a backend the task does not allow; a judge built for no task
may ask nothing.
"""

from __future__ import annotations

import ast
from dataclasses import replace

import pytest

from tnb import judge, tasks
from tnb.config import REPO_ROOT

#: The whole roster, named rather than derived. Every task here reads a public
#: corpus and none is confined, which is a fact about today's corpora and not a
#: reason to drop the guard -- so it is written down and checked.
#:
#: Named, because the empty case cannot be iterated. A loop over "every
#: confidential task" passes when there are none, which is this repository's
#: oldest failure: a test that stops measuring instead of failing.
EVERY_TASK = ("soap", "icare")


def test_a_task_added_here_has_to_declare_its_corpus():
    """The guard against the empty case.

    No task reads a confidential corpus in this repository today. That makes
    every other test in this file agree with a `None` it never had to look at,
    so the roster itself is pinned: a task added without a line in this file is
    a task nobody was made to answer the question about.
    """
    assert sorted(tasks.TASKS) == sorted(EVERY_TASK), (
        "the task roster changed. Say here whether the new task's corpus may leave, "
        "then add it above -- the field defaults to None and a default is not an answer"
    )
    confined = {name: t.confined_to for name, t in tasks.TASKS.items() if t.confined_to}
    assert not confined, f"a confined task exists and this file does not test it: {confined}"


def test_the_english_tasks_are_not_confined():
    """The published corpora are public YouTube transcripts. Confining them
    would be cargo-culting the fix onto data that does not need it, and would
    quietly drop three providers from the leaderboard."""
    for name in ("soap", "icare"):
        assert tasks.TASKS[name].confined_to is None


def test_generate_refuses_rather_than_relying_on_a_flag():
    """The enforcement is in `cmd_generate`, before a job exists. Read from the
    source: a check that lives only in a docstring is what was there before."""
    source = (REPO_ROOT / "src" / "tnb" / "cli.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "cmd_generate":
            continue
        body = ast.dump(node)
        assert "confined_to" in body, "cmd_generate does not consult Task.confined_to"
        # And it must decide before building jobs, not filter them afterwards:
        # a job that exists can be run by something else.
        where = source.index("confined_to", node.lineno)
        builds = source.index("generation.build_jobs", node.lineno)
        assert where < builds, "the check runs after the jobs are built"
        return
    raise AssertionError("cmd_generate not found")


def test_the_restriction_survives_a_task_being_added():
    """Every task either says where it may go or says it does not care. A field
    that defaults to None is only safe while somebody notices it is None."""
    for name, task in tasks.TASKS.items():
        assert hasattr(task, "confined_to"), name
        assert task.confined_to is None or isinstance(task.confined_to, tuple), name


def _config(model: str, backend: str = "") -> judge.JudgeConfig:
    return judge.JudgeConfig(
        project="", location="", credentials_path="", model=model, backend=backend
    )


def test_a_judge_refuses_to_be_built_for_a_corpus_its_backend_may_not_reach():
    """The judge-side half of the guard. Both published judges run outside
    e-INFRA, so a task confined to it can be generated for and not scored --
    the right state until a judge inside it exists and is calibrated."""
    confined = replace(tasks.TASKS["soap"], confined_to=("einfra",))
    for model in ("gemini-3.1-pro-preview", "gpt-5.6-terra"):
        with pytest.raises(judge.ConfinedCorpus, match="einfra"):
            judge.Judge(_config(model), tasks=(confined,))


def test_a_judge_on_a_permitted_backend_is_built_and_the_override_is_what_counts():
    vertex_only = replace(tasks.TASKS["soap"], confined_to=("vertex",))
    built = judge.Judge(_config("gemini-3.1-pro-preview"), tasks=(vertex_only,))
    assert built.tasks == (vertex_only,)
    with pytest.raises(judge.ConfinedCorpus, match="openai"):
        judge.Judge(_config("gpt-5.6-terra"), tasks=(vertex_only,))
    # `JudgeConfig.backend` overrides the name-derived transport. The check reads
    # the property the transport reads, so the two cannot disagree.
    judge.Judge(_config("gpt-5.6-terra", backend="vertex"), tasks=(vertex_only,))


def test_the_public_tasks_build_on_every_backend():
    for model in ("gemini-3.1-pro-preview", "gpt-5.6-terra"):
        judge.Judge(_config(model), tasks=tuple(tasks.TASKS.values()))


def test_a_judge_built_for_no_task_may_ask_nothing():
    """The cache-only readers build a judge for its fingerprint and cache
    directory. That object must not be a way around the guard."""
    client = judge.Judge(_config("gemini-3.1-pro-preview"), tasks=())
    assert client.config.fingerprint()
    with pytest.raises(judge.ConfinedCorpus, match="no task"):
        client.ask("a question")
    # Counting tokens sends the prompt to Vertex as well.
    with pytest.raises(judge.ConfinedCorpus, match="no task"):
        client.count_tokens("a question")


def test_every_judge_in_the_harness_is_built_for_named_tasks():
    """Read from the source, like the generation-side check. A construction
    that omits `tasks=` fails when it runs, and the cache-only paths run
    rarely; this fails on the day it is written."""
    for path in sorted((REPO_ROOT / "src" / "tnb").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name != "Judge":
                continue
            assert any(k.arg == "tasks" for k in node.keywords), (
                f"{path.relative_to(REPO_ROOT)}:{node.lineno} builds a judge for no named task"
            )


class _RecordingBackend(judge.Backend):
    """A transport that records what it was handed and never opens a socket."""

    def __init__(self):
        self.prompts = []

    def count_tokens(self, config, prompt):
        self.prompts.append(prompt)
        return 1

    def token(self, config, *, force_refresh=False):
        raise AssertionError("no request may be prepared for a denied judge")


def test_a_denied_judge_makes_no_transport_call_and_an_allowed_one_does(monkeypatch):
    """The completion condition of audit finding A01, checked on a mock transport."""
    fake = _RecordingBackend()
    monkeypatch.setitem(judge.BACKENDS, "vertex", fake)
    confined = replace(tasks.TASKS["soap"], confined_to=("einfra",))
    with pytest.raises(judge.ConfinedCorpus):
        judge.Judge(_config("gemini-3.1-pro-preview"), tasks=(confined,))
    with pytest.raises(judge.ConfinedCorpus):
        judge.Judge(_config("gemini-3.1-pro-preview"), tasks=()).count_tokens("the transcript")
    assert fake.prompts == []
    allowed = judge.Judge(_config("gemini-3.1-pro-preview"), tasks=(tasks.TASKS["soap"],))
    assert allowed.count_tokens("a public prompt") == 1
    assert fake.prompts == ["a public prompt"]
