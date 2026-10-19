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


# --- what each of the 33 acts was, and the claims buried in them -------------

CATALOG = GEN2 / "catalog" / "catalog.json"
PROTOCOL = GEN2 / "protocol.json"


@pytest.fixture(scope="module")
def candidates() -> dict:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    return {c["id"]: c for c in catalog["candidates"]}


def test_every_act_says_what_kind_it_was(decisions):
    """`decision` is the outcome; it never said what the act was.

    Thirty of the 33 are a retention verdict, two are item generation and one is
    agreement to a rewording. Flattened into one shape, a reader counts 33 human
    reviews of the instrument, which is the claim the record must not support by
    accident.
    """
    kinds = decisions["kinds"]
    assert set(kinds) == {"retention", "item_generation", "wording", "construct_correction"}
    ledger = {d["id"] for d in json.loads(PROTOCOL.read_text(encoding="utf-8"))["decision_ledger"]}
    for entry in decisions["decisions"]:
        assert entry["kind"] in kinds, entry["subject"]
        # Every one of them carried a verdict, and D13 returned every verdict to
        # the panel. A retention decision of his that is not superseded would be
        # the author deciding his own instrument's content.
        assert entry["retention_superseded_by"] in ledger, entry["subject"]
    counts = {kind: 0 for kind in kinds}
    for entry in decisions["decisions"]:
        counts[entry["kind"]] += 1
    assert counts["retention"] == 30
    assert counts["item_generation"] == 2
    assert counts["wording"] == 1
    assert decisions["not_adopted"][0]["kind"] == "item_generation"


def test_every_objection_quotes_the_reason_it_was_buried_in(decisions):
    """His words stay verbatim beside the claim read out of them."""
    reasons = {d["subject"]: d["reason"] for d in decisions["decisions"]}
    assert decisions["objections"], "the reasons carried claims; none is lifted"
    for objection in decisions["objections"]:
        assert objection["his_words"] == reasons[objection["subject"]]
        assert objection["claim"].strip()
        assert objection["status"] in {"reflected", "partly_reflected", "open"}


def test_an_objection_is_still_what_the_catalog_says(decisions, candidates):
    """The drift check, and the reason `catalog_says` is read rather than written.

    An objection is marked reflected because a field of the catalog answers it.
    If that field changes, the mark is a claim about a text that no longer
    exists, so the two are compared here instead of trusted: a catalog edit that
    unanswers one of his objections fails this and somebody has to look.
    """
    for objection in decisions["objections"]:
        code = objection["subject"].split(":")[1]
        field = objection["bears_on"]
        live = candidates[code][field]
        assert objection["catalog_says"] == live, (
            f"{code}.{field} has changed since the objection was recorded as "
            f"{objection['status']}; re-read whether it still answers him"
        )


def test_the_open_objections_are_not_quietly_counted_as_answered(decisions):
    """Five of them are open and one is partly answered, and that is the finding.

    A claim he made in 2026-09 that the instrument has not acted on is a gap, not
    a decision. Pinned so that marking one reflected needs an edit here as well
    as in the file.
    """
    by_status: dict[str, list[str]] = {}
    for objection in decisions["objections"]:
        by_status.setdefault(objection["status"], []).append(objection["subject"])
    assert sorted(by_status["open"]) == [
        "construct:K07",
        "construct:K12",
        "construct:K13",
        "construct:K14",
        "construct:K31",
    ]
    assert by_status["partly_reflected"] == ["construct:K27"]


def test_the_record_says_the_thirty_three_are_read_two_ways(decisions):
    """Two tracked files disagree about the same 33 acts, and neither said so.

    `review-record.json` records them as mode 'human' because that is what the
    form captured; `build_instrument.py` imports them as 'seen_no_objection'
    because he said on 2026-10-08 that he does not stand behind them as
    judgements. Both are true, and a reader who met only the first counted 33
    human reviews.
    """
    said = decisions["the_same_thirty_three_in_two_modes"]
    assert "human" in said and "seen_no_objection" in said
    assert "2026-10-08" in said
    assert decisions["where_the_rest_of_his_acts_are_recorded"].strip()


def test_the_record_itself_says_which_reading_of_human_it_carries(record):
    """And the record, not only the file that disagrees with it.

    A reader who opens `review-record.json` alone sees 33 subjects in mode
    `human`. The sentence is in the record because that is where the number is.
    """
    said = record["what_mode_human_means_here"]
    assert "seen_no_objection" in said
    assert "2026-10-08" in said
    assert record["summary"]["subjects_by_latest_mode"]["human"] == 33


def test_the_paper_says_it_too(decisions):
    """The methods section is where a reviewer meets this, and it went stale once."""
    methods = (REPO / "paper" / "methods.md").read_text(encoding="utf-8")
    assert "seen_no_objection" in methods
    assert "retention verdict" in methods
    counts = {"reflected": 0, "partly_reflected": 0, "open": 0}
    for objection in decisions["objections"]:
        counts[objection["status"]] += 1
    # The paper spells these out, so a change to the file has to reach it.
    assert "Nine are answered" in methods and counts["reflected"] == 9
    assert "five are not answered" in methods and counts["open"] == 5
