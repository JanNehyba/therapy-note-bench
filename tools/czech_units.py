"""Cutting a note into meaning units, so a measure can have a denominator.

Every Czech criterion this repository publishes asks whether a fault appears
*anywhere* in a note, which is why all six are entangled with length: a longer
note offers more places for one. That is a property of the unit, not of the
questions. Asking the same question of one assertion at a time, and reporting a
share of assertions, removes the entanglement by construction rather than
adjusting for it afterwards.

**The unit is one assertion.** Graneheim and Lundman's meaning unit, at the level
of abstraction where a note becomes a list of the things it claims. The sampling
unit is the note, the context unit is the section, the recording unit is what
this file produces.

**Segmentation is deterministic, and the coders are not asked to do it.** The
obvious alternative -- have each model cut the text as well as code it -- was
rejected for a reason that decides whether the study can be analysed at all: if
three coders cut differently there is no shared unit to compute agreement over,
and every reliability figure would first need an alignment step whose own error
nobody could estimate. A fixed cut means the three coders answer *the same
questions*, and disagreement is then about the code rather than about where the
sentence ended.

**The cost of that is named rather than hidden.** The rule below is this file's
own, not one taken from a published procedure, because none of the three
strategies in the tool this study borrows from applies: they need speaker labels,
blank lines, or a word cap, and 89% of real-half notes are a single unbroken
paragraph per section. So the rule is written down, its output distribution is
reported, and every coder is asked one extra question -- *does this unit contain
more than one assertion?* -- which measures the rule without asking anybody to
re-segment. A high splittable rate means the rule is wrong, and it is visible.

QualReAI declares ``unit_of_analysis: "meaning_unit"`` on its project model and
never acts on it: the field is read in two places, both display. This is what
that field would have meant.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from tnb.tasks import czech as czech_task

REPO = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = REPO / "local" / "czech-units.json"

#: A sentence ends at one of these followed by space and something that starts a
#: new sentence. The lookbehind list is what stops it firing inside an
#: abbreviation, a decimal or an initial.
ABBREVIATIONS = (
    "tj",
    "tzn",
    "tzv",
    "atd",
    "apod",
    "např",
    "resp",
    "cca",
    "mj",
    "č",
    "str",
    "hod",
    "min",
    "r",
    "st",
    "sv",
    "ing",
    "mudr",
    "mgr",
    "phdr",
    "bc",
    "prof",
    "doc",
)

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[„\"'(]?[A-ZÁ-Ž0-9])")

#: A line that is a list item or a label. Cut before it whatever the punctuation
#: did, because a model that writes a bullet has already declared the boundary.
_ITEM_LINE = re.compile(r"(?m)^\s*(?:[-*•–]\s+|\d+[.)]\s+|[A-ZÁ-Ža-zá-ž][^:\n]{1,45}:\s)")

#: A unit shorter than this in words is merged backwards into its predecessor.
#: Chosen so that a bare "Ano." or a dangling clause does not become an
#: assertion the coders then have to rate.
MIN_WORDS = 4

#: Openers that only qualify what came before. A sentence starting with one of
#: these is a continuation of the previous assertion, not a new one.
CONTINUATIONS = (
    "tedy",
    "tj.",
    "tzn.",
    "to znamená",
    "například",
    "např.",
    "zároveň",
    "současně",
    "dále",
    "rovněž",
    "také",
    "navíc",
    "přitom",
    "tím",
    "proto",
    "a to",
    "resp.",
    "respektive",
)

#: Subordinators and coordinators that open a second predication. Split before
#: them, comma and all.
#:
#: **This list was added after measuring, not before.** The first version of this
#: rule cut at sentence boundaries only, and the coders -- asked on every unit
#: whether it held more than one assertion -- said yes to 65% of them. Reading the
#: units they flagged showed they were right: a nineteen-word Czech sentence
#: routinely carries a claim and its consequence. Each marker below opens a
#: clause with its own subject and verb, which is the highest-precision boundary
#: available without a parser.
#:
#: What is deliberately NOT here is a bare ``, a `` -- Czech uses it both to join
#: two predications and to join two objects, and telling those apart needs a
#: parser. Splitting on it would cut noun phrases in half, which is a worse error
#: than leaving two claims joined: an over-cut unit is a denominator inflated by
#: grammar, and grammar is exactly what the length confound already is.
CLAUSE_MARKERS = (
    "což",
    "přičemž",
    "zatímco",
    "takže",
    "ale",
    "avšak",
    "protože",
    "neboť",
    "kdežto",
    "nicméně",
    "a proto",
    "a tak",
)

_CLAUSE = re.compile(r"(?<=[,;])\s+(?=(?:" + "|".join(CLAUSE_MARKERS) + r")\b)", re.IGNORECASE)

#: A unit longer than this is reported as oversized. Not split further: the rule
#: has no principled way to cut a long sentence, and inventing one would make the
#: denominator depend on a guess. It is counted so the reader knows how often the
#: rule gives up.
LONG_WORDS = 60


def _protect(text: str) -> str:
    """Hide the full stops that end an abbreviation, so no sentence ends there."""
    out = text
    for abbreviation in ABBREVIATIONS:
        for form in (abbreviation, abbreviation.capitalize()):
            out = re.sub(rf"(?<![\w]){re.escape(form)}\.", f"{form}\x00", out)
    return out


def _restore(text: str) -> str:
    return text.replace("\x00", ".")


def split_section(text: str) -> list[str]:
    """One section into assertions, in the order they were written."""
    body = (text or "").strip()
    if not body:
        return []

    # Line structure first: a bullet or a label is a boundary the model chose.
    pieces: list[str] = []
    for line in body.split("\n"):
        line = line.strip()
        if not line:
            continue
        marks = [match.start() for match in _ITEM_LINE.finditer(line)]
        if marks and marks[0] > 0:
            pieces.append(line[: marks[0]].strip())
            line = line[marks[0] :].strip()
        if line:
            pieces.append(line)

    units: list[str] = []
    for piece in pieces:
        for sentence in _SENTENCE_END.split(_protect(piece)):
            sentence = _restore(sentence).strip()
            if not sentence:
                continue
            for clause in _CLAUSE.split(sentence):
                _add(units, clause.strip())
    return units


def _add(units: list[str], sentence: str) -> None:
    """Append one candidate unit, merging it backwards where the rule says to."""
    if not sentence:
        return
    lowered = sentence.lower().lstrip("-*•– ")
    merge = bool(units) and (len(sentence.split()) < MIN_WORDS or lowered.startswith(CONTINUATIONS))
    if merge:
        units[-1] = f"{units[-1]} {sentence}"
    else:
        units.append(sentence)


def split_note(note: dict[str, str]) -> list[dict]:
    """Every assertion in a note, carrying where it came from.

    ``start`` and ``end`` are character offsets into that section's text, so a
    coder's verbatim span can be checked against the exact bytes it claims to
    quote. Offsets into the section rather than the note because the section is
    the context unit, and because a renderer that joins sections differently
    would otherwise silently move every offset.
    """
    out: list[dict] = []
    for section, value in note.items():
        text = (value or "").strip()
        cursor = 0
        for index, unit in enumerate(split_section(text)):
            # Locate the unit exactly; a merged unit is not a contiguous slice
            # when the merge crossed a line break, so fall back to the first
            # sentence of it and mark that the offsets are partial.
            start = text.find(unit, cursor)
            exact = start >= 0
            if not exact:
                head = unit.split(". ")[0]
                start = text.find(head, cursor)
            end = start + len(unit) if exact else (start + len(head) if start >= 0 else -1)
            if start >= 0:
                cursor = max(cursor, start)
            out.append(
                {
                    "section": section,
                    "index": index,
                    "text": unit,
                    "words": len(unit.split()),
                    "start": start,
                    "end": end,
                    "offsets_exact": exact,
                    "long": len(unit.split()) > LONG_WORDS,
                }
            )
    for position, unit in enumerate(out):
        unit["unit_index"] = position
    return out


def _profile(units: list[dict]) -> dict:
    lengths = [unit["words"] for unit in units]
    if not lengths:
        return {"units": 0}
    lengths.sort()
    return {
        "units": len(lengths),
        "words_median": lengths[len(lengths) // 2],
        "words_min": lengths[0],
        "words_max": lengths[-1],
        "long_units": sum(1 for unit in units if unit["long"]),
        "offsets_inexact": sum(1 for unit in units if not unit["offsets_exact"]),
    }


def survey(task_name: str) -> dict:
    """Cut every note on one track and report what the rule produced."""
    from tnb.scoring import czech_run

    loader = (
        czech_task.load_real if task_name == czech_task.NAME_REAL else czech_task.load_translated
    )
    per_note = {}
    counts: Counter = Counter()
    everything: list[dict] = []
    for candidate in czech_run.from_generations(loader(), task_name=task_name):
        units = split_note(candidate.note)
        per_note[f"{candidate.system_id}/{candidate.session_id}"] = _profile(units)
        counts[candidate.system_id] += len(units)
        everything.extend(units)
    return {
        "overall": _profile(everything),
        "units_per_model": dict(sorted(counts.items())),
        "per_note": per_note,
    }


RULE = (
    "One meaning unit is one assertion. Sentences are cut at terminal punctuation "
    "followed by a capital, with a fixed abbreviation list protected; a bullet or "
    "a label line is a boundary whatever the punctuation did; a fragment under "
    f"{MIN_WORDS} words, or one opening with a word that only qualifies what came "
    "before, is merged backwards. A unit over "
    f"{LONG_WORDS} words is reported as oversized and is NOT cut further, because "
    "the rule has no principled way to split a long sentence and inventing one "
    "would make every denominator depend on a guess."
)

CAVEAT = (
    "This rule is this file's own. No published procedure was available to copy: "
    "the three strategies in the tool this study borrows from need speaker "
    "labels, blank lines or a word cap, and 89% of real-half notes are one "
    "unbroken paragraph per section. Every coder is therefore asked whether a "
    "unit holds more than one assertion, and that rate is what says whether the "
    "rule is any good. Until it is measured, treat every per-unit denominator as "
    "resting on an unvalidated cut."
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cut the Czech notes into meaning units.")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    payload = {
        "rule": RULE,
        "caveat": CAVEAT,
        "tracks": {
            czech_task.NAME_REAL: survey(czech_task.NAME_REAL),
            czech_task.NAME_TRANSLATED: survey(czech_task.NAME_TRANSLATED),
        },
    }
    args.target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.target}")
    for track, data in payload["tracks"].items():
        overall = data["overall"]
        print(
            f"{track}: {overall['units']} units, median {overall['words_median']} words "
            f"(range {overall['words_min']}-{overall['words_max']}), "
            f"{overall['long_units']} over {LONG_WORDS} words, "
            f"{overall['offsets_inexact']} with inexact offsets"
        )


if __name__ == "__main__":
    main()
