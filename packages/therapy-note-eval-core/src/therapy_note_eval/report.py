"""Standalone local review UI and aggregate-only reports with no overall ranking."""

from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path

from . import PROTOCOL_VERSION
from .findings import summarize as summarize_findings
from .metrics import RECALL_MEASURES, cluster_interval, measure
from .schema import (
    AGGREGATION_VERSION,
    ERROR_TYPES,
    IMPORTANCE,
    MANDATORY,
    Bank,
    Case,
    Evaluation,
    Manifest,
    Note,
    Segmentation,
    decode,
    digest,
    implementation_digest,
    plain,
    require,
)
from .storage import Store


def safe_json(value) -> str:
    return (
        json.dumps(plain(value), ensure_ascii=True)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


HEAD = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy"
content="default-src 'none'; script-src 'unsafe-inline';
style-src 'unsafe-inline'; connect-src 'none'; img-src data:">
<style>body{font:16px/1.5 system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#20303a}
article,section{border:1px solid #b8c6ce;border-radius:8px;margin:1rem 0;padding:1rem}
pre{white-space:pre-wrap;overflow-wrap:anywhere}button,select,input,textarea{font:inherit;margin:.4rem}
textarea{display:block;width:95%;min-height:4rem}label{display:inline-block;margin:.3rem}
table{border-collapse:collapse;width:100%;margin:1rem 0}
td,th{border-bottom:1px solid #ccc;padding:.5rem;
text-align:left;vertical-align:top}small{color:#50606a}.warning{background:#fff2ce;padding:1rem}
</style>"""


def annotation_html(review: dict) -> str:
    """No predictions, model identities, CDNs, localStorage or network calls."""
    return (
        HEAD
        + """<title>Gen-2 independent review</title><h1 id="title"></h1>
<p class="warning" id="notice"></p><div id="identity"></div><main id="app"></main>
<h2 id="missingTitle"></h2><textarea id="missing"></textarea>
<div id="observations"></div><button id="save"></button><p id="progress"></p>
<script>const DATA="""
        + safe_json(review)
        + ";\n"
        + Path(__file__).with_name("review.js").read_text(encoding="utf-8")
        + "</script></html>"
    )


def write_review(store: Store, review: dict) -> Path:
    store.put("sheets", review["id"], review)
    path = store.output_path("review", review["id"] + ".html")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(annotation_html(review), encoding="utf-8")
    return path


def load_workspace(store: Store) -> dict:
    """Every artefact a report reads, decoded and keyed by revision.

    Shared with `contrast`, which needs the same population and the same
    per-case measurements and must not reach them by a second, subtly
    different route.
    """
    cases = {c.revision: c for c in (decode(Case, r) for r in store.all("cases"))}
    banks = {b.revision: b for b in (decode(Bank, r) for r in store.all("banks"))}
    notes = {n.revision: n for n in (decode(Note, r) for r in store.all("notes"))}
    segments = {
        s.revision: s for s in (decode(Segmentation, r) for r in store.all("segmentations"))
    }
    manifests = {digest(r): decode(Manifest, r) for r in store.all("manifests")}
    evaluations = [decode(Evaluation, r) for r in store.all("evaluations")]
    return {
        "cases": cases,
        "banks": banks,
        "notes": notes,
        "segments": segments,
        "manifests": manifests,
        "evaluations": evaluations,
    }


def measured_by_system(
    store: Store, key: str, manifest: Manifest, found: dict
) -> tuple[dict, dict, dict]:
    """Per-case measurements for one manifest, keyed system -> case id.

    This is the loop `build_report` averages. It is a function so that
    `contrast` can pair the values it produces across two manifests: the report
    payload carries only the means, and a paired comparison needs the notes.
    Returns the measurements, the generator identities it saw, and which cases
    each generator produced a note for.
    """
    cases, banks, notes, segments, evaluations = (
        found["cases"],
        found["banks"],
        found["notes"],
        found["segments"],
        found["evaluations"],
    )
    population = {k: cases[v] for k, v in manifest.cases.items()}
    require(
        all(c.revision == manifest.cases[c.id] for c in population.values()),
        "Report population revision mismatch",
    )
    by_system = defaultdict(dict)
    identities = {}
    generated = defaultdict(set)
    for note in notes.values():
        if note.case_revision in manifest.cases.values() and note.spec == manifest.spec:
            identities[note.generator.key] = note.generator
            generated[note.generator.key].add(note.case_id)
    for record in store.all("generation_plans"):
        if record["spec"] == plain(manifest.spec) and record["cases"] == manifest.cases:
            from .schema import Model

            model = decode(Model, record["generator"])
            identities[model.key] = model
    for evaluation in evaluations:
        if evaluation.manifest_id != key:
            continue
        note = notes[evaluation.note_revision]
        bank = banks[evaluation.bank_revision]
        segmentation = segments[evaluation.segmentation_revision]
        case = population[evaluation.case_id]
        manifest.check(case, bank, note, segmentation)
        require(evaluation.judge == manifest.judge, "Report judge mismatch")
        require(
            evaluation.measurements == manifest.measurements
            and evaluation.research_revision == manifest.research_revision
            and evaluation.methods == manifest.methods,
            "Evaluation and manifest use different research instruments",
        )
        require(
            evaluation.assessment_scope == manifest.assessment_scope
            and evaluation.required_methods == manifest.required_methods
            and evaluation.method_specs == manifest.method_specs
            and evaluation.replicate_id == manifest.replicate_id,
            "Evaluation and manifest use different scope or replicate",
        )
        # Two judgments of the same note are repeats, never two independent cases.
        previous = by_system[note.generator.key].get(case.id)
        values = measure(case, note, bank, segmentation, evaluation)
        links = [
            v for v in store.all("finding_links") if v["evaluation_revision"] == digest(evaluation)
        ]
        require(len(links) <= 1, "Choose one reviewed finding linkage in this report workspace")
        values["finding_linkage"] = summarize_findings(evaluation, links[0] if links else None)
        require(
            previous is None or previous == values,
            "Repeated judgments disagree; choose a separate run before reporting",
        )
        by_system[note.generator.key][case.id] = values
    return by_system, identities, generated


def build_report(store: Store) -> dict:
    found = load_workspace(store)
    cases, manifests = found["cases"], found["manifests"]
    cohorts = []
    archived = []
    for key, manifest in sorted(manifests.items()):
        if (
            manifest.protocol != PROTOCOL_VERSION
            or manifest.implementation_digest != implementation_digest()
            or manifest.aggregation_version != AGGREGATION_VERSION
        ):
            archived.append(
                {
                    "manifest_id": key,
                    "protocol": manifest.protocol,
                    "implementation_digest": manifest.implementation_digest,
                    "status": "Historical artifact retained; not recalculated with current metrics",
                }
            )
            continue
        population = {k: cases[v] for k, v in manifest.cases.items()}
        by_system, identities, generated = measured_by_system(store, key, manifest, found)
        systems = []
        for system, identity in sorted(identities.items()):
            measured = by_system[system]
            summary = {}
            for metric in (
                "faithfulness",
                *RECALL_MEASURES,
                "has_critical_error",
                "citation_coverage",
                "citation_support",
                "citation_validity",
                "evidence_coverage",
                "evidence_support",
                "retrieval_recall",
                *(
                    m.id + "_fail"
                    for m in manifest.measurements
                    if m.response_format == "binary" and manifest.spec.profile in m.profiles
                ),
            ):
                observed = []
                for case_id, values in measured.items():
                    if metric in values["not_requested"]:
                        continue
                    if metric.endswith("_fail"):
                        verdict = values["dimensions"].get(metric.removesuffix("_fail"))
                        value = float(verdict == "fail") if verdict in ("pass", "fail") else None
                    elif metric.endswith("_recall") and metric != "retrieval_recall":
                        value = values["coverage"][metric.removesuffix("_recall")]["recall"]
                    else:
                        value = values[metric]
                    if value is not None:
                        observed.append((population[case_id].group_id, float(value)))
                estimate = cluster_interval(observed)
                inapplicable = sum(metric in v["not_applicable"] for v in measured.values())
                eligible = len(population) - inapplicable
                complete = len(observed) == eligible
                # Conditional observations are explicitly named. Never present
                # them as the score of the full planned population.
                summary[metric] = {
                    "value": estimate["mean"] if complete else None,
                    "ci95": estimate["ci95"] if complete else None,
                    "observed_subset": estimate,
                    "answered": len(observed),
                    "expected": len(population),
                    "eligible": eligible,
                    "complete": complete,
                    "not_applicable": inapplicable,
                    "not_requested": sum(metric in v["not_requested"] for v in measured.values()),
                }
            systems.append(
                {
                    "system": plain(identity),
                    "generated": len(generated[system]),
                    "evaluations": len(measured),
                    "expected": len(population),
                    "metrics": summary,
                    "item_distributions": {
                        m.id: {
                            "labels": list(m.labels),
                            "format": m.response_format,
                            "planned": len(population),
                            "outcomes": {
                                label: sum(
                                    v["measurement_values"].get(m.id, {}).get("value") == label
                                    for v in measured.values()
                                )
                                for label in m.labels
                            },
                            "missing": sum(
                                m.id not in v["measurement_values"] for v in measured.values()
                            )
                            + len(population)
                            - len(measured),
                            "unassessable": sum(
                                v["dimensions"].get(m.id) == "unassessable"
                                for v in measured.values()
                            ),
                            "not_applicable": sum(
                                v["dimensions"].get(m.id) == "not_applicable"
                                for v in measured.values()
                            ),
                        }
                        for m in manifest.measurements
                        if m.response_format != "binary" and manifest.spec.profile in m.profiles
                    },
                    "critical_findings_observed": sum(
                        v["critical_findings_observed"] for v in measured.values()
                    ),
                    "critical_notes_observed": sum(
                        v["has_critical_error"] is True for v in measured.values()
                    ),
                    "critical_scope_complete_notes": sum(
                        v["critical_scope_complete"] for v in measured.values()
                    ),
                    "critical_scope_incomplete_notes": len(population)
                    - sum(v["critical_scope_complete"] for v in measured.values()),
                    # Findings by the kind of error the judge named, per method, summed
                    # over this system's notes. A verdict carrying several labels is
                    # counted under each, so these exceed the finding counts beside them
                    # and are not a count of incidents.
                    "error_types": {
                        kind: {
                            method: sum(v["error_types"][kind][method] for v in measured.values())
                            for method in ("claims", "qa", "items")
                        }
                        for kind in ERROR_TYPES
                    },
                    "critical_findings_by_method": {
                        method: sum(
                            v["critical_findings_by_method"].get(method, 0)
                            for v in measured.values()
                        )
                        for method in manifest.methods
                    },
                    "method_assessment": {
                        method: {
                            **{
                                k: sum(v["method_assessment"][method][k] for v in measured.values())
                                for k in (
                                    "planned",
                                    "applicable",
                                    "assessed",
                                    "missing",
                                    "unassessable",
                                )
                            },
                            "notes_without_evaluation": len(population) - len(measured),
                            "severity_unassessed": sum(
                                v["method_assessment"][method].get("severity_unassessed", 0)
                                for v in measured.values()
                            ),
                            "complete_notes": sum(
                                v["method_assessment"][method]["complete"]
                                for v in measured.values()
                            ),
                        }
                        for method in manifest.methods
                    },
                    "diagnostics": {
                        "finding_linkage": [v["finding_linkage"] for v in measured.values()],
                        "notes_measured": len(measured),
                        "word_counts": [v["word_count"] for v in measured.values()],
                        "claim_outcomes": {
                            outcome: sum(
                                v["claim_outcomes"].get(outcome, 0) for v in measured.values()
                            )
                            for outcome in (
                                "supported",
                                "contradicted",
                                "unsupported",
                                "unassessable",
                            )
                        },
                        "qa_outcomes": {
                            importance: {
                                outcome: sum(
                                    v["coverage"][importance]["outcomes"].get(outcome, 0)
                                    for v in measured.values()
                                )
                                for outcome in (
                                    "preserved",
                                    "partial",
                                    "omitted",
                                    "contradicted",
                                    "unassessable",
                                )
                            }
                            for importance in IMPORTANCE
                        },
                        "missing_qa_checks": sum(
                            v["coverage"][importance]["missing"]
                            for v in measured.values()
                            for importance in IMPORTANCE
                        ),
                    },
                }
            )
        cohorts.append(
            {
                "manifest_id": key,
                "research_revision": manifest.research_revision,
                "measurement_revision": digest(manifest.measurements),
                "validation": "synthetic demonstration"
                if manifest.origin == "synthetic"
                else "experimental measurement; external validation not established",
                "corpus": manifest.corpus,
                "origin": manifest.origin,
                "split": manifest.split,
                "spec": plain(manifest.spec),
                "judge": plain(manifest.judge),
                "source_mode": manifest.source_mode,
                "methods": list(manifest.methods),
                "assessment_scope": manifest.assessment_scope,
                "required_methods": list(manifest.required_methods),
                "replicate_id": manifest.replicate_id,
                "implementation_digest": manifest.implementation_digest,
                "aggregation_version": manifest.aggregation_version,
                "independent_groups": len({c.group_id for c in population.values()}),
                "systems": systems,
            }
        )
    return {
        "protocol": PROTOCOL_VERSION,
        "status": "experimental",
        "notice": "Automatic scores are not clinical validation. No cross-profile, "
        "cross-language or cross-judge composite is computed.",
        "cohorts": cohorts,
        "archived_runs": archived,
    }


def report_html(payload: dict) -> str:
    parts = [
        HEAD,
        "<title>Gen-2 evaluation</title><h1>Gen-2 evaluation</h1>",
        '<p class="warning">' + html.escape(payload["notice"]) + "</p>",
    ]
    if payload.get("archived_runs"):
        parts.append(
            "<details><summary>Archived runs: a derived run is required "
            "for current metrics</summary><ul>"
        )
        for archived in payload["archived_runs"]:
            parts.append(
                "<li>" + html.escape(archived["manifest_id"] + " · " + archived["status"]) + "</li>"
            )
        parts.append("</ul></details>")
    for cohort in payload["cohorts"]:
        spec = cohort["spec"]
        title = f"{cohort['corpus']} · {spec['language']} · {spec['profile']} · {spec['format']}"
        parts += [
            "<section><h2>" + html.escape(title) + "</h2>",
            "<p>Judge: "
            + html.escape(cohort["judge"]["model"])
            + " · independent groups: "
            + str(cohort["independent_groups"])
            + "</p>",
            "<table><tr><th>System</th><th>Generated / expected</th><th>Faithfulness</th>"
            f"<th>{MANDATORY.capitalize()} recall</th>"
            "<th>Notes with critical findings in declared scope</th></tr>",
        ]
        parts.append(
            "<caption>Scope: "
            + html.escape(cohort["assessment_scope"])
            + "; required methods: "
            + html.escape(", ".join(cohort["required_methods"]))
            + "; selected: "
            + html.escape(", ".join(cohort["methods"]))
            + "</caption>"
        )
        for system in cohort["systems"]:
            parts.append(
                "<tr><td>"
                + html.escape(system["system"]["model"])
                + "</td><td>"
                + f"{system['generated']} / {system['expected']}</td>"
            )
            for name in ("faithfulness", MANDATORY + "_recall", "has_critical_error"):
                m = system["metrics"][name]
                value = (
                    (
                        "not selected"
                        if m["not_requested"] == m["expected"]
                        else "not applicable"
                        if not m["eligible"]
                        else "unmeasured/incomplete"
                    )
                    if m["value"] is None
                    else f"{m['value']:.3f}"
                )
                interval = "" if m["ci95"] is None else f" [{m['ci95'][0]:.3f}, {m['ci95'][1]:.3f}]"
                parts.append(
                    f"<td>{value}{interval}<br><small>{m['answered']} / {m['expected']}"
                    " assessed</small></td>"
                )
            parts.append("</tr>")
        parts.append("</table><details><summary>All measures and observed outcomes</summary>")
        for system in cohort["systems"]:
            parts.append("<h3>" + html.escape(system["system"]["model"]) + "</h3>")
            parts.append(
                "<table><tr><th>Measure</th><th>Population estimate [95% CI]</th>"
                "<th>Assessed / planned</th><th>Not applicable</th></tr>"
            )
            for name, metric in system["metrics"].items():
                value = "unmeasured/incomplete"
                if metric["not_requested"] == metric["expected"]:
                    value = "not selected"
                elif metric["not_applicable"] == metric["expected"]:
                    value = "not applicable"
                elif metric["value"] is not None:
                    value = f"{metric['value']:.3f}"
                if metric["ci95"] is not None:
                    value += f" [{metric['ci95'][0]:.3f}, {metric['ci95'][1]:.3f}]"
                title = name.replace("_", " ").replace(" fail", " failure rate")
                parts.append(
                    f"<tr><td>{html.escape(title)}</td><td>{value}</td>"
                    f"<td>{metric['answered']} / {metric['expected']}</td>"
                    f"<td>{metric['not_applicable']}</td></tr>"
                )
            for name, distribution in system["item_distributions"].items():
                parts.append(
                    "<tr><td>"
                    + html.escape(name)
                    + "</td><td>"
                    + html.escape(json.dumps(distribution))
                    + "</td></tr>"
                )
            parts.append(
                "</table><p>Observed critical notes: "
                f"{system['critical_notes_observed']}; critical findings: "
                f"{system['critical_findings_observed']}.</p>"
                f"<p>Scope completely assessed for {system['critical_scope_complete_notes']} / "
                f"{system['expected']} notes. No observed finding is not proof of absence.</p>"
            )
            diagnostics = system["diagnostics"]
            parts.append(
                "<p>Overlapping findings: "
                + html.escape(json.dumps(diagnostics["finding_linkage"]))
                + "</p>"
            )
            parts.append(
                "<p>Word counts (descriptive): "
                + html.escape(", ".join(map(str, diagnostics["word_counts"])))
                + "</p>"
            )
            for importance, outcomes in diagnostics["qa_outcomes"].items():
                parts.append(
                    "<p>"
                    + importance
                    + " QA outcomes: "
                    + "; ".join(f"{k}: {v}" for k, v in outcomes.items())
                    + "</p>"
                )
            parts.append(f"<p>Missing required QA checks: {diagnostics['missing_qa_checks']}</p>")
        parts.append("</details></section>")
    parts.append("</html>")
    return "".join(parts)


def write_report(store: Store) -> tuple[Path, Path]:
    payload = build_report(store)
    name = digest(payload)
    data = store.output_path("reports", name + ".json")
    page = store.output_path("reports", name + ".html")
    data.parent.mkdir(parents=True, exist_ok=True)
    data.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    page.write_text(report_html(payload), encoding="utf-8")
    return data, page
