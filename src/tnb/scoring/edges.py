"""Which "beats outright" claims survive resampling the conversations they rest on.

A system beats another outright when it is at least as good on every column of
one instrument under both judges and strictly better somewhere
(`concordance._dominates`). That relation was drawn on the leaderboard for one
day, 2026-09-01 -- as a count per system and as an order -- and taken off the
same day: every edge compared two stored means, and nobody had asked whether
the differences survive resampling the conversations. When one leg of each
rubric edge was tested, a substantial share of the 29 did not hold.

This module tests every edge whole. For an ordered pair the claim has as many
legs as there are (judge, column) pairs -- six on the rubric, sixteen on
PDSQI-9, ten on iCARE -- and each leg is a difference of two means over
conversations both systems were scored on. All legs are resampled **together**:
one draw of conversations, with replacement, from the set every leg shares,
and the claim holds in that draw when the winner is at least as good on every
leg and ahead on at least one. The fraction of draws in which it holds is the
edge's `p_holds`. An edge is kept at 0.95, the threshold the band analysis
uses, and the counts at 0.90 and 0.99 are published beside it so the choice is
visible rather than buried.

Paired, like `saturation.paired_intervals`, and for the same reason: a
conversation that is hard for one system is hard for the other, and resampling
both on the same draw removes that shared difficulty from the comparison
instead of counting it as disagreement.

What comes out is `docs/edges-<track>.json`: every edge with its legs and the
thinnest of them, the edges that could not be tested and why, and the layers of
the surviving graph -- group 1 is beaten by no tested edge, group 2 only by
group 1, and so on. Nothing here averages columns, weights them, or breaks a
tie: two systems no surviving edge connects share whatever the layers give
them. An edge without enough shared conversations is named untestable, never
counted as false and never as true.
"""

from __future__ import annotations

import datetime as dt
import json
import random
from collections.abc import Sequence
from pathlib import Path

from tnb import judge, results
from tnb.scoring import concordance, saturation

#: Draws per edge. Ten thousand rather than the band analysis's two thousand:
#: the question is whether a fraction clears 0.95, and the Monte-Carlo error of
#: a fraction near 0.95 is sqrt(0.95 * 0.05 / n) -- 0.0049 at 2 000 draws and
#: 0.0022 at 10 000.
SAMPLES = 10_000
SEED = saturation.BOOTSTRAP_SEED
#: The fraction of draws an edge has to hold in to be kept. The band analysis's
#: threshold, so the two analyses answer "can these be told apart" the same way.
THRESHOLD = 0.95
THRESHOLDS = (0.90, 0.95, 0.99)
#: Fewest shared conversations an edge may be tested on. Below this a resample
#: has too few distinct draws to say anything, and the edge is named untestable
#: rather than tested on a handful.
MIN_SHARED = 10
JUDGES = (judge.DEFAULT_MODEL, judge.SECOND_JUDGE)

#: judge -> system -> column -> session -> value
PerSession = dict[str, dict[str, dict[str, dict[str, float]]]]


def artefact_path(track: str, docs_dir: Path | None = None) -> Path:
    from tnb import report

    return (docs_dir or report.DOCS_DIR) / f"edges-{track}.json"


def load(track: str, docs_dir: Path | None = None) -> dict | None:
    """The committed artefact for one track, or None when none has been built."""
    path = artefact_path(track, docs_dir)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# --- the test -------------------------------------------------------------------


