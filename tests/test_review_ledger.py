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
fetch_fulltext = _module("fetch_fulltext")


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
    # Twelve since 2026-10-07: SESPI was read in full and became S20.
    assert sum(1 for s in sources if "_abs_" in s) == 12
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


def test_catalog_reports_count_21_21_0(reports):
    """Eighteen of nineteen until 2026-10-07, and then twenty-one of twenty-one.

    S5, the 2008 preliminary report of the PDQI family, had been recorded as not
    retrieved since 2026-09-13 and was found in a repository on the second
    attempt. Having it is not reading it: its reading basis is still the
    abstract and the catalog still says `not_retrieved` for its verification,
    which is the field that tracks reading.
    """
    counts = reports["counts"]["catalog_reports"]
    assert counts == {"sought": 21, "retrieved": 21, "not_retrieved": 0, "not_sought": 0}
    s5 = _by_source(reports)["S5"]
    assert s5["report_id"] == "doi:10.1197/jamia.m2404"
    assert s5["current_status"] == "retrieved"
    assert [e["date"] for e in s5["retrieval_events"]] == ["2026-09-13", "2026-10-07"]
    assert [e["outcome"] for e in s5["retrieval_events"]] == ["not_retrieved", "retrieved"]
    assert s5["reading"]["basis"] == "abstract", "retrieved is not read"
    # The group grew by two the same day, from the other direction: SESPI was
    # read and left the abstract-only group as S20, and its 2025 application
    # joined as S21 from the Scopus round.
    by_source = _by_source(reports)
    assert by_source["S20"]["report_id"] == "pmid:31367401"
    assert by_source["S20"]["reading"]["basis"] == "full_text"
    assert by_source["S21"]["report_id"] == "doi:10.1002/capr.12829"
    assert by_source["S21"]["route"]["kind"] == "search_and_screening"
    assert by_source["S21"]["retrieval_events"][-1]["date"] == "2026-10-07"


def test_having_the_file_is_not_the_same_as_having_read_it(reports):
    """Six of the thirteen abstract-only reports arrived on 2026-09-16.

    The investigator downloaded them and they are recorded as retrieved, with a
    date, a route and a checksum. Nobody has read them, so their reading basis
    is still the abstract and the catalog still rests on the abstract for every
    claim they support. Those are two different facts and the ledger keeps them
    apart; collapsing them is how an unread paper becomes a citation.
    """
    abstract_only = [
        report
        for report in reports["reports"]
        if (report["catalog_source"] or "").startswith("S_abs_")
    ]
    # Twelve since SESPI was read in full on 2026-10-07 and became S20.
    assert len(abstract_only) == 12
    retrieved = [r for r in abstract_only if r["current_status"] == "retrieved"]
    assert len(retrieved) == 10
    # Nothing is unsought any more: the seven that had never been tried were
    # tried on 2026-10-07 and five of them came down. The two that did not are
    # recorded as attempted and failed, which is a different fact from untried.
    # The group then lost one from the top: SESPI was read and became S20.
    counts = reports["counts"]["abstract_only_reports"]
    assert counts == {"total": 12, "retrieved": 10, "not_retrieved": 2, "not_sought": 0}
    failed = {r["catalog_source"] for r in abstract_only if r["current_status"] != "retrieved"}
    assert failed == {"S_abs_disparity", "S_abs_summac"}
    for report in abstract_only:
        assert report["reading"]["human_verified"] is None
    # Six arrived on 2026-09-16 and were read on 2026-09-20; five arrived on
    # 2026-10-07 and nobody has read them. Both facts are dated, and the reading
    # basis moves only when the reading happens.
    for report in retrieved:
        event = report["retrieval_events"][-1]
        assert event["sha256"] and event["bytes"] > 0
        assert event["date"] in {"2026-09-16", "2026-10-07"}
        if event["date"] == "2026-09-16":
            assert event["route_kind"] == "investigator_supplied"
            assert report["reading"]["basis"] == "full_text", report["catalog_source"]
            assert "2026-09-20" in report["reading"]["ai_read_basis"]
        else:
            assert report["reading"]["basis"] == "abstract", report["catalog_source"]
    for report in abstract_only:
        if report["current_status"] != "retrieved":
            assert report["reading"]["basis"] == "abstract", report["catalog_source"]
            assert report["retrieval_events"], "a failure is an attempt, and is recorded"


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
        assert ledger.sha256_file(REVIEW / name) == digest, name


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
        assert ledger.sha256_file(REVIEW / name) == digest, name


def test_flow_full_text_is_report_level(flow, reports):
    full = flow["full_text"]
    assert full["unit"] == "report"
    assert {k: full["catalog_reports"][k] for k in ("sought", "retrieved", "not_retrieved")} == {
        "sought": 21,
        "retrieved": 21,
        "not_retrieved": 0,
    }
    assert full["catalog_reports"]["not_retrieved_detail"] == []
    assert full["retrieval_attempts"]["unit"] == "attempt"
    assert full["retrieval_attempts"]["total"] == reports["counts"]["attempts"]["total"]
    assert full["retrieval_attempts"]["total"] > full["catalog_reports"]["sought"]


