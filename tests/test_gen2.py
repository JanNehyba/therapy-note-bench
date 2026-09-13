"""Meaningful gen-2 boundaries; all language and clinical examples are synthetic."""

from __future__ import annotations

import json
import uuid
from dataclasses import replace
from pathlib import Path

import pytest
from therapy_note_eval import annotations, controls, pipeline, prompts, report
from therapy_note_eval.cli import main
from therapy_note_eval.metrics import cluster_interval, measure, paired_interval, plan_sample
from therapy_note_eval.schema import (
    Case,
    Claim,
    Question,
    Relevance,
    Segmentation,
    Span,
    ValidationError,
    decode,
    digest,
    plain,
    validate_cases,
)
from therapy_note_eval.storage import Budget, Runner, Store

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def workspace():
    # Python 3.13's Windows mode=700 changes the ACL in this runner. New test
    # directories inherit the already-private workspace ACL instead.
    path = REPO / "local" / ("gen2-test-" + uuid.uuid4().hex)
    path.mkdir(parents=True, mode=0o777)
    return path


class ScriptedBackend:
    identity = controls.FIXTURE_MODEL

    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []

    def complete(self, prompt):
        self.seen.append(prompt)
        value = self.replies.pop(0)
        return json.dumps(value) if not isinstance(value, str) else value


@pytest.mark.parametrize("language", ["en", "cs"])
@pytest.mark.parametrize("profile", ["continuity", "supervision", "client", "audit"])
def test_empty_note_has_zero_recall_and_no_perfect_precision(language, profile):
    c, b, n, s, _, e = controls.fixture(language, profile, "empty")
    result = measure(c, n, b, s, e)
    assert result["faithfulness"] is None
    assert result["coverage"]["essential"]["recall"] == 0
    assert result["has_critical_error"] is True


@pytest.mark.parametrize("language", ["en", "cs"])
def test_clean_and_negated_notes_are_not_equivalent(language):
    good = controls.fixture(language, "continuity", "clean")
    bad = controls.fixture(language, "continuity", "negation")
    assert measure(good[0], good[2], good[1], good[3], good[5])["faithfulness"] == 1
    assert measure(bad[0], bad[2], bad[1], bad[3], bad[5])["faithfulness"] == 0
    assert measure(bad[0], bad[2], bad[1], bad[3], bad[5])["coverage"]["essential"]["recall"] == 0


def test_note_only_question_prompt_cannot_see_transcript_or_answer():
    c, b, n, *_ = controls.fixture("en", "continuity")
    info = replace(b.information[0], source_answer="REFERENCE_ANSWER_CANARY")
    b = replace(b, information=(info,))
    prompt = prompts.answer(n, b)
    assert "REFERENCE_ANSWER_CANARY" not in prompt
    assert c.sources[0].turns[1].text not in prompt
    assert b.questions[0].text in prompt
    assert n.text in prompt


def test_source_preparation_does_not_depend_on_candidate_note():
    c, _, n, *_ = controls.fixture("en", "continuity", "wrong_session")
    assert n.text not in prompts.prepare(c)


def test_evidence_checks_revision_and_exact_unicode_offsets():
    c, b, *_ = controls.fixture("cs", "continuity")
    evidence = b.information[0].evidence[0]
    evidence.check(c)
    with pytest.raises(ValidationError, match="revision"):
        replace(evidence, source_revision="stale").check(c)
    with pytest.raises(ValidationError, match="quote"):
        replace(evidence, span=replace(evidence.span, start=1)).check(c)


def test_short_negation_remains_an_independent_claim():
    c, _, n, *_ = controls.fixture("en", "continuity")
    first = "Client reports anxiety."
    last = "Denies suicidality."
    n = replace(n, text=first + " " + last)
    claims = tuple(
        Claim(
            f"c{i}",
            text,
            "client_report",
            "client",
            "current",
            "negative",
            "reported",
            (Span("note", start, start + len(text), text),),
        )
        for i, (start, text) in enumerate(((0, first), (len(first) + 1, last)))
    )
    seg = Segmentation(n.id, n.revision, controls.FIXTURE_MODEL, claims, ())
    seg.check(n)
    with pytest.raises(ValidationError, match="omitted"):
        replace(seg, claims=claims[:1]).check(n)


