"""Regression and research-provenance tests. Every example and reviewer is synthetic."""

from __future__ import annotations

import json
import uuid
from dataclasses import replace
from pathlib import Path

import pytest
from therapy_note_eval import (
    annotations,
    controls,
    development,
    pipeline,
    report,
    research,
    research_review,
)
from therapy_note_eval.citations import extract
from therapy_note_eval.metrics import measure
from therapy_note_eval.privacy import find_fragments, fingerprints, public_report
from therapy_note_eval.registry import (
    ConstructDefinition,
    EvidenceRecord,
    InstrumentRegistry,
    SupportingSource,
    load_registry,
)
from therapy_note_eval.schema import (
    PROFILES,
    CitationVerdict,
    DimensionVerdict,
    MeasurementSpec,
    MethodSpec,
    Span,
    ValidationError,
    digest,
    plain,
)
from therapy_note_eval.storage import Budget, Runner, Store


@pytest.fixture
def store():
    path = (
        Path(__file__).resolve().parents[1] / "local" / ("gen2-research-test-" + uuid.uuid4().hex)
    )
    path.mkdir(mode=0o777, parents=True)
    return Store(path)


def response(review):
    return {
        "version": annotations.VERSION,
        "sheet_id": review["id"],
        "rater_id": "synthetic-human",
        "role": "researcher",
        "mode": "independent",
        "instrument_author": True,
        "answers": [{"id": "claim:c1", "value": "supported"}],
    }


@pytest.mark.parametrize(
    "field",
    [
        "case_revision",
        "note_revision",
        "bank_revision",
        "segmentation_revision",
        "research_revision",
    ],
)
def test_calibration_rejects_every_stale_binding(field):
    c, b, n, s, _, e = controls.fixture("en", "continuity")
    sheet = annotations.sheet(c, n, b, s, e)
    with pytest.raises(ValidationError):
        annotations.compare_to_judge(sheet, response(sheet), replace(e, **{field: "stale"}))
    changed = replace(
        e,
        measurements=(
            replace(e.measurements[0], definition="Different construct"),
            *e.measurements[1:],
        ),
    )
    with pytest.raises(ValidationError):
        annotations.compare_to_judge(sheet, response(sheet), changed)


@pytest.mark.parametrize(
    "field", ["implementation_digest", "aggregation_version", "prompts_version", "profiles_version"]
)
def test_changed_implementation_cannot_relabel_an_old_run(field):
    c, b, n, s, m, _ = controls.fixture("en", "continuity")
    with pytest.raises(ValidationError):
        replace(m, **{field: "incompatible"}).check(c, b, n, s)


def test_incomplete_segmentation_cannot_produce_perfect_evidence_precision():
    c, b, n, s, _, e = controls.fixture("en", "continuity")
    metrics = measure(c, n, b, s, replace(e, segmentation_complete=False))
    assert metrics["evidence_support"] is None
    assert metrics["faithfulness"] is None
    assert metrics["citation_support"] is None  # No author references at all.


def test_authored_wrong_reference_is_not_the_judges_correct_evidence():
    c, b, n, s, _, e = controls.fixture("en", "continuity", "wrong_citation")
    metrics = measure(c, n, b, s, e)
    assert metrics["faithfulness"] == metrics["evidence_support"] == 1
    assert metrics["citation_validity"] == 1
    assert metrics["citation_support"] == 0


def test_one_assessed_reference_does_not_claim_complete_precision():
    c, b, n, s, _, e = controls.fixture("en", "continuity")
    n = replace(n, text=n.text + " [evidence:current:t0] [evidence:current:t1]")
    s = replace(
        s,
        note_revision=n.revision,
        claims=(replace(s.claims[0], spans=(Span("note", 0, len(n.text), n.text),)),),
    )
    refs = extract(n, c)
    e = replace(
        e,
        note_revision=n.revision,
        segmentation_revision=s.revision,
        citations=(CitationVerdict(refs[0]["id"], "supported", e.claims[0].evidence),),
    )
    metrics = measure(c, n, b, s, e)
    assert metrics["citation_support"] is None
    assert metrics["citation_assessment"]["observed_subset_support"] == 1
    assert metrics["citation_assessment"]["planned"] == 2


def test_word_limit_overrides_an_optimistic_judge():
    c, b, n, s, _, e = controls.fixture("en", "continuity")
    n = replace(n, spec=replace(n.spec, word_limit=1))
    s = replace(s, note_revision=n.revision)
    e = replace(e, note_revision=n.revision, segmentation_revision=s.revision)
    metrics = measure(c, n, b, s, e)
    assert metrics["within_word_limit"] is False
    assert metrics["dimensions"]["instructions"] == "fail"


def test_known_ambiguous_content_is_not_an_api_failure():
    c, b, n, s, _, e = controls.fixture("en", "continuity")
    e = replace(
        e,
        answers=(replace(e.answers[0], status="ambiguous"),),
        qa=(replace(e.qa[0], verdict="partial", severity="minor"),),
    )
    coverage = measure(c, n, b, s, e)["coverage"]["essential"]
    assert coverage["outcomes"] == {"partial": 1}
    assert coverage["missing"] == 0
    assert coverage["ambiguous_note_answers"] == 1


