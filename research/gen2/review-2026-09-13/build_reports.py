"""Build reports.json, the report-level evidence ledger, from the tracked records.

Inputs, all tracked: report-map.json (the recorded declarations: which
report a retrieval-log slug belongs to, routes, identifiers, pool position,
events the log never held), fulltext-retrieval-log.json (the attempt rows of
2026-09-13, frozen), screening-decisions.json (AI screening proposals; no
human decision), screening-strata.json and pool-summary.json (for the
derived_from digests). Deterministic: no wall-clock value enters the file.

With --check-local the local exports and full-text files are compared with
the declarations and every disagreement is printed as a diagnostic; the
tracked output does not depend on them.

Errors stop the build; warnings are written into the ledger's diagnostics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger  # noqa: E402

ROOT = Path(__file__).resolve().parent
INPUTS = (
    "report-map.json",
    "fulltext-retrieval-log.json",
    "screening-decisions.json",
    "screening-strata.json",
    "pool-summary.json",
)
LEDGER_DATE = "2026-09-15"


def read(name: str, root: Path = ROOT) -> dict:
    return json.loads((root / name).read_text(encoding="utf-8"))


def _basename(path: str | None) -> str | None:
    if not path:
        return None
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def _log_event(slug: str, row: dict, mapping: dict, diagnostics: list[dict]) -> list[dict]:
    """The events one retrieval-log row stands for, in the order they happened."""
    times = mapping["log_row_times"]
    kinds = mapping["log_row_route_kinds"]
    events: list[dict] = []
    if row.get("correction"):
        when = times.get(slug + "#correction", {})
        events.append(
            {
                "date": "2026-09-13",
                "time": when.get("time"),
                "date_source": when.get("date_source", "fetch run of 2026-09-13"),
                "route": row["route"],
                "route_kind": kinds[slug],
                "outcome": "wrong_report",
                "file": None,
                "bytes": None,
                "sha256": None,
                "checksum_source": None,
                "bytes_source": None,
                "note": row["correction"],
                "remaining_options": None,
                "logged_retroactively": None,
                "log_row": {"slug": slug, "field": "correction"},
                "superseded_by_correction": None,
            }
        )
    when = times.get(slug, {})
    if row.get("retrieved_at"):
        time, date_source = row["retrieved_at"].split(" ")[1], "retrieval log retrieved_at"
    else:
        time, date_source = when.get("time"), when.get("date_source", "fetch run of 2026-09-13")
    file = _basename(row.get("file"))
    size, digest, checksum_source, bytes_source = (
        row.get("bytes"),
        row.get("sha256"),
        "retrieval log" if row.get("sha256") else None,
        "retrieval log" if row.get("bytes") else None,
    )
    if row.get("retrieved") and not file and slug in mapping["log_row_file_fill"]:
        fill = mapping["log_row_file_fill"][slug]
        file, size, digest = fill["file"], fill["bytes"], fill["sha256"]
        checksum_source = bytes_source = (
            "computed 2026-09-15 from the local file; the log row named no file"
        )
        diagnostics.append(
            {
                "level": "warning",
                "subject": slug,
                "message": (
                    "log row is retrieved without a file; file, size and digest recorded "
                    "from the local copy on 2026-09-15"
                ),
            }
        )
    if (
        slug in mapping["log_row_bytes_measured"]
        and mapping["log_row_bytes_measured"][slug] != size
    ):
        diagnostics.append(
            {
                "level": "warning",
                "subject": slug,
                "message": (
                    f"log records {size} bytes; the local file measures "
                    f"{mapping['log_row_bytes_measured'][slug]} and its digest matches the log"
                ),
            }
        )
        size = mapping["log_row_bytes_measured"][slug]
        bytes_source = "measured 2026-09-15 from the local file; the log value does not match"
    events.append(
        {
            "date": "2026-09-13",
            "time": time,
            "date_source": date_source,
            "route": row.get("route") or "route not recorded",
            "route_kind": kinds[slug],
            "outcome": "retrieved" if row.get("retrieved") else "not_retrieved",
            "file": file,
            "bytes": size if file else None,
            "sha256": digest if file else None,
            "checksum_source": checksum_source if file else None,
            "bytes_source": bytes_source if file else None,
            "note": row.get("note"),
            "remaining_options": row.get("remaining_options"),
            "logged_retroactively": row.get("logged_retroactively"),
            "log_row": {"slug": slug},
            "superseded_by_correction": None,
        }
    )
    return events


def _proposal_source(proposal: dict | None) -> str | None:
    if not proposal:
        return None
    detail = {
        "include_candidate": "include_candidates_detail",
        "exclude_candidate": "exclude_candidates_detail",
        "not_screened": "not_screened_detail",
    }[proposal["decision"]]
    return f"screening-decisions.json#{detail}[{proposal['priority_index']}]"


def build(
    mapping: dict,
    log: dict,
    screening: dict,
    strata: dict,
    pool_summary: dict,
    *,
    root: Path = ROOT,
) -> dict:
    diagnostics: list[dict] = []
    rows = {r["slug"]: r for r in log["records"]}
    claimed: dict[str, str] = {}
    for entry in mapping["reports"]:
        for slug in entry["log_slugs"]:
            if slug in claimed:
                raise ValueError(f"log slug {slug} mapped to two reports")
            claimed[slug] = entry["report_id"]
    unmapped = sorted(set(rows) - set(claimed))
    missing = sorted(set(claimed) - set(rows))
    if unmapped or missing:
        raise ValueError(
            f"unmapped log slugs {unmapped}; mapped slugs missing from the log {missing}"
        )
    proposals = {
        r["pool_id"]: r
        for r in screening["include_candidates_detail"]
        + screening["exclude_candidates_detail"]
        + screening.get("not_screened_detail", [])
    }
    human_made = screening.get("human_decisions_made", 0)

    reports = []
    for entry in mapping["reports"]:
        events: list[dict] = []
        for slug in entry["log_slugs"]:
            events.extend(_log_event(slug, rows[slug], mapping, diagnostics))
        events.extend(json.loads(json.dumps(entry["events"])))
        events.sort(key=lambda e: (e["date"], e.get("time") or "99:99"))
        for seq, event in enumerate(events, start=1):
            event["seq"] = seq
        pool = entry["pool"]
        proposal = proposals.get(pool["pool_record_id"]) if pool["in_pool"] else None
        if pool["in_pool"] and pool["pool_record_id_status"] == "doi_from_reference_list":
            diagnostics.append(
                {
                    "level": "warning",
                    "subject": entry["report_id"],
                    "message": (
                        f"pool id {pool['pool_record_id']} is a DOI from the record's "
                        "reference list, not the report's own"
                    ),
                }
            )
        if entry["route"]["kind"] == "not_recorded":
            diagnostics.append(
                {
                    "level": "warning",
                    "subject": entry["report_id"],
                    "message": "how the report entered the review was not recorded",
                }
            )
        report = {
            "report_id": entry["report_id"],
            "id_basis": entry["id_basis"],
            "kind": entry["kind"],
            "title": entry["title"],
            "citation_short": entry["citation_short"],
            "catalog_source": entry["catalog_source"],
            "study_family": entry["study_family"],
            "identifiers": entry["identifiers"],
            "identifier_sources": entry["identifier_sources"],
            "pool": pool,
            "route": entry["route"],
            "known_before_search": entry["known_before_search"],
            "screening": {
                "ai_proposal": (
                    proposal["decision"]
                    if proposal
                    else ("not_screened" if pool["in_pool"] else "not_applicable")
                ),
                "ai_layer": proposal.get("layer") if proposal else None,
                "ai_proposal_source": _proposal_source(proposal),
                "human_decision": None,
                "human_decision_record": None,
                "human_decision_status": "none_recorded" if human_made == 0 else "see record",
            },
            "retrieval_events": events,
            "reading": entry["reading"],
            "inclusion": entry["inclusion"],
            "notes": entry["notes"],
        }
        ledger.finish(report)
        reports.append(report)

    for message in mapping.get("flow_v1_errors", []):
        diagnostics.append({"level": "info", "subject": "flow.json (flow-v1)", "message": message})
    if mapping.get("audit_sample_drift"):
        diagnostics.append(
            {
                "level": "warning",
                "subject": "screen-audit-sample.json",
                "message": mapping["audit_sample_drift"],
            }
        )

    out = {
        "version": ledger.VERSION,
        "ledger_date": mapping["ledger_date"],
        "id_rule": ledger.ID_RULE,
        "file_base": "local/gen2-review-2026-09-13/fulltext/",
        "principle": (
            "A report is sought, retrieved or not retrieved; an attempt is an event on a report. "
            "The latest successful event decides the status; a failed attempt after a success does "
            "not revert it; a success is withdrawn only by a dated correction. Human verification "
            "and human screening decisions appear only with a named human record."
        ),
        "families": mapping["families"],
        "reports": reports,
        "diagnostics": diagnostics,
        "derived_from": {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in INPUTS
        },
        "corrections": [],
    }
    ledger.recount(out)
    ledger.validate(out)
    return out


def check_local(out: dict) -> list[str]:
    """Compare the ledger with the local exports and files; report every disagreement."""
    local = ROOT.parents[2] / "local" / "gen2-review-2026-09-13"
    findings: list[str] = []
    pool_path = local / "exports" / "pool.json"
    if pool_path.exists():
        pool = json.loads(pool_path.read_text(encoding="utf-8"))
        records = pool if isinstance(pool, list) else pool.get("records") or list(pool.values())[-1]
        by_id = {r["id"]: r for r in records}
        by_pmid = {str(r.get("pmid")): r for r in records if r.get("pmid")}
        for report in out["reports"]:
            declared = report["pool"]
            pmid = report["identifiers"].get("pmid")
            actual = (
                by_id.get(declared["pool_record_id"])
                if declared["pool_record_id"]
                else (by_pmid.get(str(pmid)) if pmid else None)
            )
            if declared["in_pool"] and actual is None:
                findings.append(f"{report['report_id']}: declared in the pool, not found")
            if not declared["in_pool"] and pmid and str(pmid) in by_pmid:
                findings.append(f"{report['report_id']}: declared outside the pool, found by PMID")
    else:
        findings.append("local pool export absent; pool declarations not checked")
    fulltext = local / "fulltext"
    for report in out["reports"]:
        for event in report["retrieval_events"]:
            if event.get("file"):
                path = fulltext / event["file"]
                if not path.exists():
                    findings.append(f"{report['report_id']}: {event['file']} absent locally")
                    continue
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != event["sha256"]:
                    findings.append(f"{report['report_id']}: {event['file']} digest differs")
                if len(data) != event["bytes"]:
                    findings.append(f"{report['report_id']}: {event['file']} size differs")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check-local", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "reports.json")
    args = parser.parse_args(argv)
    out = build(*(read(name) for name in INPUTS))
    ledger.dump(args.output, out)
    for d in out["diagnostics"]:
        print(f"{d['level']:8} {d['subject']}: {d['message']}")
    if args.check_local:
        for line in check_local(out):
            print("local   ", line)
    c = out["counts"]
    print(
        f"reports {c['reports']}; catalog sought {c['catalog_reports']['sought']} retrieved "
        f"{c['catalog_reports']['retrieved']} not retrieved "
        f"{c['catalog_reports']['not_retrieved']}; "
        f"attempts {c['attempts']['total']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
