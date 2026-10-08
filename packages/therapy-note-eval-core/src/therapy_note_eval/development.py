"""Versioned mixed-source development and actual imported human decisions.

The software checks lineage, not a person's identity or the truth of their judgment.
Only the person who performed a review may supply its human response.
"""

import json
from dataclasses import replace
from datetime import UTC, datetime

from . import annotations
from .registry import ReviewDecision, load_registry, subject_digest
from .schema import digest, plain, require


def registry_sheet(store, active, raw, *, amend=False):
    registry = load_registry(raw)
    require(registry.protocol_revision == active["protocol_revision"], "Different review protocol")
    store.put("registry_drafts", registry.revision, registry)
    subjects = registry.subjects()
    body = {
        "version": annotations.VERSION,
        "mode": "adjudication" if amend else "independent",
        "language": "en",
        "profile": "all",
        "cohort": ["research", "en", "development"],
        "stage": "registry_review",
        "study_id": active["id"],
        "registry_revision": registry.revision,
        "sources": [],
        "note": "",
        "purpose_instructions": "Check the exact content, provenance and supporting sources. "
        "Accept only after your own review; record limitations and a reason for every decision. "
        "An author review is not independent external validation.",
        "items": [
            {
                "id": key,
                "kind": "research_decision",
                "profile": "all",
                "text": key,
                "context": {"research_content": value},
                "subject_digest": subject_digest(value),
                "choices": ["accept", "exclude", "revise", "unresolved", "merge"],
                "require_reason": True,
            }
            for key, value in subjects.items()
        ],
        "missing_information_prompt": "Identify missing needs or unclear measurement rules.",
    }
    if amend:
        superseded = {key for r in registry.reviews for key in r.supersedes}
        for item in body["items"]:
            current = [
                r for r in registry.reviews if r.subject == item["id"] and r.id not in superseded
            ]
            item["supersedes"] = [r.id for r in current]
            item["human_votes"] = [
                {"rater": r.reviewer, "value": r.decision, "reason": r.reason} for r in current
            ]
    return {**body, "id": digest(body)}


def import_registry_review(store, active, sheet, response):
    require(
        sheet["study_id"] == active["id"] and sheet["stage"] == "registry_review",
        "Unknown registry review sheet",
    )
    require(
        sheet["id"] == digest({k: v for k, v in sheet.items() if k != "id"}),
        "Modified registry review sheet",
    )
    require(bool(response.get("submitted_at")), "Human decision time is missing")
    checked = annotations.import_response(sheet, response)
    registry = load_registry(store.get("registry_drafts", sheet["registry_revision"]))
    require(registry.revision == sheet["registry_revision"], "Registry draft was changed")
    response_id = digest({"study_id": active["id"], "sheet_id": sheet["id"], "response": response})
    prior = {r.id: r for r in registry.reviews}
    superseded = {k for r in registry.reviews for k in r.supersedes}
    delegated = bool(response.get("delegated", False))
    if delegated:
        ledger = {d["id"] for d in active["protocol"].get("decision_ledger", ())}
        require(
            response.get("delegation_decision") in ledger,
            "A delegated review names the protocol decision that delegates it",
        )
        require(
            all(a.get("value") == "accept" for a in checked["answers"]),
            "A delegation can only accept the assistant's reading; any other decision "
            "is the reviewer's own and is imported as one",
        )
    seen_only = bool(response.get("seen_no_objection", False))
    require(
        not (delegated and seen_only),
        "A response is either delegated or seen without objection, not both",
    )
    if seen_only:
        require(
            all(a.get("value") == "accept" for a in checked["answers"]),
            "Seeing without objection can only accept; anything else is a judgement "
            "and is imported as one",
        )
    if delegated:
        mode = "delegated"
    elif seen_only:
        mode = "seen_no_objection"
    elif response.get("ai_assisted", False):
        mode = "human_with_ai"
    else:
        mode = "human"
    decisions = []
    for answer in checked["answers"]:
        require(bool(answer.get("reason", "").strip()), "Every research decision needs a reason")
        parents = tuple(answer.get("supersedes", ()))
        require(
            all(
                k in prior and k not in superseded and prior[k].subject == answer["id"]
                for k in parents
            ),
            "Unknown or stale review amendment parent",
        )
        decisions.append(
            ReviewDecision(
                answer["id"],
                subject_digest(registry.subjects()[answer["id"]]),
                answer["value"],
                checked["rater_id"],
                checked["role"],
                response["submitted_at"],
                mode,
                answer["reason"],
                response_id,
                parents,
            )
        )
    result = replace(registry, reviews=(*registry.reviews, *decisions), research_snapshot=None)
    result.check()
    record = {
        "study_id": active["id"],
        "sheet_id": sheet["id"],
        "response": response,
        "decisions": plain(decisions),
        "imported_at": datetime.now(UTC).isoformat(),
    }
    store.put("registry_review_responses", response_id, record)
    path = store.put("registry_drafts", result.revision, result)
    return {
        "registry": str(path),
        "registry_revision": result.revision,
        "response_id": response_id,
        "decisions": len(decisions),
        "unanswered": checked["missing"],
    }