def test_unselected_qa_and_claims_are_not_run_or_presented_as_failures(store):
    c, b, n, s, m, e = controls.fixture("en", "continuity")
    item = replace(e.measurements[2], id="reader_task")
    m = replace(m, measurements=(item,), methods=("items",))

    class Backend:
        identity = controls.FIXTURE_MODEL

        def __init__(self):
            self.prompts = []

        def complete(self, prompt):
            self.prompts.append(prompt)
            return json.dumps(
                {
                    "dimensions": plain(
                        (DimensionVerdict("reader_task", "pass", "none", (), "Synthetic"),)
                    )
                }
            )

    backend = Backend()
    result = pipeline.score(c, n, b, s, m, Runner(backend, store, Budget(1)))
    assert not result.failures and len(backend.prompts) == 1
    assert not result.qa and not result.claims
    assert c.sources[0].turns[1].text not in backend.prompts[0]
    metrics = measure(c, n, b, s, result)
    assert metrics["fully_evaluated"]
    assert metrics["has_critical_error"] is None
    assert "essential_recall" in metrics["not_requested"]


def test_ordinal_registry_reaches_annotation_without_binary_coercion():
    c, b, n, s, _, e = controls.fixture("en", "client")
    item = MeasurementSpec(
        "comprehension",
        "meaning",
        "Degree of understanding",
        "How understandable?",
        "note_only",
        "ordinal",
        ("1", "2", "3"),
        {"1": "Unclear", "2": "Partly clear", "3": "Clear"},
        ("toy-evidence",),
    )
    e = replace(
        e,
        measurements=(item,),
        dimensions=(DimensionVerdict(item.id, "rated", "none", (), "Synthetic", "2"),),
    )
    e.check(c, n, b, s)
    sheet = annotations.sheet(c, n, b, s, e)
    entry = next(i for i in sheet["items"] if i["id"] == "dimension:comprehension")
    assert entry["choices"] == ("1", "2", "3", "unassessable", "not_applicable")
    assert measure(c, n, b, s, e)["measurement_values"][item.id]["value"] == "2"


def test_report_resolves_exact_case_revisions(store):
    c, b, n, s, m, e = controls.fixture("en", "continuity")
    for kind, key, obj in (
        ("cases", c.revision, c),
        ("banks", b.revision, b),
        ("notes", n.revision, n),
        ("segmentations", s.revision, s),
        ("manifests", m.id, m),
        ("evaluations", digest(e), e),
    ):
        store.put(kind, key, obj)
    later = replace(c, group_id="different-ancestry")
    store.put("cases", later.revision, later)
    assert (
        report.build_report(store)["cohorts"][0]["systems"][0]["metrics"]["faithfulness"]["value"]
        == 1
    )


def test_historical_protocol_is_archived_not_recalculated(store):
    *_, m, _ = controls.fixture("en", "continuity")
    old = {**plain(m), "protocol": "gen2-v1"}
    store.put("manifests", digest(old), old)
    payload = report.build_report(store)
    assert not payload["cohorts"]
    assert payload["archived_runs"][0]["manifest_id"] == digest(old)


def test_fragment_scan_includes_escaped_public_strings_and_never_returns_text():
    text = (
        "Synthetic private tokens one two three four five six seven eight nine ten eleven twelve."
    )
    found = find_fragments(json.dumps({"text": text}), {"source-digest": fingerprints(text)})
    assert found == ["source-digest"]
    assert not find_fragments(
        "Unrelated original interface labels", {"source-digest": fingerprints(text)}
    )


def test_public_export_cannot_include_provider_settings_or_free_text(store):
    controls.demo(store)
    payload = report.build_report(store)
    payload["cohorts"][0]["systems"][0]["system"]["settings"]["private_prompt"] = (
        "sensitive-sentinel"
    )
    exported = public_report(payload)
    assert "sensitive-sentinel" not in json.dumps(exported)
    payload["cohorts"][0]["systems"][0]["metrics"]["faithfulness"]["value"] = "sensitive-sentinel"
    with pytest.raises(ValidationError):
        public_report(payload)


def live_protocol() -> dict:
    return json.loads(
        (Path(__file__).resolve().parents[1] / "research/gen2/protocol.json").read_text(
            encoding="utf-8"
        )
    )


def start_review(store, protocol: dict | None = None):
    protocol = protocol or live_protocol()
    queries = {"queries": [{"id": "q1", "database": "PubMed", "query": "toy query"}]}
    proposals = {"proposals": [{"id": "prior", "idea": "PRIOR-SENTINEL-QA-IS-NOT-MANDATORY"}]}
    active = research.initialize(store, protocol, queries, proposals)
    log = {
        "query_id": "q1",
        "database": "PubMed",
        "platform": "fixture",
        "query": "toy query",
        "executed_at": "synthetic-time",
        "status": "completed",
    }
    research.import_records(
        store, active, "title,year,doi\nSynthetic methods paper,2020,10.example/test\n", "csv", log
    )
    record = research.records_for(store, active)[0]
    return active, record


