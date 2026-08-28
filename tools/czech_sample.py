"""Show what the judges actually flagged, so a person can check the instrument.

The planted-error control in `tools/czech_control.py` asks whether a criterion
finds a fault somebody put there on purpose. It is a clean experiment and it
cannot answer the other question: on the *real* notes, is the thing the judge
flagged really there? A criterion can pass the control and still fire on noise
once it meets a hundred notes nobody wrote to be examples.

Answering that needs no measurement, only a person and an afternoon -- and it is
the cheapest thing in this project that can reveal a whole column is worthless.
So this reads the answers already on disk, asks the judges nothing, and writes
what each of them said next to the note it said it about.

Three things are printed, in the order they are worth reading:

1. **How often each judge flagged each criterion**, and how often they
   disagreed. A criterion where one judge flags 40 notes and the other 2 is
   already suspect before anybody reads a note.
2. **The notes the two judges disagree about.** One of them is wrong on each
   of these, and which one is a question a native speaker settles by reading.
3. **The notes they both flagged.** If the fault is not there either, the
   column is measuring something other than its heading.

Output is `local/czech-sample.md`, gitignored: it carries whole notes, so it is
clinical content even though the sessions were de-identified before any model
read them. It is for Jan and not for the team.

Run: `uv run python tools/czech_sample.py --corpus real`
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from tnb import judge
from tnb.scoring import czech, czech_run
from tnb.tasks import czech as czech_task

REPO = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = REPO / "local" / "czech-sample.md"

#: What a judge said about one criterion of one note: True (the fault is
#: present), False (it is not), or None (asked and not answered, or not asked).
Answers = dict[tuple[str, str, str], bool | None]


def _read(candidates: list, judge_model: str, budget: int) -> Answers:
    """Every cached answer this judge gave, without asking it anything.

    The prompt is rebuilt and passed to `load_cached`, so an answer about a note
    that has since been regenerated is treated as absent rather than reused --
    the same rule the scorer runs under.
    """
    config = judge.config_from_env(model=judge_model, thinking_budget=budget)
    fingerprint = config.fingerprint()
    out: Answers = {}

    for candidate in candidates:
        note = czech_task.render_note(candidate.note)
        for task in czech.build_tasks(note):
            record = judge.load_cached(
                judge.cache_path(
                    config.model,
                    czech.JUDGE_PROMPT_VERSION,
                    candidate.provider,
                    candidate.system_id,
                    candidate.session_id,
                    task.unit,
                ),
                fingerprint,
                task.prompt,
            )
            key = (candidate.system_id, candidate.session_id, task.criterion)
            if record is None or not record.get("ok"):
                out[key] = None
                continue
            out[key] = czech.parse_answer(record["answer"])
    return out


def _counts(answers: Answers) -> Counter:
    return Counter(criterion for (_, _, criterion), value in answers.items() if value is True)


def _cell(value: bool | None) -> str:
    return {True: "**ano**", False: "ne"}.get(value, "--")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", choices=["real", "translated"], default="real")
    parser.add_argument("--thinking-budget", type=int, default=2048)
    parser.add_argument(
        "--disagreements", type=int, default=12, help="how many disputed notes to print"
    )
    parser.add_argument(
        "--agreed", type=int, default=2, help="how many agreed-flagged notes per criterion"
    )
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args(argv)

    load_dotenv(REPO / ".env")

    loader = czech_task.load_real if args.corpus == "real" else czech_task.load_translated
    task_name = czech_task.NAME_REAL if args.corpus == "real" else czech_task.NAME_TRANSLATED
    candidates = list(czech_run.from_generations(loader(), task_name=task_name))
    if not candidates:
        print(f"Nothing generated for {args.corpus} yet.", file=sys.stderr)
        return 1

    judges = [judge.DEFAULT_MODEL, judge.SECOND_JUDGE]
    answers = {name: _read(candidates, name, args.thinking_budget) for name in judges}
    if not any(any(v is not None for v in a.values()) for a in answers.values()):
        print("No cached answers yet. Run 'tnb score-czech' first.", file=sys.stderr)
        return 1

    by_id = {(c.system_id, c.session_id): c for c in candidates}
    a, b = (answers[name] for name in judges)

    disputed = sorted(
        key
        for key in set(a) & set(b)
        if a[key] is not None and b[key] is not None and a[key] != b[key]
    )
    both = sorted(key for key in set(a) & set(b) if a[key] is True and b[key] is True)

    lines = _header(args.corpus, judges, candidates, answers, disputed)
    lines += _disagreements(disputed[: args.disagreements], judges, a, b, by_id)
    lines += _agreed(both, judges, by_id, args.agreed)

    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.target}")
    print(f"  {len(candidates)} note(s), {len(disputed)} judge disagreement(s)")
    print(f"  {len(both)} case(s) both judges flagged")
    return 0


def _header(corpus, judges, candidates, answers, disputed) -> list[str]:
    counts = {name: _counts(answers[name]) for name in judges}
    lines = [
        f"# What the judges flagged on the {corpus} half, and where they disagree",
        "",
        f"{len(candidates)} notes. Nothing was asked to build this file -- every answer",
        "below was already on disk. Read it to answer one question the planted-error",
        "control cannot: on real notes, is the thing the judge flagged actually there?",
        "",
        "## How often each criterion fired",
        "",
        "| criterion | " + " | ".join(f"`{name}`" for name in judges) + " | disagreed |",
        "|---|" + "---|" * (len(judges) + 1),
    ]
    for criterion in czech.CRITERION_KEYS:
        clashes = sum(1 for key in disputed if key[2] == criterion)
        cells = " | ".join(str(counts[name][criterion]) for name in judges)
        lines.append(f"| {criterion} | {cells} | {clashes} |")
    lines += [
        "",
        "A criterion one judge flags often and the other almost never is not yet a",
        "finding about models. It is a finding about the criterion.",
        "",
    ]
    return lines


def _disagreements(disputed, judges, a, b, by_id) -> list[str]:
    lines = [
        "---",
        "",
        "## Where the two judges disagree",
        "",
        "One of them is wrong on each of these. Which one is a question a native",
        "speaker settles by reading, and it is the fastest way to learn what a",
        "column is worth.",
        "",
    ]
    if not disputed:
        lines += ["Neither judge contradicted the other on any note.", ""]
        return lines

    for number, key in enumerate(disputed, start=1):
        system_id, session_id, criterion = key
        candidate = by_id[(system_id, session_id)]
        criterion_def = next(c for c in czech.CRITERIA if c.key == criterion)
        lines += [
            f"### {number}. `{criterion}` — {system_id}",
            "",
            f"> {criterion_def.question}",
            "",
            f"- `{judges[0]}`: {_cell(a[key])}",
            f"- `{judges[1]}`: {_cell(b[key])}",
            "",
            "```",
            czech_task.render_note(candidate.note),
            "```",
            "",
            "Which one is right? ______",
            "",
        ]
    return lines


def _agreed(both, judges, by_id, per_criterion) -> list[str]:
    lines = [
        "---",
        "",
        "## Where both judges say the fault is present",
        "",
        "If it is not there either, the column is measuring something other than",
        f"its heading. Up to {per_criterion} per criterion.",
        "",
    ]
    seen: Counter = Counter()
    printed = 0
    for key in both:
        system_id, session_id, criterion = key
        if seen[criterion] >= per_criterion:
            continue
        seen[criterion] += 1
        printed += 1
        candidate = by_id[(system_id, session_id)]
        criterion_def = next(c for c in czech.CRITERIA if c.key == criterion)
        lines += [
            f"### `{criterion}` — {system_id}",
            "",
            f"> {criterion_def.question}",
            "",
            "```",
            czech_task.render_note(candidate.note),
            "```",
            "",
            "Is the fault in the note? ______",
            "",
        ]
    if not printed:
        lines += ["The two judges never agreed that a fault was present.", ""]
    return lines


if __name__ == "__main__":
    sys.exit(main())