def test_complete_character_coverage_does_not_prove_atomicity():
    c, b, n, s, _, e = controls.fixture("en", "continuity")
    rejected = replace(e, segmentation_complete=False)
    assert measure(c, n, b, s, rejected)["faithfulness"] is None


def test_related_clients_and_translations_cannot_cross_splits():
    c, *_ = controls.fixture("en", "continuity")
    related = replace(c, id="different-id", split="confirmation")
    with pytest.raises(ValidationError, match="splits"):
        validate_cases([c, related])
    translated = replace(related, group_id="another-client")
    with pytest.raises(ValidationError, match="splits"):
        validate_cases([c, translated])


def test_future_context_is_refused():
    c, *_ = controls.fixture("en", "continuity")
    future = replace(c.sources[0], id="future", kind="history", session_index=1)
    with pytest.raises(ValidationError, match="Future"):
        replace(c, sources=(*c.sources, future))


def test_real_data_policy_also_applies_to_note_only_requests(workspace):
    c, b, n, *_ = controls.fixture("en", "continuity")
    c = replace(c, origin="native_real", allowed_providers=("local", "einfra"))
    backend = ScriptedBackend([{}])
    backend.identity = replace(backend.identity, provider="openai")
    run = Runner(backend, Store(workspace), Budget(10))
    with pytest.raises(ValidationError, match="permitted"):
        run.ask(c, "answer", prompts.answer(n, b))
    assert backend.seen == []
    assert run.budget.calls == 0
    with pytest.raises(ValidationError, match="confined"):
        replace(c, allowed_providers=("openai",))


def test_primary_question_is_unique_and_paraphrases_do_not_inflate_recall():
    c, b, n, s, _, e = controls.fixture("en", "continuity")
    extra = Question("q2", "i1", "Another phrasing", primary=False)
    bank = replace(b, questions=(*b.questions, extra))
    bank.check(c)
    result = measure(c, n, bank, s, replace(e, bank_revision=bank.revision))
    assert result["coverage"]["essential"]["expected"] == 1
    with pytest.raises(ValidationError, match="primary"):
        replace(bank, questions=(*b.questions, replace(extra, primary=True))).check(c)


def test_appropriate_generalization_and_optional_omission_are_not_missing_essentials():
    c, b, n, s, _, e = controls.fixture("en", "continuity")
    relevance = dict(b.information[0].relevance)
    relevance["continuity"] = Relevance("not_required", "omit", "Not needed for this purpose")
    bank = replace(b, information=(replace(b.information[0], relevance=relevance),))
    result = measure(c, n, bank, s, replace(e, bank_revision=bank.revision))
    assert result["coverage"]["essential"]["expected"] == 0
    assert result["coverage"]["essential"]["recall"] is None
    assert Relevance("essential", "generalize", "Keep the relationship, omit the name")
    with pytest.raises(ValidationError):
        Relevance("essential", "omit", "Contradiction")


def test_missing_judgments_and_unclear_source_are_not_scored_as_success():
    c, b, n, s, _, e = controls.fixture("en", "continuity")
    missing = replace(e, claims=(), qa=(), answers=(), dimensions=())
    result = measure(c, n, b, s, missing)
    assert result["faithfulness"] is None
    assert result["coverage"]["essential"]["recall"] is None
    assert result["has_critical_error"] is None
    unknown = replace(e, claims=(replace(e.claims[0], verdict="unassessable"),))
    assert measure(c, n, b, s, unknown)["faithfulness"] is None


def test_rare_critical_finding_is_not_filtered_out():
    c, b, n, s, _, e = controls.fixture("en", "continuity", "negation")
    assert measure(c, n, b, s, e)["critical_findings_observed"] >= 1
    assert "occurrence_min" not in json.dumps(measure(c, n, b, s, e))