def toy_registry(active, record):
    source = SupportingSource(
        record["id"],
        record["title"],
        "synthetic locator",
        "direct",
        "article",
        "full_text_checked",
        "Test only",
    )
    evidence = EvidenceRecord(
        "ev",
        source.id,
        "synthetic section",
        "Test criterion",
        "direct_validation",
        human_checked_by="synthetic-human",
        source_artifact_digest=digest("Synthetic full text"),
        excerpt="Synthetic full text",
    )
    construct = ConstructDefinition(
        "c",
        "Toy property",
        "Toy definition",
        ("toy",),
        ("ev",),
        {p: "Investigate" for p in PROFILES},
        "note",
        ("note",),
        {
            "positive": "Positive control",
            "negative": "Negative control",
            "boundary": "Boundary control",
        },
        ("binary", "ordinal"),
        "Specified notes",
        "Development only",
        reviewed_by="synthetic-human",
        origin="literature",
    )
    return InstrumentRegistry((source,), (evidence,), (construct,), (), active["protocol_revision"])


def test_new_review_starts_with_no_legacy_constructs(store):
    active, _ = start_review(store)
    pool = store.all("literature_pools")[0]
    assert pool["constructs"] == pool["measurements"] == []
    assert research.review_status(store, active)["screening_pending"] == 1
    with pytest.raises(ValidationError):
        research.compare_proposals(store, active, "not-frozen")


def test_ris_and_nbib_import_preserve_doi_and_continued_titles():
    ris = (
        "TY  - JOUR\nTI  - Example paper\nPY  - 2020\n"
        "DO  - https://doi.org/10.Example/Test\nER  -\n"
    )
    nbib = "PMID- 1\nTI  - Example\n      paper\nDP  - 2020\nAID - 10.Example/Test [doi]\n\n"
    assert research.parse_records(ris, "ris")[0]["doi"] == "10.example/test"
    assert research.parse_records(nbib, "nbib")[0]["title"] == "Example paper"


def test_blocked_search_never_counts_as_completed(store):
    active, _ = start_review(store)
    blocked = {
        "study_id": active["id"],
        "query_id": "q2",
        "status": "blocked",
        "reason": "Synthetic network failure",
    }
    store.put("research_searches", digest(blocked), blocked)
    status = research.review_status(store, active)
    assert status["searches_completed"] == 1
    assert status["records_identified"] == 1


def reviewed_toy(store, active, registry):
    """Import explicitly synthetic human responses through the production review boundary."""
    sheet = development.registry_sheet(store, active, plain(registry))
    raw = {
        **response(sheet),
        "submitted_at": "synthetic-time",
        "answers": [
            {"id": item["id"], "value": "accept", "reason": "Synthetic test decision"}
            for item in sheet["items"]
        ],
    }
    out = development.import_registry_review(store, active, sheet, raw)
    return load_registry(json.loads(Path(out["registry"]).read_text(encoding="utf-8")))


def source_origin(store, active, request, registry):
    out = research_review.import_extraction(
        store,
        active,
        digest(request),
        [
            {
                "source_location": "synthetic section",
                "exact_quote": "Synthetic full text",
                "construct_name": "Toy property",
                "definition": "Toy definition",
            }
        ],
    )
    return replace(
        registry,
        constructs=(
            replace(registry.constructs[0], origin_reference="extraction:" + out["extraction_id"]),
        ),
    )


def operational_toy(store, active, registry):
    method = MethodSpec(
        "claims",
        ("c",),
        ("ev",),
        "Synthetic claim rules",
        "claim",
        ("source", "note"),
        "All test claims",
        {
            "supported": "Source support",
            "contradicted": "Source contradiction",
            "unsupported": "No source support",
            "unassessable": "Unclear source",
        },
        {k: "Synthetic " + k for k in ("none", "minor", "major", "critical")},
        {
            "cs": {
                "definition": "Synthetic localized rules",
                "outcomes": {
                    "supported": "Supported",
                    "contradicted": "Contradicted",
                    "unsupported": "Unsupported",
                    "unassessable": "Unassessable",
                },
                "severity_rules": {
                    k: "Synthetic " + k for k in ("none", "minor", "major", "critical")
                },
                "applicability": "All test claims",
            }
        },
    )
    registry = replace(
        registry,
        methods=("claims",),
        method_specs=(method,),
        constructs=(
            replace(
                registry.constructs[0],
                status="pilot",
                origin="prior_proposal",
                origin_reference="proposal:prior",
            ),
        ),
        assessment_scope="test-claims",
        required_methods=("claims",),
    )
    return reviewed_toy(store, active, registry)


