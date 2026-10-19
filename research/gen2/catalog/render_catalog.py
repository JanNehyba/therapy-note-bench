"""Draw `catalog.json` as one self-contained page, `docs/gen2-catalog.html`.

Deterministic: the same catalog gives the same bytes, and the suite compares
the published page with a fresh rendering. Nothing on the page is typed here;
every sentence and every count comes from the catalog, so the page cannot say
something the record does not.
"""

from __future__ import annotations

import html
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE_PATH = HERE.parents[2] / "docs" / "gen2-catalog.html"
OPERATIONAL_PATH = HERE / "operational.json"
REPO_URL = "https://github.com/JanNehyba/therapy-note-bench"
BLOB = REPO_URL + "/blob/main/"


def _catalog_module():
    spec = importlib.util.spec_from_file_location("gen2_catalog", HERE / "catalog.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("gen2_catalog", module)
    spec.loader.exec_module(module)
    return module


STYLE = """
  :root { color-scheme: light dark; --bg: #fdfcf8; --fg: #1b1a17; --ink: #3b3931;
          --muted: #6c695f; --line: #e4e0d5; --accent: #1e5c44; --raise: #f3f0e7;
          --warn: #8a5a00; }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #16150f; --fg: #ece8dc; --ink: #cfcabc; --muted: #9a958a;
            --line: #33302a; --accent: #7cc1a4; --raise: #211f18; --warn: #e0a83a; }
  }
  html { background: var(--bg); color: var(--fg); }
  body { margin: 0; font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
  main { max-width: 68rem; margin: 0 auto; padding: 1.5rem 1rem 4rem; }
  h1 { font-size: 1.8rem; margin: 0 0 .25rem; }
  h2 { font-size: 1.3rem; margin: 2.5rem 0 .5rem; border-top: 1px solid var(--line);
       padding-top: 1rem; }
  h3 { font-size: 1.05rem; margin: 1.5rem 0 .25rem; }
  p, li, td, th, dd, dt { color: var(--ink); }
  .sub { color: var(--muted); margin: 0 0 1rem; }
  .notice { border-left: 3px solid var(--warn); padding: .5rem .9rem; background: var(--raise);
            margin: 1rem 0; }
  nav ul { display: flex; flex-wrap: wrap; gap: .25rem 1rem; padding: 0; list-style: none; }
  a { color: var(--accent); }
  table { border-collapse: collapse; width: 100%; font-size: .9rem; margin: .5rem 0 1rem; }
  th, td { text-align: left; vertical-align: top; padding: .35rem .5rem;
           border-bottom: 1px solid var(--line); }
  th { color: var(--muted); font-weight: 600; }
  .scroll { overflow-x: auto; }
  dl { display: grid; grid-template-columns: minmax(8rem, 12rem) 1fr; gap: .2rem 1rem;
       margin: .5rem 0 1rem; }
  dt { color: var(--muted); }
  dd { margin: 0; }
  article { border-top: 1px solid var(--line); padding-top: .75rem; margin-top: 1rem; }
  .id { font-family: ui-monospace, Menlo, Consolas, monospace; color: var(--muted); }
  code { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: .9em; }
  .k { display: inline-block; padding: 0 .4rem; border: 1px solid var(--line);
       border-radius: .3rem; font-size: .85em; color: var(--muted); margin-right: .3rem; }
  footer { margin-top: 3rem; border-top: 1px solid var(--line); padding-top: 1rem;
           color: var(--muted); font-size: .9rem; }
  details summary { cursor: pointer; }
  .more { margin: .4rem 0 .2rem; padding: .5rem .7rem; background: var(--raise);
          border-radius: .3rem; max-width: 40rem; }
  .more h4 { margin: .5rem 0 .2rem; font-size: .8rem; text-transform: uppercase;
             letter-spacing: .04em; color: var(--muted); }
  .more h4:first-child { margin-top: 0; }
  .more dl { grid-template-columns: minmax(6rem, 9rem) 1fr; margin: .3rem 0; }
  .measured { font-weight: 600; }
"""


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return (
        f'<div class="scroll"><table><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
    )


def dl(pairs: list[tuple[str, str]]) -> str:
    return "<dl>" + "".join(f"<dt>{esc(k)}</dt><dd>{v}</dd>" for k, v in pairs) + "</dl>"


def chips(mapping: dict) -> str:
    return " ".join(f'<span class="k">{esc(k)}: {esc(v)}</span>' for k, v in mapping.items())


def _ledger_cell(source: dict) -> str:
    """The id this page is referred to by, and its report as a link where one exists."""
    url = ledger_url(source["ledger_report_id"])
    report = esc(source["ledger_report_id"])
    linked = f'<a href="{esc(url)}">{report}</a>' if url else f"<code>{report}</code>"
    return f'<span class="id" id="src-{esc(source["id"])}">{esc(source["id"])}</span><br>{linked}'


def _sources(catalog: dict) -> str:
    rows = [
        [
            _ledger_cell(s),
            esc(s["citation"]),
            esc(s["type"]) + "<br>" + esc(s["layer"]) + " / " + esc(s["verification"]),
            esc(s["study_family"]) + "<br>" + esc(s["population"]),
            esc(s["limitations"]),
        ]
        for s in catalog["sources"]
    ]
    out = table(
        [
            "Id and ledger report",
            "Citation",
            "Type, layer, verification",
            "Family, population",
            "Limitations",
        ],
        rows,
    )
    rows = [
        [
            _ledger_cell(s),
            esc(s["citation"]),
            esc(s["layer"]),
            esc(s["relevance"]),
        ]
        for s in catalog["abstract_sources"]
    ]
    out += "<h3>Read from the abstract only</h3>"
    out += (
        "<p>These were not retrieved in full. "
        "Every evidence line that rests on one of them says so.</p>"
    )
    out += table(["Id and ledger report", "Citation", "Layer", "Why it is here"], rows)
    return out


#: The overview's status words. The catalog's own state names stay as they are;
#: "rule_written" is not one of them, because writing a rule does not change a
#: candidate's state until an entry joins the pilot. A reader still has to see
#: that "not yet operationalized" stopped being true the day the rule was written.
STATUS_WORDS = {
    "proposed": "In the pilot proposal",
    "rule_written": "Rule written, not in the pilot",
    "not_yet_operationalized": "No rule yet",
    "not_measured": "Not measured this round",
    "out_of_scope": "Outside this study",
    "awaiting_raters": "No suitable rater",
    "lacking_evidence": "No source supports it",
    "irrelevant": "Not a quality property",
    "measurement_failed": "Measurement failed",
}


def _status(candidate: dict, written: set[str]) -> str:
    if candidate["state"] != "proposed" and candidate["id"] in written:
        return "rule_written"
    return candidate["state"]


def _labelled(kind: str, mapping: dict) -> list[tuple[str, str]]:
    return [(f"{kind}: {label}", esc(text)) for label, text in mapping.items()]


def _rule(candidate: dict, catalog: dict, operational: dict) -> tuple[str, str]:
    """The rule a rater or a program applies to one candidate, and where it is recorded."""
    key = candidate["id"]
    for m in operational["measurements"]:
        if m["construct_id"] == key:
            pairs = [("Question", esc(m["question"]))]
            pairs += _labelled("Answer", m["anchors"]) + _labelled("Example", m["examples"])
            return m["id"], f"<p>{esc(m['definition'])}</p>" + dl(pairs)
    for m in operational["methods"]:
        if key in m["construct_ids"]:
            shared = f"<p>One method shared by {esc(', '.join(m['construct_ids']))}.</p>"
            return (
                f"method {m['id']}",
                f"<p>{esc(m['definition'])}</p>" + dl(_labelled("Outcome", m["outcomes"])) + shared,
            )
    for m in operational["rules_written_not_in_this_round"]["items"]:
        if m["construct_id"] == key:
            pairs = [("Question", esc(m["question"]))]
            pairs += _labelled("Answer", m["anchors"]) + _labelled("Example", m["examples"])
            pairs.append(("Rater", esc(m["rater"])))
            return m["id"], f"<p>{esc(m['definition'])}</p>" + dl(pairs)
    for p in catalog["pilot_proposal"]["entries"]:
        if key in p["measures"]:
            pairs = [
                ("Entry", esc(p["label"])),
                ("Unit", esc(p["unit"])),
                ("Answer", esc(p["format"])),
            ]
            return f"pilot entry {p['id']}", f"<p>{esc(candidate['measurement'])}</p>" + dl(pairs)
    return "", ""


def _cite(source: dict) -> str:
    """Author and year where the citation opens with a person, else what names the work."""
    citation = source["citation"]
    year = re.search(r"\b(19|20)\d{2}\b", citation)
    if " et al" in citation[:40] or re.match(r"[A-Z][a-z]+ [A-Z]{1,3}[,.]", citation):
        name = citation.split()[0]
    else:
        name = source.get("study_family") or citation.split(".")[0]
        if len(name) > 40:
            name = name[:37].rstrip() + "..."
    return f"{name} {year.group(0)}" if year else name


def _overview(catalog: dict, operational: dict) -> str:
    """Every candidate on one row, the rule and the reason one click away."""
    written = {r["construct_id"] for r in operational["rules_written_not_in_this_round"]["items"]}
    family = {f["id"]: f["label"] for f in catalog["families"]}
    full = {s["id"]: s for s in catalog["sources"]}
    names = {s["id"]: s for s in catalog["sources"] + catalog["abstract_sources"]}
    basis = catalog["decision_basis"]
    rows = []
    for c in catalog["candidates"]:
        status = _status(c, written)
        where, rule = _rule(c, catalog, operational)
        if rule:
            rule = f"<h4>Rule ({esc(where)})</h4>{rule}"
        else:
            rule = f"<h4>Proposed measurement, no rule written</h4><p>{esc(c['measurement'])}</p>"
        cited = []
        for e in c["evidence"]:
            label = _cite(names[e["source"]]) + ("" if e["source"] in full else " (abstract)")
            if label not in cited:
                cited.append(label)
        rows.append(
            [
                f'<span class="id">{esc(c["id"])}</span>',
                f"<details><summary><b>{esc(c['label'])}</b></summary>"
                f'<div class="more"><h4>Definition</h4><p>{esc(c["definition"])}</p>{rule}'
                f"<h4>Why it stands here</h4><p>{esc(c['state_note'])}</p></div></details>",
                esc(family[c["family"]]),
                esc(c["unit"]),
                f'<span title="{esc(basis[c["decided_by"]])}">{esc(c["decided_by"])}</span>',
                esc("; ".join(cited)),
                f'<span class="{"measured" if status == "proposed" else ""}">'
                f"{esc(STATUS_WORDS[status])}</span>",
            ]
        )
    used = {_status(c, written) for c in catalog["candidates"]}
    meaning = {
        **catalog["candidate_states"],
        "rule_written": operational["rules_written_not_in_this_round"]["why_here"],
    }
    legend = dl([(STATUS_WORDS[s], esc(meaning[s])) for s in STATUS_WORDS if s in used])
    decided = dl([(k, esc(v)) for k, v in basis.items()])
    return (
        f'<p class="notice">{esc(catalog["pilot_proposal"]["status"])}</p>'
        "<p>One row per candidate. Open a name for its definition, the rule a rater or a "
        "program applies, and why it stands where it does.</p>"
        + table(
            ["Id", "Candidate", "Family", "Unit", "Decided by", "Sources", "Status"],
            rows,
        )
        + "<h3>What the status means</h3>"
        + legend
        + "<h3>What decides a right answer</h3>"
        + decided
    )


def _families(catalog: dict) -> str:
    return "".join(
        f'<h3><span class="id">{esc(f["id"])}</span> {esc(f["label"])}</h3>'
        f"<p>{esc(f['summary'])}</p><p><em>Boundary.</em> {esc(f['boundary'])}</p>"
        f'<p class="sub">Evidence: {esc(", ".join(f["evidence"]))}</p>'
        for f in catalog["families"]
    )


def _conditions(catalog: dict) -> str:
    rows = [
        [
            f'<span class="id">{esc(m["id"])}</span>',
            esc(m["label"]),
            esc(m["evidence"]),
            esc(m["detail"]),
        ]
        for m in catalog["conditions"]
    ]
    return table(["Id", "Condition", "Evidence", "Detail"], rows)


#: Shared with the Czech renderer, so one table decides which ids can be linked.
ledger_url = _catalog_module().ledger_url


def _source_cell(source: dict, *, abstract_only: bool) -> str:
    """A citation that is the link to the study, over the id that anchors the row.

    This column used to be the bare id `S1`, which is the one thing a reader
    cannot look up. The citation names the work and carries its link; the id is
    kept underneath because the rest of the page refers to sources by it.
    """
    label = _cite(source) + (" (abstract)" if abstract_only else "")
    url = ledger_url(source["ledger_report_id"])
    cited = f'<a href="{esc(url)}">{esc(label)}</a>' if url else esc(label)
    anchor = f'<a class="id" href="#src-{esc(source["id"])}">{esc(source["id"])}</a>'
    # An id that resolves nowhere says so by showing itself: the reader can see
    # that there is no link rather than wonder why the citation is not one.
    tail = "" if url else f"<br><code>{esc(source['ledger_report_id'])}</code>"
    return f"{cited}<br>{anchor}{tail}"


def _evidence(rows: list[dict], sources: dict[str, dict], full: set[str]) -> str:
    return table(
        ["Source", "Location", "Excerpt", "What it supports", "Our adaptation"],
        [
            [
                _source_cell(sources[e["source"]], abstract_only=e["source"] not in full),
                esc(e["location"]),
                esc(e["quote"]),
                esc(e["supports"]),
                esc(e["our_adaptation"]),
            ]
            for e in rows
        ],
    )


def _candidates(catalog: dict) -> str:
    sources = {s["id"]: s for s in catalog["sources"] + catalog["abstract_sources"]}
    full = {s["id"] for s in catalog["sources"]}
    out = []
    for c in catalog["candidates"]:
        tags = chips(
            {
                "family": c["family"],
                "kind": c["kind"],
                "origin": c["origin"],
                "state": c["state"],
            }
        )
        out.append(
            f'<article id="{esc(c["id"])}">'
            f'<h3><span class="id">{esc(c["id"])}</span> {esc(c["label"])}</h3>'
            f"<p>{tags} {chips(c['relevance'])}</p>"
            f"<p>{esc(c['definition'])}</p>"
            + dl(
                [
                    ("Origin", esc(c["origin_note"])),
                    ("State", esc(c["state"]) + ". " + esc(c["state_note"])),
                    ("Response mode", esc(c["mode"])),
                    ("Unit", esc(c["unit"])),
                    ("Inputs", esc(c["inputs"])),
                    ("Applicability", esc(c["applicability"])),
                    ("Positive example", esc(c["examples"]["positive"])),
                    ("Negative example", esc(c["examples"]["negative"])),
                    ("Boundary example", esc(c["examples"]["boundary"])),
                    ("Measurement", esc(c["measurement"])),
                    ("If it fails", esc(c["error_consequence"])),
                    ("Validation", esc(c["validation"])),
                    ("Overlaps", esc(c["overlaps"])),
                ]
            )
            + _evidence(c["evidence"], sources, full)
            + "</article>"
        )
    return "".join(out)


def _methods(catalog: dict) -> str:
    out = []
    for m in catalog["methods"]:
        out.append(
            f'<article id="{esc(m["id"])}">'
            f'<h3><span class="id">{esc(m["id"])}</span> {esc(m["label"])}</h3>'
            f"<p>{chips({'readiness': m['readiness'], 'origin': m['origin']})}</p>"
            f"<p>{esc(m['what'])}</p>"
            + dl(
                [
                    ("Measures", esc(", ".join(m["measures"]) or "no construct of this catalog")),
                    ("Evidence", esc(", ".join(m["evidence"]))),
                    ("Origin", esc(m["origin_note"])),
                    ("Limits", esc(m["limits"])),
                ]
            )
            + "</article>"
        )
    return "".join(out)


def _levels(catalog: dict) -> str:
    rows = [
        [
            f'<span class="id">{esc(lv["id"])}</span>',
            esc(lv["label"]),
            esc(lv["covered"]),
            esc(lv["by"]),
            esc(lv["gap"]),
        ]
        for lv in catalog["levels"]
    ]
    return table(["Id", "Level", "Covered", "By", "Gap"], rows)


def _blind_spots(catalog: dict) -> str:
    rows = [
        [
            f'<span class="id">{esc(b["id"])}</span>',
            esc(b["label"]),
            esc(b["example"]),
            esc(b["why_invisible"]),
            esc(b["needs"]),
        ]
        for b in catalog["blind_spots"]
    ]
    return table(["Id", "Blind spot", "Example", "Why the map does not see it", "Needs"], rows)


def _pilot(catalog: dict) -> str:
    pilot = catalog["pilot_proposal"]
    out = [f'<p class="notice">{esc(pilot["status"])}</p>', f"<p>{esc(pilot['count_note'])}</p>"]
    rows = [
        [
            f'<span class="id">{esc(p["id"])}</span>',
            esc(p["record_kind"]),
            esc(p["label"]),
            esc(p["measures"]) + "<br>" + esc(p["method"]),
            esc(p["unit"]) + "<br>" + esc(p["format"]),
            esc(p["why"]),
            esc(p["human_input"]),
            esc(p["risk"]),
            esc(p["saturation"])
            + "<br>"
            + esc(p["saturation_source"])
            + "<br>"
            + esc(p["saturation_detail"]),
        ]
        for p in pilot["entries"]
    ]
    out.append(
        table(
            [
                "Id",
                "Record kind",
                "Entry",
                "Measures, method",
                "Unit, format",
                "Why",
                "Human input",
                "Risk",
                "Room to measure",
            ],
            rows,
        )
    )
    out.append("<h3>Criteria the proposal applied</h3>")
    out.append(
        table(
            ["Id", "Criterion", "Detail"],
            [
                [esc(c["id"]), esc(c["criterion"]), esc(c["detail"])]
                for c in pilot["applied_criteria"]
            ],
        )
    )
    out.append("<h3>Rules deliberately not used</h3>")
    out.append(
        table(
            ["Rule", "Why not"],
            [[esc(r["rule"]), esc(r["why"])] for r in pilot["deliberately_not_used"]],
        )
    )
    out.append("<h3>Left out, and why</h3>")
    out.append(
        table(
            ["Candidate", "Reason"],
            [[esc(r["candidate"]), esc(r["reason"])] for r in pilot["left_out"]],
        )
    )
    return "".join(out)


def _comparison(catalog: dict) -> str:
    rows = [
        [
            esc(row["old"] or "(new)"),
            esc(row["action"]),
            esc(row["new"] or "(none)"),
            esc(row["reason"]),
        ]
        for row in catalog["comparison"]
    ]
    return table(["Earlier criterion", "Action", "Catalog entry", "Reason"], rows)


def _revisions(catalog: dict) -> str:
    """What changed after the first assembly, and on whose finding."""
    return "<h3>Revisions</h3>" + "".join(
        f"<p>{esc(r['date'])}, {esc(r['reason'])}:</p><ul>"
        + "".join(f"<li>{esc(change)}</li>" for change in r["changes"])
        + "</ul>"
        for r in catalog["revisions"]
    )


def _source_properties(props: dict, catalog: dict) -> str:
    """The inductive half: what each source itself says quality is, then the mapping."""
    names = {c["id"]: c["label"] for c in catalog["candidates"]}
    counts = props["counts"]
    out = [
        f"<p>{esc(props['method'])}</p>",
        f"<p><em>Rule.</em> {esc(props['rule'])}</p>",
        "<p>"
        + esc(
            f"{counts['properties']} properties from {counts['sources_defining_properties']} "
            f"sources; {counts['properties_mapped']} map to a candidate and "
            f"{counts['properties_unmapped']} do not; {counts['candidates_with_source_property']} "
            f"candidates rest on at least one source property and "
            f"{counts['candidates_without_source_property']} on none."
        )
        + "</p>",
    ]
    out.append("<h3>Open properties: found in a source, covered by no candidate</h3>")
    out.append(
        table(
            ["Property", "Source", "Disposition", "Reason"],
            [
                [
                    esc(row["pid"]) + " " + esc(row["label"]),
                    esc(row["source"]),
                    # A row opened and not yet decided carries a proposal; the
                    # page says which of the two it is rather than reading as
                    # though the investigator had already answered.
                    esc(row.get("disposition") or "undecided; proposal: " + row["proposal"]),
                    esc(row["reason"]),
                ]
                for row in catalog["open_source_properties"]
            ],
        )
    )
    out.append("<h3>Candidates with no source property behind them</h3>")
    out.append(
        table(
            ["Candidate", "Declared origin", "Reading"],
            [
                [esc(row["id"]) + " " + esc(row["label"]), esc(row["origin"]), esc(row["reading"])]
                for row in props["candidates_without_source_property"]
            ],
        )
    )
    for s in props["sources"]:
        title = (
            f'<h3 id="props-{esc(s["id"])}"><span class="id">{esc(s["id"])}</span> '
            f"{esc(s['citation'])}</h3>"
        )
        if not s["defines_note_quality"]:
            out.append(title + f'<p class="sub">{esc(s["note"])}</p>')
            continue
        out.append(
            title
            + f'<p class="sub">{esc(s["read"])}{"; " + esc(s["note"]) if s["note"] else ""}</p>'
        )
        out.append(
            table(
                [
                    "Id",
                    "Property, as the source names it",
                    "Kind",
                    "Location",
                    "Quote",
                    "Maps to",
                    "Mapping",
                ],
                [
                    [
                        f'<span class="id">{esc(p["pid"])}</span>',
                        esc(p["label"]),
                        esc(p["kind"]),
                        esc(p["location"]),
                        esc(p["quote"] or ""),
                        esc(", ".join(f"{k} {names.get(k, '')}" for k in p["maps_to"]) or "none"),
                        esc(p["mapping"]),
                    ]
                    for p in s["properties"]
                ],
            )
        )
    return "".join(out)


def _glossary(title: str, mapping) -> str:
    """A named vocabulary: definitions when the catalog gives them, else the values."""
    if isinstance(mapping, dict):
        return f"<h3>{esc(title)}</h3>" + dl([(k, esc(v)) for k, v in mapping.items()])
    return f"<h3>{esc(title)}</h3><p>{esc(', '.join(mapping))}</p>"


def render(catalog: dict, props: dict | None = None, operational: dict | None = None) -> str:
    if props is None:
        props = _catalog_module().load_properties()
    if operational is None:
        operational = json.loads(OPERATIONAL_PATH.read_text(encoding="utf-8"))
    n = {
        "candidates": len(catalog["candidates"]),
        "methods": len(catalog["methods"]),
        "sources": len(catalog["sources"]),
        "abstracts": len(catalog["abstract_sources"]),
        "entries": len(catalog["pilot_proposal"]["entries"]),
        "comparison": len(catalog["comparison"]),
    }
    sections = [
        (
            "overview",
            f"All {n['candidates']} candidates in one table",
            lambda c: _overview(c, operational),
        ),
        ("status", "Status and policies", None),
        ("sources", f"Sources ({n['sources']} read, {n['abstracts']} abstract-only)", _sources),
        (
            "source-properties",
            "What the sources themselves define as quality "
            f"({props['counts']['properties']} properties)",
            lambda c: _source_properties(props, c),
        ),
        ("families", "Families, an organising aid", _families),
        ("conditions", "Conditions of measurement", _conditions),
        ("candidates", f"Candidate constructs ({n['candidates']})", _candidates),
        ("methods", f"Methods ({n['methods']})", _methods),
        ("levels", "Levels of measurement", _levels),
        ("blind-spots", "Blind spots of the earlier map", _blind_spots),
        ("pilot", f"Pilot proposal ({n['entries']} entries)", _pilot),
        (
            "comparison",
            f"Comparison with the earlier criteria map ({n['comparison']} rows)",
            _comparison,
        ),
    ]
    nav = (
        "<nav><ul>"
        + "".join(f'<li><a href="#{sid}">{esc(title)}</a></li>' for sid, title, _ in sections)
        + "</ul></nav>"
    )
    status = (
        f'<p class="notice">{esc(catalog["status"])}</p>'
        + dl(
            [
                ("Review date", esc(catalog["review_date"])),
                ("Catalog date", esc(catalog["catalog_date"])),
                ("Catalog version", esc(catalog["version"])),
                ("Language policy", esc(catalog["language_policy"])),
                ("Origin policy", esc(catalog["origin_policy"])),
                ("Assembled from", esc(catalog["provenance"]["assembled_from"])),
                ("Translated by", esc(catalog["provenance"]["translated_by"])),
                ("Rule", esc(catalog["provenance"]["rule"])),
                ("Families", esc(catalog["families_policy"])),
            ]
        )
        + _revisions(catalog)
        + _glossary("Origin values", catalog["origin_values"])
        + _glossary("Candidate states", catalog["candidate_states"])
        + _glossary("Record kinds of a candidate", catalog["record_kinds"])
        + _glossary("Record kinds of a pilot entry", catalog["pilot_record_kinds"])
        + _glossary("Purposes", catalog["purposes"])
        + _glossary("Relevance levels", catalog["relevance_levels"])
        + _glossary("Evidence layers", catalog["evidence_layers"])
    )
    body = []
    for sid, title, draw in sections:
        body.append(f'<h2 id="{sid}">{esc(title)}</h2>')
        body.append(status if draw is None else draw(catalog))
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>therapy-note-bench — Gen-2 candidate catalog</title>\n"
        f"<style>{STYLE}</style>\n</head>\n<body>\n<main>\n"
        "<h1>Gen-2 candidate catalog</h1>\n"
        '<p class="sub">What the scoping search proposed for a bilingual instrument of '
        "psychotherapy note quality, entry by entry, with the evidence each rests on. "
        'Part of <a href="index.html">therapy-note-bench</a>; the generation this page '
        "belongs to is in preparation and nothing here is scored on the leaderboard.</p>\n"
        + nav
        + "\n"
        + "\n".join(body)
        + "\n<footer><p>Generated from "
        f'<a href="{BLOB}research/gen2/catalog/catalog.json">'
        "research/gen2/catalog/catalog.json</a> by "
        f'<a href="{BLOB}research/gen2/catalog/render_catalog.py">render_catalog.py</a>. '
        "The research protocol is "
        f'<a href="{BLOB}research/gen2/protocol.json">research/gen2/protocol.json</a>; '
        "what the review sought and read, report by report, is "
        f'<a href="{BLOB}research/gen2/review-2026-09-13/reports.json">its ledger</a>. '
        'Back to <a href="index.html">the leaderboard</a> or '
        '<a href="methods.html">the methods page</a>.</p></footer>\n'
        "</main>\n</body>\n</html>\n"
    )


if __name__ == "__main__":
    module = _catalog_module()
    catalog = module.load()
    found = module.problems(catalog)
    if found:
        print("\n".join(found))
        raise SystemExit(1)
    PAGE_PATH.write_bytes(render(catalog).encode("utf-8"))
    print("wrote", PAGE_PATH.relative_to(HERE.parents[2]).as_posix())
