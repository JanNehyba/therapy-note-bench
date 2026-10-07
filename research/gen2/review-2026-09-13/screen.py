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

# The second round, 2026-10-07: the records the Scopus searches added. Its file
# carries a decision and a reason per record, which the first round's does not,
# and it names the layer per record rather than per list.
ROUND2 = json.loads(
    (ROOT / "include-candidates-2026-10-07.json").read_text(encoding="utf-8")
)
ROUND2_INCLUDE = {r["title"]: r for r in ROUND2["include_candidates_detail"]}
ROUND2_EXCLUDE = {r["title"]: r for r in ROUND2["exclude_candidates_detail"]}


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
#: The same judgement over the stratum the Scopus searches added, sampled
#: separately because the rate below is a property of the frame it was drawn
#: from. Read from title and the first 360 characters of abstract on
#: 2026-10-07. The 2026-09-13 judgement above was made from its own listing, so
#: the two rates are not strictly comparable and the difference between them is
#: reported with that caveat and not as a measured ratio.
AUDIT_ELIGIBLE_BORDERLINE = [
    "On Improving Summarization Factual Consistency from Natural Language Feedback",
    "FIZZ: Factual Inconsistency Detection by Zoom-in Summary and Zoom-out Document",
    "Contrastive Decoding Mitigates Score Range Bias in LLM-as-a-Judge",
    "The frequency and quality of delirium documentation in discharge summaries",
    "Implementation of an AI-Assisted Workflow for Rehabilitation Discharge Summary Creation",
]


AUDIT_SCOPUS_ELIGIBLE_CLEAR = [
    "EHRCon: Dataset for Checking Consistency between Unstructured Notes and Structured Tables in Electronic Health Records",
    "Toward Relieving Clinician Burden by Automatically Generating Progress Notes using Interim Hospital Data",
    "Electronic Record Keeping and Psychotherapy Alliance: The Role of Concurrent Collaborative Documentation",
    "MTS-Dialog-Bangla: A Dataset and Benchmark for Bangla Clinical Dialogue-to-Note Summarization",
    "Do Clinicians Know How to Prompt? The Need for Automatic Prompt Optimization Help in Clinical Note Generation",
    "Note Keeping in the Digital Age: Making Good Use of Electronic Records Systems",
    "An interactive system for generating hospital progress notes",
    "Large Language Models for Clinical Note Simplification: A Systematic Review and Experimental Evaluation of Medical Text Readability",
    "Social circumstances reports--a critical evaluation.",
    "A Study on Automatic Generation of Chinese Discharge Summary",
    "Hallucinations and Key Information Extraction in Medical Texts: A Comprehensive Assessment of Open-Source Large Language Models",
    "Implementation and Impact of Psychiatric Electronic Medical Records in a Public Medical Center",
    "Recommendations for integrated progress notes",
    "Enhancing Clinical Note Generation from Doctor-Patient Conversations through Semantic Partition-Oriented Summarization",
    "Exploring the Potential of Ambient AI for Inpatient Documentation: A Qualitative Study with Junior Doctors",
    "Experiments in Automated Generation of Discharge Summaries in Italian",
    "Clinical documentation following aggressive incidents in mental health inpatient settings may perpetuate stigma against patients",
    "Fine-Tuning Large Language Models for Automated Subjective, Objective, Assessment, and Plan Note Generation in Medical Contexts",
    "A randomized trial of standardized nursing patient assessment using wireless devices.",
    "The third voice: Writing case-notes",
    "HuskyScribe at MEDIQA-Sum 2023: Summarizing Clinical Dialogues with Transformers",
    "Adaptive Reinforcement Learning for Quality Assurance in Clinical Assessment: A Multi-agent Framework",
    "Artificial intelligence medical scribes in allied health: a solution in search of evidence?",
    "Use of a psychiatric proforma for accident and emergency officers",
    "An evaluation of the quality of the medical information passing between primary care and specialist levels; [Evaluación de la calidad de la información médica entre los niveles de atención primaria y especializada.]",
    "Beyond ASR: Achieving Privacy-Aligned Low Diarization Error Rates in Psychiatric Transcripts Using Large Language Models",
    "NewAgeHealthWarriors at MEDIQA-Chat 2023 Task A: Summarizing Short Medical Conversation with Transformers",
    "Factual consistency evaluation of summarization in the Era of large language models",
]