def test_literature_extraction_snapshot_and_proposal_comparison_are_traceable(store):
    active, record = start_review(store)
    registry = toy_registry(active, record)
    with pytest.raises(ValidationError):
        research.extraction_prompt(store, active, record["id"], "Synthetic full text")
    research.screen(
        store,
        active,
        [
            {
                "record_id": record["id"],
                "stage": "title_abstract",
                "decision": "include",
                "mode": "human",
                "reviewer": "synthetic-human",
                "decided_at": "test",
            },
            {
                "record_id": record["id"],
                "stage": "full_text",
                "decision": "include",
                "mode": "human",
                "reviewer": "synthetic-human",
                "decided_at": "test",
            },
        ],
    )
    request = research.extraction_prompt(store, active, record["id"], "Synthetic full text")
    assert "PRIOR-SENTINEL" not in request["prompt"]
    assert "clinical_appropriateness" not in request["prompt"]
    registry = reviewed_toy(store, active, source_origin(store, active, request, registry))
    frozen = research.freeze_literature(store, active, plain(registry), "synthetic-human")
    result = research.compare_proposals(store, active, frozen["literature_id"])
    assert result["comparisons"][0]["origin_if_added"] == "prior_proposal"
    assert result["comparisons"][0]["decision"] == "pending_human_review"


def test_prior_proposal_cannot_be_part_of_the_initial_literature_freeze(store):
    active, record = start_review(store)
    registry = toy_registry(active, record)
    registry = replace(
        registry, constructs=(replace(registry.constructs[0], origin="prior_proposal"),)
    )
    with pytest.raises(ValidationError):
        research.freeze_literature(store, active, plain(registry), "synthetic-human")
    with pytest.raises(ValidationError):
        registry.check(pilot=True)


def test_clustering_is_bound_to_definitions_and_embedding_identity(store):
    pytest.importorskip("scipy")
    active, record = start_review(store)
    registry = toy_registry(active, record)
    second = replace(registry.constructs[0], id="c2", definition="Another definition")
    registry = replace(registry, constructs=(*registry.constructs, second))
    data = {
        "model": "synthetic-vectors",
        "revision": "test",
        "vectors": {
            c.id: {"text_digest": digest(c.definition), "values": v}
            for c, v in zip(registry.constructs, ([1, 0], [0, 1]), strict=True)
        },
    }
    cluster = research.cluster_definitions(registry, data)
    assert cluster["linkage"][0][2] == 1
    assert cluster["review_pairs"][0]["merge"] is None
    data["vectors"]["c"]["text_digest"] = "stale"
    with pytest.raises(ValidationError):
        research.cluster_definitions(registry, data)


def include_source(store, active, record):
    research.screen(
        store,
        active,
        [
            {
                "record_id": record["id"],
                "stage": stage,
                "decision": "include",
                "mode": "human",
                "reviewer": "synthetic-human",
                "decided_at": "test",
            }
            for stage in ("title_abstract", "full_text")
        ],
    )


def test_source_span_extraction_builds_unreviewed_pool_without_prior_fields(store):
    active, record = start_review(store)
    include_source(store, active, record)
    request = research.extraction_prompt(store, active, record["id"], "Synthetic full text")
    entry = {
        "source_location": "test section",
        "exact_quote": "Invented quotation",
        "construct_name": "Source property",
        "definition": "Candidate interpretation",
    }
    with pytest.raises(ValidationError, match="quote"):
        research_review.import_extraction(store, active, digest(request), [entry])
    entry["exact_quote"] = "Synthetic full text"
    research_review.import_extraction(store, active, digest(request), [entry])
    built = research_review.build_pool(store, active)
    raw = json.loads(Path(built["registry"]).read_text(encoding="utf-8"))
    assert built["constructs"] == 1 and not built["prior_proposals_included"]
    assert raw["constructs"][0]["families"] == []
    assert raw["constructs"][0]["reviewed_by"] is None
    assert raw["measurements"] == []
    assert raw["evidence"][0]["source_artifact_digest"] == digest("Synthetic full text")
    with pytest.raises(ValidationError):
        research.freeze_literature(store, active, raw, "synthetic-human")


def test_screening_requires_stage_order_and_current_amendment_parent(store):
    active, record = start_review(store)
    decision = {
        "record_id": record["id"],
        "stage": "full_text",
        "decision": "include",
        "mode": "human",
        "reviewer": "synthetic-human",
        "decided_at": "test",
    }
    with pytest.raises(ValidationError, match="Title/abstract"):
        research.screen(store, active, [decision])
    decision["stage"] = "title_abstract"
    first = research.screen(store, active, [decision])["decision_ids"][0]
    changed = {
        **decision,
        "decision": "uncertain",
        "supersedes": first,
        "amendment_reason": "Test correction",
    }
    research.screen(store, active, [changed])
    with pytest.raises(ValidationError, match="superseded"):
        research.screen(store, active, [{**changed, "decision": "include"}])


def test_screening_ui_import_records_actual_human_provenance(store):
    active, record = start_review(store)
    sheet = research_review.screening_sheet(store, active, "title_abstract")
    answer = {
        **response(sheet),
        "submitted_at": "synthetic-time",
        "answers": [
            {"id": record["id"], "value": "exclude", "reason": "Synthetic exclusion reason"}
        ],
    }
    result = research_review.import_screening(store, active, sheet, answer)
    saved = store.get("research_decisions", result["decision_ids"][0])
    assert saved["reviewer"] == "synthetic-human" and saved["instrument_author"] is True
    assert saved["decided_at"] == "synthetic-time"
    assert research.review_status(store, active)["screening_pending"] == 0


