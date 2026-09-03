"""The six published orders, read against each other.

`orders.examine` is pure -- it takes the tables `report.build` already made --
so every branch here is exercised on hand-built tables and nothing on disk is
read. What the file is for is the four ways this view could quietly become
something other than what its heading claims: a rank that counts rows the
profile does not draw, a system dropped instead of named, a count of
instruments that is really a count of tables, and an artefact that goes on
being drawn after the rows underneath it moved.
"""

import json

import pytest

from tnb.scoring import orders


def _table(
    track: str,
    judge: str,
    columns: dict[str, int],
    values: dict[str, dict[str, float]],
    *,
    reference: tuple[str, ...] = (),
    tested: tuple[str, ...] | None = None,
) -> dict:
    """One scored table, in the shape `report.build` publishes.

    `values` is {system: {column: value}}; anything named in `reference` is a
    row of the table and not a model, which is the only thing that decides
    whether the profile counts it.
    """
    rows = []
    for system, held in values.items():
        rows.append(
            {
                "system_id": system,
                "label": system,
                "system_type": "reference-model" if system in reference else "model",
                "headline": dict(held),
                # A place a reader would see. The profile recomputes its own
                # and compares, so this is deliberately not the same number.
                "place": 1,
                **({"group": 1 if system in (tested or ()) else 2} if tested is not None else {}),
            }
        )
    return {
        "id": f"{track}-{judge}",
        "track": track,
        "scored": True,
        "versions": {
            "harness_version": "0.7.0",
            "judge_model": judge,
            "judge_prompt_version": f"{track}-v1",
            "judge_settings": {"model": judge},
            "prompt_version": "p-v1",
        },
        "columns": [{"key": key, "digits": digits} for key, digits in columns.items()],
        "rows": rows,
        **({"groups_tested": {"layers": [list(tested)]}} if tested is not None else {}),
    }


def _ladder(track: str, judge: str, order: list[str], **kwargs) -> dict:
    """A table where the first system is best and the last is worst."""
    n = len(order)
    return _table(
        track,
        judge,
        {f"{track}_a": 3, f"{track}_b": 3},
        {
            system: {f"{track}_a": (n - i) / n, f"{track}_b": (n - i) / n}
            for i, system in enumerate(order)
        },
        **kwargs,
    )


MODELS = ["alpha", "beta", "gamma", "delta"]


def _six(order: list[str] | None = None) -> list[dict]:
    """Three instruments, two judges, the same four models on every one."""
    order = order or MODELS
    return [
        _ladder(track, judge, order)
        for track in ("one", "two", "three")
        for judge in ("judge-a", "judge-b")
    ]


def test_a_rank_counts_the_models_and_nothing_else():
    """A reference row is drawn in the table and is not in the profile.

    The failure this prevents is silent and was measured on the published
    tables: reference rows interleave, differently on each one, so a place
    among all rows means a different thing per instrument. Here the reference
    row is placed above two of the three models, which moves every published
    place under it; the profile's ranks must not move with it.
    """
    with_reference = _table(
        "one",
        "judge-a",
        {"one_a": 3},
        {
            "alpha": {"one_a": 0.9},
            "ref": {"one_a": 0.8},
            "beta": {"one_a": 0.7},
            "gamma": {"one_a": 0.6},
        },
        reference=("ref",),
    )
    plain = _table(
        "two",
        "judge-a",
        {"two_a": 3},
        {"alpha": {"two_a": 0.9}, "beta": {"two_a": 0.7}, "gamma": {"two_a": 0.6}},
    )

    found = orders.examine([with_reference, plain])

    assert found["population"] == ["alpha", "beta", "gamma"], "a reference row got into the profile"
    for order in found["orders"]:
        assert "ref" not in order["ranks"]
        assert order["ranks"] == {"alpha": 1, "beta": 2, "gamma": 3}, (
            "the reference row moved a rank it should not be part of"
        )
    named = [system["system_id"] for system in found["reference"]["systems"]]
    assert named == ["ref"], "the row left out is not named"
    assert found["reference"]["in_tables"] == 1 and found["reference"]["of_tables"] == 2


def test_a_system_missing_from_one_table_is_named_and_not_counted():
    """An absence is never a measurement.

    Dropping it quietly would make the profile a different population from the
    one its heading claims, and giving it a rank on the tables it does appear
    in would let a row with fewer numbers sit beside rows with more.
    """
    everywhere = _ladder("one", "judge-a", ["alpha", "beta", "gamma", "delta"])
    short = _ladder("two", "judge-a", ["alpha", "beta", "gamma"])

    found = orders.examine([everywhere, short])

    assert found["population"] == ["alpha", "beta", "gamma"]
    assert [gap["system_id"] for gap in found["outside"]] == ["delta"]
    assert found["outside"][0]["missing"] == ["two-judge-a"], "the table it is missing from"
    for order in found["orders"]:
        assert "delta" not in order["ranks"], "a system outside the profile was given a rank"


def test_the_pairs_are_every_pair_of_tables_grouped_by_what_they_compare():
    """Six tables make fifteen pairs: three inside an instrument, twelve across.

    The three are the comparison that needs no convention -- one instrument,
    two judges -- and the twelve are the one this whole view exists to report.
    Miscounting either way would put a cross-instrument pair in the band the
    page describes as "the same instrument under two judges".
    """
    found = orders.examine(_six())

    assert len(found["agreement"]) == 15
    inside = [pair for pair in found["agreement"] if pair["kind"] == "same_instrument"]
    assert len(inside) == 3
    assert all(pair["same_judge"] is False for pair in inside), (
        "an instrument compared with itself under one judge is a table against itself"
    )
    assert sum(pair["kind"] != "same_instrument" for pair in found["agreement"]) == 12
    assert {band["kind"] for band in found["bands"]} == {
        "same_instrument",
        "one/two",
        "one/three",
        "three/two",
    }
    assert sum(band["pairs"] for band in found["bands"]) == 15


