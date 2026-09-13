"""Compare two languages over the same conversations, pair by pair.

A paired EN/CS design is only a design if the comparison is made on the pairs.
The report averages each cohort on its own and computes no cross-language
composite, on purpose. This module does the one cross-language thing that is
sound: for every conversation that exists in both languages, take the
difference of a metric between its two notes, and resample whole clients over
those differences. Pairs are joined on `Case.translation_group`; their client
groups must agree, because the resampling unit is the client.

What must be equal. Two manifests may differ in the language of their note
spec, in the cases and banks they freeze (a translation is a different case),
and in corpus and origin (an English public demonstration and its Czech
translation are two corpora). Everything else -- judge, research instrument,
methods, scope, replicate, every version, the source mode -- must be the same,
or the difference measured would be between instruments and not between
languages. `language_contrast` refuses otherwise. The split must match too:
translation relatives share splits.

What is published and what is not. A metric is compared only where the
report's own completeness rule held on both sides; otherwise the entry says
why. The question banks are built per language, so `essential_recall` on the
two sides has two denominators; `bank_comparability` states their sizes so a
reader sees that. A confidence interval crossing zero does not establish
equivalence, and one client gives no interval at all.
"""

from __future__ import annotations

import json

from .metrics import paired_interval
from .privacy import LABEL
from .schema import Manifest, plain, require
from .storage import Store

#: Manifest fields two sides may legitimately differ on. Everything else must match.
MAY_DIFFER = frozenset({"cases", "banks", "corpus", "origin"})

#: The metrics the report averages, compared here pair by pair.
METRICS = (
    "faithfulness",
    "essential_recall",
    "supplementary_recall",
    "has_critical_error",
    "citation_coverage",
    "citation_support",
    "citation_validity",
    "evidence_coverage",
    "evidence_support",
    "retrieval_recall",
)


def comparable(left: Manifest, right: Manifest) -> dict:
    """The fields the two manifests were required to agree on, the spec without its language.

    Required headings are the one part of a spec that is legitimately written
    per language, so they may differ in wording but not in number.
    """
    require(left.spec.language != right.spec.language, "Both manifests are in the same language")
    a, b = plain(left), plain(right)
    a_spec, b_spec = dict(a.pop("spec")), dict(b.pop("spec"))
    for name in ("language", "required_headings"):
        a_spec.pop(name)
        b_spec.pop(name)
    require(a_spec == b_spec, "Note specs differ beyond language")
    require(
        len(left.spec.required_headings) == len(right.spec.required_headings),
        "Note specs require a different number of headings",
    )
    for name in sorted(set(a) | set(b)):
        if name in MAY_DIFFER:
            continue
        require(a.get(name) == b.get(name), f"Manifests differ on {name}; not a language contrast")
    return {"spec": a_spec, **{name: a[name] for name in sorted(a) if name not in MAY_DIFFER}}


def _metric_names(manifest: Manifest) -> tuple[str, ...]:
    return METRICS + tuple(
        m.id + "_fail"
        for m in manifest.measurements
        if m.response_format == "binary" and manifest.spec.profile in m.profiles
    )


def _value(metric: str, values: dict) -> float | None:
    """One case's value for one metric, exactly as the report reads it."""
    if metric in values["not_requested"]:
        return None
    if metric.endswith("_fail"):
        verdict = values["dimensions"].get(metric.removesuffix("_fail"))
        return float(verdict == "fail") if verdict in ("pass", "fail") else None
    if metric.endswith("_recall") and metric != "retrieval_recall":
        return values["coverage"][metric.removesuffix("_recall")]["recall"]
    value = values[metric]
    return None if value is None else float(value)


def _side(store: Store, key: str, manifest: Manifest, found: dict) -> dict:
    from .report import measured_by_system

    population = {k: found["cases"][v] for k, v in manifest.cases.items()}
    by_system, _, _ = measured_by_system(store, key, manifest, found)
    for case in population.values():
        require(case.translation_group, f"Case {case.id} has no translation_group; cannot pair")
    groups = {case.translation_group for case in population.values()}
    require(len(groups) == len(population), "Two cases on one side share a translation_group")
    return {
        "manifest_id": key,
        "manifest": manifest,
        "population": population,
        "by_system": by_system,
        "information": sum(len(found["banks"][rev].information) for rev in manifest.banks.values()),
    }


