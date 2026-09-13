"""Source preparation, generation, extraction and independent evaluation stages."""

from __future__ import annotations

import re
from dataclasses import replace

from . import prompts
from .schema import (
    Bank,
    Case,
    CitationVerdict,
    DimensionVerdict,
    Evaluation,
    Manifest,
    Note,
    NoteAnswer,
    NoteSpec,
    QAVerdict,
    Segmentation,
    ValidationError,
    decode,
    digest,
    plain,
    require,
)
from .storage import Runner


def prepare(case: Case, runner: Runner, instrument=None) -> Bank:
    require(
        case.origin == "synthetic" or instrument is not None,
        "Research source preparation requires explicit reviewed criteria",
    )
    if instrument is not None:
        instrument.check(pilot=True)

    def parse(raw):
        bank = decode(
            Bank,
            {
                **raw,
                "case_id": case.id,
                "case_revision": case.revision,
                "author": plain(runner.identity),
                "research_revision": instrument.revision
                if instrument
                else "development-default-v3",
            },
        )
        bank.check(case)
        return bank

    raw = (
        runner.ask(case, "prepare", prompts.prepare(case, instrument), parse)
        if instrument is None or "qa" in instrument.methods
        else {"information": [], "questions": []}
    )
    bank = parse(raw)
    runner.store.put("banks", bank.revision, bank)
    return bank


def generate(case: Case, spec: NoteSpec, runner: Runner) -> Note:
    require(spec.language == case.language, "Cross-language generation is not this protocol")

    def parse(raw):
        require(set(raw) == {"text"} and isinstance(raw["text"], str), "Invalid note response")

    raw = runner.ask(case, "generate", prompts.generate(case, spec), parse)
    note = Note(
        "n-" + digest((case.revision, spec, runner.identity))[:24],
        case.id,
        case.revision,
        runner.identity,
        spec,
        raw["text"],
    )
    runner.store.put("notes", note.revision, note)
    return note


def segment(case: Case, note: Note, runner: Runner) -> Segmentation:
    note.check(case)

    def parse(raw):
        out = decode(
            Segmentation,
            {
                **raw,
                "note_id": note.id,
                "note_revision": note.revision,
                "extractor": plain(runner.identity),
            },
        )
        out.check(note)
        return out

    raw = (
        runner.ask(case, "segment", prompts.segment(note), parse)
        if note.text.strip()
        else {"claims": [], "nonclaims": []}
    )
    out = parse(raw)
    runner.store.put("segmentations", out.revision, out)
    return out


def retrieve(case: Case, query: str, count: int) -> set[tuple[str, str]]:
    """A deterministic lexical baseline; candidate retrieval is not entailment."""
    terms = set(re.findall(r"\w+", query.casefold()))
    turns = [(s.id, t) for s in case.sources for t in s.turns]
    ranked = sorted(
        enumerate(turns),
        key=lambda pair: (
            -len(terms & set(re.findall(r"\w+", pair[1][1].text.casefold()))),
            pair[0],
        ),
    )
    return {(sid, turn.id) for _, (sid, turn) in ranked[:count]}


