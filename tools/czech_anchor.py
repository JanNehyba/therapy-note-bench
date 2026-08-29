"""How often a judge and one native speaker say the same thing.

The one figure this track has that the other three do not. iCARE's expert
ratings were never published and nobody has rated this repository's English
notes on PDSQI-9, so `docs/limitations.md` says of both that they have no human
anchor. This one can have a small one, because the notes are in Czech and there
is a native speaker on the project.

**What the number is, exactly.** One person answered the same six questions
the judge answered, about twenty notes drawn by a hash of the session and the
model. He was not reading cold: a language model walked him through each note,
pointed at candidate faults and asked; he decided every answer. That shapes what
the number means and is stated wherever it appears. A fault neither he nor the
model noticed is a fault nobody looked for, and the direction of that bias is
knowable -- it can only make the human's "no fault" answers too generous, never
the reverse.

**And what it is not.** One rater gives no ceiling. This repository publishes
therapist-against-therapist as the ceiling a judge-against-human figure is read
against, precisely so that "0.84" is not mistaken for "84% correct"; with a
single rater there is no such ceiling, so what comes out is "how often a judge
and one native speaker said the same thing" and must be published as that.

Reads the filled sheet, asks the judges nothing, and writes
`local/czech-anchor.json` for `tools/czech_brief.py` to draw. The sheet itself
stays gitignored -- it carries whole notes -- and this file carries only counts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

from tnb import judge  # noqa: E402
from tnb.scoring import czech, czech_run  # noqa: E402
from tnb.tasks import czech as czech_task  # noqa: E402

DEFAULT_SHEET = REPO / "local" / "czech-rating-sheet.md"
DEFAULT_TARGET = REPO / "local" / "czech-anchor.json"

#: How the ratings were produced. Written down because "one native speaker rated
#: twenty notes" and "a model proposed candidates and one native speaker ruled on
#: each" are different claims, and only the second one is true.
METHOD = (
    "One native speaker answered all six questions for each of twenty notes. A "
    "language model presented each note, pointed at candidate faults and asked; the "
    "person decided every answer, including one where he overruled the model. The "
    "sample was drawn by a hash of the session and the model, so no score could "
    "influence which notes were rated."
)

#: The three words the figure may be reported in, and the one it may not.
CEILING = (
    "There is one rater, so there is no human-against-human ceiling to read this "
    "against. It is not an accuracy: it is how often a judge and one native speaker "
    "said the same thing."
)

_ANSWER = {"ano": True, "ne": False, "--": None}


def read_sheet(path: Path) -> dict[tuple[str, str, str], bool | None]:
    """The filled sheet as answers, keyed the way the judges' answers are keyed.

    The note -> model mapping is read from the sheet's own footer rather than
    recomputed, so a sheet drawn from a different sample still lines up.
    """
    text = path.read_text(encoding="utf-8")
    mapping = {
        int(number): (model, session)
        for number, model, session in re.findall(
            r"^\|\s*(\d+)\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*$", text, re.M
        )
    }
    if not mapping:
        raise SystemExit(f"{path} has no note-to-model table; is it the rating sheet?")

    answers: dict[tuple[str, str, str], bool | None] = {}
    for block in re.finditer(r"## Note (\d+)(.*?)(?=## Note |\Z)", text, re.S):
        number = int(block.group(1))
        if number not in mapping:
            continue
        model, session = mapping[number]
        for key in czech.CRITERION_KEYS:
            found = re.search(rf"\|\s*{key}\s*\|\s*(ano|ne|--)\s*\|", block.group(2))
            if found:
                answers[(model, session, key)] = _ANSWER[found.group(1)]
    return answers


def agreement(
    human: dict[tuple[str, str, str], bool | None],
    notes: dict[tuple[str, str], str],
    verdicts: dict[tuple[str, str, str], bool | None],
) -> dict:
    """One judge against the person, criterion by criterion.

    **A question with no answer on disk is left out of the rate and counted
    beside it.** It is the whole reason this is a function rather than a loop:
    the first version scored a missing answer as a disagreement and reported
    that `gpt-5.6-terra` agreed with the rater on 0 of 140 questions, which was
    not a measurement of the judge but of a rubric version that had not finished
    running. Counting an absence as a bad result is the shape this repository
    has now met seventeen times.

    A criterion the note gave no chance at -- `--` from the person, nothing from
    the instrument -- is not that. Both said "this does not apply", and agreeing
    about that is agreement.
    """
    per_criterion: dict[str, dict] = {}
    for key in czech.CRITERION_KEYS:
        compared = agreed = unanswered = 0
        for (model, session, criterion), person in human.items():
            if criterion != key or (model, session) not in notes:
                continue
            note = notes[(model, session)]

            asked = key in {task.criterion for task in czech.build_tasks(note)}
            verdict = verdicts.get((model, session, key))
            if asked and verdict is None:
                unanswered += 1
                continue

            compared += 1
            agreed += int(verdict == person)

        if compared or unanswered:
            per_criterion[key] = {
                "compared": compared,
                "agreed": agreed,
                "unanswered": unanswered,
                "rate": round(agreed / compared, 4) if compared else None,
            }

    total = sum(v["compared"] for v in per_criterion.values())
    hits = sum(v["agreed"] for v in per_criterion.values())
    missing = sum(v["unanswered"] for v in per_criterion.values())
    return {
        "criteria": per_criterion,
        "compared": total,
        "agreed": hits,
        "unanswered": missing,
        # Withheld while most of the questions are unanswered. "1.00" printed
        # beside "120 missing" is a number somebody will quote without the
        # second half.
        "rate": round(hits / total, 4) if total and missing <= total else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sheet", type=Path, default=DEFAULT_SHEET)
    parser.add_argument("--thinking-budget", type=int, default=2048)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args(argv)

    load_dotenv(REPO / ".env")
    import czech_sample

    if not args.sheet.exists():
        print(f"{args.sheet} is not there. Run tools/czech_rating_sheet.py.", file=sys.stderr)
        return 1

    human = read_sheet(args.sheet)
    if not any(value is not None for value in human.values()):
        print(f"{args.sheet} is not filled in yet.", file=sys.stderr)
        return 1

    candidates = list(
        czech_run.from_generations(czech_task.load_real(), task_name=czech_task.NAME_REAL)
    )
    notes = {(c.system_id, c.session_id): czech_task.render_note(c.note) for c in candidates}
    judges = [judge.DEFAULT_MODEL, judge.SECOND_JUDGE]
    machine = {name: czech_sample._read(candidates, name, args.thinking_budget) for name in judges}

    payload: dict = {
        "sheet": args.sheet.name,
        "method": METHOD,
        "ceiling": CEILING,
        "notes_rated": len({(m, s) for m, s, _ in human}),
        "judges": {},
    }

    for name in judges:
        payload["judges"][name] = agreement(human, notes, machine[name])

    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"{payload['notes_rated']} notes rated by one native speaker.\n")
    for name in judges:
        gap = payload["judges"][name]["unanswered"]
        if gap:
            print(
                f"  ! {name}: {gap} question(s) have no answer on disk under "
                f"{czech.JUDGE_PROMPT_VERSION}. Left out of the rate rather than counted\n"
                "    against it. Re-run 'tnb score-czech' and this file again.\n"
            )

    print(f"{'criterion':16}" + "".join(f"{n[:20]:>22}" for n in judges))
    for key in czech.CRITERION_KEYS:
        cells = []
        for name in judges:
            entry = payload["judges"][name]["criteria"].get(key)
            if not entry:
                cells.append("--")
            elif entry["rate"] is None:
                cells.append(f"none of {entry['unanswered']} answered")
            else:
                gap = f" +{entry['unanswered']}?" if entry["unanswered"] else ""
                cells.append(f"{entry['agreed']}/{entry['compared']} = {entry['rate']:.2f}{gap}")
        mark = "  (counted)" if czech.CRITERIA[czech.CRITERION_KEYS.index(key)].computed else ""
        print(f"{key:16}" + "".join(f"{c:>22}" for c in cells) + mark)
    print(
        f"\n{'ALL':16}"
        + "".join(
            (f"{payload['judges'][n]['rate']:.2f}" if payload["judges"][n]["rate"] else "--").rjust(
                22
            )
            for n in judges
        )
    )
    print(f"\nwrote {args.target}")
    print(CEILING)
    return 0


if __name__ == "__main__":
    sys.exit(main())
