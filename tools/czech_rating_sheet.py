"""A sheet for one person to answer the same six questions the judge answered.

This track has no human anchor, and says so on every row. Neither of the other
two can get one -- iCARE's expert ratings are unpublished and nobody has rated
this repository's notes on PDSQI-9 -- but this one can, because the notes are in
Czech and there is a native speaker on the project. An afternoon buys the one
thing the track is missing.

**One rater is not a ceiling, and the sheet says so where it is filled in.** The
repository publishes therapist-against-therapist as the ceiling a
judge-against-human figure is read against. With a single rater there is no
ceiling, so the number that comes out is "how often the judge and one native
speaker said the same thing" -- more than nothing, less than a calibration, and
it must be published as the former.

**The sample is drawn from the note's own digest, not from its score.** Judge A
had already run on the real half when this was written, so choosing by hand --
or by anything downstream of a score -- would let the sample be picked to
flatter the result. A hash of the session id and the model name is independent
of every number in this project and reproduces exactly.

Writes `local/czech-rating-sheet.md`, which is gitignored and stays that way:
it carries whole notes, so it is clinical content even though the sessions were
de-identified before any model saw them. It is for Jan and not for the team.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from tnb.datasets import czech as corpus
from tnb.scoring import czech, czech_run
from tnb.tasks import czech as czech_task

REPO = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = REPO / "local" / "czech-rating-sheet.md"


def _rank(session_id: str, system_id: str) -> str:
    """A stable order that no score can reach."""
    return hashlib.sha256(f"{session_id}/{system_id}".encode()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--notes", type=int, default=20, help="how many notes to rate")
    parser.add_argument("--corpus", choices=["real", "translated"], default="real")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args(argv)

    loader = corpus.load_real if args.corpus == "real" else corpus.load_translated
    task_name = czech_task.NAME_REAL if args.corpus == "real" else czech_task.NAME_TRANSLATED
    candidates = list(czech_run.from_generations(loader(), task_name=task_name))
    if not candidates:
        print(f"Nothing generated for {args.corpus} yet.", file=sys.stderr)
        return 1

    chosen = sorted(candidates, key=lambda c: _rank(c.session_id, c.system_id))[: args.notes]

    lines = [
        "# Six questions, the same six the judge answered",
        "",
        f"{len(chosen)} notes from the {args.corpus} half, drawn by a hash of the session",
        "and the model rather than by anything downstream of a score. Which model",
        "wrote which note is at the bottom, so it cannot colour the reading.",
        "",
        "Answer **ano** if the fault is present, **ne** if it is not. If a note gives",
        "no chance to make the mistake -- no foreign term to leave untranslated, say",
        "-- write",
        "**--**; that is a real answer and is scored as one.",
        "",
        "One rater gives no ceiling. What comes out of this is how often a judge and",
        "one native speaker say the same thing, which is more than this track has now",
        "and less than a calibration.",
        "",
        "## The questions",
        "",
    ]
    for criterion in czech.CRITERIA:
        lines.append(f"**{criterion.key}** — {criterion.question}")
        lines.append(f"> {criterion.guidance}")
        lines.append("")

    lines += ["---", ""]
    for number, candidate in enumerate(chosen, start=1):
        note = czech_task.render_note(candidate.note)
        lines += [
            f"## Note {number}",
            "",
            "```",
            note,
            "```",
            "",
            "| criterion | ano / ne / -- |",
            "|---|---|",
        ]
        lines += [f"| {c.key} | |" for c in czech.CRITERIA]
        lines.append("")

    lines += [
        "---",
        "",
        "## Which note was whose",
        "",
        "| note | model | session |",
        "|---|---|---|",
    ]
    lines += [
        f"| {n} | `{c.system_id}` | `{c.session_id}` |" for n, c in enumerate(chosen, start=1)
    ]

    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    systems = len({c.system_id for c in chosen})
    print(f"wrote {args.target}")
    print(f"  {len(chosen)} notes from {systems} model(s), {len(czech.CRITERIA)} questions each")
    print(f"  {len(chosen) * len(czech.CRITERIA)} answers to fill in")
    return 0


if __name__ == "__main__":
    sys.exit(main())
