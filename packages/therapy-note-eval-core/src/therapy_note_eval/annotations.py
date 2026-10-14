"""Blinded local review, append-only responses and balanced pair selection."""

from __future__ import annotations

import itertools
from collections import Counter, defaultdict

from .metrics import validation_metrics
from .profiles import instructions
from .schema import (
    IMPORTANCE,
    MANDATORY,
    Bank,
    Case,
    Evaluation,
    Note,
    Segmentation,
    default_measurements,
    digest,
    plain,
    require,
)

VERSION = "annotations-v3"
PAIR_CHOICES = ("a_better", "b_better", "both_acceptable", "both_unacceptable", "cannot_decide")
LABELS = {
    "claim": ("supported", "contradicted", "unsupported", "unassessable"),
    "qa": ("preserved", "partial", "omitted", "contradicted", "unassessable"),
    "importance": IMPORTANCE,
    "disclosure": ("retain", "generalize", "omit"),
    "segmentation": ("complete_atomic", "missing_claim", "compound_claim", "incorrect_split"),
    "dimension": ("pass", "fail", "unassessable", "not_applicable"),
    "question": ("appropriate", "leading", "ambiguous", "irrelevant", "wrong_answer"),
    "pair": PAIR_CHOICES,
    "severity": ("none", "minor", "major", "critical"),
    "citation": ("supported", "unsupported", "uncertain", "invalid"),
}


def bank_sheet(case: Case, bank: Bank) -> dict:
    """Review source coverage, salience and question quality before note exposure."""
    bank.check(case)
    items = []
    for info in bank.information:
        context = {"source_answer": info.source_answer, "source_evidence": plain(info.evidence)}
        items.append(
            {
                "id": "bank:" + info.id,
                "kind": "claim",
                "profile": "all",
                "text": info.text,
                "context": context,
                "choices": LABELS["claim"],
            }
        )
        for profile in info.relevance:
            for kind in ("importance", "disclosure"):
                items.append(
                    {
                        "id": f"{kind}:{profile}:{info.id}",
                        "kind": kind,
                        "profile": profile,
                        "text": info.text,
                        "context": {},
                        "choices": LABELS[kind],
                    }
                )
        for question in bank.questions:
            if question.information_id == info.id:
                items.append(
                    {
                        "id": "question:" + question.id,
                        "kind": "question",
                        "profile": "all",
                        "text": question.text,
                        "context": context,
                        "choices": LABELS["question"],
                    }
                )
    body = {
        "version": VERSION,
        "language": case.language,
        "profile": "all",
        "cohort": case.cohort,
        "case_revision": case.revision,
        "bank_revision": bank.revision,
        "sources": plain(case.sources),
        "items": items,
        "mode": "independent",
        "stage": "source_bank",
        "missing_information_prompt": "What important information is missing? "
        "Check question coverage, clinical meaning, and language quality.",
    }
    return {**body, "id": digest(body)}


def task_sheet(case: Case, bank: Bank, note: Note) -> tuple[dict, dict]:
    """Note-only information-finding tasks; reference answers stay in a separate key."""
    bank.check(case)
    note.check(case)
    information = {
        i.id: i for i in bank.information if i.relevance[note.spec.profile].importance == MANDATORY
    }
    items = [
        {
            "id": "task:" + q.id,
            "kind": "task",
            "profile": note.spec.profile,
            "text": q.text,
            "context": {},
            "choices": [],
        }
        for q in bank.questions
        if q.primary and q.information_id in information
    ]
    require(bool(items), "No essential information-finding tasks available")
    body = {
        "version": VERSION,
        "language": case.language,
        "profile": note.spec.profile,
        "cohort": case.cohort,
        "case_revision": case.revision,
        "note_revision": note.revision,
        "bank_revision": bank.revision,
        "note": note.text,
        "items": items,
        "mode": "independent",
        "stage": "note_only_task",
        "missing_information_prompt": "Answer from the note only. Say when an answer is "
        "not available. Describe difficulties and record measured time and factual edits.",
    }
    review = {**body, "id": digest(body)}
    lookup = {
        "sheet_id": review["id"],
        "generator": plain(note.generator),
        "references": {
            "task:" + q.id: plain(information[q.information_id])
            for q in bank.questions
            if q.primary and q.information_id in information
        },
    }
    return review, lookup


