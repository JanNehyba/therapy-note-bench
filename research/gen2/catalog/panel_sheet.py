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

#: One sheet per rater, numbered rather than named. A name on a sheet is a
#: small invitation to compare answers.
RATERS = (1, 2, 3)


def order(codes: list[str], seed: int = SEED) -> list[str]:
    shuffled = sorted(codes)
    random.Random(seed).shuffle(shuffled)
    return shuffled


def rows(czech: dict, codes: list[str]) -> list[list[str]]:
    sheet = czech["panel_sheet"]
    out = [list(line) for line in sheet["instructions"]]
    out.append(list(sheet["header"]))
    for code in order(codes):
        entry = czech["candidates"][code]
        out.append([code, entry["name"], entry["statement"], "", "", ""])
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
    table = rows(czech, codes)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for rater in RATERS:
        (OUT_DIR / f"hodnoceni-kriterii-{rater}.csv").write_text(as_csv(table), encoding="utf-8")
    (OUT_DIR / "poradi.json").write_text(
        json.dumps(
            {"seed": SEED, "order": order(codes), "items": len(codes)},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"wrote {len(RATERS)} copies to {OUT_DIR} | items: {len(codes)} | rows: {len(table)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
