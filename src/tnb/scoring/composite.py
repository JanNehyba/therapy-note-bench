"""One order per table: the mean of a system's places over the instrument's columns.

A leaderboard wants one order, and for a year this one refused to give one
beyond a single column, because the columns do not predict each other and a
mean of their values is decided by weights nobody has measured. The refusal
was right about values and wrong about the reader: a table with no order is
read by the first column anyway. So the order is made explicit, in the mildest
form that exists, and everything the choice does is published beside it.

**Mean place.** On each column of the instrument every system is placed 1st,
2nd, ... best first, at the precision the table prints -- two rows that print
the same figure share a place, as they do in `concordance._positions`, because
a reader checks a place against the digits in front of them. The places are
averaged with every column counting once, and the systems are ordered by that
mean, competition-style (1, 2, 2, 4): a tie on the mean is a tie.

Why places and not values, measured on the published tables on 2026-09-02:
places agree with a mean win rate at Spearman 0.98 to 1.00 -- the same order
by a longer route -- while a min-max mean of the values reverses 21 pairs of
models on one table when the three non-model rows are removed, because it is
rescaled by whoever sits at the extremes. Places have no unit, so a 0-1
fraction and a 1-5 rating weigh the same, and removing a row moves every
place below it by one and nothing else.

What the rule embeds, and what it does not. It embeds one convention: every
column of the instrument counts once and equally. It does not embed a claim
that two adjacent places differ -- the two judges still order most systems
differently, the tested dominance graph (`edges.py`) still separates one to
four systems from the rest, and both are drawn beside the order. And it does
not embed a weighting: `sensitivity` recomputes the order with each column
counted twice and with the reference rows removed, and the page prints who is
first under every variant, so a reader who weights differently can see at
once whether it would matter.

Nothing here is a measure. A place is a statement about a table, not about a
note, and it never enters `headline`, a mean over notes, or a comparison
between judges.
"""

from __future__ import annotations

from collections.abc import Sequence

from tnb.scoring import calibration, concordance

#: The one rule this module knows, named in the payload so the page can say it.
RULE = "mean_place"

Scores = dict[str, dict[str, float]]


def places_by_column(
    scores: Scores, columns: Sequence[tuple[str, int]]
) -> dict[str, dict[str, int]]:
    """{column: {system: place}}, 1-based, best first, printed ties sharing a place.

    Over the systems that have the column; a system without it simply has no
    place there, which `order` then reports rather than filling in.
    """
    systems = sorted(scores)
    return {
        column: concordance.positions(scores, column, systems, decimals)
        for column, decimals in columns
    }


def mean_places(
    scores: Scores,
    columns: Sequence[tuple[str, int]],
    *,
    weights: dict[str, float] | None = None,
) -> tuple[dict[str, dict], dict[str, list[str]]]:
    """Each system's places and their (weighted) mean, and who could not be placed.

    Returns ``(placed, unplaced)``: ``placed[system]`` is ``{"places": {column:
    place}, "mean_place": float}``, and ``unplaced[system]`` names the columns a
    system lacks. A system missing any column gets no mean at all -- a mean over
    fewer columns is a different quantity, and filling the gap with a worst or
    a middle place would be a measurement nobody made.
    """
    by_column = places_by_column(scores, columns)
    names = [column for column, _ in columns]
    weights = weights or {}
    total = sum(weights.get(column, 1.0) for column in names)
    placed: dict[str, dict] = {}
    unplaced: dict[str, list[str]] = {}
    for system in sorted(scores):
        missing = [column for column in names if system not in by_column[column]]
        if missing:
            unplaced[system] = missing
            continue
        places = {column: by_column[column][system] for column in names}
        placed[system] = {
            "places": places,
            "mean_place": sum(weights.get(c, 1.0) * p for c, p in places.items()) / total,
        }
    return placed, unplaced


def competition_places(mean_place: dict[str, float]) -> dict[str, int]:
    """1-based place on the mean, smallest first; exact ties share the better place (1, 2, 2, 4)."""
    ordered = sorted(mean_place, key=lambda system: (mean_place[system], system))
    places: dict[str, int] = {}
    for index, system in enumerate(ordered):
        if index and mean_place[system] == mean_place[ordered[index - 1]]:
            places[system] = places[ordered[index - 1]]
        else:
            places[system] = index + 1
    return places


