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
    "search-log-scopus.json",
    "amendments.json",
    "flow-recorded.json",
)
VERSION = "flow-v2"


def read(name: str, root: Path = ROOT) -> dict:
    return json.loads((root / name).read_text(encoding="utf-8"))


def _databases(*logs: dict) -> list[dict]:
    """One entry per database, in the order the logs are passed.

    `records` is what the log's queries identified. For PubMed and the ACL
    corpus that is the number the search reported; for Scopus it is the number
    of rows in the exports, because the interface's hit count was not written
    down. The difference is carried on the entry rather than averaged away,
    and a log that cannot assert complete download says so instead of
    answering the question with a silent True.
    """
    out = []
    for log in logs:
        searches = log["searches"]
        lower_bound = any(s.get("total_records_is_a_lower_bound") for s in searches)
        complete = [s.get("download_complete") for s in searches]
        entry = {
            "name": log["database"],
            "platform": log.get("platform"),
            "queries": len(searches),
            "records": sum(s["total_records"] for s in searches),
            "records_is_a_lower_bound": lower_bound,
            "downloaded_completely": (
                "unverified"
                if any(c is None for c in complete)
                else all(s.get("records_downloaded") == s["total_records"] for s in searches)
            ),
            "source": "search-log total_records per query",
            "search_date": log.get("search_date"),
        }
        if lower_bound:
            entry["records_basis"] = searches[0]["total_records_basis"]
        out.append(entry)
    return out


def build(
    reports: dict,
    pool_summary: dict,
    screening: dict,
    strata: dict,
    pubmed: dict,
    acl: dict,
    scopus: dict,
    amendments: dict,
    recorded: dict,
    *,
    root: Path = ROOT,
) -> dict:
    databases = _databases(pubmed, acl, scopus)
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
            "records_from_databases_includes_a_lower_bound": any(
                d["records_is_a_lower_bound"] for d in databases
            ),
            "what_the_lower_bound_means": (
                "The Scopus searches were run by hand and the hit count the interface reported "
                "was not captured, so their contribution to this total is the number of records "
                "exported. The total is therefore at least this, and the shortfall, if any, is "
                "unknown rather than zero."
            ),
            "downloaded_completely": {
                d["name"]: d["downloaded_completely"] for d in databases
            },
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
            "databases_searched_after_the_parent_round": [
                {
                    "name": s["source"],
                    "searched_on": s["searched_on"],
                    "by_route": s["by_route"],
                    "why_it_was_a_gap": s["why_it_was_unavailable"],
                    "amendment": s["amendment"],
                }
                for s in amendments.get("sources_searched_after_the_parent_round", [])
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
                "identifiers; the pool was rebuilt on 2026-09-15 and this note is kept for the "
                "history."
            ),
            "second_known_defect": {
                "what": (
                    "The key order is DOI, then PMID, then normalised title, so the same work "
                    "entered twice whenever one database supplied a DOI and the other did not. "
                    "That is common between PubMed and Scopus."
                ),
                **{
                    k: v
                    for k, v in pool_summary["same_normalised_title_on_several_records"].items()
                    if k in ("groups", "records_involved", "groups_involving_scopus")
                },
                "effect": (
                    "the unique count above is an overcount by at most records_involved minus "
                    "groups; one work sits in the priority stratum twice and was screened in "
                    "twice, once in each round"
                ),
                "status": "measured on 2026-10-07, not yet corrected",
            },
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
            "rounds": screening["rounds"],
            "ai_proposals_by_round": screening["include_candidates_by_round"],
            "audit_of_unscreened": {
                **screening["audit_of_unscreened_remainder"],
                "basis": (
                    "recorded in screening-decisions.json; the sample on disk was regenerated "
                    "after the parser fix (see reports.json diagnostics) and again when the "
                    "Scopus records moved to their own stratum"
                ),
            },
            "audit_of_unscreened_scopus_remainder": {
                **screening["audit_of_unscreened_scopus_remainder"],
                "basis": "recorded in screening-decisions.json; drawn and judged on 2026-10-07",
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
            # Retrieval is not reading and reading is not verification. The field
            # that used to stand here was named `sources_full_text_verified` and
            # counted reports whose status is `retrieved`, which is all three at
            # once: forty-three were retrieved, thirty-eight were read in full
            # text, and reports.json records that nobody verified any of them.
            "sources_retrieved": sum(1 for r in catalog if r["current_status"] == "retrieved"),
            "sources_read_in_full_text": sum(
                1 for r in catalog if (r.get("reading") or {}).get("basis") == "full_text"
            ),
            "sources_read_from_the_abstract": sum(
                1 for r in catalog if (r.get("reading") or {}).get("basis") == "abstract"
            ),
            "sources_verified_by_a_human": reports["counts"]["human_verified"],
            "what_retrieval_is_not": (
                "A retrieved report is a file that arrived. Whether it was read, and on "
                "what, is its reading basis; whether a person checked its evidence against "
                "it is human_verified, which is zero. The earlier field conflated the three "
                "and published the first as the third."
            ),
            "basis": (
                "The candidate, family, method, level, blind-spot and pilot-entry counts are "
                + recorded["synthesis"]["basis"]
                + ", so they describe that date and not today: the catalog's current figures "
                "are in research/gen2/state.json, which derives them. The source counts here "
                "are derived from reports.json on every run."
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
        f"flow {flow['version']}: at least "
        f"{flow['identification']['records_from_databases']} records from "
        f"{len(flow['identification']['databases'])} databases; catalog reports sought "
        f"{ft['sought']}, "
        f"retrieved {ft['retrieved']}, not retrieved {ft['not_retrieved']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
