"""Every table is ordered by mean place; tested groups are drawn only from the artefact.

For one day the iCARE tables were ordered by dominance, with a tie-break that
decided more of the drawn order than the data did, and the order came off. The
order now is the mean of each system's places over its instrument's columns,
the same rule on every track. Dominance returns as tested layers read from
`docs/edges-<track>.json`, drawn *beside* the order and never as the order --
and only when that artefact exists, because a Group column drawn from an
untested relation was built and taken down once already.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.test_page_runs import _flat, _judges_payload, _run
from tnb import judge, report, results
from tnb.results import Metrics, Row
from tnb.scoring import edges


def _icare(system: str, judge_model: str, **measures) -> Row:
    """One iCARE row with every column present."""
    headline = {
        "rouge_l": 0.5,
        "bertscore": 0.5,
        "trace": 3.0,
        "temporal_past": 0.5,
        "temporal_next": 0.5,
        **measures,
    }
    return Row(
        track=results.TRACK_ICARE,
        system_id=system,
        system_type="model",
        provider="einfra",
        prompt_version="icare-v1",
        judge_model=judge_model,
        judge_prompt_version="icare-trace-v1",
        judge_settings={"model": judge_model, "thinking_budget": 256},
        n_sessions_attempted=40,
        n_sessions_generated=40,
        n_sessions_scored=40,
        metrics=Metrics(headline=headline, by_section={}, detail={}),
    )


def _both_judges(spec: dict[str, dict]) -> list[Row]:
    return [
        _icare(system, judge_model, **measures)
        for judge_model in (judge.DEFAULT_MODEL, judge.SECOND_JUDGE)
        for system, measures in spec.items()
    ]


#: `top` is best on every column; `middle` and `twin` print the same figures
#: everywhere and so share every place; `bottom` is last on every column.
LADDER = {
    "top": dict(rouge_l=0.9, bertscore=0.9, trace=4.0, temporal_past=0.9, temporal_next=0.9),
    "middle": dict(rouge_l=0.6, bertscore=0.6, trace=3.0, temporal_past=0.6, temporal_next=0.6),
    "twin": dict(rouge_l=0.6, bertscore=0.6, trace=3.0, temporal_past=0.6, temporal_next=0.6),
    "bottom": dict(rouge_l=0.2, bertscore=0.2, trace=2.0, temporal_past=0.2, temporal_next=0.2),
}

TESTED = {
    "layers": [["top"], ["middle", "twin"], ["bottom"]],
    "undominated": ["top"],
    "threshold": 0.95,
    "samples": 10_000,
    "counts": {"stored": 5, "tested": 5, "untestable": 0, "holds": {"0.95": 5}},
    "systems": ["bottom", "middle", "top", "twin"],
}


def _tables(rows: list[Row]) -> list[dict]:
    data = report.build(rows)
    return [table for table in data["tables"] if table["track"] == results.TRACK_ICARE]


def test_nothing_is_ordered_by_dominance_alone():
    """The switch is one constant, and it stays off: an order read from
    dominance alone needs a rule to break the ties the relation leaves, and on
    2026-09-01 that rule decided more of the drawn order than the data did."""
    assert not report.DOMINANCE_ORDERED, (
        f"{sorted(report.DOMINANCE_ORDERED)} would be ordered by dominance alone"
    )


def test_rows_are_ordered_by_mean_place_and_ties_share_a_place(monkeypatch):
    monkeypatch.setattr(edges, "load", lambda track, docs_dir=None: None)
    for table in _tables(_both_judges(LADDER)):
        assert [row["system_id"] for row in table["rows"]] == ["top", "middle", "twin", "bottom"]
        places = {row["system_id"]: row["place"] for row in table["rows"]}
        assert places == {"top": 1, "middle": 2, "twin": 2, "bottom": 4}
        assert table["ordering"]["rule"] == "mean_place"
        assert table["ordering"]["sensitivity"]["baseline"]["first"] == ["top"]


def test_no_artefact_means_no_group_anywhere(monkeypatch):
    """Absent, not empty: a table without the key draws no Group column, and a
    row without the key cannot be read as "group unknown" or "group zero"."""
    monkeypatch.setattr(edges, "load", lambda track, docs_dir=None: None)
    for table in _tables(_both_judges(LADDER)):
        assert "groups_tested" not in table
        assert all("group" not in row for row in table["rows"])


def test_groups_come_from_the_tested_artefact_and_nothing_else(monkeypatch):
    monkeypatch.setattr(
        edges,
        "load",
        lambda track, docs_dir=None: TESTED if track == results.TRACK_ICARE else None,
    )
    for table in _tables(_both_judges(LADDER)):
        assert table["groups_tested"]["undominated"] == ["top"]
        assert table["groups_tested"]["source"] == "edges-icare.json"
        groups = {row["system_id"]: row["group"] for row in table["rows"]}
        assert groups == {"top": 1, "middle": 2, "twin": 2, "bottom": 3}


def test_the_page_says_how_the_rows_are_ordered_and_grouped(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        edges,
        "load",
        lambda track, docs_dir=None: TESTED if track == results.TRACK_ICARE else None,
    )
    data = report.build(_both_judges(LADDER))
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = _judges_payload()
    data["roster"] = None
    drawn = _flat(_run(report.render_page(data), tmp_path, panel="table-host"))

    assert "mean place" in drawn, "the page does not say what orders the rows"
    assert "Group" in drawn and "beaten by no tested comparison" in drawn
    for gone in ("alphabetical", "beats outright", "not ranked", "has not been tested"):
        assert gone not in drawn, f"{gone!r} is still drawn"


def test_the_published_tables_carry_places_and_groups():
    if not report.DATA_PATH.exists():
        return
    payload = json.loads(report.DATA_PATH.read_text(encoding="utf-8"))
    for table in payload["tables"]:
        if not table["scored"]:
            continue
        assert table["ordering"]["rule"] == "mean_place"
        placed = [row for row in table["rows"] if row["place"] is not None]
        assert placed == sorted(placed, key=lambda row: (row["place"], row["mean_place"]))
        assert "ranking_measure" not in table and "not_ranked_reason" not in table
        if "groups_tested" in table:
            assert all("group" in row for row in table["rows"])
            assert table["groups_tested"]["source"] == f"edges-{table['track']}.json"
        else:
            assert all("group" not in row for row in table["rows"])
