"""The iCARE tables are ordered by the systems beating each other, not by name.

`concordance` works out which systems beat which outright -- at least as good on
every column of an instrument under both judges, and strictly better somewhere
-- and the page has drawn that as a column since it was computed. The rows
underneath were alphabetical, under a sentence saying there was nothing to order
them by.

Refusing to rank was right while the only candidate was a mean: the columns have
no common unit, the weights were never measured, and removing one row reverses
pairs among the others. Dominance has none of those properties, which is exactly
why it may order a table that a mean may not -- and those properties are what
these tests hold it to.
"""

from __future__ import annotations

from pathlib import Path

from tests.test_page_runs import _flat, _judges_payload, _run
from tnb import judge, report, results
from tnb.results import Metrics, Row


def _icare(system: str, judge_model: str, **measures) -> Row:
    """One iCARE row. Every column present, because dominance needs all of them."""
    # All five, because `_dominates` refuses a pair where either side is
    # missing a measure -- correctly, since a missing number is not a draw.
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
    """The same scores under both published judges, so dominance can be decided."""
    return [
        _icare(system, judge_model, **measures)
        for judge_model in (judge.DEFAULT_MODEL, judge.SECOND_JUDGE)
        for system, measures in spec.items()
    ]


#: `top` beats `middle` and `bottom` on every column; `middle` beats `bottom`;
#: `twin` matches `middle` exactly, so nothing separates them.
LADDER = {
    "top": {
        "rouge_l": 0.9,
        "bertscore": 0.9,
        "trace": 4.0,
        "temporal_past": 0.9,
        "temporal_next": 0.9,
    },
    "middle": {
        "rouge_l": 0.6,
        "bertscore": 0.6,
        "trace": 3.0,
        "temporal_past": 0.6,
        "temporal_next": 0.6,
    },
    "twin": {
        "rouge_l": 0.6,
        "bertscore": 0.6,
        "trace": 3.0,
        "temporal_past": 0.6,
        "temporal_next": 0.6,
    },
    "bottom": {
        "rouge_l": 0.2,
        "bertscore": 0.2,
        "trace": 2.0,
        "temporal_past": 0.2,
        "temporal_next": 0.2,
    },
}


def _table(rows: list[Row]) -> dict:
    data = report.build(rows)
    return next(table for table in data["tables"] if table["track"] == results.TRACK_ICARE)


def test_the_rows_are_ordered_by_dominance_and_not_by_name():
    table = _table(_both_judges(LADDER))
    drawn = [row["system_id"] for row in table["rows"]]
    assert drawn[0] == "top", f"the table is not led by the system that beats everything: {drawn}"
    assert drawn[-1] == "bottom", f"the system everything beats is not last: {drawn}"
    assert drawn != sorted(drawn), "the rows are still in alphabetical order"
    assert table["ordered_by"] == "dominance"


def test_systems_nothing_separates_share_a_place_and_the_next_is_skipped():
    table = _table(_both_judges(LADDER))
    places = {row["system_id"]: row["place"] for row in table["rows"]}
    assert places["middle"] == places["twin"], (
        "two systems with identical scores on every column were drawn one above the other "
        "as though something separated them"
    )
    assert places["top"] == 1
    assert places["bottom"] == places["middle"] + 2, (
        "a shared place did not consume the place after it, so the numbers claim a rank "
        "nobody holds"
    )
    assert table["places"] == {"n": 3, "of": 4}


def test_the_order_is_the_same_under_both_judges():
    """Dominance holds only where both judges agree, so it cannot move with one.

    A reader switching the judge switch is told the tables disagree about
    order. On this one they must not, and the reason is not a coincidence.
    """
    data = report.build(_both_judges(LADDER))
    tables = [t for t in data["tables"] if t["track"] == results.TRACK_ICARE]
    assert len(tables) == 2, "the fixture did not produce one table per judge"
    orders = {tuple(row["system_id"] for row in table["rows"]) for table in tables}
    assert len(orders) == 1, f"the two judges' tables are ordered differently: {orders}"