def test_literature_freeze_cannot_accept_unanchored_or_mistyped_evidence(store):
    active, record = start_review(store)
    include_source(store, active, record)
    research.extraction_prompt(store, active, record["id"], "Synthetic full text")
    registry = toy_registry(active, record)
    for bad in (
        replace(registry, evidence=(replace(registry.evidence[0], excerpt="not in source"),)),
        replace(registry, sources=(replace(registry.sources[0], publication_type="unverified"),)),
    ):
        with pytest.raises(ValidationError):
            research.freeze_literature(store, active, plain(bad), "synthetic-human")


def test_calibration_keeps_distinct_measures_separate():
    c, b, n, s, _, e = controls.fixture("en", "continuity")
    sheet = annotations.sheet(c, n, b, s, e)
    raw = {
        **response(sheet),
        "answers": [
            {"id": "dimension:clinical", "value": "pass"},
            {"id": "dimension:language", "value": "fail"},
        ],
    }
    result = annotations.compare_to_judge(sheet, raw, e)
    assert "dimension" not in result["by_kind"]
    assert result["by_kind"]["dimension:language"]["n"] == 1
    assert result["by_kind"]["dimension:language"]["positive_class"] == "fail"


def test_explicit_heading_and_length_checks_apply_to_custom_item_ids():
    from therapy_note_eval.deterministic import checks

    c, b, n, s, _, e = controls.fixture("en", "continuity")
    n = replace(n, spec=replace(n.spec, required_headings=("Required heading",)))
    s = replace(s, note_revision=n.revision)
    item = replace(e.measurements[-1], id="task_contract")
    e = replace(
        e,
        note_revision=n.revision,
        segmentation_revision=s.revision,
        measurements=(item,),
        dimensions=(DimensionVerdict(item.id, "pass", "none", (), "Test"),),
    )
    assert checks(n)["required_headings"] is False
    assert measure(c, n, b, s, e)["dimensions"]["task_contract"] == "fail"
    assert checks(replace(n, text="## Required heading\n" + n.text))["required_headings"] is True


def test_manifest_allows_explicit_methods_without_generic_items():
    c, b, n, s, m, _ = controls.fixture("en", "continuity")
    replace(m, measurements=(), methods=("claims",)).check(c, b, n, s)
    with pytest.raises(ValidationError, match="research criteria"):
        replace(m, research_revision="other research").check(c, b, n, s)


def test_report_archives_old_implementation_before_resolving_missing_inputs(store):
    *_, manifest, _ = controls.fixture("en", "continuity")
    changed = replace(manifest, implementation_digest="previous-code")
    store.put("manifests", changed.id, changed)
    result = report.build_report(store)
    assert not result["cohorts"]
    assert result["archived_runs"][0]["implementation_digest"] == "previous-code"


def test_overlapping_qa_and_claim_findings_need_reviewed_links():
    from therapy_note_eval.findings import inventory, summarize

    *_, e = controls.fixture("en", "continuity", "negation")
    ids = list(inventory(e))
    assert len(ids) >= 2
    assert summarize(e)["distinct_errors"] is None
    links = {
        "evaluation_revision": digest(e),
        "mode": "human_reviewed",
        "reviewer": "synthetic-human",
        "groups": [{"id": "g1", "finding_ids": ids, "reason": "Same planted negation change"}],
    }
    assert summarize(e, links)["distinct_errors"] == 1
    with pytest.raises(ValidationError):
        summarize(replace(e, research_revision="stale"), links)
    with pytest.raises(ValidationError):
        summarize(e, {**links, "groups": [*links["groups"], {**links["groups"][0], "id": "g2"}]})


def test_balanced_pilot_is_a_plan_not_fabricated_human_data(store):
    from collections import Counter

    from therapy_note_eval.pilot import plan

    active, record = start_review(store)
    instrument = operational_toy(store, active, toy_registry(active, record))
    base, *_ = controls.fixture("en", "continuity")
    cases = []
    for origin, language in (
        ("public_demo", "en"),
        ("translated_demo", "cs"),
        ("native_real", "cs"),
    ):
        for index in range(2):
            cases.append(
                replace(
                    base,
                    id=f"{origin}-{index}",
                    origin=origin,
                    language=language,
                    group_id="native-one-client" if origin == "native_real" else f"pair-{index}",
                    translation_group=None if origin == "native_real" else f"pair-{index}",
                    split="pilot",
                    allowed_providers=("local",),
                )
            )
    models = [
        replace(controls.FIXTURE_MODEL, family=f"family-{i}", model=f"model-{i}") for i in range(2)
    ]
    result = plan(cases, instrument, models, models, 11, protocol=active["protocol"])
    assert len(result["jobs"]) == 48 and len(result["human_note_sample"]) == 24
    assert result["independent_native_client_groups"] == 1
    selected = [j for j in result["jobs"] if j["id"] in result["human_note_sample"]]
    assert set(Counter(j["case_revision"] for j in selected).values()) == {4}
    assert result["human_item_budget"]["blinded_repeats"] == 30
    assert result["human_item_budget"]["unique_decisions"] == 120
    assert "no notes" in result["status"]
    with pytest.raises(ValidationError):
        plan(
            [replace(cases[0], translation_group=None), *cases[1:]],
            instrument,
            models,
            models,
            11,
            protocol=active["protocol"],
        )


