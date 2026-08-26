"""The figures, checked against the artefacts they claim to be drawn from.

A figure is the most quotable thing this repository produces and the hardest to
check: a number in an SVG is a shape. So every figure is generated from
``docs/leaderboard.json`` and the saturation files, and these tests compare what
it prints with what those files say.

The first draft of figure 1 published "71 of 75 pairs" where the answer is 125.
It happened because the leaderboard calls a system ``mistral-large-v2 (TN-Eval,
2025)`` and the saturation file calls it ``mistral-large-v2``, so intersecting
the two name sets dropped three systems in silence. Nothing about that was
visible in the picture.
"""

from __future__ import annotations

import json
import re
import sys

import pytest

from tnb.config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tools"))

figures = pytest.importorskip("figures")

DOCS = REPO_ROOT / "docs"


@pytest.fixture(scope="module")
def data():
    if not (DOCS / "leaderboard.json").exists():
        pytest.skip("no published payload in this checkout")
    return figures.Data.load()


@pytest.fixture(scope="module")
def drawn(data) -> dict[str, str]:
    return {name: draw(data) for name, draw in figures.FIGURES.items()}


def numbers_in(svg: str, klass: str) -> list[str]:
    return re.findall(rf'class="{klass}"[^>]*>([^<]*)<', svg)


# --- the figures say what the files say ---------------------------------------


def test_the_pair_count_matches_the_saturation_files(data, drawn):
    """Figure 1's headline is two counts. Both come out of the bootstrap."""
    separable, agree = figures.agreeing_pairs(data, "tneval-soap", "completeness")

    bands_a, bands_b = data.bands(figures.JUDGE_A), data.bands(figures.JUDGE_B)
    names = sorted(set(bands_a) & set(bands_b))
    assert len(names) == 19, "every system is banded under both judges"
    assert 0 < agree <= separable <= len(names) * (len(names) - 1) // 2

    title = numbers_in(drawn["positions.svg"], "title")[0]
    assert f"{agree} of the {separable} pairs" in title


def test_every_system_the_table_holds_is_in_the_figure(data, drawn):
    """The name mismatch that produced "71 of 75" was invisible in the picture,
    so it is checked here rather than looked for there."""
    table = data.scores("tneval-soap", figures.JUDGE_A, "completeness")
    assert len(table) == 19

    labels = numbers_in(drawn["positions.svg"], "name")
    drawn_names = {re.sub(r"^\d+\.\s*", "", label) for label in labels}
    assert set(table) <= drawn_names, "a system in the table and not in the figure"


def test_the_bar_chart_prints_the_published_completeness(data, drawn):
    """Figure 4 is the one a reader will quote. Every bar's number is checked
    against `docs/leaderboard.json` to three decimals."""
    scores = data.scores("tneval-soap", figures.JUDGE_A, "completeness")
    printed = set(numbers_in(drawn["what-the-rubric-rewards.svg"], "value"))

    for name, value in scores.items():
        assert f"{value:.3f}" in printed, f"{name}'s figure is not on the chart"


def test_the_temporal_figure_prints_both_columns(data, drawn):
    past = data.scores("icare", figures.JUDGE_A, "temporal_past")
    ahead = data.scores("icare", figures.JUDGE_A, "temporal_next")
    svg = drawn["temporal.svg"]

    for name in past:
        assert f"{ahead[name]:.2f} → {past[name]:.2f}" in svg, f"{name} is missing a pair"

    assert min(past.values()) > 0.9, "the fixture assumption: looking back is near-total"
    assert min(ahead.values()) == 0.0, "and at least one model never looks forward"


def test_the_scatter_reports_the_rho_the_site_computed(data, drawn):
    """Not recomputed here. The site publishes it and the figure quotes it."""
    svg = drawn["coverage-against-invention.svg"]
    for judge in (figures.JUDGE_A, figures.JUDGE_B):
        rho = figures._rho("tneval-soap", "completeness", "faithfulness", data, judge)
        assert rho is not None
        assert f"{rho:+.3f}" in svg


# --- how they are drawn --------------------------------------------------------


def test_no_colour_is_written_outside_the_stylesheet(drawn):
    """A literal `#fcfcfb` ring put a white halo on every dot in dark mode.

    Every colour comes from a class so the whole set flips at once, and the
    `prefers-color-scheme` block is the only place a second value exists.
    """
    for name, svg in drawn.items():
        body = svg.split("</style>", 1)[1]
        literals = set(re.findall(r'(?:fill|stroke)="(#[0-9a-fA-F]{3,6})"', body))
        assert not literals, f"{name} paints {sorted(literals)} outside the stylesheet"


def test_every_figure_carries_both_themes(drawn):
    for name, svg in drawn.items():
        assert "prefers-color-scheme: dark" in svg, f"{name} has one theme"


def test_nothing_runs_off_the_canvas(drawn):
    """SVG does not wrap text: a caption that does not fit is simply gone off
    the edge, and it looks fine in the source. The first draft had a footnote
    1409px wide on a 900px page.
    """
    widths = {"note": 5.8, "sub": 6.4, "title": 8.6}
    for name, svg in drawn.items():
        canvas = int(re.search(r'width="(\d+)"', svg).group(1))
        for match in re.finditer(r'class="(note|title|sub)"[^>]*x="(-?\d+)"[^>]*>([^<]*)<', svg):
            klass, x, text = match.group(1), int(match.group(2)), match.group(3)
            estimate = x + len(text) * widths[klass]
            assert estimate <= canvas + 8, (
                f"{name}: a {klass} needs about {estimate:.0f}px on a {canvas}px canvas"
            )


def test_every_figure_names_where_its_numbers_came_from(drawn):
    """A figure travels further than the page it was made for."""
    for name, svg in drawn.items():
        assert "Source:" in svg, f"{name} does not say where it is from"
        assert "harness 0.2.0" in svg, f"{name} does not say which harness"


def test_a_figure_is_the_same_bytes_twice(data):
    """A figure that churns turns every regeneration into a diff nobody reads."""
    for name, draw in figures.FIGURES.items():
        assert draw(data) == draw(data), f"{name} is not deterministic"


def test_the_generator_is_not_part_of_the_package():
    """`tools/` is a reading of the results; `src/tnb` is the harness.

    A change to how a figure is drawn must not be able to fail `make test` for
    the harness or argue for a `harness_version` bump.
    """
    assert not (REPO_ROOT / "src" / "tnb" / "figures.py").exists()
    assert (REPO_ROOT / "tools" / "figures.py").exists()


def test_the_published_figures_are_current(data):
    """The SVGs in `docs/figures/` are what the generator produces today.

    They are committed, so a reader gets them without running anything -- which
    means they can go stale against the payload beside them.
    """
    directory = DOCS / "figures"
    if not directory.exists():
        pytest.skip("figures have not been generated in this checkout")

    for name, draw in figures.FIGURES.items():
        path = directory / name
        assert path.exists(), f"{name} has not been generated"
        assert path.read_text(encoding="utf-8") == draw(data), (
            f"{name} is stale — run `python tools/figures.py`"
        )


def test_the_payload_the_figures_read_is_the_one_the_site_publishes():
    """One source, so a figure and the page cannot disagree."""
    payload = json.loads((DOCS / "leaderboard.json").read_text(encoding="utf-8"))
    assert payload["generated_from"] == "rows.jsonl"
