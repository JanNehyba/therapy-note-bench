"""The rescued registry review record.

The review of the instrument ran in eight working copies under `local/`, which
git ignores. `research/gen2/decisions.json` kept the 33 construct decisions and
the two blanket delegations, and that was all: the 32 sources, the 61 evidence
items, the Czech measurements and the methods were decided one at a time, and
those records existed nowhere a commit could see. Deleting a stale view would
have deleted them.

Pinned here: the file equals the builder's output, its counts equal its own
lists, it holds the subjects `decisions.json` only covers by a blanket
delegation, and it never upgrades a delegation into a review. The snapshots
themselves are gitignored, so the tests that need them skip where they are
absent rather than passing vacuously.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GEN2 = REPO / "research" / "gen2"
RECORD = GEN2 / "review-record.json"
DECISIONS = GEN2 / "decisions.json"
SNAPSHOTS = REPO / "local"


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_review_record", GEN2 / "build_review_record.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_review_record"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def record() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def decisions() -> dict:
    return json.loads(DECISIONS.read_text(encoding="utf-8"))


def _have_snapshots() -> bool:
    return any(SNAPSHOTS.glob("gen2-review-v*/registry_review_responses/*.json"))


needs_snapshots = pytest.mark.skipif(
    not _have_snapshots(),
    reason="local/gen2-review-v* is gitignored and absent on this machine",
)


# --- the file is what the builder makes of the snapshots --------------------


@needs_snapshots
def test_the_record_equals_the_builder_output(tmp_path, monkeypatch):
    """A hand edit to the record fails, as it does for the review ledger.

    The record exists because the snapshots are not in git. If it could be
    edited by hand it would be a second untracked source rather than a rescue
    of the first one.
    """
    module = _builder()
    out = tmp_path / "review-record.json"
    monkeypatch.setattr(module, "OUT", out)
    assert module.main() == 0
    assert out.read_text(encoding="utf-8") == RECORD.read_text(encoding="utf-8")


@needs_snapshots
def test_every_source_file_is_pinned_by_its_digest(record):
    for source in record["sources"]:
        path = REPO / source["path"]
        assert path.is_file(), source["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"], source["path"]


# --- the counts are the lists ----------------------------------------------


def test_the_summary_counts_its_own_lists(record):
    summary = record["summary"]
    assert summary["response_files"] == len(record["sources"])
    assert summary["decision_records"] == len(record["decisions"])
    assert summary["snapshots"] == len({s["snapshot"] for s in record["sources"]})
    assert summary["subjects"] == len({d["subject"] for d in record["decisions"]})
    assert summary["subjects_decided_differently_across_snapshots"] == len(
        record["subjects_decided_differently_across_snapshots"]
    )
    assert summary["subjects_a_later_snapshot_stopped_naming"] == len(
        record["subjects_a_later_snapshot_stopped_naming"]
    )
    assert sum(summary["subjects_by_kind"].values()) == summary["subjects"]
    assert sum(summary["subjects_by_latest_mode"].values()) == summary["subjects"]
    assert sum(s["decisions"] for s in record["sources"]) == summary["decision_records"]


def test_every_decision_names_a_subject_a_snapshot_and_a_source(record):
    paths = {s["path"] for s in record["sources"]}
    snapshots = {s["snapshot"] for s in record["sources"]}
    for row in record["decisions"]:
        assert row["subject"] and row["decision"] and row["mode"]
        assert row["source"] in paths
        assert row["snapshot"] in snapshots


# --- the rescue is load-bearing --------------------------------------------


def test_it_holds_the_subjects_decisions_json_covers_only_by_delegation(record, decisions):
    """The point of the file: what a blanket instruction stood in for.

    `decisions.json` records "ber to jako prectene" as a delegation over the
    source and evidence subjects. That is the policy. The 32 source and 61
    evidence records it produced are the evidence that the policy was applied,
    and they are only here.
    """
    delegated_kinds = {kind for row in decisions["delegations"] for kind in row["subjects"]}
    assert {"source", "evidence"} <= delegated_kinds

    tracked = DECISIONS.read_text(encoding="utf-8")
    subjects = {row["subject"] for row in record["decisions"]}
    sources = {s for s in subjects if s.startswith("source:")}
    evidence = {s for s in subjects if s.startswith("evidence:")}
    assert len(sources) == 32
    assert len(evidence) == 61
    assert not any(subject in tracked for subject in sources | evidence)


def test_the_constructs_are_in_both_and_agree_on_their_count(record, decisions):
    subjects = {row["subject"] for row in record["decisions"]}
    constructs = {s for s in subjects if s.startswith("construct:")}
    assert len(constructs) == len(decisions["decisions"]) == 33


# --- a delegation never becomes a review -----------------------------------


def test_a_delegated_decision_is_never_recorded_as_human(record):
    """Whatever rests on these subjects may not be called human-verified.

    106 of the 139 subjects carry the assistant's reading under a recorded
    delegation. The registry keeps that distinction (`delegated_subjects`), and
    the rescue would defeat it by flattening the mode away.
    """
    by_mode = record["summary"]["subjects_by_latest_mode"]
    assert by_mode["delegated"] == 106
    assert by_mode["human"] == 33
    assert set(by_mode) <= {"human", "human_with_ai", "delegated", "seen_no_objection"}

    delegated = {row["subject"] for row in record["decisions"] if row["mode"] == "delegated"}
    human = {row["subject"] for row in record["decisions"] if row["mode"] == "human"}
    assert not delegated & human, "a subject recorded both ways would hide which it is"


def test_the_record_claims_no_authority_over_the_registry(record):
    """It transcribes; it does not decide.

    One subject was decided twice (K23: `revise`, then `accept` of the
    rewritten wording, with the subject digest moving between them). The file
    lists both and names no winner, because picking one would be a decision
    nobody made.
    """
    assert "picks no winner" in record["what_this_is"]
    assert "supersedes nothing" in record["what_this_is"]
    changed = record["subjects_decided_differently_across_snapshots"]
    for entry in changed:
        assert len(entry["records"]) >= 2
        assert "current" not in entry and "winner" not in entry
