"""The Czech briefing's four figures, checked against the files they are drawn from.

The same problem `tests/test_figures.py` exists for -- a number in an SVG is a
shape, and nothing about a wrong one is visible in the picture -- with one more
reason here. `tools/czech_crosscheck.py` compares the set of figures on the page
against the set in the PDF, and it drops chart text from both sides, because
`pdftotext` merges two numbers drawn close together into one token and reports a
difference that does not exist. So the crosscheck deliberately does not look
inside a chart. This file is what looks inside instead, and it compares what is
drawn with the payload rather than with itself.

The fifth rule is the one the English figures do not need: every figure is
rendered a second time in Czech. `_t` raises rather than falling back, so an
untranslated caption is a Czech build that stops -- and finding that here, at
the moment a figure is written, beats finding a hundred of them on the last
commit of the document.

Everything read here is under `local/`, which is gitignored, so the whole file
skips in a checkout that has not run the Czech track.
"""

from __future__ import annotations

import re
import sys
from statistics import fmean

import pytest

from tnb.config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tools"))

czech_figures = pytest.importorskip("czech_figures")
czech_brief = pytest.importorskip("czech_brief")
figures = pytest.importorskip("figures")


@pytest.fixture(scope="module")
def data():
    found = czech_figures.Data.load()
    if not found.rows:
        pytest.skip("no local Czech rows in this checkout")
    return found


@pytest.fixture(scope="module")
def drawn(data) -> dict[str, str]:
    return {
        name: draw(data, czech_figures.identity)
        for name, draw in czech_figures.CZECH_FIGURES.items()
    }


@pytest.fixture(scope="module")
def drawn_cs(data) -> dict[str, str]:
    """The same four in Czech. A missing translation raises here, not in a build."""
    before = czech_brief.LANG
    try:
        czech_brief.LANG = "cs"
        return {
            name: draw(data, czech_brief._t) for name, draw in czech_figures.CZECH_FIGURES.items()
        }
    finally:
        czech_brief.LANG = before


def _body(svg: str) -> str:
    """The drawing without its stylesheet, which is where the colours live."""
    return svg.split("</style>", 1)[-1]


def test_every_figure_draws_something(drawn):
    assert set(drawn) == set(czech_figures.CZECH_FIGURES)
    for name, svg in drawn.items():
        assert svg.startswith("<svg"), f"{name} drew nothing from this checkout"


# --- the fifth rule: it has to survive the Czech build ------------------------


def test_every_figure_renders_in_czech(drawn_cs):
    """The whole point of the fixture above: `czech_brief._t` raises
    `Untranslated` rather than falling back to English, so this test failing is
    a caption that would have stopped the Czech document.

    It is here rather than at the end of the work because a hundred missing
    sentences found on the last commit is a day, and four found on this one is
    an hour.
    """
    for name, svg in drawn_cs.items():
        assert svg.startswith("<svg"), f"{name} drew nothing in Czech"


def test_a_missing_czech_sentence_stops_the_figure_rather_than_leaking_english():
    """The guard the test above rests on. If `_t` ever gained a fallback, every
    Czech assertion in this file would pass while the figures printed English."""
    before = czech_brief.LANG
    try:
        czech_brief.LANG = "cs"
        with pytest.raises(czech_brief.Untranslated):
            czech_brief._t("a caption nobody has translated yet")
    finally:
        czech_brief.LANG = before


def test_the_generator_carries_no_czech():
    """`tools/czech_figures.py` is not on the diacritic scanner's allow-list and
    must never need to be: every sentence it draws lives in `czech_brief_cs`."""
    source = (REPO_ROOT / "tools" / "czech_figures.py").read_text(encoding="utf-8")
    assert source.isascii(), "a non-ASCII character reached the figure generator"


# --- how they are drawn -------------------------------------------------------


def test_no_colour_is_written_outside_the_stylesheet(drawn):
    """A literal `#fcfcfb` ring put a white halo on every dot in dark mode.

    Every colour comes from a class, so the whole set flips at once and the
    `prefers-color-scheme` block is the only place a second value exists.
    """
    for name, svg in drawn.items():
        literals = set(re.findall(r'(?:fill|stroke)="(#[0-9a-fA-F]{3,6})"', _body(svg)))
        assert not literals, f"{name} paints {sorted(literals)} outside the stylesheet"


def test_every_figure_carries_both_themes(drawn):
    for name, svg in drawn.items():
        assert "prefers-color-scheme: dark" in svg, f"{name} has one theme"


