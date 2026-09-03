"""The profile is drawn from a committed artefact, or it is not drawn.

The rule this file enforces is the one three reverted commits were about: a
visible column whose basis is not a committed artefact goes up and comes back
down. Here the artefact is `docs/orders.json`, and the section may not survive
its absence, its staleness, or a table appearing that it was not built from.

The other half is what the section may not say. Its numbers support a narrow
claim and invite a wider one -- that the three instruments measure different
things -- which this repository's own measurement contradicts. So the wording
is pinned too.
"""

import json

import pytest

from tests.test_page_runs import _flat, _page_data, _run
from tnb import report, results
from tnb.scoring import orders


def _drawn(tmp_path, data) -> str:
    return _flat(_run(report.render_page(data), tmp_path, panel="profile"))


PROMPTS = {
    results.TRACK_TNEVAL: "tneval-soap-v1",
    results.TRACK_PDSQI: "tneval-soap-v1",
    results.TRACK_ICARE: "icare-zeroshot-v1",
}


def _three_tracks() -> list:
    """Six tables: three instruments, two judges, five models on every one.

    The published shape, because the sentences this section is judged on are
    about pairs of instruments and a payload with one instrument has no pair to
    describe. The three tracks disagree on purpose -- each orders the models
    differently -- so the bands are not all the same number.
    """
    from tnb import judge

    ladders = {
        results.TRACK_TNEVAL: ["a", "b", "c", "d", "e"],
        results.TRACK_PDSQI: ["c", "a", "e", "b", "d"],
        results.TRACK_ICARE: ["e", "d", "c", "b", "a"],
    }
    rows = []
    for track, order in ladders.items():
        for judge_model in (judge.DEFAULT_MODEL, judge.SECOND_JUDGE):
            for position, system in enumerate(order):
                value = (len(order) - position) / len(order)
                rows.append(
                    results.Row(
                        track=track,
                        system_id=system,
                        system_type="model",
                        provider="einfra",
                        prompt_version=PROMPTS[track],
                        judge_model=judge_model,
                        judge_prompt_version=f"{track}-v1",
                        judge_settings={"model": judge_model},
                        n_sessions_attempted=10,
                        n_sessions_generated=10,
                        n_sessions_scored=10,
                        metrics=results.Metrics(
                            headline={key: value for key, _ in report.COLUMNS[track]}
                        ),
                    )
                )
    return rows


@pytest.fixture
def payload(monkeypatch) -> dict:
    """A page payload with a profile that fits the tables it is drawn beside."""
    data = report.build(_three_tracks())
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = None
    data["concordance"] = {}
    found = orders.examine(data["tables"])
    assert found, "the fixture's tables cannot carry a profile"
    monkeypatch.setattr(orders, "load", lambda docs_dir=None: json.loads(json.dumps(found)))
    data["orders"] = report._orders_for(data["tables"], report.DOCS_DIR)
    assert data["orders"], "the profile was refused by its own guard"
    return data


def test_no_artefact_means_no_section(tmp_path, monkeypatch):
    """Absent, not empty, and not a heading over a promise.

    A section that draws itself with "not yet measured" is the shape this
    repository took down twice: a reader reads the heading and remembers the
    claim, whatever the body says.
    """
    monkeypatch.setattr(orders, "load", lambda docs_dir=None: None)
    data = _page_data(tmp_path)
    data["orders"] = report._orders_for(data["tables"], report.DOCS_DIR)

    assert data["orders"] is None
    summary = _run(report.render_page(data), tmp_path)
    removed = next((line for line in summary.splitlines() if line.startswith("removed:")), "")
    assert "profile" in removed, "the section stayed on the page with no artefact behind it"
    empty = next(
        (line for line in summary.splitlines() if line.startswith("empty and not removed:")), ""
    )
    assert "profile" not in empty, "an empty frame is worse than no frame"


def test_one_rank_out_of_place_is_enough_to_withdraw_it(tmp_path, monkeypatch):
    """The guard the tested-edges artefact does not have.

    Rebuilding this costs nothing, so a profile drawn beside tables it was not
    computed from has no excuse. The failure it prevents is silent: new rows,
    old ranks, and a page that looks exactly as right as it did yesterday.
    """
    data = _page_data(tmp_path)
    fresh = orders.examine(data["tables"])
    stale = json.loads(json.dumps(fresh))
    system = stale["orders"][0]["systems"][0]
    stale["orders"][0]["ranks"][system] += 1

    monkeypatch.setattr(orders, "load", lambda docs_dir=None: stale)
    assert report._orders_for(data["tables"], report.DOCS_DIR) is None