def test_case_roundtrip_rejects_unknown_fields_and_bool_index():
    c, *_ = controls.fixture("cs", "client")
    assert decode(Case, plain(c)) == c
    with pytest.raises(ValidationError):
        decode(Case, {**plain(c), "session_index": True})
    with pytest.raises(ValidationError):
        decode(Case, {**plain(c), "unexpected": "hidden"})


def test_manifest_changes_for_bank_purpose_language_budget_or_population():
    c, b, n, s, m, _ = controls.fixture("en", "continuity")
    changed = [
        replace(m, banks={c.id: "different-bank"}),
        replace(m, spec=replace(n.spec, profile="client")),
        replace(m, spec=replace(n.spec, language="cs")),
        replace(m, judge=replace(m.judge, settings={"max_tokens": 4096})),
        replace(m, cases={**m.cases, "second": "r2"}, banks={**m.banks, "second": "b2"}),
    ]
    assert len({m.id, *(x.id for x in changed)}) == 6


def test_full_scoring_pipeline_uses_separate_calls_and_reuses_exact_cache(workspace):
    c, b, n, s, m, e = controls.fixture("en", "continuity")
    replies = [
        {"answers": plain(e.answers)},
        {"qa": plain(e.qa)},
        {
            "claims": plain(e.claims),
            "dimensions": plain(
                tuple(d for d in e.dimensions if d.dimension in ("clinical", "privacy"))
            ),
            "segmentation_complete": True,
        },
        {"dimensions": plain(tuple(d for d in e.dimensions if d.dimension == "language"))},
        {"dimensions": plain(tuple(d for d in e.dimensions if d.dimension == "instructions"))},
    ]
    backend = ScriptedBackend(replies)
    run = Runner(backend, Store(workspace), Budget(5))
    result = pipeline.score(c, n, b, s, m, run)
    assert not result.failures
    assert len(backend.seen) == 5
    assert c.sources[0].turns[1].text not in backend.seen[3]
    assert c.sources[0].turns[1].text not in backend.seen[0]
    assert pipeline.score(c, n, b, s, m, run) == result
    assert len(backend.seen) == 5


def test_failed_api_json_is_not_cached_as_a_measurement(workspace):
    c, *_ = controls.fixture("en", "continuity")
    backend = ScriptedBackend(["not-json", {}])
    run = Runner(backend, Store(workspace), Budget(2))
    with pytest.raises(ValidationError):
        run.ask(c, "test", "prompt")
    assert run.ask(c, "test", "prompt") == {}
    assert run.budget.calls == 2


def test_invalid_structured_answer_is_not_cached(workspace):
    c, *_ = controls.fixture("en", "continuity")
    backend = ScriptedBackend([{}, {"okay": True}])
    run = Runner(backend, Store(workspace), Budget(2))

    def check(value):
        if not value.get("okay"):
            raise ValidationError("Invalid")

    with pytest.raises(ValidationError):
        run.ask(c, "test", "prompt", check)
    assert run.ask(c, "test", "prompt", check) == {"okay": True}


def test_budget_is_reserved_before_network_and_failures_still_cost(workspace):
    c, *_ = controls.fixture("en", "continuity")
    backend = ScriptedBackend([{}])
    run = Runner(backend, Store(workspace), Budget(5, 0.000001, 1, 1))
    with pytest.raises(ValidationError, match="Dollar"):
        run.ask(c, "test", "prompt")
    assert not backend.seen
    with pytest.raises(ValidationError, match="prices"):
        Budget(1, 1).reserve("x", 10)


def test_input_context_is_never_silently_truncated(workspace):
    c, *_ = controls.fixture("en", "continuity")
    backend = ScriptedBackend([{}])
    with pytest.raises(ValidationError, match="truncation"):
        Runner(backend, Store(workspace), Budget(1), max_input_chars=4).ask(
            c, "test", "long prompt"
        )
    assert not backend.seen