def verify_reviews(store, active, registry):
    for decision in registry.reviews:
        response = store.get("registry_review_responses", decision.response_id)
        require(
            response is not None
            and response["study_id"] == active["id"]
            and plain(decision) in response["decisions"],
            "Human decision has no matching imported response",
        )


def amend_parent(store, active, kind, parent, reason, registry=None):
    snapshots = {digest(s): s for s in store.all(kind) if s["study_id"] == active["id"]}
    parents = {s.get("parent") for s in snapshots.values()}
    heads = set(snapshots) - parents
    require(
        not snapshots or (parent in heads and bool(reason)),
        "A new snapshot needs its current parent and an amendment reason",
    )
    require(parent is None or parent in snapshots, "Unknown snapshot parent")
    if registry is not None:
        for snapshot in snapshots.values():
            for old in snapshot["registry"]["constructs"]:
                for current in registry.constructs:
                    if (
                        current.id == old["id"]
                        and old.get("origin", "unclassified") != "unclassified"
                    ):
                        require(
                            (current.origin, current.origin_reference)
                            == (old["origin"], old.get("origin_reference", "")),
                            "Historical origin cannot be rewritten; preserve the original record",
                        )


def origin_inputs(store, active):
    inputs = {"proposal:" + p["id"]: p for p in active["prior_proposals"]["proposals"]}
    inputs.update(
        {r["reference"]: r for r in store.all("research_inputs") if r["study_id"] == active["id"]}
    )
    return inputs


def record_input(store, active, value):
    require(value.get("kind") in ("proposal", "observation"), "Unknown development input kind")
    require(
        all(value.get(k) for k in ("id", "content", "attribution", "rationale")),
        "Development input needs content, attribution and a rationale",
    )
    record = {**value, "study_id": active["id"], "recorded_at": datetime.now(UTC).isoformat()}
    reference = value["kind"] + ":" + digest(record)
    record["reference"] = reference
    path = store.put("research_inputs", digest(record), record)
    return {
        "reference": reference,
        "artifact_digest": digest(record),
        "artifact": str(path),
        "status": "proposal_not_validation",
    }