def sheet(
    case: Case,
    note: Note,
    bank: Bank,
    segmentation: Segmentation,
    evaluation: Evaluation | None = None,
    measurements=None,
    research_revision: str = "development-default-v3",
    methods: tuple[str, ...] = ("qa", "claims", "items", "citations"),
) -> dict:
    """Source and note evidence are visible; no automatic verdict is embedded."""
    bank.check(case)
    note.check(case)
    segmentation.check(note)
    if evaluation:
        evaluation.check(case, note, bank, segmentation)
        measurements = evaluation.measurements
        research_revision = evaluation.research_revision
        methods = evaluation.methods
    measurements = default_measurements() if measurements is None else measurements
    require(
        case.origin == "synthetic" or research_revision != "development-default-v3",
        "Real-note review needs an explicit research registry",
    )
    items = []

    def add(key, kind, text, context, profile=note.spec.profile):
        items.append(
            {
                "id": key,
                "kind": kind,
                "profile": profile,
                "text": text,
                "context": context,
                "choices": LABELS[kind],
            }
        )

    if "claims" in methods:
        add(
            "segmentation",
            "segmentation",
            "Are all assertions represented and atomic?",
            plain(segmentation.claims),
        )
    for claim in segmentation.claims if "claims" in methods else ():
        add("claim:" + claim.id, "claim", claim.text, plain(claim.spans))
        add("severity:claim:" + claim.id, "severity", claim.text, {})
    answers = {a.question_id: a for a in evaluation.answers} if evaluation else {}
    for info in bank.information if "qa" in methods else ():
        add(
            "bank:" + info.id,
            "claim",
            info.text,
            {"source_answer": info.source_answer, "evidence": plain(info.evidence)},
            "all",
        )
        for profile in info.relevance:
            for kind in ("importance", "disclosure"):
                add(f"{kind}:{profile}:{info.id}", kind, info.text, {"purpose": profile}, profile)
        primary = next(q for q in bank.questions if q.primary and q.information_id == info.id)
        context = {
            "source_answer": info.source_answer,
            "source_evidence": plain(info.evidence),
            "note_answer": plain(answers.get(primary.id)),
        }
        add("question:" + primary.id, "question", primary.text, context)
        add("qa:" + info.id, "qa", primary.text, context)
        add("severity:qa:" + info.id, "severity", primary.text, context)
    if "citations" in methods:
        from .citations import extract

        for citation in extract(note, case):
            add(
                "citation:" + citation["id"],
                "citation",
                "Does this authored reference support the cited assertion?",
                citation,
            )
    for definition in measurements if "items" in methods else ():
        if note.spec.profile not in definition.profiles:
            continue
        localized = definition.localized(note.spec.language)
        add("dimension:" + definition.id, "dimension", localized["question"], {})
        items[-1]["choices"] = (*definition.labels, "unassessable", "not_applicable")
        items[-1]["definition"] = localized
    body = {
        "version": VERSION,
        "language": case.language,
        "profile": note.spec.profile,
        "cohort": case.cohort,
        "case_revision": case.revision,
        "note_revision": note.revision,
        "bank_revision": bank.revision,
        "segmentation_revision": segmentation.revision,
        "measurement_revision": digest(measurements),
        "methods": list(methods),
        "research_revision": research_revision,
        "method_definitions": [m.localized(case.language) for m in evaluation.method_specs]
        if evaluation
        else [],
        "purpose_instructions": instructions(note.spec),
        "rater_provenance_required": True,
        "annotation_support": {
            "automatic_verdict_hidden": True,
            "model_extracted_note_answers_visible": bool(answers),
        },
        "sources": plain(case.sources),
        "note": note.text,
        "items": items,
        "mode": "independent",
        "missing_information_prompt": "What clinically important information or question "
        "is missing from this bank? Include reasons for your judgments.",
    }
    return {**body, "id": digest(body)}


def import_response(review: dict, response: dict) -> dict:
    require(response.get("sheet_id") == review["id"], "Annotation is for a different sheet")
    require(response.get("version") == VERSION, "Unknown annotation version")
    require(
        isinstance(response.get("rater_id"), str) and response["rater_id"].strip(),
        "Rater identity is required",
    )
    require(response.get("mode") == review["mode"], "Independent and adjudicated ratings differ")
    require(
        response.get("role")
        in (
            "therapist",
            "supervisor",
            "client",
            "documentation_specialist",
            "native_speaker",
            "researcher",
        ),
        "Rater role is required",
    )
    items = {i["id"]: i for i in review["items"]}
    require(response.get("instrument_author") in (True, False, None), "Invalid rater provenance")
    seen = set()
    answers = response.get("answers")
    require(isinstance(answers, list), "Annotation answers must be a list")
    for answer in answers:
        key = answer.get("id")
        require(key in items and key not in seen, "Unknown or duplicate annotation unit")
        if items[key]["kind"] == "task":
            require(
                isinstance(answer.get("value"), str) and 0 < len(answer["value"]) <= 32_000,
                "A task answer must be nonempty text",
            )
        else:
            require(answer.get("value") in items[key]["choices"], "Invalid annotation category")
        seen.add(key)
        if items[key].get("require_reason"):
            require(bool(answer.get("reason", "").strip()), "This decision requires a reason")
    for key in ("review_seconds", "factual_edits", "style_edits", "information_found_seconds"):
        value = response.get(key)
        require(
            value is None or (type(value) in (int, float) and 0 <= value < 1e9),
            "Invalid usability observation",
        )
    return {
        **response,
        "expected": len(items),
        "answered": len(seen),
        "missing": len(items) - len(seen),
        "language": review["language"],
        "profile": review["profile"],
        "cohort": review["cohort"],
        "instrument_author": response.get("instrument_author"),
        "annotation_support": review.get("annotation_support", {}),
        "provenance_status": "declared"
        if type(response.get("instrument_author")) is bool
        else "not_declared",
        "status": "Human observations attached; author review is not external validation.",
    }