@pytest.mark.parametrize("methods", [("qa", "claims"), ("qa", "claims", "citations")])
def test_omitted_methods_cannot_produce_a_complete_negative_critical_finding(methods):
    c, b, n, s, _, e = controls.fixture("en", "continuity")
    e = replace(e, methods=methods, dimensions=(), measurements=())
    result = measure(c, n, b, s, e)
    assert result["has_critical_error"] is None
    assert not result["critical_scope_complete"]
    assert "items" not in result["method_assessment"]
    assert "items" in result["required_methods"]
    scoped = replace(e, assessment_scope="faithfulness-and-content-only", required_methods=methods)
    assert measure(c, n, b, s, scoped)["has_critical_error"] is False


def test_critical_findings_remain_visible_when_other_tasks_fail():
    c, b, n, s, _, e = controls.fixture("en", "continuity", "negation")
    critical = replace(e.claims[0], severity="critical")
    out = measure(c, n, b, s, replace(e, claims=(critical,), failures=("qa_comparison_failed",)))
    assert out["has_critical_error"] is True and not out["critical_scope_complete"]
    assert out["critical_findings_by_method"]["claims"] == 1


def test_clock_times_are_not_authored_references():
    c, _, n, *_ = controls.fixture("en", "continuity")
    refs = extract(replace(n, text="Appointment [10:30] then [11:20]. [evidence:current:t0]"), c)
    assert len(refs) == 1 and refs[0]["valid"]
    assert not extract(replace(n, text="Legacy syntax [current:t0]"), c)


def test_missing_origin_is_unknown_and_names_do_not_establish_review(store):
    active, record = start_review(store)
    raw = plain(toy_registry(active, record))
    del raw["constructs"][0]["origin"]
    registry = load_registry(raw)
    assert registry.constructs[0].origin == "unclassified"
    with pytest.raises(ValidationError):
        registry.check(pilot=True)
    ready = operational_toy(store, active, toy_registry(active, record))
    with pytest.raises(ValidationError):
        replace(ready, reviews=()).check(pilot=True)
    with pytest.raises(ValidationError, match="origin"):
        replace(ready, constructs=(replace(ready.constructs[0], origin="unclassified"),)).check(
            pilot=True
        )


def test_qa_or_claim_only_instrument_cannot_bypass_method_or_czech_reviews(store):
    active, record = start_review(store)
    registry = operational_toy(store, active, toy_registry(active, record))
    registry.check(pilot=True)
    registry.check_language("cs")
    with pytest.raises(ValidationError, match="operational"):
        replace(registry, method_specs=()).check(pilot=True)
    changed = replace(registry.method_specs[0], definition="Changed operational meaning")
    with pytest.raises(ValidationError, match="stale"):
        replace(registry, method_specs=(changed,)).check(pilot=True)
    with pytest.raises(ValidationError, match="Czech"):
        replace(registry, method_specs=(replace(changed, language_variants={}),)).check_language(
            "cs"
        )


def test_proposals_can_be_reviewed_before_any_literature_snapshot(store):
    active, _ = start_review(store)
    compared = research.compare_proposals(store, active)
    raw = {
        "comparison_id": digest(compared),
        "mode": "human",
        "reviewer": "synthetic-human",
        "role": "researcher",
        "decided_at": "synthetic-time",
        "decisions": [
            {
                "reference": "proposal:prior",
                "decision": "revise",
                "reason": "Synthetic operationalization needed",
            }
        ],
    }
    saved = development.import_proposal_decisions(store, active, digest(compared), raw)
    assert saved["decided"] == 1 and not saved["registry_changed"]
    with pytest.raises(ValidationError, match="parent"):
        development.import_proposal_decisions(store, active, digest(compared), raw)
    with pytest.raises(ValidationError, match="Stale"):
        development.import_proposal_decisions(
            store, active, digest(compared), {**raw, "comparison_id": "stale"}
        )
    assert research.review_status(store, active)["proposal_decision_records"] == 1


def test_registry_review_rejects_stale_content_ai_authorship_and_missing_decisions(store):
    active, record = start_review(store)
    registry = operational_toy(store, active, toy_registry(active, record))
    with pytest.raises(ValidationError, match="stale"):
        replace(
            registry, evidence=(replace(registry.evidence[0], interpretation="Changed meaning"),)
        ).check(pilot=True)
    with pytest.raises(ValidationError, match="matching imported"):
        altered = replace(registry.reviews[0], response_id="fictional")
        development.verify_reviews(store, active, replace(registry, reviews=(altered,)))
    sheet = development.registry_sheet(store, active, plain(registry))
    raw = {**response(sheet), "submitted_at": "synthetic-time", "answers": []}
    out = development.import_registry_review(store, active, sheet, raw)
    assert out["decisions"] == 0 and out["unanswered"] == len(sheet["items"])


