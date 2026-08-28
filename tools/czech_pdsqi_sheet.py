"""The second sheet: is the note any good, on the instrument the judge used.

`tools/czech_rating_sheet.py` asks whether the Czech is right. It cannot ask
whether the note is any good, and neither can its seven criteria -- a flawless
Czech sentence about nothing passes all of them. This is the other half, and it
puts the same person against the same instrument PDSQI-9 put to the judges.

**The same twenty notes, in a different order, and that is not a detail.**
Rating the same note for typos and then immediately for quality lets the typos
colour the quality score, which is a known effect and one this project can avoid
for free. The sample is identical -- drawn by the same hash of the session and
the model, so it is still independent of every score -- and only the order in
which the notes are presented differs. The note-to-model table is at the bottom
of both sheets for the same reason.

**Six attributes, not eight.** `accurate` and `thorough` cannot be answered
without the session, and the real sessions never leave the infrastructure that
holds them. The judges were asked six of the eight here; so is the person.

**And the scale is the instrument's, not ours.** PDSQI-9 is published and its
anchors are reproduced word for word, including the ones this project thinks
reward an empty note. Rewriting them would make it a different instrument with
nothing validating it -- and the point of this sheet is that the person and the
judge answered the *same* question.

Writes `local/czech-pdsqi-sheet.md`, gitignored: it carries whole notes.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from tnb.scoring import czech_pdsqi, czech_run, pdsqi
from tnb.tasks import czech as czech_task

REPO = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = REPO / "local" / "czech-pdsqi-sheet.md"


def _rank(session_id: str, system_id: str) -> str:
    """The language sheet's draw, so both sheets rate the same twenty notes."""
    return hashlib.sha256(f"{session_id}/{system_id}".encode()).hexdigest()


def _order(session_id: str, system_id: str) -> str:
    """A different presentation order, so note 1 here is not note 1 there."""
    return hashlib.sha256(f"pdsqi/{session_id}/{system_id}".encode()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--notes", type=int, default=20)
    parser.add_argument("--corpus", choices=["real", "translated"], default="real")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args(argv)

    loader = czech_task.load_real if args.corpus == "real" else czech_task.load_translated
    task_name = czech_task.NAME_REAL if args.corpus == "real" else czech_task.NAME_TRANSLATED
    candidates = list(czech_run.from_generations(loader(), task_name=task_name))
    if not candidates:
        print(f"Nothing generated for {args.corpus} yet.", file=sys.stderr)
        return 1

    drawn = sorted(candidates, key=lambda c: _rank(c.session_id, c.system_id))[: args.notes]
    shown = sorted(drawn, key=lambda c: _order(c.session_id, c.system_id))

    keys = czech_pdsqi.attribute_keys(task_name)
    attributes = [a for a in pdsqi.ATTRIBUTES if a.key in keys]

    lines = [
        "# The same notes, rated for whether they are any good",
        "",
        f"{len(shown)} notes from the {args.corpus} half -- the same twenty the language",
        "sheet drew, in a different order on purpose. Rating one note for typos and then",
        "for quality lets the typos colour the quality, and reshuffling costs nothing.",
        "",
        f"{len(attributes)} attributes of PDSQI-9's eight. `accurate` and `thorough` are not",
        "asked, because answering them means reading the session and these sessions never",
        "leave the infrastructure that holds them. The judges were asked these six too.",
        "",
        "The wording and the anchors below are the published instrument's, reproduced",
        "word for word. Where an anchor seems to reward a note that says nothing, that is",
        "the instrument and not a transcription error -- an empty note scores 5.00 on two",
        "of these under one judge, which is why an empty note is never rated at all.",
        "",
        "One rater gives no ceiling. What comes out is how often a judge and one native",
        "speaker said the same thing, which is more than this track has and less than a",
        "calibration.",
        "",
        "## The attributes",
        "",
    ]
    for attribute in attributes:
        lines.append(f"**{attribute.key}** ({attribute.label}, PDSQI-9 item {attribute.item})")
        lines.append(f"> {attribute.question} {attribute.definition}")
        if attribute.guidance:
            lines.append(">")
            lines.append(f"> {attribute.guidance}")
        if attribute.binary:
            lines.append("")
            lines.append("Answer **ano** (the fault is present) or **ne**.")
        else:
            lines.append("")
            for number, anchor in enumerate(attribute.anchors, start=1):
                lines.append(f"> {number}. {anchor}")
        lines.append("")

    lines += ["---", ""]
    for number, candidate in enumerate(shown, start=1):
        lines += [
            f"## Note {number}",
            "",
            "```",
            czech_task.render_note(candidate.note),
            "```",
            "",
            "| attribute | 1-5, or ano/ne |",
            "|---|---|",
        ]
        lines += [f"| {a.key} | |" for a in attributes]
        lines.append("")

    lines += [
        "---",
        "",
        "## Which note was whose",
        "",
        "| note | model | session |",
        "|---|---|---|",
    ]
    lines += [f"| {n} | `{c.system_id}` | `{c.session_id}` |" for n, c in enumerate(shown, start=1)]

    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.target}")
    print(f"  {len(shown)} notes, {len(attributes)} attributes each")
    print(f"  {len(shown) * len(attributes)} answers to fill in")
    print("  the same notes as the language sheet, shuffled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
