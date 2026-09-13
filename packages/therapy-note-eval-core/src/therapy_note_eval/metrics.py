"""Observed findings, planned denominators and client-cluster uncertainty."""

from __future__ import annotations

import math
import random
import statistics
from collections import Counter, defaultdict

from .deterministic import checks, violations
from .schema import Bank, Case, Evaluation, Note, Segmentation, digest, require

VERSION = "aggregation-v3"


def fraction(found: int, expected: int, complete: bool = True) -> float | None:
    return found / expected if complete and expected else None


def measure(
    case: Case, note: Note, bank: Bank, segmentation: Segmentation, evaluation: Evaluation
) -> dict:
    evaluation.check(case, note, bank, segmentation)
    use_qa, use_claims = "qa" in evaluation.methods, "claims" in evaluation.methods
    claims = Counter(c.verdict for c in evaluation.claims)
    claim_complete = (
        evaluation.segmentation_complete is True
        and len(evaluation.claims) == len(segmentation.claims)
        and not claims["unassessable"]
    )
    qa = {q.information_id: q for q in evaluation.qa}
    answers = {a.question_id: a for a in evaluation.answers}
    coverage = {}
    for importance in ("essential", "supplementary"):
        ids = {
            i.id
            for i in bank.information
            if i.relevance[note.spec.profile].importance == importance and use_qa
        }
        valid_ids = {
            q.information_id
            for q in bank.questions
            if q.primary and q.id in answers and answers[q.id].status != "failed"
        }
        counts = Counter(qa[i].verdict for i in ids if i in qa and i in valid_ids)
        complete = sum(counts.values()) == len(ids) and not counts["unassessable"]
        coverage[importance] = {
            "expected": len(ids),
            "answered": sum(counts.values()),
            "missing": len(ids) - sum(counts.values()),
            "eligible": len(ids),
            "assessed": sum(v for k, v in counts.items() if k != "unassessable"),
            "source_unresolved": sum(
                i.id in ids
                and i.epistemic_status in ("uncertain", "conflicting")
                and i.id in qa
                and qa[i.id].verdict == "unassessable"
                for i in bank.information
            ),
            "ambiguous_note_answers": sum(
                q.information_id in ids
                and q.primary
                and q.id in answers
                and answers[q.id].status == "ambiguous"
                for q in bank.questions
            ),
            "outcomes": dict(counts),
            "recall": fraction(counts["preserved"], len(ids), complete),
        }
    dimensions = {d.dimension: d.verdict for d in evaluation.dimensions}
    word_limit_ok = len(note.text.split()) <= note.spec.word_limit
    active_items = {
        m.id: m
        for m in evaluation.measurements
        if note.spec.profile in m.profiles and "items" in evaluation.methods
    }
    for item_id in violations(note, tuple(active_items.values())):
        dimensions[item_id] = "fail"
    all_complete = (
        (claim_complete or not use_claims)
        and (len(evaluation.qa) == len(bank.information) or not use_qa)
        and all(q.verdict != "unassessable" for q in evaluation.qa)
        and (len(evaluation.answers) == len([q for q in bank.questions if q.primary]) or not use_qa)
        and all(a.status != "failed" for a in evaluation.answers)
        and set(dimensions) == set(active_items)
        and all(v != "unassessable" for v in dimensions.values())
        and not evaluation.failures
    )
    critical = sum(
        v.severity == "critical"
        for v in (*evaluation.claims, *evaluation.qa, *evaluation.dimensions, *evaluation.citations)
    )
    expected_evidence = {
        digest((e.source_id, e.span.unit_id)) for i in bank.information for e in i.evidence
    }
    evidence_found = expected_evidence & set(evaluation.retrieved_sources)
    cited = [v for v in evaluation.claims if v.evidence]
    from .citations import extract

    authored = extract(note, case) if "citations" in evaluation.methods else []
    citation_verdicts = {v.citation_id: v for v in evaluation.citations}
    assessed_citations = [
        citation_verdicts[c["id"]].verdict
        for c in authored
        if c["id"] in citation_verdicts and citation_verdicts[c["id"]].verdict != "uncertain"
    ]
    citation_complete = len(assessed_citations) == len(authored)
    citation_severity_complete = all(
        c.verdict not in ("unsupported", "invalid") or c.severity is not None
        for c in evaluation.citations
    )
    all_complete = all_complete and (
        (citation_complete and citation_severity_complete) or "citations" not in evaluation.methods
    )
    method_assessment = {
        "claims": {
            "planned": len(segmentation.claims),
            "applicable": len(segmentation.claims),
            "assessed": len(evaluation.claims) - claims["unassessable"],
            "missing": len(segmentation.claims) - len(evaluation.claims),
            "unassessable": claims["unassessable"],
            "complete": claim_complete,
        },
        "qa": {
            "planned": len(bank.information),
            "applicable": len(bank.information),
            "assessed": sum(q.verdict != "unassessable" for q in evaluation.qa),
            "missing": len(bank.information) - len(evaluation.qa),
            "unassessable": sum(q.verdict == "unassessable" for q in evaluation.qa),
            "complete": len(evaluation.qa) == len(bank.information)
            and all(q.verdict != "unassessable" for q in evaluation.qa)
            and len(evaluation.answers) == len([q for q in bank.questions if q.primary])
            and all(a.status != "failed" for a in evaluation.answers),
        },
        "items": {
            "planned": len(active_items),
            "applicable": len(active_items)
            - sum(v == "not_applicable" for v in dimensions.values()),
            "assessed": sum(v in ("pass", "fail", "rated") for v in dimensions.values()),
            "missing": len(active_items) - len(dimensions),
            "unassessable": sum(v == "unassessable" for v in dimensions.values()),
            "complete": set(dimensions) == set(active_items)
            and all(v != "unassessable" for v in dimensions.values()),
        },
        "citations": {
            "planned": len(authored),
            "applicable": len(authored),
            "assessed": len(assessed_citations),
            "missing": len(authored) - len(citation_verdicts),
            "unassessable": sum(v.verdict == "uncertain" for v in evaluation.citations),
            "complete": citation_complete and citation_severity_complete,
            "severity_unassessed": sum(
                c.verdict in ("unsupported", "invalid") and c.severity is None
                for c in evaluation.citations
            ),
        },
    }
    scope_complete = (
        bool(evaluation.required_methods)
        and not evaluation.failures
        and all(
            method in evaluation.methods and method_assessment[method]["complete"]
            for method in evaluation.required_methods
        )
    )
    cited_claims = sum(
        any(
            any(
                span.start <= c["span"]["start"] and c["span"]["end"] <= span.end
                for span in claim.spans
            )
            for c in authored
        )
        for claim in segmentation.claims
    )
    not_applicable = []
    if evaluation.segmentation_complete is True and not segmentation.claims:
        not_applicable.extend(
            ("faithfulness", "citation_coverage", "evidence_coverage", "evidence_support")
        )
    elif claim_complete and not cited:
        not_applicable.append("evidence_support")
    if not authored:
        not_applicable.extend(("citation_support", "citation_validity"))
    not_applicable.extend(
        key + "_fail" for key, value in dimensions.items() if value == "not_applicable"
    )
    if evaluation.source_mode == "full_context":
        not_applicable.append("retrieval_recall")
    for importance in ("essential", "supplementary"):
        if not coverage[importance]["expected"]:
            not_applicable.append(importance + "_recall")
    not_requested = []
    if not use_claims:
        not_requested.extend(
            ("faithfulness", "evidence_coverage", "evidence_support", "citation_coverage")
        )
    if not use_qa:
        not_requested.extend(("essential_recall", "supplementary_recall"))
    if "citations" not in evaluation.methods:
        not_requested.extend(("citation_coverage", "citation_support", "citation_validity"))
    return {
        "not_requested": not_requested,
        "methods": list(evaluation.methods),
        "assessment_scope": evaluation.assessment_scope,
        "required_methods": list(evaluation.required_methods),
        "method_assessment": {
            k: v for k, v in method_assessment.items() if k in evaluation.methods
        },
        "critical_scope_complete": scope_complete,
        "critical_findings_by_method": {
            k: sum(v.severity == "critical" for v in values)
            for k, values in (
                ("qa", evaluation.qa),
                ("claims", evaluation.claims),
                ("items", evaluation.dimensions),
                ("citations", evaluation.citations),
            )
            if k in evaluation.methods
        },
        "not_applicable": not_applicable,
        "claim_checks_expected": len(segmentation.claims) if use_claims else 0,
        "claim_checks_answered": len(evaluation.claims),
        "claim_outcomes": dict(claims),
        "segmentation_audit": evaluation.segmentation_complete,
        "faithfulness": fraction(claims["supported"], len(segmentation.claims), claim_complete),
        "coverage": coverage,
        "dimensions": dimensions,
        "critical_findings_observed": critical,
        "has_critical_error": True if critical else (False if scope_complete else None),
        "fully_evaluated": all_complete,
        "evidence_coverage": fraction(len(cited), len(segmentation.claims), claim_complete),
        "evidence_support": fraction(
            sum(c.citation_support == "supported" for c in cited),
            len(cited),
            claim_complete and all(c.citation_support != "uncertain" for c in cited),
        ),
        "citation_coverage": fraction(
            cited_claims, len(segmentation.claims), evaluation.segmentation_complete is True
        ),
        "citation_support": fraction(
            assessed_citations.count("supported"),
            len(authored),
            citation_complete,
        ),
        "citation_validity": fraction(sum(c["valid"] for c in authored), len(authored)),
        "citation_assessment": {
            "planned": len(authored),
            "assessed": len(assessed_citations),
            "missing": len(authored) - len(assessed_citations),
            "severity_unassessed": sum(
                c.verdict in ("unsupported", "invalid") and c.severity is None
                for c in evaluation.citations
            ),
            "observed_subset_support": fraction(
                assessed_citations.count("supported"), len(assessed_citations)
            ),
            "interpretation": "Conditional on assessed author references; not full-note precision",
        },
        "measurement_values": {
            d.dimension: {
                "status": dimensions[d.dimension],
                "value": d.value,
                "format": active_items[d.dimension].response_format,
            }
            for d in evaluation.dimensions
        },
        "item_assessment": {
            "planned": len(active_items),
            "not_applicable": sum(v == "not_applicable" for v in dimensions.values()),
            "assessed": sum(v in ("pass", "fail", "rated") for v in dimensions.values()),
            "missing": len(active_items) - len(dimensions),
            "unassessable": sum(v == "unassessable" for v in dimensions.values()),
        },
        "retrieval_recall": (
            fraction(len(evidence_found), len(expected_evidence))
            if evaluation.source_mode == "retrieved"
            else None
        ),
        "word_count": len(note.text.split()),
        "within_word_limit": word_limit_ok,
        "deterministic_checks": checks(note),
        "failures": list(evaluation.failures),
    }


