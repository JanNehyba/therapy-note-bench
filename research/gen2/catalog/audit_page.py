"""Audit the Czech overview page: what it shows, and what is wrong with it.

Written on 2026-10-15, after the investigator said he was dissatisfied with the
table and asked for an audit of it and of the rest of the page.

It checks rather than asserts. Every check here is a defect somebody found by
reading, one at a time, over two days: raw English on a Czech page, two columns
carrying one fact under different names, two labels that sound alike, and a gap
where the reader needed a sentence first. Each is now something that can be run,
so the next one is found by running this instead of by the investigator losing
patience.

It reads two things: the page's data file, and the template, so that it audits
**what the page displays** rather than everything the data happens to hold. The
first version of this file checked the whole data blob and reported 83 English
strings, most of them in fields no reader ever sees. A number that overstates a
problem is the same kind of defect as one that hides it.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent

#: Diacritics that Czech uses and English does not. A displayed string with none
#: of them and with several English function words is English, and on this page
#: that is a defect rather than a quotation.
CZECH_LETTERS = re.compile(r"[ěščřžýáíéúůňťďĚŠČŘŽÝÁÍÉÚŮŇŤĎ]")
ENGLISH_WORDS = re.compile(
    r"\b(the|that|which|with|from|this|these|only|must|would|should|note|claim|source|"
    r"error|measure|rater|session)\b",
    re.I,
)

#: Fields whose value is a quotation from an English paper. English there is
#: correct: a quote translated is no longer a quote.
QUOTED = {"quote", "quotes", "en"}

#: Words too common in this domain to count as a collision between two labels.
COMMON = {"se", "to", "co", "na", "o", "v", "a", "je", "nebo", "proč", "ten", "tom"}


def displayed_fields(template: str) -> set[str]:
    """Which fields of a row the template actually renders.

    Taken from the template rather than listed here, so a field added to the page
    is audited without anybody remembering to add it.
    """
    return set(re.findall(r"\bc\.([a-z_]+)\b", template))


def displayed_labels(template: str) -> list[str]:
    """Every column heading and detail label the reader sees."""
    headings = re.findall(r"<th>([^<]{2,60})</th>", template)
    labels = re.findall(r'\["([^"]{4,60})",\s*c\.', template)
    return [h.strip() for h in headings + labels if h.strip()]


def english_strings(rows: list[dict], fields: set[str]) -> list[dict]:
    found = []
    for row in rows:
        for field in sorted(fields):
            value = row.get(field)
            if not isinstance(value, str) or len(value) < 30 or field in QUOTED:
                continue
            if CZECH_LETTERS.search(value) or len(ENGLISH_WORDS.findall(value)) < 2:
                continue
            found.append({"id": row.get("id"), "field": field, "text": value[:110]})
    return found


def duplicate_fields(rows: list[dict], fields: set[str]) -> list[dict]:
    """Pairs of displayed fields that carry the same value on most rows.

    Two columns that agree everywhere are one column with two names. `Kategorie`
    against `Naše skupina`, and `Kde to je` against `Stav`, were both caught this
    way by the investigator rather than by a check.
    """
    keys = sorted(fields)
    out = []
    for i, left in enumerate(keys):
        for right in keys[i + 1 :]:
            both = [
                (r[left], r[right])
                for r in rows
                if isinstance(r.get(left), str) and isinstance(r.get(right), str)
            ]
            if len(both) < 5:
                continue
            same = sum(1 for a, b in both if a == b)
            if same / len(both) >= 0.8:
                out.append(
                    {"fields": [left, right], "rows_compared": len(both), "identical": same}
                )
    return out


def colliding_labels(labels: list[str]) -> list[dict]:
    """Labels that share their distinguishing words.

    "Na čem se to měří" and "Jak se měří, nebo proč ne" both reduce to `měří`,
    which is why the investigator read them as the same thing.
    """

    def stems(name: str) -> set[str]:
        words = re.findall(r"[a-zěščřžýáíéúůňťď]+", name.lower())
        return {w[:4] for w in words if w not in COMMON and len(w) > 2}

    out = []
    for i, left in enumerate(labels):
        for right in labels[i + 1 :]:
            shared = stems(left) & stems(right)
            if shared:
                out.append({"labels": [left, right], "shared": sorted(shared)})
    return out


def coverage(rows: list[dict], fields: tuple[str, ...]) -> dict:
    return {
        field: {
            "present": sum(1 for r in rows if r.get(field)),
            "missing": [r["id"] for r in rows if not r.get(field)],
        }
        for field in fields
    }


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: audit_page.py <page-data.json> <template.html>", file=sys.stderr)
        return 2
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    template = Path(sys.argv[2]).read_text(encoding="utf-8")
    rows = data["criteria"]

    fields = displayed_fields(template)
    labels = displayed_labels(template)
    # Sekce s návrhem sady se vykresluje ze stejné šablony, ale z jiného kořene,
    # takže by jinak proklouzla celá. První verze tohohle auditu ji neviděla.
    proposal = data.get("proposal") or {}
    proposal_rows = [
        {**c, "id": c.get("name")}
        for layer in ("neutral_layer", "czech_layer")
        for c in (proposal.get(layer) or {}).get("criteria", [])
    ]
    english = english_strings(rows, fields) + english_strings(proposal_rows, fields)
    by_field: dict[str, int] = defaultdict(int)
    for item in english:
        by_field[item["field"]] += 1

    report = {
        "version": "page-audit-v2",
        "subject": Path(sys.argv[1]).name,
        "what_this_is": (
            "An audit of the Czech overview page, run against the data it displays and the "
            "template that decides what is displayed. Each check is one defect somebody found "
            "by reading, turned into something that can be run."
        ),
        "fields_the_template_renders": sorted(fields),
        "A1_english_on_a_czech_page": {
            "found": len(english),
            "by_field": dict(sorted(by_field.items(), key=lambda kv: -kv[1])),
            "why_it_happens": (
                "The page reads repository fields directly and the repository is English by "
                "the project's own rule. Quotations are exempt; everything counted here is "
                "text meant for a Czech reader."
            ),
            "examples": english[:6],
        },
        "A2_two_fields_carrying_one_fact": {
            "found": duplicate_fields(rows, fields),
            "why_it_matters": (
                "Two fields that agree on most rows are one fact with two names, and the "
                "reader has to work out which is which."
            ),
        },
        "A3_labels_that_sound_alike": {
            "found": colliding_labels(labels),
            "labels_checked": labels,
            "why_it_matters": (
                "Different content under names sharing their key word reads as a duplicate "
                "even when it is not."
            ),
        },
        "A4_what_the_reader_needs_first": coverage(rows, ("name", "plain", "example", "status")),
        "A5_rows": {
            "proposal_criteria_audited": len(proposal_rows),
            "total": len(rows),
            "catalog": sum(1 for r in rows if not r.get("first_generation")),
            "first_generation": sum(1 for r in rows if r.get("first_generation")),
        },
        "not_checked_here": (
            "Whether a number written into the page's prose matches the data, and whether a "
            "sentence describing the state of the work is still true. Both have gone wrong: a "
            "count of 27 that the data did not support, and a section that said work was in "
            "progress after it was finished. Neither is mechanical unless the prose declares "
            "which number it quotes, which it does not."
        ),
        "the_builder_is_not_in_the_repository": (
            "The page is built by build_page_data.py and build_overview.py, both of which live "
            "in a session-scoped temp directory. This is the defect that cost thirteen Czech "
            "views on 2026-10-13, repeated here within two days. Nothing can regenerate this "
            "page once the directory is cleaned."
        ),
    }
    out = HERE / "page-audit.json"
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"pole, která šablona zobrazuje: {len(fields)}")
    print(f"A1 anglických řetězců: {len(english)}")
    for field, count in report["A1_english_on_a_czech_page"]["by_field"].items():
        print(f"      {field}: {count}")
    dupes = report["A2_two_fields_carrying_one_fact"]["found"]
    print(f"A2 dvojic polí se stejnou hodnotou: {len(dupes)}")
    for pair in dupes:
        print(f"      {pair['fields']}  {pair['identical']}/{pair['rows_compared']}")
    collisions = report["A3_labels_that_sound_alike"]["found"]
    print(f"A3 kolidujících popisků: {len(collisions)}")
    for pair in collisions:
        print(f"      {pair['labels']}  sdílí {pair['shared']}")
    print(f"\nzapsáno do {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
