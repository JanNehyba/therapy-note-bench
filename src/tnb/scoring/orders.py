"""The six published orders, read against each other.

Each table on the leaderboard publishes one order: the mean of a system's
places over its instrument's columns. `composite` builds one of those. This
module holds all six at once and asks the question no single table can answer
-- *which model*, put to all three instruments together.

The answer is that there is no single order to publish, and the artefact says
why rather than inventing one:

- **The judge is close to interchangeable and the instrument is not.** Two
  judges of one instrument order the models at Spearman +0.82 to +0.95; two
  instruments under one judge reach as low as -0.28. The rubric and PDSQI-9
  score *the same notes* and still agree only +0.04 to +0.36, so it is not the
  corpora that differ, it is the questions.
- **Pooled over all three instruments, dominance separates nobody.** Not one
  ordered pair of the eighteen models is at least as good on every column of
  every instrument under both judges. That is partly mechanical -- more legs
  make dominance harder whatever the models do -- so the same count is taken
  per instrument as the control, and the artefact carries all four.
- **And the disagreement is not the instruments measuring different things.**
  Between individual columns, where no ordering convention is involved at all,
  columns of *different* instruments predict each other about as well as
  columns of the same one. Whatever separates the six orders happens in the
  averaging of places, not in the measurements. That is recorded here because
  it is unexplained, and because without it a reader would take the six
  disagreeing orders for a finding about the instruments.

What this module deliberately does not do is combine anything. There is no
mean, median, Borda count or sum of the six ranks in the artefact: a total over
the three instruments would have to say what a SOAP rubric is worth against a
17-field form, which is a clinical judgement and not something these numbers
can be asked for.

**Ranks are recomputed among the models alone**, which is not the same as the
`place` each table prints. Those count the reference rows, and the reference
rows interleave: `mistral-large-v2` sits ninth on one SOAP table, above nine
models, and the iCARE tables have no reference row at all. A place among all
rows therefore means a different thing on each table. The recomputation is
`composite.order` over the models -- the `models_only` variant the tables
already publish under their sensitivity -- so no new ordering rule is invented
here.

Nothing in the artefact is prose. Every sentence the page draws is written in
the template, so a wording can be fixed by editing the page rather than by
re-running a command, and a data file cannot carry text nobody proof-reads.
"""

from __future__ import annotations

import datetime as dt
import itertools
import json
import statistics
from collections.abc import Sequence
from pathlib import Path

from tnb.scoring import calibration, composite, concordance

#: The committed artefact. `profile.json` was rejected: `corpus-profile.json`
#: already exists and is about the corpora. *Order* is this repository's own
#: word -- `composite` produces one per table, and this holds six.
ARTEFACT_NAME = "orders.json"

#: Fewer than this and a rank correlation is not a statistic. `calibration.
#: spearman` already returns None below three; this refuses the whole artefact,
#: because a profile of two models is a comparison, not a profile.
MIN_SYSTEMS = 3

#: Rounded once, at three decimals, which is what every surface draws. Stored
#: deeper, the page rounds a second time and prints a different figure from the
#: sentence beside it -- the fault fixed in the concordance payload on
#: 2026-09-03, arriving here by the same road.
DECIMALS = 3


def artefact_path(docs_dir: Path | None = None) -> Path:
    """Where the artefact lives. Same shape as `edges.artefact_path`."""
    from tnb import report

    return (docs_dir or report.DOCS_DIR) / ARTEFACT_NAME