def test_single_client_does_not_receive_a_population_confidence_interval():
    assert cluster_interval([("one", 0.5)] * 100)["ci95"] is None
    paired = paired_interval(
        {"s1": ("c1", 1.0), "s2": ("c2", 0.5)}, {"s1": ("c1", 0.5), "s2": ("c2", 1.0)}
    )
    assert paired["mean"] == 0
    assert "does not establish equivalence" in paired["interpretation"]


def test_sample_plan_accounts_for_clustering_and_positive_opportunities():
    assert plan_sample()["independent_equivalent"] == 385
    clustered = plan_sample(sessions_per_client=10, intraclient_correlation=0.5)
    assert clustered["design_effect"] == 5.5
    assert clustered["clients"] > 39


def test_blinded_sheet_has_no_automatic_verdict_or_model_identity():
    c, b, n, s, _, e = controls.fixture("en", "continuity", "negation")
    e = replace(e, claims=(replace(e.claims[0], rationale="JUDGE_VERDICT_CANARY"),))
    review = annotations.sheet(c, n, b, s, e)
    page = report.annotation_html(review)
    assert "JUDGE_VERDICT_CANARY" not in page
    assert n.generator.model not in page
    assert "fetch(" not in page and "localStorage" not in page
    assert "connect-src 'none'" in page


def test_hostile_note_text_cannot_close_the_script():
    encoded = report.safe_json({"note": "</script><script>fetch('https://invalid')</script>"})
    assert "</script>" not in encoded
    assert json.loads(encoded)["note"].startswith("</script>")


def response(review, rater="r1", value="supported"):
    return {
        "version": annotations.VERSION,
        "sheet_id": review["id"],
        "rater_id": rater,
        "role": "therapist",
        "mode": "independent",
        "answers": [{"id": "claim:c1", "value": value}],
        "review_seconds": 20,
        "factual_edits": 1,
        "style_edits": 3,
        "information_found_seconds": 4,
    }


def test_partial_human_reviews_preserve_missingness_and_adjudication(workspace):
    c, b, n, s, _, e = controls.fixture("en", "continuity")
    review = annotations.sheet(c, n, b, s, e)
    first, second = response(review), response(review, "r2", "unsupported")
    result = annotations.import_response(review, first)
    assert result["answered"] == 1 and result["missing"] == len(review["items"]) - 1
    adjudication = annotations.adjudication_sheet(review, [first, second])
    assert adjudication["parent_sheet"] == review["id"]
    assert adjudication["mode"] == "adjudication"
    assert len(next(i for i in adjudication["items"] if i["id"] == "claim:c1")["human_votes"]) == 2
    assert annotations.agreement(review, [first, second])["rater_count"] == 2
    with pytest.raises(ValidationError):
        annotations.adjudication_sheet(review, [first, first])


def test_calibration_is_bound_to_human_and_machine_artifact_versions():
    c, b, n, s, _, e = controls.fixture("en", "continuity")
    review = annotations.sheet(c, n, b, s, e)
    out = annotations.compare_to_judge(review, response(review), e)
    assert out["by_kind"]["claim"]["observed_agreement"] == 1
    with pytest.raises(ValidationError):
        annotations.compare_to_judge(
            review, response(review), replace(e, bank_revision="different")
        )


def test_pairwise_design_is_connected_and_does_not_collapse_ties():
    fixtures = [controls.fixture("en", "continuity", v) for v in ("clean", "negation", "empty")]
    c = fixtures[0][0]
    review, lookup = annotations.pair_sheet({c.id: c}, [f[2] for f in fixtures], maximum=3)
    assert lookup["connected"]
    assert set(lookup["model_appearances"].values()) == {2}
    assert "both_unacceptable" in review["items"][0]["choices"]
    assert "both_acceptable" in review["items"][0]["choices"]


def test_offline_demo_reports_separate_languages_profiles_and_judges(workspace):
    assert main(["--workspace", str(workspace), "demo"]) == 0
    payload = report.build_report(Store(workspace))
    assert payload["status"] == "experimental"
    assert len(payload["cohorts"]) == 8
    assert {c["spec"]["language"] for c in payload["cohorts"]} == {"en", "cs"}
    assert all(c["independent_groups"] == 1 for c in payload["cohorts"])
    assert all(len(c["systems"]) == 3 for c in payload["cohorts"])
    assert sum(s["generated"] for c in payload["cohorts"] for s in c["systems"]) == 24
    assert "transcript" not in json.dumps(payload)


