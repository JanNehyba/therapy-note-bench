"""Does each category fire on a note built to carry it, and stay quiet on one that is not?

Gate 7 of the graduation test, and the one the study reported as NOT RUN. A share
tells you which model scored higher. It cannot tell a category that measures
something from a category that produces numbers -- for that somebody has to put a
known instance in front of the coders and see whether it comes back.

**The stimulus is invented and the prediction is written down first.** The clean
note is `czech_control.CLEAN`, already in this repository and already the control
for the six language criteria, so the two gates are run against the same baseline
rather than two different ones. Each variant adds exactly one sentence carrying
exactly one category, in the section that category belongs to, and `EXPECTED`
below says which category each was built to move -- written into the source
before the coders were asked, the same convention `czech_pdsqi_control.py` keeps.

**What a failure looks like, and both directions matter.** A category that does
not fire on the note built to carry it is not measuring what its question says. A
category that fires on the clean note is worse: it is producing a number from
nothing, and every share it contributed to is inflated by however often that
happens. The second is the reason the clean note is coded too.

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
        "Vzhled upravený, oční kontakt udržuje, tempo řeči mírně zrychlené, "
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


def _code(note: dict[str, str], label: str, codebook: dict) -> dict[str, set[str]]:
    """Put one note to every coder and return which categories each marked.

    A shim `Candidate` is enough: `code_note` needs a system id and a session id
    to key its cache on, and these are invented notes with neither. They are
    named for what they are, so a cached control answer can never be mistaken for
    a cached answer about a real note.
    """

    class Stub:
        system_id = f"control-{label}"
        session_id = "control"

    units = czech_units.split_note(note)
    marked: dict[str, set[str]] = {}
    for coder in czech_code.PANEL:
        tally = czech_code.Tally()
        rows = czech_code.code_note(coder, Stub(), units, codebook, "control", tally)
        marked[coder.name] = {
            row["category"] for row in rows if row["value"] == "present" and row["span_valid"]
        }
    return marked


def run(codebook: dict) -> dict:
    clean = _code(czech_control.CLEAN, "clean", codebook)
    variants = {name: _code(variant(name), name, codebook) for name in PLANTED}

    verdicts = {}
    for name in PLANTED:
        by_coder = {}
        for coder in czech_code.PANEL:
            fired = name in variants[name][coder.name]
            false_alarm = name in clean[coder.name]
            by_coder[coder.name] = {
                "found_it": fired,
                "fired_on_the_clean_note": false_alarm,
                "also_fired": sorted(variants[name][coder.name] - {name}),
                "verdict": (
                    "found it"
                    if fired and not false_alarm
                    else "false alarm"
                    if false_alarm
                    else "missed it"
                ),
            }
        verdicts[name] = by_coder

    passed = [
        name
        for name in PLANTED
        if all(by["verdict"] == "found it" for by in verdicts[name].values())
    ]
    return {
        "what_this_is": __doc__.strip().split("\n\n")[0],
        "clean_note_marked": {coder: sorted(cats) for coder, cats in clean.items()},
        "coders": [{"name": c.name, "model": c.model} for c in czech_code.PANEL],
        "expected": list(EXPECTED),
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
    for name, by_coder in payload["verdicts"].items():
        line = "  ".join(f"{coder}: {found['verdict']}" for coder, found in by_coder.items())
        extra = sorted({c for found in by_coder.values() for c in found["also_fired"]})
        print(f"{name:26s} {line}" + (f"   also: {', '.join(extra)}" if extra else ""))
    print(f"\npassed {len(payload['gate_7_passed'])} of {len(EXPECTED)}")
    for coder, cats in payload["clean_note_marked"].items():
        print(f"  clean note, coder {coder}: {', '.join(cats) or 'nothing'}")


if __name__ == "__main__":
    main()
