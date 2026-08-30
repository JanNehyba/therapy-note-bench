"""The Czech briefing's four figures, checked against the files they are drawn from.

The same problem `tests/test_figures.py` exists for -- a number in an SVG is a
shape, and nothing about a wrong one is visible in the picture -- with one more
reason here. `tools/czech_crosscheck.py` compares the set of figures on the page
against the set in the PDF, and it drops chart text from both sides, because
`pdftotext` merges two numbers drawn close together into one token and reports a
difference that does not exist. So the crosscheck deliberately does not look
inside a chart. This file is what looks inside instead, and it compares what is
drawn with the payload rather than with itself.

The fifth rule is the one the English figures do not need: the figures have to
come out Czech in the Czech document. That is checked by **building the document
with the script that builds it**, not by calling the four functions from a test.
The difference is the whole reason this section was rewritten: the figures used
to fetch the translator with `from czech_brief import _t`, and a test that
imports `czech_brief` as a module is the one arrangement where that works. A
real build runs the file as a script, so it is `__main__`, that import loaded a
second copy whose language was still English, and all four charts printed
English inside the Czech document while every test here passed.

Everything read here is under `local/`, which is gitignored, so the whole file
skips in a checkout that has not run the Czech track.
"""

from __future__ import annotations

import ast
import html
import json
import re
import subprocess
import sys
from statistics import fmean

import pytest

from tnb.config import REPO_ROOT
from tnb.report import TRACK_SWITCH_LABELS

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


# --- the fifth rule: the figures of a real Czech build are Czech --------------

BRIEF = REPO_ROOT / "tools" / "czech_brief.py"
LOCAL_ROWS = REPO_ROOT / "local" / "czech-rows.jsonl"

#: How many models the document under test is built from. The figures read
#: `local/czech-rows.jsonl` themselves and are drawn in full whatever this is,
#: so cutting it costs the figures nothing. The tables are built from the source
#: given here, and the chapter that permutes models for a p-value is a minute
#: over all of them and eight seconds over five.
BUILD_SYSTEMS = 5

#: Czech letters no English word has. Enough to say a text node was translated;
#: not enough to say it was translated well, which is a reader's job.
CZECH_LETTERS = (
    "\u00e1\u010d\u010f\u00e9\u011b\u00ed\u0148\u00f3\u0159\u0161\u0165\u00fa\u016f\u00fd\u017e"
)


@pytest.fixture(scope="module")
def built_cs(tmp_path_factory) -> list[str]:
    """The figures of a Czech document, built by running the script.

    A subprocess, and that is the point rather than an accident: it is the
    arrangement the bug needed. `tools/czech_brief.py` becomes `__main__` here,
    exactly as it does for the person who runs it, so anything inside the build
    that reaches for that module by name gets a second, English copy.
    """
    if not LOCAL_ROWS.exists():
        pytest.skip("no local Czech rows in this checkout")
    rows = [
        json.loads(line) for line in LOCAL_ROWS.read_text(encoding="utf-8").splitlines() if line
    ]
    keep = sorted({row["system_id"] for row in rows})[:BUILD_SYSTEMS]

    work = tmp_path_factory.mktemp("czech-brief")
    source, target = work / "czech-rows.jsonl", work / "czech-brief-cs.html"
    source.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n" for row in rows if row["system_id"] in keep
        ),
        encoding="utf-8",
    )
    finished = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(BRIEF),
            "--language",
            "cs",
            "--source",
            str(source),
            "--target",
            str(target),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
    )
    assert finished.returncode == 0, finished.stdout + finished.stderr
    drawn = re.findall(r"<svg\b.*?</svg>", target.read_text(encoding="utf-8"), re.S)
    if not drawn:
        pytest.skip("this checkout has no payloads behind the figures")
    return drawn


def _said(svg: str) -> str:
    """Every word the figure prints, on one line.

    `figures.wrap` breaks a subtitle and a footnote into one `<text>` per line
    at whatever width fits, so a whole sentence is never a substring of the SVG.
    The text nodes rejoined in order are, and `wrap` splits on whitespace, so
    the same normalisation on both sides makes the two comparable.
    """
    nodes = re.findall(r"<text\b[^>]*>(.*?)</text>", svg, re.S)
    plain = " ".join(re.sub(r"<[^>]+>", " ", node) for node in nodes)
    return " ".join(html.unescape(plain).split())


