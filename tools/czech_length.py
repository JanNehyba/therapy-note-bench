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
import random
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

# Resampling is seeded, so rebuilding the payload gives the same file back.
# The seed is the date it was written and means nothing else.
RESAMPLE_SEED = 20260829
RESAMPLES = 4000

# Two systems count as separated only above this, on a 0-1 composite of the
# six criteria. Ten notes per model cannot resolve a hundredth of a point,
# and a pair below it is left undecided rather than decided quietly.
SEPARATION = 0.05


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
    out["deepsy"]["limit_words"] = deepsy.default_length()
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
    limit = deepsy.default_length()
    out: dict[str, dict] = {}
    for track in (results.TRACK_DEEPSY_REAL, results.TRACK_DEEPSY_TRANSLATED):
        task_name = TASK_OF_TRACK[track]
        per_section: dict[str, list[int]] = collections.defaultdict(list)
        per_model: dict[str, list[int]] = collections.defaultdict(list)
        # A whole note is the three sections of one session added up. Three
        # times a section's median is not that, and using it overstated the
        # corpus by a hundred words a note in the one place it was compared
        # against SOAP.
        per_note: dict[str, dict[str, int]] = collections.defaultdict(
            lambda: collections.defaultdict(int)
        )
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
            per_note[record["model"]][record.get("session_id") or path.parts[-2]] += count
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
            "by_note": {
                model: int(statistics.median(sessions.values()))
                for model, sessions in sorted(per_note.items())
                if sessions
            },
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


