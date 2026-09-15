"""Generate flow.json, the PRISMA-ScR-style flow of the 2026-09-13 review, from the records.

flow-v1 was maintained by hand and drifted from the records it summarised: it
counted retrieval attempts as reports, listed a report as not retrieved after
its copy had been logged, and showed identification from the databases only.
This generator derives every count it can from the tracked files -- the
search logs, the pool summary, the screening decisions and strata, the
amendments and the report ledger -- and copies the rest from
flow-recorded.json, marked as recorded rather than derived. A test holds
flow.json to this generator's output, so a hand edit fails the suite.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import ledger  # noqa: E402

INPUTS = (
    "reports.json",
    "pool-summary.json",
    "screening-decisions.json",
    "screening-strata.json",
    "search-log-pubmed.json",
    "search-log-acl.json",
    "amendments.json",
    "flow-recorded.json",
)
VERSION = "flow-v2"


def read(name: str, root: Path = ROOT) -> dict:
    return json.loads((root / name).read_text(encoding="utf-8"))


def _databases(pubmed: dict, acl: dict) -> list[dict]:
    out = []
    for log in (pubmed, acl):
        searches = log["searches"]
        out.append(
            {
                "name": log["database"],
                "platform": log.get("platform"),
                "queries": len(searches),
                "records": sum(s["total_records"] for s in searches),
                "downloaded_completely": all(
                    s.get("records_downloaded") == s["total_records"] for s in searches
                ),
                "source": "search-log total_records per query",
            }
        )
    return out


def build(
    reports: dict,
    pool_summary: dict,
    screening: dict,
    strata: dict,
    pubmed: dict,
    acl: dict,
    amendments: dict,
    recorded: dict,
    *,
    root: Path = ROOT,
) -> dict:
    databases = _databases(pubmed, acl)
    from_databases = sum(d["records"] for d in databases)
    other = [r for r in reports["reports"] if r["route"]["kind"] != "search_and_screening"]
    by_route: dict[str, list[dict]] = {}
    for r in other:
        by_route.setdefault(r["route"]["kind"], []).append(
            {
                "report_id": r["report_id"],
                "catalog_source": r["catalog_source"],
                "kind": r["kind"],
                "from": r["route"].get("from"),
            }
        )
    catalog = [
        r for r in reports["reports"] if r["catalog_source"] and "_abs_" not in r["catalog_source"]
    ]
    abstract = [
        r for r in reports["reports"] if r["catalog_source"] and "_abs_" in r["catalog_source"]
    ]
    support = [r for r in reports["reports"] if r["kind"] == "supporting_material"]
    non_catalog = [
        r
        for r in reports["reports"]
        if not r["catalog_source"] and r["kind"] != "supporting_material"
    ]
    events = [e for r in reports["reports"] for e in r["retrieval_events"]]
    proposals = screening["include_candidates_detail"] + screening["exclude_candidates_detail"]
    by_layer: dict[str, int] = {}
    for p in screening["include_candidates_detail"]:
        by_layer[p["layer"]] = by_layer.get(p["layer"], 0) + 1
    use_counts: dict[str, int] = {}
    for r in catalog:
        use = r["inclusion"]["use"] or "none"
        use_counts[use] = use_counts.get(use, 0) + 1
    layer_counts: dict[str, int] = {}
    for r in catalog:
        layer = r["inclusion"]["layer"] or "none"
        layer_counts[layer] = layer_counts.get(layer, 0) + 1

    def detail(group):
        return [
            {
                "report_id": r["report_id"],
                "catalog_source": r["catalog_source"],
                "last_attempt": r["last_attempt_date"],
                "remaining_options": next(
                    (
                        e.get("remaining_options")
                        for e in reversed(r["retrieval_events"])
                        if e.get("remaining_options")
                    ),
                    None,
                ),
            }
            for r in group
            if r["current_status"] == "not_retrieved"
        ]

    flow = {
        "version": VERSION,
        "generated_from": (
            "build_flow.py over the files named in derived_from; hand edits fail the suite"
        ),
        "identification": {
            "databases": databases,
            "records_from_databases": from_databases,
            "downloaded_completely": all(d["downloaded_completely"] for d in databases),
            "not_parsed_into_pool": {
                "count": from_databases - pool_summary["sum_before_dedup"],
                "what": (
                    "PubmedBookArticle records (book chapters); structurally different and "
                    "excluded from the screening pool, quantified rather than silently dropped"
                ),
            },
            "databases_not_searched": [
                {"name": s["source"], "reason": s.get("evidence") or s.get("status")}
                for s in amendments.get("unavailable_sources", [])
            ],
            "other_methods": {
                "principle": (
                    "Records identified through routes other than the database search, as "
                    "PRISMA-ScR reports them: known before the search, professional or "
                    "methodological guidance, citations and author searches from an included "
                    "report, the audit sample of the unscreened remainder, or not recorded."
                ),
                "counts": {kind: len(items) for kind, items in sorted(by_route.items())},
                "reports": {kind: items for kind, items in sorted(by_route.items())},
            },
        },
        "deduplication": {
            "before": pool_summary["sum_before_dedup"],
            "after": pool_summary["unique_records_after_dedup"],
            "removed": pool_summary["duplicates_removed"],
            "rule": pool_summary["dedup_rule"],
            "source": "pool-summary.json",
            "known_defect": (
                "build_pool.py keyed PubMed records by the last DOI in the record, which can "
                "be a cited reference; some merges are therefore wrong and some report ids in "
                "the pool are not the report's own. The ledger keys reports by verified "
                "identifiers; the pool is to be rebuilt in a separate correction."
            ),
        },
        "screening": {
            "pool": strata["pool_size"],
            "priority_threshold": strata["priority_threshold"],
            "priority_stratum": strata["priority_stratum"],
            "priority_stratum_screened": screening["priority_stratum_screened"],
            "priority_stratum_not_screened": screening.get("not_screened", 0),
            "remainder_not_screened": strata["remainder_stratum"],
            "ai_proposals": {
                "include": len(screening["include_candidates_detail"]),
                "exclude": len(screening["exclude_candidates_detail"]),
                "total": len(proposals),
                "include_by_layer": dict(sorted(by_layer.items())),
                "status": screening["status"],
            },
            "human_decisions": {
                "made": screening["human_decisions_made"],
                "source": "screening-decisions.json#human_decisions_made",
            },
            "audit_of_unscreened": {
                **screening["audit_of_unscreened_remainder"],
                "basis": (
                    "recorded in screening-decisions.json; the sample on disk was regenerated "
                    "after the parser fix (see reports.json diagnostics)"
                ),
            },
        },
        "full_text": {
            "unit": "report",
            "catalog_reports": {
                "sought": len(catalog),
                "retrieved": sum(1 for r in catalog if r["current_status"] == "retrieved"),
                "not_retrieved": sum(1 for r in catalog if r["current_status"] == "not_retrieved"),
                "not_retrieved_detail": detail(catalog),
            },
            "other_reports": {
                "total": len(non_catalog),
                "retrieved": sum(1 for r in non_catalog if r["current_status"] == "retrieved"),
                "not_retrieved": sum(
                    1 for r in non_catalog if r["current_status"] == "not_retrieved"
                ),
                "not_retrieved_detail": detail(non_catalog),
            },
            "supporting_materials": {
                "total": len(support),
                "retrieved": sum(1 for r in support if r["current_status"] == "retrieved"),
            },
            "retrieval_attempts": {
                "unit": "attempt",
                **reports["counts"]["attempts"],
                "by_route_kind": {
                    kind: sum(1 for e in events if e["route_kind"] == kind)
                    for kind in sorted({e["route_kind"] for e in events})
                },
            },
            "retrieved_after_failed_attempt": reports["counts"]["retrieved_after_failed_attempt"],
            "reading": {
                "full_text_ai_read": sum(
                    1
                    for r in reports["reports"]
                    if r["reading"]["basis"] == "full_text" and r["reading"]["ai_read"]
                ),
                "abstract_only": len(abstract),
                "human_verified": reports["counts"]["human_verified"],
            },
        },
        "inclusion": {
            "catalog_sources_by_use": dict(sorted(use_counts.items())),
            "catalog_sources_by_layer": dict(sorted(layer_counts.items())),
            "abstract_only_sources": len(abstract),
            "supporting_materials_not_registry_sources": len(support),
            "human_inclusion_decisions": 0,
            "basis": (
                "reports.json inclusion blocks, which record the local catalog; no human "
                "inclusion decision exists"
            ),
        },
        "synthesis": {
            **recorded["synthesis"],
            "sources_full_text_verified": sum(
                1 for r in catalog if r["current_status"] == "retrieved"
            ),
            "sources_abstract_only": len(abstract),
            "basis": (
                "candidates, families, methods, levels, blind spots and pilot entries are "
                "recorded from the local catalog; the source counts are derived from "
                "reports.json"
            ),
        },
        "caveat": recorded["caveat"],
        "corrections": recorded["corrections"],
        "derived_from": {name: ledger.sha256_file(root / name) for name in INPUTS},
    }
    return flow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=ROOT / "flow.json")
    args = parser.parse_args(argv)
    flow = build(*(read(name) for name in INPUTS))
    args.output.write_bytes((json.dumps(flow, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    ft = flow["full_text"]["catalog_reports"]
    print(
        f"flow {flow['version']}: {flow['identification']['records_from_databases']} records from "
        f"{len(flow['identification']['databases'])} databases; catalog reports sought "
        f"{ft['sought']}, "
        f"retrieved {ft['retrieved']}, not retrieved {ft['not_retrieved']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
