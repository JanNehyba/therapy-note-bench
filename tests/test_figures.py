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


# --- the briefing --------------------------------------------------------------


@pytest.fixture(scope="module")
def brief_html(data) -> str:
    brief = pytest.importorskip("brief")
    return brief.render(data)


def test_the_briefing_quotes_the_published_calibration(brief_html):
    """It prints the judge's agreement with two therapists. Those four figures
    come out of `docs/calibration.json`, so they cannot drift from the panel
    that shows the same table on the site."""
    calibration = json.loads((DOCS / "calibration.json").read_text(encoding="utf-8"))
    for entry in calibration["agreements"]:
        assert f"{entry['alpha']:.2f}" in brief_html
        assert f"{entry['alpha_humans']:.2f}" in brief_html
    assert f"{calibration['notes']} of those notes" in brief_html


def test_the_briefing_quotes_the_published_self_preference(data, brief_html):
    """The document's third headline claim is a measured effect, so every digit
    of it is checked against the file it came from."""
    effects = (data.preference or {}).get("effects") or []
    assert effects, "the fixture needs a self-preference panel"
    for entry in effects:
        assert f"{entry['estimate']:+.3f}" in brief_html
        assert f"{entry['low']:+.3f} to {entry['high']:+.3f}" in brief_html


def test_the_briefing_headline_matches_the_bootstrap(data, brief_html):
    separable, agree = figures.agreeing_pairs(data, "tneval-soap", "completeness")
    assert f"{agree}/{separable}" in brief_html
    assert f"in {agree} of {separable} pairs" in brief_html


def test_the_briefing_inlines_the_figures_it_uses(brief_html):
    """Inlined, not linked: an `<img src>` would leave the PDF depending on
    four files beside it.

    Four of the five. `room-left.svg` is on the methods page, beside the
    saturation panel whose analysis it draws.
    """
    brief = pytest.importorskip("brief")

    assert brief.BRIEF_FIGURES, "the document names the figures it uses"
    assert set(brief.BRIEF_FIGURES) <= set(figures.FIGURES), "and each one is generated"
    assert brief_html.count("<svg") == len(brief.BRIEF_FIGURES)
    assert "Figure missing" not in brief_html


def test_a_figure_the_briefing_does_not_use_is_on_a_page():
    """Otherwise it is a file nobody sees."""
    from tnb import report

    brief = pytest.importorskip("brief")
    unused = set(figures.FIGURES) - set(brief.BRIEF_FIGURES)
    assert unused == set(report.FIGURE_MARKERS.values()), (
        "every generated figure is either in the briefing or inlined into a page"
    )


def test_the_briefing_has_no_unrendered_placeholder(brief_html):
    """A conditional written inside an f-string is not a conditional — it is
    four words of literal text in the document, and that shipped once.

    Every `<style>` block is stripped first, including the four the figures
    bring with them: CSS is made of braces and the first version of this test
    found them all.
    """
    prose = re.sub(r"<style>.*?</style>", "", brief_html, flags=re.S)

    assert " if " not in re.sub(r"<[^>]+>", " ", prose).replace(" if you ", " ")
    for leak in ("{", "}"):
        assert leak not in prose, f"the body carries an unrendered {leak!r}"


def test_the_briefing_says_what_it_is_not(brief_html):
    """The one paragraph that must survive every edit: nothing here is a
    clinical validation."""
    assert "Nothing here is a clinical validation" in brief_html
    assert "lower bound on what you would have to check" in brief_html


def test_no_html_entity_survives_into_the_briefing_as_text():
    """`claim()` escapes its heading, so an `&ndash;` written there reaches the
    page as five letters. It did: the fourth card read `0.00&ndash;0.55`."""
    brief = pytest.importorskip("brief")
    html = brief.render(figures.Data.load())
    prose = re.sub(r"<svg.*?</svg>", " ", html, flags=re.S)
    prose = re.sub(r"<style>.*?</style>", "", prose, flags=re.S)
    visible = re.sub(r"<[^>]+>", " ", prose)

    assert not re.findall(r"&amp;[a-z]+;", visible), "an entity was escaped and printed"


def test_the_briefing_reports_saturation_from_the_published_analysis(brief_html, data):
    """Whether a benchmark still measures anything is the first question anybody
    who has watched one die will ask, and the counts were published before the
    document said a word about them."""
    saturation = data.saturation[figures.JUDGE_A]
    counts = saturation["verdict_counts"]
    total = len(saturation["criteria"])

    for verdict in ("saturated", "unreachable", "discriminating"):
        assert f"{counts[verdict]} of {total}" in brief_html, f"{verdict} is not reported"

    trace = {}
    for judge in (figures.JUDGE_A, figures.JUDGE_B):
        values = [
            row["headline"]["trace"]
            for row in data.tables[("icare", judge)]["rows"]
            if row["headline"].get("trace") is not None
        ]
        trace[judge] = (min(values), max(values))
        assert f"{min(values):.2f}" in brief_html and f"{max(values):.2f}" in brief_html

    # The claim rests on the range being small, so the fixture assumption is
    # asserted rather than assumed: if a future model breaks out of it, this
    # fails and the paragraph gets rewritten instead of quietly going wrong.
    for low, high in trace.values():
        assert (high - low) / 4 < 0.25, "TRACE has more room than the paragraph says"


# --- the anti-pattern catalogue, as far as it can be checked -----------------


def _body(svg: str) -> str:
    """The drawing without its stylesheet.

    Checking the whole file matches every class the stylesheet *defines*, which
    is how a check for "two inks and no legend" flagged a single-series chart.
    """
    return svg.split("</style>")[-1]


def test_no_marker_is_below_the_accessible_size(drawn):
    """8px across is the floor. The slopegraph's endpoints were 7."""
    for name, svg in drawn.items():
        radii = [float(r) for r in re.findall(r'<circle[^>]*r="([\d.]+)"', _body(svg))]
        assert all(r * 2 >= 8 for r in radii), f"{name} has a marker under 8px across"


def test_a_figure_with_two_inks_names_them(drawn):
    """A legend, or a direct label on each. Colour is never the only channel."""
    naming = ("judge A", "looks back", "separates models", "therapist", "2025 model")
    for name, svg in drawn.items():
        body = _body(svg)
        inks = {token for token in ("fill-a", "fill-b", "fill-flat", "v-") if token in body}
        if len(inks) > 1:
            assert any(word in body for word in naming), f"{name} has {inks} and names none"


def test_gridlines_are_solid(drawn):
    """Dashing reads as a threshold or a projection when it is just a grid."""
    for name, svg in drawn.items():
        assert not re.search(r'class="rule"[^>]*stroke-dasharray', _body(svg)), (
            f"{name} has a dashed gridline"
        )


def test_the_saturation_figure_groups_by_verdict(drawn, data):
    """Its palette clears CVD separation at 6.7 on the tritan axis in dark mode,
    which the skill allows only with a second channel.

    The groups supply two of the ones it names — a gap and a direct label —
    and reading by state is what the figure is about anyway.
    """
    svg = drawn["room-left.svg"]
    counts = data.saturation[figures.JUDGE_A]["verdict_counts"]

    for verdict, count in counts.items():
        if count:
            word = figures.VERDICT_INK[verdict][2]
            assert svg.count(word) >= 2, f"{verdict} is not named as a group and in the legend"
