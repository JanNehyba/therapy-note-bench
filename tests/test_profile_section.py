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
    it is printed as apparatus, after the span, and says that it is not a score
    in the tooltip on its own heading -- where the three column glosses moved
    on 2026-09-03, out of a list under the table that put three paragraphs of
    definition between a reader and the question the table answers.
    """
    drawn = _drawn(tmp_path, payload)
    profile = payload["orders"]

    assert "It is not a score" in drawn, "the median is drawn with nothing saying what it is not"
    assert "no way of building one would be a measurement" in drawn
    # The span is read before the middle, which is the whole reason both are
    # printed: one model runs from first to last and no middle describes it.
    # The *columns*, not the first mention of either word: the blurb names the
    # two the rows are ordered by, which is the one thing a reader was asking
    # the table and could not find, and it necessarily says "Median" first.
    assert drawn.index(">Span<") < drawn.index(">Median<")
    for absent in ("Score", "Total", "Overall", "Combined score"):
        assert f">{absent}<" not in drawn, f"a column headed {absent} is an aggregate"
    for row in profile["rows"]:
        assert "mean" not in row, "the payload's rows carry an average across instruments"


def test_the_top_group_is_counted_per_instrument_not_per_table(tmp_path, payload):
    """Three, because dominance is tested on both judges at once.

    Six would be one test counted twice, and would offer a reader a resolution
    the artefact cannot express: undominated under one judge and not the other.

    It was a column until 2026-09-03 and is a sentence now: as the table's first
    sort key it made the order unreadable -- a row with a median of 6.0 sat
    below one with 16.0, correctly, and nothing on screen said why.
    """
    drawn = _drawn(tmp_path, payload)
    tested = len(payload["orders"]["instruments_tested"])
    counted = sum(1 for row in payload["orders"]["rows"] if row["top_group"] == tested)

    assert f"{counted} of the {len(payload['orders']['rows'])} models are in the top group" in (
        " ".join(drawn.split())
    )
    assert '<span class="of">' not in drawn, (
        "the top group is drawn as a column again; it is the table's evidence and not its order"
    )


def test_the_rows_are_ordered_by_the_column_the_reader_can_see(tmp_path, payload):
    """One key, and it is the last column.

    Ordered by top group first and then by the median, the table read as broken
    to anybody who did not know what the first column was. The median is now
    the only key, so a reader can check the order against the numbers in front
    of them -- which is the whole of what an order in a table is for.
    """
    rows = payload["orders"]["rows"]
    medians = [row["median"] for row in rows]
    assert medians == sorted(medians), (
        "the rows are not in median order, so the column a reader checks the order "
        "against disagrees with the order"
    )
    for first, second in zip(rows, rows[1:], strict=False):
        if first["median"] == second["median"]:
            assert first["label"] <= second["label"], "ties are not broken by name"

    drawn = _drawn(tmp_path, payload)
    assert "the rows are ordered by the Median column" in " ".join(drawn.split()), (
        "the page does not say what puts the rows in this order"
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


def test_the_section_names_the_interval_it_does_not_have(tmp_path, payload):
    """`docs/methodology.md` says this page names the gap. It did not.

    The jackknife leaves out a model, so it answers whether a band rests on one
    system. It says nothing about whether the correlation would hold on a
    different set of conversations, and the repository resamples conversations
    everywhere else -- for the tested comparisons, the bands and the judges'
    own-vendor lean -- so a reader has every reason to assume it was done here
    too. An absence a reader assumes closed is the failure this whole file is
    about, one level up.
    """
    drawn = _drawn(tmp_path, payload)

    assert "resamples the sessions" in drawn, (
        "the section prints correlations and does not say which interval is missing"
    )
    assert "rather than assumed" in drawn


def test_the_apparatus_is_behind_a_toggle_and_the_findings_are_not(tmp_path, payload):
    """Eight paragraphs stood between this table and the next section, in the
    order they had been written rather than the order anybody needs them: the
    answer to "which model" was seventh and the first six were definitions.

    Two findings stay in the open -- how many models no instrument separates,
    and that the instrument decides the order where the judge does not. The
    rest is apparatus for a reader who is checking those two, and it is behind
    a summary that says so.
    """
    drawn = _drawn(tmp_path, payload)
    if "<details" not in drawn:
        pytest.skip("this payload draws no apparatus to fold away")

    head, _, folded = drawn.partition("<details")
    assert '<p class="note">' not in head, (
        "a note is drawn between the table and the toggle; all of the prose folds"
    )
    for inside in (
        "models are in the top group of every instrument",
        "decides almost everything",
        "no way of building one would be a measurement",
        "Pooled over all three instruments",
        "resamples the sessions",
        "No heading here sorts",
    ):
        assert inside in folded, f"{inside!r} is drawn in the open rather than folded"
    assert "<summary>" in folded


def test_the_page_says_llm_judge_where_a_stranger_would_read_a_person(tmp_path, payload):
    """ "The judge is close to interchangeable" is the most quotable sentence on
    this page, and to anybody who has not seen this repository it is a claim
    about a person. The two notes that stay in the open name what a judge is.
    """
    drawn = _drawn(tmp_path, payload)
    if "judge" not in drawn.lower():
        pytest.skip("this section mentions no judge in this payload")
    assert "LLM judge" in drawn, "the section says 'judge' with nothing saying what kind"


# --- the six ranks and the median, reimplemented from the definition ----------
#
# A reader asked how they are to know these were computed right. The answer
# cannot be "the code that computed them says so", so the rule is written out a
# second time here, from `composite.order` and `concordance._positions` as a
# specification rather than as an import, and the two are compared.
#
# The rule, in full:
#   1. Take the models alone -- reference rows are not in this table.
#   2. Per column, sort by value descending; two systems share a place when
#      their values print the same at that column's decimals.
#   3. A system's place on a table is the mean of its places over that
#      instrument's columns, equal weights.
#   4. Rank on that mean, exact ties sharing the better place (1, 2, 2, 4).
#   5. The row's median is the middle of its six ranks; with six there is no
#      single middle, so it is the mean of the third and fourth.


def _printed(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}"


def _places_on_one_column(values: dict[str, float], decimals: int) -> dict[str, int]:
    ordered = sorted(values.items(), key=lambda pair: (-pair[1], pair[0]))
    places: dict[str, int] = {}
    for index, (system, value) in enumerate(ordered):
        previous = ordered[index - 1] if index else None
        if previous and _printed(value, decimals) == _printed(previous[1], decimals):
            places[system] = places[previous[0]]
        else:
            places[system] = index + 1
    return places


def _rank_one_table(table: dict, population: set[str]) -> dict[str, int]:
    rows = [
        row
        for row in table["rows"]
        if row.get("system_type") == "model" and row["system_id"] in population
    ]
    columns = [(c["key"], c["digits"]) for c in table["columns"]]
    per_column = {}
    for key, decimals in columns:
        values = {
            row["system_id"]: row["headline"][key]
            for row in rows
            if row["headline"].get(key) is not None
        }
        per_column[key] = _places_on_one_column(values, decimals)

    mean_place = {}
    for row in rows:
        system = row["system_id"]
        if any(system not in per_column[key] for key, _ in columns):
            continue  # a mean over fewer columns is a different quantity
        mean_place[system] = sum(per_column[key][system] for key, _ in columns) / len(columns)

    ordered = sorted(mean_place, key=lambda s: (mean_place[s], s))
    ranks: dict[str, int] = {}
    for index, system in enumerate(ordered):
        if index and mean_place[system] == mean_place[ordered[index - 1]]:
            ranks[system] = ranks[ordered[index - 1]]
        else:
            ranks[system] = index + 1
    return ranks


def _middle(values: list[int]) -> float:
    ordered = sorted(values)
    half = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[half])
    return (ordered[half - 1] + ordered[half]) / 2


@pytest.fixture
def recomputed(payload) -> dict[str, list[int]]:
    orders = payload.get("orders")
    if not orders:
        pytest.skip("no orders artefact in this payload")
    by_id = {t["id"]: t for t in payload["tables"] if t.get("scored") and t.get("id")}
    population = set(orders["population"])
    found: dict[str, list[int]] = {}
    for column in orders["columns_drawn"]:
        table = by_id.get(column["table"])
        assert table is not None, f"the profile draws a column from an absent table: {column}"
        ranks = _rank_one_table(table, population)
        for system in population:
            found.setdefault(system, []).append(ranks[system])
    return found


def test_every_rank_in_the_profile_is_the_one_the_rule_gives(payload, recomputed):
    """Six ranks a row, against a second implementation of the ordering rule."""
    for row in payload["orders"]["rows"]:
        assert row["ranks"] == recomputed[row["system_id"]], (
            f"{row['label']}: the table draws {row['ranks']} where the rule gives "
            f"{recomputed[row['system_id']]}"
        )


def test_every_median_and_span_is_the_middle_of_those_ranks(payload, recomputed):
    """And the two summary columns, taken by hand off the six."""
    for row in payload["orders"]["rows"]:
        ranks = recomputed[row["system_id"]]
        assert row["median"] == pytest.approx(round(_middle(ranks), 1)), (
            f"{row['label']}: median {row['median']} against {_middle(ranks)} over {ranks}"
        )
        assert (row["best"], row["worst"]) == (min(ranks), max(ranks)), (
            f"{row['label']}: span {row['best']}-{row['worst']} over ranks {ranks}"
        )


def test_the_rows_are_drawn_in_the_order_the_medians_put_them(payload, recomputed):
    """The one thing a reader checks by eye, and the one that was wrong.

    The rows were ordered by the top-group count and then by the median, so a
    row with a median of 6.0 sat below one with 16.0 -- correct under the rule
    and unreadable, because the key was a column most rows share a value on.
    """
    rows = payload["orders"]["rows"]
    keys = [(row["median"], row["label"]) for row in rows]
    assert keys == sorted(keys), (
        "the rows are not in median order, so the column a reader checks the order against "
        f"disagrees with the order: {[(r['label'], r['median']) for r in rows]}"
    )


def test_a_median_over_a_span_wider_than_half_the_table_is_marked(tmp_path, payload):
    """A row ranked 1 on one table and 18 on another has a median of 6.0 and
    sits sixth. That reads as an error, and it was reported as one.

    The rule is half the table: a row whose ranks straddle more than that is not
    being summarised by a middle number, it is being hidden by one. The median
    stays printed, because the rows are ordered by it and an order whose key a
    reader cannot see is one they cannot check.
    """
    rows = payload["orders"]["rows"]
    over = [r for r in rows if (r["worst"] - r["best"]) > len(rows) // 2]
    for row in rows:
        assert row["span_over_half"] == (row in over), (
            f"{row['label']}: span {row['best']}-{row['worst']} over {len(rows)} rows"
        )

    drawn = _drawn(tmp_path, payload)
    marked = drawn.count('class="meta hollow"')
    assert marked == len(over), (
        f"{len(over)} rows have a span over half the table and {marked} medians are marked"
    )
    if over:
        assert "describes nothing" in drawn, "the mark is drawn with nothing saying what it means"
        assert f"{len(over)} of these {len(rows)} models are ranked in the top half" in (
            " ".join(drawn.split())
        ), "the count of unreliable medians is not stated where a reader meets the table"
