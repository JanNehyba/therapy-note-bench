"""Rank the record pool for AI-assisted title/abstract screening.

This is a documented, deterministic ordering, not a screening decision. Records
below the priority threshold are not excluded: they are moved to a stratum that
is audited by random sampling, so the miss rate of the ordering can be estimated
and reported instead of assumed to be zero.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPORTS = Path("C:/Users/Nehyba/therapy-note-bench/local/gen2-review-2026-09-13/exports")
POOL = EXPORTS / "pool.json"

# Weighted signals, each tied to a review question. Weights are a stated
# convention for ordering only; they carry no claim about study importance.
SIGNALS: list[tuple[str, str, int]] = [
    # Q1/Q3 - an explicit named instrument or rating scale for note quality
    (
        r"\b(PDQI|PDSQI|QNOTE|SOAP note|rubric|psychometric|content validity|inter-?rater)\b",
        "instrument",
        5,
    ),
    (
        r"\b(note quality|documentation quality|quality of (clinical )?(notes?|documentation))\b",
        "note-quality",
        5,
    ),
    # Q1 - psychotherapy / mental-health documentation specifically (direct layer)
    (
        r"\b(psychotherap\w*|counsel\w*|therapy session|behavioral health|mental health)\b.{0,80}\b(note|documentation|record|summar)",
        "direct-mh",
        4,
    ),
    (
        r"\b(progress note|session note|therapy note|session summar|case note)\w*\b",
        "direct-note",
        4,
    ),
    # Q4 - model-generated documentation and its evaluation
    (
        r"\b(large language model|LLM|generative AI|ambient (AI|documentation|scribe)|AI scribe)\b",
        "llm",
        3,
    ),
    (
        r"\b(hallucinat\w*|factual\w*|faithful\w*|omission|fabricat\w*|error taxonom\w*)\b",
        "fidelity",
        3,
    ),
    # Q3 - measurement methods transferable to automated evaluation
    (
        r"\b(question answering|QA-based|atomic fact|claim verification|attribution|entailment)\b",
        "method",
        3,
    ),
    # Q2 - recipients and purposes
    (r"\b(open ?notes|patient access|client access|patients? read\w*|shared notes)\b", "client", 4),
    (r"\b(supervis\w*)\b", "supervision", 3),
    (
        r"\b(record.?keeping|documentation (standard|guideline|requirement)|audit|compliance|accreditation)\b",
        "audit",
        3,
    ),
    (
        r"\b(privacy|confidential\w*|sensitive information|de-?identif\w*|stigmat\w*)\b",
        "privacy",
        2,
    ),
    # Q4 - language transfer
    (r"\b(Czech|multilingual|cross-?lingual|translation)\b", "language", 2),
    # study-type signals that raise the value of a record for this review
    (
        r"\b(validat\w*|reliabilit\w*|agreement|Delphi|consensus|development and validation)\b",
        "validation",
        2,
    ),
    (
        r"\b(interview\w*|focus group|survey|qualitative|user need|information need)\b",
        "user-need",
        2,
    ),
]

# Signals that a record is probably off-topic for this review even when it
# scores. They subtract; they never exclude on their own.
NEGATIVE: list[tuple[str, int]] = [
    (r"\b(chatbot|conversational agent)\b.{0,60}\b(therap|treatment|intervention)\b", -3),
    (r"\b(randomi[sz]ed controlled trial|efficacy of (therapy|treatment)|symptom reduction)\b", -2),
    (r"\b(radiolog\w*|patholog\w* report|surgical|anesthes\w*|dental)\b", -2),
]


def score(rec: dict) -> tuple[int, list[str]]:
    hay = f"{rec.get('title', '')} {rec.get('abstract', '')}"
    total, tags = 0, []
    for pat, tag, w in SIGNALS:
        if re.search(pat, hay, re.I):
            total += w
            tags.append(tag)
    for pat, w in NEGATIVE:
        if re.search(pat, hay, re.I):
            total += w
            tags.append("neg")
    return total, tags


def main() -> None:
    records = json.loads(POOL.read_text(encoding="utf-8"))
    for r in records:
        r["priority_score"], r["signals"] = score(r)
    records.sort(key=lambda r: (-r["priority_score"], r.get("year") or ""))

    threshold = 9
    priority = [r for r in records if r["priority_score"] >= threshold]
    remainder = [r for r in records if r["priority_score"] < threshold]

    # Two remainders, audited separately. A record "reached only through
    # Scopus" has no PubMed or ACL query behind it, so it was unreachable
    # before 2026-10-07 and the audit of 2026-09-13 says nothing about it.
    parent_remainder = [r for r in remainder if r["source_dbs"] != ["Scopus"]]
    scopus_remainder = [r for r in remainder if r["source_dbs"] == ["Scopus"]]

    rng = random.Random(20260913)
    audit = rng.sample(parent_remainder, min(200, len(parent_remainder)))
    rng_scopus = random.Random(20261007)
    audit_scopus = rng_scopus.sample(scopus_remainder, min(200, len(scopus_remainder)))

    (EXPORTS / "screen-priority.json").write_bytes((json.dumps(priority, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    (EXPORTS / "screen-audit-sample.json").write_bytes((json.dumps(audit, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    (EXPORTS / "screen-audit-sample-scopus.json").write_bytes((json.dumps(audit_scopus, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))

    dist: dict[int, int] = {}
    for r in records:
        dist[r["priority_score"]] = dist.get(r["priority_score"], 0) + 1

    summary = {
        "pool_size": len(records),
        "ordering_rule": "weighted keyword signals over title+abstract; a stated convention for ordering only",
        "signals": [{"tag": t, "weight": w, "pattern": p} for p, t, w in SIGNALS],
        "negative_signals": [{"weight": w, "pattern": p} for p, w in NEGATIVE],
        "priority_threshold": threshold,
        "priority_threshold_basis": (
            "registered before the screen of 2026-09-13 and unchanged since. The Scopus "
            "records of 2026-10-07 were ranked by the same rule at the same cut; choosing a "
            "cut with the new records in view would be choosing it after seeing the data."
        ),
        "priority_stratum": len(priority),
        "priority_stratum_reached_only_through_scopus": sum(
            1 for r in priority if r["source_dbs"] == ["Scopus"]
        ),
        "remainder_stratum": len(remainder),
        "remainder_parent": len(parent_remainder),
        "remainder_reached_only_through_scopus": len(scopus_remainder),
        "why_the_remainder_is_split": (
            "the audit of 2026-09-13 sampled the PubMed and ACL remainder, so its eligibility "
            "rate is a property of that remainder. The records Scopus alone brought in were "
            "unreachable then and are sampled separately rather than covered by an "
            "extrapolation nobody measured."
        ),
        "audit_sample_size": len(audit),
        "audit_sample_seed": 20260913,
        "audit_sample_frame": "the remainder reachable without Scopus",
        "audit_sample_note": (
            "The 200-record sample judged on 2026-09-13 was drawn before the parser fix of "
            "that evening; the file on disk is a later draw with the same seed over a changed "
            "remainder and does not reproduce the judged sample. The judgement itself is "
            "recorded in screening-decisions.json. The frame shrank again on 2026-10-07, when "
            "the Scopus records moved to their own stratum, so the drift is larger, not "
            "smaller, than it was."
        ),
        "audit_sample_scopus_size": len(audit_scopus),
        "audit_sample_scopus_seed": 20261007,
        "audit_sample_scopus_frame": "the remainder reached only through Scopus",
        "audit_sample_scopus_note": (
            "Drawn on 2026-10-07 from the stratum the Scopus searches added. This draw does "
            "reproduce: the frame is fixed by the three export checksums in "
            "search-log-scopus.json and the seed is recorded here."
        ),
        "audit_purpose": (
            "Estimate how many eligible records the ordering pushed below the threshold. "
            "The remainder is not excluded; it is unscreened and reported as such."
        ),
        "score_distribution": dict(sorted(dist.items(), reverse=True)),
        "priority_sha256": hashlib.sha256(
            (EXPORTS / "screen-priority.json").read_bytes()
        ).hexdigest(),
        "audit_sha256": hashlib.sha256(
            (EXPORTS / "screen-audit-sample.json").read_bytes()
        ).hexdigest(),
        "audit_scopus_sha256": hashlib.sha256(
            (EXPORTS / "screen-audit-sample-scopus.json").read_bytes()
        ).hexdigest(),
    }
    (ROOT / "screening-strata.json").write_bytes((json.dumps(summary, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(
        f"pool={len(records)} priority={len(priority)} remainder={len(remainder)} "
        f"audit={len(audit)}"
    )
    print(
        f"  scopus-only: priority={summary['priority_stratum_reached_only_through_scopus']} "
        f"remainder={len(scopus_remainder)} audit={len(audit_scopus)}"
    )
    print("score distribution (top):", dict(list(sorted(dist.items(), reverse=True))[:18]))


if __name__ == "__main__":
    main()