def examine(
    track: str,
    columns: Sequence[tuple[str, int]],
    by_judge: dict[str, dict[str, dict[str, float]]],
    per_session: PerSession,
    *,
    samples: int = SAMPLES,
    seed: int = SEED,
    min_shared: int = MIN_SHARED,
    threshold: float = THRESHOLD,
    thresholds: Sequence[float] = THRESHOLDS,
) -> dict:
    """Test every edge of the dominance graph and layer what survives.

    ``by_judge`` holds the published means -- {judge: {system: {column: value}}}
    -- and decides which edges exist, exactly as the concordance panel does.
    ``per_session`` holds the per-conversation values the means were taken
    over, and decides which of those edges hold. Pure: everything it reads is
    an argument, so the arithmetic is pinned on constructed cases in the tests.
    """
    decimals = dict(columns)
    names = [name for name, _ in columns]
    judges = sorted(by_judge)

    every = sorted(set().union(*(set(scores) for scores in by_judge.values())))
    population: list[str] = []
    outside: list[dict] = []
    for system in every:
        missing = [
            f"{judge_model}:{column}"
            for judge_model in judges
            for column in names
            if by_judge[judge_model].get(system, {}).get(column) is None
        ]
        if missing:
            outside.append({"system": system, "missing": missing})
        else:
            population.append(system)

    stored = [
        (winner, loser)
        for winner in population
        for loser in population
        if winner != loser and concordance._dominates(winner, loser, by_judge, decimals)
    ]

    rng = random.Random(seed)
    tested: list[dict] = []
    untestable: list[dict] = []
    legs = [(judge_model, column) for judge_model in judges for column in names]
    for winner, loser in stored:
        values = {}
        shared_per_leg = {}
        for judge_model, column in legs:
            first = per_session.get(judge_model, {}).get(winner, {}).get(column, {})
            second = per_session.get(judge_model, {}).get(loser, {}).get(column, {})
            values[(judge_model, column)] = (first, second)
            shared_per_leg[(judge_model, column)] = set(first) & set(second)
        common = sorted(set.intersection(*shared_per_leg.values()))
        if len(common) < min_shared:
            starved = min(legs, key=lambda leg: (len(shared_per_leg[leg]), leg))
            untestable.append(
                {
                    "winner": winner,
                    "loser": loser,
                    "n_shared": len(common),
                    "why": (
                        f"{starved[0]}:{starved[1]} has {len(shared_per_leg[starved])} shared "
                        f"conversation(s); {min_shared} are needed"
                    ),
                }
            )
            continue
        tested.append(
            _resample(
                winner,
                loser,
                common,
                legs,
                values,
                by_judge,
                rng=rng,
                samples=samples,
                threshold=threshold,
            )
        )

    kept = [(edge["winner"], edge["loser"]) for edge in tested if edge["holds"]]
    grouped = layers(population, kept)
    return {
        "track": track,
        "judges": judges,
        "columns": names,
        "decimals": decimals,
        "samples": samples,
        "seed": seed,
        "threshold": threshold,
        "thresholds": list(thresholds),
        "min_shared": min_shared,
        "systems": population,
        "outside": outside,
        "edges": tested,
        "untestable": untestable,
        "counts": {
            "stored": len(stored),
            "tested": len(tested),
            "untestable": len(untestable),
            "holds": {
                f"{cut:.2f}": sum(1 for edge in tested if edge["p_holds"] >= cut)
                for cut in thresholds
            },
        },
        "layers": grouped,
        "undominated": grouped[0] if grouped else [],
    }


def _resample(
    winner: str,
    loser: str,
    common: list[str],
    legs: list[tuple[str, str]],
    values: dict,
    by_judge: dict,
    *,
    rng: random.Random,
    samples: int,
    threshold: float,
) -> dict:
    """One edge, every leg on the same draws."""
    n = len(common)
    diffs = {
        leg: [values[leg][0][session] - values[leg][1][session] for session in common]
        for leg in legs
    }
    ahead = dict.fromkeys(legs, 0)
    not_behind = dict.fromkeys(legs, 0)
    holds = 0
    population = range(n)
    for _ in range(samples):
        picked = rng.choices(population, k=n)
        all_legs = True
        some_leg = False
        for leg in legs:
            total = sum(map(diffs[leg].__getitem__, picked))
            if total > 0:
                ahead[leg] += 1
                not_behind[leg] += 1
                some_leg = True
            elif total == 0:
                not_behind[leg] += 1
            else:
                all_legs = False
        if all_legs and some_leg:
            holds += 1

    described = []
    for judge_model, column in legs:
        leg = (judge_model, column)
        described.append(
            {
                "judge": judge_model,
                "column": column,
                "n": len(set(values[leg][0]) & set(values[leg][1])),
                "difference": round(sum(diffs[leg]) / n, 4),
                "stored_difference": round(
                    by_judge[judge_model][winner][column] - by_judge[judge_model][loser][column], 4
                ),
                "p_ahead": ahead[leg] / samples,
                "p_not_behind": not_behind[leg] / samples,
            }
        )
    thinnest = min(described, key=lambda leg: (leg["p_not_behind"], leg["difference"]))
    p_holds = holds / samples
    return {
        "winner": winner,
        "loser": loser,
        "n_shared": n,
        "p_holds": p_holds,
        "holds": p_holds >= threshold,
        "legs": described,
        "thinnest": {
            "judge": thinnest["judge"],
            "column": thinnest["column"],
            "p_not_behind": thinnest["p_not_behind"],
            "difference": thinnest["difference"],
        },
    }


