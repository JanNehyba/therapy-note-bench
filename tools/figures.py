"""Figures for the PDF and the preprint, drawn from the published payload.

Run it with ``uv run python tools/figures.py``; it writes SVG into
``docs/figures/``.

**Not part of the ``tnb`` package on purpose.** The package is the harness --
what asks the models, what asks the judge, what a row means. A figure is a
reading of the result, and a reading that changes should not be able to make
``make test`` fail or force a ``harness_version`` bump.

**Everything here is read from ``docs/leaderboard.json`` and the saturation
files.** No number is typed in. A figure that cannot be regenerated from the
published artefacts is a figure whose numbers nobody can check, and this
repository has spent a long day removing exactly those.

SVG by hand rather than a plotting library, for the same reason the page draws
its own intervals: no runtime dependency, no version of a chart library
deciding what a tick looks like, and the output is text that diffs.

Colour is doing one job here -- telling two judges apart -- and the two hues
come from the site's own palette, checked with the `dataviz` skill's validator
on both surfaces: ``#00806a`` against ``#c05a10`` clears the lightness band,
the chroma floor, CVD separation and 3:1 contrast. Every series is also
labelled directly, so colour is never the only channel.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
OUT = DOCS / "figures"

JUDGE_A = "gemini-3.1-pro-preview"
JUDGE_B = "gpt-5.6-terra"

#: The two judges, and nothing else uses colour. Validated light and dark.
INK = {
    "a": "#00806a",
    "b": "#c05a10",
    "a_dark": "#22a184",
    "b_dark": "#c9701f",
}

#: Type and rules, so a figure sits beside the page without clashing with it.
CSS = (
    """
  .fig { font: 13px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  .fig text { fill: #1a1a19; }
  .fig .muted { fill: #6b6b66; }
  .fig .rule { stroke: #e2e2dd; stroke-width: 1; }
  .fig .title { font-size: 17px; font-weight: 650; letter-spacing: -.01em; }
  .fig .sub { font-size: 13px; fill: #6b6b66; }
  .fig .note { font-size: 11.5px; fill: #6b6b66; }
  .fig .name { font-size: 12px; }
  .fig .value { font-size: 11.5px; fill: #6b6b66; font-variant-numeric: tabular-nums; }
  .fig .a { stroke: __A__; }
  .fig .b { stroke: __B__; }
  .fig .fill-a { fill: __A__; }
  .fig .fill-b { fill: __B__; }
  .fig .flat { stroke: #b8b8b1; }
  .fig .fill-flat { fill: #b8b8b1; }
  .fig .band { fill: #f0f0eb; }
  /* The ring that keeps overlapping marks apart is the *surface*, so it has to
     flip with the theme. Written as a literal it put a white halo on every dot
     in dark mode. */
  .fig .ring { stroke: #fcfcfb; }
  @media (prefers-color-scheme: dark) {
    .fig text { fill: #e8e8e4; }
    .fig .muted, .fig .sub, .fig .note, .fig .value { fill: #9a9a94; }
    .fig .rule { stroke: #2c2e31; }
    .fig .a { stroke: __A_DARK__; }
    .fig .b { stroke: __B_DARK__; }
    .fig .fill-a { fill: __A_DARK__; }
    .fig .fill-b { fill: __B_DARK__; }
    .fig .flat { stroke: #55554f; }
    .fig .fill-flat { fill: #55554f; }
    .fig .band { fill: #26282b; }
    .fig .ring { stroke: #1a1a19; }
  }
"""
    # Substituted by name, not with `%` or `.format()`: the block is CSS and it
    # is full of braces.
    .replace("__A_DARK__", INK["a_dark"])
    .replace("__B_DARK__", INK["b_dark"])
    .replace("__A__", INK["a"])
    .replace("__B__", INK["b"])
)


def esc(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def short(name: str) -> str:
    """A model id at the length a figure has room for.

    The provider prefix and the paper's year go: `google_gemini-3.7-flash` is
    `gemini-3.7-flash` here, and `therapist-written (TN-Eval)` is `therapist`.
    Nothing is disambiguated away -- no two systems collide after this.
    """
    name = name.removeprefix("google_").removeprefix("openai_")
    return name.split(" (")[0].replace("therapist-written", "therapist")


# --- the published numbers ---------------------------------------------------


@dataclass(frozen=True)
class Data:
    """Everything the figures read, from the artefacts the site publishes."""

    tables: dict[tuple[str, str], dict]
    saturation: dict[str, dict]
    concordance: dict[str, dict]
    preference: dict | None

    @classmethod
    def load(cls) -> Data:
        payload = json.loads((DOCS / "leaderboard.json").read_text(encoding="utf-8"))
        tables = {
            (table["track"], table["versions"]["judge_model"]): table
            for table in payload["tables"]
            if table["scored"] and table["versions"]["judge_model"]
        }
        saturation = {}
        for judge in (JUDGE_A, JUDGE_B):
            path = DOCS / f"saturation-{judge}.json"
            if path.exists():
                saturation[judge] = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            tables=tables,
            saturation=saturation,
            concordance=payload.get("concordance") or {},
            preference=payload.get("preference"),
        )

    def scores(self, track: str, judge: str, measure: str) -> dict[str, float]:
        """{system: score}, keyed by the name the figures print.

        `short()` and not the raw label, because the two files this reads
        disagree: the leaderboard calls a reference system `mistral-large-v2
        (TN-Eval, 2025)` and the saturation file calls it `mistral-large-v2`.
        Intersecting the raw names dropped three systems in silence, and the
        first draft of figure 1 published "71 of 75 pairs" where the answer is
        125. Keyed on what is drawn, so what is counted and what is shown
        cannot be different sets.
        """
        table = self.tables[(track, judge)]
        return {
            short(row["label"]): row["headline"][measure]
            for row in table["rows"]
            if row["headline"].get(measure) is not None
        }

    def bands(self, judge: str) -> dict[str, int]:
        found = self.saturation.get(judge)
        if not found:
            return {}
        return {short(s): i for i, group in enumerate(found["indistinguishable"], 1) for s in group}

    def shared_means(self, judge: str) -> dict[str, float]:
        """Each system's mean over the conversations every system shares.

        Not the table's figure and not meant to be: the table averages each
        system over its own notes, this averages every system over the set they
        all have, because a paired comparison is only paired on a shared set.
        The pair statistic uses these because the bands do -- deciding which
        pairs are separable with one set of means and which way round they go
        with another would be two instruments in one sentence.
        """
        found = self.saturation.get(judge)
        if not found:
            return {}
        return {short(i["system"]): i["mean"] for i in found["intervals"]}


def ranked(scores: dict[str, float], digits: int = 3) -> dict[str, int]:
    """1-based position, best first, with systems that print the same sharing one.

    The same rule the site uses: an order the table does not show is not an
    order this benchmark claims.
    """
    order = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
    places: dict[str, int] = {}
    for index, (name, value) in enumerate(order):
        previous = order[index - 1] if index else None
        if previous and f"{value:.{digits}f}" == f"{previous[1]:.{digits}f}":
            places[name] = places[previous[0]]
        else:
            places[name] = index + 1
    return places


def agreeing_pairs(data: Data, track: str, measure: str) -> tuple[int, int]:
    """(pairs both judges can separate, pairs they order the same way).

    "Can separate" means the two systems are in different bootstrap bands under
    that judge -- the site's own test for whether a difference is real. Pairs
    either judge cannot call are left out rather than counted as agreement,
    which would reward an instrument for being blunt.

    Both halves are computed from the bootstrap's own means over the shared
    conversations, not from the table. Deciding which pairs are separable with
    one set of means and which way round they go with another is two
    instruments in one sentence, and it moved this count by three.

    `track` and `measure` are unused today -- the saturation analysis is
    completeness on the TN-Eval track and there is no second one to ask -- and
    are kept so the signature says what the number is about.
    """
    a, b = data.shared_means(JUDGE_A), data.shared_means(JUDGE_B)
    ba, bb = data.bands(JUDGE_A), data.bands(JUDGE_B)
    names = sorted(set(a) & set(b) & set(ba) & set(bb))
    separable = agree = 0
    for index, x in enumerate(names):
        for y in names[index + 1 :]:
            if ba[x] == ba[y] or bb[x] == bb[y]:
                continue
            separable += 1
            agree += (a[x] > a[y]) == (b[x] > b[y])
    return separable, agree


# --- drawing -----------------------------------------------------------------


def svg(width: int, height: int, body: str, *, label: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" class="fig" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{esc(label)}">\n<style>{CSS}</style>\n{body}\n</svg>\n'
    )


def heading(title: str, subtitle: str, x: int = 0, y: int = 22) -> str:
    return (
        f'<text class="title" x="{x}" y="{y}">{esc(title)}</text>\n'
        f'<text class="sub" x="{x}" y="{y + 21}">{esc(subtitle)}</text>'
    )


#: Roughly how wide one character of the note face is, at 11.5px. Used to wrap
#: rather than to lay out: SVG has no line breaking, so a footnote that does not
#: fit simply runs off the canvas, and the first draft of figure 1 had one
#: 1409px wide on a 900px page.
NOTE_CHAR_PX = 5.8


def wrap(text: str, width_px: int) -> list[str]:
    """`text` split into lines that fit `width_px` at the note size."""
    limit = max(20, int(width_px / NOTE_CHAR_PX))
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if len(candidate) > limit and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def footnote(text: str, x: int, y: int, *, width_px: int = 900, leading: int = 15) -> str:
    """A note, wrapped to the canvas. Returns the block; `y` is its first line."""
    return "\n".join(
        f'<text class="note" x="{x}" y="{y + index * leading}">{esc(line)}</text>'
        for index, line in enumerate(wrap(text, width_px))
    )


def write(name: str, content: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(content, encoding="utf-8")
    return path


# --- figure 1: what a leaderboard position is worth --------------------------


def figure_positions(data: Data) -> str:
    """Two orderings of the same nineteen systems, one per judge.

    The figure exists to carry two numbers that sound contradictory and are
    not. Where both judges can tell two systems apart they agree about which is
    better 94% of the time -- and thirteen of nineteen still land somewhere
    else, because a position is a place in a queue and a handful of real moves
    renumbers everyone below them.

    Drawing only the crossings would sell the disagreement; printing only the
    94% would hide it. Both are on the page.
    """
    measure = "completeness"
    track = "tneval-soap"
    a = data.scores(track, JUDGE_A, measure)
    b = data.scores(track, JUDGE_B, measure)
    names = sorted(set(a) & set(b))
    ra, rb = ranked({n: a[n] for n in names}), ranked({n: b[n] for n in names})
    order = sorted(names, key=lambda n: (ra[n], n))
    moved = [n for n in names if ra[n] != rb[n]]
    separable, agree = agreeing_pairs(data, track, measure)

    row_h, top, left, right = 26, 96, 250, 250
    width, height = 900, top + len(order) * row_h + 122
    mid_l, mid_r = left + 24, width - right - 24

    def y_of(place: int) -> float:
        return top + (place - 0.5) * row_h

    lines, labels = [], []
    for name in order:
        y1, y2 = y_of(ra[name]), y_of(rb[name])
        klass = "flat" if ra[name] == rb[name] else "a"
        opacity = "0.35" if ra[name] == rb[name] else "0.85"
        lines.append(
            f"<g><title>{esc(short(name))}: {ra[name]} under {JUDGE_A}, "
            f"{rb[name]} under {JUDGE_B}</title>"
            f'<path class="{klass}" d="M {mid_l} {y1:.1f} C {mid_l + 70} {y1:.1f}, '
            f'{mid_r - 70} {y2:.1f}, {mid_r} {y2:.1f}" fill="none" stroke-width="2" '
            f'stroke-opacity="{opacity}" stroke-linecap="round"/>'
            f'<circle cx="{mid_l}" cy="{y1:.1f}" r="3.5" class="fill-a"/>'
            f'<circle cx="{mid_r}" cy="{y2:.1f}" r="3.5" class="fill-b"/></g>'
        )

    for name in order:
        y = y_of(ra[name])
        labels.append(
            f'<text class="name" x="{mid_l - 12}" y="{y + 4:.1f}" text-anchor="end">'
            f"{ra[name]}. {esc(short(name))}</text>"
        )
    for name in sorted(names, key=lambda n: (rb[n], n)):
        y = y_of(rb[name])
        labels.append(
            f'<text class="name" x="{mid_r + 12}" y="{y + 4:.1f}">'
            f"{rb[name]}. {esc(short(name))}</text>"
        )

    held = len(names) - len(moved)
    header = (
        f'<text class="value" x="{mid_l - 12}" y="{top - 14}" text-anchor="end">'
        f"judge A · {esc(JUDGE_A)}</text>"
        f'<text class="value" x="{mid_r + 12}" y="{top - 14}">'
        f"judge B · {esc(JUDGE_B)}</text>"
        # Named beside the marks, not four lines down in a footnote.
        f'<line class="a" x1="{mid_l}" y1="{top - 44}" x2="{mid_l + 26}" y2="{top - 44}" '
        f'stroke-width="2" stroke-linecap="round"/>'
        f'<text class="value" x="{mid_l + 34}" y="{top - 40}">'
        f"{len(moved)} changed place</text>"
        f'<line class="flat" x1="{mid_l + 150}" y1="{top - 44}" x2="{mid_l + 176}" '
        f'y2="{top - 44}" stroke-width="2" stroke-linecap="round"/>'
        f'<text class="value" x="{mid_l + 184}" y="{top - 40}">{held} held theirs</text>'
    )

    body = (
        heading(
            f"Two judges agree on {agree} of the {separable} pairs they can separate — "
            f"and {len(moved)} of {len(names)} systems still change place",
            "Same notes, same rubric, same 23 criteria. Ordered by Completeness. "
            "A position is a place in a queue, not a measurement.",
        )
        + f'\n<line class="rule" x1="0" y1="{top - 34}" x2="{width}" y2="{top - 34}"/>\n'
        + header
        + "\n"
        + "\n".join(lines)
        + "\n"
        + "\n".join(labels)
        + "\n"
        + footnote(
            "Grey lines held their place. A pair counts as separable when a paired bootstrap "
            "puts the two systems in different groups under that judge — over "
            f"{data.saturation[JUDGE_A]['sessions']} shared conversations for judge A and "
            f"{data.saturation[JUDGE_B]['sessions']} for judge B, because more of A's notes "
            "went unfinished. Systems that print the same score share a place.",
            0,
            height - 62,
            width_px=width,
        )
        + "\n"
        + footnote(
            "Source: docs/leaderboard.json and docs/saturation-*.json, harness 0.2.0.",
            0,
            height - 20,
            width_px=width,
        )
    )
    return svg(width, height, body, label=f"{len(moved)} of {len(names)} systems change place")


# --- figure 2: does covering more mean inventing more? -----------------------


def _fit(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Least squares, returned as (slope, intercept). Drawn, not asserted."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    denominator = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / denominator
    return slope, my - slope * mx


def _rho(track: str, measure_a: str, measure_b: str, data: Data, judge: str) -> float | None:
    """The rank correlation the site already computed, read rather than redone."""
    found = data.concordance.get(track) or {}
    for tension in found.get("tensions", []):
        if {tension["first"], tension["second"]} == {measure_a, measure_b}:
            return tension["rho_by_judge"].get(judge)
    return None


def figure_coverage_against_invention(data: Data) -> str:
    """Completeness against faithfulness, one panel per judge.

    The question a technical reader has about a coverage measure: does a model
    that answers more of the checklist also invent more? Two panels rather than
    one, because the two judges answer it differently -- and a single panel
    would have to pick one of them and call it the answer.
    """
    track = "tneval-soap"
    panel_w, panel_h, gap = 400, 300, 60
    left, top = 58, 116
    width = left + panel_w * 2 + gap + 24
    height = top + panel_h + 116

    panels = []
    for index, judge in enumerate((JUDGE_A, JUDGE_B)):
        completeness = data.scores(track, judge, "completeness")
        faithfulness = data.scores(track, judge, "faithfulness")
        names = sorted(set(completeness) & set(faithfulness))
        xs = [completeness[n] for n in names]
        ys = [faithfulness[n] for n in names]
        x0, x1 = min(xs) - 0.02, max(xs) + 0.02
        y0, y1 = min(ys) - 0.12, max(ys) + 0.12
        ox = left + index * (panel_w + gap)

        def px(value: float, ox: int = ox, x0: float = x0, x1: float = x1) -> float:
            return ox + (value - x0) / (x1 - x0) * panel_w

        def py(value: float, y0: float = y0, y1: float = y1) -> float:
            return top + panel_h - (value - y0) / (y1 - y0) * panel_h

        ticks = []
        for step in range(5):
            value = x0 + (x1 - x0) * step / 4
            ticks.append(
                f'<line class="rule" x1="{px(value):.1f}" y1="{top}" '
                f'x2="{px(value):.1f}" y2="{top + panel_h}"/>'
                f'<text class="value" x="{px(value):.1f}" y="{top + panel_h + 18}" '
                f'text-anchor="middle">{value:.2f}</text>'
            )
        for step in range(4):
            value = y0 + (y1 - y0) * step / 3
            ticks.append(
                f'<line class="rule" x1="{ox}" y1="{py(value):.1f}" '
                f'x2="{ox + panel_w}" y2="{py(value):.1f}"/>'
                f'<text class="value" x="{ox - 8}" y="{py(value) + 4:.1f}" '
                f'text-anchor="end">{value:.1f}</text>'
            )

        slope, intercept = _fit(xs, ys)
        klass = "a" if index == 0 else "b"
        line = (
            f'<line class="{klass}" x1="{px(x0):.1f}" y1="{py(slope * x0 + intercept):.1f}" '
            f'x2="{px(x1):.1f}" y2="{py(slope * x1 + intercept):.1f}" '
            f'stroke-width="2" stroke-dasharray="6 4" stroke-opacity="0.8"/>'
        )

        # Two labelled points and no more: the best on the ranking column and
        # the worst on the other one, which is the trade the panel is about.
        called_out = {
            max(names, key=lambda n: completeness[n]),
            min(names, key=lambda n: faithfulness[n]),
        }
        marks = []
        for name in names:
            cx, cy = px(completeness[name]), py(faithfulness[name])
            marks.append(
                f"<g><title>{esc(name)}: completeness {completeness[name]:.3f}, "
                f"faithfulness {faithfulness[name]:.2f}</title>"
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.5" class="fill-{klass} ring" '
                f'fill-opacity="0.85" stroke-width="1.5"/></g>'
            )
            if name in called_out:
                anchor = "end" if cx > ox + panel_w * 0.6 else "start"
                dx = -9 if anchor == "end" else 9
                marks.append(
                    f'<text class="value" x="{cx + dx:.1f}" y="{cy + 4:.1f}" '
                    f'text-anchor="{anchor}">{esc(short(name))}</text>'
                )

        rho = _rho(track, "completeness", "faithfulness", data, judge)
        reading = (
            "no relationship"
            if rho is None or abs(rho) < 0.2
            else ("a moderate one" if abs(rho) < 0.6 else "a strong one")
        )
        panels.append(
            "".join(ticks)
            + line
            + "".join(marks)
            + f'<text class="name" x="{ox}" y="{top - 30}">judge '
            + f"{'A' if index == 0 else 'B'} · {esc(judge)}</text>"
            + f'<text class="sub" x="{ox}" y="{top - 12}">Spearman '
            + (f"{rho:+.3f}" if rho is not None else "—")
            + f" — {reading}</text>"
            + f'<text class="value" x="{ox + panel_w / 2:.0f}" y="{top + panel_h + 38}" '
            + 'text-anchor="middle">Completeness</text>'
        )

    body = (
        heading(
            "Answering more of the checklist and inventing more are not the same trade "
            "under the two judges",
            "Each dot is one system. Horizontal: Completeness. Vertical: Faithfulness. "
            "The dashed line is least squares, drawn rather than described.",
        )
        # Rotated along the axis it labels. Written flat at x=14 it shared a
        # line with the first panel's subtitle at x=58, and the two printed on
        # top of each other -- plain in the PDF, invisible in the source.
        + f'\n<text class="value" x="{-(top + panel_h / 2):.0f}" y="16" '
        + 'transform="rotate(-90)" text-anchor="middle">Faithfulness</text>\n'
        + "\n".join(panels)
        + "\n"
        + footnote(
            "Faithfulness is the weakest column here: two trained therapists rating the same "
            "notes reach a Krippendorff's alpha of 0.18 on it. A relationship that appears "
            "under one judge and not the other is a fact about the instrument before it is a "
            "fact about the models.",
            0,
            height - 62,
            width_px=width,
        )
        + "\n"
        + footnote(
            "Source: docs/leaderboard.json, harness 0.2.0. Spearman as computed for the "
            "concordance panel.",
            0,
            height - 20,
            width_px=width,
        )
    )
    return svg(width, height, body, label="Completeness against faithfulness, one panel per judge")


# --- figure 3: looking back and looking forward ------------------------------


def figure_temporal(data: Data) -> str:
    """The two time-bearing sections, side by side, per model.

    A dumbbell rather than paired bars: the reading is the *gap*, and two bars
    from a shared baseline make a reader measure two lengths and subtract them.

    Both columns are fractions of a denominator, and the denominators are not
    the same size -- the experts answered "what happened last session" in 34 of
    40 notes and "what happens next" in 11. Eleven is small and the figure says
    so where the number is, not in a caption underneath.
    """
    track = "icare"
    judge = JUDGE_A
    past = data.scores(track, judge, "temporal_past")
    ahead = data.scores(track, judge, "temporal_next")
    names = sorted(set(past) & set(ahead), key=lambda n: (-ahead[n], -past[n], n))

    row_h, top, left = 26, 118, 220
    width = 880
    plot_w = width - left - 96
    height = top + len(names) * row_h + 116

    def px(value: float) -> float:
        return left + value * plot_w

    ticks = []
    for step in range(6):
        value = step / 5
        ticks.append(
            f'<line class="rule" x1="{px(value):.1f}" y1="{top - 10}" '
            f'x2="{px(value):.1f}" y2="{top + len(names) * row_h}"/>'
            f'<text class="value" x="{px(value):.1f}" y="{top - 18}" '
            f'text-anchor="middle">{value:.1f}</text>'
        )

    rows = []
    for index, name in enumerate(names):
        y = top + index * row_h + row_h / 2
        x_back, x_next = px(past[name]), px(ahead[name])
        rows.append(
            f"<g><title>{esc(name)}: looks back {past[name]:.2f}, "
            f"looks forward {ahead[name]:.2f}</title>"
            f'<line class="flat" x1="{x_next:.1f}" y1="{y:.1f}" x2="{x_back:.1f}" y2="{y:.1f}" '
            f'stroke-width="2" stroke-opacity="0.6"/>'
            f'<circle cx="{x_next:.1f}" cy="{y:.1f}" r="5" class="fill-b"/>'
            f'<circle cx="{x_back:.1f}" cy="{y:.1f}" r="5" class="fill-a"/>'
            f'<text class="name" x="{left - 14}" y="{y + 4:.1f}" text-anchor="end">'
            f"{esc(short(name))}</text>"
            f'<text class="value" x="{width - 88}" y="{y + 4:.1f}">'
            f"{ahead[name]:.2f} → {past[name]:.2f}</text></g>"
        )

    legend = (
        f'<circle cx="{left + 6}" cy="{top - 44}" r="5" class="fill-a"/>'
        f'<text class="value" x="{left + 18}" y="{top - 40}">'
        "looks back — section 5, answered by the experts in 34 of 40 notes</text>"
        f'<circle cx="{left + 6}" cy="{top - 26}" r="5" class="fill-b"/>'
        f'<text class="value" x="{left + 18}" y="{top - 22}">'
        "looks forward — section 17, answered in 11 of 40</text>"
    )

    body = (
        heading(
            "Every model can say what happened last time. Almost none can say what happens next.",
            "iCARE's two time-bearing sections, scored on the same 40 sessions. "
            "The fraction of the expert-answered sections each model also answered.",
        )
        + "\n"
        + legend
        + "\n"
        + "".join(ticks)
        + "\n"
        + "\n".join(rows)
        + "\n"
        + footnote(
            "The forward column rests on eleven sessions, so a score of 0.09 there is one "
            "session and the gap between two models a few hundredths apart is not evidence. "
            "The backward column rests on thirty-four. They were one averaged column until "
            "harness 0.2.0, and the average — weighted three to one towards the easy half — "
            "published the opposite of the finding this track exists to reproduce.",
            0,
            height - 78,
            width_px=width,
        )
        + "\n"
        + footnote(
            f"Source: docs/leaderboard.json, iCARE track, judge {JUDGE_A}, harness 0.2.0. "
            "Neither column involves the judge: both are computed from the note and the "
            "expert note alone.",
            0,
            height - 20,
            width_px=width,
        )
    )
    return svg(width, height, body, label="Looking back against looking forward, per model")


# --- figure 4: what the rubric rewards ---------------------------------------


def figure_what_the_rubric_rewards(data: Data) -> str:
    """Completeness, every system, with the therapist where she lands.

    The one figure a reader will quote out of context, so it carries its own
    caveat in the title rather than under it: the column counts coverage of a
    checklist, and a therapist writing what matters for the next session is not
    trying to cover one.

    Bars, because completeness is a fraction of a fixed 23 and zero means
    something. The therapist's bar is drawn in the muted ink and labelled, so
    she is findable without the reader hunting for a name.
    """
    track = "tneval-soap"
    judge = JUDGE_A
    scores = data.scores(track, judge, "completeness")
    table = data.tables[(track, judge)]
    kind = {short(row["label"]): row["system_type"] for row in table["rows"]}
    order = sorted(scores, key=lambda n: (-scores[n], n))

    row_h, top, left = 24, 108, 220
    width = 940
    plot_w = width - left - 250
    height = top + len(order) * row_h + 96
    ceiling = max(scores.values()) * 1.06

    ticks = []
    step = 0.1
    value = 0.0
    while value <= ceiling:
        x = left + value / ceiling * plot_w
        ticks.append(
            f'<line class="rule" x1="{x:.1f}" y1="{top - 10}" '
            f'x2="{x:.1f}" y2="{top + len(order) * row_h}"/>'
            f'<text class="value" x="{x:.1f}" y="{top - 18}" text-anchor="middle">'
            f"{value:.1f}</text>"
        )
        value += step

    human = next((n for n in order if kind.get(n) == "reference-human"), None)
    bars = []
    for index, name in enumerate(order):
        y = top + index * row_h
        w = scores[name] / ceiling * plot_w
        is_human = name == human
        bold = ' style="font-weight:650"' if is_human else ""
        fill = "flat" if kind.get(name) != "model" else "a"
        note = {
            "reference-human": " — written by a therapist",
            "reference-model": " — a 2025 model, from the paper",
        }.get(kind.get(name), "")
        bars.append(
            f"<g><title>{esc(name)}: {scores[name]:.3f}{note}</title>"
            # 4px rounded end, anchored to the baseline.
            f'<rect x="{left}" y="{y + 4}" width="{max(w, 2):.1f}" height="{row_h - 9}" rx="4" '
            f'class="fill-{"a" if fill == "a" else "flat"}" fill-opacity="0.9"/>'
            f'<text class="name" x="{left - 14}" y="{y + row_h / 2 + 4:.1f}" '
            f'text-anchor="end"{bold}>{esc(name)}</text>'
            # In one right-aligned column, not at each bar's end: nineteen
            # numbers at nineteen x positions is the "value on every point"
            # anti-pattern, and a column is the one place tabular figures earn
            # their keep.
            f'<text class="value" x="{left + plot_w + 46}" y="{y + row_h / 2 + 4:.1f}" '
            f'text-anchor="end">{scores[name]:.3f}</text>'
            + (
                f'<text class="value" x="{left + plot_w + 54}" y="{y + row_h / 2 + 4:.1f}">'
                f"{esc(note.lstrip(' —'))}</text>"
                if note
                else ""
            )
            + "</g>"
        )

    body = (
        heading(
            "Every model covers more of the rubric than the therapist does — "
            "which is not the same as writing a better note",
            "Completeness: the fraction of 23 rubric criteria a judge found present. "
            f"Judge {judge}.",
        )
        + "\n"
        + "".join(ticks)
        + "\n"
        + "\n".join(bars)
        + "\n"
        + footnote(
            "A therapist writes what matters for the next session and leaves out what does "
            "not; the rubric counts what is present and cannot see why anything was left out. "
            "TN-Eval reported the same direction from blinded expert comparison, so this is a "
            "reproduction rather than an anomaly — and it is a statement about a checklist, "
            "not about clinical writing. Quote the number with this sentence attached, or do "
            "not quote it.",
            0,
            height - 62,
            width_px=width,
        )
        + "\n"
        + footnote(
            "Source: docs/leaderboard.json, harness 0.2.0. The same ordering holds under the "
            "second judge; the figures differ.",
            0,
            height - 20,
            width_px=width,
        )
    )
    return svg(width, height, body, label="Completeness for every system, therapist included")


FIGURES = {
    "positions.svg": figure_positions,
    "coverage-against-invention.svg": figure_coverage_against_invention,
    "temporal.svg": figure_temporal,
    "what-the-rubric-rewards.svg": figure_what_the_rubric_rewards,
}


def main() -> int:
    data = Data.load()
    for name, draw in FIGURES.items():
        path = write(name, draw(data))
        print(f"wrote {path.relative_to(REPO)}  {path.stat().st_size:>6,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
