"""The versioned candidate catalog of the Gen-2 review: one file, checked here.

`catalog.json` is the tracked English record of what the scoping search of
2026-09-13 proposed: sources, candidate constructs, methods, measurement
levels, blind spots, a pilot proposal and the comparison with the earlier
criteria map. It is AI-authored and carries no human acceptance; the page under
`docs/` and the draft registry beside it are generated from it and the suite
fails when either drifts.

`problems` is the whole validation rule. It names fields, never reproduces a
clinical text, and refuses anything that would read as a human decision.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOG_PATH = HERE / "catalog.json"
REPORTS_PATH = HERE.parent / "review-2026-09-13" / "reports.json"

VERSION = "catalog-v1"
SECTIONS = (
    "sources",
    "abstract_sources",
    "families",
    "conditions",
    "candidates",
    "methods",
    "levels",
    "blind_spots",
    "pilot_proposal",
    "comparison",
)
META = (
    "version",
    "review_date",
    "catalog_date",
    "status",
    "language_policy",
    "origin_policy",
    "origin_values",
    "record_kinds",
    "pilot_record_kinds",
    "purposes",
    "relevance_levels",
    "evidence_layers",
    "provenance",
)
READINESS = ("implemented", "transferable", "candidate", "human_only")
ACTIONS = ("keep", "revise", "merge", "drop", "add")
COVERED = ("yes", "partly", "no")
EXAMPLES = ("positive", "negative", "boundary")
CANDIDATE_TEXT = (
    "label",
    "definition",
    "origin_note",
    "mode",
    "unit",
    "inputs",
    "applicability",
    "measurement",
    "error_consequence",
    "validation",
    "overlaps",
)
ENTRY_TEXT = (
    "label",
    "unit",
    "format",
    "why",
    "human_input",
    "risk",
    "saturation",
    "saturation_source",
    "saturation_detail",
)
#: Letters of Czech that English does not have. Written as escapes, as the
#: repository's own scanner writes them, so this file passes its own rule.
DIACRITIC = re.compile(
    "[" + "\u011b\u0161\u010d\u0159\u017e\u00fd\u00e1\u00ed\u00e9\u00fa\u016f\u0148\u0165\u010f"
    "\u011a\u0160\u010c\u0158\u017d\u00dd\u00c1\u00cd\u00c9\u00da\u016e\u0147\u0164\u010e]"
)
#: Words that would turn a catalog entry into a claim about a person's decision.
DECISION_KEYS = ("reviewed_by", "human_checked_by", "accepted_by", "decision")
ID = re.compile(r"\b(K\d\d|ME\d\d|M\d|S_abs_\w+|S\d\d?|P\d\d|F\d|L\d+b?|B\d+)\b")


def load(path: Path = CATALOG_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ids(catalog: dict, section: str) -> list[str]:
    items = catalog["pilot_proposal"]["entries"] if section == "pilot" else catalog[section]
    return [item["id"] for item in items]


def source_ids(catalog: dict) -> set[str]:
    return set(ids(catalog, "sources")) | set(ids(catalog, "abstract_sources"))


def _strings(value, path="$"):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _strings(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _strings(v, f"{path}[{i}]")


def problems(catalog: dict, reports: dict | None = None) -> list[str]:
    """Every rule the catalog must satisfy, as messages; an empty list is valid."""
    out: list[str] = []
    missing = [k for k in META + SECTIONS if k not in catalog]
    if missing:
        return [f"missing top-level keys: {missing}"]
    if catalog["version"] != VERSION:
        out.append(f"version is {catalog['version']!r}, expected {VERSION!r}")
    unknown = set(catalog) - set(META) - set(SECTIONS)
    if unknown:
        out.append(f"unknown top-level keys: {sorted(unknown)}")
    for path, text in _strings(catalog):
        if DIACRITIC.search(text):
            out.append(f"{path}: Czech text in the public catalog")
    for path, _ in _strings(catalog):
        if path.rsplit(".", 1)[-1] in DECISION_KEYS:
            out.append(f"{path}: a human decision field in an AI-authored catalog")
    if "no human" not in catalog["status"].lower():
        out.append("status does not say that no human acceptance exists")
    if "no human" not in catalog["pilot_proposal"]["status"].lower():
        out.append("pilot_proposal.status does not say that no human selection exists")

    for section in SECTIONS:
        if section == "pilot_proposal":
            continue
        found = ids(catalog, section) if section != "comparison" else []
        if len(found) != len(set(found)):
            out.append(f"{section}: duplicate ids")
    entries = ids(catalog, "pilot")
    if len(entries) != len(set(entries)):
        out.append("pilot_proposal.entries: duplicate ids")

    sources = source_ids(catalog)
    layers = set(catalog["evidence_layers"])
    for s in catalog["sources"]:
        if s["layer"] not in layers:
            out.append(f"{s['id']}: unknown layer {s['layer']!r}")
        if s["verification"] not in ("full_text", "not_retrieved"):
            out.append(f"{s['id']}: unknown verification {s['verification']!r}")
        if not s.get("ledger_report_id"):
            out.append(f"{s['id']}: no ledger report id")
    for s in catalog["abstract_sources"]:
        if s["layer"] not in layers:
            out.append(f"{s['id']}: unknown layer {s['layer']!r}")
        if s["verification"] != "abstract":
            out.append(f"{s['id']}: abstract-only source claims {s['verification']!r}")
        if not s.get("ledger_report_id"):
            out.append(f"{s['id']}: no ledger report id")
    if reports is not None:
        by_source = {r["catalog_source"]: r["report_id"] for r in reports["reports"]}
        for s in catalog["sources"] + catalog["abstract_sources"]:
            if by_source.get(s["id"]) != s["ledger_report_id"]:
                out.append(f"{s['id']}: ledger report id does not match reports.json")

    families = set(ids(catalog, "families"))
    for f in catalog["families"]:
        if not set(f["evidence"]) <= sources:
            out.append(f"{f['id']}: evidence names an unknown source")
    for m in catalog["conditions"]:
        if not set(ID.findall(m["evidence"])) <= sources:
            out.append(f"{m['id']}: evidence names an unknown source")

    candidates = set(ids(catalog, "candidates"))
    for c in catalog["candidates"]:
        if c["family"] not in families:
            out.append(f"{c['id']}: unknown family {c['family']!r}")
        if c["kind"] not in catalog["record_kinds"]:
            out.append(f"{c['id']}: unknown record kind {c['kind']!r}")
        if c["origin"] not in catalog["origin_values"]:
            out.append(f"{c['id']}: unknown origin {c['origin']!r}")
        if set(c["relevance"]) != set(catalog["purposes"]):
            out.append(f"{c['id']}: relevance does not address every purpose")
        if not set(c["relevance"].values()) <= set(catalog["relevance_levels"]):
            out.append(f"{c['id']}: unknown relevance level")
        if set(c["examples"]) != set(EXAMPLES):
            out.append(f"{c['id']}: examples are not positive, negative and boundary")
        if not c["evidence"]:
            out.append(f"{c['id']}: no evidence")
        for i, e in enumerate(c["evidence"]):
            if e["source"] not in sources:
                out.append(f"{c['id']} evidence {i}: unknown source {e['source']!r}")
            for key in ("location", "supports", "our_adaptation"):
                if not e.get(key):
                    out.append(f"{c['id']} evidence {i}: empty {key}")
        for key in CANDIDATE_TEXT:
            if not c.get(key):
                out.append(f"{c['id']}: empty {key}")

    for m in catalog["methods"]:
        if not set(m["measures"]) <= candidates:
            out.append(f"{m['id']}: measures an unknown candidate")
        if not set(m["evidence"]) <= sources:
            out.append(f"{m['id']}: evidence names an unknown source")
        if m["readiness"] not in READINESS:
            out.append(f"{m['id']}: unknown readiness {m['readiness']!r}")
        if m["origin"] not in catalog["origin_values"]:
            out.append(f"{m['id']}: unknown origin {m['origin']!r}")
        for key in ("label", "what", "origin_note", "limits"):
            if not m.get(key):
                out.append(f"{m['id']}: empty {key}")

    for lv in catalog["levels"]:
        if lv["covered"] not in COVERED:
            out.append(f"{lv['id']}: unknown coverage {lv['covered']!r}")
    methods = set(ids(catalog, "methods"))
    conditions = set(ids(catalog, "conditions"))
    for b in catalog["blind_spots"]:
        for key in ("label", "example", "why_invisible", "needs"):
            if not b.get(key):
                out.append(f"{b['id']}: empty {key}")

    pilot = catalog["pilot_proposal"]
    for p in pilot["entries"]:
        if p["record_kind"] not in catalog["pilot_record_kinds"]:
            out.append(f"{p['id']}: unknown record kind {p['record_kind']!r}")
        named = set(ID.findall(p["measures"]))
        if not named or not named <= candidates | conditions:
            out.append(f"{p['id']}: measures names nothing known: {p['measures']!r}")
        if not set(re.findall(r"ME\d\d", p["method"])) <= methods:
            out.append(f"{p['id']}: unknown method in {p['method']!r}")
        for key in ENTRY_TEXT:
            if not p.get(key):
                out.append(f"{p['id']}: empty {key}")
    for key in ("applied_criteria", "deliberately_not_used", "left_out"):
        if not pilot.get(key):
            out.append(f"pilot_proposal.{key}: empty")
    for row in pilot["left_out"]:
        if not set(ID.findall(row["candidate"])) <= candidates:
            out.append(f"left_out: unknown candidate in {row['candidate']!r}")
    if not pilot.get("count_note"):
        out.append("pilot_proposal.count_note: empty")

    for i, row in enumerate(catalog["comparison"]):
        if row["action"] not in ACTIONS:
            out.append(f"comparison[{i}]: unknown action {row['action']!r}")
        if row["new"] is not None and row["new"] not in candidates:
            out.append(f"comparison[{i}]: unknown candidate {row['new']!r}")
        if (row["action"] == "add") != (row["old"] is None):
            out.append(f"comparison[{i}]: an added row has no old entry and only it")
        if (row["action"] == "drop") != (row["new"] is None):
            out.append(f"comparison[{i}]: a dropped row has no new entry and only it")
        if not row.get("reason"):
            out.append(f"comparison[{i}]: empty reason")
    return out


if __name__ == "__main__":
    found = problems(load(), json.loads(REPORTS_PATH.read_text(encoding="utf-8")))
    for line in found:
        print(line)
    raise SystemExit(1 if found else 0)
