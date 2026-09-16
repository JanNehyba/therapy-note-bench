"""Draw `catalog.json` as one self-contained page, `docs/gen2-catalog.html`.

Deterministic: the same catalog gives the same bytes, and the suite compares
the published page with a fresh rendering. Nothing on the page is typed here;
every sentence and every count comes from the catalog, so the page cannot say
something the record does not.
"""

from __future__ import annotations

import html
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE_PATH = HERE.parents[2] / "docs" / "gen2-catalog.html"
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


def _sources(catalog: dict) -> str:
    rows = [
        [
            f'<span class="id">{esc(s["id"])}</span><br><code>{esc(s["ledger_report_id"])}</code>',
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
            f'<span class="id">{esc(s["id"])}</span><br><code>{esc(s["ledger_report_id"])}</code>',
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


def _evidence(rows: list[dict]) -> str:
    return table(
        ["Source", "Location", "Excerpt", "What it supports", "Our adaptation"],
        [
            [
                esc(e["source"]),
                esc(e["location"]),
                esc(e["quote"]),
                esc(e["supports"]),
                esc(e["our_adaptation"]),
            ]
            for e in rows
        ],
    )


def _candidates(catalog: dict) -> str:
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
            + _evidence(c["evidence"])
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


def _glossary(title: str, mapping) -> str:
    """A named vocabulary: definitions when the catalog gives them, else the values."""
    if isinstance(mapping, dict):
        return f"<h3>{esc(title)}</h3>" + dl([(k, esc(v)) for k, v in mapping.items()])
    return f"<h3>{esc(title)}</h3><p>{esc(', '.join(mapping))}</p>"


def render(catalog: dict) -> str:
    n = {
        "candidates": len(catalog["candidates"]),
        "methods": len(catalog["methods"]),
        "sources": len(catalog["sources"]),
        "abstracts": len(catalog["abstract_sources"]),
        "entries": len(catalog["pilot_proposal"]["entries"]),
        "comparison": len(catalog["comparison"]),
    }
    sections = [
        ("status", "Status and policies", None),
        ("sources", f"Sources ({n['sources']} read, {n['abstracts']} abstract-only)", _sources),
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