def cluster_interval(
    values: list[tuple[str, float]], samples: int = 2000, seed: int = 20260911
) -> dict:
    """Resample whole clients, retaining all their sessions. One client gives no CI."""
    groups: dict[str, list[float]] = defaultdict(list)
    for group, value in values:
        groups[group].append(value)
    mean = statistics.mean(v for _, v in values) if values else None
    if len(groups) < 2:
        return {"mean": mean, "ci95": None, "independent_groups": len(groups), "n": len(values)}
    rng = random.Random(seed)
    names = sorted(groups)
    draws = sorted(
        statistics.mean(v for name in rng.choices(names, k=len(names)) for v in groups[name])
        for _ in range(samples)
    )
    return {
        "mean": mean,
        "ci95": [draws[int(samples * 0.025)], draws[int(samples * 0.975) - 1]],
        "independent_groups": len(groups),
        "n": len(values),
    }


def paired_interval(
    left: dict[str, tuple[str, float]], right: dict[str, tuple[str, float]]
) -> dict:
    shared = sorted(set(left) & set(right))
    require(all(left[k][0] == right[k][0] for k in shared), "Pair has inconsistent client groups")
    out = cluster_interval([(left[k][0], left[k][1] - right[k][1]) for k in shared])
    return {
        **out,
        "shared_cases": len(shared),
        "left_only": len(set(left) - set(right)),
        "right_only": len(set(right) - set(left)),
        "interpretation": "A CI crossing zero does not establish equivalence.",
    }