def adjudication_sheet(review: dict, responses: list[dict]) -> dict:
    ratings = [import_response(review, r) for r in responses]
    require(all(r["mode"] == "independent" for r in ratings), "Use independent initial ratings")
    require(len({r["rater_id"] for r in ratings}) >= 2, "Adjudication needs two independent raters")
    require(len({r["rater_id"] for r in ratings}) == len(ratings), "Duplicate initial rater")
    items = []
    for item in review["items"]:
        votes = [
            {"rater": r["rater_id"], "value": a["value"]}
            for r in ratings
            for a in r["answers"]
            if a["id"] == item["id"]
        ]
        if len(votes) < len(ratings) or len({v["value"] for v in votes}) > 1:
            items.append({**item, "human_votes": votes})
    body = {**review, "parent_sheet": review["id"], "mode": "adjudication", "items": items}
    body.pop("id")
    return {**body, "id": digest(body)}


def agreement(review: dict, responses: list[dict]) -> dict:
    ratings = [import_response(review, r) for r in responses]
    independent = [r for r in ratings if r["mode"] == "independent"]
    require(
        len({r["rater_id"] for r in independent}) == len(independent),
        "Repeated responses from a rater are not independent observations",
    )
    groups = defaultdict(list)
    for a, b in itertools.combinations(independent, 2):
        left = {r["id"]: r["value"] for r in a["answers"]}
        right = {r["id"]: r["value"] for r in b["answers"]}
        for item in review["items"]:
            if item["id"] in left and item["id"] in right:
                groups[(measurement_group(item), item["profile"])].append(
                    (left[item["id"]], right[item["id"]])
                )
    return {
        "sheet_id": review["id"],
        "language": review["language"],
        "cohort": review["cohort"],
        "rater_count": len(independent),
        "coverage": [
            {"rater": r["rater_id"], "answered": r["answered"], "expected": r["expected"]}
            for r in ratings
        ],
        "by_kind_and_profile": {
            "/".join(k): validation_metrics(v, positive_label(review, k[0]))
            for k, v in groups.items()
        },
        "status": "Pilot agreement. Correlated items do not form independent clinical samples.",
    }


def compare_to_judge(review: dict, response: dict, evaluation: Evaluation) -> dict:
    """Attach calibration to exact note/bank versions without exposing predictions in the sheet."""
    checked = import_response(review, response)
    require(
        review["note_revision"] == evaluation.note_revision
        and review["bank_revision"] == evaluation.bank_revision
        and review["segmentation_revision"] == evaluation.segmentation_revision
        and review["case_revision"] == evaluation.case_revision
        and review["measurement_revision"] == digest(evaluation.measurements)
        and review["research_revision"] == evaluation.research_revision
        and tuple(review["methods"]) == evaluation.methods,
        "Human and automatic ratings refer to different material",
    )
    predicted = {"claim:" + c.claim_id: c.verdict for c in evaluation.claims}
    predicted.update({"qa:" + q.information_id: q.verdict for q in evaluation.qa})
    predicted.update(
        {
            "dimension:" + d.dimension: d.value if d.verdict == "rated" else d.verdict
            for d in evaluation.dimensions
        }
    )
    predicted.update({"severity:claim:" + c.claim_id: c.severity for c in evaluation.claims})
    predicted.update({"severity:qa:" + q.information_id: q.severity for q in evaluation.qa})
    predicted.update({"citation:" + c.citation_id: c.verdict for c in evaluation.citations})
    kinds = {i["id"]: measurement_group(i) for i in review["items"]}
    grouped = defaultdict(list)
    for answer in checked["answers"]:
        if answer["id"] in predicted:
            grouped[kinds[answer["id"]]].append((answer["value"], predicted[answer["id"]]))
    return {
        "sheet_id": review["id"],
        "judge": plain(evaluation.judge),
        "rater": checked["rater_id"],
        "mode": checked["mode"],
        "instrument_author": checked["instrument_author"],
        "language": review["language"],
        "profile": review["profile"],
        "cohort": review["cohort"],
        "by_kind": {
            k: validation_metrics(v, positive_label(review, k)) for k, v in grouped.items()
        },
        "status": "Pilot comparison to this rater; not independent validation of all profiles.",
    }


