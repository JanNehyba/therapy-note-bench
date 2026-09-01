"""Which band boundaries rest on a comparison the bootstrap cannot call.

`indistinguishable` separates two systems when one beats the other in at least
0.95 of resamples. That fraction is a mean of `BOOTSTRAP_SAMPLES` Bernoulli
draws and carries a standard error of its own -- 0.0049 at the cut with 2000 of
them. A comparison landing at 0.9505 is a tenth of one away, and which side of
the threshold the truth lies on is not something this measurement answers.

Published today: seven such comparisons under `gemini-3.1-pro-preview` and five
under `gpt-5.6-terra`. Flipping the worst of the seven moves thirteen of
nineteen systems into a different band.

Two things this must not become.

It must not be read as instability of the estimate. Drawing 20 000 and 200 000
samples instead of 2 000 moves no system between bands under either judge, so
the answer is not a bigger budget -- and reporting how far `beats` wanders
between seeds, which is what a first attempt measured, publishes the
estimator's own imprecision as though it were uncertainty about the models.

And the denominator must stay honest. The grouping walks best-first and puts
each system in the first group none of whose members beat it, so it only ever
reads `beats[earlier][later]`: 171 comparisons among nineteen systems, not the
342 ordered pairs the matrix holds.
"""

from __future__ import annotations

import json
import math

from tnb import report
from tnb.scoring import saturation


def _interval(system: str, mean: float) -> saturation.Interval:
    return saturation.Interval(
        system=system, mean=mean, low=mean - 0.05, high=mean + 0.05, sessions=25, own_sessions=25
    )


def _ladder(*values: float) -> tuple[list[saturation.Interval], dict[str, dict[str, float]]]:
    """Systems in descending order, and a beats matrix that separates all of them."""
    names = [f"s{index}" for index, _ in enumerate(values)]
    intervals = [_interval(name, value) for name, value in zip(names, values, strict=True)]
    beats = {
        a: {b: (0.999 if values[i] > values[j] else 0.001) for j, b in enumerate(names) if a != b}
        for i, a in enumerate(names)
    }
    return intervals, beats


def test_only_the_comparisons_the_rule_can_make_are_counted():
    """The matrix holds both directions; the grouping asks one of them."""
    intervals, beats = _ladder(0.9, 0.8, 0.7, 0.6)
    found = saturation.near_the_cut(intervals, beats)
    assert found["comparisons"] == 6, (
        "four systems give six comparisons the rule can make and twelve ordered pairs; "
        f"it counted {found['comparisons']}"
    )


def test_a_comparison_far_from_the_cut_is_not_listed():
    intervals, beats = _ladder(0.9, 0.8, 0.7)
    found = saturation.near_the_cut(intervals, beats)
    assert found["pairs"] == [], "a comparison at 0.999 was called close to 0.95"
    assert found["unplaced"] == []


def test_a_comparison_on_the_cut_is_listed_with_its_distance():
    intervals, beats = _ladder(0.9, 0.8, 0.7)
    beats["s0"]["s1"] = 0.9505
    found = saturation.near_the_cut(intervals, beats)
    assert [pair["beats"] for pair in found["pairs"]] == ["s0"]
    pair = found["pairs"][0]
    assert pair["loses"] == "s1"
    # The distance is in units of the estimate's own error, not in raw points:
    # 0.0005 means one thing at 2000 draws and another at 200 000.
    error = math.sqrt(0.9505 * (1 - 0.9505) / saturation.BOOTSTRAP_SAMPLES)
    assert pair["sigmas"] == round(0.0005 / error, 2)
    assert found["error"] == round(math.sqrt(0.95 * 0.05 / saturation.BOOTSTRAP_SAMPLES), 4)


def test_the_rows_a_flip_would_move_are_counted_with_their_cascade():
    """Merging two bands shifts every band after them, and the count must say so."""
    intervals, beats = _ladder(0.9, 0.8, 0.7, 0.6)
    beats["s0"]["s1"] = 0.9505
    found = saturation.near_the_cut(intervals, beats)
    moved = found["pairs"][0]["moves"]
    assert "s1" in moved, "the system that would join the band above is not counted"
    assert set(found["unplaced"]) == set(moved)
    assert len(moved) >= 3, (
        "only the pair itself was counted; collapsing a band moves everything below it "
        f"as well, and this reported {moved}"
    )


def test_a_flip_that_changes_nothing_is_reported_as_changing_nothing():
    """A near-cut comparison is not automatically a fragile band.

    Two systems already inseparable for another reason can have a borderline
    comparison between them that decides nothing. Reporting them as unplaced
    would name rows the measurement does place.
    """
    intervals, beats = _ladder(0.9, 0.8, 0.7)
    # s0 does not separate s1 either way: s1 is already grouped with s0 by the
    # first comparison the rule reads.
    beats["s0"]["s1"] = 0.5
    beats["s0"]["s2"] = 0.9505
    found = saturation.near_the_cut(intervals, beats)
    assert [pair["moves"] for pair in found["pairs"]] == [[]], (
        "a comparison that decides no band was reported as one that does"
    )
    assert found["unplaced"] == []


def test_widening_the_window_never_names_fewer_systems():
    """Raising the window is the safe direction: it names more, never fewer."""
    intervals, beats = _ladder(0.9, 0.8, 0.7, 0.6)
    beats["s0"]["s1"] = 0.9605
    narrow = saturation.near_the_cut(intervals, beats, sigmas=1.0)
    wide = saturation.near_the_cut(intervals, beats, sigmas=5.0)
    assert set(narrow["unplaced"]) <= set(wide["unplaced"])
    assert len(narrow["pairs"]) <= len(wide["pairs"])


def test_the_published_analyses_carry_it_and_agree_with_their_own_bands():
    """The artefact, not a fixture. Every named system must be in the table."""
    for path in sorted(report.DOCS_DIR.glob("saturation-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        found = data.get("near_the_cut")
        assert found, f"{path.name} carries no statement about its own boundary"
        systems = {interval["system"] for interval in data["intervals"]}
        assert set(found["unplaced"]) <= systems, (
            "a system is named as unplaced that this analysis does not contain"
        )
        assert found["samples"] == data["bootstrap"]["samples"]
        n = len(systems)
        assert found["comparisons"] == n * (n - 1) // 2, (
            "the denominator counts ordered pairs; the grouping never asks the reverse "
            "direction, so half of them are comparisons it cannot make"
        )
        for pair in found["pairs"]:
            assert abs(pair["value"] - found["threshold"]) < found["sigmas"] * math.sqrt(
                pair["value"] * (1 - pair["value"]) / found["samples"]
            ), f"{pair} is not within the window it was listed under"
            assert set(pair["moves"]) <= set(found["unplaced"])


def test_the_page_names_the_systems_its_bands_do_not_place():
    """A count with no names is not something a reader can act on."""
    payload = report.DATA_PATH
    if not payload.exists():
        return
    data = json.loads(payload.read_text(encoding="utf-8"))
    for table in data["tables"]:
        groups = table.get("groups")
        if not groups:
            continue
        assert groups.get("near_the_cut"), (
            f"{table['track']} draws a Band column and says nothing about what its edges rest on"
        )