def verify_sources(store, active, registry):
    from .research import current_decisions
    from .research_review import flat

    decisions = current_decisions(store, active)
    title_included = {
        d["record_id"]
        for d in decisions
        if d["stage"] == "title_abstract" and d["decision"] == "include"
    }
    included = {
        d["record_id"]
        for d in decisions
        if d["stage"] == "full_text" and d["decision"] == "include"
    } & title_included
    inputs = origin_inputs(store, active)
    for c in registry.constructs:
        if c.origin == "literature":
            require(
                c.origin_reference.startswith("extraction:"), "Literature origin lacks extraction"
            )
            extract = store.get(
                "research_extractions", c.origin_reference.removeprefix("extraction:")
            )
            require(
                extract is not None
                and extract["study_id"] == active["id"]
                and extract["record_id"] in included,
                "Origin extraction lacks included source",
            )
        elif c.origin in ("prior_proposal", "inductive"):
            prefix = "proposal:" if c.origin == "prior_proposal" else "observation:"
            require(
                c.origin_reference.startswith(prefix) and c.origin_reference in inputs,
                "Unknown expert or empirical origin record",
            )
        else:
            require(False, "Unclassified construct origin")
    for source in registry.sources:
        if source.layer in ("expert", "inductive"):
            require(source.locator in inputs, "Local evidence lacks its recorded input")
            local = inputs[source.locator]
            for evidence in (e for e in registry.evidence if e.source_id == source.id):
                require(
                    evidence.source_artifact_digest == digest(local)
                    and bool(evidence.excerpt)
                    and evidence.excerpt in json.dumps(local, ensure_ascii=False),
                    "Local evidence does not match its recorded input",
                )
            continue
        require(source.id in included, "Literature evidence lacks a full-text inclusion decision")
        for evidence in (e for e in registry.evidence if e.source_id == source.id):
            require(
                bool(evidence.excerpt and evidence.source_artifact_digest)
                and any(
                    r["study_id"] == active["id"]
                    and r["record_id"] == source.id
                    and r["full_text_digest"] == evidence.source_artifact_digest
                    and flat(evidence.excerpt) in flat(r["source_text"])
                    for r in store.all("research_extraction_requests")
                ),
                "Evidence does not match a supplied source passage",
            )


def freeze_instrument(store, active, raw, parent=None, reason=""):
    registry = load_registry(raw, pilot=True)
    require(
        registry.protocol_revision == active["protocol_revision"], "Different research protocol"
    )
    verify_reviews(store, active, registry)
    verify_sources(store, active, registry)
    amend_parent(store, active, "instrument_snapshots", parent, reason, registry)
    registry = replace(registry, research_snapshot=None)
    snapshot = {
        "study_id": active["id"],
        "registry": plain(registry),
        "parent": parent,
        "amendment_reason": reason,
        "recorded_at": datetime.now(UTC).isoformat(),
        "status": "development_instrument_not_clinically_validated",
        "delegated_reviews": list(registry.delegated_subjects()),
        "delegated_note": (
            "these subjects were accepted on the assistant's reading by a recorded "
            "delegation and are not human-verified item by item"
            if registry.delegated_subjects()
            else None
        ),
        "seen_without_objection": list(registry.seen_subjects()),
        "seen_note": (
            "the reviewer opened each of these subjects and accepted it without "
            "objecting, and does not stand behind those acceptances as judgements; "
            "they are not human-verified and nothing may be reported as reviewed "
            "on their account"
            if registry.seen_subjects()
            else None
        ),
        "unverified_subjects": list(registry.unverified_subjects()),
    }
    key = digest(snapshot)
    store.put("instrument_snapshots", key, snapshot)
    final = replace(registry, research_snapshot=key)
    path = store.put("registries", final.revision, final)
    return {"snapshot_id": key, "registry": str(path), "registry_revision": final.revision}


def verify_snapshot(store, registry):
    from .research import study

    require(bool(registry.research_snapshot), "Pilot needs its exact reviewed instrument snapshot")
    snapshot = store.get("instrument_snapshots", registry.research_snapshot)
    require(
        snapshot is not None and digest(snapshot) == registry.research_snapshot,
        "Missing instrument snapshot",
    )
    require(
        snapshot["registry"] == plain(replace(registry, research_snapshot=None)),
        "Instrument differs from its frozen revision",
    )
    active = study(store, snapshot["study_id"])
    require(registry.protocol_revision == active["protocol_revision"], "Changed protocol")
    verify_reviews(store, active, registry)
    verify_sources(store, active, registry)
    return active