def order(
    scores: Scores,
    columns: Sequence[tuple[str, int]],
    *,
    weights: dict[str, float] | None = None,
) -> dict:
    """The order of one table.

    ``{"rule", "columns", "systems": {system: {"place", "mean_place", "places"}},
    "unplaced": {system: [missing columns]}}`` -- ``mean_place`` rounded to two
    decimals for printing, the place computed on the exact value.
    """
    placed, unplaced = mean_places(scores, columns, weights=weights)
    places = competition_places({system: found["mean_place"] for system, found in placed.items()})
    return {
        "rule": RULE,
        "columns": [column for column, _ in columns],
        "systems": {
            system: {
                "place": places[system],
                "mean_place": round(found["mean_place"], 2),
                "places": found["places"],
            }
            for system, found in placed.items()
        },
        "unplaced": unplaced,
    }


def _at(found: dict, place: int) -> list[str]:
    return sorted(system for system, entry in found["systems"].items() if entry["place"] == place)


def _reversed_pairs(before: dict, after: dict) -> int:
    """Pairs of systems, placed in both, whose strict order differs."""
    shared = sorted(set(before["systems"]) & set(after["systems"]))
    flips = 0
    for index, first in enumerate(shared):
        for second in shared[index + 1 :]:
            was = before["systems"][first]["place"] - before["systems"][second]["place"]
            now = after["systems"][first]["place"] - after["systems"][second]["place"]
            if was * now < 0:
                flips += 1
    return flips


def _rho(before: dict, after: dict) -> float | None:
    shared = sorted(set(before["systems"]) & set(after["systems"]))
    if len(shared) < 3:
        return None
    rho = calibration.spearman(
        [before["systems"][s]["mean_place"] for s in shared],
        [after["systems"][s]["mean_place"] for s in shared],
    )
    return None if rho is None else round(rho, 3)


def sensitivity(
    scores: Scores,
    columns: Sequence[tuple[str, int]],
    *,
    reference: Sequence[str] = (),
) -> dict:
    """What the order does under the weightings a reader might prefer.

    One variant per column with that column counted twice, and one with the
    reference rows -- the therapist, the released reference models -- taken
    out, which is the variant that broke the min-max mean. Each variant reports
    who is first and second, how many systems changed place, the furthest any
    moved, and Spearman against the equal-weight order. ``first_under_any`` is
    the set the page prints: the systems that lead under at least one variant.
    """
    baseline = order(scores, columns)
    variants: list[dict] = []
    for column, _ in columns:
        variant = order(scores, columns, weights={column: 2.0})
        moved = [
            system
            for system in baseline["systems"]
            if variant["systems"][system]["place"] != baseline["systems"][system]["place"]
        ]
        furthest = max(
            (
                abs(variant["systems"][s]["place"] - baseline["systems"][s]["place"])
                for s in baseline["systems"]
            ),
            default=0,
        )
        variants.append(
            {
                "name": f"double:{column}",
                "column": column,
                "first": _at(variant, 1),
                "second": _at(variant, 2),
                "moved": len(moved),
                "furthest": furthest,
                "rho": _rho(baseline, variant),
            }
        )
    dropped = sorted(system for system in reference if system in scores)
    if dropped and len(scores) - len(dropped) >= 2:
        remaining = {system: values for system, values in scores.items() if system not in dropped}
        variant = order(remaining, columns)
        variants.append(
            {
                "name": "models_only",
                "dropped": dropped,
                "first": _at(variant, 1),
                "second": _at(variant, 2),
                "reversed_pairs": _reversed_pairs(baseline, variant),
                "rho": _rho(baseline, variant),
            }
        )
    first_under_any = sorted(set(_at(baseline, 1)).union(*(set(v["first"]) for v in variants)))
    return {
        "baseline": {"first": _at(baseline, 1), "second": _at(baseline, 2)},
        "variants": variants,
        "first_under_any": first_under_any,
        "most_moved": max((v.get("moved", 0) for v in variants), default=0),
        "furthest": max((v.get("furthest", 0) for v in variants), default=0),
        "n_systems": len(baseline["systems"]),
    }
