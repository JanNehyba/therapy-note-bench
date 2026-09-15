"""Findings counted by the kind of error the judge named.

`schema.ERROR_TYPES` was validated on every verdict and shown to the judge, and
never counted: no per-type totals reached the report or the public export, so
"what kind of error does this system make" could not be answered from any
artefact. Now it can. Pinned here: every type is a key; a verdict carrying two
labels counts under both, which is why the totals exceed the finding count and
the docstring says so; the export passes the integers through; and the
aggregation version this changed is owned in one place.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from therapy_note_eval import controls, metrics, report
from therapy_note_eval.privacy import public_report
from therapy_note_eval.schema import AGGREGATION_VERSION, ERROR_TYPES, Manifest, decode, digest
from therapy_note_eval.storage import Store

REPO = Path(__file__).resolve().parents[1]


def _measured(variant: str = "clean"):
    c, b, n, s, _, e = controls.fixture("en", "continuity", variant)
    return c, b, n, s, e, metrics.measure(c, n, b, s, e)


def test_every_error_type_is_a_key_with_three_method_counts():
    *_, found = _measured()
    assert set(found["error_types"]) == set(ERROR_TYPES)
    for counts in found["error_types"].values():
        assert set(counts) == {"claims", "qa", "items"}
        assert all(isinstance(v, int) and v >= 0 for v in counts.values())


def test_a_verdict_with_two_labels_counts_under_both():
    c, b, n, s, e, before = _measured()
    assert e.claims, "the fixture has no claim verdicts to relabel"
    first, *rest = e.claims
    relabelled = replace(e, claims=(replace(first, error_types=("speaker", "negation")), *rest))
    after = metrics.measure(c, n, b, s, relabelled)["error_types"]
    base = before["error_types"]
    assert after["speaker"]["claims"] == base["speaker"]["claims"] + (
        0 if "speaker" in first.error_types else 1
    )
    assert after["negation"]["claims"] == base["negation"]["claims"] + (
        0 if "negation" in first.error_types else 1
    )
    # The same verdict is one finding and two type counts: totals are not incidents.
    total_types = sum(v["claims"] for v in after.values())
    assert total_types >= len(relabelled.claims) - sum(
        1 for v in relabelled.claims if not v.error_types
    )


def test_labels_on_one_verdict_are_counted_once_each():
    c, b, n, s, e, _ = _measured()
    first, *rest = e.claims
    doubled = replace(e, claims=(replace(first, error_types=("time", "time")), *rest))
    found = metrics.measure(c, n, b, s, doubled)["error_types"]
    clean = metrics.measure(c, n, b, s, e)["error_types"]
    assert found["time"]["claims"] == clean["time"]["claims"] + (
        0 if "time" in first.error_types else 1
    )


def test_the_report_sums_per_system_and_the_export_passes_them_through(workspace):
    store = Store(workspace)
    controls.demo(store)
    payload = report.build_report(store)
    assert payload["cohorts"], "the demo produced no cohorts"
    for cohort in payload["cohorts"]:
        for system in cohort["systems"]:
            assert set(system["error_types"]) == set(ERROR_TYPES)
    exported = public_report(payload)
    for cohort in exported["cohorts"]:
        for system in cohort["systems"]:
            assert set(system["error_types"]) == set(ERROR_TYPES)
            for counts in system["error_types"].values():
                assert all(type(v) is int for v in counts.values())


def test_the_aggregation_version_is_owned_once():
    assert (
        metrics.VERSION
        == AGGREGATION_VERSION
        == Manifest.__dataclass_fields__["aggregation_version"].default
    )


def test_a_run_under_the_previous_aggregation_is_archived_not_recalculated(workspace):
    """A manifest recorded under aggregation-v3 is a historical artefact now.

    The counts this change added are part of what a measurement returns, so
    the version moved. The report keeps the old run and says it was not
    recalculated, rather than silently reading it with the new arithmetic.
    """
    store = Store(workspace)
    controls.demo(store)
    record = store.all("manifests")[0]
    old = replace(decode(Manifest, record), aggregation_version="aggregation-v3")
    store.put("manifests", old.id, old)
    payload = report.build_report(store)
    archived = {a["manifest_id"] for a in payload["archived_runs"]}
    assert old.id in archived
    assert digest(record) not in archived
    assert all("not recalculated" in a["status"] for a in payload["archived_runs"])
