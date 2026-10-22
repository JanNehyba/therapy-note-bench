"""Build the rating sheet for the content-validity panel, one file per rater.

Each rater answers on their own copy, because a shared sheet makes the second
answer a reaction to the first. Items are shown blind: the code, the Czech name
and one statement, in a fixed random order drawn from a recorded seed, with no
state, no origin and no citation, so a rater judges rather than ratifies.

The sheet was first built on 2026-10-07 by a script in a temp directory, which
left three CSV files nobody could regenerate. The order depends on a seed and
the panel's answers depend on the order, so a sheet that cannot be rebuilt is a
sheet whose results cannot be checked. It is generated from `catalog.json` and
`czech.json` and carries no wording of its own; the Czech lives in the data, as
it does for every other script here, so this file stays public-safe.

Writes into a gitignored directory: the sheets go to people, and what comes back
is answers about an instrument, which belong in the record and not in a view.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT_DIR = REPO / "local" / "panel"


def _catalog_module():
    spec = importlib.util.spec_from_file_location("gen2_catalog", HERE / "catalog.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("gen2_catalog", module)
    spec.loader.exec_module(module)
    return module


#: Recorded before the first answer existed. The order is part of the method:
#: re-drawing it would make two panels incomparable, so it never changes.
SEED = 20261007

#: The raters, read from a gitignored file so that no name enters this
#: repository, which is public. Each entry gives a surname and which purpose
#: that rater sees first; the order alternates so that four people tired on the
#: same tab do not make fatigue look like a difference between purposes. Without
#: the file the sheets are numbered, which is what the tests build.
RATERS_FILE = "raters.json"
NUMBERED = ({"surname": "1", "first": None}, {"surname": "2", "first": None})


def raters() -> list[dict]:
    # The directory is read at call time, not at import: a test that redirects
    # OUT_DIR must not reach the real file, or the suite depends on one machine
    # and prints four people's names while it runs.
    path = OUT_DIR / RATERS_FILE
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["raters"]
    return [dict(r) for r in NUMBERED]


#: The instruction line the four scale steps replace. The steps live in
#: czech.json with the rest of the Czech; a sheet that spelled them out here
#: could drift from the rule that counts them.
ANCHORS = "{anchors}"

#: The instruction line that the tab's own note type replaces.
PURPOSE = "{purpose}"


def order(codes: list[str], seed: int = SEED) -> list[str]:
    shuffled = sorted(codes)
    random.Random(seed).shuffle(shuffled)
    return shuffled


def rows(czech: dict, codes: list[str], catalog: dict, purpose: str = None) -> list[list[str]]:
    """One tab: the framing, the purpose it asks about, and every candidate.

    `purpose` names which of the two note types this tab is about. The two are
    not two versions of one thing -- the American rule keeps diagnosis, plan,
    symptoms, prognosis and progress out of a therapeutic note by name -- so a
    property may be essential on one tab and pointless on the other, and the
    rater answers each on its own tab without seeing the other answer.
    """
    sheet = czech["panel_sheet"]
    scale = czech["vocabulary"]["relevance_scale"]
    purposes = sheet["purposes"]
    purpose = purpose or next(iter(purposes))
    if purpose not in purposes:
        raise SystemExit(f"unknown purpose {purpose!r}")
    # The instruction tells the rater how many properties follow, and it used to
    # say so in a typed number: it read 36 while the sheet listed 39, true on
    # 2026-10-07 and false from 2026-10-14, when three criteria arrived and
    # nothing re-read the sentence. The count is filled from the list it counts,
    # so the sentence cannot be wrong without the sheet being empty.
    out = []
    for line in sheet["instructions"]:
        # One instruction line is a placeholder for the scale, so that the four
        # steps and what they mean are written once, in the data, and the sheet
        # cannot disagree with the rule that reads them.
        if line and line[0] == PURPOSE:
            out.append([purposes[purpose]["description"]])
            out.append([sheet["both_tabs"]])
            continue
        if line and line[0] == ANCHORS:
            out.extend([f"{step['label']} \u2014 {step['anchor']}"] for step in scale)
            continue
        out.append([cell.format(count=len(codes)) for cell in line])
    out.append(list(sheet["header"]))
    # What the property is judged over. Thirty-six of the thirty-nine are about
    # one note, one is about several sessions with a client and two about a model
    # across clients, and until 2026-10-21 the sheet did not say so -- so for
    # those three a rater was answering a question about a single note that
    # nobody had asked. The Czech label lives in czech.json like every other
    # word on the sheet; the catalog holds which label applies.
    units = czech["vocabulary"]["unit_of_analysis"]
    judged_over = {c["id"]: units[c["unit_of_analysis"]] for c in catalog["candidates"]}
    for code in order(codes):
        entry = czech["candidates"][code]
        # A criterion written as the absence of a fault has a positive example
        # that reads as an ordinary sentence, so the pair goes in and not the
        # one: the rater is shown the phenomenon and its opposite rather than
        # asked to imagine what a definition covers.
        example = "\n".join(
            (
                czech["vocabulary"]["example_labels"]["positive"] + " " + entry["example_positive"],
                czech["vocabulary"]["example_labels"]["negative"] + " " + entry["example"],
            )
        )
        out.append(
            [code, entry["name"], entry["statement"], example, judged_over[code], "", "", ""]
        )
    out.extend(list(line) for line in sheet["tail"])
    return out


def as_csv(table: list[list[str]]) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(table)
    return buf.getvalue()


def main() -> int:
    catalog = _catalog_module()
    cat = catalog.load()
    czech = catalog.load_czech()
    problems = catalog.czech_problems(cat, czech)
    if problems:
        # A sheet built from a drifted file is a sheet whose results answer a
        # question nobody asked. Five views once claimed five different counts.
        for line in problems:
            print(line)
        return 2

    codes = catalog.ids(cat, "candidates")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    names = list(czech["panel_sheet"]["purposes"])
    written = 0
    for rater in raters():
        first = rater.get("first") or names[0]
        order_of_tabs = [first] + [p for p in names if p != first]
        for position, purpose in enumerate(order_of_tabs, start=1):
            table = rows(czech, codes, cat, purpose)
            name = f"hodnoceni-{rater['surname']}-{position}-{purpose}.csv"
            (OUT_DIR / name).write_text(as_csv(table), encoding="utf-8")
            written += 1
    (OUT_DIR / "poradi.json").write_text(
        json.dumps(
            {
                "seed": SEED,
                "order": order(codes),
                "items": len(codes),
                "purposes": names,
                "tab_order": {r["surname"]: r.get("first") for r in raters()},
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"wrote {written} tabs to {OUT_DIR} | raters: {len(raters())} | items: {len(codes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
