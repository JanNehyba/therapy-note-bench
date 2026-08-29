"""A confidential corpus may only be sent where it is allowed to go.

Offline. Nothing here calls a provider.

**The incident.** `tnb generate --tasks deepsy-real,deepsy-translated` was run
without `--providers`. The default is every provider with a token, so all ten
real Czech clinical transcripts went to OpenAI and to Google Vertex: 150 calls,
every one answered, between 01:09 and 03:39 on 2026-08-29. The Deepsy prompt
carries the transcript, so the disclosure was in the request itself.

The published methodology said in the same breath that those sessions never
leave the university's infrastructure. It was true of every run before that one
because whoever ran them happened to pass the flag.

A flag somebody remembers is not a safeguard. The task carries the restriction
and `cmd_generate` cannot build a job that breaks it.
"""

from __future__ import annotations

import ast

from tnb import tasks
from tnb.config import REPO_ROOT

#: Every task whose sessions are confidential. Named here rather than derived,
#: so adding a task over the Czech corpus and forgetting to confine it fails
#: this file rather than a future audit.
MUST_BE_CONFINED = ("czech-real", "czech-translated", "deepsy-real", "deepsy-translated")


def test_every_confidential_task_names_where_it_may_go():
    for name in MUST_BE_CONFINED:
        task = tasks.TASKS[name]
        assert task.confined_to == ("einfra",), (
            f"{name} reads confidential clinical sessions and must be confined to "
            f"the infrastructure that holds them; it says {task.confined_to!r}"
        )


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