def test_missing_planned_case_cannot_shrink_the_report_denominator(workspace):
    store = Store(workspace)
    c, b, n, s, m, e = controls.fixture("en", "continuity")
    second = replace(c, id="second", group_id="second-client", translation_group=None)
    b2 = replace(b, case_id=second.id, case_revision=second.revision)
    m = replace(
        m,
        cases={c.id: c.revision, second.id: second.revision},
        banks={c.id: b.revision, second.id: b2.revision},
    )
    e = replace(e, manifest_id=m.id)
    for kind, key, obj in (
        ("cases", c.revision, c),
        ("cases", second.revision, second),
        ("banks", b.revision, b),
        ("banks", b2.revision, b2),
        ("notes", n.revision, n),
        ("segmentations", s.revision, s),
        ("manifests", m.id, m),
        ("evaluations", digest(e), e),
    ):
        store.put(kind, key, obj)
    metric = report.build_report(store)["cohorts"][0]["systems"][0]["metrics"]["essential_recall"]
    assert metric["expected"] == 2 and metric["answered"] == 1
    assert metric["value"] is None


def test_raw_artifacts_cannot_be_written_into_public_docs():
    with pytest.raises(ValidationError, match="private"):
        Store(REPO / "docs" / "raw-gen2")


def test_gen1_cli_exposes_the_separate_gen2_entrypoint(capsys):
    from tnb.cli import main as host_main

    assert host_main(["gen2", "sample-plan"]) == 0
    assert "385" in capsys.readouterr().out


def test_host_adapter_reuses_provider_dialect_without_hidden_retries(monkeypatch):
    from types import SimpleNamespace

    from therapy_note_eval.legacy import HostBackend

    from tnb.providers import openai_compatible

    observed = []
    monkeypatch.setattr(
        openai_compatible,
        "discover",
        lambda _: [SimpleNamespace(id="invented-versioned-model", included=True)],
    )

    def complete(provider, model, prompt, **settings):
        observed.append((provider, model, settings))
        return SimpleNamespace(ok=True, text='{"ok": true}')

    monkeypatch.setattr(openai_compatible, "complete", complete)
    backend = HostBackend("einfra", "invented-versioned-model", "fixture", max_tokens=512)
    assert backend.complete("synthetic request") == '{"ok": true}'
    provider, model, settings = observed[0]
    assert model == backend.identity.model
    assert provider.generation.retries == 0 and provider.generation.concurrency == 1
    assert settings == {"max_tokens": 512}
    assert backend.identity.settings["dialect"]


@pytest.mark.parametrize("language", ["en", "cs"])
@pytest.mark.parametrize("variant", controls.VARIANTS)
def test_challenge_artifacts_bind_real_spans_without_asserting_llm_sensitivity(language, variant):
    c, b, n, s, m, e = controls.fixture(language, "continuity", variant)
    e.check(c, n, b, s)
    m.check(c, b, n, s)
    metrics = measure(c, n, b, s, e)
    if variant in controls.POSITIVE:
        assert metrics["coverage"]["essential"]["recall"] == 1
        assert not controls.assess(variant, e, metrics)["detected"]
    if variant == "wrong_citation":
        assert metrics["faithfulness"] == 1
        assert metrics["citation_support"] == 0
        assert controls.assess(variant, e, metrics)["target_detected"]


def test_retrieval_verifier_cannot_see_unretrieved_gold_answer():
    c, b, n, s, _, _ = controls.fixture("en", "continuity")
    b = replace(b, information=(replace(b.information[0], source_answer="HIDDEN_GOLD_CANARY"),))
    prompt = prompts.verify(c, n, s, b, {("current", "t2")})
    assert "HIDDEN_GOLD_CANARY" not in prompt
    assert c.sources[0].turns[0].text not in prompt
    assert c.sources[0].turns[2].text in prompt


