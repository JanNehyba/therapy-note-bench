"""The report-level evidence ledger: one record per report, its retrieval history, one status.

A report is a thing that can be sought and read: an article, a preprint, a
guideline, a manual. A retrieval attempt is an event on a report, and a report
can have several -- a failed open-access route, then a copy the investigator
supplied. The status a reader needs is derived from the events by one rule
that lives here and nowhere else: the latest successful event wins, a failed
attempt after a success does not revert it, and a success is withdrawn only by
a dated correction, never by deleting the event.

Everything in the ledger is public-safe: citations, identifiers, routes,
dates, sizes and digests. No article text, no clinical text, no absolute path.
Human verification is recorded only with a named human record; the builder
never writes one.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

VERSION = "reports-v1"

KINDS = (
    "database_record",
    "supplementary_discovery",
    "professional_guidance",
    "methodological_guidance",
    "supporting_material",
)
ROUTE_KINDS = (
    "search_and_screening",
    "known_before_search",
    "professional_guidance",
    "methodological_guidance",
    "citation_from",
    "author_search_from",
    "remainder_audit_sample",
    "not_recorded",
)
EVENT_ROUTE_KINDS = (
    "open_access_api",
    "direct_url",
    "publisher",
    "repository",
    "web_page",
    "investigator_supplied",
)
OUTCOMES = ("retrieved", "not_retrieved", "wrong_report")
STATUSES = ("retrieved", "not_retrieved", "not_sought")
USES = ("evidence", "guidance", "method", "support")
OVERLAP = ("established", "suspected", "not_assessed", "not_applicable")
ID_RULE = (
    "doi:<own DOI, normalised> when the DOI is verified by a record other than the map "
    "(retrieval log, PubMed export, retrieval seeds); else pmid:<pmid>; else ttl:<normalised "
    "title> for pool records; supp:<slug> for other material; guid:<slug> for guidance "
    "documents without a DOI. Equal to the pool id whenever the pool id is right, and fixed "
    "when the pool is rebuilt."
)
_ID = re.compile(r"^(doi|pmid|ttl|supp|guid):[a-z0-9][a-z0-9._/()+-]*$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def live_events(events: list[dict]) -> list[dict]:
    return [e for e in events if not e.get("superseded_by_correction")]


def derive_status(events: list[dict]) -> str:
    live = live_events(events)
    if any(e["outcome"] == "retrieved" for e in live):
        return "retrieved"
    return "not_retrieved" if live else "not_sought"


def current_file(events: list[dict]) -> dict | None:
    hits = [e for e in live_events(events) if e["outcome"] == "retrieved" and e.get("file")]
    if not hits:
        return None
    last = max(hits, key=lambda e: e["seq"])
    return {"file": last["file"], "bytes": last.get("bytes"), "sha256": last.get("sha256")}


def finish(report: dict) -> dict:
    """Recompute every derived field of one report from its recorded ones."""
    events = sorted(report.get("retrieval_events", []), key=lambda e: e["seq"])
    for seq, event in enumerate(events, start=1):
        event["seq"] = seq
    report["retrieval_events"] = events
    report["current_status"] = derive_status(events)
    report["current_file"] = current_file(events)
    dates = [e["date"] for e in events]
    report["last_attempt_date"] = max(dates) if dates else None
    return report


def recount(ledger: dict) -> dict:
    reports = ledger["reports"]
    catalog = [
        r
        for r in reports
        if r.get("catalog_source")
        and r["catalog_source"].startswith("S")
        and "_abs_" not in r["catalog_source"]
    ]
    abstract = [r for r in reports if r.get("catalog_source") and "_abs_" in r["catalog_source"]]
    others = [
        r for r in reports if not r.get("catalog_source") and r["kind"] != "supporting_material"
    ]
    support = [r for r in reports if r["kind"] == "supporting_material"]
    events = [e for r in reports for e in r["retrieval_events"]]

    def status_counts(group):
        return {s: sum(1 for r in group if r["current_status"] == s) for s in STATUSES}

    by_route: dict[str, int] = {}
    for r in reports:
        by_route[r["route"]["kind"]] = by_route.get(r["route"]["kind"], 0) + 1
    ledger["counts"] = {
        "reports": len(reports),
        "catalog_reports": {"sought": len(catalog), **status_counts(catalog)},
        "abstract_only_reports": {"total": len(abstract), **status_counts(abstract)},
        "other_reports": {"total": len(others), **status_counts(others)},
        "supporting_materials": {"total": len(support), **status_counts(support)},
        "attempts": {
            "total": len(events),
            "succeeded": sum(1 for e in events if e["outcome"] == "retrieved"),
            "failed": sum(1 for e in events if e["outcome"] == "not_retrieved"),
            "wrong_report": sum(1 for e in events if e["outcome"] == "wrong_report"),
            "logged_retroactively": sum(1 for e in events if e.get("logged_retroactively")),
        },
        "retrieved_after_failed_attempt": sorted(
            r["report_id"]
            for r in reports
            if r["current_status"] == "retrieved"
            and any(e["outcome"] != "retrieved" for e in live_events(r["retrieval_events"]))
        ),
        "by_route": dict(sorted(by_route.items())),
        "human_verified": sum(1 for r in reports if r["reading"].get("human_verified") is True),
    }
    return ledger


def problems(ledger: dict) -> list[str]:
    """Every way the ledger could be wrong, as messages; empty means valid."""
    out: list[str] = []
    if ledger.get("version") != VERSION:
        out.append("version")
    ids: set[str] = set()
    families = {f["family_id"]: f for f in ledger.get("families", [])}
    for f in families.values():
        if f.get("sample_overlap") not in OVERLAP:
            out.append(f"family {f['family_id']}: sample_overlap")
        if f.get("assessed_by") is not None and f.get("sample_overlap") != "established":
            out.append(f"family {f['family_id']}: assessed_by without an established overlap")
    sources_seen: set[str] = set()
    for r in ledger.get("reports", []):
        rid = r.get("report_id", "")
        if not _ID.match(rid):
            out.append(f"report id {rid!r}")
        if rid in ids:
            out.append(f"duplicate report id {rid}")
        ids.add(rid)
        if r.get("kind") not in KINDS:
            out.append(f"{rid}: kind")
        if r.get("route", {}).get("kind") not in ROUTE_KINDS:
            out.append(f"{rid}: route kind")
        if r["route"]["kind"] in ("citation_from", "author_search_from") and not r["route"].get(
            "from"
        ):
            out.append(f"{rid}: route without a source report")
        src = r.get("catalog_source")
        if src:
            if src in sources_seen:
                out.append(f"{rid}: catalog source {src} used twice")
            sources_seen.add(src)
        fam = r.get("study_family")
        if fam is not None and (fam not in families or rid not in families[fam]["members"]):
            out.append(f"{rid}: family {fam} does not list it")
        if r.get("inclusion", {}).get("use") not in USES + (None,):
            out.append(f"{rid}: inclusion use")
        reading = r.get("reading", {})
        if reading.get("human_verified") is True and not reading.get("human_verification"):
            out.append(f"{rid}: human_verified without a human record")
        if r.get("screening", {}).get("human_decision") is not None and not r["screening"].get(
            "human_decision_record"
        ):
            out.append(f"{rid}: human screening decision without a record")
        events = r.get("retrieval_events", [])
        for n, e in enumerate(events, start=1):
            where = f"{rid} event {n}"
            if e.get("seq") != n:
                out.append(f"{where}: seq")
            if not _DATE.match(e.get("date") or ""):
                out.append(f"{where}: date")
            if not e.get("date_source"):
                out.append(f"{where}: date_source")
            if not e.get("route"):
                out.append(f"{where}: route")
            if e.get("route_kind") not in EVENT_ROUTE_KINDS:
                out.append(f"{where}: route_kind")
            if e.get("outcome") not in OUTCOMES:
                out.append(f"{where}: outcome")
            if e.get("file"):
                if "/" in e["file"] or "\\" in e["file"]:
                    out.append(f"{where}: file is not a basename")
                if type(e.get("bytes")) is not int or e["bytes"] <= 0:
                    out.append(f"{where}: bytes")
                if not _SHA.match(e.get("sha256") or ""):
                    out.append(f"{where}: sha256")
                if not e.get("checksum_source"):
                    out.append(f"{where}: checksum_source")
            if e["outcome"] == "retrieved" and not e.get("file"):
                out.append(f"{where}: retrieved without a file")
        if r.get("current_status") != derive_status(events):
            out.append(f"{rid}: current_status is not derived")
        if r.get("current_file") != current_file(events):
            out.append(f"{rid}: current_file is not derived")
    for fam in families.values():
        for member in fam["members"]:
            if member not in ids:
                out.append(f"family {fam['family_id']}: unknown member {member}")
    return out


def validate(ledger: dict) -> dict:
    found = problems(ledger)
    if found:
        raise ValueError("invalid ledger: " + "; ".join(found[:12]))
    return ledger


def append_event(ledger: dict, report_id: str, event: dict) -> dict:
    """A copy of the ledger with one more event on one report; older events untouched."""
    for key in ("date", "route", "route_kind", "outcome"):
        if not event.get(key):
            raise ValueError(f"event needs {key}")
    copy = json.loads(json.dumps(ledger))
    for report in copy["reports"]:
        if report["report_id"] == report_id:
            before = json.dumps(report["retrieval_events"], sort_keys=True)
            report["retrieval_events"].append({**event, "seq": len(report["retrieval_events"]) + 1})
            finish(report)
            after = json.dumps(report["retrieval_events"][:-1], sort_keys=True)
            if before != after:
                raise AssertionError("appending an event changed an older event")
            return validate(recount(copy))
    raise ValueError(f"unknown report {report_id}")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, ledger: dict) -> None:
    path.write_bytes((json.dumps(ledger, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
