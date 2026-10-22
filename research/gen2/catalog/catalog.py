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

VERSION = "catalog-v2"
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
    "candidate_states",
    "families_policy",
    "method",
    "decision_basis",
    "units_of_analysis",
    "purposes_in_scope",
    "open_source_properties",
    "purposes",
    "relevance_levels",
    "evidence_layers",
    "provenance",
    "revisions",
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
    "state_note",
)
#: A candidate named by a pilot entry is proposed for measurement; every other
#: state is a reason it is not, and the reasons are not interchangeable (A07).
PROPOSED = "proposed"
#: What a candidate needs before it may be measured. The item pool is drawn from
#: the literature and from this project alike, which is how an item pool is built
#: (S12, Item generation); what keeps that from being a free pass is that nothing
#: is measured on its origin. At least one evidence line has to quote a source
#: read in full, whoever thought of the criterion first.
SUPPORT_RULE = "proposed for measurement without a source read in full"
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
#:
#: A pointer to the protocol's decision ledger is a different thing and is
#: spelled `protocol_decision`: it says which recorded decision set the scope,
#: which is provenance rather than an acceptance of the entry it sits on.
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
        # Every source has to be traceable to the record of how it was found.
        # Until 2026-10-14 there was one such record, the report ledger of the
        # 2026-09-13 review, so the rule was that the id matches it. The
        # language layer added by AM-8 has its own search log and no report
        # ledger, and a source found there is traced by a published identifier
        # that resolves to the work instead. The
        # exception is by layer and not by source id, so a source cannot escape
        # the ledger by being named.
        by_source = {r["catalog_source"]: r["report_id"] for r in reports["reports"]}
        for s in catalog["sources"] + catalog["abstract_sources"]:
            # The exemption is for a language-layer source the ledger does not
            # hold. S34 is in the ledger since 2026-10-21, and an exemption that
            # went on applying to it would let the one entry drift from the
            # catalog unseen.
            if s["layer"] == "language" and s["id"] not in by_source:
                # Any identifier that resolves, not a DOI specifically. The rule
                # named the DOI while every language-layer source had one, and
                # ELERRANT does not: its venue publishes none. What the rule is
                # for is that a source outside the report ledger can be looked
                # up, so it asks whether the id resolves.
                if not ledger_url(s["ledger_report_id"]):
                    out.append(
                        f"{s['id']}: a language-layer source is traced by an identifier "
                        "that resolves"
                    )
            elif by_source.get(s["id"]) != s["ledger_report_id"]:
                out.append(f"{s['id']}: ledger report id does not match reports.json")

    families = set(ids(catalog, "families"))
    for f in catalog["families"]:
        if not set(f["evidence"]) <= sources:
            out.append(f"{f['id']}: evidence names an unknown source")
    for m in catalog["conditions"]:
        if not set(ID.findall(m["evidence"])) <= sources:
            out.append(f"{m['id']}: evidence names an unknown source")

    candidates = set(ids(catalog, "candidates"))
    full_text_sources = {s["id"] for s in catalog["sources"]}
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
        if c.get("state") not in catalog["candidate_states"]:
            out.append(f"{c['id']}: unknown state {c.get('state')!r}")
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
    named_by_entries = {
        found
        for p in pilot["entries"]
        for found in ID.findall(p["measures"])
        if found in candidates
    }
    for c in catalog["candidates"]:
        if (c["id"] in named_by_entries) != (c.get("state") == PROPOSED):
            out.append(
                f"{c['id']}: state {c.get('state')!r} does not match the pilot proposal; "
                "a candidate a pilot entry measures is proposed, and only it"
            )
        if c.get("decided_by") not in catalog["decision_basis"]:
            out.append(f"{c['id']}: unknown decided_by {c.get('decided_by')!r}")
        # What entity the candidate is a property of. It used to be carried in
        # free text inside `inputs`, which nothing read, so a property of a
        # generator could be measured on one note and reported as that note's.
        if c.get("unit_of_analysis") not in catalog["units_of_analysis"]:
            out.append(f"{c['id']}: unknown unit_of_analysis {c.get('unit_of_analysis')!r}")
        elif c.get("unit_of_analysis") != "note":
            # It may be measured, but not by an entry that runs on a note. The
            # pilot's own vocabulary draws the line: `corpus_level_proxy` is
            # "computed over a system's notes, never for one note", which is
            # what a property of a generator needs. K28 passes because P13 is
            # one; a per-note number for it would be a measurement nobody made.
            for entry in catalog["pilot_proposal"]["entries"]:
                if c["id"] in set(ID.findall(entry["measures"])):
                    if entry.get("record_kind") != "corpus_level_proxy":
                        out.append(
                            f"{c['id']}: a property of {c['unit_of_analysis']} measured by "
                            f"{entry['id']}, which is a {entry.get('record_kind')} and runs "
                            "on one note"
                        )
        if c.get("decided_by") in ("indicator", "derived") and c.get("state") == PROPOSED:
            kinds = {
                p["record_kind"]
                for p in catalog["pilot_proposal"]["entries"]
                if c["id"] in set(ID.findall(p["measures"]))
            }
            if kinds - {"corpus_level_proxy", "derived_ratio"}:
                out.append(
                    f"{c['id']}: describes rather than grades, so a pilot entry may only carry it "
                    f"as a proxy or a derived ratio, not as {sorted(kinds)}"
                )
        if c.get("state") == PROPOSED and not any(
            e["source"] in full_text_sources for e in c["evidence"]
        ):
            out.append(f"{c['id']}: {SUPPORT_RULE}")
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