AUDIT_SCOPUS_ELIGIBLE_BORDERLINE = [
    "A Comparative Analysis of Ai-Based Solutions for Clinical Documentation",
    "Artificial intelligence scribe: A new era in medical documentation",
    "Ai-Augmented Clinical Handoff Systems: Integrating Large Language Models With Electronic Health Records For Safer Care Transitions",
    "Collaboration of Large and Small Language Models with Iterative Reflection Framework for Clinical Note Summarization; [大型和小型语言模型协同迭代反射框架在临床病历摘要中的应用]",
    "Large language models (LLMs) for healthcare: A practical guide to their process and evaluation",
    "Technology-Enabled Diagnosis and Documentation in Psychiatry: Prospects, Challenges, and Future Directions",
    "MaLei at MultiClinSUM: Summarisation of Clinical Documents using Perspective-Aware Iterative Self-Prompting with LLMs",
    "Automated Brief Hospital Course Summarization in Cardiac Surgery Using a Lightweight Large Language Model-Based Framework: Development and Evaluation Study on the Medical Information Mart for Intensive Care-IV",
    "Development and implementation of an evidence-based biofield therapy standardized documentation tool",
    "Workload, Motivation, and Nursing Compliance with Electronic Documentation: A CrossSectional Study in Indonesia; [Carga de Trabajo, Motivación y Cumplimiento de Documentación Electrónica de Enfermería: Estudio Transversal en Indonesia]",
    "Large language models for the mental health community: framework for translating code to care",
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
    parent_remainder_n = strata["remainder_parent"]
    scopus_remainder_n = strata["remainder_reached_only_through_scopus"]
    audit_n = strata["audit_sample_size"]
    audit_scopus_n = strata["audit_sample_scopus_size"]
    by_pool_id = {r["id"]: r for r in priority}

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

    for title, row in sorted(ROUND2_INCLUDE.items()):
        if title not in by_title:
            raise SystemExit(
                f"a 2026-10-07 include names a record not in the priority stratum: {title!r}"
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
                "eid": r.get("eid"),
                "title": r["title"],
                "venue": (r.get("venue") or "").split('"')[0].strip(", "),
                "year": r.get("year"),
                "layer": row["layer"],
                "confidence": row["confidence"],
                "decision": "include_candidate",
                "why": row["why"],
                "round": "2026-10-07",
                "decided_by": "AI proposal; no human eligibility decision has been made",
            }
        )

    excluded_priority = []
    not_screened = []
    for i, r in enumerate(priority):
        if i in seen:
            continue
        if r["title"] in ROUND2_EXCLUDE:
            row = ROUND2_EXCLUDE[r["title"]]
            code = row["reason_code"]
            excluded_priority.append(
                {
                    "priority_index": i,
                    "pool_id": r["id"],
                    "title": r["title"],
                    "decision": "exclude_candidate",
                    "reason_code": code,
                    "reason": ROUND2["exclusion_reasons"][code],
                    "round": "2026-10-07",
                    "decided_by": "AI proposal; no human eligibility decision has been made",
                }
            )
        elif r["title"] in previously_excluded:
            excluded_priority.append(
                {
                    "priority_index": i,
                    "pool_id": r["id"],
                    "title": r["title"],
                    "decision": "exclude_candidate",
                    "reason": "no identifiable documentation-quality construct, operational criterion or measurement method for this review",
                    "round": "2026-09-13",
                    "decided_by": "AI proposal; no human eligibility decision has been made",
                }
            )
        else:
            # Why a record is unscreened depends on what put it in the stratum,
            # so it is derived rather than asserted. A record Scopus alone
            # reached cannot have been missed by a screen that ran before the
            # Scopus searches existed.
            reason = (
                "entered the pool with the Scopus searches of 2026-10-07 and was not reached by "
                "that round's screen"
                if r["source_dbs"] == ["Scopus"]
                else "entered the priority stratum after the pool correction of 2026-09-15; no "
                "AI proposal and no human decision exist for it"
            )
            not_screened.append(
                {
                    "priority_index": i,
                    "pool_id": r["id"],
                    "title": r["title"],
                    "decision": "not_screened",
                    "reason": reason,
                    "decided_by": "nobody yet",
                }
            )

    k_clear = len(AUDIT_ELIGIBLE_CLEAR)
    k_any = k_clear + len(AUDIT_ELIGIBLE_BORDERLINE)
    lo_c, hi_c = wilson(k_clear, audit_n)
    lo_a, hi_a = wilson(k_any, audit_n)
    s_clear = len(AUDIT_SCOPUS_ELIGIBLE_CLEAR)
    s_any = s_clear + len(AUDIT_SCOPUS_ELIGIBLE_BORDERLINE)
    s_lo_c, s_hi_c = wilson(s_clear, audit_scopus_n)
    s_lo_a, s_hi_a = wilson(s_any, audit_scopus_n)

    payload = {
        "version": "screening-v1",
        "status": "AI-assisted screening proposals awaiting human decision",
        "human_decisions_made": 0,
        "deviation_declared": (
            "JBI guidance asks for a minimum of two reviewers at selection. This round "
            "has one investigator and an AI assistant, and the AI proposals below are "
            "not a completed screen."
        ),
        "rounds": [
            {
                "round": "2026-09-13",
                "frame": "the priority stratum of the PubMed and ACL searches",
                "source": "include-candidates.json",
            },
            {
                "round": "2026-10-07",
                "frame": "the 180 priority records the Scopus searches of amendment AM-7 added",
                "source": "include-candidates-2026-10-07.json",
                "include": ROUND2["counts"]["include_candidates"],
                "exclude": ROUND2["counts"]["exclude_candidates"],
            },
        ],
        "priority_stratum": len(priority),
        "priority_stratum_screened": len(included) + len(excluded_priority),
        "include_candidates": len(included),
        "include_candidates_by_round": {
            "2026-09-13": sum(1 for r in included if r.get("round") != "2026-10-07"),
            "2026-10-07": sum(1 for r in included if r.get("round") == "2026-10-07"),
        },
        "exclude_candidates": len(excluded_priority),
        "not_screened": len(not_screened),
        "remainder_unscreened": remainder_n,
        "audit_of_unscreened_remainder": {
            "frame": "the remainder reachable without Scopus",
            "frame_size": parent_remainder_n,
            "sampled": audit_n,
            "sampling": "simple random sample, seed 20260913",
            "clearly_eligible_found": k_clear,
            "borderline_eligible_found": len(AUDIT_ELIGIBLE_BORDERLINE),
            "clearly_eligible_titles": AUDIT_ELIGIBLE_CLEAR,
            "borderline_titles": AUDIT_ELIGIBLE_BORDERLINE,
            "clear_rate": round(k_clear / audit_n, 4),
            "clear_rate_ci95_wilson": [round(lo_c, 4), round(hi_c, 4)],
            "estimated_eligible_records_below_threshold": round(
                parent_remainder_n * k_clear / audit_n
            ),
            "estimated_ci95": [
                round(parent_remainder_n * lo_c),
                round(parent_remainder_n * hi_c),
            ],
            "estimated_including_borderline": round(parent_remainder_n * k_any / audit_n),
            "estimated_including_borderline_ci95": [
                round(parent_remainder_n * lo_a),
                round(parent_remainder_n * hi_a),
            ],
            "applies_to": (
                "this frame only. Until 2026-10-07 the frame was the whole remainder; the "
                "Scopus records now have their own stratum and their own estimate, because "
                "applying this rate to them would extrapolate to a population nobody sampled."
            ),
            "interpretation": (
                "The priority ordering is not a complete screen. An estimated share of "
                "eligible records sits below the threshold and was never screened. Most "
                "of them are transfer-layer NLP method papers, a large and well-populated "
                "literature; two of the six clear finds were direct or requirements "
                "evidence, so the gap is not confined to the transfer layer."
            ),
        },
        "audit_of_unscreened_scopus_remainder": {
            "frame": "the remainder reached only through the Scopus searches of 2026-10-07",
            "frame_size": scopus_remainder_n,
            "sampled": audit_scopus_n,
            "sampling": "simple random sample, seed 20261007",
            "read_from": "title and the first 360 characters of the abstract",
            "clearly_eligible_found": s_clear,
            "borderline_eligible_found": len(AUDIT_SCOPUS_ELIGIBLE_BORDERLINE),
            "clearly_eligible_titles": AUDIT_SCOPUS_ELIGIBLE_CLEAR,
            "borderline_titles": AUDIT_SCOPUS_ELIGIBLE_BORDERLINE,
            "clear_rate": round(s_clear / audit_scopus_n, 4),
            "clear_rate_ci95_wilson": [round(s_lo_c, 4), round(s_hi_c, 4)],
            "estimated_eligible_records_below_threshold": round(
                scopus_remainder_n * s_clear / audit_scopus_n
            ),
            "estimated_ci95": [
                round(scopus_remainder_n * s_lo_c),
                round(scopus_remainder_n * s_hi_c),
            ],
            "estimated_including_borderline": round(scopus_remainder_n * s_any / audit_scopus_n),
            "estimated_including_borderline_ci95": [
                round(scopus_remainder_n * s_lo_a),
                round(scopus_remainder_n * s_hi_a),
            ],
            "interpretation": (
                "The clear rate in this stratum is several times the rate measured in the "
                "parent remainder in September. The likely reason is that the Scopus queries "
                "name this review's subject matter directly and Scopus matches them against "
                "indexed keywords as well as title and abstract, so a record can be squarely "
                "on topic and still score below a threshold built from title and abstract "
                "words. The ordering rule and its threshold were left unchanged, because they "
                "were registered before the first screen; what changes is the size of the "
                "declared gap."
            ),
            "not_a_measured_ratio": (
                "The two strata were judged by the same assistant on different days from "
                "differently formatted listings, so the difference between the two rates is "
                "not a measurement of anything. Comparing them properly would mean judging "
                "the parent frame again under this round's procedure, which has not been done."
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
        f"{round(parent_remainder_n * k_clear / audit_n)} "
        f"[{round(parent_remainder_n * lo_c)}, {round(parent_remainder_n * hi_c)}] "
        f"of {parent_remainder_n} below threshold"
    )
    print(
        f"       incl. borderline {k_any}/{audit_n} -> est. "
        f"{round(parent_remainder_n * k_any / audit_n)} "
        f"[{round(parent_remainder_n * lo_a)}, {round(parent_remainder_n * hi_a)}]"
    )
    print(
        f"scopus audit: {s_clear}/{audit_scopus_n} clearly eligible -> est. "
        f"{round(scopus_remainder_n * s_clear / audit_scopus_n)} "
        f"[{round(scopus_remainder_n * s_lo_c)}, {round(scopus_remainder_n * s_hi_c)}] "
        f"of {scopus_remainder_n} below threshold"
    )


if __name__ == "__main__":
    main()
