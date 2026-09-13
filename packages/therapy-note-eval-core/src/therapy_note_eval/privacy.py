"""Local fragment detection and allow-listed aggregate export. Never print source text."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

from .schema import require


def words(text: str) -> list[str]:
    # Public HTML and JSON can carry escaped Unicode, including inside script tags.
    text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m[1], 16)), text)
    return re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold())


def fingerprints(text: str, window: int = 12) -> set[str]:
    require(window >= 8, "Fragment window is too small")
    tokens = words(text)
    return {
        hashlib.sha256(" ".join(tokens[i : i + window]).encode("utf-8")).hexdigest()
        for i in range(len(tokens) - window + 1)
    }


def find_fragments(text: str, sources: dict[str, set[str]]) -> list[str]:
    """Return source digests only. Exact normalized overlap cannot detect paraphrased disclosure."""
    observed = fingerprints(text)
    return sorted(key for key, fragments in sources.items() if observed & fragments)


def load_local_fingerprints(roots: list[Path]) -> dict[str, set[str]]:
    result = {}
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.txt")):
            text = path.read_text(encoding="utf-8-sig")
            result[hashlib.sha256(text.encode("utf-8")).hexdigest()] = fingerprints(text)
        for path in sorted(root.glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(record, dict) and record.get("origin") == "native_real":
                for source in record.get("sources", []):
                    text = " ".join(t["text"] for t in source["turns"])
                    result[hashlib.sha256(text.encode("utf-8")).hexdigest()] = fingerprints(text)
    return result


def public_report(payload: dict) -> dict:
    """Export fixed aggregate fields, never raw settings, rationales or arbitrary metadata."""

    def label(value):
        require(
            isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", value) is not None,
            "Unsafe public identifier",
        )
        return value

    def numeric(value):
        if isinstance(value, dict):
            return {label(k): numeric(v) for k, v in value.items() if k != "interpretation"}
        if isinstance(value, list):
            return [numeric(v) for v in value]
        require(
            value is None or type(value) in (int, float, bool), "Public aggregate contains text"
        )
        json.dumps(value, allow_nan=False)
        return value

    cohorts = []
    for cohort in payload["cohorts"]:
        cohorts.append(
            {
                "manifest_id": label(cohort["manifest_id"]),
                "language": label(cohort["spec"]["language"]),
                "profile": label(cohort["spec"]["profile"]),
                "origin": label(cohort["origin"]),
                "corpus": label(cohort["corpus"]),
                "split": label(cohort["split"]),
                "research_revision": label(cohort["research_revision"]),
                "measurement_revision": label(cohort["measurement_revision"]),
                "implementation_digest": label(cohort["implementation_digest"]),
                "aggregation_version": label(cohort["aggregation_version"]),
                "assessment_scope": label(cohort["assessment_scope"]),
                "methods": [label(m) for m in cohort["methods"]],
                "required_methods": [label(m) for m in cohort["required_methods"]],
                "replicate_id": label(cohort["replicate_id"]),
                "source_mode": label(cohort["source_mode"]),
                "judge": {k: label(cohort["judge"][k]) for k in ("provider", "model", "family")},
                "validation_status": "synthetic_demonstration"
                if cohort["origin"] == "synthetic"
                else "experimental_not_validated",
                "independent_groups": numeric(cohort["independent_groups"]),
                "systems": [
                    {
                        "model": label(s["system"]["model"]),
                        "metrics": numeric(s["metrics"]),
                        "generated": numeric(s["generated"]),
                        "expected": numeric(s["expected"]),
                        "critical_notes_observed": numeric(s["critical_notes_observed"]),
                        "evaluations": numeric(s["evaluations"]),
                        "critical_findings_observed": numeric(s["critical_findings_observed"]),
                        "critical_findings_by_method": numeric(s["critical_findings_by_method"]),
                        "error_types": numeric(s["error_types"]),
                        "critical_scope_complete_notes": numeric(
                            s["critical_scope_complete_notes"]
                        ),
                        "critical_scope_incomplete_notes": numeric(
                            s["critical_scope_incomplete_notes"]
                        ),
                        "method_assessment": numeric(s["method_assessment"]),
                        "item_distributions": {
                            label(k): {
                                "format": label(d["format"]),
                                "labels": [label(v) for v in d["labels"]],
                                **numeric(
                                    {
                                        name: value
                                        for name, value in d.items()
                                        if name not in ("labels", "format")
                                    }
                                ),
                            }
                            for k, d in s["item_distributions"].items()
                        },
                    }
                    for s in cohort["systems"]
                ],
            }
        )
    return {"protocol": label(payload["protocol"]), "status": "experimental", "cohorts": cohorts}
