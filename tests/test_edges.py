"""Which "beats outright" claims survive resampling -- pinned on constructed cases.

Offline. The arithmetic is checked where the right answer is known in advance;
the committed artefacts are checked against the published table they were read
from, which is the only check that needs no answer cache.
"""

from __future__ import annotations

import json

import pytest

from tnb.config import REPO_ROOT
from tnb.scoring import edges
from tnb.scoring.concordance import _dominates

COLUMNS = (("x", 3), ("y", 2))
JUDGES = ("judge-a", "judge-b")


def _sessions(values: list[float]) -> dict[str, float]:
    return {str(index): value for index, value in enumerate(values)}


def _per_session(spec: dict[str, dict[str, list[float]]]) -> edges.PerSession:
    """The same per-conversation values under both judges."""
    return {
        judge: {
            system: {column: _sessions(values) for column, values in columns.items()}
            for system, columns in spec.items()
        }
        for judge in JUDGES
    }


def _means(spec: dict[str, dict[str, list[float]]]) -> dict:
    return {
        judge: {
            system: {column: sum(values) / len(values) for column, values in columns.items()}
            for system, columns in spec.items()
        }
        for judge in JUDGES
    }


def _examine(spec, samples=400, **overrides):
    return edges.examine(
        "t", COLUMNS, _means(spec), _per_session(spec), samples=samples, **overrides
    )


def test_a_wide_consistent_lead_holds_and_orders_the_layers():
    spec = {
        "top": {"x": [0.9] * 30, "y": [4.0] * 30},
        "bottom": {"x": [0.2] * 30, "y": [2.0] * 30},
    }
    found = _examine(spec)

    (edge,) = found["edges"]
    assert (edge["winner"], edge["loser"], edge["holds"], edge["p_holds"]) == (
        "top",
        "bottom",
        True,
        1.0,
    )
    assert found["layers"] == [["top"], ["bottom"]]
    assert found["undominated"] == ["top"]
    assert found["counts"] == {
        "stored": 1,
        "tested": 1,
        "untestable": 0,
        "holds": {"0.90": 1, "0.95": 1, "0.99": 1},
    }


def test_a_thin_inconsistent_lead_does_not_hold():
    """The stored means say A beats B outright; the conversations do not.

    A is ahead by five hundredths on odd conversations and behind by almost as
    much on even ones. The means differ by a thousandth in A's favour, so the
    dominance test on stored values passes, and about half the resamples put B
    ahead -- which is the claim the leaderboard drew for a day.
    """
    base = [0.5 + (index % 5) * 0.02 for index in range(47)]
    a_x = [value + (-0.049 if index % 2 else 0.05) for index, value in enumerate(base)]
    spec = {"a": {"x": a_x, "y": [3.0] * 47}, "b": {"x": base, "y": [3.0] * 47}}
    means = _means(spec)
    assert _dominates("a", "b", means, dict(COLUMNS)), "the fixture must dominate on the means"

    found = _examine(spec, samples=1000)

    (edge,) = found["edges"]
    assert edge["holds"] is False and 0.3 < edge["p_holds"] < 0.8, edge["p_holds"]
    assert edge["thinnest"]["column"] == "x"
    assert found["layers"] == [["a", "b"]], "an edge that does not hold separates nobody"
    assert found["counts"]["holds"] == {"0.90": 0, "0.95": 0, "0.99": 0}


def test_a_tiny_but_consistent_lead_holds():
    """What pairing buys: a lead on every conversation survives however small it
    is, because no resample can reverse it. Consistency is the evidence."""
    base = [0.5 + (index % 5) * 0.02 for index in range(40)]
    spec = {
        "a": {"x": [value + 0.001 for value in base], "y": [3.0] * 40},
        "b": {"x": base, "y": [3.0] * 40},
    }
    found = _examine(spec)

    (edge,) = found["edges"]
    assert edge["holds"] is True and edge["p_holds"] == 1.0
    tie = next(leg for leg in edge["legs"] if leg["column"] == "y")
    assert tie["p_ahead"] == 0.0 and tie["p_not_behind"] == 1.0, "a tie leg never obstructs"


def test_an_edge_without_per_conversation_values_is_untestable_not_false():
    spec = {
        "a": {"x": [0.9] * 30, "y": [4.0] * 30},
        "b": {"x": [0.2] * 30, "y": [2.0] * 30},
    }
    per_session = _per_session(spec)
    del per_session["judge-b"]["a"]["y"]

    found = edges.examine("t", COLUMNS, _means(spec), per_session, samples=100)

    assert found["edges"] == []
    (gap,) = found["untestable"]
    assert (gap["winner"], gap["loser"], gap["n_shared"]) == ("a", "b", 0)
    assert gap["why"].startswith("judge-b:y has 0 shared conversation(s)")
    assert found["counts"]["untestable"] == 1 and found["counts"]["stored"] == 1
    assert found["layers"] == [["a", "b"]], "untestable is not false, and it is not true either"