def test_a_system_the_comparison_never_placed_does_not_lead_the_table():
    """Nobody beat it because nobody could compare it. That is not a clean sheet.

    A system scored by only one of the two judges is outside the population
    dominance is computed over. Counting its zero defeats as a zero would put it
    first, which publishes an absence as a perfect record.
    """
    rows = _both_judges(LADDER)
    rows.append(
        _icare(
            "only-one-judge",
            judge.DEFAULT_MODEL,
            rouge_l=0.99,
            bertscore=0.99,
            trace=5.0,
            temporal_past=0.99,
            temporal_next=0.99,
        )
    )
    table = _table(rows)
    drawn = [row["system_id"] for row in table["rows"]]
    assert drawn[0] == "top", f"an unplaced system led the table: {drawn}"
    assert drawn.index("only-one-judge") > drawn.index("bottom"), (
        "a system the comparison could not place was sorted among the ones it placed"
    )
    placed = {row["system_id"]: row["place"] for row in table["rows"]}
    assert placed["only-one-judge"] is None, "a system nobody compared was given a place"


def test_removing_a_row_cannot_reverse_two_others():
    """The property a mean does not have, and the reason this ordering is allowed.

    Removing the therapist's row from a mean-ordered table reversed twenty
    pairs. Dominance is pairwise, so a third system leaving cannot change what
    two others did to each other -- only how many others each of them beat.
    """
    full = _table(_both_judges(LADDER))
    order = [row["system_id"] for row in full["rows"]]
    without = _table(_both_judges({k: v for k, v in LADDER.items() if k != "twin"}))
    kept = [row["system_id"] for row in without["rows"]]
    assert kept == [system for system in order if system != "twin"], (
        f"removing one row re-ordered the others: {order} -> {kept}"
    )


def test_the_page_says_how_many_places_there_are(tmp_path: Path):
    data = report.build(_both_judges(LADDER))
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = _judges_payload()
    data["roster"] = None
    drawn = _flat(_run(report.render_page(data), tmp_path, panel="table-host"))

    assert "3 places for 4 systems" in drawn, (
        "the table gives an order and does not say how much of it the evidence contains"
    )
    assert "alphabetical order" not in drawn, "the page still calls the rows alphabetical"
    assert "beats outright" in drawn.lower(), "the order is given with no statement of what it is"


def test_the_published_icare_tables_are_ordered_and_say_so():
    """The published artefact, not a fixture: the order and the count must agree."""
    import json

    if not report.DATA_PATH.exists():
        return
    payload = json.loads(report.DATA_PATH.read_text(encoding="utf-8"))
    for table in payload["tables"]:
        if table["track"] != results.TRACK_ICARE:
            continue
        places = [row["place"] for row in table["rows"] if row["place"] is not None]
        assert places == sorted(places), f"the drawn order does not follow the places: {places}"
        assert table["places"]["n"] == len(set(places))
        assert table["places"]["of"] == len(places)
        assert table["ordered_by"] == "dominance"


def test_a_row_whose_label_differs_from_its_id_still_gets_its_place():
    """`concordance` keys on the printed label; the places were looked up by id.

    Three published rows carry a label their id does not match -- the
    therapist's note is drawn as "therapist-written (TN-Eval)" and TN-Eval's two
    models carry the paper and the year. Looked up by id they all missed, and a
    miss here is not a dash in one cell: it sorts the row out of the comparison
    entirely, among the systems nobody could place. `pdsqi-soap` is the other
    track ordered this way and holds all three.
    """
    rows = _both_judges(LADDER)
    labelled = []
    for row in rows:
        if row.system_id == "top":
            labelled.append(Row(**{**row.__dict__, "system_label": "top-written (somewhere else)"}))
        else:
            labelled.append(row)
    table = _table(labelled)
    places = {row["system_id"]: row["place"] for row in table["rows"]}
    assert places["top"] == 1, (
        "a row whose printed name differs from its id lost the place the comparison gave it"
    )
    assert table["rows"][0]["system_id"] == "top"


def test_one_judge_is_no_comparison_and_the_table_says_so():
    """Dominance is "under both judges", so one judge yields no places at all.

    The table then has to fall back to saying its rows are alphabetical.
    `ordered_by` was set from the track's comparison rather than from this
    table's own rows, and a table with nothing placed in it would have carried
    an ordering it is not part of.
    """
    rows = [_icare(system, judge.DEFAULT_MODEL, **measures) for system, measures in LADDER.items()]
    data = report.build(rows)
    tables = [table for table in data["tables"] if table["track"] == results.TRACK_ICARE]
    assert tables, "the fixture produced no iCARE table"
    for table in tables:
        assert table["ordered_by"] is None, (
            "a single judge's table published an ordering that is defined across two"
        )
        assert table["places"] is None
        assert all(row["place"] is None for row in table["rows"])
    drawn = [row["system_id"] for row in tables[0]["rows"]]
    assert drawn == sorted(drawn), (
        "with no comparison to order by, the rows are not in the alphabetical order the "
        "sentence under them claims"
    )