def test_dominance_is_asked_of_every_column_of_every_instrument():
    """Pooled and per instrument, because the pooled figure is partly mechanical.

    More legs make dominance harder whatever the models do, so a bare "nothing
    is separated" would be read as a finding about the models when part of it
    is arithmetic. The control is the same statistic at fewer legs.
    """
    down = {"alpha": 0.9, "beta": 0.5, "gamma": 0.1}
    up = {"alpha": 0.1, "beta": 0.5, "gamma": 0.9}
    first = _table("one", "judge-a", {"one_a": 3}, {s: {"one_a": v} for s, v in down.items()})
    second = _table("one", "judge-b", {"one_a": 3}, {s: {"one_a": v} for s, v in down.items()})
    other = _table("two", "judge-a", {"two_a": 3}, {s: {"two_a": v} for s, v in up.items()})

    found = orders.examine([first, second, other])
    pooled = found["dominance"]["pooled"]

    assert pooled["legs"] == 3, "one column on each of the three tables"
    assert pooled["pairs"] == 6, "three systems make six ordered pairs"
    assert pooled["dominating"] == 0, (
        "every system that wins on the first instrument loses on the second, so pooling "
        "them must separate nobody"
    )
    inside = found["dominance"]["per_instrument"]["one"]
    assert inside["dominating"] == 3, (
        "inside the instrument the order is a ladder and every pair is separated"
    )
    assert inside["legs"] == 2, "one column under each of that instrument's two judges"


def test_one_column_name_on_two_instruments_is_refused():
    """Pooling them would compare two different measures under one key.

    Loudly, because the alternative is a dominance count quietly computed over
    a column that means one thing on one table and another on the next.
    """
    values = {"alpha": {"shared": 0.9}, "beta": {"shared": 0.5}, "gamma": {"shared": 0.1}}
    first = _table("one", "judge-a", {"shared": 3}, values)
    second = _table("two", "judge-a", {"shared": 3}, values)

    with pytest.raises(ValueError, match="used by both"):
        orders.examine([first, second])


def test_the_sensitivity_is_the_same_twice():
    """Nothing here is resampled, so nothing here may move between runs.

    The jackknife is every band's range with each system left out in turn. It
    answers "does this depend on one model" and not "is this distinguishable
    from zero"; what it must not do is give two answers to the same question.
    """
    first = orders.examine(_six())
    second = orders.examine(_six())

    assert first["jackknife"]["rule"] == "leave_one_system_out"
    assert first["jackknife"]["refits"] == len(first["population"])
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_the_top_group_counts_instruments_and_not_tables():
    """`docs/edges-<track>.json` tests both judges at once.

    The same layer is drawn on both of that track's tables, so counting it per
    table would count one test twice and offer a reader a resolution the
    evidence does not have -- a system undominated under one judge and not the
    other, which that artefact cannot express.
    """
    tables = [
        _ladder(track, judge, MODELS, tested=("alpha", "beta"))
        for track in ("one", "two", "three")
        for judge in ("judge-a", "judge-b")
    ]

    found = orders.examine(tables)

    assert found["tables"] == 6, "six tables were drawn"
    assert found["instruments"] == 3
    assert found["instruments_tested"] == ["one", "three", "two"]
    assert found["undominated"]["alpha"] == 3, "three instruments, not six tables"
    assert found["undominated"]["delta"] == 0


def test_an_artefact_that_no_longer_describes_the_tables_is_refused():
    """The guard `edges.load` does not have.

    Rebuilding this costs nothing -- pure arithmetic over the published rows,
    no cache, no seed -- so a profile drawn beside tables it was not computed
    from has no excuse. One rank out of place is enough to refuse it.
    """
    tables = _six()
    found = orders.examine(tables)

    assert orders.matches(found, tables)

    stale = json.loads(json.dumps(found))
    system = stale["orders"][0]["systems"][0]
    stale["orders"][0]["ranks"][system] += 1
    assert not orders.matches(stale, tables), "a stale artefact would have been drawn"
    assert not orders.matches(None, tables)
    assert not orders.matches(found, tables[:1]), "one table is not a profile"


def test_the_artefact_carries_numbers_and_names_and_no_prose():
    """Every sentence the page draws is written in the page.

    A wording kept in a data file can only be fixed by re-running a command,
    and it is text nobody proof-reads beside the paragraph it lands in. The
    longest string here is a system id or a table id.
    """
    found = orders.examine(_six())

    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for held in value.values():
                yield from strings(held)
        elif isinstance(value, list):
            for held in value:
                yield from strings(held)

    prose = [text for text in strings(found) if " " in text.strip()]
    assert not prose, f"the artefact carries a sentence: {prose}"


def test_the_committed_artefact_describes_the_committed_tables():
    """A profile that has gone stale fails here rather than on the site.

    This is only possible because the computation is free: no answer cache, no
    resampling, no seed. So the artefact can simply be rebuilt from the
    committed payload and compared, and there is no version of "it is expensive
    to check" to hide behind. Absent is allowed -- the section is not drawn
    without it -- and wrong is not.
    """
    from tnb import report

    if not report.DATA_PATH.exists():
        pytest.skip("no published payload in this checkout")
    found = orders.load()
    if found is None:
        pytest.skip("no orders artefact in this checkout")

    payload = json.loads(report.DATA_PATH.read_text(encoding="utf-8"))
    assert orders.matches(found, payload["tables"]), (
        "docs/orders.json was built from different tables than docs/leaderboard.json "
        "draws -- run `uv run tnb orders`"
    )
