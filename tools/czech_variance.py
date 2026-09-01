"""How big a gap between two models has to be before it is a gap.

A table of proportions invites its reader to compare neighbouring rows. With at
most ten notes per model, most of those comparisons are reading noise, and
saying so with a number is the difference between a caveat somebody skips and a
threshold they can apply to the row in front of them.

Two questions, in the order they matter.

**Is the table reading models or sessions?** The design asks every model for a
note from every transcript -- that is what makes the comparison possible at all
-- but if sessions differ from each other more than models do, the ordering is a
fact about which transcripts were drawn. Measured: the spread between model
means against the spread between session means, criterion by criterion.

**Which pairs of models are actually separable?** The sessions are resampled with
replacement, both models rescored on each resample, and the difference between
them read off the middle 95% of the resulting distribution. **Paired on the
session**, on the sessions both models of a pair actually have -- a pair with
fewer than five in common is not compared at all -- because a test that ignored
the pairing would throw away the design's whole advantage. The design is not the
outcome: e-INFRA refused some calls and some answers never parsed, so what each
model has is counted per model and written into the `coverage` block rather than
assumed.

The number this produces is the one a reader needs: the width of that interval
is how far apart two rows must be before their order means anything. Everything
narrower is the same reading twice.

Sessions are resampled and models are not. `docs/limitations.md` records a
published "detected" verdict that came from resampling conversations only, which
treated four models as the whole of OpenAI -- that was a claim about a *family*
of models, where the models are the sample. Here the models are the whole
population being compared, named individually, and the sessions are the sample
that could have been drawn differently. How many models that is differs by
track and is not stated here: it was written as "the eleven models" and the
Deepsy tracks have twelve, which is the kind of sentence a later run makes
quietly false.

Writes `local/czech-variance.json` for `tools/czech_brief.py`.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from statistics import mean, pstdev
from typing import NamedTuple

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

from tnb import judge, report, results  # noqa: E402
from tnb.scoring import czech, czech_run, deepsy_run  # noqa: E402
from tnb.tasks import czech as czech_task  # noqa: E402
from tnb.tasks import deepsy as deepsy_task  # noqa: E402

DEFAULT_TARGET = REPO / "local" / "czech-variance.json"

#: Resamples. Two thousand puts the 2.5th percentile fifty draws from the end,
#: which is enough for a threshold reported to two decimals.
DRAWS = 2000

#: Fixed, because a threshold that moves between runs invites running it again.
SEED = 0


class Spec(NamedTuple):
    """How one criteria track's notes are found, rendered and looked up.

    A table rather than a branch on the track name. `_cells` used to pick its
    corpus with `task_name == czech_task.NAME_REAL` -- that is `"czech-real"`,
    so `"deepsy-real"` compares false and would have silently loaded the
    *translated* sessions, pairing every note with the wrong transcript. That is
    the exact failure `CLAUDE.md` records against TN-Eval's stated selection.
    """

    #: The generation cache's task directory: `czech-real`, `deepsy-translated`.
    task_name: str
    #: The corpus this track's notes were written from.
    load: Callable[[], list]
    #: Which assembler turns generations into candidates. Deepsy needs its own:
    #: a note is three separate calls and two of three is not a note.
    assemble: Callable[..., object]
    #: SOAP headings, or Deepsy's three sections. Whatever wrote the prompt the
    #: cached answer was keyed on.
    render: Callable[[dict], str]
    #: Where this track's judge answers live. Deepsy needs a root of its own:
    #: `judge.cache_path` is keyed on judge, rubric, provider, system, session
    #: and unit, and Deepsy shares every one of those six with the SOAP track --
    #: same sessions, same models, same six criteria, same `czech-criteria-v2`.
    #: Only the note differs. See `tests/test_judge_cache_collision.py`.
    cache_root: Path | None = None


#: The four criteria tracks, in the order they are drawn.
CRITERIA_TRACKS = {
    results.TRACK_CZECH_REAL: Spec(
        czech_task.NAME_REAL,
        czech_task.load_real,
        czech_run.from_generations,
        czech_task.render_note,
    ),
    results.TRACK_CZECH_TRANSLATED: Spec(
        czech_task.NAME_TRANSLATED,
        czech_task.load_translated,
        czech_run.from_generations,
        czech_task.render_note,
    ),
    results.TRACK_DEEPSY_REAL: Spec(
        deepsy_task.NAME_REAL,
        deepsy_task.load_real,
        deepsy_run.from_generations,
        deepsy_task.render_note,
        judge.CACHE_DIR / deepsy_task.PROMPT_VERSION,
    ),
    results.TRACK_DEEPSY_TRANSLATED: Spec(
        deepsy_task.NAME_TRANSLATED,
        deepsy_task.load_translated,
        deepsy_run.from_generations,
        deepsy_task.render_note,
        judge.CACHE_DIR / deepsy_task.PROMPT_VERSION,
    ),
}


#: How each PDSQI track's notes are found, rendered and looked up: the same
#: three facts `Spec` carries for the criteria tracks. The Deepsy pair needs a
#: cache root of its own because `judge.cache_path` holds the judge, the prompt
#: version, the provider, the system, the session and the attribute -- and the
#: Deepsy PDSQI track shares all six with the SOAP one. Only the note differs,
#: and the note is not in the path.
PDSQI_CORPORA = {
    czech_task.NAME_REAL: (czech_task.load_real, czech_task.render_note, None),
    czech_task.NAME_TRANSLATED: (czech_task.load_translated, czech_task.render_note, None),
    deepsy_task.NAME_REAL: (
        deepsy_task.load_real,
        deepsy_task.render_note,
        judge.CACHE_DIR / deepsy_task.PROMPT_VERSION,
    ),
    deepsy_task.NAME_TRANSLATED: (
        deepsy_task.load_translated,
        deepsy_task.render_note,
        judge.CACHE_DIR / deepsy_task.PROMPT_VERSION,
    ),
}


class Read(NamedTuple):
    """The cells, and how much of what was asked for came back.

    The coverage travels with the cells because a band drawn over 98% of the
    questions and a band drawn over all of them are different claims, and the
    difference is invisible once the cells are a bare dict.
    """

    cells: dict[tuple[str, str, str], float]
    #: (model, session, criterion) triples the notes on disk imply.
    expected: int
    #: How many of them the cache answers.
    answered: int


def _cells(spec: Spec, judge_model: str, budget: int) -> Read:
    """Every (model, session, criterion) score, from the cache, asking nothing."""
    import czech_sample

    candidates = list(spec.assemble(spec.load(), task_name=spec.task_name))
    answers = czech_sample._read(
        candidates, judge_model, budget, render=spec.render, cache_root=spec.cache_root
    )

    cells: dict[tuple[str, str, str], float] = {}
    expected = 0
    for candidate in candidates:
        # The same renderer that `_read` asked with. If these two ever drift
        # apart the prompt handed to `load_cached` stops matching the one its
        # path was keyed on, and every answer is rejected on the digest.
        note = spec.render(candidate.note)
        for task in czech.build_tasks(note):
            expected += 1
            verdict = answers.get((candidate.system_id, candidate.session_id, task.criterion))
            if verdict is not None:
                cells[(candidate.system_id, candidate.session_id, task.criterion)] = (
                    0.0 if verdict else 1.0
                )
    return Read(cells, expected, len(cells))


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
    # The same six, deliberately, and not the PDSQI subset. Deepsy is scored by
    # `czech.build_tasks` under `czech-criteria-v2` -- the identical instrument --
    # and `report.COLUMNS` draws all six of `DRAWN_CRITERIA` in its tables, so
    # this is exactly the set the reader is shown. The reason the PDSQI tracks
    # drop columns does not apply: no Deepsy criterion is flat, the
    # between-model spread running 0.067 to 0.303 across the four (track, judge)
    # tables. Banding Deepsy on a different set would turn any SOAP-to-Deepsy
    # difference into a fact about the two composites rather than the formats.
    "deepsy-real": report.DRAWN_CRITERIA,
    "deepsy-translated": report.DRAWN_CRITERIA,
}

#: Which PDSQI tracks share a half, and therefore a composite. A fixed
#: attribute list cannot serve all four: the real half is rated from the note
#: alone, so `accurate` and `thorough` -- the two that need the session -- are
#: never asked there, and the triple this used to name banded that half on
#: `succinct` by itself while the table beside it drew six columns. Each half's
#: composite is instead taken from the cells, by the same rule the `COMPOSITES`
#: docstring states for flat columns: the attributes that exist there and
#: separate models. One set per half, shared by SOAP and Deepsy and by both
#: judges, so a difference between two tracks of a half is a fact about the
#: formats and not about two composites.
PDSQI_HALVES = {
    "real": (
        (results.TRACK_CZECH_REAL_PDSQI, czech_task.NAME_REAL),
        (results.TRACK_DEEPSY_REAL_PDSQI, deepsy_task.NAME_REAL),
    ),
    "translated": (
        (results.TRACK_CZECH_TRANSLATED_PDSQI, czech_task.NAME_TRANSLATED),
        (results.TRACK_DEEPSY_TRANSLATED_PDSQI, deepsy_task.NAME_TRANSLATED),
    ),
}


#: How far the threshold moves between resampling seeds. Not a preference: band
#: membership depends on the seed ONLY through this one number, because the
#: scores and their order are arithmetic and the banding rule compares a fixed
#: gap against it. So a bound on the threshold bounds every way a seed can
#: redraw a band.
#:
#: **Measured, over 25 seeds on the eight criteria tables.** The widest ranges
#: were 0.133-0.142 (`czech-translated`, `gpt-5.6-terra`) and 0.158-0.167
#: (`deepsy-translated`, `gemini-3.1-pro-preview`); the narrowest did not move
#: at all. Rounded up to 0.01, and checked against what those seeds did rather
#: than assumed: banding at plus and minus this flags every model that actually
#: changed band -- `glm-5`, `glm-5.2` and `qwen3.8-27b` on `deepsy-real` under
#: `gemini-3.1-pro-preview`, `gemma4`, `glm-5.2` and `gpt-oss-120b` on
#: `deepsy-translated` under the same judge -- and some besides.
#:
#: The extra ones are not slack. On `czech-real` under `gpt-5.6-terra` the
#: threshold is 0.167 and the nearest value that redraws a band is 0.170, three
#: thousandths away: those 25 seeds never landed on the far side of it, and a
#: separate run that seeded the whole loop reported exactly that table's
#: `gemma4` and `kimi-k3` as unstable. A model three thousandths from a boundary
#: is not placed by this measurement whether or not a particular draw notices.
THRESHOLD_JITTER = 0.01


def _split(order: list[str], score: dict[str, float], threshold: float) -> list[list[str]]:
    """The banding rule itself: a new band where the gap from its best exceeds `threshold`."""
    grouped, current = [], [order[0]]
    for model in order[1:]:
        if score[current[0]] - score[model] > threshold:
            grouped.append(current)
            current = [model]
        else:
            current.append(model)
    grouped.append(current)
    return grouped


def _places(grouped: list[list[str]]) -> dict[str, int]:
    """Which band each model landed in, counting from one."""
    return {model: number for number, band in enumerate(grouped, start=1) for model in band}


def bands(per_note: dict, rng: random.Random) -> dict | None:
    """Models grouped so that within a band nothing separates them.

    A ranking of a dozen models over ten notes is mostly an ordering of noise,
    and printing it invites the one reading it cannot support. Bands say the
    same measurement without the invitation: a new band starts where the gap
    from the band's best exceeds what resampling the sessions can rule out.

    A model's score is the mean of the notes it has, and the models do not all
    have the same ones -- so the bands rest on unequal denominators and the
    `coverage` block says whose, per model, for the document to mark.

    The threshold is the median half-width of the interval on a pairwise
    difference, the same quantity `separable` reports, computed on the
    composite rather than on a single column.

    **`rng` is this function's own, never the separability loop's.** `main`
    used to hand one generator to the six `separable` calls and then to this
    one, so the threshold depended on how much randomness those six had already
    drawn -- a quantity about the criteria loop and not about the data being
    banded. Measured: on `deepsy-real` under `gemini-3.1-pro-preview` the
    leftover state gave 0.160 where a fresh generator gives 0.162, and
    `qwen3.8-27b` fell between the two.

    **Decoupling them does not make the bands stable, and the payload says so.**
    The threshold still moves with the seed, and `unresolved` names the models
    that a move of `THRESHOLD_JITTER` either way puts in a different band. They
    are drawn in a band because the table has to draw them somewhere; the
    measurement does not place them.
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

    grouped = _split(order, score, threshold)
    # Which models the threshold's own imprecision moves. Band membership is a
    # step function of the threshold and of nothing else -- the scores and their
    # order are arithmetic -- so banding at each end of `THRESHOLD_JITTER`
    # enumerates every model a different resample could redraw, cascades
    # included, and costs no further resampling.
    low = _places(_split(order, score, threshold - THRESHOLD_JITTER))
    high = _places(_split(order, score, threshold + THRESHOLD_JITTER))
    unresolved = sorted(model for model in order if low[model] != high[model])

    return {
        "threshold": round(threshold, 3),
        "sessions": len(sessions),
        "jitter": THRESHOLD_JITTER,
        "unresolved": unresolved,
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


def _varying(read: Read) -> set[str]:
    """The attributes in `read` that separate models.

    The rule the `COMPOSITES` docstring states, applied to the cells a run
    actually holds: a column every model averages the same on cannot change an
    order, and averaged into a composite it only shrinks every difference
    against the threshold, merging bands the data holds apart. The fixed triple
    this replaces never applied that rule to the real half, where two of its
    three columns are never asked.
    """
    per: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for (_model, _session, attribute), value in read.cells.items():
        per[attribute][_model].append(value)
    return {
        attribute
        for attribute, models in per.items()
        if len({round(mean(values), 6) for values in models.values()}) > 1
    }


def _pdsqi_cells(task_name: str, judge_model: str, budget: int) -> Read:
    """Every (model, session, attribute) PDSQI score, from the cache.

    A `Read` like the criteria tracks', and for the same reason: a band drawn
    over 98% of the questions and one drawn over all of them are different
    claims, so the coverage travels with the cells rather than being recovered
    later from a bare dict.
    """
    from tnb.scoring import czech_pdsqi, pdsqi_run

    # A lookup that raises, not a conditional that falls through. The old
    # form asked `task_name == czech_task.NAME_REAL` and took the translated
    # loader otherwise, so a Deepsy task name -- which compares false -- would
    # have paired every Deepsy note with a translated AnnoMI transcript and
    # rendered it with the four-heading SOAP renderer, which emits nothing. The
    # `Spec` docstring above records that same failure on the criteria side.
    loader, render, cache_root = PDSQI_CORPORA[task_name]
    candidates = list(czech_pdsqi.from_generations(loader(), task_name=task_name))
    client = judge.Judge(judge.config_from_env(model=judge_model, thinking_budget=budget))
    scored = pdsqi_run.from_cache(
        candidates,
        client,
        with_transcript=czech_pdsqi.transcripts_may_leave(task_name),
        render=render,
        cache_root=cache_root,
        judge_prompt_version=czech_pdsqi.JUDGE_PROMPT_VERSION,
    )
    cells = {
        (note.candidate.system_id, note.candidate.session_id, key): value
        for note in scored
        for key, value in note.scored.items()
    }
    # What the notes on disk imply, the same quantity `_cells` counts: one
    # question per candidate per attribute this corpus is allowed to ask.
    expected = len(candidates) * len(czech_pdsqi.attribute_keys(task_name))
    return Read(cells, expected, len(cells))


def _coverage(read: Read, keys, per_note: dict) -> dict:
    """What a band was computed over, for the track and for each model in it.

    The track totals answer "is this drawn over all the questions". The
    per-model block answers the one a reader needs at the row: the bands rest
    on unequal denominators -- one model's nine notes beside another's ten, one
    model's note averaged over five columns instead of six -- and a band table
    printed without that is an uneven comparison the reader is not told is
    uneven. `tools/czech_brief.py` marks these rows the way its score tables
    already mark a thin one.

    **A column nobody was allowed to ask is not a missing answer.** The real
    corpus is rated from the note alone, so `accurate` and `thorough` -- the two
    that need the session -- are never put to a judge there. Counting them as
    unanswered would have called every real note partial and hidden the columns
    the band was actually built on. So `columns` is what the track really has
    and `columns_absent` names what it does not, beside the `columns_named` the
    composite asked for.
    """
    present = {criterion for _model, _session, criterion in read.cells}
    available = tuple(key for key in keys if key in present)
    drawn: dict[tuple[str, str], int] = defaultdict(int)
    for model, session, criterion in read.cells:
        if criterion in available:
            drawn[(model, session)] += 1

    systems: dict[str, dict[str, int]] = {}
    for (model, _session), count in drawn.items():
        block = systems.setdefault(model, {"notes": 0, "answered": 0, "partial": 0})
        block["notes"] += 1
        block["answered"] += count
        block["partial"] += 1 if count < len(available) else 0

    return {
        "expected": read.expected,
        "answered": read.answered,
        "notes": len(per_note),
        "sessions": len({session for _model, session in per_note}),
        "columns": len(available),
        "columns_named": len(keys),
        "columns_absent": [key for key in keys if key not in present],
        "partial": sum(1 for count in drawn.values() if count < len(available)),
        "systems": dict(sorted(systems.items())),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--thinking-budget", type=int, default=2048)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="TRACK",
        help=(
            "compute these tracks and merge them into the payload already on disk, "
            "leaving every other track's numbers exactly as they were"
        ),
    )
    args = parser.parse_args(argv)

    load_dotenv(REPO / ".env")
    # With `--only`, start from what is already there. A band rests on the
    # judge cache, and a cache can lose answers between two runs of this tool --
    # recomputing an untouched track from a thinner cache would quietly narrow
    # a published band. So the six sets computed on 2026-08-29 are carried
    # forward rather than re-derived, and only the named tracks are written.
    payload: dict = {"draws": DRAWS, "seed": SEED, "tracks": {}}
    if args.only and args.target.exists():
        payload = json.loads(args.target.read_text(encoding="utf-8"))
        payload["draws"], payload["seed"] = DRAWS, SEED

    for track, spec in CRITERIA_TRACKS.items():
        if args.only and track not in args.only:
            continue
        for judge_model in (judge.DEFAULT_MODEL, judge.SECOND_JUDGE):
            read = _cells(spec, judge_model, args.thinking_budget)
            root = spec.cache_root or judge.CACHE_DIR
            # Loud, not `continue`. A track that produced nothing used to vanish
            # from the payload in silence, and the document then said no figure
            # had been computed for it -- true, and indistinguishable from a
            # wrong cache root or a renderer that emits headings the task
            # builder strips. Both of those return exactly zero cells.
            if not read.cells:
                print(
                    f"!! {track} | {judge_model}: 0 of {read.expected} answers under {root}"
                    " -- nothing banded, nothing separability-tested.",
                    flush=True,
                )
                continue
            rng = random.Random(SEED)  # noqa: S311 -- a threshold, not a secret
            block = {}
            for criterion in czech.CRITERION_KEYS:
                spread = spreads(read.cells, criterion)
                gaps = separable(read.cells, criterion, rng)
                if spread or gaps:
                    block[criterion] = {"spread": spread, "gaps": gaps}
            if block:
                payload["tracks"].setdefault(track, {})[judge_model] = block
            else:
                print(f"!! {track} | {judge_model}: no criterion cleared the guards.", flush=True)

            keys = COMPOSITES[track]
            per_note = _composite(read.cells, keys)
            # Its own generator. Passing `rng` on from the loop above made the
            # band threshold depend on how much randomness six `separable` calls
            # had already drawn, which is a fact about the criteria loop and not
            # about the models being banded -- and it moved a model.
            grouped = bands(per_note, random.Random(SEED))  # noqa: S311 -- not a secret
            if grouped:
                payload.setdefault("bands", {}).setdefault(track, {})[judge_model] = grouped
            else:
                print(
                    f"!! {track} | {judge_model}: too few models or sessions to band.", flush=True
                )

            # What the figures above were computed over. A band drawn on 98% of
            # the questions and one drawn on all of them are different claims,
            # and `_composite` averages a note over whatever criteria came back,
            # so `partial` is the count of notes that entered the band on fewer
            # than the full set of columns.
            payload.setdefault("coverage", {}).setdefault(track, {})[judge_model] = _coverage(
                read, keys, per_note
            )

    # The quality tracks band too. Their per-note scores come from the PDSQI
    # cache rather than the criteria's. Each half bands on the attributes that
    # exist on it and separate models -- a column every model scores 5.00 on
    # does not change who is ahead, but it shrinks every difference against
    # the threshold and would merge bands that are really apart -- and the set
    # is recorded under `composites`, so the document can name the columns a
    # band was built from.
    for half, tracks in PDSQI_HALVES.items():
        # Both tracks of the half are read even under `--only`: the composite is
        # the half's, so recomputing one track alone would band it on a
        # different set of columns than the track the reader compares it with.
        reads: dict[tuple[str, str], Read] = {}
        for track, task_name in tracks:
            for judge_model in (judge.DEFAULT_MODEL, judge.SECOND_JUDGE):
                read = _pdsqi_cells(task_name, judge_model, args.thinking_budget)
                if read.cells:
                    reads[(track, judge_model)] = read
        if not reads:
            continue
        keys = tuple(sorted(set.union(*(_varying(read) for read in reads.values()))))
        if not keys:
            print(f"!! {half} half: no PDSQI attribute separates any model.", flush=True)
            continue
        payload.setdefault("composites", {})[half] = list(keys)
        for (track, judge_model), read in reads.items():
            if args.only and track not in args.only:
                continue
            per_note = _composite(read.cells, keys)
            grouped = bands(per_note, random.Random(SEED))  # noqa: S311 -- not a secret
            if grouped:
                payload.setdefault("bands", {}).setdefault(track, {})[judge_model] = grouped
            # These four tables are drawn from the same panel as the criteria
            # ones, so they carry the same denominators or the panel has a hole
            # where two of its six tracks should be -- which is the shape this
            # whole block exists to close.
            payload.setdefault("coverage", {}).setdefault(track, {})[judge_model] = _coverage(
                read, keys, per_note
            )

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
            if grouped["unresolved"]:
                print(
                    f"  not placed by this measurement (a threshold "
                    f"+/-{grouped['jitter']} moves them): " + ", ".join(grouped["unresolved"])
                )

    print(f"\nwrote {args.target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