def layers(systems: Sequence[str], edges: Sequence[tuple[str, str]]) -> list[list[str]]:
    """Groups of the surviving graph, best first, with nothing breaking ties.

    Group 1 is every system no kept edge beats; group 2 is every system beaten
    only by group 1; and so on. Two systems no kept edge connects can share a
    group, and that is the reading: the evidence does not separate them.
    Dominance is a strict partial order, so the graph has no cycles; a cycle
    would still terminate here, with the systems in it left ungrouped.
    """
    beaten_by: dict[str, set[str]] = {system: set() for system in systems}
    for winner, loser in edges:
        if winner in beaten_by and loser in beaten_by:
            beaten_by[loser].add(winner)
    remaining = set(systems)
    grouped: list[list[str]] = []
    while remaining:
        free = sorted(system for system in remaining if not (beaten_by[system] & remaining))
        if not free:
            break
        grouped.append(free)
        remaining -= set(free)
    return grouped


# --- reading what the tables were built from -----------------------------------


def published(rows: list[results.Row], track: str) -> dict[str, dict[str, dict[str, float]]]:
    """{judge: {system_id: headline}} for the two judges' current rows of one track.

    Pass rows through `report.current_rows` first; like the concordance panel
    this raises rather than overwriting when a system appears twice under one
    judge, because two harness versions are two definitions of a measure.
    """
    out: dict[str, dict[str, dict[str, float]]] = {}
    for row in rows:
        if row.track != track or not row.is_scored or row.judge_model not in JUDGES:
            continue
        seen = out.setdefault(row.judge_model, {})
        if row.system_id in seen:
            raise ValueError(
                f"{row.system_id!r} appears twice for judge {row.judge_model!r} on {track!r}; "
                "pass rows through `report.current_rows` first"
            )
        seen[row.system_id] = dict(row.metrics.headline)
    return out


def _client(judge_model: str) -> judge.Judge:
    """A judge object for its fingerprint and name only; nothing here calls it."""
    return judge.Judge(judge.config_from_env(model=judge_model))


def _collect(out: dict, system: str, session: str, headline: dict[str, float]) -> None:
    for column, value in headline.items():
        out.setdefault(system, {}).setdefault(column, {})[session] = value


def soap_per_session(judge_model: str, *, cache_root: Path | None = None) -> dict:
    """{system_id: {column: {session: value}}} from the rubric answer cache.

    Through `run.from_cache`, the path `tnb score --cache-only` publishes from,
    so a per-conversation value here is exactly what the published mean
    averaged: notes the judge answered in full, and nothing else.
    """
    from tnb.scoring import run

    sessions = run.load_sessions()
    candidates = list(run.from_reference(sessions)) + list(run.from_generations(sessions))
    out: dict = {}
    for note in run.from_cache(candidates, _client(judge_model), cache_root=cache_root):
        if note.scores.is_complete:
            _collect(out, note.candidate.system_id, note.candidate.session_id, note.scores.headline)
    return out


