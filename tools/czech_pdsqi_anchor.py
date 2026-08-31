"""How often a judge and one native speaker gave the same PDSQI rating.

The companion to ``czech_anchor.py``, which does this for the six language
criteria. It exists because the PDSQI half of the same question had no reader at
all: ``tools/czech_pdsqi_form.py`` writes ``local/czech-pdsqi-answers.json`` from
the browser and **nothing in this repository ever read it back**. Fifteen ratings
sat on disk with no path into any table.

**Two things make this different from the criteria anchor, and both are
subtractions rather than additions.**

The criteria are yes/no, so agreement is a share of matches. PDSQI is a 1-5
scale, and "how often two raters picked the same integer" is a poor summary of a
scale -- it counts 4-against-5 as a total miss and 1-against-5 the same way. So
three numbers are reported and never one: exact agreement, agreement within one
point, and the mean signed difference, which is the one that carries the finding.
A signed difference says *which way* the disagreement runs.

And the sheet is **incomplete on purpose**. The rater answered 15 of 30 and
stopped, which is a fact about the instrument rather than about the rater: the
questions did not fit what was in front of him. ``questions_asked`` records what
was offered and ``questions_answered`` what came back, and the gap is printed
rather than divided away. An unrated note is not a note both parties agreed about.

Nothing here asks a judge anything. Every judge rating is read from the cache and
a rating that is not cached is counted as unanswered, never as a disagreement --
the same rule ``czech_anchor.agreement`` runs under, for the same reason.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

import dotenv

from tnb import judge
from tnb.scoring import czech_pdsqi, czech_run, pdsqi
from tnb.tasks import czech as czech_task

REPO = Path(__file__).resolve().parent.parent
DEFAULT_ANSWERS = REPO / "local" / "czech-pdsqi-answers.json"
DEFAULT_TARGET = REPO / "local" / "czech-pdsqi-anchor.json"

#: The track the form drew from. The form only ever offered the real half.
TASK_NAME = czech_task.NAME_REAL

#: The judges to read. Both, because where they disagree is the only control.
JUDGE_MODELS = ("gemini-3.1-pro-preview", "gpt-5.6-terra")

METHOD = (
    "One native speaker rated notes on three PDSQI-9 attributes in an offline "
    "form that showed the note and the de-identified session. The notes were "
    "drawn by a hash of the session and the model, so no score could influence "
    "which ones were rated. He answered 15 of the 30 questions and stopped, "
    "because the questions did not fit what he was reading -- which is recorded "
    "here rather than treated as missing data."
)

CEILING = (
    "There is one rater, so there is no human-against-human ceiling to read this "
    "against. PDSQI-9 publishes one -- trained physicians reach Krippendorff's "
    "alpha 0.575 -- but that is a ceiling for physicians rating English EHR notes "
    "on the full instrument, not for this rater on these notes. It is not an "
    "accuracy: it is how often a judge and one native speaker said the same "
    "thing, and which way they differed when they did not."
)


def asked_attributes() -> tuple[str, ...]:
    """The attributes the form asked, read from the form rather than retyped.

    ``czech_pdsqi_form.py`` is a script rather than a package module, so it is
    loaded by path. Retyping the three names here would let the form and this
    reader drift apart silently, which is the failure this repository keeps
    meeting in other guises.
    """
    spec = importlib.util.spec_from_file_location(
        "_czech_pdsqi_form", REPO / "tools" / "czech_pdsqi_form.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return tuple(module.ASKED)


def read_answers(path: Path) -> tuple[dict[tuple[str, str, str], int], int]:
    """The human ratings, keyed like the judge's, plus how many were asked.

    Returns the ``of`` field untouched. A caller that wants a rate needs both,
    and a caller that quietly used the number of answers would be dividing by
    what somebody got round to rather than by what was put to him.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    human = {
        (row["system"], row["session"], row["attribute"]): int(row["rating"])
        for row in payload["answers"]
    }
    return human, int(payload.get("of") or 0)


