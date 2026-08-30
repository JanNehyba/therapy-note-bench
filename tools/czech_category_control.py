"""Does each category fire on the sentence built to carry it?

Gate 7 of the graduation test, and the one the study reported as NOT RUN. A
share tells you which model scored higher. It cannot tell a category that
measures something from a category that produces numbers -- for that somebody
has to put a known instance in front of the coders and see whether it comes
back.

**The stimulus is invented and the prediction is written down first.** The clean
note is `czech_control.CLEAN`, already in this repository and already the control
for the six language criteria, so the two gates are run against the same baseline
rather than two different ones. Each variant adds exactly one sentence carrying
exactly one category, in the section that category belongs to, and `EXPECTED`
below says which category each was built to move -- written into the source
before the coders were asked, the same convention `czech_pdsqi_control.py` keeps.

**The first version of this tool asked the wrong question and reported the
opposite answer.** It collapsed each coding to the note -- "did this category
appear anywhere in it" -- and then read a category found in the clean note as a
false alarm. Five of the six came back "false alarm" and one passed. That
verdict was about the stimulus, not about the coders: `CLEAN` is an ordinary
therapy note, so it restates what the client said, quotes her, describes her
speech and offers a formulation, and five of the six categories are in it
because a therapy note without them would not be a therapy note. A note-level
negative control cannot exist for a content category, which is the difference
between these six and the six language criteria the same clean note controls,
where a note free of the fault is easy to write.

These categories are answered one sentence at a time, so the gate is asked one
sentence at a time. Three questions, and the first is the gate proper:

1. **Did the planted sentence fire its own category**, under every coder.
2. **Did the planted sentence attract categories it was not built to carry.**
   This is what specificity can mean here. Overlap is not automatically a
   failure -- the codebook says these categories overlap by design -- but
   `restatement` and `clinical_hypothesis` were written as near-mirrors
   precisely because they are the pair that has to be told apart, and a
   category firing on both is not separating them.
3. **Did adding one sentence move the verdicts on the other thirteen.** The
   variant is the clean note plus one sentence and nothing else changed, so
   nothing else should move. A coder whose reading of sentence nine depends on
   what was inserted at sentence three is not answering one sentence at a time,
   and that is the claim the entire unit-level design rests on.

This cannot say the categories are right about real notes. A planted instance is
unambiguous by construction and a real one is not, so passing here is the floor
rather than the ceiling -- and the categories that pass are still categories two
models agreed on, about notes no clinician has read.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import dotenv

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import czech_code  # noqa: E402
import czech_control  # noqa: E402
import czech_units  # noqa: E402

DEFAULT_TARGET = REPO / "local" / "czech-category-control.json"

#: One sentence per category, added to the clean note in the section where that
#: category lives. Each is written to be unambiguous: the point is to test the
#: instrument, not the coders' patience with a borderline case.
#:
#: `restatement` and `clinical_hypothesis` are the pair that has to be told
#: apart, so they are built as near-mirrors -- the same content, once reported
#: and once interpreted -- rather than as two unrelated sentences. A category
#: that fires on both is not separating them.
PLANTED: dict[str, tuple[str, str]] = {
    "restatement": (
        "subjective",
        "Klientka uvádí, že se jí před zkouškou hůř usíná a že to podle svých "
        "slov zná už z minulého semestru.",
    ),
    "clinical_hypothesis": (
        "assessment",
        "Obtíže odpovídají anticipační úzkosti, kde očekávání selhání udržuje "
        "vyhýbavé chování a to zpětně potvrzuje očekávání.",
    ),
    "client_quotation": (
        "subjective",
        "Svůj stav popsala slovy: „jako bych měla v hrudníku sevřenou pěst“.",
    ),
    "unsupported_observation": (
        "objective",
        # `oční kontakt udržuje` was here and is not any more: it is a stock
        # phrase, and it turned up in six coded spans of real model notes. A
        # planted sentence has to share no wording with the corpus, or a coder
        # could be recognising the corpus rather than the category.
        "Vzhled upravený, pohled zvedá jen občas, tempo řeči mírně zrychlené, "
        "bez psychomotorického neklidu.",
    ),
    "verbal_expression": (
        "objective",
        "Vyjadřuje se souvisle, s dlouhými souvětími a četnými vsuvkami, hlasitost přiměřená.",
    ),
    "declines_to_judge": (
        "objective",
        "Údaje o medikaci nelze z přepisu posoudit, v záznamu chybí.",
    ),
}

#: What each variant was built to move, written before the coders were asked.
#: A variant is expected to fire its own category and nothing else -- but the
#: categories overlap by design, so a second category firing is reported rather
#: than counted as a failure, and which ones overlap is itself a finding.
EXPECTED = tuple(PLANTED)


def variant(category: str) -> dict[str, str]:
    """The clean note with one sentence added, in the section it belongs to."""
    section, sentence = PLANTED[category]
    note = dict(czech_control.CLEAN)
    note[section] = f"{note[section]} {sentence}"
    return note


def planted_unit(category: str) -> int | None:
    """Which numbered sentence of the variant is the planted one.

    Found by exact text rather than by position. The sentence is appended to
    its section, so its number depends on how the segmenter cut everything
    before it, and assuming a position is how the first reading of this run
    compared the wrong sentence and disagreed with itself.
    """
    _section, sentence = PLANTED[category]
    for unit in czech_units.split_note(variant(category)):
        if unit["text"].strip() == sentence.strip():
            return unit["unit_index"]
    return None


def _code(note: dict[str, str], label: str, codebook: dict) -> dict[str, dict]:
    """Put one note to every coder and return every verdict, by sentence.

    A shim `Candidate` is enough: `code_note` needs a system id and a session id
    to key its cache on, and these are invented notes with neither. They are
    named for what they are, so a cached control answer can never be mistaken for
    a cached answer about a real note.

    Verdicts are kept per sentence rather than collapsed to the note. Collapsing
    is what made the first version of this gate answer a different question from
    the one the categories are asked.
    """

    class Stub:
        system_id = f"control-{label}"
        session_id = "control"

    units = czech_units.split_note(note)
    out: dict[str, dict] = {}
    for coder in czech_code.PANEL:
        tally = czech_code.Tally()
        rows = czech_code.code_note(coder, Stub(), units, codebook, "control", tally)
        by_unit: dict[int, dict[str, str]] = {}
        for row in rows:
            by_unit.setdefault(row["unit_index"], {})[row["category"]] = row["value"]
        out[coder.name] = {
            "by_unit": by_unit,
            "units": len(units),
            "spans_discarded": tally.spans_discarded,
            "spans_checked": tally.spans_checked,
        }
    return out


def _shifted(category: str, planted: int, units: int) -> dict[int, int]:
    """Variant sentence number -> the clean note's number for the same sentence.

    Everything before the insertion keeps its number and everything after moves
    by one, which is what lets question 3 compare like with like.
    """
    return {i: (i if i < planted else i - 1) for i in range(units) if i != planted}


def run(codebook: dict) -> dict:
    clean = _code(czech_control.CLEAN, "clean", codebook)
    variants = {name: _code(variant(name), name, codebook) for name in PLANTED}
    at = {name: planted_unit(name) for name in PLANTED}

    verdicts: dict[str, dict] = {}
    for name in PLANTED:
        by_coder = {}
        for coder in czech_code.PANEL:
            marks = (
                variants[name][coder.name]["by_unit"].get(at[name], {})
                if at[name] is not None
                else {}
            )
            found = marks.get(name) == "present"
            by_coder[coder.name] = {
                "planted_unit": at[name],
                "verdict_on_it": marks.get(name, "no answer"),
                "found_it": found,
                "also_fired_on_it": sorted(
                    other for other in PLANTED if other != name and marks.get(other) == "present"
                ),
                "verdict": "found it" if found else "missed it",
            }
        verdicts[name] = by_coder

    #: Question 3. Counted over every sentence the variant shares with the clean
    #: note and every category, so a coder that reads one sentence differently
    #: because of another shows up as a rate rather than as an impression.
    stability = {}
    for coder in czech_code.PANEL:
        base = clean[coder.name]["by_unit"]
        moved = same = 0
        for name in PLANTED:
            if at[name] is None:
                continue
            var = variants[name][coder.name]
            for vi, ci in _shifted(name, at[name], var["units"]).items():
                for category in PLANTED:
                    before = base.get(ci, {}).get(category)
                    after = var["by_unit"].get(vi, {}).get(category)
                    if before is None or after is None:
                        continue
                    same += before == after
                    moved += before != after
        total = same + moved
        stability[coder.name] = {
            "verdicts_compared": total,
            "verdicts_changed": moved,
            "rate": round(moved / total, 4) if total else None,
        }

    passed = [
        name
        for name in PLANTED
        if all(by["found_it"] for by in verdicts[name].values()) and verdicts[name]
    ]
    #: What the clean note contains, kept because it is the reason the
    #: note-level version of this gate could never have worked.
    clean_marked = {
        coder: sorted(
            {
                category
                for marks in reading["by_unit"].values()
                for category, value in marks.items()
                if value == "present"
            }
        )
        for coder, reading in clean.items()
    }
    return {
        "what_this_is": __doc__.strip().split("\n\n")[0],
        "clean_note_marked": clean_marked,
        "clean_note_is_not_a_negative_control": (
            "`czech_control.CLEAN` is an ordinary therapy note. It restates what "
            "the client said, quotes her, describes her speech and offers a "
            "formulation, so five of the six categories are in it by construction "
            "and none of that is a false alarm. It is a negative control for the "
            "six language criteria, where a note free of the fault is easy to "
            "write, and it cannot be one for a content category."
        ),
        "coders": [{"name": c.name, "model": c.model} for c in czech_code.PANEL],
        "expected": list(EXPECTED),
        "planted_unit": at,
        "stability": stability,
        "gate_7_passed": passed,
        "gate_7_failed": [name for name in PLANTED if name not in passed],
        "verdicts": verdicts,
    }


def main() -> None:
    dotenv.load_dotenv(REPO / ".env")
    parser = argparse.ArgumentParser(description="Gate 7: planted instances of each category.")
    parser.add_argument("--codebook", type=Path, default=REPO / "local" / "czech-codebook.json")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    codebook = json.loads(args.codebook.read_text(encoding="utf-8"))["categories"]
    payload = run(codebook)
    args.target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.target}\n")
    print("1. did the planted sentence fire its own category?")
    for name, by_coder in payload["verdicts"].items():
        line = "  ".join(
            f"{coder}: {found['verdict_on_it']}" for coder, found in sorted(by_coder.items())
        )
        print(f"   {name:26s} sentence {payload['planted_unit'][name]:>3}   {line}")

    print("\n2. did it also attract categories it was not built to carry?")
    for name, by_coder in payload["verdicts"].items():
        extra = sorted({c for found in by_coder.values() for c in found["also_fired_on_it"]})
        print(f"   {name:26s} {', '.join(extra) or 'nothing'}")

    print("\n3. did adding one sentence move the verdicts on the others?")
    for coder, s in sorted(payload["stability"].items()):
        print(
            f"   coder {coder}: {s['verdicts_changed']} of {s['verdicts_compared']} changed"
            f"  ({s['rate']:.1%})"
            if s["rate"] is not None
            else f"   coder {coder}: nothing to compare"
        )

    print(f"\npassed {len(payload['gate_7_passed'])} of {len(EXPECTED)}")
    print("\nwhat the clean note itself contains, which is why it is not a negative control:")
    for coder, cats in sorted(payload["clean_note_marked"].items()):
        print(f"   coder {coder}: {', '.join(cats) or 'nothing'}")


if __name__ == "__main__":
    main()