def test_too_few_shared_conversations_is_untestable():
    spec = {"a": {"x": [0.9] * 5, "y": [4.0] * 5}, "b": {"x": [0.2] * 5, "y": [2.0] * 5}}
    found = _examine(spec, samples=100, min_shared=10)
    assert found["edges"] == [] and len(found["untestable"]) == 1
    assert "5 shared conversation(s); 10 are needed" in found["untestable"][0]["why"]


def test_a_system_missing_a_column_is_outside_the_population():
    spec = {
        "a": {"x": [0.9] * 20, "y": [4.0] * 20},
        "b": {"x": [0.2] * 20, "y": [2.0] * 20},
        "c": {"x": [0.5] * 20, "y": [3.0] * 20},
    }
    means = _means(spec)
    del means["judge-b"]["c"]["y"]

    found = edges.examine("t", COLUMNS, means, _per_session(spec), samples=100)

    assert found["systems"] == ["a", "b"]
    assert found["outside"] == [{"system": "c", "missing": ["judge-b:y"]}]
    assert {edge["winner"] for edge in found["edges"]} | {
        edge["loser"] for edge in found["edges"]
    } == {"a", "b"}
    assert "c" not in [system for group in found["layers"] for system in group]


def test_layers_share_a_group_where_no_kept_edge_separates():
    systems = ["low", "mid", "mid2", "top", "loner"]
    kept = [("top", "mid"), ("top", "mid2"), ("mid", "low")]
    assert edges.layers(systems, kept) == [["loner", "top"], ["mid", "mid2"], ["low"]]


def test_the_result_is_deterministic():
    base = [0.5 + (index % 7) * 0.03 for index in range(30)]
    spec = {
        "a": {
            "x": [value + 0.01 * (index % 3) for index, value in enumerate(base)],
            "y": [3.0] * 30,
        },
        "b": {"x": base, "y": [3.0] * 30},
    }
    assert _examine(spec, samples=300) == _examine(spec, samples=300)


def test_counts_at_the_thresholds_are_monotone():
    base = [0.5 + (index % 7) * 0.03 for index in range(30)]
    spec = {
        "a": {
            "x": [value + 0.01 * (index % 3) for index, value in enumerate(base)],
            "y": [3.0] * 30,
        },
        "b": {"x": base, "y": [3.0] * 30},
        "c": {"x": [value - 0.3 for value in base], "y": [2.0] * 30},
    }
    holds = _examine(spec, samples=300)["counts"]["holds"]
    assert holds["0.99"] <= holds["0.95"] <= holds["0.90"]


# --- the committed artefacts against the published table ---------------------


def _published_by_judge(payload: dict, track: str) -> dict:
    """{judge: {system_id: headline}} for one track, from docs/leaderboard.json."""
    out: dict = {}
    for table in payload["tables"]:
        if table["track"] != track or not table.get("scored"):
            continue
        judge_model = table["versions"].get("judge_model")
        if judge_model not in edges.JUDGES:
            continue
        for row in table["rows"]:
            if row.get("headline"):
                out.setdefault(judge_model, {})[row["system_id"]] = dict(row["headline"])
    return out


@pytest.mark.parametrize("path", sorted((REPO_ROOT / "docs").glob("edges-*.json")))
def test_a_committed_artefact_is_consistent_with_itself_and_with_the_table(path):
    """No answer cache is needed for this: every edge must be a dominance on the
    published means, the layers must partition the population, and the counts
    must be the edge list counted."""
    found = json.loads(path.read_text(encoding="utf-8"))
    payload = json.loads((REPO_ROOT / "docs" / "leaderboard.json").read_text(encoding="utf-8"))
    by_judge = _published_by_judge(payload, found["track"])
    if len(by_judge) < 2:
        pytest.skip(f"{found['track']} is not published under two judges")

    systems = set(found["systems"])
    assert sorted(found["judges"]) == sorted(by_judge), "the artefact names other judges"
    for edge in found["edges"] + found["untestable"]:
        assert {edge["winner"], edge["loser"]} <= systems
        assert _dominates(edge["winner"], edge["loser"], by_judge, found["decimals"]), (
            f"{edge['winner']} > {edge['loser']} is not a dominance on the published means"
        )
    for edge in found["edges"]:
        assert edge["holds"] == (edge["p_holds"] >= found["threshold"])
        assert len(edge["legs"]) == len(found["judges"]) * len(found["columns"])
        assert min(leg["p_not_behind"] for leg in edge["legs"]) >= edge["p_holds"] - 1e-9

    flat = [system for group in found["layers"] for system in group]
    assert sorted(flat) == sorted(systems), "the layers do not partition the population"
    assert found["undominated"] == found["layers"][0]
    kept = [(e["winner"], e["loser"]) for e in found["edges"] if e["holds"]]
    assert found["layers"] == edges.layers(found["systems"], kept)

    counts = found["counts"]
    assert counts["stored"] == len(found["edges"]) + len(found["untestable"])
    assert counts["tested"] == len(found["edges"])
    for cut, number in counts["holds"].items():
        assert number == sum(1 for e in found["edges"] if e["p_holds"] >= float(cut))
