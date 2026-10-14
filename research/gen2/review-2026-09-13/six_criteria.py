"""What the language layer found, criterion by criterion.

Six properties, one question each: did the search find work that offers this
property of a text, a rule for recognising it, or a way of measuring it?

The counts are of records above the registered cut whose title or abstract names
the property. A count is not support: a paper can name diacritics and be about
restoring them in speech output. What the count does is say whether there is
anything to read, which is the thing the catalog could not say before, because
nothing had looked.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

EXPORTS = Path("C:/Users/Nehyba/therapy-note-bench/local/gen2-review-2026-09-13/exports")
PRIORITY = EXPORTS / "screen-priority-language.json"
OUT = Path(__file__).resolve().parent / "six-criteria-language-layer.json"

#: The six criteria of src/tnb/scoring/czech.py, with the words a paper about
#: each one would use. `agreement` is the hardest to search for: the word means
#: inter-annotator agreement far more often than grammatical agreement, so it is
#: paired with what a paper about the grammatical kind would also say.
SIX = {
    "diacritics": (
        "a missing or wrong diacritic",
        r"\bdiacritics?\b|\bdiacriti[sz]\w*\b|\baccent restoration\b",
    ),
    "calque": (
        "a term formed by translating word for word from English",
        r"\bcalque\w*\b|\bliteral translation\b|\binterference\b|\btranslationese\b",
    ),
    "untranslated": (
        "an English technical term left as it is",
        r"\buntranslated\b|\bloan ?word\w*\b|\banglicism\w*\b|\bborrowing\w*\b"
        r"|\bcode[- ]switch\w*\b",
    ),
    "agreement": (
        "a broken agreement, case or unfinished sentence",
        r"\bagreement error\w*\b|\bgrammatical error correction\b|\bmorphosyntactic\b"
        r"|\binflection\w* error\w*\b|\bcase marking\b",
    ),
    "register": (
        "a colloquial word where a professional one belongs",
        r"\bregister\b|\bformality\b|\bcolloquial\w*\b|\bstyle transfer\b",
    ),
    "nonword": (
        "a word that does not exist in the language",
        r"\bnon[- ]?words?\b|\bneologism\w*\b|\bnonsense words?\b|\bmalformed\b",
    ),
}

#: What would make a record support a criterion rather than merely mention it.
#: Checked here only as a filter for reading order; the judgement is a human one.
OFFERS_A_RULE = re.compile(
    r"\bguideline\w*|\bannotation scheme|\btaxonom\w*|\btypolog\w*|\bdefinition\b"
    r"|\bcriteri\w*|\brubric|\bwe define\b|\bcategor\w*",
    re.I,
)


def main() -> int:
    records = json.loads(PRIORITY.read_text(encoding="utf-8"))
    out = {}
    for key, (what, pattern) in SIX.items():
        regex = re.compile(pattern, re.I)
        named = [
            r for r in records if regex.search(f"{r.get('title', '')} {r.get('abstract', '')}")
        ]
        with_rule = [
            r
            for r in named
            if OFFERS_A_RULE.search(f"{r.get('title', '')} {r.get('abstract', '')}")
        ]
        out[key] = {
            "what_it_measures": what,
            "search_terms": pattern,
            "priority_records_naming_it": len(named),
            "of_those_also_offering_a_definition_or_scheme": len(with_rule),
            "top_to_read": [
                {
                    "score": r["priority_score"],
                    "year": r.get("year"),
                    "title": r.get("title"),
                    "venue": r.get("booktitle"),
                    "url": r.get("url"),
                    "signals": sorted(set(r["signals"])),
                }
                for r in sorted(with_rule or named, key=lambda r: -r["priority_score"])[:8]
            ],
        }
        print(f"{key:14} named={len(named):4}  with a scheme={len(with_rule):4}")

    out["_note"] = (
        "Counts of records above the registered cut whose title or abstract names the "
        "property. A count is not support: a paper can name diacritics and be about restoring "
        "them in speech output. What it says is whether there is anything to read, which the "
        "catalog could not say before because nothing had looked."
    )
    out["_priority_records"] = len(records)
    OUT.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"\nwrote {OUT.name} from {len(records)} priority records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
