"""Private human screening sheets and source-anchored extraction imports."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from . import annotations
from .registry import ConstructDefinition, EvidenceRecord, InstrumentRegistry, SupportingSource
from .schema import PROFILES, digest, require


def screening_sheet(store, active, stage):
    from .research import current_decisions, records_for

    decisions = current_decisions(store, active)
    previous = {d["record_id"]: digest(d) for d in decisions if d["stage"] == stage}
    included = {
        d["record_id"]
        for d in decisions
        if d["stage"] == "title_abstract" and d["decision"] == "include"
    }
    finished = {
        d["record_id"] for d in decisions if d["stage"] == stage and d["decision"] != "uncertain"
    }
    records = [
        r
        for r in records_for(store, active)
        if r["id"] not in finished and (stage == "title_abstract" or r["id"] in included)
    ]
    require(bool(records), "No pending records at this screening stage")
    body = {
        "version": annotations.VERSION,
        "mode": "independent",
        "language": "en",
        "profile": "all",
        "cohort": ["literature", "en", "published"],
        "stage": "literature_screening",
        "screening_stage": stage,
        "study_id": active["id"],
        "previous_decisions": previous,
        "sources": [],
        "note": "",
        "purpose_instructions": "Apply the frozen inclusion and exclusion criteria. "
        "Read the full text before a full-text decision. "
        "Record uncertainty and every exclusion reason. This sheet contains no automatic verdict.",
        "eligibility": {k: active["protocol"].get(k, []) for k in ("include", "exclude")},
        "items": [
            {
                "id": r["id"],
                "kind": "eligibility",
                "profile": "all",
                "text": r["title"],
                "context": {"abstract": r["records"][0].get("abstract", ""), "doi": r["doi"]},
                "choices": ["include", "exclude", "uncertain"]
                + (["not_retrieved"] if stage == "full_text" else []),
                "require_reason": True,
            }
            for r in records
        ],
        "missing_information_prompt": "Record additional coverage gaps "
        "or problems with eligibility rules.",
    }
    return {**body, "id": digest(body)}


def import_screening(store, active, sheet, response):
    from .research import screen

    require(sheet["study_id"] == active["id"], "Screening sheet belongs to another review")
    checked = annotations.import_response(sheet, response)
    decisions = [
        {
            "record_id": a["id"],
            "stage": sheet["screening_stage"],
            "decision": a["value"],
            "reason": a.get("reason", ""),
            "reviewer": checked["rater_id"],
            "instrument_author": checked["instrument_author"],
            "mode": "human",
            "decided_at": response.get("submitted_at", "not recorded"),
            "imported_at": datetime.now(UTC).isoformat(),
            "sheet_id": sheet["id"],
        }
        for a in checked["answers"]
    ]
    for decision in decisions:
        previous = sheet.get("previous_decisions", {}).get(decision["record_id"])
        if previous:
            decision.update(supersedes=previous, amendment_reason=decision["reason"])
    return screen(store, active, decisions)


def flat(text: str) -> str:
    """The text with its whitespace removed, for comparing a quote with a source.

    Every extractor breaks words at a line or column edge, with a hyphen or
    without one, so a quote that is in the document is often not in the string
    the extractor produced. Dropping whitespace on both sides keeps the check
    exact in the character sequence, which is what a quote is, and stops it
    failing on the layout of the page it came from.
    """
    return re.sub(r"\s+", "", text)


def import_extraction(store, active, request_id, entries):
    request = store.get("research_extraction_requests", request_id)
    require(
        request is not None and request["study_id"] == active["id"], "Unknown extraction request"
    )
    require(isinstance(entries, list), "Extraction must be a JSON array")
    text = request["source_text"]
    for entry in entries:
        require(isinstance(entry, dict), "Invalid extraction entry")
        require(
            bool(
                entry.get("source_location")
                and entry.get("exact_quote")
                and entry.get("construct_name")
                and entry.get("definition")
            ),
            "Incomplete source-derived candidate",
        )
        require(
            flat(entry["exact_quote"]) in flat(text),
            "Extraction quote is absent from the supplied source",
        )
    result = {
        "study_id": active["id"],
        "request_id": request_id,
        "record_id": request["record_id"],
        "full_text_digest": request["full_text_digest"],
        "entries": entries,
        "status": "source_span_checked_human_interpretation_pending",
    }
    store.put("research_extractions", digest(result), result)
    return {"extraction_id": digest(result), "candidates": len(entries), "status": result["status"]}


def build_pool(store, active):
    from .research import records_for

    records = {r["id"]: r for r in records_for(store, active)}
    extracts = [e for e in store.all("research_extractions") if e["study_id"] == active["id"]]
    # Do not silently combine two competing extractions of the same report.
    require(
        len({e["record_id"] for e in extracts}) == len(extracts),
        "Select one extraction per report before pooling; competing outputs need review",
    )
    sources, evidence, constructs = [], [], []
    for extract in extracts:
        record = records[extract["record_id"]]
        sources.append(
            SupportingSource(
                record["id"],
                record["title"],
                "https://doi.org/" + record["doi"] if record["doi"] else record["id"],
                "unclassified",
                "unverified",
                "candidate",
                "Source layer and publication type are provisional and need human verification.",
            )
        )
        for entry in extract["entries"]:
            eid = "ev-" + digest((extract["record_id"], entry))[:20]
            evidence.append(
                EvidenceRecord(
                    eid,
                    record["id"],
                    entry["source_location"],
                    entry["definition"],
                    "hypothesis",
                    population=str(entry.get("population") or "not stated"),
                    languages=(str(entry["language"]),) if entry.get("language") else (),
                    raters=str(entry.get("raters") or "not stated"),
                    unit=str(entry.get("unit") or "not stated"),
                    response_format=str(entry.get("original_response_format") or "not stated"),
                    validation=str(entry.get("validation_design") or "not stated"),
                    limitations="Extraction is a candidate interpretation; "
                    "exact span checking is not human validation. Source limitations: "
                    + str(entry.get("limitations") or "not stated"),
                    source_artifact_digest=extract["full_text_digest"],
                    excerpt=entry["exact_quote"],
                )
            )
            constructs.append(
                ConstructDefinition(
                    "c-" + digest((record["id"], entry))[:20],
                    entry["construct_name"],
                    entry["definition"],
                    (),
                    (eid,),
                    {p: "Requires purpose-specific human assessment" for p in PROFILES},
                    str(entry.get("unit") or "not stated"),
                    ("to be operationalized",),
                    {
                        k: "Not established; develop after verifying the source"
                        for k in ("positive", "negative", "boundary")
                    },
                    (str(entry.get("original_response_format") or "not stated in source"),),
                    "Requires source and purpose review",
                    "Requires clinical assessment",
                    origin="literature",
                    origin_reference="extraction:" + digest(extract),
                )
            )
    registry = InstrumentRegistry(
        tuple(sources), tuple(evidence), tuple(constructs), (), active["protocol_revision"]
    )
    registry.check()
    path = store.put("literature_pools", registry.revision, registry)
    return {
        "registry": str(path),
        "constructs": len(constructs),
        "status": "candidate_pool_unreviewed",
        "prior_proposals_included": False,
    }