def pdsqi_per_session(judge_model: str, *, cache_root: Path | None = None) -> dict:
    """{system_id: {attribute: {session: value}}} from the PDSQI-9 answer cache."""
    from tnb.scoring import pdsqi_run, run

    sessions = run.load_sessions()
    candidates = list(run.from_reference(sessions)) + list(run.from_generations(sessions))
    out: dict = {}
    for note in pdsqi_run.from_cache(candidates, _client(judge_model), cache_root=cache_root):
        if note.is_complete:
            _collect(out, note.candidate.system_id, note.candidate.session_id, note.scored)
    return out


def icare_per_session(judge_model: str, *, cache_root: Path | None = None) -> dict:
    """{system_id: {column: {session: value}}} for iCARE, asking nobody anything.

    TRACE comes from the judge's answer cache, BERTScore from its pair-keyed
    cache and ROUGE-L and the temporal columns are recomputed from the notes,
    which is what `tnb score-icare` does when everything is cached. A note
    whose BERTScore pair is not cached simply has no value in that column here;
    it is never computed, because computing it loads a model.
    """
    from tnb.scoring import icare as scorer
    from tnb.scoring import icare_run

    client = _client(judge_model)
    fingerprint = client.config.fingerprint()
    known: dict[str, float] = {}
    if scorer.BERT_CACHE.exists():
        known = json.loads(scorer.BERT_CACHE.read_text(encoding="utf-8"))

    out: dict = {}
    for candidate in icare_run.from_generations(icare_run.load_sessions()):
        answers: dict[str, str] = {}
        for task in scorer.build_trace_tasks(candidate.note, candidate.conversation):
            path = judge.cache_path(
                client.config.model,
                scorer.JUDGE_PROMPT_VERSION,
                candidate.provider,
                candidate.system_id,
                candidate.session_id,
                task.unit,
                fingerprint=fingerprint,
                root=cache_root,
            )
            record = judge.load_cached(path, fingerprint, task.prompt, accepts=task.accepts)
            if record is not None:
                answers[task.unit] = record["answer"]
        note, gold = scorer.comparable_pair(candidate.note, candidate.reference)
        bert = known.get(scorer._bert_key(note, gold))
        scores = scorer.aggregate(candidate.note, candidate.reference, answers, bert=bert)
        if scores.is_complete:
            _collect(out, candidate.system_id, candidate.session_id, scores.headline)
    return out


LOADERS = {
    results.TRACK_TNEVAL: soap_per_session,
    results.TRACK_PDSQI: pdsqi_per_session,
    results.TRACK_ICARE: icare_per_session,
}


def build_track(
    track: str,
    *,
    rows: list[results.Row] | None = None,
    samples: int = SAMPLES,
    cache_root: Path | None = None,
    docs_dir: Path | None = None,
) -> dict | None:
    """The artefact for one track, or None when fewer than two judges scored it."""
    from tnb import report

    current = report.current_rows(rows if rows is not None else results.load())
    by_judge = published(current, track)
    if len(by_judge) < 2:
        return None
    per_session = {
        judge_model: LOADERS[track](judge_model, cache_root=cache_root) for judge_model in by_judge
    }
    found = examine(track, report.COLUMNS[track], by_judge, per_session, samples=samples)
    found["built"] = dt.date.today().isoformat()
    found["tables"] = {
        row.judge_model: {name: getattr(row, name) for name in results.COMPARABILITY_KEYS}
        for row in current
        if row.track == track and row.is_scored and row.judge_model in by_judge
    }
    if track == results.TRACK_TNEVAL:
        # The audit's one-leg check beside the whole-edge one: the fraction of
        # the band analysis's own resamples in which the winner led on
        # completeness alone, over the conversations every system shares.
        beats = {
            found_sat["judge_model"]: found_sat.get("beats") or {}
            for found_sat in report.load_saturations(docs_dir)
        }
        for edge in found["edges"] + found["untestable"]:
            one_leg = {
                judge_model: table[edge["winner"]][edge["loser"]]
                for judge_model, table in beats.items()
                if edge["loser"] in table.get(edge["winner"], {})
            }
            if one_leg:
                edge["one_leg_completeness"] = one_leg
    return found


def write(track: str, found: dict, docs_dir: Path | None = None) -> Path:
    path = artefact_path(track, docs_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(found, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
