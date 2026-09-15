"""Record the AI title/abstract screening decisions and the audit miss estimate.

Every decision here is an AI proposal. None of it is a human eligibility
decision, and the file says so on every record. The audit block estimates how
many eligible records the priority ordering left unscreened, with an interval,
instead of treating the unscreened remainder as if it were empty.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPORTS = Path("C:/Users/Nehyba/therapy-note-bench/local/gen2-review-2026-09-13/exports")

# Screening proposals, keyed by record title.
#
# These were first recorded as positions in the priority ordering. A bib-parser
# fix on 2026-09-13 merged 7 duplicate records; the set of 487 priority records
# stayed identical but 29 positions moved within it. A position is therefore not
# a stable identifier for a decision, and titles are used instead.
INCLUDE = json.loads((ROOT / "include-candidates.json").read_text(encoding="utf-8"))
LAYERS: dict[str, list[str]] = INCLUDE["layers"]


# Audit sample judgements. Titles of records the AI screen judges eligible
# despite falling below the priority threshold.
AUDIT_ELIGIBLE_CLEAR = [
    '"I think it\'s something that we should lean in to": The use of OpenNotes in Canadian psychiatric care contexts',
    "Clinical supervision of psychotherapy: essential ethics issues for supervisors and supervisees",
    "SummaC: Re-Visiting NLI-based Models for Inconsistency Detection in Summarization",
    "DecompEval: Evaluating Generated Texts as Unsupervised Decomposed Question Answering",
    "Analyzing and Evaluating Faithfulness in Dialogue Summarization",
    "An evaluation of existing text de-identification tools for use with patient progress notes",
]
AUDIT_ELIGIBLE_BORDERLINE = [
    "On Improving Summarization Factual Consistency from Natural Language Feedback",
    "FIZZ: Factual Inconsistency Detection by Zoom-in Summary and Zoom-out Document",
    "Contrastive Decoding Mitigates Score Range Bias in LLM-as-a-Judge",
    "The frequency and quality of delirium documentation in discharge summaries",
    "Implementation of an AI-Assisted Workflow for Rehabilitation Discharge Summary Creation",
]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def main() -> None:
    priority = json.loads((EXPORTS / "screen-priority.json").read_text(encoding="utf-8"))
    strata = json.loads((ROOT / "screening-strata.json").read_text(encoding="utf-8"))
    remainder_n = strata["remainder_stratum"]
    audit_n = strata["audit_sample_size"]

    by_title = {r["title"]: (i, r) for i, r in enumerate(priority)}
    included: list[dict] = []
    seen: set[int] = set()
    for layer, titles in LAYERS.items():
        for title in titles:
            if title not in by_title:
                raise SystemExit(
                    f"screening decision names a record not in the priority stratum: {title!r}"
                )
            i, r = by_title[title]
            if i in seen:
                continue
            seen.add(i)
            included.append(
                {
                    "priority_index": i,
                    "pool_id": r["id"],
                    "pmid": r.get("pmid"),
                    "doi": r.get("doi"),
                    "acl_key": r.get("acl_key"),
                    "title": r["title"],
                    "venue": (r.get("venue") or "").split('"')[0].strip(", "),
                    "year": r.get("year"),
                    "layer": layer,
                    "decision": "include_candidate",
                    "decided_by": "AI proposal; no human eligibility decision has been made",
                }
            )

    # A record that entered the priority stratum after the AI screen of
    # 2026-09-13 (the pool correction of 2026-09-15 unmerged records) has no
    # proposal and no decision; it is listed as not screened, never as excluded.
    previous_path = ROOT / "screening-decisions.json"
    previous = (
        json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else {}
    )
    previously_excluded = {r["title"] for r in previous.get("exclude_candidates_detail", [])}
    excluded_priority = [
        {
            "priority_index": i,
            "pool_id": r["id"],
            "title": r["title"],
            "decision": "exclude_candidate",
            "reason": "no identifiable documentation-quality construct, operational criterion or measurement method for this review",
            "decided_by": "AI proposal; no human eligibility decision has been made",
        }
        for i, r in enumerate(priority)
        if i not in seen and r["title"] in previously_excluded
    ]
    not_screened = [
        {
            "priority_index": i,
            "pool_id": r["id"],
            "title": r["title"],
            "decision": "not_screened",
            "reason": "entered the priority stratum after the pool correction of 2026-09-15; no AI proposal and no human decision exist for it",
            "decided_by": "nobody yet",
        }
        for i, r in enumerate(priority)
        if i not in seen and r["title"] not in previously_excluded
    ]

    k_clear = len(AUDIT_ELIGIBLE_CLEAR)
    k_any = k_clear + len(AUDIT_ELIGIBLE_BORDERLINE)
    lo_c, hi_c = wilson(k_clear, audit_n)
    lo_a, hi_a = wilson(k_any, audit_n)

    payload = {
        "version": "screening-v1",
        "status": "AI-assisted screening proposals awaiting human decision",
        "human_decisions_made": 0,
        "deviation_declared": (
            "JBI guidance asks for a minimum of two reviewers at selection. This round "
            "has one investigator and an AI assistant, and the AI proposals below are "
            "not a completed screen."
        ),
        "priority_stratum": len(priority),
        "priority_stratum_screened": len(included) + len(excluded_priority),
        "include_candidates": len(included),
        "exclude_candidates": len(excluded_priority),
        "not_screened": len(not_screened),
        "remainder_unscreened": remainder_n,
        "audit_of_unscreened_remainder": {
            "sampled": audit_n,
            "sampling": "simple random sample, seed 20260913",
            "clearly_eligible_found": k_clear,
            "borderline_eligible_found": len(AUDIT_ELIGIBLE_BORDERLINE),
            "clearly_eligible_titles": AUDIT_ELIGIBLE_CLEAR,
            "borderline_titles": AUDIT_ELIGIBLE_BORDERLINE,
            "clear_rate": round(k_clear / audit_n, 4),
            "clear_rate_ci95_wilson": [round(lo_c, 4), round(hi_c, 4)],
            "estimated_eligible_records_below_threshold": round(remainder_n * k_clear / audit_n),
            "estimated_ci95": [round(remainder_n * lo_c), round(remainder_n * hi_c)],
            "estimated_including_borderline": round(remainder_n * k_any / audit_n),
            "estimated_including_borderline_ci95": [
                round(remainder_n * lo_a),
                round(remainder_n * hi_a),
            ],
            "interpretation": (
                "The priority ordering is not a complete screen. An estimated share of "
                "eligible records sits below the threshold and was never screened. Most "
                "of them are transfer-layer NLP method papers, a large and well-populated "
                "literature; two of the six clear finds were direct or requirements "
                "evidence, so the gap is not confined to the transfer layer."
            ),
        },
        "include_candidates_detail": included,
        "exclude_candidates_detail": excluded_priority,
        "not_screened_detail": not_screened,
    }
    (ROOT / "screening-decisions.json").write_bytes((json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(f"include candidates: {len(included)}")
    print(f"exclude candidates (priority stratum): {len(excluded_priority)}")
    print(f"not screened (entered the stratum after the screen): {len(not_screened)}")
    print(f"unscreened remainder: {remainder_n}")
    print(
        f"audit: {k_clear}/{audit_n} clearly eligible -> est. "
        f"{round(remainder_n * k_clear / audit_n)} "
        f"[{round(remainder_n * lo_c)}, {round(remainder_n * hi_c)}] eligible records below threshold"
    )
    print(
        f"       incl. borderline {k_any}/{audit_n} -> est. "
        f"{round(remainder_n * k_any / audit_n)} "
        f"[{round(remainder_n * lo_a)}, {round(remainder_n * hi_a)}]"
    )


if __name__ == "__main__":
    main()