def test_false_preservation_and_false_safety_are_invalid_imports():
    c, b, n, s, _, e = controls.fixture("en", "continuity")
    with pytest.raises(ValidationError, match="note answer"):
        replace(e, answers=()).check(c, n, b, s)
    with pytest.raises(ValidationError, match="dimension"):
        replace(e, dimensions=(replace(e.dimensions[0], severity="critical"),)).check(c, n, b, s)


def test_bank_can_be_reviewed_without_a_candidate_note():
    c, b, _, _, _, _ = controls.fixture("cs", "continuity")
    review = annotations.bank_sheet(c, b)
    assert "note" not in review and "note_revision" not in review
    assert all("note_answer" not in i["context"] for i in review["items"])
    assert {i["kind"] for i in review["items"]} == {"claim", "importance", "disclosure", "question"}


def test_pilot_sizes_do_not_establish_confirmation_precision():
    recall, sensitivity = plan_sample(0.05), plan_sample(0.10)
    assert recall["confidence"] == sensitivity["confidence"] == 0.95
    assert recall["independent_equivalent"] > 150
    assert sensitivity["independent_equivalent"] > 50


def test_usability_task_does_not_reveal_the_reference_answer():
    c, b, n, _, _, _ = controls.fixture("en", "continuity", "empty")
    b = replace(b, information=(replace(b.information[0], source_answer="REFERENCE_CANARY"),))
    review, key = annotations.task_sheet(c, b, n)
    assert "REFERENCE_CANARY" not in json.dumps(review)
    assert "REFERENCE_CANARY" in json.dumps(key)
    assert "sources" not in review
    reply = response(review)
    reply["answers"] = [{"id": "task:q1", "value": "Not available in the note."}]
    assert annotations.import_response(review, reply)["answered"] == 1


def test_report_exposes_all_dimensions_and_partial_qa_outcomes(workspace):
    controls.demo(Store(workspace))
    page = report.report_html(report.build_report(Store(workspace)))
    for heading in (
        "clinical failure rate",
        "privacy failure rate",
        "language failure rate",
        "instructions failure rate",
        "citation support",
        "supplementary recall",
        "partial:",
        "omitted:",
        "not applicable",
        "Word counts",
    ):
        assert heading in page


def test_annotation_javascript_downloads_importable_blinded_ratings(workspace):
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required to execute the standalone annotation interface")
    c, b, n, s, _, e = controls.fixture("cs", "continuity")
    review = annotations.sheet(c, n, b, s, e)
    path = report.write_review(Store(workspace), review)
    harness = r"""
const fs = require('node:fs'), vm = require('node:vm');
class Element {
  constructor() { this.children = []; this.value = ''; }
  append(e) { this.children.push(e); }
  setAttribute() {}
  click() {}
}
const nodes = new Map();
const document = {documentElement: {}, createElement: () => new Element(),
  querySelector: id => {if (!nodes.has(id)) nodes.set(id, new Element());return nodes.get(id)}};
let saved;
const context = vm.createContext({document, alert: m => {throw Error(m)},
  Blob: class {constructor(parts) {saved = parts.join('')}},
  URL: {createObjectURL: () => 'blob:local', revokeObjectURL() {}}, setTimeout() {}});
const page = fs.readFileSync(process.argv[1], 'utf8');
vm.runInContext(page.split('<script>')[1].split('</script>')[0], context);
vm.runInContext("if (!document.querySelector('#app').children.some(e => " +
  "e.children.some(c => c.textContent === DATA.items[0].text))) throw Error('Item text changed');",
  context);
vm.runInContext("rater.value='r1';role.value='therapist';author.value='yes';" +
  "controls.get('claim:c1').value='supported';save.onclick();", context);
process.stdout.write(saved);
"""
    result = subprocess.run(
        [node, "-e", harness, str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    imported = annotations.import_response(review, json.loads(result.stdout))
    assert imported["answered"] == 1
    assert imported["missing"] == len(review["items"]) - 1
    assert imported["review_seconds"] is None
