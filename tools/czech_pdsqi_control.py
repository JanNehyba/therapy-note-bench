"""Can a PDSQI column come back below 5, or does the judge not look?

Three of the six attributes this project can ask about a confidential note are
the same value for every model: `organized` and `synthesized` are 5.00 for all
eleven under both judges, and `useful` is 5.00 for all eleven under one of them.
The published English track has the same shape over nineteen systems and 942
notes a judge.

A flat column has two possible causes and they call for opposite responses.

**A property of the task.** Every model writes into the four-part structure the
prompt dictates, so a question about structure has nothing left to separate.
Then the column is honest and simply uninformative here, and the tables may keep
it with a note.

**A property of the instrument.** The judge does not look, and would answer 5
whatever it was shown. Then every `organized` figure on both pages is not a
measurement and should be withdrawn and reported as unmeasurable on this
material -- which is a publishable negative finding, not a gap.

Nothing already measured can tell those apart, because nothing already measured
contains a badly organised note. This does: a clean note, and variants each
damaged in one specific way, with a prediction written down for each before it
is asked. `tools/czech_control.py` does exactly this for the language criteria;
this is the same experiment on the quality instrument.

**Read it the way that file says.** A variant that collapses on the attribute it
attacks and holds elsewhere means the attribute measures what it claims. A
variant that changes nothing means the judge cannot see that fault. A variant
that moves everything means the judge is rating an impression rather than
answering the question.

**Six attributes, not eight.** `accurate` and `thorough` can only be answered by
reading the session, and both judges run outside the university. `build_tasks`
with no transcript returns the six that can be asked, and the enforcement is
that no transcript is in scope at all -- the same shape the real-session track
uses.

The note is invented. No clinical text is read, written or sent, which is why
this file may be read by anyone and why its output may be quoted.

Run: `uv run python tools/czech_pdsqi_control.py --judge-model gemini-3.1-pro-preview`
Costs 4 notes x 6 attributes = 24 calls a judge. Writes
`local/czech-pdsqi-control.{md,json}`. Appends no result row: a control is not a
system and `results/` is append-only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from tnb import judge
from tnb.scoring import pdsqi
from tnb.tasks import czech as czech_task

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
DEFAULT_TARGET = REPO / "local" / "czech-pdsqi-control.md"


def _clean() -> dict[str, str]:
    """The clean note, taken from the language control rather than rewritten.

    One invented note for both experiments. Two would drift, and the day they
    differed the two controls would stop being comparable without anyone
    noticing which had changed.
    """
    from czech_control import CLEAN

    return dict(CLEAN)


def _shuffled(note: dict[str, str]) -> dict[str, str]:
    """Every sentence kept, every one in the wrong section.

    Aimed at `organized`, whose published anchor for 1 reads "all assertions
    presented out of order and groupings incoherent". Nothing is added, removed
    or misspelled: the note is as accurate, as thorough and as readable
    sentence by sentence as the clean one. Only the grouping is destroyed. If
    `organized` measures grouping, this is the note it exists to catch.
    """
    sentences = [
        sentence.strip() + " "
        for section in note.values()
        for sentence in section.split(". ")
        if sentence.strip()
    ]
    # Deal them round-robin so no section keeps a run of its own sentences, and
    # deterministically so the experiment repeats. `Math.random` equivalents are
    # what make a control unrepeatable.
    sections = list(note)
    dealt: dict[str, list[str]] = {name: [] for name in sections}
    for index, sentence in enumerate(sentences):
        dealt[sections[(index * 3 + 1) % len(sections)]].append(sentence)
    return {name: "".join(parts).strip() for name, parts in dealt.items()}


def _truncated(note: dict[str, str]) -> dict[str, str]:
    """The first section only: what the client said, and nothing done with it.

    Aimed at `useful` and `synthesized`. There is no assessment and no plan, so
    a reader taking over this client is told nothing they could act on and
    nothing has been drawn together from anything. `has_content` still passes,
    which is the point -- this is not the empty note, it is a real but useless
    one.
    """
    first = next(iter(note))
    return {name: (text if name == first else "") for name, text in note.items()}


def _padded(note: dict[str, str]) -> dict[str, str]:
    """Every sentence said three times, in different words, adding nothing.

    A positive control. `succinct` is the one attribute that already separates
    the models, so it SHOULD collapse here -- and if it does not, the reading of
    every other variant is in doubt, because it would mean the instrument does
    not respond even where it is known to work.
    """
    filler = (
        " Tato skutečnost byla v průběhu sezení opakovaně zmíněna. "
        "Lze ji tedy považovat za opakovaně doloženou. "
        "Uvedené je zaznamenáno pro úplnost."
    )
    return {name: (text + filler * 2 if text else text) for name, text in note.items()}


#: What each variant is expected to do, written before it is asked.
#:
#: A prediction recorded afterwards is a description. The value of this file is
#: that the expectations are here in the source, so a result that matches them
#: is weak evidence and a result that contradicts them is strong.
VARIANTS = {
    "shuffled": (_shuffled, ("organized",)),
    "truncated": (_truncated, ("useful", "synthesized")),
    "padded": (_padded, ("succinct",)),
}


def _ask(note: str, client: judge.Judge, spend: judge.Spend) -> dict[str, float | None]:
    """One call per attribute, parsed the way that attribute is asked.

    `stigmatizing` is a yes/no -- "is there presence of stigmatizing language?"
    -- and every other attribute is a 1-5 rating. Running the rating parser over
    a "No" returns nothing, which the first version of this file did: the column
    printed `?` on all four notes and looked like a judge that would not answer.
    An absence is never a measurement, and a parser reading the wrong scale
    manufactures one.
    """
    answers: dict[str, float | None] = {}
    for task in pdsqi.build_tasks(note):
        answer = client.ask(task.prompt)
        spend.record(client.config.model, answer)
        if not answer.ok:
            answers[task.attribute] = None
            continue
        if task.attribute == "stigmatizing":
            present = pdsqi.parse_yes_no(answer.text)
            # Published as the share *free* of it, so a "yes" is 0.
            answers[task.attribute] = None if present is None else float(not present)
        else:
            answers[task.attribute] = pdsqi.parse_rating(answer.text)
    return answers


def _cell(value: float | None) -> str:
    return "  ?  " if value is None else f"{value:5.2f}"


def _report(model: str, budget: int, clean: dict, variants: dict, calls: int) -> str:
    keys = [key for key in pdsqi.ATTRIBUTE_KEYS if key in clean]
    lines = [
        "# Can a PDSQI column come back below 5?",
        "",
        f"Judge `{model}`, thinking budget {budget}, {calls} calls. One invented note,",
        "three variants, each damaged in one named way. No clinical text was used.",
        "",
        "| note | " + " | ".join(keys) + " |",
        "|---|" + "---|" * len(keys),
        "| clean | " + " | ".join(_cell(clean.get(k)).strip() for k in keys) + " |",
    ]
    for name, answers in variants.items():
        lines.append(
            f"| {name} | " + " | ".join(_cell(answers.get(k)).strip() for k in keys) + " |"
        )
    lines += ["", "## What each variant was expected to move", ""]
    for name, (_, targets) in VARIANTS.items():
        answers = variants.get(name, {})
        verdicts = []
        for key in targets:
            before, after = clean.get(key), answers.get(key)
            if before is None or after is None:
                verdicts.append(f"`{key}`: not answered")
            elif after < before:
                verdicts.append(f"`{key}`: {before:.2f} -> {after:.2f}, it moved")
            else:
                verdicts.append(f"`{key}`: {before:.2f} -> {after:.2f}, **it did not move**")
        moved_elsewhere = [
            key
            for key in keys
            if key not in targets
            and clean.get(key) is not None
            and answers.get(key) is not None
            and answers[key] < clean[key]
        ]
        lines.append(f"- **{name}** — " + "; ".join(verdicts))
        if moved_elsewhere:
            names = ", ".join(f"`{key}`" for key in moved_elsewhere)
            lines.append(f"  - also moved, which was not predicted: {names}")
    lines += [
        "",
        "## How to read it",
        "",
        "- The attacked attribute drops and the others hold — the attribute measures",
        "  what it says, and its flatness on the real tables is a property of the task.",
        "- It does not drop — the judge cannot see that fault, and every figure in that",
        "  column should be withdrawn as unmeasurable rather than published as 5.00.",
        "- Everything drops — the judge is rating an impression, and the columns are one",
        "  column wearing six hats.",
        "",
        "One judge and one note. This says whether the instrument CAN respond, not how",
        "well it discriminates in the ordinary range, and it is not a substitute for the",
        "human ratings `local/czech-pdsqi-sheet.md` is waiting for.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--judge-model", default=judge.DEFAULT_MODEL)
    parser.add_argument("--thinking-budget", type=int, default=2048)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args(argv)

    load_dotenv(REPO / ".env")
    config = judge.config_from_env(model=args.judge_model, thinking_budget=args.thinking_budget)
    client = judge.Judge(config)
    spend = judge.Spend(limit_usd=25.0)

    note = _clean()
    print(f"judge {config.model}, thinking budget {config.thinking_budget}")
    keys = [k for k in pdsqi.ATTRIBUTE_KEYS]

    clean = _ask(czech_task.render_note(note), client, spend)
    print("  clean      " + " ".join(_cell(clean.get(k)) for k in keys if k in clean))

    variants: dict[str, dict[str, float | None]] = {}
    for name, (make, _targets) in VARIANTS.items():
        answers = _ask(czech_task.render_note(make(note)), client, spend)
        variants[name] = answers
        print(f"  {name:10} " + " ".join(_cell(answers.get(k)) for k in keys if k in answers))

    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(
        _report(config.model, config.thinking_budget, clean, variants, spend.calls),
        encoding="utf-8",
    )
    payload = args.target.with_suffix(".json")
    existing = {}
    if payload.exists():
        try:
            existing = json.loads(payload.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            existing = {}
    existing[config.model] = {
        "thinking_budget": config.thinking_budget,
        "clean": clean,
        "variants": variants,
        "expected": {name: list(targets) for name, (_, targets) in VARIANTS.items()},
        "calls": spend.calls,
    }
    payload.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nwrote {args.target} and {payload.name}  ({spend.calls} calls)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