def _longest_literal(text: str) -> str:
    """The longest run of a phrase that carries no `{placeholder}`.

    A template is never printed as written -- `"{worse} of {models} models score
    lower"` reaches the page with numbers in it -- so what is checked is the
    longest stretch that comes through `.format` unchanged.
    """
    return max(re.split(r"\{[^}]*\}", text), key=len).strip()


def _marker(english: str, czech: str) -> str | None:
    """The stretch of `english` whose presence on a figure means English.

    Two things disqualify a stretch. One is a `{placeholder}`, which is filled
    before the phrase is drawn. The other is the Czech itself: the translation
    of "Spearman {rho}, p {p}, {n} models" keeps the word Spearman, because a
    coefficient is named after a person in either language, so finding
    "Spearman" on a chart says nothing about which language it is in.

    `None` when nothing distinctive is left. That phrase is dropped rather than
    guessed at.
    """
    for piece in sorted(re.split(r"\{[^}]*\}", english), key=len, reverse=True):
        piece = piece.strip()
        if len(piece) >= 4 and piece not in czech:
            return piece
    return None


def _english_the_figures_draw() -> dict[str, str]:
    """Every English phrase the figures draw, against the mark that gives it away.

    Read out of the module, so a caption added tomorrow is swept without anybody
    remembering to add it here. Three sources, because the figures name their
    strings three ways: module constants, literals written straight into a
    `t(...)` call, and the track labels they borrow from `tnb.report`.

    A phrase with no Czech is dropped rather than failed: it would be a name
    that is written the same in both languages, and `_t` says so by raising.
    Nothing in the module is in that position today -- every phrase the figures
    draw has a twin -- so this is a branch held open for a name that has not
    been added yet rather than one the current data reaches.
    """
    found = {
        value
        for name, value in vars(czech_figures).items()
        if name.isupper() and isinstance(value, str)
    }
    tree = ast.parse((REPO_ROOT / "tools" / "czech_figures.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "t" or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            found.add(first.value)
    found |= set(TRACK_SWITCH_LABELS.values())

    before, wanted = czech_brief.LANG, {}
    try:
        czech_brief.LANG = "cs"
        for phrase in found:
            try:
                czech = czech_brief._t(phrase)
            except czech_brief.Untranslated:
                continue
            mark = _marker(phrase, czech)
            if mark:
                wanted[phrase] = mark
    finally:
        czech_brief.LANG = before
    return wanted


def test_a_real_build_draws_every_figure(built_cs):
    """Four charts in the document, or the sweep below is checking three."""
    assert len(built_cs) == len(czech_figures.CZECH_FIGURES)


def test_the_figures_of_a_real_build_are_in_czech(built_cs):
    """The finding this section exists for: the charts printed English.

    178 text nodes of it -- titles, subtitles, panel headings, axis labels,
    legends, footnotes and source lines -- under Czech figcaptions, in a
    document whose whole promise is that the caveats reach a Czech reader in
    Czech.
    """
    swept = _english_the_figures_draw()
    assert len(swept) >= 25, f"only {len(swept)} phrases were swept; the sweep found nothing"
    for index, svg in enumerate(built_cs):
        said = _said(svg)
        leaked = sorted(phrase for phrase, mark in swept.items() if mark in said)
        assert not leaked, f"figure {index} prints English: {leaked[:3]}"
        assert any(letter in said for letter in CZECH_LETTERS), (
            f"figure {index} carries no Czech letter at all"
        )


def test_a_real_build_prints_the_czech_title_of_every_figure(built_cs):
    """The other direction. Absent English is also what a chart that printed
    nothing would look like, so each title is looked for in the language it is
    supposed to be in."""
    titles = {
        html.unescape(title)
        for svg in built_cs
        for title in re.findall(r'class="title"[^>]*>([^<]*)<', svg)
    }
    before = czech_brief.LANG
    try:
        czech_brief.LANG = "cs"
        for name, english in (
            ("formats", czech_figures.FORMATS_TITLE),
            ("external", czech_figures.EXTERNAL_TITLE),
            ("join", czech_figures.JOIN_TITLE),
            ("length", czech_figures.LENGTH_TITLE),
        ):
            czech = _longest_literal(czech_brief._t(english))
            assert any(czech in title for title in titles), (
                f"the {name} figure does not print its Czech title"
            )
    finally:
        czech_brief.LANG = before


def test_a_missing_czech_sentence_stops_the_figure_rather_than_leaking_english():
    """The guard everything above rests on. If `_t` ever gained a fallback, the
    Czech assertions in this file would pass while the figures printed English
    -- which is exactly what happened, by a different route."""
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
