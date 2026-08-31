"""Count the composite strings that say nothing while looking like content.

The claim `docs/datasets.md` and `corpus.is_filled` used to make -- "150 distinct
composite strings over 534 records" -- could not be reproduced, because "says
nothing while looking like content" was never defined. This writes the
definition down and measures it.

THE DEFINITION, in the terms the code already uses:

    A value is a *dressed-up empty* when
      (a) `is_filled(value)` is False -- no sub-field carries content, so the
          expert or the model said nothing a clinician could use; and
      (b) the value is not the bare marker -- `value.strip()`, lowercased and
          stripped of trailing punctuation, is not itself in `EMPTY_MARKERS`.

    (b) is what "while looking like content" means: a naive reader of the whole
    string, checking only whether it is literally "Nil", would call it content.

Counted separately over the two populations the sentence could mean, because
they give different numbers and the old sentence named neither:

  * the expert notes -- the 40 held-out iHOPE gold notes, 17 fields each;
  * the model-written sections -- every generated iCARE section on disk.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from tnb import corpus  # noqa: E402


def dressed_up_empty(value: str) -> bool:
    """(a) nothing is filled, and (b) it is not the bare marker."""
    if corpus.is_filled(value):
        return False
    bare = value.strip().lower().rstrip(".;,! ")
    return bare not in corpus.EMPTY_MARKERS


def report(name: str, values: list[str]) -> None:
    hits = [v for v in values if dressed_up_empty(v)]
    distinct = Counter(v.strip() for v in hits)
    empties = sum(1 for v in values if not corpus.is_filled(v))
    print(f"\n{name}")
    print(f"  values read                : {len(values)}")
    print(f"  empty by is_filled         : {empties}")
    print(f"  of those, dressed up       : {len(hits)} records")
    print(f"  distinct dressed-up strings: {len(distinct)}")
    if distinct:
        longest = max(distinct, key=len)
        print(f"  longest is {len(longest)} chars, {len(longest.split())} words")


# --- the expert notes ------------------------------------------------------
expert: list[str] = []
gold = REPO / "data" / "ihope_test.json"
if gold.exists():
    raw = json.loads(gold.read_text(encoding="utf-8"))
    entries = raw if isinstance(raw, list) else list(raw.values())
    for entry in entries:
        note = entry.get("summary") or entry.get("note") or ""
        if isinstance(note, str) and note:
            for _, value in (
                corpus.split_sections(note) if hasattr(corpus, "split_sections") else []
            ):
                expert.append(value)
    if not expert:
        # Fall back to the field separator the module publishes.
        for entry in entries:
            note = entry.get("summary") or entry.get("note") or ""
            for part in str(note).split(corpus.FIELD_SEPARATOR):
                if ":" in part:
                    expert.append(part.split(":", 1)[1])
report("expert gold notes (data/ihope_test.json)", expert)

# --- the model-written sections -------------------------------------------
model: list[str] = []
for path in (REPO / "generations").rglob("section-*.json"):
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        continue
    if not d.get("ok"):
        continue
    text = d.get("text")
    if isinstance(text, str) and text:
        model.append(text)
report("model-written iCARE sections (generations/)", model)
