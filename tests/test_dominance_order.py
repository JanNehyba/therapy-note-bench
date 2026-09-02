"""No table is ordered by dominance, and no row carries a place, until the edges are tested.

For one day the iCARE tables were ordered by (systems that beat me, systems I
beat) with a Place column. The relation underneath had never been tested; when
it was, a substantial share of its edges did not survive resampling the
conversations, and the tie-break decided more of the drawn order than the data
did. Both came off. The interim these tests hold is the honest one: rows in
alphabetical order, labelled as such, with the reason, and nothing in the
payload that could be read as a rank.

The fixtures stay, because the ordering comes back -- from tested layers, with
nothing breaking ties -- and these are the rows it will be tested on.
"""

from __future__ import annotations

from pathlib import Path

from tests.test_page_runs import _flat, _judges_payload, _run
from tnb import judge, report, results
from tnb.config import REPO_ROOT
from tnb.results import Metrics, Row


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


#: `top` beats everything on every column; `middle` beats `bottom`; `twin`
#: matches `middle` exactly. Under an untested relation none of that may order
#: the table.
LADDER = {
    "top": dict(rouge_l=0.9, bertscore=0.9, trace=4.0, temporal_past=0.9, temporal_next=0.9),
    "middle": dict(rouge_l=0.6, bertscore=0.6, trace=3.0, temporal_past=0.6, temporal_next=0.6),
    "twin": dict(rouge_l=0.6, bertscore=0.6, trace=3.0, temporal_past=0.6, temporal_next=0.6),
    "bottom": dict(rouge_l=0.2, bertscore=0.2, trace=2.0, temporal_past=0.2, temporal_next=0.2),
}


def _tables(rows: list[Row]) -> list[dict]:
    data = report.build(rows)
    return [table for table in data["tables"] if table["track"] == results.TRACK_ICARE]


def test_nothing_is_ordered_by_dominance_while_the_edges_are_untested():
    """The switch is one constant, and it is off until an edges artefact exists."""
    assert not report.DOMINANCE_ORDERED, (
        f"{sorted(report.DOMINANCE_ORDERED)} would be ordered by a relation nobody has tested"
    )
    assert not list((REPO_ROOT / "docs").glob("edges-*.json")), (
        "docs/edges-*.json exists: the ordering may return from tested layers, and this "
        "test retires with it"
    )


def test_unranked_rows_are_alphabetical_and_carry_no_place():
    for table in _tables(_both_judges(LADDER)):
        drawn = [row["system_id"] for row in table["rows"]]
        assert drawn == sorted(drawn), f"rows are not alphabetical: {drawn}"
        assert "ordered_by" not in table and "places" not in table, (
            "the table still claims an ordering the relation cannot support"
        )
        for row in table["rows"]:
            assert "place" not in row, f"{row['system_id']} carries a place"


def test_a_ranked_table_is_untouched():
    """Completeness still orders SOAP; only the dominance path is off."""
    from tests.test_page_runs import _row

    data = report.build(
        [_row("worse", judge.DEFAULT_MODEL, 0.4), _row("better", judge.DEFAULT_MODEL, 0.6)]
    )
    soap = next(table for table in data["tables"] if table["track"] == results.TRACK_TNEVAL)
    assert [row["system_id"] for row in soap["rows"]] == ["better", "worse"]
    assert soap["ranking_measure"] == "completeness"


def test_the_page_says_the_rows_are_alphabetical_and_why(tmp_path: Path):
    data = report.build(_both_judges(LADDER))
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = _judges_payload()
    data["roster"] = None
    drawn = _flat(_run(report.render_page(data), tmp_path, panel="table-host"))

    assert "alphabetical order" in drawn, "the page does not say the rows are alphabetical"
    assert "has not been tested" in drawn, (
        "the page says there is nothing to order these rows by; there is, and it is untested"
    )
    for gone in ("places for", "Place", "beats outright"):
        assert gone not in drawn, f"{gone!r} is still drawn"


def test_the_published_icare_tables_are_alphabetical_and_place_free():
    import json

    if not report.DATA_PATH.exists():
        return
    payload = json.loads(report.DATA_PATH.read_text(encoding="utf-8"))
    for table in payload["tables"]:
        if table["track"] != results.TRACK_ICARE:
            continue
        ids = [row["system_id"] for row in table["rows"]]
        assert ids == sorted(ids), f"published iCARE rows are not alphabetical: {ids}"
        assert "ordered_by" not in table and "places" not in table
        assert all("place" not in row for row in table["rows"])
