"""The four figures the Czech briefing draws, and nothing else draws.

`tools/figures.py` is the same job for the published pages, and everything here
builds on it: the stylesheet, the two inks, the heading, the footnote, the
wrapping and the ranking are its, so a Czech figure sets like an English one
and a change to the house style reaches both.

**Hand-written SVG, no plotting library.** The repository's rule, and the
practical reason is `tools/pdf.py`: inline SVG with its own `<style>` block is
the one thing that has been shown to survive the print with its type and its
colour intact. It is also text, so a figure diffs.

**Nothing here is ever written to a file.** `docs/figures/` is in version
control and these numbers come from confidential clinical material; a figure
that reaches disk is a figure that can reach a commit. They are rendered into
the document in memory and they live nowhere else. That is also why they are
not in `figures.FIGURES`: every entry there is asserted to be published, and
none of these may be.

**Every sentence goes through the translator the caller hands in.** Each
`draw_*` takes `(data, t)`; the document passes its own `_t`, which raises
rather than falling back, so a figure with an untranslated caption stops the
Czech build instead of printing English inside a Czech page. The translator is
a parameter and never an import: `tools/czech_brief.py` runs as a script, so
importing `_t` from it here loaded a second copy of that module whose language
was still English, and the whole guarantee was bypassed silently.
`tests/test_czech_figures.py` builds the document through its script entry
point for exactly that reason.

**Decimals are kept apart on purpose.** `pdftotext` rebuilds text runs from
where the glyphs landed, so two numbers drawn close together can come back as
one token. Axis ticks are integers where the scale allows it, tick labels sit
in the margin rather than inside the plot, and no value is printed twice.
`tools/czech_crosscheck.py` drops chart text from both sides of its comparison
for the same reason; these tests are what check the numbers instead.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from czech_external import QUALITY  # noqa: E402
from figures import _fit, esc, footnote, heading, ranked, short, svg  # noqa: E402

from tnb import results  # noqa: E402
from tnb.report import TRACK_SWITCH_LABELS  # noqa: E402
from tnb.scoring import czech as czech_scorer  # noqa: E402

LOCAL = REPO / "local"

#: One canvas width for all four, so they sit in the document as a set.
WIDTH = 900


#: The translator every figure is handed. `tools/czech_brief.py` passes its own
#: `_t`, which raises `Untranslated` rather than falling back to English.
Translate = Callable[[str], str]


def identity(text: str) -> str:
    """The English translator: every phrase in this file is already English.

    Only for a caller that has no document around it -- `main` below, and a
    test that wants the English drawing. A build passes the document's `_t`,
    because that is the one that raises on a missing Czech sentence.

    **The figures are handed a translator, never allowed to find one.** This
    file used to do `from czech_brief import _t` at the moment of the call, and
    `tools/czech_brief.py` is run as a script: it is `__main__`, so that import
    loaded a *second* copy of the module under the name `czech_brief`, whose
    `LANG` was still "en". Its `_t` returned the argument unchanged, nothing
    raised, and all four figures printed English inside the Czech document for
    as long as they existed. A parameter cannot pick up the wrong module.
    """
    return text


# --- the payloads ------------------------------------------------------------


def _payload(name: str) -> dict:
    path = LOCAL / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Data:
    """Everything the four figures read. All of it local, none of it published."""

    rows: list
    length: dict
    external: dict
    join: dict

    @classmethod
    def load(cls) -> Data:
        rows: list = []
        if results.LOCAL_ROWS_PATH.exists():
            drawable, _refused = results.drawable(results.load(results.LOCAL_ROWS_PATH))
            rows = [row for row in results.latest(drawable) if row.is_scored]
        return cls(
            rows=rows,
            length=_payload("czech-length.json"),
            external=_payload("czech-external.json"),
            join=_payload("czech-join.json"),
        )

    def rubric(self, track: str) -> str | None:
        """The newest rubric version scored on this track.

        Both versions of the Czech criteria are in the local record and
        `results.latest` keeps both, because a rubric version is part of a row's
        identity. A figure that iterated over all of them would take whichever
        row came last for each model -- two instruments in one line, and nothing
        on the page saying which. The document's tables draw the newest and name
        the older; so does this.
        """
        found = [row.judge_prompt_version for row in self.rows if row.track == track]
        return max(found) if found else None

    def judges(self, track: str) -> list[str]:
        rubric = self.rubric(track)
        return sorted(
            {
                row.judge_model or ""
                for row in self.rows
                if row.track == track and row.judge_prompt_version == rubric
            }
        )

    def composite(self, track: str, judge: str, keys: tuple[str, ...]) -> dict[str, float]:
        """The mean of `keys`, per model, on the newest rubric for that track.

        A model that is missing any one of the keys is left out rather than
        averaged over what it has. Averaging the answered ones would publish a
        score built from a smaller instrument than the one the axis is labelled
        with, and what goes missing clusters on the hard cases.
        """
        rubric = self.rubric(track)
        found: dict[str, float] = {}
        for row in self.rows:
            if row.track != track or row.judge_model != judge:
                continue
            if row.judge_prompt_version != rubric:
                continue
            if any(key not in row.metrics.headline for key in keys):
                continue
            found[row.system_id] = fmean(row.metrics.headline[key] for key in keys)
        return found


# --- shared drawing ----------------------------------------------------------

#: The class that carries each judge's ink, in the order the judges are drawn.
INKS = ("a", "b")


def _judge_ink(index: int) -> str:
    return INKS[index % len(INKS)]


def _scale(values: list[float], pad: float) -> tuple[float, float]:
    """The range the values occupy, with room around them.

    Padded rather than fitted, so the highest dot is not sitting on the frame.
    A set that is all one value still comes back as an interval, which is what
    keeps the division that follows from being a division by zero.
    """
    return min(values) - pad, max(values) + pad


def _rule(x1: float, y1: float, x2: float, y2: float) -> str:
    return f'<line class="rule" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>'


def _dot(x: float, y: float, ink: str, radius: float = 4.5) -> str:
    return (
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" class="fill-{ink} ring" '
        f'fill-opacity="0.9" stroke-width="1.5"/>'
    )


def _nice_step(span: float) -> int:
    """A round integer step that puts four to eight ticks across `span`."""
    for step in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000):
        if span / step <= 8:
            return step
    return 2000


def _decimal_ticks(low: float, high: float) -> list[float]:
    """Round values inside a score range, three to seven of them.

    Dividing the range into five equal parts is what a first draft does, and it
    labels the axis 0.16, 0.36, 0.55, 0.75, 0.95 -- five numbers a reader has to
    parse before they can read a position off the chart. These are the round
    ones inside the same range, and there are fewer of them.
    """
    for step in (0.02, 0.05, 0.1, 0.2, 0.25, 0.5, 1.0):
        first = -(-low // step) * step
        values, value = [], first
        while value <= high + 1e-9:
            values.append(round(value, 4))
            value += step
        if 3 <= len(values) <= 7:
            return values
    return [low, high]


# --- figure 1: the two note formats ------------------------------------------

FORMATS_TITLE = "The Deepsy note scores lower in {worse} of {compared} model-and-judge pairs"
FORMATS_SUB = (
    "Each line is one model: on the left its SOAP note, on the right its Deepsy note from "
    "the same sessions, read against the same six criteria by the same judge."
)
FORMATS_LOWER = "{worse} of {models} models score lower"
FORMATS_CONFOUND = (
    "A Deepsy note is also longer, and length runs against most of these criteria, so the "
    "format and the length point the same way here and {models} models cannot separate "
    "them. Which of the two the drop belongs to is not measured."
)
FORMATS_SOURCE = (
    "Source: local/czech-rows.jsonl, rubric {rubric}. Nothing in this figure is on the public site."
)
FORMATS_LABEL = "The SOAP note and the Deepsy note of each model, side by side"

#: The two halves of the corpus, each with the Deepsy track that pairs with it.
FORMAT_PAIRS = (
    (results.TRACK_CZECH_REAL, results.TRACK_DEEPSY_REAL),
    (results.TRACK_CZECH_TRANSLATED, results.TRACK_DEEPSY_TRANSLATED),
)


def draw_formats(data: Data, t: Translate) -> str:
    """SOAP against the Deepsy format, one line per model, four panels.

    Four rather than one, because the comparison was made four times -- two
    halves of the corpus, two judges -- and the finding is that all four go the
    same way. Averaging them would be one number where the evidence is four,
    and pooling the judges is the one thing this track never does.

    The lines are not labelled. The figure is about how uniform the slope is,
    the table under it says which model is which, and ten names in each of four
    panels would be forty labels arguing with the thing they sit on.
    """
    keys = czech_scorer.CRITERION_KEYS
    panels = []
    every: list[float] = []
    for row, (soap_track, deepsy_track) in enumerate(FORMAT_PAIRS):
        # The column is the judge's place in the sorted list, not a running
        # count of panels: with one judge deployed the second pair would
        # otherwise be drawn in the second column and inked as the second
        # judge, and nothing on the figure would say so.
        for column, judge in enumerate(data.judges(deepsy_track)):
            soap = data.composite(soap_track, judge, keys)
            deepsy = data.composite(deepsy_track, judge, keys)
            shared = sorted(set(soap) & set(deepsy))
            if len(shared) < 3:
                continue
            panels.append((row, column, soap_track, judge, shared, soap, deepsy))
            every.extend(soap[name] for name in shared)
            every.extend(deepsy[name] for name in shared)
    if not panels or not every:
        return ""

    # The vertical gap carries three lines between one row and the next: the
    # count under the panel above, the heading of the row below and the rule
    # under it. At 110 the count and the heading were twelve pixels apart.
    panel_w, panel_h, gap_x, gap_y = 320, 196, 110, 136
    left, top = 66, 152
    rows = max(row for row, *_rest in panels) + 1
    # The bottom carries the column captions, the count under the last panel
    # and two footnotes, which is why it is deeper than the gap between rows.
    height = top + rows * panel_h + (rows - 1) * gap_y + 156
    low, high = _scale(every, 0.05)

    def py(value: float, top_of: float) -> float:
        return top_of + panel_h - (value - low) / (high - low) * panel_h

    body, worse_total, compared_total = [], 0, 0
    seen_row = None
    for row, column, soap_track, judge, shared, soap, deepsy in panels:
        ox = left + column * (panel_w + gap_x)
        oy = top + row * (panel_h + gap_y)
        ink = _judge_ink(column)

        if seen_row != row:
            seen_row = row
            body.append(
                f'<text class="name" x="0" y="{oy - 58}" style="font-weight:650">'
                f"{esc(t(TRACK_SWITCH_LABELS.get(soap_track, soap_track)))}</text>"
                + _rule(0, oy - 48, WIDTH, oy - 48)
            )
        body.append(
            f'<text class="value" x="{ox}" y="{oy - 26}">'
            f"{esc(t('Judge'))} &middot; {esc(judge)}</text>"
        )

        for value in _decimal_ticks(low, high):
            y = py(value, oy)
            body.append(_rule(ox, y, ox + panel_w, y))
            body.append(
                f'<text class="value" x="{ox - 8}" y="{y + 4:.1f}" text-anchor="end">'
                f"{value:.1f}</text>"
            )

        worse = 0
        for name in shared:
            y1, y2 = py(soap[name], oy), py(deepsy[name], oy)
            worse += deepsy[name] < soap[name]
            body.append(
                f"<g><title>{esc(short(name))}: SOAP {soap[name]:.2f}, "
                f"Deepsy {deepsy[name]:.2f}</title>"
                f'<line class="{ink}" x1="{ox}" y1="{y1:.1f}" x2="{ox + panel_w}" '
                f'y2="{y2:.1f}" stroke-width="2" stroke-opacity="0.75" '
                f'stroke-linecap="round"/>'
                f"{_dot(ox, y1, ink, 4)}{_dot(ox + panel_w, y2, ink, 4)}</g>"
            )
        worse_total += worse
        compared_total += len(shared)

        body.append(
            f'<text class="value" x="{ox}" y="{oy + panel_h + 20}">SOAP</text>'
            f'<text class="value" x="{ox + panel_w}" y="{oy + panel_h + 20}" '
            f'text-anchor="end">Deepsy</text>'
            f'<text class="value" x="{ox}" y="{oy + panel_h + 40}">'
            f"{esc(t(FORMATS_LOWER).format(worse=worse, models=len(shared)))}</text>"
        )

    rubric = data.rubric(results.TRACK_DEEPSY_REAL) or ""
    smallest = min(len(entry[4]) for entry in panels)
    drawing = (
        heading(
            t(FORMATS_TITLE).format(worse=worse_total, compared=compared_total),
            t(FORMATS_SUB),
            width_px=WIDTH,
        )
        + "\n"
        + "\n".join(body)
        + "\n"
        + footnote(t(FORMATS_CONFOUND).format(models=smallest), 0, height - 74, width_px=WIDTH)
        + "\n"
        + footnote(t(FORMATS_SOURCE).format(rubric=rubric), 0, height - 20, width_px=WIDTH)
    )
    return svg(WIDTH, height, drawing, label=t(FORMATS_LABEL))


# --- figure 2: capability from outside ---------------------------------------

EXTERNAL_TITLE = "General capability tracks the English notes more closely than the Czech ones"
EXTERNAL_SUB = (
    "Each dot is one model: its score on a published capability index against the quality "
    "a judge gave its notes. The dashed line is least squares, drawn rather than described."
)
EXTERNAL_ENGLISH = "The English SOAP notes"
EXTERNAL_CZECH = "The Czech notes, translated half"
EXTERNAL_Y = "PDSQI-9 quality, 1 to 5"
EXTERNAL_RHO = "Spearman {rho}, p {p}, {n} models"
EXTERNAL_MATCH = (
    "Matched by name, and the name is the weak link: on this endpoint one id has already "
    "returned another model's output, so every dot is an assumption. These could not be "
    "matched to a public model at all and are absent rather than guessed: {names}."
)
EXTERNAL_SOURCE = (
    "Source: local/czech-external.json, {version}, fetched {fetched}. Nothing on this "
    "axis was measured by this project."
)
EXTERNAL_LABEL = "A published capability index against the quality of the notes"

#: The two panels, and the block of `czech-external.json` each one reads.
EXTERNAL_PANELS = (("english_quality", EXTERNAL_ENGLISH), ("czech_quality", EXTERNAL_CZECH))

#: What the horizontal axis is, spelled the way the table under this figure
#: spells it. It was "Intelligence Index" and drawn without going through the
#: translator at all, on the grounds that a product name does not translate --
#: but the document's own table three paragraphs below the chart calls it Index
#: inteligence, so a Czech reader met one index under two names in one chapter.
#: Whether to translate it is the document's decision to make; drawing it a
#: second way here is not.
EXTERNAL_X = "Intelligence index"


def draw_external(data: Data, t: Translate) -> str:
    """The capability index against PDSQI-9 quality, English and Czech.

    Two panels and two judges, because the answer differs by both: the index
    predicts the English quality under one judge strongly and the other
    moderately, and predicts the Czech under neither. The full 1-to-5 scale is
    drawn rather than the range the models occupy, so that a reader sees how
    little of the instrument is in use before reading the slope across it.
    """
    judges = sorted(data.external.get("judges") or {})
    if not judges:
        return ""

    blocks = {}
    for field, _title in EXTERNAL_PANELS:
        for judge in judges:
            entry = (data.external["judges"][judge].get(field) or {}).get("intelligence_index")
            if entry and entry.get("points"):
                blocks.setdefault(field, {})[judge] = entry
    if not blocks:
        return ""

    every_x = [
        point["outside"]
        for field in blocks
        for entry in blocks[field].values()
        for point in entry["points"]
    ]
    step = _nice_step(max(every_x) - min(every_x))
    x0 = (min(every_x) // step) * step
    x1 = ((max(every_x) // step) + 1) * step
    y0, y1 = 1.0, 5.0

    panel_w, panel_h, gap = 330, 250, 110
    left, top = 66, 156
    height = top + panel_h + 140

    def px(value: float, ox: float) -> float:
        return ox + (value - x0) / (x1 - x0) * panel_w

    def py(value: float) -> float:
        return top + panel_h - (value - y0) / (y1 - y0) * panel_h

    body = []
    for column, (field, title) in enumerate(EXTERNAL_PANELS):
        if field not in blocks:
            continue
        ox = left + column * (panel_w + gap)
        body.append(f'<text class="name" x="{ox}" y="{top - 78}">{esc(t(title))}</text>')

        value = x0
        while value <= x1:
            x = px(value, ox)
            body.append(_rule(x, top, x, top + panel_h))
            body.append(
                f'<text class="value" x="{x:.1f}" y="{top + panel_h + 18}" '
                f'text-anchor="middle">{value:.0f}</text>'
            )
            value += step
        for tick in range(1, 6):
            y = py(tick)
            body.append(_rule(ox, y, ox + panel_w, y))
            body.append(
                f'<text class="value" x="{ox - 8}" y="{y + 4:.1f}" text-anchor="end">{tick}</text>'
            )
        body.append(
            f'<text class="value" x="{ox + panel_w / 2:.0f}" y="{top + panel_h + 40}" '
            f'text-anchor="middle">{esc(t(EXTERNAL_X))}</text>'
        )

        for index, judge in enumerate(judges):
            entry = blocks[field].get(judge)
            if not entry:
                continue
            ink = _judge_ink(index)
            xs = [point["outside"] for point in entry["points"]]
            ys = [point["here"] for point in entry["points"]]
            if len(set(xs)) > 1:
                slope, intercept = _fit(xs, ys)
                body.append(
                    f'<line class="{ink}" x1="{px(x0, ox):.1f}" '
                    f'y1="{py(min(max(slope * x0 + intercept, y0), y1)):.1f}" '
                    f'x2="{px(x1, ox):.1f}" '
                    f'y2="{py(min(max(slope * x1 + intercept, y0), y1)):.1f}" '
                    f'stroke-width="2" stroke-dasharray="6 4" stroke-opacity="0.8"/>'
                )
            for point in entry["points"]:
                body.append(
                    f"<g><title>{esc(short(point['system']))}: {esc(t(EXTERNAL_X))} "
                    f"{point['outside']:.0f}, PDSQI-9 {point['here']:.2f}</title>"
                    + _dot(px(point["outside"], ox), py(point["here"]), ink)
                    + "</g>"
                )
            legend_y = top - 56 + index * 18
            body.append(
                _dot(ox + 5, legend_y - 4, ink, 4)
                + f'<text class="value fill-{ink}" x="{ox + 16}" y="{legend_y}">'
                + esc(
                    t(EXTERNAL_RHO).format(
                        rho=f"{entry['rho']:+.2f}", p=f"{entry['p']:.3f}", n=entry["n"]
                    )
                )
                + f' <tspan class="value">&middot; {esc(judge)}</tspan></text>'
            )

    unmatched = data.external.get("unmatched") or []
    notes = []
    if unmatched:
        notes.append(t(EXTERNAL_MATCH).format(names=", ".join(unmatched)))
    notes.append(
        t(EXTERNAL_SOURCE).format(
            version=data.external.get("index_version", ""),
            fetched=data.external.get("fetched", ""),
        )
    )

    drawing = (
        heading(t(EXTERNAL_TITLE), t(EXTERNAL_SUB), width_px=WIDTH)
        + f'\n<text class="value" x="{-(top + panel_h / 2):.0f}" y="16" '
        + f'transform="rotate(-90)" text-anchor="middle">{esc(t(EXTERNAL_Y))}</text>\n'
        + "\n".join(body)
        + "\n"
        + footnote(notes[0], 0, height - 74, width_px=WIDTH)
        + "\n"
        + footnote(notes[-1], 0, height - 20, width_px=WIDTH)
    )
    return svg(WIDTH, height, drawing, label=t(EXTERNAL_LABEL))


# --- figure 3: the English standing against the Czech one --------------------

JOIN_TITLE = "A place in English is not a place in Czech: {moved} of {models} change"
JOIN_SUB = (
    "PDSQI-9 on the English SOAP notes against PDSQI-9 on the Czech ones, averaged over the "
    "three attributes that are not the same for every model. Same instrument, same judge, "
    "only the language of the note differs."
)
#: The two columns of the slopegraph. Not the bare words "English" and
#: "Czech": a one-word key that broad would be reached by any other sentence
#: needing either word, and this is a column caption, not a language name.
JOIN_ENGLISH = "In English"
JOIN_CZECH = "In Czech"
JOIN_MOVED = "changed place: {moved}"
JOIN_HELD = "held their place: {held}"
JOIN_SOURCE = "Source: local/czech-join.json, both judges, the models both tables hold."
JOIN_LABEL = "Each model's place in English against its place in Czech"


def draw_join(data: Data, t: Translate) -> str:
    """Place in English against place in Czech, one block per judge.

    A place is not a measurement and this figure is about how little a place
    carries: the composite behind it is the mean of the three PDSQI-9
    attributes that vary, the same three `tools/czech_external.py` composes,
    and the lines are drawn rather than the scores because the scores under the
    two judges are a point and a half apart and would need two axes.
    """
    judges = sorted(data.join.get("judges") or {})
    blocks = []
    for judge in judges:
        found = data.join["judges"][judge].get("same_instrument") or {}
        english: dict[str, list[float]] = {}
        czech: dict[str, list[float]] = {}
        for key in QUALITY:
            for point in (found.get(key) or {}).get("points") or []:
                english.setdefault(point["system"], []).append(point["english"])
                czech.setdefault(point["system"], []).append(point["czech"])
        # Only models measured on every attribute of the composite: a mean over
        # two of three is a different instrument from a mean over three.
        names = sorted(
            name
            for name in english
            if len(english[name]) == len(QUALITY) and len(czech.get(name, [])) == len(QUALITY)
        )
        if len(names) < 3:
            continue
        blocks.append(
            (
                judge,
                names,
                ranked({name: fmean(english[name]) for name in names}),
                ranked({name: fmean(czech[name]) for name in names}),
            )
        )
    if not blocks:
        return ""

    row_h = 24
    mid_l, mid_r = 300, 600
    top, gap = 146, 104
    tallest = max(len(names) for _judge, names, _a, _b in blocks)
    height = top + len(blocks) * tallest * row_h + (len(blocks) - 1) * gap + 118

    body, moved_total, models_total = [], 0, 0
    for index, (judge, names, english, czech) in enumerate(blocks):
        oy = top + index * (tallest * row_h + gap)

        # A row per model, not a row per place. Two models that print the same
        # score share a place -- the site's rule, and this document's -- and
        # putting both on the line their place names drew the two labels on top
        # of each other: `gemma4` and `kimi-k3` are both fourth under one judge
        # and the figure printed them as one word. They get a row each and the
        # same number in front of both, which is what a shared place is.
        def rows_of(places: dict[str, int]) -> dict[str, int]:
            order = sorted(places, key=lambda name: (places[name], name))
            return {name: place for place, name in enumerate(order)}

        english_row, czech_row = rows_of(english), rows_of(czech)

        def y_of(row: int, oy: float = oy) -> float:
            return oy + (row + 0.5) * row_h

        moved = [name for name in names if english[name] != czech[name]]
        moved_total += len(moved)
        models_total += len(names)
        # Three lines, not two. The counts and the column captions shared a
        # line at first and the counts ran under the left caption: the left
        # caption is right-aligned to the slope's own edge, so the two grow
        # towards each other and the collision only appears once a count has
        # two digits or a translation is longer than its English.
        body.append(
            f'<text class="name" x="0" y="{oy - 62}" style="font-weight:650">'
            f"{esc(t('Judge'))} &middot; {esc(judge)}</text>"
            f'<text class="value" x="0" y="{oy - 42}">'
            f"{esc(t(JOIN_MOVED).format(moved=len(moved)))} &middot; "
            f"{esc(t(JOIN_HELD).format(held=len(names) - len(moved)))}</text>"
            f'<text class="value" x="{mid_l - 12}" y="{oy - 12}" text-anchor="end">'
            f"{esc(t(JOIN_ENGLISH))}</text>"
            f'<text class="value" x="{mid_r + 12}" y="{oy - 12}">'
            f"{esc(t(JOIN_CZECH))}</text>" + _rule(0, oy - 32, WIDTH, oy - 32)
        )
        for name in names:
            y1, y2 = y_of(english_row[name]), y_of(czech_row[name])
            ink = "flat" if english[name] == czech[name] else _judge_ink(index)
            body.append(
                f"<g><title>{esc(short(name))}: {english[name]} &rarr; {czech[name]}</title>"
                f'<path class="{ink}" d="M {mid_l} {y1:.1f} C {mid_l + 70} {y1:.1f}, '
                f'{mid_r - 70} {y2:.1f}, {mid_r} {y2:.1f}" fill="none" stroke-width="2" '
                f'stroke-opacity="0.8" stroke-linecap="round"/>'
                f"{_dot(mid_l, y1, _judge_ink(index), 4)}"
                f"{_dot(mid_r, y2, _judge_ink(index), 4)}</g>"
                f'<text class="name" x="{mid_l - 12}" y="{y1 + 4:.1f}" text-anchor="end">'
                f"{english[name]}. {esc(short(name))}</text>"
                f'<text class="name" x="{mid_r + 12}" y="{y2 + 4:.1f}">'
                f"{czech[name]}. {esc(short(name))}</text>"
            )

    # The confound is the payload's own sentence, translated where the document
    # already translates it. Empty rather than absent means an older payload,
    # and `t("")` would stop the Czech build over a caption nobody wrote.
    confound = data.join.get("confound") or ""
    drawing = (
        heading(
            t(JOIN_TITLE).format(moved=moved_total, models=models_total),
            t(JOIN_SUB),
            width_px=WIDTH,
        )
        + "\n"
        + "\n".join(body)
        + "\n"
        + (footnote(t(confound), 0, height - 74, width_px=WIDTH) + "\n" if confound else "")
        + footnote(t(JOIN_SOURCE), 0, height - 20, width_px=WIDTH)
    )
    return svg(WIDTH, height, drawing, label=t(JOIN_LABEL))


# --- figure 4: length against score ------------------------------------------

LENGTH_TITLE = "The longer a model's note, the worse it does on the Czech criteria"
LENGTH_SUB = (
    "Each dot is one model: the median length of its notes against the mean of the six "
    "criteria under one judge. The dashed line is least squares, drawn rather than "
    "described."
)
LENGTH_X = "Median words in one note"
LENGTH_Y = "The six criteria, averaged"
LENGTH_WHY = (
    "Length was not assigned to the models, they chose it, so this is not a correction to "
    "apply -- a model may write long BECAUSE it summarises badly, and subtracting what "
    "length predicts would take the result away with the artefact. It is a reason not to "
    "read the bottom of the table as bad Czech and nothing else."
)
LENGTH_SOURCE = (
    "Source: local/czech-length.json and local/czech-rows.jsonl, rubric {rubric}. "
    "The lengths are medians over the notes that parsed."
)
LENGTH_LABEL = "Note length against the criteria score, one dot per model"

#: The two halves the length payload records a word count for.
LENGTH_TRACKS = (results.TRACK_CZECH_REAL, results.TRACK_CZECH_TRANSLATED)


def draw_length(data: Data, t: Translate) -> str:
    """How long each model writes against what the criteria gave it.

    One panel per half of the corpus and one ink per judge. Length does not
    depend on the judge, so each model is one x with two y's, which is the
    cheapest way to show that both judges answer the question the same way.
    """
    words = data.length.get("czech") or {}
    panels = []
    every_x: list[float] = []
    every_y: list[float] = []
    for track in LENGTH_TRACKS:
        by_system = (words.get(track) or {}).get("by_system") or {}
        lengths = {
            name: float(value)
            for name, value in by_system.items()
            if isinstance(value, int | float)
        }
        if not lengths:
            continue
        series = []
        for index, judge in enumerate(data.judges(track)):
            scores = data.composite(track, judge, czech_scorer.CRITERION_KEYS)
            shared = sorted(set(scores) & set(lengths))
            if len(shared) < 3:
                continue
            series.append((judge, _judge_ink(index), shared, scores))
            every_x.extend(lengths[name] for name in shared)
            every_y.extend(scores[name] for name in shared)
        if series:
            panels.append((track, lengths, series))
    if not panels or not every_x:
        return ""

    step = _nice_step(max(every_x) - min(every_x))
    x0 = (min(every_x) // step) * step
    x1 = ((max(every_x) // step) + 1) * step
    y0, y1 = _scale(every_y, 0.05)

    panel_w, panel_h, gap = 330, 240, 110
    left, top = 74, 158
    height = top + panel_h + 140

    def py(value: float) -> float:
        return top + panel_h - (value - y0) / (y1 - y0) * panel_h

    body = []
    for column, (track, lengths, series) in enumerate(panels):
        ox = left + column * (panel_w + gap)

        def px(value: float, ox: float = ox) -> float:
            return ox + (value - x0) / (x1 - x0) * panel_w

        body.append(
            f'<text class="name" x="{ox}" y="{top - 78}">'
            f"{esc(t(TRACK_SWITCH_LABELS.get(track, track)))}</text>"
        )
        value = x0
        while value <= x1:
            x = px(value)
            body.append(_rule(x, top, x, top + panel_h))
            body.append(
                f'<text class="value" x="{x:.1f}" y="{top + panel_h + 18}" '
                f'text-anchor="middle">{value:.0f}</text>'
            )
            value += step
        for value in _decimal_ticks(y0, y1):
            y = py(value)
            body.append(_rule(ox, y, ox + panel_w, y))
            body.append(
                f'<text class="value" x="{ox - 8}" y="{y + 4:.1f}" text-anchor="end">'
                f"{value:.1f}</text>"
            )
        body.append(
            f'<text class="value" x="{ox + panel_w / 2:.0f}" y="{top + panel_h + 40}" '
            f'text-anchor="middle">{esc(t(LENGTH_X))}</text>'
        )

        for index, (judge, ink, shared, scores) in enumerate(series):
            xs = [lengths[name] for name in shared]
            ys = [scores[name] for name in shared]
            if len(set(xs)) > 1:
                slope, intercept = _fit(xs, ys)
                body.append(
                    f'<line class="{ink}" x1="{px(x0):.1f}" '
                    f'y1="{py(min(max(slope * x0 + intercept, y0), y1)):.1f}" '
                    f'x2="{px(x1):.1f}" '
                    f'y2="{py(min(max(slope * x1 + intercept, y0), y1)):.1f}" '
                    f'stroke-width="2" stroke-dasharray="6 4" stroke-opacity="0.8"/>'
                )
            for name in shared:
                body.append(
                    f"<g><title>{esc(short(name))}: {lengths[name]:.0f}, "
                    f"{scores[name]:.2f}</title>"
                    + _dot(px(lengths[name]), py(scores[name]), ink)
                    + "</g>"
                )
            legend_y = top - 56 + index * 18
            body.append(
                _dot(ox + 5, legend_y - 4, ink, 4)
                + f'<text class="value" x="{ox + 16}" y="{legend_y}">'
                + f"{esc(t('Judge'))} &middot; {esc(judge)}</text>"
            )

    rubric = data.rubric(results.TRACK_CZECH_REAL) or ""
    drawing = (
        heading(t(LENGTH_TITLE), t(LENGTH_SUB), width_px=WIDTH)
        + f'\n<text class="value" x="{-(top + panel_h / 2):.0f}" y="16" '
        + f'transform="rotate(-90)" text-anchor="middle">{esc(t(LENGTH_Y))}</text>\n'
        + "\n".join(body)
        + "\n"
        + footnote(t(LENGTH_WHY), 0, height - 74, width_px=WIDTH)
        + "\n"
        + footnote(t(LENGTH_SOURCE).format(rubric=rubric), 0, height - 20, width_px=WIDTH)
    )
    return svg(WIDTH, height, drawing, label=t(LENGTH_LABEL))


#: The four, by the name the document refers to them by. Deliberately not added
#: to `figures.FIGURES`: every entry there is asserted to appear on a published
#: page, and none of these may ever be published.
CZECH_FIGURES = {
    "formats": draw_formats,
    "external": draw_external,
    "join": draw_join,
    "length": draw_length,
}


def main() -> int:
    """Render all four in English and report their size. Nothing is written.

    English because there is no document here to ask: a translator that raises
    belongs to a build, and this entry point is a size check.
    """
    data = Data.load()
    for name, draw in CZECH_FIGURES.items():
        drawn = draw(data, identity)
        if not drawn:
            print(f"{name:10} no data in this checkout")
            continue
        print(f"{name:10} {len(drawn):>7,} bytes, {drawn.count('<circle'):>3} marks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
