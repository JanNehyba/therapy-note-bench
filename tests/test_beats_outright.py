"""The ordering column that answers less than a mean and invents nothing.

A leaderboard wants one number to sort by, and the obvious one is a mean of the
columns. This project cannot have it, and the reason is measurable rather than
philosophical: the rubric's three columns do not predict each other, so the
ordering a mean produces is decided by the weights, and nobody has measured the
weights. Fitting them needs a human saying which note they would sign, and
TN-Eval's annotators rated three dimensions separately and were never asked.

So the table is ordered, where it can be, by the models beating each other.
**A system beats another outright when it is at least as good on every column
of one instrument under both judges, and strictly better somewhere.** That is
the project's only surviving definition of "better", and the tests below pin
the two properties it rests on:

* it is exactly the part of the ordering every weighting agrees on, and
* removing an unrelated system cannot reverse it.

Neither holds for a mean. Measured on the published rows: a mean reverses 20
pairs when the therapist's row is removed, and every one of the 141 pairs it
orders by weight can be made to go either way by choosing the weights.

Compared on the **stored** figures, not the printed ones, and the direction is
the reason. Dominance asks for "at least as good everywhere", so rounding a
narrow *loss* into a tie removes an obstacle: it lets a claim through rather
than holding one back. It fired once on the published rows --
`gemini-3.1-pro-preview` beat `glm-5.2` outright on a 0.0029 faithfulness gap
in `glm-5.2`'s favour that printed as 4.97 against 4.97 -- and the
verifiability the printed comparison was chosen for failed exactly there: a
reader sees two equal figures, concludes a tie, and is told otherwise. The
change costs one claim of thirty on the rubric and none of eleven on PDSQI-9,
and leaves `undominated` identical, so no published sentence moves.
"""

from __future__ import annotations

import itertools
import json
import random

import pytest

from tnb.config import REPO_ROOT

DOCS = REPO_ROOT / "docs"
JUDGES = ("gemini-3.1-pro-preview", "gpt-5.6-terra")