def measurement_group(item: dict) -> str:
    return item["id"] if item["kind"] == "dimension" else item["kind"]


def positive_label(review: dict, group: str) -> str:
    choices = next(i["choices"] for i in review["items"] if measurement_group(i) == group)
    return "critical" if group == "severity" else "fail" if "fail" in choices else choices[0]


def pair_sheet(cases: dict[str, Case], notes: list[Note], maximum: int = 50, seed: int = 20260911):
    require(bool(notes) and maximum > 0, "No candidate pairs")
    contexts = {(cases[n.case_id].cohort, cases[n.case_id].split, digest(n.spec)) for n in notes}
    require(len(contexts) == 1, "Pairwise study must have one cohort, split, purpose and format")
    roster = sorted({n.generator.key for n in notes})
    require(maximum >= max(1, len(roster) - 1), "Pair budget cannot connect the model roster")
    candidates = [
        (a, b)
        for a, b in itertools.combinations(notes, 2)
        if a.case_id == b.case_id and a.generator.key != b.generator.key
    ]
    candidates.sort(key=lambda pair: digest((seed, pair[0].revision, pair[1].revision)))
    counts, pair_counts = Counter(), Counter()
    components = {m: m for m in roster}

    def root(model):
        while components[model] != model:
            model = components[model]
        return model

    chosen = []
    while candidates and len(chosen) < maximum:

        def priority(pair):
            a, b = pair[0].generator.key, pair[1].generator.key
            return (
                root(a) == root(b),
                max(counts[a], counts[b]),
                counts[a] + counts[b],
                pair_counts[tuple(sorted((a, b)))],
            )

        a, b = min(candidates, key=priority)
        candidates.remove((a, b))
        ka, kb = a.generator.key, b.generator.key
        components[root(ka)] = root(kb)
        counts.update((ka, kb))
        pair_counts[tuple(sorted((ka, kb)))] += 1
        # Alternation avoids a fixed model always appearing on the left.
        if len(chosen) % 2:
            a, b = b, a
        chosen.append((a, b))
    require(len({root(m) for m in roster}) == 1, "Available paired cases do not connect the roster")
    body = {
        "version": VERSION,
        "mode": "independent",
        "language": notes[0].spec.language,
        "profile": notes[0].spec.profile,
        "cohort": cases[notes[0].case_id].cohort,
        "note": "",
        "sources": [],
        "items": [
            {
                "id": digest((a.revision, b.revision)),
                "kind": "pair",
                "profile": a.spec.profile,
                "text": "Which note serves this purpose better?",
                "choices": PAIR_CHOICES,
                "context": {"A": a.text, "B": b.text, "sources": plain(cases[a.case_id].sources)},
            }
            for a, b in chosen
        ],
        "missing_information_prompt": "Explain clinically meaningful reasons for your choices.",
    }
    review = {**body, "id": digest(body)}
    # Identity lookup is stored separately and never embedded in the blinded page.
    key = {
        item["id"]: {"A": a.generator.key, "B": b.generator.key, "case": a.case_id}
        for item, (a, b) in zip(review["items"], chosen, strict=True)
    }
    return review, {"lookup": key, "model_appearances": dict(counts), "connected": True}


def pair_results(review: dict, lookup: dict, responses: list[dict]) -> dict:
    outcomes = defaultdict(Counter)
    usability = []
    for raw in responses:
        response = import_response(review, raw)
        for answer in response["answers"]:
            pair = lookup["lookup"][answer["id"]]
            value = answer["value"]
            outcomes[pair["A"]][value] += 1
            reverse = {"a_better": "b_better", "b_better": "a_better"}.get(value, value)
            outcomes[pair["B"]][reverse] += 1
        usability.append(
            {
                k: response.get(k)
                for k in (
                    "review_seconds",
                    "factual_edits",
                    "style_edits",
                    "information_found_seconds",
                )
            }
        )
    return {
        "sheet_id": review["id"],
        "outcomes_by_model": dict(outcomes),
        "usability_observations": usability,
        "model_appearances": lookup["model_appearances"],
        "status": "Descriptive pilot; ties, rejection and indecision remain separate. "
        "No Bradley-Terry ranking is inferred from this small sample.",
    }