def test_expert_instrument_snapshot_preserves_origin_and_rejects_silent_amendments(store):
    active, record = start_review(store)
    registry = toy_registry(active, record)
    prior = active["prior_proposals"]["proposals"][0]
    registry = replace(
        registry,
        sources=(
            replace(
                registry.sources[0],
                layer="expert",
                publication_type="expert_proposal",
                verification="local_checked",
                locator="proposal:prior",
            ),
        ),
        evidence=(
            replace(
                registry.evidence[0],
                relationship="hypothesis",
                source_artifact_digest=digest(prior),
                excerpt=prior["idea"],
            ),
        ),
    )
    registry = operational_toy(store, active, registry)
    frozen = development.freeze_instrument(store, active, plain(registry))
    checked = load_registry(
        json.loads(Path(frozen["registry"]).read_text(encoding="utf-8")), pilot=True
    )
    assert development.verify_snapshot(store, checked)["id"] == active["id"]
    assert checked.constructs[0].origin == "prior_proposal"
    with pytest.raises(ValidationError, match="parent"):
        development.freeze_instrument(store, active, plain(registry))
    with pytest.raises(ValidationError, match="differs"):
        development.verify_snapshot(store, replace(checked, assessment_scope="different"))
    amended = development.freeze_instrument(
        store, active, plain(registry), frozen["snapshot_id"], "Synthetic checkpoint"
    )
    assert amended["snapshot_id"] != frozen["snapshot_id"]


def test_not_retrieved_is_not_a_full_text_exclusion(store):
    active, record = start_review(store)
    research.screen(
        store,
        active,
        [
            {
                "record_id": record["id"],
                "stage": "title_abstract",
                "decision": "include",
                "mode": "human",
                "reviewer": "synthetic",
                "decided_at": "synthetic",
            }
        ],
    )
    sheet = research_review.screening_sheet(store, active, "full_text")
    raw = {
        **response(sheet),
        "submitted_at": "synthetic",
        "answers": [
            {"id": record["id"], "value": "not_retrieved", "reason": "Synthetic access gap"}
        ],
    }
    research_review.import_screening(store, active, sheet, raw)
    status = research.review_status(store, active)
    assert status["reports_not_retrieved"] == 1
    assert "full_text/exclude" not in status["decisions"]


def test_public_exports_keep_scope_denominators_and_no_false_registration(store):
    controls.demo(store)
    exported = public_report(report.build_report(store))
    cohort = exported["cohorts"][0]
    assert set(cohort["required_methods"]) == {"qa", "claims", "items", "citations"}
    assert cohort["research_revision"] and cohort["judge"]["model"]
    assert "method_assessment" in cohort["systems"][0]
    assert cohort["validation_status"] == "synthetic_demonstration"
    active, _ = start_review(store)
    bundle = development.public_protocol_bundle(store, active)
    raw = json.loads(Path(bundle["export"]).read_text(encoding="utf-8"))
    assert raw["registration"]["status"] == "not_registered"
    assert "PRIOR-SENTINEL" not in json.dumps(raw)
    assert bundle["registered"] is False


def test_review_status_and_protocol_bundle_read_the_protocol(store):
    """Both used to hard-code one planned reviewer and an unregistered
    protocol; an amendment that recruits a second screener or registers the
    study must show up in the status and the export without a code change."""
    live = live_protocol()
    active, _ = start_review(store)
    status = research.review_status(store, active)
    assert status["human_reviewers_planned"] == live["reviewers"]["human_count"]
    bundle = development.public_protocol_bundle(store, active)
    raw = json.loads(Path(bundle["export"]).read_text(encoding="utf-8"))
    assert raw["registration"]["status"] == live["registration"]["status"]
    assert raw["registration"]["external_timestamp"] is None

    more = json.loads(json.dumps(live))
    more["reviewers"]["human_count"] = 3
    more["prior_exposure"] += " (three reviewers)"
    active, _ = start_review(store, more)
    assert research.review_status(store, active)["human_reviewers_planned"] == 3

    registered = json.loads(json.dumps(live))
    registered["registration"] = {"status": "registered"}
    registered["prior_exposure"] += " (registered)"
    active, _ = start_review(store, registered)
    with pytest.raises(ValidationError, match="timestamp"):
        development.public_protocol_bundle(store, active)
    registered["registration"]["external_timestamp"] = "2026-09-15T00:00:00Z"
    registered["prior_exposure"] += " (stamped)"
    active, _ = start_review(store, registered)
    assert development.public_protocol_bundle(store, active)["registered"] is True