def _per_metric(side: dict, system: str, metric: str) -> tuple[dict, bool]:
    """{translation_group: (group_id, value)} for one system and metric, and whether it is whole."""
    measured = side["by_system"].get(system, {})
    population = side["population"]
    out: dict[str, tuple[str, float]] = {}
    inapplicable = 0
    for case_id, values in measured.items():
        if metric in values["not_applicable"]:
            inapplicable += 1
            continue
        value = _value(metric, values)
        if value is None:
            continue
        case = population[case_id]
        out[case.translation_group] = (case.group_id, value)
    eligible = len(population) - inapplicable
    return out, len(out) == eligible


def language_contrast(store: Store, left_id: str, right_id: str) -> dict:
    from .report import load_workspace

    found = load_workspace(store)
    manifests = found["manifests"]
    require(left_id in manifests and right_id in manifests, "Unknown manifest")
    left_m, right_m = manifests[left_id], manifests[right_id]
    shared = comparable(left_m, right_m)
    left, right = _side(store, left_id, left_m, found), _side(store, right_id, right_m, found)

    systems: dict[str, dict] = {}
    for system in sorted(set(left["by_system"]) & set(right["by_system"])):
        systems[system] = {}
        for metric in _metric_names(left_m):
            l_values, l_whole = _per_metric(left, system, metric)
            r_values, r_whole = _per_metric(right, system, metric)
            if not (l_whole and r_whole):
                systems[system][metric] = {
                    "not_comparable": "incomplete on "
                    + " and ".join(
                        side for side, whole in (("left", l_whole), ("right", r_whole)) if not whole
                    ),
                    "complete_left": l_whole,
                    "complete_right": r_whole,
                }
                continue
            if not l_values and not r_values:
                systems[system][metric] = {"not_comparable": "not applicable on either side"}
                continue
            systems[system][metric] = {
                **paired_interval(l_values, r_values),
                "complete_left": True,
                "complete_right": True,
            }

    return {
        "left": {
            "manifest_id": left_id,
            "language": left_m.spec.language,
            "corpus": left_m.corpus,
            "origin": left_m.origin,
            "cases": len(left["population"]),
            "required_headings": len(left_m.spec.required_headings),
        },
        "right": {
            "manifest_id": right_id,
            "language": right_m.spec.language,
            "corpus": right_m.corpus,
            "origin": right_m.origin,
            "cases": len(right["population"]),
            "required_headings": len(right_m.spec.required_headings),
        },
        "compared_on": sorted(shared),
        "pairing": "Case.translation_group; client groups must agree per pair",
        "bank_comparability": {
            "left_information": left["information"],
            "right_information": right["information"],
            "note": (
                "Question banks are built per language, so a recall on each side has its "
                "own denominator. Equal counts do not make them the same bank."
            ),
        },
        "systems": systems,
        "left_only_systems": sorted(set(left["by_system"]) - set(right["by_system"])),
        "right_only_systems": sorted(set(right["by_system"]) - set(left["by_system"])),
        "interpretation": (
            "Differences are left minus right per pair, resampled over clients. A CI "
            "crossing zero does not establish equivalence; one client gives no CI."
        ),
    }


def public_contrast(found: dict) -> dict:
    """The contrast with every free-text field removed, for the same reason as `public_report`."""

    def label(value):
        require(
            isinstance(value, str) and LABEL.fullmatch(value) is not None,
            "Unsafe public identifier",
        )
        return value

    def numeric(value):
        if isinstance(value, dict):
            return {
                label(k): numeric(v)
                for k, v in value.items()
                if k not in ("interpretation", "not_comparable", "note")
            }
        if isinstance(value, list):
            return [numeric(v) for v in value]
        require(
            value is None or type(value) in (int, float, bool), "Public aggregate contains text"
        )
        json.dumps(value, allow_nan=False)
        return value

    def side(s):
        return {k: label(s[k]) for k in ("manifest_id", "language", "corpus", "origin")} | {
            k: numeric(s[k]) for k in ("cases", "required_headings")
        }

    return {
        "left": side(found["left"]),
        "right": side(found["right"]),
        "compared_on": [label(f) for f in found["compared_on"]],
        "bank_comparability": numeric(found["bank_comparability"]),
        "systems": {
            label(system): {
                label(metric): (
                    {"not_comparable": True, **numeric(entry)}
                    if "not_comparable" in entry
                    else numeric(entry)
                )
                for metric, entry in metrics.items()
            }
            for system, metrics in found["systems"].items()
        },
        "left_only_systems": [label(s) for s in found["left_only_systems"]],
        "right_only_systems": [label(s) for s in found["right_only_systems"]],
    }
