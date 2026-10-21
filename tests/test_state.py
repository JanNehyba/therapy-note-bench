"""One file says what has been run, and the audit of what is claimed stays at zero.

The repository had no file stating its own state. Five documents each said part of
it in their own words and went stale apart from one another, and on 2026-10-21 an
audit found 42 claims that had gone false -- a pool size given as seven different
numbers across 24 files, twelve searches recorded as not run while four logs held
their dates and export checksums, a rating sheet telling three therapists a count
the sheet contradicted, and a Czech page printing "is measured" for the state
whose English says "an AI proposal awaiting human selection".

Two things are pinned here. `research/gen2/state.json` must equal a fresh run of
its builder, because a state file that has gone stale is worse than none: five
documents disagreeing at least look like five. And `research/gen2/audit.py` must
report no live finding, which is what turns the audit from a report somebody reads
into a gate that holds.

That second assertion is deliberately strict and will fail on the next stale
claim. That is the point, and it is affordable only because the count is at zero:
a test that is red from the day it is written is a test nobody reads.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GEN2 = REPO / "research" / "gen2"


def _module(name: str):
    spec = importlib.util.spec_from_file_location(f"gen2_{name}", GEN2 / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"gen2_{name}"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def state() -> dict:
    return json.loads((GEN2 / "state.json").read_text(encoding="utf-8"))


def test_the_state_file_equals_a_fresh_derivation(state):
    assert state == _module("state").build(), (
        "research/gen2/state.json is stale -- run research/gen2/state.py --write"
    )


def test_it_answers_the_question_nothing_answered_before(state):
    """Whether generation 2 has been run, from the only file that would know.

    Seven claims by the assistant in two days turned on this and every one was
    wrong, because no file said it: generation 2's criteria were analysed against
    generation 1's prompt, four purposes were called live a month after a decision
    cut them to two, and a limitation was written for a measurement that does not
    exist.
    """
    rows = [
        json.loads(line)
        for line in (REPO / "results" / "rows.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    gen1_prompts = {"tneval-soap-v1", "icare-zeroshot-v1"}
    gen2_rows = [r for r in rows if r.get("prompt_version") not in gen1_prompts]

    generations = state["generations"]
    assert generations["rows_in_total"] == len(rows)
    assert generations["generation_1"]["measured"] is True
    assert generations["generation_2"]["measured"] is bool(gen2_rows)
    assert generations["generation_2"]["rows"] == len(gen2_rows)

    # The wording has to follow the number, not be required alongside it. This
    # test used to assert the literal sentence "No note has been written", which
    # a review named as the defect: handed a generation-2 row the builder said
    # `measured: true` and kept that sentence, and the test demanded the sentence
    # rather than asking whether it was true. So what is checked is the
    # conditional, and tests/test_audit_detects.py plants a row to exercise the
    # other branch.
    said = generations["generation_2"]["what_that_means"]
    if gen2_rows:
        assert "has rows in the result ledger" in said
        assert "nothing" not in said.lower()
    else:
        assert "Nothing from generation 2 has been scored" in said
    # And either way it names what the ledger's silence cannot establish.
    assert "pipeline.py" in generations["generation_2"]["what_this_does_not_establish"]


def test_it_names_a_source_for_every_figure_it_reports(state):
    """A figure with no named source is one a reader cannot check."""
    assert set(state["sources"]) >= {"generated_and_scored", "protocol", "catalog", "panel"}
    for where in state["sources"].values():
        for named in where.replace(" and ", ", ").split(", "):
            head = named.split()[0]
            if head.endswith((".json", ".jsonl", "/")):
                assert (REPO / head).exists(), f"{head} is named as a source and is not there"


def test_it_reads_nothing_from_a_gitignored_directory(state):
    """Otherwise it would not be the same file twice, and the test above would lie.

    The first version listed the sheets built under `local/panel/`, which is
    gitignored, so the state file described the machine it ran on.
    """
    assert "local/" not in json.dumps(state["sources"])
    # The note names the directory in order to say that it is not read, so the
    # check is on the shape rather than the word: nothing in the panel block is a
    # list, because a list there could only have come from listing that directory.
    assert not any(isinstance(value, list) for value in state["panel"].values())
    assert "Nothing here is read from" in state["panel"]["note"]
    assert state["panel"]["registration_status_as_the_protocol_states_it"]


def test_the_audit_of_what_is_claimed_reports_nothing_live():
    """The gate. It will fail on the next claim that goes stale, which is its job.

    `in_dated_records` is allowed to be non-zero: a record of a dated round that
    says 36 candidates was true when written, and rewriting it would falsify the
    record rather than repair it.
    """
    report = _module("audit").run()
    live = report["live"]
    assert live == [], "\n".join(
        f"{item['check']} {item['path']}: says {item['says']!r}, "
        f"{item['holder']} holds {item['holds']!r}"
        for item in live
    )
    assert report["counts"]["live"] == 0
    assert report["found_by_reading"], "the classes a script cannot decide must stay listed"


def test_the_audit_artefact_is_what_a_fresh_run_produces():
    recorded = json.loads((GEN2 / "audit-findings.json").read_text(encoding="utf-8"))
    assert recorded == _module("audit").run(), (
        "research/gen2/audit-findings.json is stale -- run research/gen2/audit.py --write"
    )