@pytest.fixture(scope="module")
def payload() -> dict:
    return json.loads((DOCS / "leaderboard.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def tracks(payload) -> list[str]:
    return sorted(payload.get("concordance") or {})


def test_the_compared_population_is_published(tracks, payload):
    """Without it the page cannot tell "beats nobody" from "not comparable".

    `_dominates` refuses a comparison where either system is missing a measure
    under either judge, so a system outside the population has no count at all.
    Printing 0 for it would be an absence reported as a measurement, which is
    the oldest rule in this repository.
    """
    for track in tracks:
        found = payload["concordance"][track]
        assert isinstance(found.get("systems"), list), f"{track} publishes no population"
        assert len(found["systems"]) == found["n_systems"], (
            f"{track}: systems lists {len(found['systems'])} where n_systems says "
            f"{found['n_systems']}"
        )


def test_the_population_is_the_dominance_graph_it_was_read_from(tracks, payload):
    """Everyone is either beaten by somebody or in `undominated`, and no one else."""
    for track in tracks:
        found = payload["concordance"][track]
        reconstructed = set(found["undominated"])
        for entry in found.get("dominance") or []:
            reconstructed.update(entry["beats"])
        assert reconstructed == set(found["systems"]), (
            f"{track}: the published population and the dominance graph disagree; "
            f"only in one: {sorted(reconstructed ^ set(found['systems']))}"
        )


def test_the_column_is_not_a_measure(tracks, payload):
    """It must stay out of `columns`, or everything that iterates them takes it.

    The correlation grid, the legend, the per-section detail and the ranking
    switch all walk `table.columns`. A count of comparisons landing in there
    would be correlated against a 1-5 rating and averaged into a section.
    """
    for table in payload["tables"]:
        keys = {column["key"] for column in table["columns"]}
        assert not {key for key in keys if key.startswith("beats")}, (
            f"{table['track']}: a beats column is in `columns`, where it will be "
            "read as something a judge said about a note"
        )


def test_the_count_is_the_same_under_either_judge(tracks, payload):
    """Both judges are already inside the definition, so the switch cannot move it.

    Worth pinning because a reader who flips the judge and sees this column
    stand still will otherwise think it is broken -- and because a future edit
    that computed it per judge would silently halve the claim.
    """
    for track in tracks:
        found = payload["concordance"][track]
        assert found["judge_a"] in JUDGES and found["judge_b"] in JUDGES, (
            f"{track} was compared over {found['judge_a']} and {found['judge_b']}, "
            "which are not the two published judges"
        )


def _printed(payload, track: str):
    """The figures as the table prints them, per system, per judge, per measure."""
    tables = {
        table["versions"]["judge_model"]: table
        for table in payload["tables"]
        if table["scored"] and table["versions"].get("judge_model") in JUDGES
    }
    source = "tneval-soap" if track in ("tneval-soap", "pdsqi-soap") else track
    tables = {judge: table for judge, table in tables.items() if table["track"] == source}
    if len(tables) != 2:
        return None, None

    rubric = ("completeness", "conciseness", "faithfulness")
    digits = {column["key"]: column["digits"] for column in next(iter(tables.values()))["columns"]}
    if track == "tneval-soap":
        measures = [m for m in rubric if m in digits]
    elif track == "pdsqi-soap":
        measures = [m for m in digits if m not in rubric]
    else:
        measures = list(digits)

    scores: dict[str, dict[str, dict[str, float]]] = {}
    for judge, table in tables.items():
        for row in table["rows"]:
            head = row["headline"] or {}
            if all(head.get(m) is not None for m in measures):
                scores.setdefault(row["label"], {})[judge] = {
                    m: round(head[m], digits[m]) for m in measures
                }
    return {s: v for s, v in scores.items() if len(v) == 2}, measures


def test_no_weighting_reverses_a_system_that_beats_another_outright(tracks, payload):
    """The property the whole column rests on, checked rather than argued.

    If A is at least as good on every column, A's weighted mean is at least B's
    for every choice of non-negative weights -- so the claim survives whatever
    a reader believes a point of one column is worth in another. The converse
    is checked too: where neither beats the other, some weighting puts each one
    ahead, which is why the column is silent there instead of guessing.
    """
    random.seed(20260901)
    for track in tracks:
        scores, measures = _printed(payload, track)
        if not scores or len(scores) < 3:
            continue
        systems = sorted(scores)
        axes = [(judge, m) for judge in JUDGES for m in measures]
        span = {}
        for axis in axes:
            values = [scores[s][axis[0]][axis[1]] for s in systems]
            span[axis] = (min(values), (max(values) - min(values)) or 1.0)
        unit = {
            s: {a: (scores[s][a[0]][a[1]] - span[a][0]) / span[a][1] for a in axes} for s in systems
        }
        draws = [{a: random.random() for a in axes} for _ in range(300)]
        draws += [{a: (1.0 if a == axis else 0.0) for a in axes} for axis in axes]

        beats = {d["system"]: set(d["beats"]) for d in payload["concordance"][track]["dominance"]}

        def ahead(first, second, weights, unit=unit, axes=axes):
            return sum(weights[a] * unit[first][a] for a in axes) > sum(
                weights[a] * unit[second][a] for a in axes
            )

        for a, b in itertools.combinations(systems, 2):
            if b in beats.get(a, set()):
                winner, loser = a, b
            elif a in beats.get(b, set()):
                winner, loser = b, a
            else:
                continue
            assert not [w for w in draws if ahead(loser, winner, w)], (
                f"{track}: {winner} beats {loser} outright, yet a weighting puts the "
                "loser ahead -- the column's central claim does not hold"
            )


def test_removing_a_system_cannot_reverse_the_order_of_two_others(tracks, payload):
    """The property a mean does not have, and the reason this column can be sorted.

    Dropping one row lowers each count by at most one, so a strict lead can
    shrink to a tie and can never invert. The same test on a mean of the same
    columns reverses twenty pairs when the therapist's row is removed, because
    min-max normalisation is relative to whoever is in the table.
    """
    for track in tracks:
        found = payload["concordance"][track]
        systems = sorted(found["systems"])
        beats = {d["system"]: set(d["beats"]) for d in found.get("dominance") or []}
        if len(systems) < 3:
            continue
        for dropped in systems:
            keep = set(systems) - {dropped}
            after = {s: len(beats.get(s, set()) & keep) for s in keep}
            before = {s: len(beats.get(s, set())) for s in keep}
            for a, b in itertools.combinations(sorted(keep), 2):
                was = (before[a] > before[b]) - (before[a] < before[b])
                now = (after[a] > after[b]) - (after[a] < after[b])
                assert not (was and now and was != now), (
                    f"{track}: removing {dropped} reversed {a} against {b} "
                    f"({before[a]}:{before[b]} became {after[a]}:{after[b]})"
                )


def test_rounding_cannot_manufacture_a_claim():
    """The direction that matters: a tie made by rounding lets dominance through.

    Two systems, one measure where B is ahead by less than the printed
    precision and one where A is ahead by a lot. On the stored figures A does
    not beat B, because it is not at least as good everywhere. Rounding the
    first to two places would make it a tie, remove the obstacle, and publish a
    claim the numbers do not support -- which is what happened, once, on the
    real rows.
    """
    from tnb.scoring.concordance import _dominates

    by_judge = {
        "judge-a": {
            "A": {"faithfulness": 4.9716, "completeness": 0.900},
            "B": {"faithfulness": 4.9745, "completeness": 0.500},
        },
        "judge-b": {
            "A": {"faithfulness": 4.5000, "completeness": 0.900},
            "B": {"faithfulness": 4.5000, "completeness": 0.500},
        },
    }
    decimals = {"faithfulness": 2, "completeness": 3}
    assert not _dominates("A", "B", by_judge, decimals), (
        "A is 0.0029 behind on faithfulness and dominance was granted anyway, so "
        "the comparison is rounding again"
    )
    # With that one gap removed it does dominate, so the test is about the gap
    # and not about something else in the fixture.
    by_judge["judge-a"]["B"]["faithfulness"] = 4.9716
    assert _dominates("A", "B", by_judge, decimals)


def test_the_page_draws_the_column_and_can_sort_by_it():
    """The template, not the rendered page: the table is built in the browser."""
    template = (REPO_ROOT / "src" / "tnb" / "templates" / "leaderboard.html").read_text(
        encoding="utf-8"
    )
    for needed in ("function dominanceOf", "beats:${track}", "beatsCells", "beatsLegend"):
        assert needed in template, f"the beats column lost {needed!r}"
    assert "found.systems.has(row.label)" in template, (
        "the cell no longer distinguishes a system outside the compared "
        "population from one that beats nobody"
    )
