"""The mean of places, pinned on constructed cases where the right order is known."""

from __future__ import annotations

from tnb.scoring import composite

COLUMNS = (("x", 3), ("y", 2))


def _scores(**systems: tuple[float, float]) -> dict[str, dict[str, float]]:
    return {name: {"x": x, "y": y} for name, (x, y) in systems.items()}


def test_the_best_on_every_column_is_first_and_a_swap_is_a_tie():
    found = composite.order(_scores(a=(0.9, 4.0), b=(0.6, 2.0), c=(0.3, 3.0)), COLUMNS)
    systems = found["systems"]
    assert systems["a"] == {"place": 1, "mean_place": 1.0, "places": {"x": 1, "y": 1}}
    # b is 2nd on x and 3rd on y; c the other way round: one mean, one place.
    assert systems["b"]["mean_place"] == systems["c"]["mean_place"] == 2.5
    assert systems["b"]["place"] == systems["c"]["place"] == 2
    assert found["rule"] == "mean_place" and found["unplaced"] == {}


def test_places_are_competition_style():
    places = composite.competition_places({"a": 1.0, "b": 2.5, "c": 2.5, "d": 3.0})
    assert places == {"a": 1, "b": 2, "c": 2, "d": 4}


def test_two_figures_that_print_the_same_share_a_place():
    """A reader checks a place against the digits in front of them, so the
    place is made at the table's precision: 0.9742 and 0.9735 both print 0.974."""
    found = composite.order(_scores(a=(0.9742, 3.0), b=(0.9735, 3.0), c=(0.5, 3.0)), COLUMNS)
    assert found["systems"]["a"]["places"]["x"] == found["systems"]["b"]["places"]["x"] == 1
    assert found["systems"]["c"]["places"]["x"] == 3, "the shared place is the better one"
    assert found["systems"]["a"]["place"] == found["systems"]["b"]["place"] == 1


def test_a_system_missing_a_column_is_unplaced_and_named_and_moves_nobody_else():
    scores = _scores(a=(0.9, 4.0), b=(0.6, 2.0), c=(0.3, 3.0))
    del scores["b"]["y"]
    found = composite.order(scores, COLUMNS)
    assert found["unplaced"] == {"b": ["y"]}
    assert "b" not in found["systems"]
    # a and c are placed over the two systems that have every column: on x
    # b's value still counts for the places on that column (it exists there),
    # so c is 3rd on x and 2nd on y.
    assert found["systems"]["a"]["place"] == 1
    assert found["systems"]["c"]["places"] == {"x": 3, "y": 2}


def test_doubling_a_column_can_change_who_is_first_and_the_page_is_told():
    """A leads on x, B on y, and the equal-weight mean puts A first only
    because A's lead is one place wider. Count y twice and B is first; the
    sensitivity block names both, which is what a reader who weights y more
    heavily needs to see before trusting the order."""
    # x: a, c, d, b; y: b, d, a, c. Equal weights: a 2.0, b 2.5, d 2.5, c 3.0.
    scores = _scores(a=(0.9, 3.0), b=(0.3, 4.0), c=(0.7, 2.0), d=(0.5, 3.5))
    found = composite.sensitivity(scores, COLUMNS)
    assert found["baseline"] == {"first": ["a"], "second": ["b", "d"]}
    doubled_y = next(v for v in found["variants"] if v["name"] == "double:y")
    assert doubled_y["first"] == ["b"]
    assert doubled_y["moved"] >= 2 and doubled_y["furthest"] >= 1
    assert found["first_under_any"] == ["a", "b"]
    assert -1.0 <= doubled_y["rho"] <= 1.0


def test_removing_a_system_that_is_last_everywhere_reverses_nothing():
    """Places have no scale to be rescaled by: the row at the bottom of every
    column lifts every place above it by one and changes no pair's order. The
    min-max mean this replaces reversed 21 pairs on the same operation."""
    scores = _scores(a=(0.9, 3.0), b=(0.6, 4.0), c=(0.3, 2.0), ref=(0.05, 1.0))
    found = composite.sensitivity(scores, COLUMNS, reference=["ref"])
    models_only = next(v for v in found["variants"] if v["name"] == "models_only")
    assert models_only["dropped"] == ["ref"]
    assert models_only["reversed_pairs"] == 0
    assert models_only["rho"] == 1.0


def test_a_reference_row_in_the_middle_can_reverse_a_pair_and_it_is_counted():
    """The property the baseline does *not* have, reported rather than hidden:
    with `ref` placed between a and b on y, removing it closes a gap that the
    other column had made up, and a pair changes order."""
    scores = _scores(a=(0.9, 2.0), b=(0.8, 4.0), ref=(0.85, 3.0), c=(0.1, 1.0))
    baseline = composite.order(scores, COLUMNS)["systems"]
    assert baseline["a"]["place"] == baseline["b"]["place"], "tied with the reference in"
    found = composite.sensitivity(scores, COLUMNS, reference=["ref"])
    models_only = next(v for v in found["variants"] if v["name"] == "models_only")
    without = composite.order({k: v for k, v in scores.items() if k != "ref"}, COLUMNS)
    assert without["systems"]["a"]["place"] == without["systems"]["b"]["place"] == 1
    assert models_only["reversed_pairs"] == 0, "a tie becoming a tie is not a reversal"


def test_the_order_is_a_pure_function_of_its_inputs():
    scores = _scores(a=(0.9, 4.0), b=(0.6, 2.0), c=(0.3, 3.0))
    assert composite.order(scores, COLUMNS) == composite.order(scores, COLUMNS)
    assert composite.sensitivity(scores, COLUMNS) == composite.sensitivity(scores, COLUMNS)


def test_a_place_never_looks_like_a_measure():
    """The payload keys are places, not values: nothing here is a `headline`."""
    found = composite.order(_scores(a=(0.9, 4.0), b=(0.6, 2.0)), COLUMNS)
    for entry in found["systems"].values():
        assert set(entry) == {"place", "mean_place", "places"}
        assert isinstance(entry["place"], int)