def load(docs_dir: Path | None = None) -> dict | None:
    """The committed artefact, or None when none has been built."""
    path = artefact_path(docs_dir)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write(found: dict, docs_dir: Path | None = None) -> Path:
    """Publish the artefact whole or not at all."""
    from tnb.config import write_published

    path = artefact_path(docs_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_published(path, json.dumps(found, indent=2, sort_keys=True) + "\n")
    return path


def _models(table: dict) -> list[dict]:
    """The rows a profile may cover.

    `system_type != "model"` is the rule `report._placed` already passes to
    `composite.sensitivity` as its `reference`, so the two cannot drift into
    different ideas of what a model is.
    """
    return [row for row in table["rows"] if row["system_type"] == "model"]


def _kind(a: dict, b: dict) -> str:
    """What a pair of tables has in common, which is what the bands group on."""
    if a["track"] == b["track"]:
        return "same_instrument"
    return "/".join(sorted((a["track"], b["track"])))


def _order_of(table: dict, systems: Sequence[str]) -> dict[str, dict]:
    """One table's order over the given systems, by the rule the page uses."""
    scores = {
        row["system_id"]: dict(row["headline"])
        for row in _models(table)
        if row["system_id"] in systems
    }
    return composite.order(scores, [(c["key"], c["digits"]) for c in table["columns"]])["systems"]


def _correlations(placed: dict[str, dict[str, int]], scored: list[dict], systems: list[str]):
    """Spearman between every pair of the tables, on the places they draw.

    On `place` and not on `mean_place`: the profile prints places, and a
    correlation between two columns of numbers a reader can see is one they can
    check. Ties are shared places, which is what `calibration.spearman` handles
    with average ranks.
    """
    for a, b in itertools.combinations(scored, 2):
        rho = calibration.spearman(
            [placed[a["id"]][s] for s in systems], [placed[b["id"]][s] for s in systems]
        )
        yield a, b, rho


def _bands(pairs: list[dict]) -> list[dict]:
    """The pairs grouped by what they compare, with the range each covers."""
    grouped: dict[str, list[float]] = {}
    for pair in pairs:
        if pair["rho"] is not None:
            grouped.setdefault(pair["kind"], []).append(pair["rho"])
    return [
        {
            "kind": kind,
            "pairs": len(values),
            "low": round(min(values), DECIMALS),
            "high": round(max(values), DECIMALS),
        }
        for kind, values in sorted(grouped.items())
    ]


def _jackknife(scored: list[dict], systems: list[str]) -> dict:
    """Every band's range again, with each system left out in turn.

    The sensitivity this artefact carries, and the only one: it answers "does
    this depend on one model", which is the question a reader of eighteen rows
    asks. It does **not** answer "is this correlation distinguishable from
    zero" -- nothing here resamples the conversations the scores came from, and
    the page says so rather than leaving the gap for a reader to assume closed.

    Deterministic, and computed from the published rows alone: no cache, no
    seed, no draw count to argue about.
    """
    spread: dict[str, list[float]] = {}
    for dropped in systems:
        kept = [s for s in systems if s != dropped]
        if len(kept) < MIN_SYSTEMS:
            continue
        placed = {t["id"]: {s: v["place"] for s, v in _order_of(t, kept).items()} for t in scored}
        for a, b, rho in _correlations(placed, scored, kept):
            if rho is not None:
                spread.setdefault(_kind(a, b), []).append(rho)
    return {
        "rule": "leave_one_system_out",
        "refits": len(systems),
        "bands": [
            {
                "kind": kind,
                "low": round(min(values), DECIMALS),
                "high": round(max(values), DECIMALS),
            }
            for kind, values in sorted(spread.items())
        ],
    }


def _pooled(scored: list[dict], systems: list[str], tracks: Sequence[str] | None = None) -> dict:
    """How many ordered pairs one system beats another outright.

    `concordance._dominates` unchanged, over every column of every table in
    scope under both judges. Restricted to one instrument it is the control the
    pooled figure needs: three instruments make 32 legs where one makes 6, and
    more legs make dominance harder whatever the models do.
    """
    in_scope = [t for t in scored if tracks is None or t["track"] in tracks]
    by_judge: dict[str, dict[str, dict[str, float]]] = {}
    decimals: dict[str, int] = {}
    owner: dict[str, str] = {}
    legs = 0
    for table in in_scope:
        judge = table["versions"]["judge_model"]
        for column in table["columns"]:
            key = column["key"]
            if owner.setdefault(key, table["track"]) != table["track"]:
                raise ValueError(
                    f"column {key!r} is used by both {owner[key]!r} and {table['track']!r}; "
                    "pooling them would silently compare two different measures"
                )
            decimals[key] = column["digits"]
            legs += 1
        for row in _models(table):
            if row["system_id"] not in systems:
                continue
            held = by_judge.setdefault(judge, {}).setdefault(row["system_id"], {})
            held.update({c["key"]: row["headline"][c["key"]] for c in table["columns"]})
    dominating = sum(
        1
        for winner, loser in itertools.permutations(systems, 2)
        if concordance._dominates(winner, loser, by_judge, decimals)
    )
    return {
        "legs": legs,
        "judges": len(by_judge),
        "systems": len(systems),
        "pairs": len(systems) * (len(systems) - 1),
        "dominating": dominating,
    }


def _median(values: list[float]) -> dict:
    """A group of correlations, as a count and a middle. Absent, not zero, when
    the group is empty: no pair measured is not a correlation of nothing."""
    return {
        "pairs": len(values),
        "median_abs_rho": round(statistics.median(values), DECIMALS) if values else None,
    }


def _column_pairs(scored: list[dict], systems: list[str]) -> list[dict]:
    """Whether columns of different instruments predict each other.

    The counter-finding, and the reason the page may not say the three
    instruments measure different things. Between individual columns no
    ordering convention is involved, so this asks the question the six orders
    cannot: do the *measurements* disagree, or only the averages of their
    places?

    A column on which half or more of the systems print the same figure is left
    out, by `concordance.Tension.rankable`'s rule and for its reason: a measure
    that cannot tell the systems apart cannot be correlated with one that can.
    """
    found = []
    for judge in sorted({t["versions"]["judge_model"] for t in scored}):
        series: dict[tuple[str, str], list[float]] = {}
        for table in (t for t in scored if t["versions"]["judge_model"] == judge):
            values = {r["system_id"]: r["headline"] for r in _models(table)}
            for column in table["columns"]:
                key, digits = column["key"], column["digits"]
                if any(values[s].get(key) is None for s in systems):
                    continue
                printed = [concordance.as_printed(values[s][key], digits) for s in systems]
                tied = max(printed.count(one) for one in set(printed))
                if tied * 2 > len(systems):
                    continue
                series[(table["track"], key)] = [values[s][key] for s in systems]
        within, across = [], []
        for (track_a, key_a), (track_b, key_b) in itertools.combinations(series, 2):
            rho = calibration.spearman(series[(track_a, key_a)], series[(track_b, key_b)])
            if rho is None:
                continue
            (within if track_a == track_b else across).append(abs(rho))
        found.append(
            {
                "judge_model": judge,
                "columns": len(series),
                "within_instrument": _median(within),
                "across_instruments": _median(across),
            }
        )
    return found


def _undominated(scored: list[dict], systems: list[str]) -> tuple[dict[str, int], list[str]]:
    """In how many instruments no tested comparison beats this system.

    Counted per **instrument**, not per table. `docs/edges-<track>.json` tests
    every leg under both judges at once and the same layer is drawn on both of
    that track's tables, so counting it twice would count one test twice. The
    denominator is three where all three tracks have a tested artefact.
    """
    tested = sorted({t["track"] for t in scored if "groups_tested" in t})
    top: dict[str, int] = dict.fromkeys(systems, 0)
    for track in tested:
        table = next(t for t in scored if t["track"] == track and "groups_tested" in t)
        for row in _models(table):
            if row["system_id"] in top and row.get("group") == 1:
                top[row["system_id"]] += 1
    return top, tested


def _reference(scored: list[dict]) -> dict:
    """The rows a profile leaves out, and where they are.

    Not an omission to be inferred from a shorter table: the therapist's own
    note and the two systems TN-Eval published are drawn in the tables that
    have them, scored by the identical protocol. They are left out here because
    the iCARE tables have no such row at all, so a place among all rows would
    be a place among a different population on each instrument. The page says
    that in a sentence, and takes every figure in it from this block.
    """
    where: dict[str, dict] = {}
    for table in scored:
        for row in table["rows"]:
            if row["system_type"] == "model":
                continue
            held = where.setdefault(
                row["system_id"],
                {"system_id": row["system_id"], "label": row["label"], "tables": []},
            )
            held["tables"].append(table["id"])
    for held in where.values():
        held["tables"].sort()
    with_any = {table for held in where.values() for table in held["tables"]}
    return {
        "systems": [where[key] for key in sorted(where)],
        "in_tables": len(with_any),
        "of_tables": len(scored),
    }


def examine(tables: list[dict]) -> dict | None:
    """The six orders read against each other, from the payload's own tables.

    Pure: it takes what `report.build` already produced and imports nothing
    from `report`, so two toy tables are enough to test every branch.
    """
    scored = sorted(
        (t for t in tables if t.get("scored")),
        key=lambda t: (t["track"], t["versions"]["judge_model"]),
    )
    if len(scored) < 2:
        return None

    held = {t["id"]: {r["system_id"] for r in _models(t)} for t in scored}
    population = sorted(set.intersection(*held.values()))
    if len(population) < MIN_SYSTEMS:
        return None
    # Named, never counted. A system missing from one table has no place to
    # compare, and dropping it silently would make the profile a different
    # population from the one its heading claims.
    outside = [
        {
            "system_id": system,
            "missing": sorted(i for i, have in held.items() if system not in have),
        }
        for system in sorted(set().union(*held.values()) - set(population))
    ]

    orders, placed = [], {}
    for table in scored:
        found = _order_of(table, population)
        ranks = {s: v["place"] for s, v in found.items()}
        placed[table["id"]] = ranks
        published = {r["system_id"]: r.get("place") for r in _models(table)}
        orders.append(
            {
                "table": table["id"],
                "track": table["track"],
                "judge_model": table["versions"]["judge_model"],
                "versions": dict(table["versions"]),
                "systems": sorted(population),
                "ranks": ranks,
                "mean_places": {s: v["mean_place"] for s, v in found.items()},
                # The models whose rank here is not the Place their table
                # prints. Not a fault in either: the two count different
                # populations, and the page says so where both appear.
                "differs_from_place": sorted(
                    s for s in population if published.get(s) != ranks.get(s)
                ),
            }
        )

    pairs = [
        {
            "a": a["id"],
            "b": b["id"],
            "kind": _kind(a, b),
            "same_judge": a["versions"]["judge_model"] == b["versions"]["judge_model"],
            "rho": None if rho is None else round(rho, DECIMALS),
        }
        for a, b, rho in _correlations(placed, scored, population)
    ]
    top, tested = _undominated(scored, population)
    tracks = sorted({t["track"] for t in scored})

    return {
        "rule": composite.RULE,
        "population": population,
        "outside": outside,
        "orders": orders,
        "agreement": pairs,
        "bands": _bands(pairs),
        "jackknife": _jackknife(scored, population),
        "dominance": {
            "pooled": _pooled(scored, population),
            "per_instrument": {track: _pooled(scored, population, [track]) for track in tracks},
        },
        "columns": _column_pairs(scored, population),
        "undominated": top,
        "reference": _reference(scored),
        "tables": len(scored),
        "instruments": len(tracks),
        "instruments_tested": tested,
    }


def build(rows: list | None = None) -> dict | None:
    """The artefact for the tables the page is drawing right now."""
    from tnb import report, results

    data = report.build(rows if rows is not None else results.load())
    found = examine(data["tables"])
    if found is not None:
        found["built"] = dt.date.today().isoformat()
    return found


def matches(found: dict | None, tables: list[dict]) -> bool:
    """Whether the artefact still describes the tables being drawn.

    Recomputed and compared, not trusted. `edges.load` keys on the track alone
    and never reads its own record of what it was built from, so an artefact
    computed from a different set of rows is drawn beside fresh tables with
    nothing saying so. That gap is affordable there only because rebuilding
    costs a cache read and ten thousand draws. This is pure arithmetic over the
    published rows, so there is no excuse for a stale profile, and none is made.
    """
    if not found:
        return False
    fresh = examine(tables)
    if fresh is None:
        return False
    for name in ("population", "outside", "orders", "agreement", "bands", "undominated"):
        if found.get(name) != fresh[name]:
            return False
    return True