def wilson(successes: int, total: int) -> list[float] | None:
    if not total:
        return None
    require(0 <= successes <= total, "Invalid binomial counts")
    z = statistics.NormalDist().inv_cdf(0.975)
    p, scale = successes / total, 1 + z * z / total
    center = (p + z * z / (2 * total)) / scale
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / scale
    return [max(0.0, center - radius), min(1.0, center + radius)]


def validation_metrics(pairs: list[tuple[str, str]], positive: str) -> dict:
    """Human-reference confusion counts; agreement is not an accuracy ceiling."""
    labels = sorted({label for pair in pairs for label in pair})
    cells = {a: {b: sum(x == a and y == b for x, y in pairs) for b in labels} for a in labels}
    n = len(pairs)
    agree = sum(a == b for a, b in pairs)
    chance = (
        sum(sum(a == k for a, _ in pairs) * sum(b == k for _, b in pairs) for k in labels) / n**2
        if n
        else None
    )
    tp = sum(a == positive and b == positive for a, b in pairs)
    positives = sum(a == positive for a, _ in pairs)
    negatives = n - positives
    tn = sum(a != positive and b != positive for a, b in pairs)
    return {
        "n": n,
        "positive_class": positive,
        "confusion": cells,
        "observed_agreement": fraction(agree, n),
        "kappa": (agree / n - chance) / (1 - chance) if n and chance < 1 else None,
        "sensitivity": fraction(tp, positives),
        "sensitivity_ci95": None,
        "specificity": fraction(tn, negatives),
        "specificity_ci95": None,
        "ci_method": "Not estimated: annotation units may share clients, notes and raters. "
        "Use a cluster-aware confirmatory design; binomial intervals would assume independence.",
        "reference_positives": positives,
        "interpretation": "Agreement with these raters, not a theoretical ceiling.",
    }


def plan_sample(
    half_width: float = 0.05,
    prevalence: float = 0.5,
    sessions_per_client: int = 1,
    intraclient_correlation: float = 0.0,
) -> dict:
    require(
        0 < half_width < 1
        and 0 < prevalence < 1
        and sessions_per_client > 0
        and 0 <= intraclient_correlation < 1,
        "Invalid planning assumptions",
    )
    independent = math.ceil(
        statistics.NormalDist().inv_cdf(0.975) ** 2 * prevalence * (1 - prevalence) / half_width**2
    )
    effect = 1 + (sessions_per_client - 1) * intraclient_correlation
    return {
        "independent_equivalent": independent,
        "design_effect": effect,
        "clients": math.ceil(independent * effect / sessions_per_client),
        "half_width": half_width,
        "confidence": 0.95,
        "prevalence_assumption": prevalence,
        "sessions_per_client": sessions_per_client,
        "icc": intraclient_correlation,
        "status": "Planning approximation; freeze assumptions before confirmation sampling.",
        "sensitivity_note": "For sensitivity, n counts reference-positive error opportunities; "
        "enriched controls do not estimate real-world error prevalence.",
    }
