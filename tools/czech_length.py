"""How long a note the models write, and whether the tables reward it.

Nobody told the models how long to write on three of the four prompts, and on
the fourth they were told twice -- a ceiling and a target -- and obeyed only the
ceiling. That asymmetry is the whole reason this file exists: **length is an
uncontrolled variable in every table this project publishes**, and a column that
moves with it is measuring something the reader did not ask about.

Three questions, in the order they matter.

**What was actually asked for?** The English TN-Eval SOAP prompt names no length
at all, and neither does its Czech translation -- checked here rather than
asserted, because "the prompt says nothing about length" is the kind of claim
that stays true only until somebody edits the prompt. The Deepsy prompts carry
`STRIKTNI LIMIT DELKY` with a word count, reproduced verbatim from the
application's own YAML.

**How long is a note, against a human?** TN-Eval released the therapists' own
notes, so the English track has an anchor the Czech track has not: 50 notes a
person actually wrote. It sits outside the range of all sixteen models, which is
a fact about the models as a group rather than about any one of them.

**Does length buy score?** Spearman between a model's median note length and
each measure, per comparability group and per judge. Read it as a warning rather
than as a result: eleven or sixteen points, and the coefficient is reported
without a p-value because the question is "is this column entangled with
length", which a reader answers by seeing both judges say the same thing, not by
crossing a threshold.

**The reason this matters most in Czech.** Each Czech criterion asks one yes/no
question about a whole note -- is there a fault *anywhere* in it. A note of 812
words offers more places for one to be found than a note of 289. A negative
correlation there is expected from the shape of the question and does not by
itself mean the longer-writing model is worse at Czech. Where that correlation
is strong, the column is partly a length measurement, and the document says so
beside the table rather than in a footnote.

Lengths are counted from the generation cache, not from the rows: `czech_run`
never records `note_words` on a Czech row the way the SOAP runner does. Counting
both languages from the same place means they are counted the same way, which
was checked against the published column before this file was trusted -- three
of sixteen models differ from it by one word, from rounding a median, and none
by more.

No note text is read out. Counts only.

Run: `uv run python tools/czech_length.py`. Writes `local/czech-length.json`.
Costs nothing: no model and no judge is called.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import statistics
import sys
from pathlib import Path

from tnb import results
from tnb.tasks import czech as czech_task
from tnb.tasks import deepsy, soap

REPO = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = REPO / "local" / "czech-length.json"
CACHE = REPO / "generations" / "einfra"

#: Which generation task stands behind each scored track. The PDSQI tracks rate
#: the notes the criteria tracks generated, so they share a task with them.
TASK_OF_TRACK = {
    results.TRACK_CZECH_REAL: czech_task.NAME_REAL,
    results.TRACK_CZECH_TRANSLATED: czech_task.NAME_TRANSLATED,
    results.TRACK_CZECH_REAL_PDSQI: czech_task.NAME_REAL,
    results.TRACK_CZECH_TRANSLATED_PDSQI: czech_task.NAME_TRANSLATED,
    results.TRACK_DEEPSY_REAL: deepsy.NAME_REAL,
    results.TRACK_DEEPSY_TRANSLATED: deepsy.NAME_TRANSLATED,
}

#: Words a length instruction would have to use. Searched over every string a
#: prompt module exposes, so a limit added to any of them shows up here rather
#: than silently making this file's headline claim false.
LENGTH_WORDS = re.compile(
    r"\b(\d+\s*(?:words?|slov\w*|v[eě]t\w*|sentences?|characters?|znak\w*)"
    r"|word limit|no more than|at most|maximum length"
    r"|limit d[eé]lky|c[ií]lov[aá] d[eé]lka"
    r"|nesm[ií].{0,20}p[rř]ekro[cč]it)\b",
    re.IGNORECASE,
)

#: How many measured points before a correlation is worth printing. Below this
#: the coefficient is decided by one model.
MIN_SYSTEMS = 8


def _words(value: object) -> int:
    return len(str(value or "").split())


def _prompt_text(module: object) -> str:
    """Every string a prompt module exposes, flattened."""
    found: list[str] = []

    def walk(value: object) -> None:
        if isinstance(value, str):
            found.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)

    for name, value in vars(module).items():
        if not name.startswith("_"):
            walk(value)
    return " ".join(found)


def instructions() -> dict[str, dict]:
    """What each prompt family says about length, found rather than remembered."""
    out = {}
    for label, module in (("soap", soap), ("czech", czech_task), ("deepsy", deepsy)):
        blob = _prompt_text(module)
        hits = sorted({" ".join(m.group(0).split()) for m in LENGTH_WORDS.finditer(blob)})
        out[label] = {"has_limit": bool(hits), "phrases": hits}
    out["deepsy"]["limit_words"] = deepsy.DEFAULT_LENGTH
    out["deepsy"]["sections"] = list(deepsy.SECTIONS)
    return out


def note_lengths(task_name: str) -> dict[str, list[int]]:
    """Words per note, per model, from the answer cache."""
    per: dict[str, list[int]] = collections.defaultdict(list)
    for path in CACHE.glob(f"{task_name}/**/*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        note = record.get("note")
        if not record.get("ok") or not isinstance(note, dict):
            continue
        per[record["model"]].append(sum(_words(value) for value in note.values()))
    return dict(per)


def human_lengths() -> dict[str, dict]:
    """The therapist's own notes, and the two the source paper generated.

    The only human anchor for length anywhere in this project. It is on the
    English corpus, so it says nothing about how long a Czech note should be --
    but it does say what a person writes when nobody sets a limit, which is the
    number every model in the English table is missing.
    """
    per: dict[str, list[int]] = collections.defaultdict(list)
    for path in sorted((REPO / "data").glob("tneval_notes_part*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        entries = payload if isinstance(payload, list) else list(payload.values())
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for key in ("human", "llm_llama31_70B", "llm_mistral_large_v2"):
                value = entry.get(key)
                if value is None:
                    continue
                per[key].append(
                    sum(_words(part) for part in value.values())
                    if isinstance(value, dict)
                    else _words(value)
                )
    return {
        key: {"n": len(v), "median": int(statistics.median(v)), "min": min(v), "max": max(v)}
        for key, v in per.items()
        if v
    }


def _ranks(values: list[float]) -> list[float]:
    """Average ranks, ties shared.

    Written out because this project's offline suite carries no scientific
    stack -- the same reason `saturation._sign_test` is written out.
    """
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    start = 0
    while start < len(order):
        stop = start
        while stop + 1 < len(order) and values[order[stop + 1]] == values[order[start]]:
            stop += 1
        shared = (start + stop) / 2 + 1
        for index in range(start, stop + 1):
            out[order[index]] = shared
        start = stop + 1
    return out


def spearman(a: list[float], b: list[float]) -> float | None:
    """None when either side is flat.

    A column every model scores the same on has no ordering to correlate, and
    `concordance.rankable` refuses such a column for the same reason: a
    coefficient computed over it would be decided by whichever single system is
    not at the ceiling, or by nothing at all.
    """
    if len(a) != len(b) or len(a) < 3:
        return None
    ra, rb = _ranks(a), _ranks(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    top = sum((x - ma) * (y - mb) for x, y in zip(ra, rb, strict=True))
    left = sum((x - ma) ** 2 for x in ra) ** 0.5
    right = sum((y - mb) ** 2 for y in rb) ** 0.5
    if not left or not right:
        return None
    return top / (left * right)


def _group_rows(rows: list[results.Row], track: str) -> list[list[results.Row]]:
    """The drawn comparability groups for one track, largest first."""
    groups: dict[tuple, list[results.Row]] = collections.defaultdict(list)
    for row in rows:
        if row.track == track:
            groups[row.comparability_key()].append(row)
    return [group for _, group in sorted(groups.items(), key=lambda kv: -len(kv[1]))]


def english() -> dict:
    """The published English track: lengths, and what length buys."""
    rows = [row for row in results.latest(results.load()) if row.is_scored]
    out: dict[str, dict] = {}
    for group in _group_rows(rows, results.TRACK_TNEVAL):
        mine = [r for r in group if r.system_type == "model" and r.settings.note_words]
        if len(mine) < MIN_SYSTEMS:
            continue
        judge = mine[0].judge_model or ""
        # Newest harness only. The notes are identical in every group -- only
        # the measures were redefined -- so an older group would print the same
        # lengths beside columns that no longer mean what they meant.
        if judge in out and out[judge]["harness_version"] >= mine[0].harness_version:
            continue
        length = [float(r.settings.note_words or 0) for r in mine]
        correlations: dict[str, float | None] = {}
        for key in sorted({k for r in mine for k in r.metrics.headline}):
            values = [r.metrics.headline.get(key) for r in mine]
            if any(value is None for value in values):
                continue
            rho = spearman(length, [float(value) for value in values])
            correlations[key] = None if rho is None else round(rho, 2)
        out[judge] = {
            "harness_version": mine[0].harness_version,
            "systems": len(mine),
            "min": int(min(length)),
            "max": int(max(length)),
            "median": int(statistics.median(length)),
            "by_system": {r.system_id: int(r.settings.note_words or 0) for r in mine},
            "correlations": correlations,
        }
    return out


def czech() -> dict:
    """Every local track: lengths from the cache, correlations per judge."""
    rows = [row for row in results.latest(results.load(results.LOCAL_ROWS_PATH)) if row.is_scored]
    out: dict[str, dict] = {}
    for track, task_name in TASK_OF_TRACK.items():
        lengths = note_lengths(task_name)
        if not lengths:
            continue
        medians = {model: statistics.median(v) for model, v in lengths.items()}
        judges: dict[str, dict] = {}
        for group in _group_rows(rows, track):
            mine = [row for row in group if row.system_id in medians]
            if len(mine) < MIN_SYSTEMS:
                continue
            judge = mine[0].judge_model or ""
            newest = mine[0].judge_prompt_version
            if judge in judges and judges[judge]["judge_prompt_version"] >= newest:
                continue
            length = [float(medians[row.system_id]) for row in mine]
            correlations: dict[str, float | None] = {}
            for key in sorted({k for row in mine for k in row.metrics.headline}):
                if key in getattr(czech_task, "INTERNAL_MEASURES", ()):
                    continue
                values = [row.metrics.headline.get(key) for row in mine]
                if any(value is None for value in values):
                    continue
                rho = spearman(length, [float(value) for value in values])
                correlations[key] = None if rho is None else round(rho, 2)
            judges[judge] = {
                "judge_prompt_version": newest,
                "systems": len(mine),
                "correlations": correlations,
            }
        if not judges:
            continue
        every = [int(value) for value in medians.values()]
        out[track] = {
            "task": task_name,
            "systems": len(medians),
            "min": min(every),
            "max": max(every),
            "median": int(statistics.median(every)),
            "by_system": {model: int(value) for model, value in sorted(medians.items())},
            "judges": judges,
        }
    return out


def deepsy_compliance() -> dict:
    """The one prompt that sets a length, and what the models did with it.

    Two numbers, because the instruction is two instructions. `over_limit`
    counts answers above the ceiling the prompt itself calls invalid.
    `share_of_target` is how much of the length it asks for they actually use. A
    model can obey the first perfectly while ignoring the second, and on this
    corpus that is exactly what happens -- so reporting only the first would
    read as "the instruction was followed".
    """
    limit = deepsy.DEFAULT_LENGTH
    out: dict[str, dict] = {}
    for track in (results.TRACK_DEEPSY_REAL, results.TRACK_DEEPSY_TRANSLATED):
        task_name = TASK_OF_TRACK[track]
        per_section: dict[str, list[int]] = collections.defaultdict(list)
        per_model: dict[str, list[int]] = collections.defaultdict(list)
        for path in CACHE.glob(f"{task_name}/**/*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            note = record.get("note")
            section = record.get("unit")
            if not record.get("ok") or not isinstance(note, dict) or section not in deepsy.KEYS:
                continue
            count = sum(_words(note.get(key)) for key in deepsy.KEYS[section])
            per_section[section].append(count)
            per_model[record["model"]].append(count)
        if not per_section:
            continue
        sections = {
            name: {
                "answers": len(v),
                "median": int(statistics.median(v)),
                "max": max(v),
                "over_limit": sum(1 for x in v if x > limit),
                "share_of_target": round(statistics.median(v) / limit, 2),
            }
            for name, v in per_section.items()
        }
        every = [x for v in per_section.values() for x in v]
        out[track] = {
            "limit_words": limit,
            "answers": len(every),
            "over_limit": sum(1 for x in every if x > limit),
            "sections": sections,
            "by_system": {
                model: {
                    "answers": len(v),
                    "over_limit": sum(1 for x in v if x > limit),
                    "median": int(statistics.median(v)),
                }
                for model, v in sorted(per_model.items())
            },
        }
    return out


def longest_writers(payload: dict, how_many: int = 3) -> dict:
    """Where the longest-writing models land in each Czech table.

    The claim this document wants to make -- that the bottom of the Czech table
    is partly a length effect -- is checkable, so it is checked rather than
    asserted. For each track and judge: the rank the {n} longest writers occupy
    out of however many models were drawn, and whether all of them are in the
    bottom {n}. A run where that stops being true should stop printing the
    sentence, not print it beside numbers that contradict it.
    """
    rows = [row for row in results.latest(results.load(results.LOCAL_ROWS_PATH)) if row.is_scored]
    out: dict[str, dict] = {}
    for track, block in (payload.get("czech") or {}).items():
        by_system = block["by_system"]
        longest = [
            model for model, _ in sorted(by_system.items(), key=lambda kv: -kv[1])[:how_many]
        ]
        judges: dict[str, dict] = {}
        for group in _group_rows(rows, track):
            mine = [row for row in group if row.system_id in by_system]
            if len(mine) < MIN_SYSTEMS:
                continue
            judge = mine[0].judge_model or ""
            if judge in judges:
                continue
            keys = sorted({k for row in mine for k in row.metrics.headline})
            keys = [
                k
                for k in keys
                if k not in getattr(czech_task, "INTERNAL_MEASURES", ())
                and all(k in row.metrics.headline for row in mine)
            ]
            if not keys:
                continue
            ranked = sorted(
                mine,
                key=lambda row: -sum(row.metrics.headline[k] for k in keys) / len(keys),
            )
            order = [row.system_id for row in ranked]
            places = sorted(order.index(model) + 1 for model in longest if model in order)
            judges[judge] = {
                "models": len(order),
                "places": places,
                "all_in_the_tail": bool(places) and min(places) > len(order) - how_many,
            }
        if judges:
            out[track] = {"longest": longest, "judges": judges}
    return out


def build() -> dict:
    payload = {
        "instructions": instructions(),
        "english": english(),
        "czech": czech(),
        "deepsy": deepsy_compliance(),
        "human": human_lengths(),
    }
    payload["tail"] = longest_writers(payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args(argv)

    payload = build()
    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    for label, found in payload["instructions"].items():
        print(f"{label:8} length instruction: {'YES' if found['has_limit'] else 'none'}")
    for judge, block in payload["english"].items():
        print(
            f"\nEnglish | {judge} | {block['systems']} models | "
            f"{block['min']}-{block['max']} words (median {block['median']})"
        )
        for key, rho in sorted(block["correlations"].items()):
            print(f"   {key:16} " + ("flat" if rho is None else f"rho {rho:+.2f}"))
    for name, block in payload["human"].items():
        print(f"human anchor | {name:22} n={block['n']} median {block['median']} words")
    for track, block in payload["czech"].items():
        print(
            f"\n{track} | {block['systems']} models | "
            f"{block['min']}-{block['max']} words (median {block['median']})"
        )
        for judge, found in block["judges"].items():
            print(f"  {judge}")
            for key, rho in sorted(found["correlations"].items()):
                print(f"     {key:16} " + ("flat" if rho is None else f"rho {rho:+.2f}"))
    for track, block in payload["deepsy"].items():
        print(
            f"\n{track} | limit {block['limit_words']} words | "
            f"{block['over_limit']}/{block['answers']} answers over it"
        )
        for name, found in block["sections"].items():
            print(
                f"   {name:22} median {found['median']:4} = "
                f"{found['share_of_target']:.0%} of target, max {found['max']}"
            )

    print(f"\nwrote {args.target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