def test_nothing_runs_off_the_canvas(drawn, drawn_cs):
    """SVG does not wrap text: a caption that does not fit is simply gone off
    the edge, and it looks fine in the source.

    Both languages, which is not decoration. A title is not wrapped at all, and
    a Czech sentence is reliably longer than the English it replaces -- so the
    language that overflows first is the one this document is written in.
    """
    widths = {"note": 5.8, "sub": 6.4, "title": 8.6}
    for language, batch in (("en", drawn), ("cs", drawn_cs)):
        for name, svg in batch.items():
            canvas = int(re.search(r'width="(\d+)"', svg).group(1))
            for match in re.finditer(
                r'class="(note|title|sub)"[^>]*x="(-?\d+)"[^>]*>([^<]*)<', svg
            ):
                klass, x, text = match.group(1), int(match.group(2)), match.group(3)
                estimate = x + len(text) * widths[klass]
                assert estimate <= canvas + 8, (
                    f"{name} in {language}: a {klass} needs about {estimate:.0f}px "
                    f"on a {canvas}px canvas"
                )


def test_every_mark_is_inside_the_canvas(drawn, drawn_cs):
    """The other half of "nothing runs off the canvas": the drawing itself.

    A caption that overflows is caught above; a panel laid out past the bottom
    of the canvas is not, because it carries no text. Every dot and every rule
    is checked against the viewBox instead, in both languages, since a longer
    Czech heading can push a block down.

    The one exception is the rotated axis label, whose x is negative by
    construction -- `rotate(-90)` puts it up the left edge.
    """
    for language, batch in (("en", drawn), ("cs", drawn_cs)):
        for name, svg in batch.items():
            width = int(re.search(r'width="(\d+)"', svg).group(1))
            height = int(re.search(r'height="(\d+)"', svg).group(1))
            for element in re.finditer(r"<(circle|line)\b([^>]*)>", _body(svg)):
                attributes = dict(re.findall(r'(\w+)="(-?[\d.]+)"', element.group(2)))
                for key, limit in (
                    ("cx", width),
                    ("x1", width),
                    ("x2", width),
                    ("cy", height),
                    ("y1", height),
                    ("y2", height),
                ):
                    if key not in attributes:
                        continue
                    value = float(attributes[key])
                    assert -1 <= value <= limit + 1, (
                        f"{name} in {language}: a {element.group(1)} has {key}={value} "
                        f"on a {width} by {height} canvas"
                    )


def test_a_figure_is_the_same_bytes_twice(data):
    """A figure that churns turns every rebuild into a diff nobody reads."""
    for name, draw in czech_figures.CZECH_FIGURES.items():
        english = czech_figures.identity
        assert draw(data, english) == draw(data, english), f"{name} is not deterministic"


def test_every_figure_says_where_its_numbers_came_from(drawn):
    for name, svg in drawn.items():
        assert "Source:" in svg, f"{name} does not say where it is from"


# --- nothing here may be published --------------------------------------------


def test_no_czech_figure_is_a_published_figure():
    """`tests/test_figures.py` asserts that every entry in `figures.FIGURES`
    appears on a published page. These may never appear on one, so they are a
    separate set and the two must not overlap."""
    assert not set(czech_figures.CZECH_FIGURES) & set(figures.FIGURES)


def test_the_generator_never_writes_a_figure_to_disk():
    """`docs/figures/` is in version control and these are numbers from
    confidential clinical material. A figure that reaches disk is a figure that
    can reach a commit, so the generator has no way of putting one there."""
    source = (REPO_ROOT / "tools" / "czech_figures.py").read_text(encoding="utf-8")
    # The call, not the words. The module's own docstring says why it may not
    # write to `docs/figures/`, and a check that forbade the phrase would forbid
    # the explanation along with the act.
    for forbidden in ("write_text(", "write_bytes(", "figures.write", "open("):
        assert forbidden not in source, f"the generator can write: {forbidden}"

    for name in czech_figures.CZECH_FIGURES:
        assert not list((REPO_ROOT / "docs" / "figures").glob(f"{name}*")), (
            f"a Czech figure has been written into docs/figures as {name}"
        )


# --- what they say is what the files say ---------------------------------------


def test_the_formats_figure_counts_the_rows_rather_than_asserting_them(data, drawn):
    """The headline is two counts over four comparisons. Both are recounted here
    from the rows, so the sentence cannot drift from the drawing under it."""
    from tnb.scoring import czech as czech_scorer

    worse = compared = 0
    for soap_track, deepsy_track in czech_figures.FORMAT_PAIRS:
        for judge in data.judges(deepsy_track):
            soap = data.composite(soap_track, judge, czech_scorer.CRITERION_KEYS)
            deepsy = data.composite(deepsy_track, judge, czech_scorer.CRITERION_KEYS)
            shared = sorted(set(soap) & set(deepsy))
            if len(shared) < 3:
                continue
            worse += sum(1 for name in shared if deepsy[name] < soap[name])
            compared += len(shared)

    assert compared > 0, "the fixture needs at least one pair of tracks"
    title = re.findall(r'class="title"[^>]*>([^<]*)<', drawn["formats"])[0]
    assert czech_figures.FORMATS_TITLE.format(worse=worse, compared=compared) == title