def test_a_system_the_artefact_never_saw_withdraws_it(tmp_path, monkeypatch):
    """A model joins the benchmark and the profile has not been rebuilt.

    The most likely way this goes stale in practice, and the one a reader could
    not possibly detect: eighteen rows where the tables now draw nineteen.
    """
    data = _page_data(tmp_path)
    fresh = orders.examine(data["tables"])
    monkeypatch.setattr(orders, "load", lambda docs_dir=None: fresh)
    assert report._orders_for(data["tables"], report.DOCS_DIR) is not None

    for table in data["tables"]:
        if not table["scored"]:
            continue
        newcomer = dict(table["rows"][0])
        newcomer["system_id"] = newcomer["label"] = "newcomer"
        table["rows"].append(newcomer)
    assert report._orders_for(data["tables"], report.DOCS_DIR) is None


def test_every_rank_drawn_is_the_rank_the_artefact_holds(tmp_path, payload):
    """Cell by cell, because the page could draw a plausible table of its own.

    The rows arrive already ordered and the template only lays them out, so a
    rank on the page that is not in the artefact means the page computed
    something, which is the thing it is not allowed to do.
    """
    drawn = _drawn(tmp_path, payload)
    profile = payload["orders"]

    for row in profile["rows"]:
        assert row["label"] in drawn, f"{row['label']} is not on the page"
        for rank in row["ranks"]:
            assert f">{rank}</td>" in drawn, f"{row['label']}'s rank {rank} is not drawn"
    assert drawn.count("<tr>") == len(profile["rows"]) + 1, "a row was invented or dropped"


def test_the_section_does_not_claim_the_instruments_measure_different_things(tmp_path, payload):
    """The wider claim the numbers invite and the measurements refuse.

    Between individual columns, where no ordering rule is involved, columns of
    different instruments predict each other about as well as columns of the
    same one. So the six orders disagreeing is a fact about the averaging of
    places, and a sentence saying the instruments measure different things
    would be false. It has to be on the page, next to the thing that invites
    it, and it has to stay there.
    """
    drawn = _drawn(tmp_path, payload)

    assert "not the instruments measuring different things" in drawn, (
        "the counter-finding left the section, and the section now reads as its own opposite"
    )
    assert "in the averaging of places" in drawn


def test_the_section_publishes_no_order_of_its_own(tmp_path, payload):
    """No total, and nothing that could be read as one.

    A mean over the three instruments would have to price a SOAP rubric against
    a 17-field form. The median is printed because the rows are ordered by it
    and an order whose key a reader cannot see is one they cannot check -- so
    it is printed as apparatus, after the span, and says in the legend that it
    is not a score.
    """
    drawn = _drawn(tmp_path, payload)
    profile = payload["orders"]

    assert "It is not a score" in drawn, "the median is drawn with nothing saying what it is not"
    assert "no way of building one would be a measurement" in drawn
    # The span is read before the middle, which is the whole reason both are
    # printed: one model runs from first to last and no middle describes it.
    assert drawn.index("Span") < drawn.index("Median")
    for absent in ("Score", "Total", "Overall", "Combined score"):
        assert f">{absent}<" not in drawn, f"a column headed {absent} is an aggregate"
    for row in profile["rows"]:
        assert "mean" not in row, "the payload's rows carry an average across instruments"


def test_the_top_group_denominator_is_the_instruments(tmp_path, payload):
    """Three, because dominance is tested on both judges at once.

    Six would be one test counted twice, and would offer a reader a resolution
    the artefact cannot express: undominated under one judge and not the other.
    """
    drawn = _drawn(tmp_path, payload)
    tested = len(payload["orders"]["instruments_tested"])

    assert f'<span class="of">/{tested}</span>' in drawn
    assert f'<span class="of">/{len(payload["orders"]["columns_drawn"])}</span>' not in drawn, (
        "the top group is counted per table rather than per instrument"
    )


def test_the_headings_lead_back_to_the_tables_they_came_from(tmp_path, payload):
    """A rank belongs to a table, and the table is one click away.

    Which is also what keeps the ranking with the table that owns it: this
    section shows where a model landed, and the scores behind each landing stay
    where they were published.
    """
    drawn = _drawn(tmp_path, payload)
    for column in payload["orders"]["columns_drawn"]:
        assert f'data-target="{column["table"]}"' in drawn, (
            f"the {column['instrument']} column does not open its own table"
        )


def test_the_readme_says_it_too_and_only_when_it_can(payload):
    """The README prints one table of the six and has no switch to correct a
    reader with, so it is the surface most likely to be taken for the ranking.
    The finding belongs there. Absent the artefact it says nothing rather than
    saying it with a hole in it, and every figure in it is read off the payload
    -- a sentence with a typed number is the shape that goes stale here."""
    said = report._orders_sentences(payload["orders"])
    profile = payload["orders"]

    assert "adds nothing up" in said
    assert "not the instruments measuring different things" in said
    assert f"{len(profile['population'])} models" in said
    pooled = profile["dominance"]["pooled"]
    assert f"{pooled['dominating']} of {pooled['pairs']} ordered pairs" in said
    assert report._orders_sentences(None) == "", "the block appears with no profile behind it"
