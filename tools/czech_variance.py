"""How big a gap between two models has to be before it is a gap.

A table of proportions invites its reader to compare neighbouring rows. With ten
notes per model, most of those comparisons are reading noise, and saying so with
a number is the difference between a caveat somebody skips and a threshold they
can apply to the row in front of them.

Two questions, in the order they matter.

**Is the table reading models or sessions?** Every model wrote a note from every
transcript -- that design is what makes the comparison possible at all -- but if
sessions differ from each other more than models do, the ordering is a fact
about which transcripts were drawn. Measured: the spread between model means
against the spread between session means, criterion by criterion.

**Which pairs of models are actually separable?** The sessions are resampled with
replacement, both models rescored on each resample, and the difference between
them read off the middle 95% of the resulting distribution. **Paired on the
session**, because both models wrote from the same ten transcripts and a test
that ignored that would throw away the design's whole advantage.

The number this produces is the one a reader needs: the width of that interval
is how far apart two rows must be before their order means anything. Everything
narrower is the same reading twice.

Sessions are resampled and models are not. `docs/limitations.md` records a
published "detected" verdict that came from resampling conversations only, which
treated four models as the whole of OpenAI -- that was a claim about a *family*
of models, where the models are the sample. Here the eleven models are the whole
population being compared, named individually, and the ten sessions are the
sample that could have been drawn differently.

Writes `local/czech-variance.json` for `tools/czech_brief.py`.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

from tnb import judge, report, results  # noqa: E402
from tnb.scoring import czech, czech_run  # noqa: E402
from tnb.tasks import czech as czech_task  # noqa: E402

DEFAULT_TARGET = REPO / "local" / "czech-variance.json"

#: Resamples. Two thousand puts the 2.5th percentile fifty draws from the end,
#: which is enough for a threshold reported to two decimals.
DRAWS = 2000

#: Fixed, because a threshold that moves between runs invites running it again.
SEED = 0


def _cells(task_name: str, judge_model: str, budget: int) -> dict:
    """Every (model, session, criterion) score, from the cache, asking nothing."""
    import czech_sample

    loader = (
        czech_task.load_real if task_name == czech_task.NAME_REAL else czech_task.load_translated
    )
    candidates = list(czech_run.from_generations(loader(), task_name=task_name))
    answers = czech_sample._read(candidates, judge_model, budget)

    cells: dict[tuple[str, str, str], float] = {}
    for candidate in candidates:
        note = czech_task.render_note(candidate.note)
        for task in czech.build_tasks(note):
            verdict = answers.get((candidate.system_id, candidate.session_id, task.criterion))
            if verdict is not None:
                cells[(candidate.system_id, candidate.session_id, task.criterion)] = (
                    0.0 if verdict else 1.0
                )
    return cells


def spreads(cells: dict, criterion: str) -> dict | None:
    """Model-to-model spread against session-to-session spread.

    Both are population standard deviations of the group means. A ratio under 1
    would say the table is ordering transcripts rather than models, and the
    ordering should not be read at all.
    """
    values = {(m, s): v for (m, s, c), v in cells.items() if c == criterion}
    if len(values) < 20:
        return None
    by_model, by_session = defaultdict(list), defaultdict(list)
    for (model, session), value in values.items():
        by_model[model].append(value)
        by_session[session].append(value)
    if len(by_model) < 2 or len(by_session) < 2:
        return None

    models = pstdev([mean(v) for v in by_model.values()])
    sessions = pstdev([mean(v) for v in by_session.values()])
    return {
        "between_models": round(models, 4),
        "between_sessions": round(sessions, 4),
        "ratio": round(models / sessions, 3) if sessions else None,
    }


def separable(cells: dict, criterion: str, rng: random.Random) -> dict | None:
    """Which model pairs survive resampling the sessions, and the gap it takes.

    The threshold reported is the median half-width of the interval on a
    difference. Two rows closer together than that are one reading printed
    twice, whatever order they happen to be in.
    """
    models = sorted({m for m, _, c in cells if c == criterion})
    sessions = sorted({s for _, s, c in cells if c == criterion})
    if len(models) < 2 or len(sessions) < 3:
        return None

    pairs = apart = 0
    half_widths = []
    for index, first in enumerate(models):
        for second in models[index + 1 :]:
            paired = [
                (cells[(first, s, criterion)], cells[(second, s, criterion)])
                for s in sessions
                if (first, s, criterion) in cells and (second, s, criterion) in cells
            ]
            if len(paired) < 5:
                continue
            pairs += 1
            differences = []
            for _ in range(DRAWS):
                draw = [paired[rng.randrange(len(paired))] for _ in paired]
                differences.append(mean(a for a, _ in draw) - mean(b for _, b in draw))
            differences.sort()
            low = differences[int(0.025 * DRAWS)]
            high = differences[int(0.975 * DRAWS)]
            if low > 0 or high < 0:
                apart += 1
            half_widths.append((high - low) / 2)

    if not pairs:
        return None
    half_widths.sort()
    return {
        "pairs": pairs,
        "separable": apart,
        "share": round(apart / pairs, 4),
        "threshold": round(half_widths[len(half_widths) // 2], 3),
    }


#: What a track's models are banded on. The criteria tracks average all six,
#: which is what "how good is the Czech" means here. The PDSQI tracks average
#: the attributes that are not flat -- adding a column every model scores 5.00
#: on does not change who is ahead, but it shrinks every difference against the
#: threshold and would merge bands that are really apart.
COMPOSITES = {
    # Named rather than left to the scorer. `None` here meant "every criterion",
    # which silently included `quotes` -- withdrawn
    # from the tables because it turned out to measure the prompt's punctuation
    # rather than the models. A band built on a column the tables refuse to draw
    # ranks models on something the reader is never shown and is told not to
    # believe.
    "czech-real": report.DRAWN_CRITERIA,
    "czech-translated": report.DRAWN_CRITERIA,
    "czech-real-pdsqi": ("accurate", "thorough", "succinct"),
    "czech-translated-pdsqi": ("accurate", "thorough", "succinct"),
}


def bands(per_note: dict, rng: random.Random) -> dict | None:
    """Models grouped so that within a band nothing separates them.

    A ranking of eleven models over ten notes is mostly an ordering of noise,
    and printing it invites the one reading it cannot support. Bands say the
    same measurement without the invitation: a new band starts where the gap
    from the band's best exceeds what resampling the sessions can rule out.

    The threshold is the median half-width of the interval on a pairwise
    difference, the same quantity `separable` reports, computed on the
    composite rather than on a single column.
    """
    models = sorted({m for m, _ in per_note})
    sessions = sorted({s for _, s in per_note})
    if len(models) < 2 or len(sessions) < 3:
        return None

    score = {m: mean([per_note[(m, s)] for s in sessions if (m, s) in per_note]) for m in models}
    order = sorted(models, key=lambda m: -score[m])

    half_widths = []
    for index, first in enumerate(order):
        for second in order[index + 1 :]:
            paired = [
                (per_note[(first, s)], per_note[(second, s)])
                for s in sessions
                if (first, s) in per_note and (second, s) in per_note
            ]
            if len(paired) < 5:
                continue
            differences = []
            for _ in range(DRAWS):
                draw = [paired[rng.randrange(len(paired))] for _ in paired]
                differences.append(mean(a for a, _ in draw) - mean(b for _, b in draw))
            differences.sort()
            half_widths.append(
                (differences[int(0.975 * DRAWS)] - differences[int(0.025 * DRAWS)]) / 2
            )
    if not half_widths:
        return None
    half_widths.sort()
    threshold = half_widths[len(half_widths) // 2]

    grouped, current = [], [order[0]]
    for model in order[1:]:
        if score[current[0]] - score[model] > threshold:
            grouped.append(current)
            current = [model]
        else:
            current.append(model)
    grouped.append(current)

    return {
        "threshold": round(threshold, 3),
        "sessions": len(sessions),
        "bands": [
            {
                "models": band,
                "high": round(score[band[0]], 3),
                "low": round(score[band[-1]], 3),
            }
            for band in grouped
        ],
    }


def _composite(cells: dict, keys) -> dict:
    """One number per (model, session): the mean of the columns that count."""
    grouped = defaultdict(list)
    for (model, session, criterion), value in cells.items():
        if keys is None or criterion in keys:
            grouped[(model, session)].append(value)
    return {pair: mean(values) for pair, values in grouped.items() if values}


def _pdsqi_cells(task_name: str, judge_model: str, budget: int) -> dict:
    """Every (model, session, attribute) PDSQI score, from the cache."""
    from tnb.scoring import czech_pdsqi, pdsqi_run

    loader = (
        czech_task.load_real if task_name == czech_task.NAME_REAL else czech_task.load_translated
    )
    candidates = list(czech_pdsqi.from_generations(loader(), task_name=task_name))
    client = judge.Judge(judge.config_from_env(model=judge_model, thinking_budget=budget))
    scored = pdsqi_run.from_cache(
        candidates,
        client,
        with_transcript=czech_pdsqi.transcripts_may_leave(task_name),
        render=czech_task.render_note,
        judge_prompt_version=czech_pdsqi.JUDGE_PROMPT_VERSION,
    )
    return {
        (note.candidate.system_id, note.candidate.session_id, key): value
        for note in scored
        for key, value in note.scored.items()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--thinking-budget", type=int, default=2048)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args(argv)

    load_dotenv(REPO / ".env")
    payload: dict = {"draws": DRAWS, "seed": SEED, "tracks": {}}

    for track, task_name in (
        (results.TRACK_CZECH_REAL, czech_task.NAME_REAL),
        (results.TRACK_CZECH_TRANSLATED, czech_task.NAME_TRANSLATED),
    ):
        for judge_model in (judge.DEFAULT_MODEL, judge.SECOND_JUDGE):
            cells = _cells(task_name, judge_model, args.thinking_budget)
            if not cells:
                continue
            rng = random.Random(SEED)  # noqa: S311 -- a threshold, not a secret
            block = {}
            for criterion in czech.CRITERION_KEYS:
                spread = spreads(cells, criterion)
                gaps = separable(cells, criterion, rng)
                if spread or gaps:
                    block[criterion] = {"spread": spread, "gaps": gaps}
            if block:
                payload["tracks"].setdefault(track, {})[judge_model] = block
            grouped = bands(_composite(cells, COMPOSITES[track]), rng)
            if grouped:
                payload.setdefault("bands", {}).setdefault(track, {})[judge_model] = grouped

    # The quality tracks band too. Their per-note scores come from the PDSQI
    # cache rather than the criteria's, and they are banded on the attributes
    # that vary: adding a column every model scores 5.00 on does not change who
    # is ahead, but it shrinks every difference against the threshold and would
    # merge bands that are really apart.
    for track, task_name in (
        (results.TRACK_CZECH_REAL_PDSQI, czech_task.NAME_REAL),
        (results.TRACK_CZECH_TRANSLATED_PDSQI, czech_task.NAME_TRANSLATED),
    ):
        for judge_model in (judge.DEFAULT_MODEL, judge.SECOND_JUDGE):
            cells = _pdsqi_cells(task_name, judge_model, args.thinking_budget)
            if not cells:
                continue
            rng = random.Random(SEED)  # noqa: S311 -- a threshold, not a secret
            grouped = bands(_composite(cells, COMPOSITES[track]), rng)
            if grouped:
                payload.setdefault("bands", {}).setdefault(track, {})[judge_model] = grouped

    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for track, judges in payload["tracks"].items():
        for judge_model, block in judges.items():
            print(f"\n### {track} | {judge_model}")
            print(
                f"{'criterion':14}{'models':>9}{'sessions':>10}{'ratio':>7}"
                f"{'separable':>11}{'gap needed':>12}"
            )
            for criterion, entry in block.items():
                spread, gaps = entry["spread"], entry["gaps"]
                if not spread or not gaps:
                    continue
                print(
                    f"{criterion:14}{spread['between_models']:>9.3f}"
                    f"{spread['between_sessions']:>10.3f}{spread['ratio']:>7.2f}"
                    f"{gaps['separable']:>5}/{gaps['pairs']:<5}{gaps['threshold']:>12.2f}"
                )
    for track, judges in (payload.get("bands") or {}).items():
        for judge_model, grouped in judges.items():
            print(
                f"\n### bands: {track} | {judge_model}"
                f"  (threshold {grouped['threshold']:.2f}, {grouped['sessions']} sessions)"
            )
            for number, band in enumerate(grouped["bands"], start=1):
                print(
                    f"  band {number}  {band['high']:.2f}-{band['low']:.2f}  "
                    + ", ".join(band["models"])
                )

    print(f"\nwrote {args.target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