def compare_proposals(store, active, literature_id=None, registry_raw=None):
    if literature_id:
        snapshot = store.get("literature_freezes", literature_id)
        require(
            snapshot is not None and snapshot["study_id"] == active["id"],
            "Unknown literature snapshot",
        )
        registry_raw = snapshot["registry"]
    registry = load_registry(registry_raw) if registry_raw else None
    require(
        registry is None or registry.protocol_revision == active["protocol_revision"],
        "Different proposal-comparison protocol",
    )
    result = {
        "study_id": active["id"],
        "literature_id": literature_id,
        "registry": plain(registry) if registry else None,
        "recorded_at": datetime.now(UTC).isoformat(),
        "comparisons": [
            {
                "reference": key,
                "proposal": value,
                "matched_constructs": [],
                "decision": "pending_human_review",
                "reason": "",
                "origin_if_added": "prior_proposal" if key.startswith("proposal:") else "inductive",
            }
            for key, value in origin_inputs(store, active).items()
        ],
    }
    store.put("proposal_comparisons", digest(result), result)
    return result


def import_proposal_decisions(store, active, comparison_id, response):
    comparison = store.get("proposal_comparisons", comparison_id)
    require(
        comparison is not None and comparison["study_id"] == active["id"],
        "Unknown proposal comparison",
    )
    require(response.get("comparison_id") == comparison_id, "Stale proposal response")
    require(
        response.get("mode") in ("human", "human_with_ai")
        and all(response.get(k) for k in ("reviewer", "role", "decided_at")),
        "Proposal decisions need actual human provenance",
    )
    choices = {p["reference"] for p in comparison["comparisons"]}
    decisions = response.get("decisions", [])
    require(
        len({d["reference"] for d in decisions}) == len(decisions), "Duplicate proposal decision"
    )
    for decision in decisions:
        require(
            decision.get("reference") in choices
            and decision.get("decision") in ("accept", "exclude", "merge", "revise", "unresolved")
            and bool(decision.get("reason")),
            "Invalid proposal decision",
        )
        targets = {c["id"] for c in (comparison["registry"] or {}).get("constructs", [])}
        require(set(decision.get("matched_constructs", [])) <= targets, "Unknown matched construct")
        require(
            decision["decision"] != "merge" or bool(decision.get("matched_constructs")),
            "A merge needs exact target constructs",
        )
    previous = [r for r in store.all("proposal_decisions") if r["comparison_id"] == comparison_id]
    superseded = {r.get("supersedes") for r in previous}
    if previous:
        require(
            response.get("supersedes") in {digest(r) for r in previous} - superseded
            and response.get("amendment_reason"),
            "Proposal amendment needs current parent and reason",
        )
    record = {**response, "study_id": active["id"], "imported_at": datetime.now(UTC).isoformat()}
    store.put("proposal_decisions", digest(record), record)
    return {
        "decision_id": digest(record),
        "decided": len(decisions),
        "pending": len(choices) - len(decisions),
        "registry_changed": False,
    }


def public_protocol_bundle(store, active):
    """Stage a shareable protocol, excluding inputs, excerpts, reviews and clinical derivatives."""
    from .research import review_status

    # Registration is a fact about the protocol, read from it: an export that
    # hard-codes "not registered" would keep saying so after a registration.
    registration = {"external_timestamp": None, **active["protocol"].get("registration", {})}
    require(
        registration.get("status") == "not_registered"
        or bool(registration.get("external_timestamp")),
        "A registered protocol needs its external registration timestamp",
    )
    result = {
        "protocol": active["protocol"],
        "queries": active["queries"],
        "protocol_revision": active["protocol_revision"],
        "prepared_at": active["recorded_at"],
        "study_id": active["id"],
        "review_status": review_status(store, active),
        "prior_input_count": len(origin_inputs(store, active)),
        "registration": registration,
        "release_status": "staged_for_human_disclosure_review_not_published",
    }
    path = store.put("protocol_exports", digest(result), result)
    return {
        "export": str(path),
        "published": False,
        "registered": registration["status"] != "not_registered",
    }
