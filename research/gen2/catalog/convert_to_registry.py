"""Convert the catalog into a draft `InstrumentRegistry`, and say what did not map.

The catalog is a research record; the registry is what the Gen-2 core runs.
They have different shapes, and the audit of 2026-09-15 (A03) asked for one
explicit conversion instead of a second hand-kept copy. This is it.

What it does: every source, every evidence line and every candidate becomes a
registry record with `status: candidate`, `reviewed_by: null` and no human
decision anywhere. What it refuses to do: invent an operational item, a
selected method or a review. The pilot proposal's entries lack anchors, labels
and a reference mode, so none becomes a `MeasurementSpec`; each is listed in
the diagnostics with its record kind and the reason. The core's own pilot check
is run on the result and its refusal is recorded verbatim, which is the proof
that the draft cannot be frozen by relabelling.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

from therapy_note_eval.registry import load_registry
from therapy_note_eval.schema import ValidationError, digest

HERE = Path(__file__).resolve().parent
PROTOCOL_PATH = HERE.parent / "protocol.json"
PROPOSALS_PATH = HERE.parent / "prior-proposals.json"
REGISTRY_PATH = HERE / "draft-registry.json"
DIAGNOSTICS_PATH = HERE / "conversion-diagnostics.json"

LAYER = {
    "direct": "direct",
    "transfer": "transfer",
    "requirements": "requirements",
    "method": "methodology",
}
VERIFICATION = {
    "full_text": "full_text_checked",
    "not_retrieved": "metadata_checked",
    "abstract": "metadata_checked",
}
RELATIONSHIP = {
    "direct": "direct_validation",
    "transfer": "method_transfer",
    "requirements": "requirement",
    "methodology": "hypothesis",
}
ORIGIN = {
    "literature": "literature",
    "prior_local": "prior_proposal",
    "expert_proposal": "prior_proposal",
    "empirical_observation": "inductive",
}
ORIGIN_NEEDS = {
    "literature": "an extraction record (extraction:<id>) bound to an included full text",
    "prior_proposal": "a recorded proposal (proposal:<id>) from prior-proposals.json "
    "or record-input",
    "inductive": "a recorded observation (observation:<id>) from record-input",
}
#: The four methods the core implements, and the catalog method each stands for.
IMPLEMENTATION = {"ME01": "qa", "ME02": "claims", "ME03": "items", "ME08": "citations"}
NOT_A_MEASUREMENT = {
    "executable_measure": "no anchors, labels, question or reference mode are recorded, "
    "and no human selected it",
    "requirements_check": "a deterministic check against an external specification, "
    "not a rated item",
    "human_use_outcome": "a task a person performs; the core has no human-task record type",
    "study_condition": "a check of the instrument, not a property of a note",
    "corpus_level_proxy": "computed over a system's notes; a MeasurementSpec scores one note",
    "derived_ratio": "derived from another entry; not an item a rater answers",
}


def _catalog_module():
    spec = importlib.util.spec_from_file_location("gen2_catalog", HERE / "catalog.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("gen2_catalog", module)
    spec.loader.exec_module(module)
    return module


def publication_type(kind: str) -> str:
    kind = kind.lower()
    if "preprint" in kind:
        return "preprint"
    if "peer-reviewed" in kind:
        return "article"
    if "guidance" in kind or "guideline" in kind or "legal" in kind:
        return "guideline"
    return "unverified"


def origin_reference(candidate: dict, proposals: set[str]) -> tuple[str, str]:
    """The reference the workflow expects, when the catalog states it verbatim."""
    origin = ORIGIN[candidate["origin"]]
    if origin == "prior_proposal":
        named = sorted(
            p for p in proposals if re.search(rf"\b{re.escape(p)}\b", candidate["origin_note"])
        )
        if len(named) == 1:
            return "proposal:" + named[0], "origin note names the recorded proposal " + named[0]
    return "catalog:" + candidate["id"], (
        f"placeholder: the workflow needs {ORIGIN_NEEDS[origin]}; "
        "the catalog records the origin in prose only"
    )


def convert(catalog: dict, protocol: dict, proposals: dict) -> tuple[dict, dict]:
    by_source = {s["id"]: s for s in catalog["sources"]}
    proposal_ids = {p["id"] for p in proposals["proposals"]}
    sources, source_notes = [], []
    for s in catalog["sources"]:
        ptype = publication_type(s["type"])
        sources.append(
            {
                "id": s["id"],
                "title": s["citation"],
                "locator": "ledger:" + s["ledger_report_id"],
                "layer": LAYER[s["layer"]],
                "publication_type": ptype,
                "verification": VERIFICATION[s["verification"]],
                "limitations": s["limitations"],
                "version": "source-v1",
            }
        )
        if ptype == "unverified" or s["verification"] != "full_text":
            source_notes.append(
                {
                    "id": s["id"],
                    "publication_type": ptype,
                    "verification": VERIFICATION[s["verification"]],
                    "note": "type or verification could not be mapped to a checked category",
                }
            )
    for s in catalog["abstract_sources"]:
        sources.append(
            {
                "id": s["id"],
                "title": s["citation"],
                "locator": "ledger:" + s["ledger_report_id"],
                "layer": LAYER[s["layer"]],
                "publication_type": "unverified",
                "verification": "metadata_checked",
                "limitations": "Read from the abstract only; the full text was not retrieved "
                "in this round. " + s["relevance"],
                "version": "source-v1",
            }
        )
        source_notes.append(
            {
                "id": s["id"],
                "publication_type": "unverified",
                "verification": "metadata_checked",
                "note": "abstract-only source; the pilot check refuses it until the full text "
                "is verified",
            }
        )
    evidence, constructs, construct_notes = [], [], []
    for c in catalog["candidates"]:
        ids = []
        for i, e in enumerate(c["evidence"], start=1):
            source = by_source.get(e["source"])
            abstract_only = source is None
            eid = f"{c['id']}-e{i}"
            ids.append(eid)
            evidence.append(
                {
                    "id": eid,
                    "source_id": e["source"],
                    "location": e["location"],
                    "interpretation": e["supports"],
                    "relationship": "hypothesis"
                    if abstract_only
                    else RELATIONSHIP[LAYER[source["layer"]]],
                    "population": "not established" if abstract_only else source["population"],
                    "languages": [] if abstract_only else [source["language"]],
                    "raters": "not established" if abstract_only else source["raters"],
                    "unit": "not established" if abstract_only else source["unit"],
                    "response_format": "not established" if abstract_only else source["format"],
                    "validation": "not established",
                    "limitations": e["our_adaptation"],
                    "human_checked_by": None,
                    "source_artifact_digest": "",
                    "excerpt": e["quote"],
                }
            )
        reference, note = origin_reference(c, proposal_ids)
        constructs.append(
            {
                "id": c["id"],
                "name": c["label"],
                "definition": c["definition"],
                "families": [c["family"]],
                "evidence_ids": ids,
                "relevance": dict(c["relevance"]),
                "unit": c["unit"],
                "required_inputs": [x.strip() for x in c["inputs"].split(",") if x.strip()],
                "examples": dict(c["examples"]),
                "candidate_formats": [c["mode"]],
                "applicability": c["applicability"],
                "error_consequences": c["error_consequence"],
                "status": "candidate",
                "decision_reason": "Awaiting human review",
                "reviewed_by": None,
                "origin": ORIGIN[c["origin"]],
                "origin_reference": reference,
            }
        )
        construct_notes.append(
            {
                "id": c["id"],
                "catalog_state": c["state"],
                "catalog_origin": c["origin"],
                "origin": ORIGIN[c["origin"]],
                "origin_reference": reference,
                "note": note,
                "record_kind": c["kind"],
            }
        )
    registry = {
        "sources": sources,
        "evidence": evidence,
        "constructs": constructs,
        "measurements": [],
        "protocol_revision": digest(protocol),
        "version": "registry-v2",
        "literature_freeze": None,
        "methods": [],
        "method_evidence": {},
        "methods_reviewed_by": None,
        "method_specs": [],
        "reviews": [],
        "assessment_scope": "",
        "required_methods": [],
        "research_snapshot": None,
    }
    load_registry(registry)
    try:
        load_registry(registry, pilot=True)
        refusal = None
    except ValidationError as exc:
        refusal = str(exc)
    pilot_notes = [
        {
            "id": p["id"],
            "record_kind": p["record_kind"],
            "measures": p["measures"],
            "method": p["method"],
            "why_not_a_measurement": NOT_A_MEASUREMENT[p["record_kind"]],
        }
        for p in catalog["pilot_proposal"]["entries"]
    ]
    method_notes = [
        {
            "id": m["id"],
            "implementation": IMPLEMENTATION.get(m["id"]),
            "readiness": m["readiness"],
            "note": (
                "stands for the core's "
                + IMPLEMENTATION[m["id"]]
                + " method; not selected, because selection is a human decision"
            )
            if m["id"] in IMPLEMENTATION
            else "no counterpart among the four implemented methods; usable only after its "
            "own implementation and review",
        }
        for m in catalog["methods"]
    ]
    diagnostics = {
        "version": "conversion-diagnostics-v1",
        "catalog_version": catalog["version"],
        "catalog_date": catalog["catalog_date"],
        "protocol_version": protocol["version"],
        "protocol_revision": registry["protocol_revision"],
        "rule": "Every source, evidence line and candidate maps to a registry record with no "
        "human decision. Nothing becomes an operational item, a selected method or a review; "
        "each such gap is listed here with its reason.",
        "mapped": {
            "sources": len(sources),
            "evidence": len(evidence),
            "constructs": len(constructs),
        },
        "not_mapped": {
            "measurements": len(catalog["pilot_proposal"]["entries"]),
            "methods": len(catalog["methods"]),
            "reviews": 0,
        },
        "pilot_check": {"result": "refused" if refusal else "passed", "message": refusal},
        "relationship_rule": "derived from the source's evidence layer, not from a human "
        "reading of the passage",
        "state_rule": "a catalog state is a research judgement and never becomes a registry "
        "status: every construct is decoded as candidate, because pilot status is a human "
        "selection the core refuses to infer",
        "origin_rule": "catalog origins prior_local and expert_proposal both map to "
        "prior_proposal; empirical_observation maps to inductive; the historical origin never "
        "changes because of later evidence",
        "sources": source_notes,
        "constructs": construct_notes,
        "pilot_entries": pilot_notes,
        "methods": method_notes,
    }
    return registry, diagnostics


def _dump(path: Path, value) -> None:
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


if __name__ == "__main__":
    module = _catalog_module()
    catalog = module.load()
    found = module.problems(catalog)
    if found:
        print("\n".join(found))
        raise SystemExit(1)
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    proposals = json.loads(PROPOSALS_PATH.read_text(encoding="utf-8"))
    registry, diagnostics = convert(catalog, protocol, proposals)
    _dump(REGISTRY_PATH, registry)
    _dump(DIAGNOSTICS_PATH, diagnostics)
    print(
        "draft registry:",
        diagnostics["mapped"],
        "pilot check:",
        diagnostics["pilot_check"]["result"],
    )
