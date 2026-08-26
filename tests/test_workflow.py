"""The button in the Actions tab, checked against the CLI it calls.

For as long as it existed, the workflow's central step ran `tnb run` -- a stub
that prints "not built yet" and exits 2 -- while exporting `ANTHROPIC_API_KEY`,
which nothing in ``src/`` reads, and none of the four variables a judge needs.
Nothing failed locally, because nothing here looked at the workflow at all.

Two properties, both mechanical:

* every ``tnb`` subcommand the workflow calls exists and is implemented;
* every secret it exports is read by the code, and every trigger is one
  somebody chose.
"""

from __future__ import annotations

import re

import pytest
import yaml

from tnb import cli
from tnb.config import REPO_ROOT

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "benchmark.yml"

#: `uv run tnb <subcommand>`, wherever it appears in a `run:` block.
CALLS = re.compile(r"\buv run tnb\s+([a-z][a-z-]*)")

#: Secrets referenced as `${{ secrets.NAME }}`.
SECRETS = re.compile(r"\$\{\{\s*secrets\.([A-Z_][A-Z0-9_]*)\s*\}\}")


@pytest.fixture(scope="module")
def workflow() -> dict:
    # `on:` is the YAML 1.1 boolean `True` once parsed, which is a trap worth
    # naming rather than working around silently.
    parsed = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    parsed["on"] = parsed.pop(True, parsed.get("on"))
    return parsed


@pytest.fixture(scope="module")
def text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _subcommands() -> dict[str, object]:
    """Every `tnb` subcommand, mapped to the function it dispatches to."""
    import argparse

    parser = cli.build_parser()
    actions = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    assert actions, "the CLI has no subcommands to check against"
    return {name: sub.get_default("func") for name, sub in actions[0].choices.items()}


def test_every_command_the_workflow_calls_exists(text):
    called = set(CALLS.findall(text))
    assert called, "the workflow calls no tnb command at all"

    known = _subcommands()
    assert not (called - set(known)), f"not tnb subcommands: {sorted(called - set(known))}"


def test_the_workflow_does_not_call_a_command_that_is_not_built(text):
    """`tnb run` is a stub. The workflow's one substantive step called it."""
    known = _subcommands()
    stubs = sorted(name for name in CALLS.findall(text) if known[name] is cli.cmd_not_implemented)

    assert not stubs, f"called by the workflow and not implemented: {stubs}"


def test_every_secret_the_workflow_exports_is_read_by_something(workflow, text):
    """It exported `ANTHROPIC_API_KEY` for months. Nothing in `src/` reads it.

    A secret in a workflow is not free: it is one more value that exists in the
    runner's environment and can reach a log. One nothing reads is pure risk.
    """
    exported = set(SECRETS.findall(text))
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in (REPO_ROOT / "src").rglob("*.py")
    )
    source += (REPO_ROOT / "models.yaml").read_text(encoding="utf-8")

    unread = sorted(name for name in exported if name not in source)
    assert not unread, f"exported to the runner and read by nothing: {unread}"


def test_a_step_that_needs_a_token_is_given_one(workflow):
    """The mirror of the test above: a step calling a provider needs its key."""
    needs_a_token = {"models", "generate"}
    for step in workflow["jobs"]["benchmark"]["steps"]:
        called = set(CALLS.findall(step.get("run", "")))
        if called & needs_a_token:
            assert step.get("env"), f"{step.get('name')!r} calls a provider with no token"


def test_the_only_trigger_is_the_button(workflow):
    """A run costs e-INFRA quota, which is one person's academic allowance.

    `pull_request` would also make the secrets reachable from a fork. Both are
    deliberate absences and both are cheap to lose in an edit.
    """
    assert set(workflow["on"]) == {"workflow_dispatch"}


def test_the_schedule_is_commented_out_rather_than_deleted(text):
    """So that turning it on is two lines and a decision, not a rewrite."""
    assert "# schedule:" in text
    assert "#   - cron:" in text