def _line(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Least squares, written out. No scientific stack in the offline suite."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if not sxx:
        return 0.0, my
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx
    return slope, my - slope * mx


def _distinct(sample: list[tuple]) -> list[tuple]:
    """One entry per system, whatever the resample happened to draw twice."""
    return list({item[0]: item for item in sample}.values())


def _residuals(sample: list[tuple], keys: list[str]) -> dict[str, float] | None:
    """Each system's mean residual after a line through the resample.

    The line is fitted on the sample *with* its duplicates, because that is what
    weights a resample. The ranking is then taken over the distinct systems: a
    model drawn twice is one model, not two, and adding its residual twice would
    let the draw decide the order instead of the fit.
    """
    xs = [item[1] for item in sample]
    if len({round(x, 6) for x in xs}) < 2:
        return None
    here = _distinct(sample)
    out = {item[0]: 0.0 for item in here}
    for key in keys:
        slope, intercept = _line(xs, [item[2][key] for item in sample])
        for item in here:
            out[item[0]] += (item[2][key] - (intercept + slope * item[1])) / len(keys)
    return out


def _percentile(values: list[float], fraction: float) -> float:
    return values[min(len(values) - 1, int(fraction * len(values)))]


def _resampled(sample: list[tuple], keys: list[str]) -> dict:
    """The slope and the adjusted last place, with the models drawn again.

    **The models are what gets resampled, not the notes.** The claim under test
    is about models -- "the ones this endpoint deploys sit on a line" -- so the
    models are the sample. Resampling notes inside a model would answer a
    different question and give a narrower interval for it.

    Two numbers come back and they are *not* required to agree, which is the
    reason both are here. `slope` says whether the effect has a direction; it is
    one number fitted to every point. `last_place_holds` says whether the order
    that effect implies can be relied on; it is eleven residuals, each of them
    small, competing with each other. A well-measured average is perfectly
    compatible with an order that will not sit still, and here it is exactly
    that -- which is why this file publishes the first and withholds the second.
    """
    rng = random.Random(RESAMPLE_SEED)
    xs = [item[1] for item in sample]
    slope, _ = _line(xs, [sum(item[2][k] for k in keys) / len(keys) for item in sample])
    base = _residuals(sample, keys)
    if base is None:
        return {}
    lowest = min(base, key=base.get)
    slopes: list[float] = []
    holds = 0
    degenerate = 0
    for _ in range(RESAMPLES):
        drawn = [rng.choice(sample) for _ in sample]
        if len({round(item[1], 6) for item in drawn}) < 2:
            degenerate += 1
            continue
        drawn_x = [item[1] for item in drawn]
        drawn_y = [sum(item[2][k] for k in keys) / len(keys) for item in drawn]
        slopes.append(_line(drawn_x, drawn_y)[0])
        residual = _residuals(drawn, keys)
        if residual and min(residual, key=residual.get) == lowest:
            holds += 1
    if not slopes:
        return {}
    slopes.sort()
    return {
        "slope_per_100_words": round(slope * 100, 4),
        "interval_90": [
            round(_percentile(slopes, 0.05) * 100, 4),
            round(_percentile(slopes, 0.95) * 100, 4),
        ],
        "wrong_sign": round(sum(1 for value in slopes if value > 0) / len(slopes), 4),
        "last_place": lowest,
        "last_place_holds": round(holds / len(slopes), 4),
        "resamples": len(slopes),
        "degenerate": degenerate,
    }


def adjusted() -> dict:
    """What is left of a Czech score once note length is taken out of it.

    **Why this is worth computing.** Every Czech criterion asks one yes/no
    question about a whole note -- is there a fault anywhere in it -- so a
    longer note offers more places for one to be found. Measured rather than
    argued: on the composite of the six criteria, length accounts for 32 to 41
    per cent of the variance between models across the four track-and-judge
    combinations, at seven to nine hundredths of a point per hundred words.

    Per criterion it is far less even, and the composite hides that. Across the
    same twenty-four fits it runs from 0.00 to 0.73, and eleven of the
    twenty-four reach a quarter. `untranslated` is flat everywhere (0.00 to
    0.05) -- leaving an English term in is not something a longer note does more
    of -- while `diacritics` reaches 0.73 on one of the four. So "these columns
    are partly a length measurement" is true of the set and not of each member
    of it, and the per-criterion slopes are returned for that reason.

    **What this publishes, and what it withholds.** The slope, its interval and
    its direction are published: the direction is settled, with the ninety per
    cent interval clear of zero on all four fits and the sign reversing in about
    one resample in a hundred. The *adjusted ordering* is computed here and is
    not for publication, and `_resampled` records why -- even the safest
    position in it, the last place, survives redrawing the models only about
    half the time. An order that moves when the same models are drawn again is
    not a result, and printing it beside the real one would invite the reader to
    prefer it.

    **And it would not be trustworthy even if it were stable.** Length was not
    assigned at random. A model may write long *because* it summarises badly,
    and subtracting what length predicts then subtracts real signal along with
    the artefact. Eleven points, one predictor, and the ends of the range do not
    overlap: the correction for the shortest writer is an extrapolation from
    where no model sits. The honest use of this fit is to say how large the
    entanglement is, which `tools/czech_brief.py` prints beside the table, and
    then to hand the reader `handicapped()` for the orderings that need no fit
    at all.
    """
    rows = [row for row in results.latest(results.load(results.LOCAL_ROWS_PATH)) if row.is_scored]
    out: dict[str, dict] = {}
    for track in (results.TRACK_CZECH_REAL, results.TRACK_CZECH_TRANSLATED):
        words = note_lengths(TASK_OF_TRACK[track])
        medians = {model: statistics.median(v) for model, v in words.items() if v}
        judges: dict[str, dict] = {}
        for judge in sorted({row.judge_model or "" for row in rows if row.track == track}):
            here = [
                row
                for row in rows
                if row.track == track and row.judge_model == judge and row.system_id in medians
            ]
            if len(here) < MIN_SYSTEMS:
                continue
            newest = max(row.judge_prompt_version for row in here)
            here = [row for row in here if row.judge_prompt_version == newest]
            keys = sorted(
                {k for row in here for k in row.metrics.headline}
                - set(getattr(czech_task, "INTERNAL_MEASURES", ()))
            )
            keys = [k for k in keys if all(k in row.metrics.headline for row in here)]
            if not keys:
                continue
            sample = [
                (
                    row.system_id,
                    float(medians[row.system_id]),
                    {k: float(row.metrics.headline[k]) for k in keys},
                )
                for row in here
            ]
            xs = [item[1] for item in sample]
            raw = {item[0]: sum(item[2][k] for k in keys) / len(keys) for item in sample}
            slopes = {}
            for key in keys:
                slope, _ = _line(xs, [item[2][key] for item in sample])
                slopes[key] = round(slope * 100, 4)
            residual = _residuals(sample, keys)
            if residual is None:
                continue
            centre = sum(raw.values()) / len(raw)
            adj = {model: value + centre for model, value in residual.items()}
            order_raw = [m for m, _ in sorted(raw.items(), key=lambda kv: -kv[1])]
            order_adj = [m for m, _ in sorted(adj.items(), key=lambda kv: -kv[1])]
            judges[judge] = {
                "judge_prompt_version": newest,
                "systems": len(here),
                "slope_per_criterion_per_100_words": slopes,
                "raw": {m: round(v, 4) for m, v in raw.items()},
                # Kept so the claim in the docstring can be checked, and named
                # so that nothing renders it by accident.
                "not_for_publication_adjusted": {m: round(v, 4) for m, v in adj.items()},
                "not_for_publication_order": order_adj,
                "moved": sum(1 for m in order_raw if order_raw.index(m) != order_adj.index(m)),
                **_resampled(sample, keys),
            }
        if judges:
            out[track] = judges
    return out


def handicapped() -> dict:
    """Which models beat which without length being able to explain it.

    The adjusted column is a fitted model and inherits every assumption in one.
    This is not: nothing is fitted, nothing is extrapolated, and a pair the data
    cannot separate is left out rather than resolved.

    A pair of systems is **decided** when one beats the other by more than
    `SEPARATION` on the composite under *both* judges -- one judge is an
    opinion, and ten notes cannot resolve a hundredth of a point. A decided pair
    **survives the handicap** when the winner also wrote at least as many words
    as the loser. Then the longer note had more places for a fault to be found
    and still had fewer of them, so the shape of the question cannot be what
    produced the result.

    What survives is a partial order and not a ranking, and it is deliberately
    small: most pairs are either too close to call or are exactly the case the
    handicap exists to catch. That it is small is the finding.
    """
    rows = [row for row in results.latest(results.load(results.LOCAL_ROWS_PATH)) if row.is_scored]
    out: dict[str, dict] = {}
    for track in (results.TRACK_CZECH_REAL, results.TRACK_CZECH_TRANSLATED):
        words = note_lengths(TASK_OF_TRACK[track])
        medians = {model: statistics.median(v) for model, v in words.items() if v}
        here = [row for row in rows if row.track == track and row.system_id in medians]
        composite: dict[str, dict[str, float]] = {}
        for judge in sorted({row.judge_model or "" for row in here}):
            mine = [row for row in here if row.judge_model == judge]
            newest = max(row.judge_prompt_version for row in mine)
            mine = [row for row in mine if row.judge_prompt_version == newest]
            keys = sorted(
                {k for row in mine for k in row.metrics.headline}
                - set(getattr(czech_task, "INTERNAL_MEASURES", ()))
            )
            keys = [k for k in keys if all(k in row.metrics.headline for row in mine)]
            if not keys:
                continue
            composite[judge] = {
                row.system_id: sum(float(row.metrics.headline[k]) for k in keys) / len(keys)
                for row in mine
            }
        if len(composite) < 2:
            continue
        systems = sorted(set.intersection(*(set(v) for v in composite.values())))
        decided, pairs = 0, []
        for first in systems:
            for second in systems:
                if first >= second:
                    continue
                margins = [composite[j][first] - composite[j][second] for j in composite]
                if all(m > SEPARATION for m in margins):
                    winner, loser = first, second
                elif all(m < -SEPARATION for m in margins):
                    winner, loser = second, first
                else:
                    continue
                decided += 1
                if medians[winner] >= medians[loser]:
                    pairs.append(
                        {
                            "winner": winner,
                            "loser": loser,
                            "winner_words": int(medians[winner]),
                            "loser_words": int(medians[loser]),
                            "margin": round(min(abs(m) for m in margins), 4),
                        }
                    )
        wins = collections.Counter(pair["winner"] for pair in pairs)
        out[track] = {
            "systems": len(systems),
            "judges": sorted(composite),
            "separation": SEPARATION,
            "decided": decided,
            "survived": len(pairs),
            "pairs": sorted(pairs, key=lambda p: (-p["margin"], p["winner"])),
            "wins_by_system": dict(sorted(wins.items(), key=lambda kv: (-kv[1], kv[0]))),
        }
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
    payload["adjusted"] = adjusted()
    payload["handicapped"] = handicapped()
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
