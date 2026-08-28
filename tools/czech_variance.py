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

from tnb import judge, results  # noqa: E402
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
        # The counted column has no cached answer to find.
        if czech.has_content(note) and czech.has_quotes(note):
            cells[(candidate.system_id, candidate.session_id, "quotes")] = (
                0.0 if czech.has_straight_quotes(note) else 1.0
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
    print(f"\nwrote {args.target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