PROPERTIES_PATH = HERE / "source-properties.json"


def load_properties(path: Path = PROPERTIES_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


#: A mapping note that admits a part of a bundled property has no candidate
#: must be matched by an open property. The checker reads a property as one
#: atom, so without this a concept named inside a label can be set aside in
#: prose and never decided; terminology sat in such a note for three weeks
#: before it became K34.
NO_CANDIDATE = re.compile(r"no (?:direct )?candidate|nothing covers|unmapped", re.I)


def property_problems(catalog: dict, props: dict) -> list[str]:
    """The source-first table against the catalog it was mapped to.

    The extraction is source-first and the mapping comes second, so what is
    checked here is only that the two agree: every property names a source the
    catalog has, every mapping target is a candidate, a candidate the catalog
    calls literature-origin rests on at least one source property, and every
    property no candidate covers is listed as open in the catalog or explained
    as something that is not a property of a note.
    """
    out: list[str] = []
    sources = source_ids(catalog)
    candidates = {c["id"]: c for c in catalog["candidates"]}
    listed = {row["pid"] for row in catalog["open_source_properties"]}
    seen: set[str] = set()
    covered: dict[str, list[str]] = {k: [] for k in candidates}
    for s in props["sources"]:
        if s["id"] not in sources:
            out.append(f"{s['id']}: property source is not in the catalog")
        for p in s["properties"]:
            if p["pid"] in seen:
                out.append(f"{p['pid']}: duplicate property id")
            seen.add(p["pid"])
            if not p["label"] or not p["location"]:
                out.append(f"{p['pid']}: empty label or location")
            if s["read"] == "full_text" and not p.get("quote"):
                out.append(f"{p['pid']}: a full-text property needs a quote")
            if p["kind"] not in props["kinds"]:
                out.append(f"{p['pid']}: unknown kind {p['kind']!r}")
            if NO_CANDIDATE.search(p.get("mapping") or "") and not any(
                row == p["pid"] or row.startswith(p["pid"]) for row in listed
            ):
                out.append(
                    f"{p['pid']}: its mapping says a part has no candidate and no open "
                    "property records that part"
                )
            for k in p["maps_to"]:
                if k not in candidates:
                    out.append(f"{p['pid']}: maps to unknown candidate {k!r}")
                else:
                    covered[k].append(p["pid"])
    for k, c in candidates.items():
        if c["origin"] == "literature" and not covered[k]:
            out.append(f"{k}: literature origin without any source property behind it")
    for row in props["unmapped_properties"]:
        method_like = any(
            word in row["why_unmapped"]
            for word in (
                "not a property",
                "rating format",
                "a finding",
                "a condition",
                "a scale",
                "limitation",
            )
        )
        if row["pid"] not in listed and not method_like:
            out.append(f"{row['pid']}: unmapped and neither open in the catalog nor explained")
    for row in catalog["open_source_properties"]:
        # An open property may name one part of a bundled row, and then it says
        # which row it came out of rather than standing in the table itself.
        parent = row.get("part_of")
        if row["pid"] not in seen and not (parent and parent in seen):
            out.append(f"{row['pid']}: open property is not in the source-first table")
    if props["counts"]["properties"] != len(seen):
        out.append("counts.properties does not match the table")
    return out


#: How a ledger report id becomes a URL, for the pages that draw citations.
#:
#: The catalog records what identifies a report, not where to click, which is
#: right: an id outlives a host. Two of the 46 sources carry an id that resolves
#: nowhere, a Czech decree and a file the investigator supplied, and the decree
#: backs four evidence lines, so the shapes that cannot be linked have to be
#: drawn as text rather than guessed at. A dead link on a page about provenance
#: is worse than no link, and this is why the mapping is a closed table and not
#: a pattern.
#: `acl` joined on 2026-10-23 for ELERRANT, whose venue publishes no DOI: RANLP
#: 2021 is distributed through the ACL Anthology and an Anthology id is the
#: published identifier for it. A prefix belongs here when it resolves to a
#: landing page for the work and not to a copy somebody uploaded.
LEDGER_URLS = {
    "doi": "https://doi.org/{}",
    "pmid": "https://pubmed.ncbi.nlm.nih.gov/{}/",
    "acl": "https://aclanthology.org/{}/",
}


def ledger_url(ledger_report_id: str) -> str | None:
    """The URL a ledger report id resolves to, or None when it resolves nowhere."""
    prefix, _, rest = str(ledger_report_id).partition(":")
    template = LEDGER_URLS.get(prefix)
    return template.format(rest) if template and rest else None


CZECH_PATH = HERE / "czech.json"

#: Fields of `czech.json` that must name every candidate. The name is what a
#: reader identifies a criterion by and the statement is what a panel marks
#: agreement with, so a candidate missing either cannot be put on a sheet.
#: `plain` and `example` joined them on 2026-10-17: they are the two columns of
#: the first table on the Czech page, the one a reader meets before any of the
#: rest, and a criterion with neither is a row that says only its own name. The
#: remaining fields are allowed to be partial: a criterion that is not measured
#: has no `how`, and saying nothing is the honest shape of that.
CZECH_REQUIRED = ("name", "statement", "plain", "example")


def load_czech(path: Path = CZECH_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def czech_problems(catalog: dict, czech: dict) -> list[str]:
    """The Czech text of the catalog against the catalog.

    `catalog.json` stays the single list of candidates. This file translates it
    and must therefore name exactly the same codes: a Czech view built from a
    file that had drifted is how five views came to claim five different counts.

    Partial coverage is allowed and counted, never guessed. What is refused is a
    code neither file knows, a required field left empty, and a count that does
    not match the list it counts.
    """
    out: list[str] = []
    codes = set(ids(catalog, "candidates"))
    named = set(czech["candidates"])
    for code in sorted(named - codes):
        out.append(f"czech.candidates[{code}]: not a candidate of the catalog")
    for code in sorted(codes - named):
        out.append(f"czech.candidates[{code}]: candidate has no Czech text")
    for code in sorted(named & codes):
        entry = czech["candidates"][code]
        for field in CZECH_REQUIRED:
            if not str(entry.get(field, "")).strip():
                out.append(f"czech.candidates[{code}].{field}: required and empty")
        for field, value in entry.items():
            if field == "from":
                continue
            if not str(value).strip():
                out.append(f"czech.candidates[{code}].{field}: present and empty")

    # Everything below counts the entries, so it reads the codes both files
    # know. A missing candidate is already reported above, and indexing it here
    # would answer the drift this function exists to name with a traceback.
    shared = sorted(named & codes, key=_code)
    coverage = czech["coverage"]
    if coverage["candidates"] != len(codes):
        out.append("czech.coverage.candidates does not match the catalog")
    for field, count in coverage["by_field"].items():
        actual = sum(1 for e in czech["candidates"].values() if field in e)
        if actual != count:
            out.append(f"czech.coverage.by_field[{field}]: says {count}, the entries have {actual}")
    for field, listed in coverage["missing_by_field"].items():
        actual = [c for c in shared if field not in czech["candidates"][c]]
        if actual != listed:
            out.append(f"czech.coverage.missing_by_field[{field}]: does not match the entries")
    unexplained = [
        code
        for code in shared
        if not {"how", "why_not_measured", "measured_otherwise"} & set(czech["candidates"][code])
    ]
    if unexplained != coverage["candidates_with_no_explanation_of_their_state"]:
        out.append("czech.coverage.candidates_with_no_explanation_of_their_state: does not match")

    # A grouping is a claim about the criteria, not a translation, so it may
    # cover fewer than all of them; what it may not do is name a code that is
    # not a candidate, or quietly place one twice.
    for name, groups in czech["groupings"].items():
        placed: list[str] = []
        for group, members in groups.items():
            for code in members:
                if code not in codes:
                    out.append(f"czech.groupings[{name}][{group}]: {code} is not a candidate")
                placed.append(code)
        duplicated = sorted({c for c in placed if placed.count(c) > 1})
        if duplicated:
            out.append(f"czech.groupings[{name}]: places {', '.join(duplicated)} more than once")

    for entry in czech["conflicts_resolved"]:
        code = entry["candidate"]
        if code not in codes:
            out.append(f"czech.conflicts_resolved: {code} is not a candidate")
        if not entry["rejected"]:
            out.append(f"czech.conflicts_resolved[{code}]: nothing was rejected")
        if code not in named:
            out.append(f"czech.conflicts_resolved[{code}]: resolves a conflict for no entry")
            continue
        # A resolution can be overtaken. K31's name was settled between two
        # generators and then changed on 2026-10-22 for a different reason: it
        # named the defect where the sheet asks about a property. The record
        # keeps what was resolved that day and says it no longer holds, which a
        # rewrite of `kept` would have erased. It may say so only where the
        # entry carries the rewording, so this cannot quietly excuse a drift.
        if entry.get("superseded_on"):
            if czech["candidates"][code].get("reworded_on") != entry["superseded_on"]:
                out.append(
                    f"czech.conflicts_resolved[{code}].{entry['field']}: "
                    "superseded on a date the entry does not record as a rewording"
                )
            continue
        kept = czech["candidates"][code].get(entry["field"])
        if kept != entry["kept"]["text"]:
            out.append(
                f"czech.conflicts_resolved[{code}].{entry['field']}: "
                "the kept text is not the one in the entry"
            )
    return out


def _code(candidate: str) -> int:
    return int(candidate[1:])


if __name__ == "__main__":
    found = problems(load(), json.loads(REPORTS_PATH.read_text(encoding="utf-8")))
    found += property_problems(load(), load_properties())
    found += czech_problems(load(), load_czech())
    for line in found:
        print(line)
    raise SystemExit(1 if found else 0)