def score(
    case: Case,
    note: Note,
    bank: Bank,
    segmentation: Segmentation,
    manifest: Manifest,
    runner: Runner,
) -> Evaluation:
    bank.check(case)
    note.check(case)
    segmentation.check(note)
    manifest.check(case, bank, note, segmentation)
    require(manifest.judge == runner.identity, "Judge differs from manifest")
    require(manifest.replicate_id == runner.replicate_id, "Replicate differs from manifest")
    case.authorize(runner.identity.provider)
    if case.origin != "synthetic":
        from .registry import load_registry

        raw_registry = runner.store.get("registries", manifest.research_revision)
        require(raw_registry is not None, "Research run lacks its reviewed registry artifact")
        registry = load_registry(raw_registry, pilot=True)
        registry.check_language(case.language)
        require(
            registry.revision == manifest.research_revision
            and registry.measurements == manifest.measurements
            and registry.method_specs == manifest.method_specs
            and registry.methods == manifest.methods
            and registry.required_methods == manifest.required_methods
            and registry.assessment_scope == manifest.assessment_scope,
            "Manifest differs from reviewed research instrument",
        )
        # Two conditions, two messages. Joined, an instrument that had passed
        # review but carried one unreviewed measurement failed with "legacy
        # defaults are demo-only", which sends the reader to the wrong file.
        require(
            manifest.research_revision != "development-default-v3",
            "Real research runs require a reviewed registry; legacy defaults are demo-only",
        )
        unreviewed = [m.id for m in manifest.measurements if m.status != "pilot_reviewed"]
        require(
            not unreviewed,
            "Real research runs require every measurement to be pilot_reviewed; "
            f"not reviewed: {', '.join(unreviewed)}",
        )
    selected = (
        retrieve(case, note.text, manifest.retrieval_turns)
        if manifest.source_mode == "retrieved"
        else None
    )
    use_qa, use_claims = "qa" in manifest.methods, "claims" in manifest.methods
    active_items = manifest.measurements if "items" in manifest.methods else ()
    need_source = (
        use_claims
        or "citations" in manifest.methods
        or any(m.reference_mode == "source" for m in active_items)
    )
    result = Evaluation(
        case.id,
        note.id,
        note.revision,
        bank.revision,
        segmentation.revision,
        runner.identity,
        source_mode=manifest.source_mode,
        retrieved_sources=tuple(sorted(digest(pair) for pair in selected or ())),
        manifest_id=manifest.id,
        measurements=manifest.measurements,
        research_revision=manifest.research_revision,
        case_revision=case.revision,
        methods=manifest.methods,
        assessment_scope=manifest.assessment_scope,
        required_methods=manifest.required_methods,
        method_specs=manifest.method_specs,
        replicate_id=manifest.replicate_id,
    )
    if not note.text.strip():
        # These are observed absences, not missing judge calls. Precision remains
        # undefined. Usability/dimensions remain unassessed rather than perfect.
        result = replace(
            result,
            segmentation_complete=True if use_claims else None,
            answers=tuple(
                NoteAnswer(q.id, "not_in_note", "", ())
                for q in bank.questions
                if q.primary and use_qa
            ),
            qa=tuple(
                QAVerdict(
                    i.id,
                    "omitted",
                    "critical"
                    if i.critical and i.relevance[note.spec.profile].importance == "essential"
                    else "none",
                    (),
                    "Empty note",
                )
                for i in bank.information
                if use_qa
            ),
        )
    else:

        def answers(raw):
            require(set(raw) == {"answers"}, "Invalid note-answer response")
            out = replace(result, answers=decode(tuple[NoteAnswer, ...], raw["answers"]))
            out.check(case, note, bank, segmentation)
            require(
                {a.question_id for a in out.answers} == {q.id for q in bank.questions if q.primary},
                "Note-only QA is incomplete",
            )
            return out

        if use_qa:
            try:
                result = answers(runner.ask(case, "answer", prompts.answer(note, bank), answers))
            except ValidationError:
                result = replace(result, failures=(*result.failures, "note_answer_failed"))

        if result.answers:

            def compare(raw):
                require(set(raw) == {"qa"}, "Invalid answer-comparison response")
                out = replace(result, qa=decode(tuple[QAVerdict, ...], raw["qa"]))
                out.check(case, note, bank, segmentation)
                require(
                    len(out.qa) == len(bank.information),
                    "QA comparison is incomplete",
                )
                answer_by_question = {a.question_id: a for a in result.answers}
                for verdict in out.qa:
                    primary = next(
                        q
                        for q in bank.questions
                        if q.primary and q.information_id == verdict.information_id
                    )
                    answer = answer_by_question[primary.id]
                    require(
                        verdict.verdict != "preserved" or answer.status == "answered",
                        "No preservation credit without a note answer",
                    )
                    require(
                        verdict.verdict not in ("preserved", "unassessable")
                        or verdict.severity == "none",
                        "Invalid QA error severity",
                    )
                return out

            try:
                result = compare(
                    runner.ask(
                        case,
                        "compare",
                        prompts.compare(note, bank, plain(result.answers), manifest.method_specs),
                        compare,
                    )
                )
            except ValidationError:
                result = replace(result, failures=(*result.failures, "qa_comparison_failed"))

        def verify(raw):
            require(
                set(raw)
                in (
                    {"claims", "dimensions", "segmentation_complete"},
                    {"claims", "dimensions", "segmentation_complete", "citations"},
                ),
                "Invalid verification response",
            )
            out = decode(Evaluation, {**plain(result), **raw})
            if selected is not None:
                # A retrieval miss is an evidence gap for this claim, not failure of every item.
                out = replace(
                    out,
                    claims=tuple(
                        replace(
                            c,
                            verdict="unassessable",
                            severity="none",
                            error_types=(),
                            rationale="Insufficient retrieved evidence",
                        )
                        if c.verdict == "unsupported"
                        else c
                        for c in out.claims
                    ),
                )
            out.check(case, note, bank, segmentation)
            expected_items = {
                m.id
                for m in active_items
                if m.reference_mode == "source" and note.spec.profile in m.profiles
            }
            require(
                len(out.claims) == (len(segmentation.claims) if use_claims else 0)
                and {v.dimension for v in out.dimensions} == expected_items
                and (
                    out.segmentation_complete is not None
                    if use_claims
                    else out.segmentation_complete is None
                ),
                "Verification is incomplete",
            )
            if selected is not None:
                require(
                    all(
                        (e.source_id, e.span.unit_id) in selected
                        for c in out.claims
                        for e in c.evidence
                    ),
                    "A citation points outside the retrieved context",
                )
            return out

        if need_source:
            try:
                result = verify(
                    runner.ask(
                        case,
                        "verify",
                        prompts.verify(
                            case,
                            note,
                            segmentation,
                            bank,
                            selected,
                            active_items,
                            check_claims=use_claims,
                            check_citations="citations" in manifest.methods,
                            method_specs=manifest.method_specs,
                        ),
                        verify,
                    )
                )
            except ValidationError:
                result = replace(result, failures=(*result.failures, "verification_failed"))
        for mode in ("note_only", "norm"):
            items = tuple(
                m
                for m in active_items
                if m.reference_mode == mode and note.spec.profile in m.profiles
            )
            if not items:
                continue

            def assess(raw, items=items, base=result):
                require(set(raw) == {"dimensions"}, "Invalid item assessment response")
                values = decode(tuple[DimensionVerdict, ...], raw["dimensions"])
                require(
                    {v.dimension for v in values} == {m.id for m in items},
                    "Incomplete item assessment",
                )
                out = replace(base, dimensions=(*base.dimensions, *values))
                out.check(case, note, bank, segmentation)
                return out

            try:
                result = assess(
                    runner.ask(
                        case, mode, prompts.assess_items(note, items, manifest.method_specs), assess
                    )
                )
            except ValidationError:
                result = replace(result, failures=(*result.failures, mode + "_assessment_failed"))
    from .citations import extract

    # Invalid reference syntax targets and word counts need no model judgment.
    invalid = {
        c["id"] for c in extract(note, case) if not c["valid"] and "citations" in manifest.methods
    }
    result = replace(
        result,
        citations=result.citations
        + tuple(
            CitationVerdict(k, "invalid")
            for k in sorted(invalid)
            if k not in {c.citation_id for c in result.citations}
        ),
    )
    from .deterministic import violations

    for item_id, failed_checks in violations(note, active_items).items():
        result = replace(
            result,
            dimensions=tuple(d for d in result.dimensions if d.dimension != item_id)
            + (
                DimensionVerdict(
                    item_id,
                    "fail",
                    "minor",
                    (),
                    "Deterministic violation: " + ", ".join(failed_checks),
                ),
            ),
        )
    result.check(case, note, bank, segmentation)
    runner.store.put("manifests", manifest.id, manifest)
    runner.store.put("evaluations", digest(result), result)
    return result