def test_repeat_calls_use_distinct_cache_entries_and_remain_resumable(store):
    c, *_ = controls.fixture("en", "continuity")

    class Backend:
        identity = controls.FIXTURE_MODEL
        calls = 0

        def complete(self, prompt):
            self.calls += 1
            return json.dumps({"call": self.calls})

    backend = Backend()
    first = Runner(backend, store, Budget(2), replicate_id="repeat-1")
    second = Runner(backend, store, Budget(2), replicate_id="repeat-2")
    assert first.ask(c, "test", "same question")["call"] == 1
    assert second.ask(c, "test", "same question")["call"] == 2
    assert second.ask(c, "test", "same question")["call"] == 2
    assert backend.calls == 2


@pytest.mark.parametrize(
    "text", ["[evidence:current:]", "[evidence:current:t0", "[evidence:bad id:t0]"]
)
def test_malformed_reserved_citations_remain_visible(text):
    c, _, n, *_ = controls.fixture("en", "continuity")
    refs = extract(replace(n, text=text), c)
    assert len(refs) == 1 and not refs[0]["valid"] and not refs[0]["syntax_valid"]


def test_research_amendment_import_keeps_initial_decisions(store):
    active, record = start_review(store)
    registry = operational_toy(store, active, toy_registry(active, record))
    changed = replace(
        registry, constructs=(replace(registry.constructs[0], definition="Revised definition"),)
    )
    sheet = development.registry_sheet(store, active, plain(changed), amend=True)
    item = next(i for i in sheet["items"] if i["id"] == "construct:c")
    raw = {
        **response(sheet),
        "mode": "adjudication",
        "submitted_at": "synthetic-time",
        "answers": [
            {
                "id": item["id"],
                "value": "accept",
                "reason": "Synthetic correction",
                "supersedes": item["supersedes"],
            }
        ],
    }
    out = development.import_registry_review(store, active, sheet, raw)
    revised = load_registry(
        json.loads(Path(out["registry"]).read_text(encoding="utf-8")), pilot=True
    )
    assert len(revised.reviews) == len(registry.reviews) + 1
    assert all(r in revised.reviews for r in registry.reviews)


def test_browser_behavior_keeps_missing_answer_api_failure_and_absence_distinct():
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for the offline annotation UI behavior check")
    script = Path(report.__file__).with_name("review.js").read_text(encoding="utf-8")
    setup = r"""
const vm = require('vm');
const script = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const elements=[];
class Element {
  constructor(tag) {
    this.tag=tag; this.children=[]; this.value=''; this.textContent=''; elements.push(this);
  }
  append(e) { this.children.push(e); }
  setAttribute(k,v) { this[k]=v; }
  click() {}
}
const roots = new Map();
const document={documentElement:{}, createElement:t=>new Element(t),
  querySelector:s=>{if(!roots.has(s)) roots.set(s,new Element(s)); return roots.get(s);}};
const statuses=[null, {status:'failed'}, {status:'not_in_note'},
  {status:'ambiguous',text:'Synthetic ambiguity'}];
const DATA={language:'en',mode:'independent',version:'test',id:'sheet',profile:'continuity',
 items:statuses.map((a,i)=>({id:'q'+i,kind:'qa',profile:'continuity',text:'Synthetic question '+i,
 choices:['preserved','omitted','unassessable'],context:{note_answer:a}})),
 missing_information_prompt:'What is missing?',sources:[]};
let saved;
const ctx={DATA,document,Map,Object,Number,Date,JSON,console,
  alert:msg=>{throw Error(msg);},setTimeout:()=>{},
  Blob:class {constructor(parts){saved=JSON.parse(parts[0]);}},
  URL:{createObjectURL:()=> 'blob:private',revokeObjectURL:()=>{}}};
vm.createContext(ctx);vm.runInContext(script,ctx);
const messages=elements.map(e=>e.textContent);
for(const wanted of ['Not measured','failed','not in note','ambiguous']) {
  if(!messages.includes(wanted)) throw Error('State lost: '+wanted);
}
const id=roots.get('#identity');
id.children.find(e=>e.tag==='input').value='synthetic-human';
id.children.find(e=>e.tag==='select').value='researcher';
id.children.find(e=>e.tag==='label').children[0].value='yes';
roots.get('#save').onclick();
if(saved.answers.length!==0) throw Error('Blank fields became human judgments');
if(saved.review_seconds!==null) throw Error('Missing time became zero');
console.log('distinct states and blank export verified');
"""
    result = subprocess.run(
        [node, "-e", setup],
        input=json.dumps(script),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )
    assert result.returncode == 0, result.stderr


def test_citation_severity_is_not_assumed_when_the_target_check_succeeds():
    c, b, n, s, _, e = controls.fixture("en", "continuity", "wrong_citation")
    unknown = replace(e, citations=(replace(e.citations[0], severity=None),))
    result = measure(c, n, b, s, unknown)
    assert result["citation_support"] == 0
    assert result["citation_assessment"]["severity_unassessed"] == 1
    assert result["has_critical_error"] is None
    observed = replace(e, citations=(replace(e.citations[0], severity="critical"),))
    result = measure(c, n, b, s, observed)
    assert result["has_critical_error"] is True
    assert result["critical_findings_by_method"]["citations"] == 1