def test_the_two_audited_strata_are_estimated_apart(flow):
    """The September rate is not applied to records September could not reach.

    The audit of 2026-09-13 sampled the remainder of the PubMed and ACL
    searches. The Scopus searches added 1639 records to the remainder that no
    earlier query reached, so they are a stratum of their own with their own
    sample, their own seed and their own rate. Multiplying the old rate by the
    new, larger remainder would have reported an estimate for a population
    nobody sampled.
    """
    screening = flow["screening"]
    parent = screening["audit_of_unscreened"]
    scopus = screening["audit_of_unscreened_scopus_remainder"]
    assert parent["frame_size"] + scopus["frame_size"] == screening["remainder_not_screened"]
    assert parent["sampled"] == scopus["sampled"] == 200
    assert parent["sampling"].endswith("20260913") and scopus["sampling"].endswith("20261007")
    # Each estimate is its own rate times its own frame, not the other's.
    for block in (parent, scopus):
        rate = block["clearly_eligible_found"] / block["sampled"]
        assert block["estimated_eligible_records_below_threshold"] == round(
            block["frame_size"] * rate
        )
        lo, hi = block["estimated_ci95"]
        assert lo <= block["estimated_eligible_records_below_threshold"] <= hi
    assert scopus["clear_rate"] > parent["clear_rate"]
    # ... and the difference between the two rates is not offered as a finding.
    assert "not a measurement" in scopus["not_a_measured_ratio"]


def test_the_two_screening_rounds_are_kept_apart(flow):
    """One priority stratum, two dated rounds, and no record in neither.

    The 180 records the Scopus searches put above the threshold were screened
    on 2026-10-07. Every one of them carries a decision with a reason, which
    the first round's exclusions do not, and the reason a record is still
    unscreened names the event that put it in the stratum.
    """
    screening = flow["screening"]
    assert [r["round"] for r in screening["rounds"]] == ["2026-09-13", "2026-10-07"]
    assert screening["ai_proposals_by_round"]["2026-10-07"] > 0
    assert (
        screening["priority_stratum_screened"] + screening["priority_stratum_not_screened"]
        == screening["pool"] - screening["remainder_not_screened"]
    )


def test_flow_preserves_the_correction_history(flow):
    recorded = json.loads((REVIEW / "flow-recorded.json").read_text(encoding="utf-8"))
    assert flow["corrections"] == recorded["corrections"]
    dates = [c["date"] for c in flow["corrections"]]
    assert dates == sorted(dates) and dates[-1] == "2026-09-15"
    assert any("attempts" in c["what"] for c in flow["corrections"])


def test_flow_identification_derives_from_the_search_logs(flow):
    """Three databases, and one of the three counts is a floor rather than a total.

    PubMed and the ACL corpus report how many records a query matched. Scopus
    was searched by hand on 2026-10-07 and the hit count it showed was not
    written down, so its 3172 is the number of rows exported: at least that
    many records, with the shortfall unknown rather than zero. The total is
    marked accordingly, and `downloaded_completely` answers per database
    instead of collapsing an unverifiable claim into one boolean.
    """
    identification = flow["identification"]
    by_name = {d["name"].split("/")[0].split(" ")[0]: d for d in identification["databases"]}
    assert by_name["PubMed"]["records"] == 8820
    assert by_name["ACL"]["records"] == 2577
    assert by_name["Scopus"]["records"] == 3172
    assert identification["records_from_databases"] == 8820 + 2577 + 3172
    assert identification["records_from_databases_includes_a_lower_bound"] is True
    assert [d["name"] for d in identification["databases"] if d["records_is_a_lower_bound"]] == [
        "Scopus"
    ]
    assert identification["downloaded_completely"] == {
        "PubMed/MEDLINE": True,
        "ACL Anthology": True,
        "Scopus": "unverified",
    }
    assert by_name["Scopus"]["queries"] == 3 and by_name["Scopus"]["search_date"] == "2026-10-07"
    # The 35 unparsed records are the PubmedBookArticle entries, and every
    # Scopus row parsed, so the figure did not move when the pool grew.
    assert identification["not_parsed_into_pool"]["count"] == 35
    other = flow["identification"]["other_methods"]["counts"]
    assert "search_and_screening" not in other
    assert sum(other.values()) == sum(
        1
        for r in json.loads((REVIEW / "reports.json").read_text(encoding="utf-8"))["reports"]
        if r["route"]["kind"] != "search_and_screening"
    )
    # Scopus was on this list until 2026-10-07 and is not on it now; the
    # reason it was there, an API that needs a key, is kept with the amendment
    # that moved it. PsycINFO is unchanged and still unsearched.
    assert {d["name"] for d in flow["identification"]["databases_not_searched"]} == {"APA PsycINFO"}
    searched_later = flow["identification"]["databases_searched_after_the_parent_round"]
    assert [d["name"] for d in searched_later] == ["Scopus"]
    assert searched_later[0]["searched_on"] == "2026-10-07"
    assert searched_later[0]["amendment"] == "AM-7"