def test_the_formats_figure_never_mixes_two_rubric_versions(data):
    """The local record holds both versions of the Czech criteria and
    `results.latest` keeps both, because the version is part of a row's
    identity. Taking whichever came last would put two instruments on one line.
    """
    from tnb.scoring import czech as czech_scorer

    versions = {row.judge_prompt_version for row in data.rows if row.track == "czech-real"}
    assert len(versions) > 1, "this checkout cannot show the failure this guards"

    newest = data.rubric("czech-real")
    assert newest == max(versions)
    drawn = data.composite("czech-real", data.judges("czech-real")[0], czech_scorer.CRITERION_KEYS)
    for name, value in drawn.items():
        rows = [
            row
            for row in data.rows
            if row.track == "czech-real"
            and row.system_id == name
            and row.judge_prompt_version == newest
            and row.judge_model == data.judges("czech-real")[0]
        ]
        assert len(rows) == 1
        expected = fmean(rows[0].metrics.headline[key] for key in czech_scorer.CRITERION_KEYS)
        assert value == pytest.approx(expected)


def test_the_external_figure_prints_the_coefficients_the_payload_holds(data, drawn):
    """Every rho and p on the figure comes out of `local/czech-external.json`.

    The crosscheck no longer compares a chart's numbers against the print, so
    this is the only place they are checked at all.
    """
    if not data.external.get("judges"):
        pytest.skip("no external comparison in this checkout")

    printed = drawn["external"]
    seen = 0
    for field, _title in czech_figures.EXTERNAL_PANELS:
        for judge in sorted(data.external["judges"]):
            entry = (data.external["judges"][judge].get(field) or {}).get("intelligence_index")
            if not entry:
                continue
            seen += 1
            assert (
                czech_figures.EXTERNAL_RHO.format(
                    rho=f"{entry['rho']:+.2f}", p=f"{entry['p']:.3f}", n=entry["n"]
                )
                in printed
            ), f"{judge} {field} is not on the figure"
    assert seen >= 2, "the comparison did not actually run"


def test_the_external_figure_names_the_models_it_could_not_match(data, drawn):
    """An absence is never a measurement: the models that could not be matched
    to a public index are named on the figure rather than quietly missing from
    it."""
    unmatched = data.external.get("unmatched") or []
    if not unmatched:
        pytest.skip("every model matched in this checkout")
    for name in unmatched:
        assert name in drawn["external"], f"{name} is absent and unnamed"


def test_the_join_figure_places_every_model_the_payload_holds(data, drawn):
    """The two columns are places, and a place is computed from the payload's
    own points here rather than read off the picture."""
    if not data.join.get("judges"):
        pytest.skip("no join payload in this checkout")

    checked = 0
    for judge in sorted(data.join["judges"]):
        found = data.join["judges"][judge].get("same_instrument") or {}
        english: dict[str, list[float]] = {}
        czech: dict[str, list[float]] = {}
        for key in czech_figures.QUALITY:
            for point in (found.get(key) or {}).get("points") or []:
                english.setdefault(point["system"], []).append(point["english"])
                czech.setdefault(point["system"], []).append(point["czech"])
        names = sorted(
            name
            for name in english
            if len(english[name]) == len(czech_figures.QUALITY)
            and len(czech.get(name, [])) == len(czech_figures.QUALITY)
        )
        if len(names) < 3:
            continue
        places_en = figures.ranked({name: fmean(english[name]) for name in names})
        places_cs = figures.ranked({name: fmean(czech[name]) for name in names})
        for name in names:
            short = figures.short(name)
            assert f"{places_en[name]}. {short}</text>" in drawn["join"]
            assert f"{places_cs[name]}. {short}</text>" in drawn["join"]
            checked += 1
    assert checked >= 9, f"only {checked} placements were checked"


def test_the_length_figure_draws_a_dot_for_every_model_with_both_numbers(data, drawn):
    """A model needs a length and a score to be a point. The count of marks is
    checked against the count of models that have both, so a model dropped by a
    silent name mismatch shows up here rather than as a thinner cloud."""
    from tnb.scoring import czech as czech_scorer

    expected = 0
    for track in czech_figures.LENGTH_TRACKS:
        lengths = ((data.length.get("czech") or {}).get(track) or {}).get("by_system") or {}
        if not lengths:
            continue
        for judge in data.judges(track):
            scores = data.composite(track, judge, czech_scorer.CRITERION_KEYS)
            shared = set(scores) & set(lengths)
            if len(shared) >= 3:
                expected += len(shared)
    if not expected:
        pytest.skip("no length payload in this checkout")

    # Two more circles than points: each panel carries one legend dot per judge.
    legend = 2 * len(czech_figures.LENGTH_TRACKS)
    assert drawn["length"].count("<circle") == expected + legend