def judge_ratings(
    candidates: list, judge_model: str, budget: int, keys: tuple[str, ...]
) -> dict[tuple[str, str, str], int | None]:
    """Every cached PDSQI rating this judge gave, without asking it anything.

    The prompt is rebuilt and passed to ``load_cached``, so a rating about a note
    that has since been regenerated is treated as absent rather than reused.
    """
    config = judge.config_from_env(model=judge_model, thinking_budget=budget)
    fingerprint = config.fingerprint()
    out: dict[tuple[str, str, str], int | None] = {}

    for candidate in candidates:
        note = czech_task.render_note(candidate.note)
        for task in pdsqi.build_tasks(note, transcript=""):
            if task.attribute not in keys:
                continue
            record = judge.load_cached(
                judge.cache_path(
                    config.model,
                    czech_pdsqi.JUDGE_PROMPT_VERSION,
                    candidate.provider,
                    candidate.system_id,
                    candidate.session_id,
                    task.unit,
                    fingerprint=fingerprint,
                ),
                fingerprint,
                task.prompt,
            )
            key = (candidate.system_id, candidate.session_id, task.attribute)
            if record is None or not record.get("ok"):
                out[key] = None
                continue
            out[key] = pdsqi.parse_rating(record["answer"])
    return out


def agreement(
    human: dict[tuple[str, str, str], int],
    verdicts: dict[tuple[str, str, str], int | None],
) -> dict:
    """Exact agreement, agreement within one, and which way the gap runs.

    A question the human answered and the judge did not is ``unanswered`` and
    leaves the denominator. Counting it as a disagreement would punish the judge
    for a cache miss; counting it as agreement would invent a measurement.
    """
    blank = {"compared": 0, "exact": 0, "within_one": 0, "unanswered": 0}
    per: dict[str, dict] = defaultdict(lambda: {**blank, "diff": []})

    for key, value in sorted(human.items()):
        attribute = key[2]
        theirs = verdicts.get(key)
        if theirs is None:
            per[attribute]["unanswered"] += 1
            continue
        row = per[attribute]
        row["compared"] += 1
        row["exact"] += int(theirs == value)
        row["within_one"] += int(abs(theirs - value) <= 1)
        # Judge minus human. Positive means the judge rated higher.
        row["diff"].append(theirs - value)

    def summarise(row: dict) -> dict:
        entry = {name: row[name] for name in blank}
        compared = row["compared"]
        if compared:
            entry["exact_rate"] = round(row["exact"] / compared, 4)
            entry["within_one_rate"] = round(row["within_one"] / compared, 4)
            entry["mean_signed_difference"] = round(sum(row["diff"]) / compared, 4)
            entry["judge_higher"] = sum(1 for value in row["diff"] if value > 0)
            entry["judge_lower"] = sum(1 for value in row["diff"] if value < 0)
        return entry

    totals: dict = {**blank, "diff": []}
    attributes = {}
    for attribute, row in sorted(per.items()):
        attributes[attribute] = summarise(row)
        for name in blank:
            totals[name] += row[name]
        totals["diff"].extend(row["diff"])

    return {"attributes": attributes, **summarise(totals)}


def build(answers_path: Path, budget: int) -> dict:
    human, asked = read_answers(answers_path)
    rated = {(system, session) for system, session, _ in human}
    keys = tuple(key for key in asked_attributes() if key in czech_pdsqi.attribute_keys(TASK_NAME))

    sessions = czech_task.load_real()
    candidates = [
        candidate
        for candidate in czech_run.from_generations(sessions, task_name=TASK_NAME)
        if (candidate.system_id, candidate.session_id) in rated
    ]

    payload = {
        "answers_file": answers_path.name,
        "attributes_asked": list(keys),
        "ceiling": CEILING,
        "judges": {},
        "method": METHOD,
        "notes_rated": len(rated),
        "notes_with_a_generation": len(candidates),
        "questions_answered": len(human),
        "questions_asked": asked,
    }
    for model in JUDGE_MODELS:
        payload["judges"][model] = agreement(human, judge_ratings(candidates, model, budget, keys))
    return payload


def main() -> None:
    dotenv.load_dotenv(REPO / ".env")
    parser = argparse.ArgumentParser(description="Judge against the one native speaker, on PDSQI.")
    parser.add_argument("--answers", type=Path, default=DEFAULT_ANSWERS)
    parser.add_argument("--thinking-budget", type=int, default=2048)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    payload = build(args.answers, args.thinking_budget)
    args.target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"wrote {args.target}")
    print(
        f"{payload['questions_answered']} of {payload['questions_asked']} questions "
        f"answered, over {payload['notes_rated']} notes"
    )
    for model, summary in payload["judges"].items():
        if not summary.get("compared"):
            print(f"  {model}: nothing comparable")
            continue
        print(
            f"  {model}: exact {summary['exact']}/{summary['compared']}, "
            f"within one {summary['within_one']}/{summary['compared']}, "
            f"judge higher on {summary['judge_higher']}, lower on {summary['judge_lower']}, "
            f"mean signed {summary['mean_signed_difference']:+.2f}"
        )


if __name__ == "__main__":
    main()