def _review_copy(tmp_path: Path) -> Path:
    copy = tmp_path / "review"
    copy.mkdir()
    for name in set(build_reports.INPUTS) | set(build_flow.INPUTS):
        (copy / name).write_bytes((REVIEW / name).read_bytes())
    return copy


def test_fetch_appends_to_the_map_and_rebuilds_the_ledger_not_the_log(tmp_path):
    """A new attempt is an event on the report, recorded in the map so the
    builder reproduces it; the 2026-09-13 log stays byte-identical, and a
    later failure does not revert an earlier success."""
    copy = _review_copy(tmp_path)
    log_digest = ledger.sha256_file(copy / "fulltext-retrieval-log.json")
    s5 = "doi:10.1197/jamia.m2404"

    def found(report):
        route = "unpaywall repository https://example.invalid/s5.pdf"
        return b"%PDF-1.4 synthetic", route, "open_access_api", "pdf"

    grown = fetch_fulltext.run(
        copy, [s5], fetch=found, today="2026-10-08", fulltext_dir=tmp_path / "ft"
    )
    report = next(r for r in grown["reports"] if r["report_id"] == s5)
    assert report["current_status"] == "retrieved"
    assert report["retrieval_events"][-1]["date"] == "2026-10-08"
    expected = hashlib.sha256(b"%PDF-1.4 synthetic").hexdigest()
    assert report["retrieval_events"][-1]["sha256"] == expected
    assert (tmp_path / "ft" / "S5.pdf").read_bytes() == b"%PDF-1.4 synthetic"
    mapping = json.loads((copy / "report-map.json").read_text(encoding="utf-8"))
    entry = next(e for e in mapping["reports"] if e["report_id"] == s5)
    assert entry["events"][-1]["outcome"] == "retrieved"
    assert entry["events"][-1]["log_row"] is None
    rebuilt = build_reports.build(
        *(build_reports.read(n, copy) for n in build_reports.INPUTS), root=copy
    )
    assert rebuilt == json.loads((copy / "reports.json").read_text(encoding="utf-8"))
    flow = json.loads((copy / "flow.json").read_text(encoding="utf-8"))
    assert flow["full_text"]["catalog_reports"]["retrieved"] == 21
    assert ledger.sha256_file(copy / "fulltext-retrieval-log.json") == log_digest

    def gone(report):
        return None, "attempted: publisher (403)", "publisher", ""

    again = fetch_fulltext.run(
        copy, [s5], fetch=gone, today="2026-10-09", fulltext_dir=tmp_path / "ft"
    )
    report = next(r for r in again["reports"] if r["report_id"] == s5)
    outcomes = [e["outcome"] for e in report["retrieval_events"]]
    assert outcomes[-2:] == ["retrieved", "not_retrieved"]
    assert report["current_status"] == "retrieved"
    with pytest.raises(ValueError, match="unknown report"):
        fetch_fulltext.run(
            copy, ["doi:nobody"], fetch=gone, today="2026-10-09", fulltext_dir=tmp_path / "ft"
        )


def test_the_fetch_script_has_no_roster_and_requires_a_report():
    source = (REVIEW / "fetch_fulltext.py").read_text(encoding="utf-8")
    assert "TIER_A" not in source
    with pytest.raises(SystemExit):
        fetch_fulltext.main([])
    log = json.loads((REVIEW / "fulltext-retrieval-log.json").read_text(encoding="utf-8"))
    assert log["superseded_by"]["file"] == "reports.json"


def test_pool_keys_are_the_reports_own_identifiers(reports):
    """The pool once keyed a third of its PubMed records by a cited reference's
    DOI; since the correction of 2026-09-15 every pool key of a report in the
    ledger is the report's own identifier, and the builder has no
    reference-list warning left to print."""
    assert not any("reference list" in d["message"] for d in reports["diagnostics"])
    for report in reports["reports"]:
        pool = report["pool"]
        if pool["in_pool"]:
            assert pool["pool_record_id_status"] in ("matches_report_id", "own_doi_pool_key"), (
                report["report_id"]
            )
    summary = json.loads((REVIEW / "pool-summary.json").read_text(encoding="utf-8"))
    assert "reference list" in summary["doi_rule"]
    assert summary["corrections"][0]["date"] == "2026-09-15"


def test_flow_screening_counts_are_consistent(flow):
    """Records that entered the priority stratum after the AI screen are counted
    as not screened, never folded into the excluded ones."""
    s = flow["screening"]
    assert (
        s["priority_stratum"] == s["priority_stratum_screened"] + s["priority_stratum_not_screened"]
    )
    assert s["pool"] == s["priority_stratum"] + s["remainder_not_screened"]
    assert s["ai_proposals"]["total"] == s["priority_stratum_screened"]
    decisions = json.loads((REVIEW / "screening-decisions.json").read_text(encoding="utf-8"))
    assert all(r["decision"] == "not_screened" for r in decisions["not_screened_detail"])
    assert len(decisions["not_screened_detail"]) == s["priority_stratum_not_screened"]
    assert decisions["human_decisions_made"] == 0
