"""The one Czech table of the candidate catalog, generated.

Five hand-run scripts in a temp directory had produced five Czech views of the
same criteria, and on 2026-10-13 they claimed 36, 34, 33, 17 and 16 of them. The
counts had been written into the pages by hand, so each was correct on the day
it ran and wrong the day after; one was six days old and sixteen criteria short.
A panel shown the wrong one would rate a different instrument.

So this is the only Czech view, it is generated from `catalog.json` and
`czech.json`, and it counts rather than states: no number on the page is typed
anywhere. The header carries the catalog digest, so a stale copy says so instead
of having to be recounted.

Writes into a gitignored directory, because the published pages are English.
Carries no Czech of its own: the wording is in `czech.json`, which keeps this
file public-safe like the rest of the catalog scripts.
"""

from __future__ import annotations

import hashlib
import html
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OPERATIONAL_PATH = HERE / "operational.json"
CATALOG_PATH = HERE / "catalog.json"
OUT = REPO / "local" / "kriteria-cesky.html"


def _catalog_module():
    spec = importlib.util.spec_from_file_location("gen2_catalog", HERE / "catalog.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("gen2_catalog", module)
    spec.loader.exec_module(module)
    return module


esc = html.escape

STYLE = """
:root{color-scheme:light dark;--bg:#fcfcfb;--panel:#f3f2ed;--ink:#0b0b0b;--ink2:#52514e;
--mut:#79776f;--line:#e2e0d8;--src:#2a78d6;--norm:#1baf7a;--note:#4a3aa7;--rater:#eb6834;
--ind:#79776f}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#1a1a19;--panel:#232321;
--ink:#fff;--ink2:#c3c2b7;--mut:#9b998f;--line:#35352f;--src:#3987e5;--norm:#199e70;
--note:#9085e9;--rater:#d95926;--ind:#9b998f}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);padding:1.5rem 1rem 4rem;
font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:94rem;margin:0 auto}
h1{font-size:1.5rem;margin:0 0 .3rem}
p{margin:.4rem 0;max-width:68rem;color:var(--ink2)}
.bar{display:flex;gap:.5rem;margin:1rem 0 .4rem;flex-wrap:wrap}
button{font:inherit;padding:.35rem .9rem;border-radius:.3rem;border:1px solid var(--line);
background:var(--panel);color:var(--ink);cursor:pointer}
button[aria-pressed=true]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.wrap{overflow-x:auto}
table{border-collapse:collapse;width:100%;min-width:60rem}
th,td{border-top:1px solid var(--line);padding:.42rem .5rem;text-align:left;vertical-align:top}
th{position:sticky;top:0;background:var(--panel);font-size:.75rem;letter-spacing:.04em;
text-transform:uppercase;color:var(--mut);z-index:1}
tr.off{color:var(--mut)} tr.off b{font-weight:600}
td.id{font-family:ui-monospace,monospace;color:var(--mut);white-space:nowrap}
.ask{color:var(--ink2);font-size:.92rem} .small{font-size:.88rem}
.gap{color:var(--mut);font-style:italic}
.chip{display:inline-block;padding:.02rem .42rem;border-radius:1rem;font-size:.8rem;
border:1px solid;white-space:nowrap}
.chip.src{color:var(--src);border-color:var(--src)}
.chip.norm{color:var(--norm);border-color:var(--norm)}
.chip.note{color:var(--note);border-color:var(--note)}
.chip.rater{color:var(--rater);border-color:var(--rater)}
.chip.ind{color:var(--ind);border-color:var(--ind)}
footer{margin-top:2rem;border-top:1px solid var(--line);padding-top:.7rem;color:var(--mut);
font-size:.85rem}
"""

SCRIPT = """
const rows = [...document.querySelectorAll('tbody tr')];
const btns = [...document.querySelectorAll('button[data-f]')];
function show(f) {
  btns.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.f === f)));
  rows.forEach(r => {
    const on = r.dataset.on === 'true';
    r.hidden = (f === 'on' && !on) || (f === 'off' && on);
  });
}
btns.forEach(b => b.onclick = () => show(b.dataset.f));
show('all');
"""

#: Which css class paints the basis chip. The vocabulary itself is Czech and
#: lives in czech.json; only the colour is decided here.
CHIP = {
    "source": "src",
    "norm": "norm",
    "note": "note",
    "rater": "rater",
    "derived": "ind",
    "indicator": "ind",
}


def short_cite(citation: str) -> str:
    """Author and year, or the title's opening where the first word is not a surname."""
    year = re.search(r"(19|20)\d{2}", citation)
    head = re.split(r"\s+et al\.|,|\.\s", citation.strip())[0].split()
    name = head[0] if head else "?"
    if name.lower().strip(",.:") in {
        "the",
        "clinical",
        "development",
        "race",
        "errors",
        "quality",
        "what",
        "objective",
        "american",
        "decree",
        "benefits",
        "assessing",
        "preliminary",
        "updated",
        "prisma",
    }:
        name = " ".join(citation.split()[:4]).rstrip(",.:")
    return f"{name} {year.group(0) if year else ''}".strip()


def sources_for(catalog: dict, abstract_only_suffix: str) -> dict[str, str]:
    """One short citation list per candidate, abstract-only sources marked.

    A source read only in abstract supports a candidate more weakly than one
    read in full, and the page has to show which is which or it overstates its
    own evidence.
    """
    cite = {
        s["id"]: short_cite(s["citation"]) for s in catalog["sources"] + catalog["abstract_sources"]
    }
    full = {s["id"] for s in catalog["sources"]}
    out = {}
    for candidate in catalog["candidates"]:
        seen: list[str] = []
        for evidence in candidate["evidence"]:
            label = cite[evidence["source"]]
            if evidence["source"] not in full:
                label += abstract_only_suffix
            if label not in seen:
                seen.append(label)
        out[candidate["id"]] = "; ".join(seen)
    return out


def render(catalog: dict, czech: dict, operational: dict, stamp: str, digest: str) -> str:
    page = czech["page"]
    labels = page["states"]
    with_rule = {k for m in operational["methods"] for k in m["construct_ids"]} | {
        x["construct_id"] for x in operational["measurements"]
    }
    written = {r["construct_id"] for r in operational["rules_written_not_in_this_round"]["items"]}
    basis_cz = czech["vocabulary"]["basis"]
    why_cz = czech["vocabulary"]["why_state"]
    groups = {
        code: name for name, members in czech["groupings"]["our_groups"].items() for code in members
    }
    cites = sources_for(catalog, page["abstract_only"])

    body = []
    measured = 0
    for candidate in catalog["candidates"]:
        code = candidate["id"]
        entry = czech["candidates"][code]
        on = candidate["state"] == "proposed"
        measured += on
        if on:
            state = f"<b>{esc(labels['measured'])}</b>"
            rule = labels["rule_yes"] if code in with_rule else labels["rule_other"]
        else:
            # "the rule is missing" was the label for every unmeasured candidate
            # and stopped being true once the rules were written: what is missing
            # then is not the rule but a place in the round.
            if candidate["state"] == "not_yet_operationalized" and code in written:
                state = esc(labels["rule_but_no_round"])
            else:
                state = esc(why_cz[candidate["state"]])
            rule = labels["rule_written_not_used"] if code in written else labels["none"]
        chip = CHIP[candidate["decided_by"]]
        question = entry.get("question")
        asked = esc(question) if question else f"<span class=gap>{esc(page['no_question'])}</span>"
        unit = entry.get("unit")
        counted = f"<b>{esc(unit)}</b>" if unit else f"<span class=gap>{esc(labels['none'])}</span>"
        body.append(
            f"<tr class='{'on' if on else 'off'}' data-on='{str(on).lower()}'>"
            f"<td class=id>{esc(code)}</td>"
            f"<td><b>{esc(entry['name'])}</b></td>"
            f"<td class=ask>{asked}</td>"
            f"<td class=small>{esc(groups.get(code, labels['none']))}</td>"
            f"<td class=small>{esc(cites[code] or labels['none'])}</td>"
            f"<td class=small>{counted}</td>"
            f"<td class=small><span class='chip {chip}'>{esc(basis_cz[candidate['decided_by']])}"
            f"</span></td>"
            f"<td class=small>{esc(rule)}</td>"
            f"<td class=small>{state}</td></tr>"
        )

    total = len(catalog["candidates"])
    counts = {"all": total, "on": measured, "off": total - measured}
    buttons = "".join(
        f"<button data-f={key}>{esc(label)} ({counts[key]})</button>"
        for key, label in page["filters"].items()
    )
    headers = "".join(f"<th>{esc(column)}</th>" for column in page["columns"])
    intro = "".join(f"<p>{paragraph}</p>" for paragraph in page["intro"])
    generated = page["generated"].format(stamp=esc(stamp), digest=esc(digest[:12]))
    return (
        "<!doctype html><html lang=cs><head><meta charset=utf-8>\n"
        '<meta name=viewport content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(page['title'])}</title><style>{STYLE}</style></head><body><main>\n"
        f"<h1>{esc(page['title'])}</h1>\n{intro}\n"
        f"<p class=small>{generated} {esc(page['stale'])}</p>\n"
        f"<div class=bar>{buttons}</div>\n"
        f"<div class=wrap><table><thead><tr>{headers}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>\n"
        f"<footer>{page['footer']}</footer>\n"
        f"<script>{SCRIPT}</script></main></body></html>\n"
    )


def main() -> int:
    catalog = _catalog_module()
    cat = catalog.load()
    czech = catalog.load_czech()
    problems = catalog.czech_problems(cat, czech)
    if problems:
        for line in problems:
            print(line)
        return 2
    operational = json.loads(OPERATIONAL_PATH.read_text(encoding="utf-8"))
    # The digest is of the bytes on disk, not of the parsed object: what a
    # reader needs to know is whether this page was made from the file they are
    # looking at.
    digest = hashlib.sha256(CATALOG_PATH.read_bytes()).hexdigest()
    stamp = datetime.now().strftime("%d. %m. %Y %H:%M")
    page = render(cat, czech, operational, stamp, digest)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(page.encode("utf-8"))
    print(f"wrote {OUT} | candidates: {len(cat['candidates'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
