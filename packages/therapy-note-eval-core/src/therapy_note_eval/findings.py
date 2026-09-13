"""Explicit human linkage of overlapping findings, without inventing independence."""

from .schema import Evaluation, digest, require, unique


def inventory(evaluation: Evaluation) -> dict:
    return {
        **{
            "citation:" + c.citation_id: c.severity
            for c in evaluation.citations
            if c.verdict in ("unsupported", "invalid")
        },
        **{
            "claim:" + c.claim_id: c.severity
            for c in evaluation.claims
            if c.verdict in ("contradicted", "unsupported")
        },
        **{
            "qa:" + q.information_id: q.severity
            for q in evaluation.qa
            if q.verdict in ("partial", "omitted", "contradicted")
        },
        **{
            "dimension:" + d.dimension: d.severity
            for d in evaluation.dimensions
            if d.verdict == "fail"
        },
    }


def summarize(evaluation: Evaluation, linkage: dict | None = None) -> dict:
    findings = inventory(evaluation)
    groups = []
    if linkage is not None:
        require(
            linkage.get("evaluation_revision") == digest(evaluation),
            "Finding links refer to a different evaluation",
        )
        require(
            linkage.get("mode") == "human_reviewed" and bool(linkage.get("reviewer")),
            "Error grouping requires an actual human review",
        )
        groups = linkage.get("groups", [])
        require(isinstance(groups, list), "Invalid finding groups")
        unique((g["id"] for g in groups), "Duplicate finding group")
        members = [key for g in groups for key in g["finding_ids"]]
        unique(members, "One finding cannot be counted in two error groups")
        require(set(members) <= set(findings), "Unknown finding in error group")
        require(
            all(g["finding_ids"] and g.get("reason") for g in groups),
            "Every reviewed group needs members and a reason",
        )
    linked = {key for g in groups for key in g["finding_ids"]}
    return {
        "raw_findings": len(findings),
        "reviewed_groups": len(groups),
        "unlinked_findings": len(set(findings) - linked),
        "distinct_errors": len(groups) if linkage is not None and linked == set(findings) else None,
        "status": "Human grouping of overlapping findings; not independent statistical samples.",
    }
