"""The report-level evidence ledger of the 2026-09-13 review.

Attempts and reports were counted together: a failed open-access route left a
report listed as not retrieved after the investigator had supplied its PDF,
the log counters counted rows, and three guidance documents were read without
a record. The ledger keeps one record per report with its retrieval history
and derives one status by a rule that lives in ledger.py. Pinned here: the
ledger validates, the status follows the rule, every log row is exactly one
event, the counts are the report-level truth, human verification is never
invented, the file equals the builder's output, and nothing in it is a path,
a token or Czech text.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
REVIEW = REPO / "research" / "gen2" / "review-2026-09-13"


def _module(name: str):
    spec = importlib.util.spec_from_file_location(name, REVIEW / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ledger = _module("ledger")
build_reports = _module("build_reports")
build_flow = _module("build_flow")


@pytest.fixture(scope="module")
def reports() -> dict:
    return json.loads((REVIEW / "reports.json").read_text(encoding="utf-8"))


def _by_source(reports: dict) -> dict[str, dict]:
    return {r["catalog_source"]: r for r in reports["reports"] if r["catalog_source"]}


def test_ledger_validates(reports):
    assert ledger.problems(reports) == []
    sources = [r["catalog_source"] for r in reports["reports"] if r["catalog_source"]]
    assert len(sources) == len(set(sources))
    assert {f"S{n}" for n in range(1, 20)} <= set(sources)
    assert sum(1 for s in sources if "_abs_" in s) == 13
    for family in reports["families"]:
        for member in family["members"]:
            report = next(r for r in reports["reports"] if r["report_id"] == member)
            assert report["study_family"] == family["family_id"]


def test_every_retrieval_event_is_dated_and_sequenced(reports):
    for report in reports["reports"]:
        seqs = [e["seq"] for e in report["retrieval_events"]]
        assert seqs == list(range(1, len(seqs) + 1)), report["report_id"]
        for event in report["retrieval_events"]:
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", event["date"])
            assert event["date_source"] and event["route"]


def test_current_status_follows_the_rule(reports):
    for report in reports["reports"]:
        assert report["current_status"] == ledger.derive_status(report["retrieval_events"])
        assert report["current_file"] == ledger.current_file(report["retrieval_events"])
    # The rule itself, on synthetic histories.
    fail = {"seq": 1, "outcome": "not_retrieved", "date": "2026-09-13"}
    ok = {"seq": 2, "outcome": "retrieved", "date": "2026-09-13", "file": "a.pdf"}
    late_fail = {"seq": 3, "outcome": "not_retrieved", "date": "2026-09-14"}
    assert ledger.derive_status([]) == "not_sought"
    assert ledger.derive_status([fail]) == "not_retrieved"
    assert ledger.derive_status([fail, ok]) == "retrieved"
    assert ledger.derive_status([fail, ok, late_fail]) == "retrieved"
    withdrawn = {**ok, "superseded_by_correction": "2026-09-15"}
    assert ledger.derive_status([fail, withdrawn]) == "not_retrieved"


def test_retrieved_events_with_a_file_carry_bytes_and_sha256(reports):
    for report in reports["reports"]:
        for event in report["retrieval_events"]:
            if event["outcome"] == "retrieved":
                assert event["file"], report["report_id"]
            if event["file"]:
                assert re.fullmatch(r"[0-9a-f]{64}", event["sha256"])
                assert type(event["bytes"]) is int and event["bytes"] > 0
                assert event["checksum_source"]


def test_human_verification_is_never_invented(reports):
    assert reports["counts"]["human_verified"] == 0
    screening = json.loads((REVIEW / "screening-decisions.json").read_text(encoding="utf-8"))
    for report in reports["reports"]:
        assert report["reading"]["human_verified"] is None
        assert report["reading"]["human_verification"] is None
        if screening["human_decisions_made"] == 0:
            assert report["screening"]["human_decision"] is None
    for family in reports["families"]:
        assert family["assessed_by"] is None or family["sample_overlap"] == "established"


def test_catalog_reports_count_19_18_1(reports):
    counts = reports["counts"]["catalog_reports"]
    assert counts == {"sought": 19, "retrieved": 18, "not_retrieved": 1, "not_sought": 0}
    by_source = _by_source(reports)
    assert by_source["S5"]["current_status"] == "not_retrieved"
    assert by_source["S5"]["report_id"] == "doi:10.1197/jamia.m2404"
    assert reports["counts"]["abstract_only_reports"]["not_sought"] == 13


def test_psychres_2026_is_retrieved_after_a_failed_attempt(reports):
    s19 = _by_source(reports)["S19"]
    outcomes = [e["outcome"] for e in s19["retrieval_events"]]
    assert outcomes == ["not_retrieved", "retrieved"]
    assert s19["retrieval_events"][1]["route_kind"] == "investigator_supplied"
    assert s19["retrieval_events"][1]["sha256"].startswith("9fa660246f02")
    assert s19["current_status"] == "retrieved"
    assert s19["report_id"] in reports["counts"]["retrieved_after_failed_attempt"]


def test_every_log_row_is_a_primary_event_exactly_once(reports):
    log = json.loads((REVIEW / "fulltext-retrieval-log.json").read_text(encoding="utf-8"))
    primary = [
        e["log_row"]["slug"]
        for r in reports["reports"]
        for e in r["retrieval_events"]
        if e.get("log_row") and "field" not in e["log_row"]
    ]
    assert sorted(primary) == sorted(r["slug"] for r in log["records"])
    derived = sum(
        1
        for r in reports["reports"]
        for e in r["retrieval_events"]
        if not e.get("log_row") or "field" in e["log_row"]
    )
    assert reports["counts"]["attempts"]["total"] == len(log["records"]) + derived


def test_derived_from_digests_match(reports):
    for name, digest in reports["derived_from"].items():
        assert hashlib.sha256((REVIEW / name).read_bytes()).hexdigest() == digest, name


def test_reports_equals_the_builder_output(reports):
    rebuilt = build_reports.build(*(build_reports.read(name) for name in build_reports.INPUTS))
    assert rebuilt == reports


def test_ledger_is_public_safe():
    text = (REVIEW / "reports.json").read_text(encoding="utf-8")
    assert "C:\\" not in text and "/Users/" not in text
    assert not re.search(r"[\u00C0-\u017F]", text)
    assert "view_only" not in text and "casa_token" not in text
    for key in ("dataset_checksums", "failure_reasons", "unreached_reasons"):
        assert key not in text


def test_append_event_never_touches_existing_events(reports):
    s19 = _by_source(reports)["S19"]["report_id"]
    before = json.dumps(reports, sort_keys=True)
    event = {
        "date": "2026-09-16",
        "date_source": "test",
        "route": "publisher page",
        "route_kind": "publisher",
        "outcome": "not_retrieved",
        "file": None,
    }
    grown = ledger.append_event(reports, s19, event)
    assert json.dumps(reports, sort_keys=True) == before
    report = next(r for r in grown["reports"] if r["report_id"] == s19)
    assert report["retrieval_events"][-1]["seq"] == len(report["retrieval_events"])
    assert report["current_status"] == "retrieved"
    assert report["last_attempt_date"] == "2026-09-16"
    with pytest.raises(ValueError, match="unknown report"):
        ledger.append_event(reports, "doi:nobody", event)
    with pytest.raises(ValueError, match="needs"):
        ledger.append_event(reports, s19, {"date": "2026-09-16"})


@pytest.fixture(scope="module")
def flow() -> dict:
    return json.loads((REVIEW / "flow.json").read_text(encoding="utf-8"))


def test_flow_equals_the_generator_output(flow):
    rebuilt = build_flow.build(*(build_flow.read(name) for name in build_flow.INPUTS))
    assert rebuilt == flow
    for name, digest in flow["derived_from"].items():
        assert hashlib.sha256((REVIEW / name).read_bytes()).hexdigest() == digest, name


def test_flow_full_text_is_report_level(flow, reports):
    full = flow["full_text"]
    assert full["unit"] == "report"
    assert {k: full["catalog_reports"][k] for k in ("sought", "retrieved", "not_retrieved")} == {
        "sought": 19,
        "retrieved": 18,
        "not_retrieved": 1,
    }
    listed = {d["catalog_source"] for d in full["catalog_reports"]["not_retrieved_detail"]}
    assert listed == {"S5"}
    assert full["retrieval_attempts"]["unit"] == "attempt"
    assert full["retrieval_attempts"]["total"] == reports["counts"]["attempts"]["total"]
    assert full["retrieval_attempts"]["total"] > full["catalog_reports"]["sought"]


def test_flow_preserves_the_correction_history(flow):
    recorded = json.loads((REVIEW / "flow-recorded.json").read_text(encoding="utf-8"))
    assert flow["corrections"] == recorded["corrections"]
    dates = [c["date"] for c in flow["corrections"]]
    assert dates == sorted(dates) and dates[-1] == "2026-09-15"
    assert any("attempts" in c["what"] for c in flow["corrections"])


def test_flow_identification_derives_from_the_search_logs(flow):
    by_name = {
        d["name"].split("/")[0].split(" ")[0]: d for d in flow["identification"]["databases"]
    }
    assert by_name["PubMed"]["records"] == 8820
    assert by_name["ACL"]["records"] == 2577
    assert flow["identification"]["records_from_databases"] == 11397
    assert flow["identification"]["not_parsed_into_pool"]["count"] == 35
    other = flow["identification"]["other_methods"]["counts"]
    assert "search_and_screening" not in other
    assert sum(other.values()) == sum(
        1
        for r in json.loads((REVIEW / "reports.json").read_text(encoding="utf-8"))["reports"]
        if r["route"]["kind"] != "search_and_screening"
    )
    assert {d["name"] for d in flow["identification"]["databases_not_searched"]} == {
        "APA PsycINFO",
        "Scopus",
    }
