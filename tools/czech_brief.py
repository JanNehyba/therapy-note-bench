"""Write the Czech track's briefing: the document that becomes the PDF.

The tables answer "which model". This answers "what was measured, and what may
not be concluded from it" -- which is the half a table cannot carry and the half
that matters when the numbers leave the machine they were computed on.

It reads `local/czech-rows.jsonl` and writes `local/czech-brief.html`, and both
of those are gitignored. `tools/pdf.py --source local/czech-brief.html --target
local/czech-report.pdf` turns it into the single file that can be sent to
people who have no checkout.

**Two rules the document is built to keep.** The caveats travel with the
numbers, in the same document rather than in a link somebody may not follow: a
team handed a table without them will supply their own, and theirs will be
generous. And no transcript text appears anywhere -- only scores, counts and
model names. `local/` is outside the reach of
`tests/test_no_clinical_content.py`, so that property is asserted here instead,
in `check_no_clinical_text`, before the file is written.
"""

from __future__ import annotations

import argparse
import collections
import functools
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from tnb import i18n, results
from tnb.report import (
    COLUMNS,
    MEASURE_TABLES,
    TRACK_BLURBS,
    TRACK_SWITCH_LABELS,
    TRACK_TITLES,
)
from tnb.scoring import czech as czech_scorer
from tnb.tasks import TASKS

sys.path.insert(0, str(Path(__file__).resolve().parent))
from czech_brief_cs import CS  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO / "local" / "czech-rows.jsonl"
DEFAULT_TARGET = REPO / "local" / "czech-brief.html"

#: The language the document is written in for this run. A module-level switch
#: rather than a parameter threaded through fifteen functions: every one of them
#: renders prose, and the alternative is fifteen signatures that exist to carry
#: one word.
LANG = "en"


class Untranslated(RuntimeError):
    """A sentence that would have gone to a Czech reader in English."""


def _t(text: str) -> str:
    """One phrase in the language this run is writing.

    **Strict on purpose.** A missing translation raises rather than falling back
    to English, because the failure it prevents is the one that matters: a
    document that is Czech everywhere a reader looks first and English in the
    caveats, which is where the reader who most needs them stops reading.

    Two dictionaries, in order. `tnb.i18n` already holds every column label,
    definition and caveat, because the published pages are bilingual and those
    strings are the same strings. `czech_brief_cs` holds this document's own
    prose. Nothing is duplicated between them.
    """
    if LANG == "en":
        return text
    found = _index().get(i18n.norm(text))
    if found is None:
        raise Untranslated(f"no {LANG} for: {text[:120]}")
    return found


@functools.cache
def _index() -> dict[str, str]:
    """Both dictionaries, normalised once. This document's own prose wins."""
    return {i18n.norm(k): v for k, v in i18n.CS.items()} | {i18n.norm(k): v for k, v in CS.items()}


#: Words that would only be in this document if a transcript had leaked into it.
#: Not a Czech-diacritic scan: the criteria have Czech labels and the model ids
#: are ASCII, so what is checked is length -- no free-text field on a row is
#: long enough to be a sentence of a session.
MAX_FIELD_CHARS = 200

#: The criteria tracks, split by note format. Named rather than derived from
#: "everything that is not PDSQI": the two formats are measured with the same
#: six criteria but are never counted together, because not every model was
#: asked in both and because a Deepsy note is longer under a length ceiling a
#: SOAP note does not have. A filter that says what a track is *not* quietly
#: pools whatever is added next.
SOAP_CRITERIA_TRACKS = (results.TRACK_CZECH_REAL, results.TRACK_CZECH_TRANSLATED)
DEEPSY_CRITERIA_TRACKS = (results.TRACK_DEEPSY_REAL, results.TRACK_DEEPSY_TRANSLATED)

STYLE = """
:root { --ink:#14161a; --muted:#5b6270; --rule:#d8dce3; --accent:#1c4e80; }
* { box-sizing: border-box; }
body { font: 11pt/1.5 "Source Serif 4", Georgia, serif; color: var(--ink);
       max-width: 52rem; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }
h1 { font-size: 1.9rem; line-height: 1.2; margin: 0 0 .3rem; }
h2 { font-size: 1.15rem; margin: 2.4rem 0 .6rem; padding-bottom: .25rem;
     border-bottom: 2px solid var(--rule); }
h3 { font-size: 1rem; margin: 1.6rem 0 .4rem; }
.sub { color: var(--muted); margin: 0 0 2rem; font-size: .95rem; }
table { border-collapse: collapse; width: 100%; font-size: .85rem;
        font-family: "Source Sans 3", system-ui, sans-serif; margin: .8rem 0 1.4rem; }
th, td { padding: .35rem .5rem; text-align: right; border-bottom: 1px solid var(--rule); }
th:first-child, td:first-child { text-align: left; white-space: nowrap; }
thead th { border-bottom: 2px solid var(--ink); font-weight: 600; vertical-align: bottom; }
tbody tr:nth-child(even) { background: #f6f7f9; }
.dash { color: var(--muted); }
td.differ { background: #fdf4e8; }
tr.place td { border-top: 2px solid var(--rule); }
dl { margin: .6rem 0 0; }
dt { font-weight: 600; font-family: "Source Sans 3", system-ui, sans-serif;
     font-size: .85rem; margin-top: .7rem; }
dd { margin: .1rem 0 0; color: var(--muted); font-size: .9rem; }
.warn { border-left: 3px solid var(--accent); padding: .1rem 0 .1rem .9rem; margin: 1rem 0; }
/* The summary, and the only tinted block in the document. It is the one
   thing a reader who reads nothing else should read, so it is above the
   first table and looks unlike the prose around it. */
.summary { background: #f4f6f9; border: 1px solid var(--rule); border-radius: 3px;
           padding: .2rem 1.1rem 1rem; margin: 1.4rem 0 1.8rem; }
.summary h2 { margin-top: 1.2rem; border-bottom: none; }
.summary p:last-child { margin-bottom: 0; }
.warn p { margin: .4rem 0; }
footer { margin-top: 3rem; padding-top: .8rem; border-top: 1px solid var(--rule);
         color: var(--muted); font-size: .8rem; }
code { font-family: ui-monospace, monospace; font-size: .9em; }
@media print {
  body { max-width: none; padding: 0; font-size: 10pt; }
  h2 { break-after: avoid; } table { break-inside: auto; }
  tr { break-inside: avoid; } .warn { break-inside: avoid; }
  .summary { break-inside: avoid; background: #f4f6f9 !important; }
}
"""

#: The document's own sentences, named so they can be translated. Inlined in
#: the template they could not be: an f-string cannot carry a call around a
#: paragraph without becoming unreadable, and a paragraph that cannot be wrapped
#: is a paragraph that stays English.
TITLE = "Czech note quality"
HEADLINE = "How well do language models write Czech therapy notes?"
SUBTITLE = "therapy-note-bench \u00b7 Czech track \u00b7 measured, not published"
INTRO = (
    "{models} models were asked for notes from twenty psychotherapy sessions -- "
    "ten real and ten translated -- in two note formats, SOAP and the one the Deepsy "
    "application writes, and two independent judges rated every note that came back. "
    "Not every model was asked in both formats, and {written} of the {asked} notes "
    "were written; the rest are named where they are missing. "
    "Two instruments: six yes/no criteria asking whether the Czech is right, and "
    "PDSQI-9, a published instrument, asking whether the note is any good -- and "
    "PDSQI-9 was put only to the SOAP notes. Both, "
    "because neither answers the other: a flawless Czech sentence about nothing "
    "passes all six criteria, and a note full of insight can be written in bad "
    "Czech."
)
#: The second question, and it is second. The document used to open with it,
#: which made a report about Czech notes look like a footnote to the English
#: leaderboard.
INTRO_SECOND = (
    "A second question runs alongside: the same models are ranked on an English "
    "leaderboard, and whether that standing says anything about the Czech they write "
    "has its own section below."
)
NOT_PUBLIC = "These numbers are not on the public site and this document is not a publication."
NOT_PUBLIC_WHY = (
    "They were measured from confidential clinical material and the decision to "
    "publish anything from them has not been made. The transcripts were de-identified "
    "before any model saw them, and no transcript text appears in this document or in "
    "any file it was built from."
)
#: Placeholders, because the alternative is two numbers typed into a sentence
#: that a later run silently makes false. Both translations carry the same two.
SCALE_NOT_ADDITIVE = (
    "The two instruments did not read the same notes, so the rows do not add up: "
    "{models} models wrote {written} notes in all, and the {soap} SOAP notes among "
    "them were each read twice by each judge -- once against the criteria and once "
    "against PDSQI-9."
)
#: Printed only where there are Deepsy rows to be printed about. It says which
#: notes an instrument was never put to, and a document with no Deepsy rows in
#: it would be naming a gap that is not there.
SCALE_NO_PDSQI = (
    "The {deepsy} notes in the Deepsy format were read against the criteria only. "
    "PDSQI-9 was never asked about a Deepsy note, so no quality figure anywhere in "
    "this document is about one."
)
METHOD_CORPORA = (
    "Two halves, both read only from a directory that is not in version control. "
    "Every model was asked for a note from every transcript, on e-INFRA -- that is the "
    "design, and {written} of the {asked} notes are the outcome. Where a model wrote "
    "fewer, it is named: {short}."
)
METHOD_SIZE = (
    "a real session runs seven times longer than a translated AnnoMI conversation, so "
    "the two halves differ in how hard the summarising is before language is "
    "considered at all."
)
METHOD_BOUNDARY = (
    "What leaves for the judge's provider is the note a model wrote, which is what "
    "lets a confidential session be scored at all. The one place a transcript is sent "
    "is the PDSQI table on the translated half: those transcripts are AnnoMI, "
    "published under CC-BY, and sending them buys the two attributes -- is the note "
    "accurate, is it thorough -- that cannot be answered without the session. The real "
    "half is asked the other six and those two columns are absent from it, because the "
    "question could not be put rather than because a note failed."
)
METHOD_CRITERIA = (
    "Each criterion is one question, answered yes or no, asked in its own call. A "
    "column is the share of notes free of that fault, so higher is better throughout. "
    "A judge that answered neither yes nor no is recorded as not having answered -- "
    'never as "no fault" -- and a note with no content is not asked at all, because '
    "every one of the six asks about the absence of a fault and an empty note would "
    "pass all six."
)
METHOD_PDSQI = (
    "PDSQI-9 is reproduced in English, word for word, because a translated instrument "
    "is a different instrument with nothing validating it. The note it rates is Czech "
    "and is shown with the Czech headings the model wrote. Seven of its eight "
    "attributes are rated 1 to 5 and the eighth is a yes/no; they are reported "
    "separately and never averaged, which is how the instrument's own authors report "
    "them."
)
FOOTER = "Generated by tools/czech_brief.py from local/czech-rows.jsonl. Both are gitignored."

LIMITS = [
    (
        "Ten sessions, and they are all one client",
        "Every model was asked for a note from every transcript, which is what makes "
        "the comparison between models valid at all -- the first attempt gave each "
        "model a different session and could not tell a worse model from a harder "
        "session. The asking held and the answering did not always: {written} of the "
        "{asked} notes came back, and the shortfalls are {short}. But "
        "ten notes per model is a small number, and the real half is one client with "
        "one therapist. Read the ordering, not the gaps between neighbours.",
    ),
    (
        "The two halves differ by more than language, and mostly by size",
        "A real session runs to a median of {real_words} words and {real_turns} turns; "
        "a translated AnnoMI conversation to {other_words} words and {other_turns} turns. "
        "Seven times the material, so "
        "the summarising is a harder task before any question of Czech arises. They "
        "differ in topic too -- AnnoMI is motivational interviewing about substance "
        "use and the real sessions are not -- and in who transcribed them. A model "
        "that does worse on one half may be doing worse at length, at motivational "
        "interviewing, or at Czech, and these numbers cannot separate the three.",
    ),
    (
        "Nothing here says whether a note is true",
        "The criteria ask about the Czech and nothing else. A fluent, correctly typeset, "
        "entirely invented note passes all six. Whether the note says what the session "
        "contained is a different measurement and this is not it.",
    ),
    (
        "The instrument has never been checked against a person",
        "These six criteria are this repository's own, because no published Czech "
        "note-quality instrument exists to reproduce. Nobody has rated these notes by "
        "hand, and unlike PDSQI-9 there is not even a published figure for how well two "
        "people would agree on them. Two independent judges answer every question, and "
        "where they disagree is the only control there is.",
    ),
    (
        "SOAP is not what a Czech psychologist writes",
        "The prompt is a translation of TN-Eval's, so that the task is the same task in "
        "another language and the English numbers mean something beside these. It is not "
        "a reproduction of any Czech documentation standard -- there is none to "
        "reproduce. The notes are therefore formally artificial, equally so for every "
        "model.",
    ),
    (
        "A criterion every model passes is not agreement",
        "Where every model scores the same, two judges agreeing about it says nothing: a "
        "correlation over a column of identical values is a coin. Such columns are "
        "reported as unmeasured rather than as unanimous.",
    ),
]


def _grouped(value: int) -> str:
    """A thousands separator the reader's language uses.

    English groups with a comma and Czech with a space, and the document had
    both: the prose said 5 266 and the table beside it said 5,266, which a
    Czech reader reads as five and a quarter. A non-breaking space, so the
    print does not wrap a number in half.
    """
    text = f"{value:,}"
    return text if LANG == "en" else text.replace(",", "\u00a0")


def _fill(body: str) -> str:
    """Fill a caveat's placeholders, if it has any. Most do not."""
    return body.format(**_corpus_sizes()) if "{" in body else body


def _corpus_sizes() -> dict[str, str]:
    """The two corpora's medians, measured rather than typed.

    The sentence about them carried its own figures for a while. This document
    has been through that before -- four of five hand-written numbers had
    drifted from the table printing the same measurement three sections below --
    and a caveat with a stale number in it is worse than no caveat, because it
    is the paragraph a reader trusts.
    """
    # Imported here, as `_corpus` does: the loaders touch the data directory
    # and a document built without it should still draw everything else.
    from tnb.tasks import czech as czech_task

    out = {}
    halves = (("real", czech_task.load_real), ("other", czech_task.load_translated))
    for prefix, load in halves:
        try:
            sessions = load()
        except (RuntimeError, OSError):
            sessions = []
        if not sessions:
            return dict.fromkeys(("real_words", "real_turns", "other_words", "other_turns"), "?")
        words = sorted(session.word_count for session in sessions)
        turns = sorted(len(session.turns) for session in sessions)
        out[f"{prefix}_words"] = _grouped(words[len(words) // 2])
        out[f"{prefix}_turns"] = _grouped(turns[len(turns) // 2])
    return out


def _fmt(value, digits: int) -> str:
    if value is None:
        return '<span class="dash">--</span>'
    return f"{value:.{digits}f}"


#: Below this share of its notes, a row's mean is reported with a mark rather
#: than plainly. Four fifths is a line and not a law; what matters is that a
#: reader can see which rows are thin without doing the subtraction.
THIN = 0.8

#: Below this share of separable pairs, a column's ordering is named as one not
#: to read. A quarter is a line and not a law; what it buys is that a reader
#: does not have to divide 13 by 54 to notice.
UNREADABLE = 0.25


#: The tail every criterion definition ends with. It is true of all six, so
#: printing it six times says it five times too often -- it goes above the list
#: once instead.
_SHARED_TAILS = (
    " Reported as the share of notes free of it.",
    " rated 1 (not at all) to 5 (extremely).",
    " answered yes or no and reported as the fraction of notes free of it.",
)


def _trim(text: str) -> str:
    for tail in _SHARED_TAILS:
        if text.endswith(tail):
            return text[: -len(tail)]
    return text


def _varying(track: str, rows: list[results.Row]) -> tuple[str, ...]:
    """The columns that actually separate these models.

    A column every model scores the same on tells the reader nothing about who
    is ahead, and averaging it in only shrinks the differences that are left.
    `tools/czech_variance.py` already states this for the bands; the table sort
    claimed it in a docstring and never did it.

    Computed per comparability group rather than per track, because whether a
    column is flat is a fact about the group. `organized` is 5.00 for every
    model under one judge and moves under the other.
    """
    varying = []
    for key, digits in COLUMNS[track]:
        seen = {
            round(row.metrics.headline[key], digits) for row in rows if key in row.metrics.headline
        }
        if len(seen) > 1:
            varying.append(key)
    return tuple(varying)


def _rank_of(track: str, row: results.Row, varying: tuple[str, ...]) -> float:
    """How well a model did overall, for putting the best row first.

    A table sorted by model name asks the reader to find the good ones. The mean
    of the columns that separate these models orders the rows -- and it is only
    an ordering: which gaps may be *read* is what the bands and the threshold
    are for, and they say so elsewhere.

    **Every column is put on one axis first, and that is a repair rather than a
    refinement.** A PDSQI table mixes five ratings from 1 to 5 with one share
    from 0 to 1, and this function used to average them raw -- so the worst
    stigmatising rate in a group, 0.70, sat below the entire Likert range and
    barely moved the mean. Measured on the real Czech PDSQI table under
    `gpt-5.6-terra`, correcting it moves seven of eleven models, and
    `qwen3.5-int4` falls from fourth to tenth. The published order was wrong,
    not merely unexplained.
    """
    measures = MEASURE_TABLES[track]
    scales = {measures[key]["scale"] for key in varying}
    # Rescale only where the table actually mixes scales. On the language
    # tables every column is 0-1, and putting them all on the Likert axis
    # printed an index of 4.60 beside columns reading 0.90 -- a number in a
    # unit none of the columns beside it use.
    mixed = len(scales) > 1
    values = []
    for key in varying:
        if key not in row.metrics.headline:
            continue
        value = row.metrics.headline[key]
        if mixed and measures[key]["scale"] == "0-1":
            value = 1 + 4 * value
        values.append(value)
    return sum(values) / len(values) if values else -1.0


def _sort_line(track: str, varying: tuple[str, ...]) -> str:
    """Which columns put this table in this order, named beside it.

    The list is computed, so it stays true when a column goes flat -- and when
    only one column is left it says so, which is the case a reader most needs.
    On the real Czech PDSQI half under one judge, five of the six columns are
    the same for every model and the order the reader sees is very nearly an
    order by note length. A caption that said "sorted by the mean of six
    columns" would be true and would hide that.
    """
    labels = MEASURE_TABLES[track]
    names = _join_words([_t(labels[key]["label"]) for key in varying])
    if not varying:
        return _t("Nothing here separates these models: no column takes two different values.")
    if len(varying) == 1:
        line = _t(
            "The Order column is {names}, the one column that separates these models at "
            "all, and it is what the rows are sorted by."
        ).format(names=names)
    else:
        line = _t(
            "The Order column is the mean of these {count}: {names}. It is what the rows "
            "are sorted by and it is not a measurement -- weighting spelling against "
            "clinical terminology is a judgement, which is why no such index is "
            "published. It is here so the order can be checked rather than trusted."
        ).format(count=len(varying), names=names)
    # Only when something was actually left out. The sentence used to be part of
    # the one above it and so was printed over tables where every column varies,
    # where it says that some of them do not.
    dropped = len(COLUMNS[track]) - len(varying)
    if dropped:
        line += " " + _t(
            "The other {dropped} are the same for every model here, so they order nothing "
            "and are left out."
            if dropped > 1
            else "One more is the same for every model here, so it orders nothing and is left out."
        ).format(dropped=dropped)
    return line


def _join_words(items: list[str]) -> str:
    """A, B and C -- in the document's language, not English's."""
    if len(items) < 2:
        return "".join(items)
    return f"{', '.join(items[:-1])} {_t('and')} {items[-1]}"


def _scale_line(track: str) -> str:
    """What the numbers in this table are, said beside the table.

    It used to be only in the definitions below it, which is where a reader
    goes second if at all -- so the first thing they met was a grid of decimals
    with nothing saying which end is good.
    """
    scales = {MEASURE_TABLES[track][key]["scale"] for key, _ in COLUMNS[track]}
    if scales == {"0-1"}:
        return _t(
            "Every column is 0 to 1 and higher is better: the share of notes free of that fault."
        )
    if scales == {"1-5"}:
        return _t("Every column is 1 to 5 and higher is better.")
    return _t(
        "Higher is better throughout. Most columns are rated 1 to 5; the last is the "
        "share of notes free of the fault, from 0 to 1."
    )


def _notes_cell(row: results.Row) -> str:
    """How many notes are behind this row's means, out of the corpus.

    Three numbers exist and only one of them is the denominator a reader wants:
    the corpus was `n_sessions_attempted`, the model wrote `n_sessions_generated`
    of it, and the judge answered every question of `scored - partial`. Printing
    the last on its own turned "six of ten sessions, four fully answered" into
    "4", which reads like a small number and not like a hole.
    """
    complete = row.n_sessions_scored - row.n_sessions_partial
    corpus = row.n_sessions_attempted or row.n_sessions_scored
    return str(complete) if complete == corpus else f"{complete}/{corpus}"


def _dominates(first: dict, second: dict, keys, tables: dict) -> bool:
    """Whether `first` is at least as good as `second` everywhere, and better once.

    Under every judge, on every column both were scored on. A column where
    either has no value is not compared rather than counted either way -- an
    absence is not a win and it is not a loss.
    """
    strictly = False
    for table in tables.values():
        left, right = table.get(first), table.get(second)
        if left is None or right is None:
            return False
        for key in keys:
            a, b = left.get(key), right.get(key)
            if a is None or b is None:
                continue
            if a < b - 1e-9:
                return False
            if a > b + 1e-9:
                strictly = True
    return strictly


def _dominance_places(systems: list[str], keys, tables: dict) -> dict[str, int]:
    """A place per system: how many other systems dominate it.

    Not a rank from 1 to n. Two systems neither of which dominates the other get
    the same number, which is the point -- the evidence does not order them, and
    a table that numbers them anyway invents the part the reader most wants.
    """

    def beaten_by(system: str) -> int:
        return sum(
            1 for other in systems if other != system and _dominates(other, system, keys, tables)
        )

    return {system: beaten_by(system) for system in systems}


def _merged_table(track: str, groups: list[list[results.Row]]) -> str:
    """One table for a track, with every judge's value in every cell.

    Twelve tables became six. Nothing is averaged: the two numbers sit side by
    side, so a model the judges disagree about shows it in the cell rather than
    on another page.

    Rows are ordered by dominance and models nothing separates share a place.
    Within a shared place they are alphabetical, which is arbitrary and says so
    by being alphabetical rather than by looking like a ranking.
    """
    rows_by_judge: dict[str, dict[str, results.Row]] = {}
    for group in groups:
        judge = group[0].judge_model or "?"
        rows_by_judge[judge] = {row.system_id: row for row in group}
    judges = sorted(rows_by_judge)
    if not judges:
        return ""

    columns = COLUMNS[track]
    measures = MEASURE_TABLES[track]
    every = [row for group in groups for row in group]
    varying = _varying(track, every)
    keys = [key for key, _ in columns]

    systems = sorted(set.intersection(*(set(v) for v in rows_by_judge.values())))
    tables = {
        judge: {system: rows_by_judge[judge][system].metrics.headline for system in systems}
        for judge in judges
    }
    places = _dominance_places(systems, varying or keys, tables)

    def index_of(system: str) -> float:
        found = [
            _rank_of(track, rows_by_judge[judge][system], varying)
            for judge in judges
            if system in rows_by_judge[judge]
        ]
        return sum(found) / len(found) if found else -1.0

    ordered = sorted(systems, key=lambda s: (places[s], -index_of(s), s))

    head = f"<th>{_t('Order')}</th>" + "".join(
        f"<th>{html.escape(_t(measures[key]['label']))}</th>" for key, _ in columns
    )
    body, shared = [], []
    previous = None
    for system in ordered:
        place = places[system]
        mark = "" if place == previous else " class='place'"
        previous = place
        cells = []
        for key, digits in columns:
            values = [
                _fmt(rows_by_judge[judge][system].metrics.headline.get(key), digits)
                for judge in judges
            ]
            differ = len({v for v in values if v != "--"}) > 1
            joined = " / ".join(values)
            css = " class='differ'" if differ else ""
            cells.append(f"<td{css}>{joined}</td>")
        index = " / ".join(
            f"{_rank_of(track, rows_by_judge[judge][system], varying):.2f}" for judge in judges
        )
        # Complete of the corpus, not of what this model managed to write.
        # Generation loss used to render as a bare "6" in the same column that
        # renders judge loss as "7 of 10", so a model that never wrote four of
        # its notes read as complete. The corpus is stated once, because both
        # judges read the same notes -- "8/10 / 9/10" made the slash mean two
        # things in one cell.
        rows_here = [rows_by_judge[judge][system] for judge in judges]
        complete = [r.n_sessions_scored - r.n_sessions_partial for r in rows_here]
        corpus = max(r.n_sessions_attempted or r.n_sessions_scored for r in rows_here)
        if len(set(complete)) == 1 and complete[0] == corpus:
            notes = str(corpus)
        else:
            notes = f"{' / '.join(str(c) for c in complete)} {_t('of')} {corpus}"
        body.append(
            f"<tr{mark}><td>{html.escape(system)}</td><td>{notes}</td>"
            f"<td><strong>{index}</strong></td>{''.join(cells)}</tr>"
        )
        shared.append(place)

    # Rows resting on well under their corpus, named. Measured against the
    # corpus and not against what the row happened to score: the single-judge
    # table used to test `complete < THIN * n_sessions_scored`, which marked a
    # model with nine notes of ten and never even considered one with six.
    thin = []
    for system in ordered:
        for judge in judges:
            row = rows_by_judge[judge][system]
            complete = row.n_sessions_scored - row.n_sessions_partial
            corpus = row.n_sessions_attempted or row.n_sessions_scored
            if corpus and complete < THIN * corpus:
                thin.append(f"{system} ({complete} {_t('of')} {corpus})")
                break

    ties = sum(1 for place in set(shared) if shared.count(place) > 1)
    lead = _t(MERGED_LEAD).format(judges=_join_words(judges))
    order_line = _t(MERGED_ORDER).format(places=len(set(shared)), systems=len(systems), tied=ties)
    warning = ""
    if thin:
        warning = (
            "<div class='warn'><p>"
            + html.escape(_t(THIN_ROWS))
            + f" {html.escape(', '.join(thin))}.</p></div>"
        )
    return (
        f"<p class='sub'>{html.escape(lead)} {html.escape(order_line)} "
        f"{html.escape(_t(NOTES_COLUMN))} {html.escape(_scale_line(track))}</p>"
        + f"<table><thead><tr><th>{_t('Model')}</th>"
        f"<th>{_t('Notes in the mean')}</th>{head}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>{warning}"
    )


#: What the notes column counts, said where it is read. It is the notes
#: complete on EVERY criterion, so an individual column may be a mean over
#: more of them -- a distinction the code's own docstring promised to print
#: under the table and never did.
NOTES_COLUMN = (
    "The notes column counts the ones every criterion of was answered, out of "
    "the sessions the model was asked for; a single column may average over more, "
    "because a note missing one answer still has the others."
)
THIN_ROWS = (
    "These rows rest on well under their corpus, either because the model did not "
    "write the note or because the judge did not answer it. What goes missing "
    "clusters on the longest sessions, so it is not a random sample. Read them as "
    "provisional:"
)

MERGED_LEAD = (
    "Every cell holds both judges, {judges}, in that order and never averaged: "
    "where they disagree about a model is the only control this track has, so it "
    "is shown rather than smoothed. A cell whose two numbers differ is marked."
)
MERGED_ORDER = (
    "The rows are ordered by dominance -- a model is above another only when it is "
    "at least as good on every column under BOTH judges -- so models the evidence "
    "cannot separate share a place, and {systems} models fall into {places} places "
    "of which {tied} hold more than one. Within a place the order is alphabetical "
    "and means nothing."
)


def _table(track: str, rows: list[results.Row]) -> str:
    """One comparability group, with the count behind each mean.

    **The count is of complete notes, not of scored ones**, and the two differ
    whenever a judge left a question unanswered. A note now counts in the
    columns it did answer -- it used to count in none of them -- so a row can be
    complete on six columns and thin on the seventh, and the per-column
    denominators under the table say which.

    The header count is still worth printing because it is the honest summary of
    how much of a model's corpus was answered end to end. This column once said
    `10` beside a row that averaged five notes.

    **The sort is named above the table.** A reader met an eight-column grid of
    decimals with nothing saying whether the top row was the best one, the first
    alphabetically, or the first by some column they had to guess. The rule is
    printed, and the columns it uses are listed, so a table where one column is
    doing all the work says so instead of looking like a verdict on six.
    """
    columns = COLUMNS[track]
    measures = MEASURE_TABLES[track]
    varying = _varying(track, rows)
    # The number the rows are ordered by, printed. Sorting by a figure and not
    # showing it asks the reader to take the order on trust -- and this project
    # sets `RANKING_MEASURE = None` for these tracks precisely because weighting
    # spelling against clinical terminology is a judgement rather than a
    # measurement. Both of those are reasons to SHOW it and say what it is, not
    # reasons to hide it: an unexplained order is the judgement made silently.
    head = f"<th>{_t('Order')}</th>" + "".join(
        f"<th>{html.escape(_t(measures[key]['label']))}</th>" for key, _ in columns
    )
    body, thin = [], []
    for row in sorted(rows, key=lambda r: (-_rank_of(track, r, varying), r.system_id)):
        complete = row.n_sessions_scored - row.n_sessions_partial
        index = _rank_of(track, row, varying)
        cells = f"<td><strong>{index:.2f}</strong></td>" + "".join(
            f"<td>{_fmt(row.metrics.headline.get(key), digits)}</td>" for key, digits in columns
        )
        # Against the corpus, not against what this row happened to score. The
        # test used to be `complete < THIN * n_sessions_scored` inside `if
        # n_sessions_partial`, so a model that wrote six notes of ten and had
        # all six answered was never even considered -- and one with nine of ten
        # answered was marked. It pointed at the wrong row.
        corpus = row.n_sessions_attempted or row.n_sessions_scored
        count = (
            str(complete)
            if complete == corpus
            else (f"<strong>{complete}</strong> {_t('of')} {corpus}")
        )
        if complete < THIN * corpus:
            thin.append(f"{row.system_id} ({complete} {_t('of')} {corpus})")
        body.append(f"<tr><td>{html.escape(row.system_id)}</td><td>{count}</td>{cells}</tr>")

    warning = ""
    if thin:
        warning = (
            "<div class='warn'><p>"
            + html.escape(
                _t(
                    "These rows are an average of well under all their notes, "
                    "because the judge left some questions unanswered and a note "
                    "is only counted when every criterion of it was answered:"
                )
            )
            + f" {html.escape(', '.join(thin))}. "
            + html.escape(
                _t(
                    "Unanswered questions cluster on the longer notes, so what is "
                    "missing is not a random sample of the corpus. Read these rows "
                    "as provisional."
                )
            )
            + "</p></div>"
        )
    return (
        f"<p class='sub'>{html.escape(_sort_line(track, varying))} "
        f"{html.escape(_scale_line(track))}</p>" + f"<table><thead><tr><th>{_t('Model')}</th>"
        f"<th>{_t('Notes in the mean')}</th>"
        f"{head}</tr></thead><tbody>{''.join(body)}</tbody></table>{warning}"
    )


def _definitions(track: str) -> str:
    measures = MEASURE_TABLES[track]
    items = []
    for key, _digits in COLUMNS[track]:
        measure = measures[key]
        items.append(
            f"<dt>{html.escape(_t(measure['label']))}</dt>"
            f"<dd>{html.escape(_trim(_t(measure['definition'])))}</dd>"
        )
    return (
        f"<p class='sub'>{html.escape(_scale_line(track))}</p>" + "<dl>" + "".join(items) + "</dl>"
    )


def check_no_clinical_text(rows: list[results.Row]) -> list[str]:
    """Whether any row carries something long enough to be a sentence of a session.

    `local/` is outside `tests/test_no_clinical_content.py`, which scans tracked
    files. This is the same guarantee for a document that is going to be sent to
    people: scores, counts and model names only.
    """
    problems = []
    for row in rows:
        # Pairs, not a dict. Keyed by field name, every failure reason after the
        # first would overwrite the one before it and only the last would ever
        # be checked -- in a function whose whole job is to check all of them.
        fields = [
            ("system_id", row.system_id),
            ("system_label", row.system_label),
            *(("failure_reason", key) for key in row.failure_reasons),
            *(("unreached_reason", key) for key in row.unreached_reasons),
        ]
        for name, value in fields:
            if len(str(value)) > MAX_FIELD_CHARS:
                problems.append(f"{row.track}/{row.system_id}: {name} is {len(value)} characters")
        if re.search(r"\d{4,}", row.system_id):
            problems.append(f"{row.track}: a system id carries a run of digits")
    return problems


#: The plain length table's own sentences.
LENGTH_TABLE_LEAD = (
    "The median length of one note, in words, for every model and every corpus it "
    "wrote for. These are the notes the models generated -- not anything a judge "
    "wrote. Everything the rest of this section claims is about these numbers."
)
LENGTH_TABLE_HUMAN = (
    "For scale: the therapist who wrote TN-Eval's reference notes used {human} words a note. {over}"
)
#: Filled by whether any model actually beats the therapist on any corpus. The
#: sentence used to end "and no model here reaches that", nine rows above a
#: table showing `glm-5.2` at 812 on the Czech real corpus.
LENGTH_TABLE_UNDER = "No model here reaches that on any corpus."
LENGTH_TABLE_OVER = (
    "Every model writes less than that on the English corpus, where nobody was given a "
    "length; on the Czech ones {names} write more."
)

#: The length section's own sentences. Every number in them is a placeholder
#: filled from `local/czech-length.json`, because a length that is typed into a
#: sentence is a length that a later run makes quietly false.
LENGTH_ASKED = (
    "{quiet} of the {families} prompt families say nothing at all about how long a "
    "note should be. "
    "The Deepsy prompt says it twice: a ceiling of {limit} words per section, which "
    "the prompt itself calls invalid to exceed, and a target of the same {limit} words."
)
LENGTH_HUMAN = (
    "The therapist who wrote the {n} reference notes for the English corpus used "
    "{human} words. Not one of the {systems} models comes near that: they write "
    "between {low} and {high} words, which is {share_low} to {share_high} of what the "
    "person wrote. Nobody set any of them a length, so this is what they do when left "
    "alone. It is the one place in this project where a human note can be compared "
    "with a model's at all, and the whole field of models sits on one side of it."
)
LENGTH_DEEPSY = (
    "Where a length WAS set, the ceiling was kept and the target was not. Only {over} "
    "of {answers} answers exceed the {limit}-word limit -- but {section} uses {share} "
    "of the length it was asked for. The models read \u201cmust not exceed\u201d and "
    "did not read \u201cthe target is {limit} words\u201d."
)
LENGTH_BUYS = (
    "The two languages then pull in opposite directions, and this is the most useful "
    "thing to know before reading any table above. In English a longer note scores "
    "higher for completeness under both judges. In Czech it scores lower on {against} "
    "of the {total} criterion-and-judge coefficients -- {soap_against} of "
    "{soap_total} on the SOAP halves and {deepsy_against} of {deepsy_total} in the "
    "Deepsy format, which is one reason the two are never pooled -- and the exceptions "
    "are named rather than rounded away: the columns where the coefficient stays "
    "positive under BOTH judges are {positive}. A column is printed here only when "
    "both judges agree on the direction and at least one of them reaches 0.40; both "
    "numbers are shown, so a column the two judges feel differently strongly about is "
    "visible as that rather than averaged away."
)
LENGTH_WARNING = (
    "Before reading that as \u201cthese models write worse Czech\u201d: each Czech "
    "criterion asks one yes/no question about a whole note -- is there a fault "
    "ANYWHERE in it. A SOAP note of {longest} words offers more places for one to be "
    "found than a SOAP note of {shortest}. The check is what happens to the same models "
    "under the other instrument: on the SOAP language criteria the three "
    "longest-writing models take the last three places {hit} times out of {total}, and "
    "on PDSQI-9, rating the very same notes, they do not. Part of the bottom of the "
    "Czech SOAP tables is length, not Czech."
)
#: The same test on the other note format, said rather than folded into the
#: count above it. Folded in, the sentence read "4 times out of 8" -- half the
#: time -- when the truth is every SOAP table and no Deepsy one, which is a
#: result about the formats rather than a weaker version of the SOAP finding.
LENGTH_WARNING_DEEPSY = (
    "The same test in the Deepsy format comes out {hit} of its {total} tables, and the "
    "three models that write longest there are a different three, because the two "
    "formats were not asked of the same models. Where the last three places go is a "
    "fact about the SOAP halves rather than a law about length."
)


#: What a column catches once it has met a hundred real notes, in words.
#:
#: The verdict beside each one in the table is computed from the rows; this is
#: the half a computation cannot supply. Both halves are on the page because a
#: reader handed "0.67" without either will supply their own reading, and theirs
#: will be more generous than the evidence.
#:
#: **No rater figure is written here.** Five of them were, and four disagreed
#: with `local/czech-anchor.json` -- which this same document prints three
#: sections later. One measurement, twice in one document, two sets of numbers.
#: The agreement with the native speaker is now appended from the payload by
#: `_catch`, so the two can no longer drift apart.
WHAT_IT_CATCHES = {
    "diacritics": ("Reliable: the two judges answered the same way on 79% of notes."),
    "calque": (
        "The weakest column here, and it should be read as a flag rather than a "
        "score. The two judges agree on only 67% of notes, the lowest of the six. "
        "Whether a Czech phrase is a literal translation from English is a "
        "judgement people make differently, and these numbers show that rather "
        "than hiding it."
    ),
    "untranslated": (
        "Reliable, and the fault it catches is unambiguous: an English term sitting "
        "in a Czech sentence. Judges agree on 87% of notes."
    ),
    "agreement": (
        "Catches real grammatical faults, but the two judges answer differently on "
        "a quarter of notes. A gap of one or two notes between models is inside "
        "that noise."
    ),
    "register": (
        "Catches colloquial words where clinical ones belong. Judges agree on 75% of notes."
    ),
    "quotes": (
        "Read this one against the prompt, not against the models. The same models "
        "on the same sessions score 0.00 here and 0.90 to 1.00 in the Deepsy format, "
        "and the prompt behind this table contains no Czech quotation mark at all "
        "while the Deepsy one does. "
        "Exact. It is not a judgement at all any more -- the characters in the note "
        "are counted. It became a count after a native speaker and a judge disagreed "
        "on nearly half the notes and neither was wrong: the question named only the "
        "straight double mark, and 45 of the 75 notes that quote anything use an "
        "apostrophe instead. The question now names both."
    ),
    "nonword": (
        "The strongest agreement with a person under one judge, and tied with Diacritics over both."
    ),
    "accurate": (
        "The most informative column in this document, and it exists only on the "
        "translated half, because answering it means reading the session. The two "
        "judges order the models almost identically here."
    ),
    "thorough": (
        "Also only on the translated half. The judges agree far less about it than "
        "about accuracy, so read large gaps and ignore small ones."
    ),
    "useful": ("Says almost nothing. One judge gave 5.00 to every model."),
    "organized": (
        "Says nothing, and this was written down before the run rather than after. "
        "Every model writes into the same four-part template because the prompt "
        "tells it to, so a question about structure has nothing left to separate."
    ),
    "comprehensible": ("Does not separate the models: most of them print the same value."),
    "succinct": (
        "Works, and every model fails it. No model reaches the middle of the scale "
        "under either judge. This is the one column on the real half that tells the "
        "models apart at all."
    ),
    "synthesized": ("Says nothing. 5.00 for every model under both judges on both halves."),
    "stigmatizing": (
        "Does not separate the models. Most of them are free of it, which is the "
        "good news and also why the column cannot rank anything."
    ),
}


#: The one track these hand-written verdicts and the rater figure were measured
#: on. Everything in `WHAT_IT_CATCHES` about how often the judges agree, and
#: every number in `local/czech-anchor.json`, comes from the ten real Czech
#: sessions scored by the criteria. Printed under the PDSQI and Deepsy tables it
#: said something measured elsewhere about a table it was not measured on -- on
#: the Deepsy notes `untranslated` agrees on 63% and was being described as 87%
#: and "reliable", which inverts the row's verdict.
ANCHORED_ON = results.TRACK_CZECH_REAL

#: What the cell says where there is nothing to put in it. An empty cell is not
#: an omission a reader can read: thirty-six of them sat under a heading
#: promising what is behind the number and under a lead promising it for "any
#: column here", and a blank says neither "measured and unremarkable" nor "never
#: measured". Omitting the figure is right; leaving the gap unnamed is not.
NOT_MEASURED_HERE = "not measured on this track"


def _catch(key: str, track: str) -> str:
    """What a column catches, in this run's language, or where it was not asked.

    A column with no sentence written for it says so rather than raising: the
    verdict beside it is still counted and still worth reading, and a missing
    sentence is a gap in the prose rather than in the measurement.

    **Only under the track it was measured on.** These sentences quote judge
    agreement and a native speaker's; both were measured on the real Czech
    sessions under the criteria rubric, and nobody has rated a Deepsy note or a
    translated one by hand at all. Importing them would be reporting one
    table's number under another's heading -- on the Deepsy notes `untranslated`
    agrees on 63% and was being described as 87% and "reliable".

    So the figure is omitted and the gap is named, which is this repository's
    rule about a missing measurement and was two thirds kept: the omitting was
    done and the naming was not.
    """
    written = WHAT_IT_CATCHES.get(key, "") if track == ANCHORED_ON else ""
    if not written:
        return _t(NOT_MEASURED_HERE)
    return f"{_t(written)} {_rater(key)}".strip()


def _rater(key: str) -> str:
    """How often the one native speaker said what each judge said, from the payload.

    Empty when the criterion was not in the sample, which is a gap in the anchor
    rather than in the column -- and an empty string says that better than a
    zero would.
    """
    path = REPO / "local" / "czech-anchor.json"
    if not path.exists():
        return ""
    data = json.loads(path.read_text(encoding="utf-8"))
    pairs = []
    for judge in sorted(data.get("judges", {})):
        found = data["judges"][judge].get("criteria", {}).get(key)
        if found and found.get("compared"):
            pairs.append(f"{found['agreed']}/{found['compared']}")
    if not pairs:
        return ""
    return _t("One native speaker agreed with the two judges on {pairs} notes.").format(
        pairs=_join_words(pairs)
    )


def _calls(track: str, notes: int) -> str:
    """How many answers a model had to give to produce that many notes.

    Read off the task rather than typed, because it is the one number here that
    is not one per note: the Deepsy format asks for each section separately, so
    220 notes are 660 calls. A track that rates notes somebody else generated --
    both PDSQI tracks -- generated nothing and says so with a dash.
    """
    task = next((t for name, t in TASKS.items() if results.TRACK_BY_TASK.get(name) == track), None)
    if task is None:
        return "<span class='dash'>&mdash;</span>"
    return str(notes * task.calls_per_session)


def _scale(rows: list[results.Row]) -> str:
    """How many notes and how many questions, and on whose machines.

    Counted from the rows rather than typed, so it cannot drift from what was
    actually run. It belongs in the method for two reasons: a reader judging
    whether ten notes per model is enough needs the number in front of them,
    and **where each step ran is the confidentiality boundary** -- the notes
    were written on the infrastructure that holds the sessions, and only the
    notes went anywhere else.

    No money. A price is a fact about a vendor's list on one day, not about
    this benchmark, and a figure without that day attached is unreadable a year
    later -- the same reason the external index carries its version.
    """
    latest = [row for row in results.latest(rows) if row.is_scored]
    if not latest:
        return ""

    drawn_tracks = set()

    lines = []
    for track in results.LOCAL_TRACKS:
        here = [row for row in latest if row.track == track]
        if not here:
            continue
        newest = max(row.judge_prompt_version for row in here)
        drawn = [row for row in here if row.judge_prompt_version == newest]
        drawn_tracks.add(track)
        rating = sorted({row.judge_model or "" for row in drawn})
        notes = sum(row.n_sessions_scored for row in drawn) // max(1, len(rating))
        models = len({row.system_id for row in drawn})
        lines.append(
            f"<tr><td>{html.escape(_t(TRACK_TITLES.get(track, track)))}</td>"
            f"<td>{models}</td><td>{notes}</td><td>{_calls(track, notes)}</td>"
            f"<td>{len(rating)}</td></tr>"
        )
    if not lines:
        return ""

    # Over all four criteria tracks, not the two SOAP ones. This footnote sat
    # under a six-row table, said "11 models wrote 212 notes in all" of 13 and
    # 450, and then explained the difference with a clause -- each note read
    # twice, once against PDSQI-9 -- that is false of the 238 Deepsy notes,
    # which no PDSQI judge has ever seen.
    figures = _written_figures(rows)
    footnote = _t(SCALE_NOT_ADDITIVE).format(**figures)
    # Said only when the rows it points at are drawn. A sentence explaining why
    # two rows below cost three times the calls is a puzzle, not an
    # explanation, on a run where those two rows have not been scored yet.
    deepsy = {results.TRACK_DEEPSY_REAL, results.TRACK_DEEPSY_TRANSLATED}
    deepsy_note = ""
    if drawn_tracks & deepsy:
        footnote += " " + _t(SCALE_NO_PDSQI).format(**figures)
        deepsy_note = " " + html.escape(
            _t(
                "The Deepsy format is asked for one section at a time, so a note there "
                "is three answers rather than one: the same number of notes costs three "
                "times the calls."
            )
        )
    return (
        f"<h3>{_t('What it took')}</h3>"
        + "<p>"
        + html.escape(
            _t(
                "Every note was written on e-INFRA, the infrastructure that holds the "
                "sessions. Only the notes went anywhere else: each was put to two "
                "judges, one question per criterion, on Google's and OpenAI's "
                "endpoints."
            )
        )
        + deepsy_note
        + "</p>"
        + f"<table><thead><tr><th>{_t('Track')}</th><th>{_t('Models')}</th>"
        + f"<th>{_t('Notes')}</th><th>{_t('Calls to write them')}</th>"
        + f"<th>{_t('Judges')}</th></tr></thead>"
        + f"<tbody>{''.join(lines)}</tbody></table>"
        + f"<p class='dash'>{html.escape(footnote)}</p>"
    )


def _corpus() -> str:
    """What the two halves are, counted rather than asserted.

    The sentence this replaces said "ten real sessions ... plus ten AnnoMI
    conversations translated into spoken Czech", which is true and hides the
    thing a reader most needs: **the real sessions are seven times longer.**
    A median of 5,266 words against 699, and 113 turns against 52. Summarising
    an hour of talk and summarising ten minutes of it are not the same task, so
    any sentence comparing the two halves is comparing that too.

    Counts only -- session totals, medians, ranges. No transcript text reaches
    this document, which `check_no_clinical_text` asserts separately.
    """
    from tnb.tasks import czech as czech_task

    rows = []
    for label, load, note in (
        (
            "Real sessions",
            czech_task.load_real,
            "one client, de-identified by hand, never released",
        ),
        (
            "Translated AnnoMI",
            czech_task.load_translated,
            "public counselling conversations, translated for this track",
        ),
    ):
        try:
            sessions = load()
        except (RuntimeError, OSError):
            continue
        if not sessions:
            continue
        words = sorted(session.word_count for session in sessions)
        turns = sorted(len(session.turns) for session in sessions)
        middle = len(words) // 2
        rows.append(
            f"<tr><td>{html.escape(_t(label))}</td><td>{len(sessions)}</td>"
            f"<td>{_grouped(words[middle])}</td>"
            f"<td>{_grouped(words[0])}&ndash;{_grouped(words[-1])}</td>"
            f"<td>{turns[middle]}</td>"
            f"<td class='sub'>{html.escape(_t(note))}</td></tr>"
        )
    if not rows:
        return ""
    return (
        f"<h3>{_t('The two corpora')}</h3>"
        f"<table><thead><tr><th>{_t('Half')}</th><th>{_t('Sessions')}</th>"
        f"<th>{_t('Words, median')}</th><th>{_t('Words, range')}</th>"
        f"<th>{_t('Turns, median')}</th><th></th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _halves(rows: list[results.Row]) -> str:
    """Do the models write better Czech on the real sessions or the translated ones?

    The question the two tables invite and neither answers, so it is answered
    here with the numbers side by side -- and with the reason the answer stops
    short of a claim.
    """
    latest = [row for row in results.latest(rows) if row.is_scored]
    newest = {}
    for row in latest:
        if row.track in (results.TRACK_CZECH_REAL, results.TRACK_CZECH_TRANSLATED):
            newest[row.judge_prompt_version] = max(
                newest.get(row.judge_prompt_version, ""), row.scored_at or ""
            )
    if not newest:
        return ""
    rubric = max(newest, key=lambda version: newest[version])

    judges = sorted({row.judge_model or "" for row in latest if row.judge_prompt_version == rubric})
    if not judges:
        return ""

    def mean_of(track: str, judge_model: str, key: str) -> float | None:
        values = [
            row.metrics.headline[key]
            for row in latest
            if row.track == track
            and row.judge_model == judge_model
            and row.judge_prompt_version == rubric
            and key in row.metrics.headline
        ]
        return sum(values) / len(values) if values else None

    body = []
    for key in czech_scorer.CRITERION_KEYS:
        cells = []
        drawn = False
        for judge_model in judges:
            real = mean_of(results.TRACK_CZECH_REAL, judge_model, key)
            translated = mean_of(results.TRACK_CZECH_TRANSLATED, judge_model, key)
            if real is None or translated is None:
                cells.append("<td class='dash'>--</td><td class='dash'>--</td>")
                continue
            drawn = True
            better = "<strong>" if translated > real else ""
            close = "</strong>" if translated > real else ""
            cells.append(f"<td>{real:.2f}</td><td>{better}{translated:.2f}{close}</td>")
        if drawn:
            label = _t(MEASURE_TABLES[results.TRACK_CZECH_REAL][key]["label"])
            body.append(f"<tr><td>{html.escape(label)}</td>" + "".join(cells) + "</tr>")
    if not body:
        return ""

    head = "".join(
        f"<th>{html.escape(name)}: {_t('real')}</th>"
        f"<th>{html.escape(name)}: {_t('translated')}</th>"
        for name in judges
    )
    return (
        f"<h2>{_t('Real sessions or translated ones?')}</h2>"
        + "<p>"
        + html.escape(
            _t(
                "The translated half comes out ahead on four of the six criteria "
                "under both judges. Each judge alone gives it five, but not the same "
                "five: gemini-3.1-pro-preview puts the real half ahead on Register and "
                "gpt-5.6-terra on Untranslated terms, and neither reversal is rounding. "
                "Bold marks where translated beats real."
            )
        )
        + "</p>"
        + f"<table><thead><tr><th>{_t('Criterion')}</th>{head}</tr></thead>"
        + f"<tbody>{''.join(body)}</tbody></table>"
        + "<div class='warn'><p><strong>"
        + html.escape(_t("It does not follow that the models write better Czech there."))
        + "</strong> "
        + html.escape(
            _t(
                "A real session runs seven times longer, the notes written from it are "
                "longer in turn, and every criterion asks whether a note contains a "
                "fault -- more text, more chances to have one. Matching the two halves "
                "on note length shrinks the gap but does not settle it: of three length "
                "bands, two still favour the translated half and one favours the real "
                "one, on 18 to 59 notes each. The halves also differ in topic and in "
                "who transcribed them. This comparison is worth printing and is not "
                "worth concluding from."
            )
        )
        + "</p></div>"
    )


def _verdicts(rows: list[results.Row]) -> str:
    """Which columns tell the models apart, counted rather than asserted.

    The tie count is the largest group of systems printing the same value, taken
    on whichever judge ties worst -- `concordance.MeasureAgreement.rankable`'s
    rule, applied here so the briefing states it in the same terms the page
    does. A column on which most systems are indistinguishable cannot rank them,
    whatever the rest of the table does.

    **Newest rubric only.** This selected on the track alone, so where a
    criterion had been redefined it counted both versions and reported 22
    systems where the page draws 11 -- while two sections earlier the document
    says the older rows are a different instrument and are named rather than
    drawn beside these. It drew them beside these, invisibly, and the
    unexplained denominator was the only sign.
    """
    latest = [row for row in results.latest(rows) if row.is_scored]
    blocks = []
    for track in results.LOCAL_TRACKS:
        here = [row for row in latest if row.track == track]
        if not here:
            continue
        newest = max(row.judge_prompt_version for row in here)
        here = [row for row in here if row.judge_prompt_version == newest]
        judges = sorted({row.judge_model or "" for row in here})
        lines = []
        for key, digits in COLUMNS[track]:
            worst_tied, n = 0, 0
            for judge_model in judges:
                printed = collections.Counter(
                    f"{row.metrics.headline[key]:.{digits}f}"
                    for row in here
                    if judge_model == (row.judge_model or "") and key in row.metrics.headline
                )
                if not printed:
                    continue
                n = max(n, sum(printed.values()))
                worst_tied = max(worst_tied, printed.most_common(1)[0][1])
            if not n:
                continue
            separates = n >= 2 and worst_tied * 2 <= n
            verdict = (
                f"{_t('tells')} {n - worst_tied} {_t('of')} {n} {_t('apart')}"
                if separates
                else (
                    f"<strong>{_t('cannot rank')}</strong> — {worst_tied} "
                    f"{_t('of')} {n} {_t('share one value')}"
                )
            )
            lines.append(
                f"<tr><td>{html.escape(_t(MEASURE_TABLES[track][key]['label']))}</td>"
                f"<td>{verdict}</td>"
                f"<td class='sub'>{html.escape(_catch(key, track))}</td></tr>"
            )
        if lines:
            blocks.append(
                f"<h3>{html.escape(_t(TRACK_TITLES.get(track, track)))} "
                f"<span class='dash'>&mdash; {_t('which columns can rank')}</span></h3>"
                f"<table><thead><tr><th>{_t('Column')}</th>"
                f"<th>{_t('Does it separate the models?')}</th>"
                f"<th>{_t('What is behind the number')}</th></tr></thead>"
                f"<tbody>{''.join(lines)}</tbody></table>"
            )

    if not blocks:
        return ""
    return (
        f"<h2>{_t('What is behind each number')}</h2>"
        + "<p>"
        + html.escape(
            _t(
                "A column that gives most models the same value cannot rank them, "
                "however confidently it is printed, and the first thing worth "
                "knowing about any column here is whether it separates anything at "
                "all. That half is counted from the rows. The second half — what the "
                "column actually catches, and how far two judges and one native "
                "speaker agreed about it — is written down rather than computed, "
                "because no arithmetic supplies it. It exists for one table only: "
                "both agreement figures were measured on the real Czech sessions "
                "under the six criteria, and nobody has read a Deepsy note, a "
                "translated one or a PDSQI answer against a person at all. Every "
                "other table says so in the cell rather than leaving it blank, "
                "because carrying a number across would report one table's "
                "measurement under another's heading."
            )
        )
        + "</p>"
        + "".join(blocks)
    )


def _join() -> str:
    """The question the track was built for, answered in the document that leaves.

    Written by `tools/czech_join.py`. Two tables, because there are two answers:
    the same instrument asked in both languages transfers, and the measure the
    English page actually ranks by does not. Printing only the first would be
    the more flattering half.

    A cell carries its p-value because nine models invite over-reading, and the
    two judges sit side by side because the reading rule is "believe a column
    that says the same thing under both".
    """
    path = REPO / "local" / "czech-join.json"
    if not path.exists():
        return ""
    data = json.loads(path.read_text(encoding="utf-8"))
    judges = sorted(data.get("judges", {}))
    if not judges:
        return ""

    labels = MEASURE_TABLES[results.TRACK_CZECH_TRANSLATED_PDSQI]

    def block(field: str, heading: str, lead: str) -> str:
        keys, rows = [], []
        for name in judges:
            for key in data["judges"][name].get(field, {}):
                if key not in keys:
                    keys.append(key)
        if not keys:
            return ""
        for key in keys:
            cells = []
            for name in judges:
                entry = data["judges"][name].get(field, {}).get(key)
                if not entry:
                    cells.append(f"<td class='dash'>{_t('flat')}</td>")
                    continue
                strong = "<strong>" if entry["p"] < 0.05 else ""
                close = "</strong>" if entry["p"] < 0.05 else ""
                cells.append(
                    f"<td>{strong}{entry['rho']:+.2f}{close}"
                    f" <span class='dash'>p={entry['p']:.3f}</span></td>"
                )
            label = _t(labels.get(key, {}).get("label", key))
            rows.append(f"<tr><td>{html.escape(label)}</td>" + "".join(cells) + "</tr>")
        head = "".join(f"<th>{html.escape(name)}</th>" for name in judges)
        return (
            f"<h3>{html.escape(heading)}</h3><p>{html.escape(lead)}</p>"
            f"<table><thead><tr><th>{_t('Attribute')}</th>{head}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )

    flat = sorted({key for name in judges for key in data["judges"][name].get("flat", [])})
    ranking = data["judges"][judges[0]].get("ranking_measure", "the ranking measure")
    systems = len(data["judges"][judges[0]].get("systems", []))

    return (
        f"<h2>{_t('Does the English leaderboard predict the Czech?')}</h2>"
        + f"<p>{systems} "
        + html.escape(
            _t(
                "models. Whether a standing in one predicts a standing in the other "
                "has two answers, and which one a reader gets depends on which "
                "English number they were looking at. Bold is a correlation that "
                "survives an exact permutation test at p < 0.05."
            )
        )
        + "</p>"
        + block(
            "same_instrument",
            _t("Asked the same question, quality transfers"),
            _t(
                "PDSQI-9 on the English notes against PDSQI-9 on the Czech ones. Same "
                "attributes, same anchors, same judge; only the language of the note "
                "differs."
            ),
        )
        + block(
            "leaderboard_ranking",
            _t("Asked the leaderboard's own measure, it does not"),
            f"{ranking} "
            + _t(
                "-- what the page sorts by, so what a position means -- against the "
                "Czech quality columns. Nothing here survives the test, and the two "
                "judges do not agree even on the sign."
            ),
        )
        + (
            f"<p class='sub'>{_t('Flat on one side and therefore not correlated:')} "
            f"{html.escape(', '.join(flat))}.</p>"
            if flat
            else ""
        )
        + f"<div class='warn'><p>{html.escape(_t(data.get('confound', '')))} "
        f"{html.escape(_t(data.get('reading', '')))}</p></div>"
    )


#: What to say instead of a table in which nothing cleared the test.
EXTERNAL_NOTHING = (
    "Nothing here. All {cells} coefficients between {what} and what this project "
    "measures are inside what chance produces at this sample size, under both "
    "judges. Printed as a sentence rather than as a grid of numbers a reader has "
    "to work out says nothing."
)


def _external() -> str:
    """Whether a model's general capability predicts the notes it writes.

    Written by `tools/czech_external.py`. The section exists at all only
    because the answer differs between the two languages, and it carries its
    provenance in the same breath as its numbers because none of the data
    behind it was measured here.

    Three caveats travel with it and none is decoration. The match is by name,
    and this repository's first working rule exists because a name lied. The
    external score is versioned, so a figure without its index version and
    fetch date is unattributable in a month. And the models that could not be
    matched are named rather than quietly dropped.
    """
    path = REPO / "local" / "czech-external.json"
    if not path.exists():
        return ""
    data = json.loads(path.read_text(encoding="utf-8"))
    judges = sorted(data.get("judges", {}))
    if not judges:
        return ""

    labels = {
        "english_completeness": "English completeness",
        "english_quality": "English quality (PDSQI-9)",
        "czech_quality": "Czech quality (PDSQI-9)",
        "czech_language": "Czech language (the six criteria)",
    }
    outside = {
        "intelligence_index": "Intelligence index",
        "release_date": "Release date",
    }

    blocks = []
    for label, heading in outside.items():
        rows = []
        significant = 0
        for measure, name in labels.items():
            cells = []
            drawn = False
            for judge_model in judges:
                entry = (data["judges"][judge_model].get(measure) or {}).get(label)
                if not entry:
                    cells.append("<td class='dash'>--</td>")
                    continue
                drawn = True
                significant += entry["p"] < 0.05
                strong = "<strong>" if entry["p"] < 0.05 else ""
                close = "</strong>" if entry["p"] < 0.05 else ""
                cells.append(
                    f"<td>{strong}{entry['rho']:+.2f}{close}"
                    f" <span class='dash'>p={entry['p']:.3f}, n={entry['n']}</span></td>"
                )
            if drawn:
                rows.append(f"<tr><td>{html.escape(_t(name))}</td>" + "".join(cells) + "</tr>")
        if not rows:
            continue
        # A table where nothing cleared the test is a grid of noise. Say the
        # result in a sentence instead: eight coefficients, none of them
        # separable from chance, is a finding and not a table.
        if not significant:
            blocks.append(
                f"<h3>{html.escape(_t(heading))}</h3><p>"
                + html.escape(
                    _t(EXTERNAL_NOTHING).format(
                        what=_t(heading).lower(), cells=len(rows) * len(judges)
                    )
                )
                + "</p>"
            )
            continue
        # The judge is the COLUMN, and the header used to be the bare model
        # name -- so a table about model capability appeared to have two of the
        # vendors' models as its subjects. They are not measured here; they are
        # who was asked.
        head = "".join(
            f"<th>{html.escape(_t('as {judge} sees it').format(judge=j))}</th>" for j in judges
        )
        blocks.append(
            f"<h3>{html.escape(_t(heading))}</h3>"
            f"<table><thead><tr><th>{_t('Measured here')}</th>{head}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )
    if not blocks:
        return ""

    unmatched = ", ".join(data.get("unmatched", []))
    return (
        f"<h2>{_t('Does general capability predict any of this?')}</h2>"
        + "<p>"
        + html.escape(
            _t(
                "Nothing in this repository records how big a model is or when it "
                "shipped, so this comes from outside it. Bold survives a permutation "
                "test at p < 0.05."
            )
        )
        + "</p>"
        + "".join(blocks)
        + "<div class='warn'><p><strong>"
        + html.escape(_t("None of this was measured here."))
        + "</strong> "
        + html.escape(
            _t(
                "The models are matched to the public ones by name, and a name on the "
                "endpoint is not evidence about which model is behind it -- this "
                "project's first working rule exists because one returned another's "
                "output. Models whose name does not identify a variant are absent "
                "rather than guessed:"
            )
        )
        + f" {html.escape(unmatched)}. "
        + html.escape(
            _t(
                "The external score is versioned like the measures here are, so it is "
                "recorded with the version and the day it was read:"
            )
        )
        + f" {html.escape(data.get('index_version', ''))}, "
        + f"{html.escape(data.get('fetched', ''))}.</p></div>"
    )


#: What to call each set of columns, so the one definition list per instrument
#: has a name a reader recognises rather than the name of whichever track
#: happened to be drawn first.
INSTRUMENT_OF = {
    results.TRACK_CZECH_REAL: "the six Czech criteria",
    results.TRACK_CZECH_TRANSLATED: "the six Czech criteria",
    results.TRACK_DEEPSY_REAL: "the six Czech criteria",
    results.TRACK_DEEPSY_TRANSLATED: "the six Czech criteria",
    results.TRACK_CZECH_REAL_PDSQI: "PDSQI-9, without the session",
    results.TRACK_CZECH_TRANSLATED_PDSQI: "PDSQI-9, with the session",
}


def _intro(rows: list[results.Row]) -> str:
    """The opening sentence, with what was actually written rather than asked.

    It said "eleven models wrote a note from each of twenty sessions" four times
    over, and two models did not: `qwen3.8-flash-next` produced six of ten on
    the real corpus and `qwen3.8-27b` eight. The claim is the one the whole
    model-to-model comparison rests on -- every model seeing every transcript --
    so stating it where it is false is the worst place in the document to have
    a hand-typed number.

    **All four criteria tracks, because the document draws all four.** Counted
    over the two SOAP halves alone it opened "11 models ... 212 of the 220
    notes" above six tables covering 13 models and 450 notes, and a reader who
    added the table up got a different number from the sentence introducing it.
    """
    figures = _written_figures(rows)
    if figures["written"] == "0":
        return html.escape(_t(INTRO).format(models="?", written="?", asked="?"))
    return html.escape(_t(INTRO).format(**figures))


def _refused_on_deepsy(models: set[str]) -> dict[str, int]:
    """Of these models, which wrote no Deepsy note because the endpoint refused.

    Counted from the generation cache rather than from the tables, because a
    model that produced nothing has no row to carry the reason. Only models the
    endpoint actually refused are returned: one that was simply never asked is
    not the same claim, and neither is one that answered and wrote badly.

    This exists so a band can say why a name is missing from it. `glm-5.3-flash`
    is in the bottom band of all four SOAP tables and in none of the Deepsy
    ones, and the difference is 57 errors from e-INFRA, not a better note.
    Left unsaid, its absence reads as a measurement nobody made.

    Both counters are summed. `reasons` holds what the endpoint never answered
    and `failure_reasons` what the model is charged with, but for this model
    both hold HTTP 400s and 500s -- the request refused before anything was
    written. Counting only the first would report 25 of the 57 errors and let
    the rest read as bad notes.
    """
    refused: dict[str, int] = {}
    for track in DEEPSY_CRITERIA_TRACKS:
        for (_provider, system_id), unreached in _unreached(track).items():
            if system_id not in models:
                continue
            errors = sum(unreached.reasons.values()) + sum(unreached.failure_reasons.values())
            if errors:
                refused[system_id] = refused.get(system_id, 0) + errors
    return refused


def _wrote(rows: list[results.Row]) -> dict[str, dict]:
    """Per track: how many notes each model wrote, out of the corpus.

    Two questions, and this document has answered the wrong one. What a model
    wrote comes from the rows. What it was ASKED for cannot: a model the
    endpoint refused every single time has no row to be counted in, and leaving
    it out makes the shortfall smaller than it was -- `glm-5.3-flash` has no
    Deepsy row at all, so a denominator read off the rows quietly drops twenty
    notes that were asked for and never came back.

    Those models are read from the generation cache and enter with a zero, named
    rather than absent. A model that appears there was asked; how much of the
    corpus it was asked for is the corpus, because every model is asked every
    session.
    """
    latest = [row for row in results.latest(rows) if row.is_scored]
    out: dict[str, dict] = {}
    for track in results.LOCAL_TRACKS:
        here = [row for row in latest if row.track == track]
        if not here:
            continue
        newest = max(row.judge_prompt_version for row in here)
        drawn = [row for row in here if row.judge_prompt_version == newest]
        wrote: dict[str, int] = {}
        for row in drawn:
            wrote[row.system_id] = max(wrote.get(row.system_id, 0), row.n_sessions_generated)
        corpus = max(row.n_sessions_attempted or row.n_sessions_generated for row in drawn)
        # Only the tracks that generate. A PDSQI track rates notes the SOAP
        # tracks wrote, so "the endpoint refused this model" is a question about
        # the track that asked for the note and not about the one rating it.
        if track in SOAP_CRITERIA_TRACKS + DEEPSY_CRITERIA_TRACKS:
            for system_id in _refused_entirely(track, set(wrote)):
                wrote[system_id] = 0
        out[track] = {"corpus": corpus, "wrote": wrote}
    return out


@functools.cache
def _unreached(track: str) -> dict[tuple[str, str], results.Unreached]:
    """What never got written on one track, read once per run.

    `results.unreached_by_system` walks the whole generation cache, and this
    document now asks it about six tracks from five places -- which took the
    build from five seconds to nearly a minute. The answer cannot change while
    one document is being written, so it is read once and kept.
    """
    return results.unreached_by_system(track)


def _refused_entirely(track: str, wrote: set[str]) -> dict[str, int]:
    """Models this track asked and got nothing at all from, with the error count.

    The complement of `_refused_on_deepsy`, which asks about named models on the
    two Deepsy tracks. This asks the question a denominator needs: of everything
    the endpoint was asked on this track, what produced no row.
    """
    refused: dict[str, int] = {}
    for (_provider, system_id), unreached in _unreached(track).items():
        if system_id in wrote:
            continue
        errors = sum(unreached.reasons.values()) + sum(unreached.failure_reasons.values())
        if errors:
            refused[system_id] = errors
    return refused


def _written_figures(rows: list[results.Row]) -> dict[str, str]:
    """The scale of the run, and where it fell short, as sentence placeholders.

    Every sentence about "every model wrote a note from every transcript" was a
    statement of the design read as a statement of the outcome, and the same
    page now names the 57 calls e-INFRA refused. So the design is stated as a
    design and the outcome is counted beside it, per track, with the models
    named -- which is what the intro already promises when it says the missing
    notes are named where they are missing.
    """
    # The four criteria tracks. A PDSQI track rates notes those wrote rather
    # than writing any, so counting its rows too reports every SOAP note twice.
    written_on = SOAP_CRITERIA_TRACKS + DEEPSY_CRITERIA_TRACKS
    found = {t: b for t, b in _wrote(rows).items() if t in written_on}
    written = sum(sum(block["wrote"].values()) for block in found.values())
    asked = sum(block["corpus"] * len(block["wrote"]) for block in found.values())
    models = {system for block in found.values() for system in block["wrote"]}
    soap = sum(
        sum(block["wrote"].values())
        for track, block in found.items()
        if track in SOAP_CRITERIA_TRACKS
    )
    short = []
    for track, block in found.items():
        names = [
            f"{system} {count}"
            for system, count in sorted(block["wrote"].items())
            if count < block["corpus"]
        ]
        if names:
            short.append(
                f"{_t(TRACK_SWITCH_LABELS.get(track, track))} — "
                f"{_join_words(names)} {_t('of')} {block['corpus']}"
            )
    return {
        "models": str(len(models)),
        "written": str(written),
        "asked": str(asked),
        "soap": str(soap),
        "deepsy": str(written - soap),
        "short": "; ".join(short),
    }


def _conclusion(rows: list[results.Row]) -> str:
    """What eleven models did, before the reader meets a single table.

    The document used to close on its own limitations and its method, and the
    first sentence anywhere stating a RESULT arrived pages in. A clinical team
    handed thirty tables and no conclusion writes its own, and theirs will be
    more generous than the evidence.

    **Every sentence here is computed from a payload already on disk.** Nothing
    is typed. That is not tidiness: the last time this document carried
    hand-written figures, four of five had drifted away from the table printing
    the same measurement three sections below.

    It is deliberately short, and it deliberately leads with the finding that
    changes how every table below is read rather than with the winner.
    """
    said = []

    bands = _payload("czech-variance.json").get("bands", {})
    # Named tracks, not "everything that is not PDSQI". That filter was written
    # when the only criteria tracks were the two SOAP halves, and it silently
    # swept the Deepsy tables into the same intersection the moment they were
    # banded -- pooling two note formats into one "all N tables" claim, which
    # section 4 of this document spends a page refusing to do.
    soap = {t: j for t, j in bands.items() if t in SOAP_CRITERIA_TRACKS}
    deepsy = {t: j for t, j in bands.items() if t in DEEPSY_CRITERIA_TRACKS}
    quality = {t: j for t, j in bands.items() if t.endswith("-pdsqi")}

    def shared(group: dict, index: int) -> tuple[list[str], int]:
        seen = [set(g["bands"][index]["models"]) for j in group.values() for g in j.values()]
        return (sorted(set.intersection(*seen)) if seen else []), len(seen)

    def end(models: list[str], *, lead: bool = False) -> str:
        """`X is`, `X and Y are`, or `No model is` -- subject and verb together.

        One model is, two models are, and no model *is*. The verb used to be a
        separate placeholder, which read wrong whenever the two ends of the
        sentence held different numbers of models, and had no branch at all for
        an empty end. An empty end became reachable the moment a second group of
        tables could be intersected. Subject and verb are one translated unit
        because the empty case is not a conjugation of the others: English picks
        a verb form, Czech negates the verb instead, so the word standing where
        "is" stands cannot be the same word in both the empty and the one-model
        case. The Czech itself lives in `czech_brief_cs.py`, which is the only
        tool file allowed to hold it.

        `lead` says whether the phrase opens its sentence. Only the empty case
        is ever recased -- a model id is written the way it is deployed, and
        `deepseek-v4-flash` does not become `Deepseek-v4-flash` at a full stop.
        """
        if not models:
            phrase = _t("No model is")
            return phrase if lead else phrase[:1].lower() + phrase[1:]
        return f"{_join_words(models)} {_t('is') if len(models) == 1 else _t('are')}"

    # 1. Who is ahead on the SOAP halves, and only where every table agrees.
    top, tables = shared(soap, 0)
    bottom, _ = shared(soap, -1)
    if tables:
        said.append(
            _t(
                "On writing correct Czech, {top} in the top band of all {tables} tables "
                "the bands cover -- the SOAP halves, both judges. {bottom} in the "
                "bottom band of all {tables}. Between those two ends the tables "
                "disagree with each other, so nothing else here is a ranking."
            ).format(top=end(top), bottom=end(bottom, lead=True), tables=tables)
        )

    # 1b. The same question of the Deepsy format, counted over its own tables
    #     and never pooled with the ones above. Two reasons, and the first is
    #     the one this repository cares about most: three models were asked in
    #     only one of the two formats, so an intersection across both would
    #     demote a model for a question nobody put to it. The second is that
    #     nobody has rated a Deepsy note by hand, so the two formats do not have
    #     the same evidence behind them.
    #
    #     What this sentence used to give as the reason -- Deepsy notes are
    #     longer and length costs points on every one of these criteria -- is
    #     refuted by section 4 of the same document, and refuted hardest on the
    #     Deepsy side: two of the coefficients hold positive under both judges
    #     and both of them are Deepsy. `_length_signs` counts what was measured.
    top_d, tables_d = shared(deepsy, 0)
    bottom_d, _ = shared(deepsy, -1)
    if tables_d:
        said.append(
            _t(
                "The Deepsy format was asked the same question over its own {tables} "
                "tables, and it is counted separately rather than pooled with the four "
                "above: {top} in the top band of all of them and {bottom} in the bottom "
                "band of all of them. The two formats are not added together because "
                "not every model was asked in both, because a Deepsy note is written to "
                "a different prompt and comes out a different shape, and because the "
                "one native-speaker anchor this project has was measured on SOAP notes "
                "alone. Length does not settle it either way: it runs against "
                "{soap_against} of the {soap_total} criterion-and-judge coefficients on "
                "the SOAP halves and against {deepsy_against} of {deepsy_total} in the "
                "Deepsy format, so it is not the uniform penalty one number could stand "
                "for."
            ).format(top=end(top_d), bottom=end(bottom_d), tables=tables_d, **_length_signs())
        )

    # 1c. And who is missing from that count, with the reason. A model that
    #     wrote no Deepsy note is absent from every Deepsy band, and absence is
    #     not a low score. `glm-5.3-flash` sits in the bottom band of all four
    #     SOAP tables and e-INFRA answered it with an error every time it was
    #     asked for a Deepsy note, so a pooled bottom-band claim would have
    #     dropped it and reported an outage as an exoneration.
    if tables and tables_d and bottom:
        banded_deepsy = {
            model
            for judges in deepsy.values()
            for grouped in judges.values()
            for band in grouped["bands"]
            for model in band["models"]
        }
        # Only the models the pooled claim would actually have dropped: in the
        # bottom band of every SOAP table, and in no Deepsy band at all.
        refused = _refused_on_deepsy(set(bottom) - banded_deepsy)
        if refused:
            said.append(
                _t(
                    "One caution about that second count. {subject} in the bottom band "
                    "of all {tables} SOAP tables and in no Deepsy band at all -- not "
                    "because of anything written, but because e-INFRA answered {calls} "
                    "of the calls asking for those notes with an error and returned no "
                    "note. Adding the two counts together would have removed it from "
                    "the bottom of the table on the strength of an outage."
                ).format(
                    subject=end(sorted(refused), lead=True),
                    tables=tables,
                    calls=sum(refused.values()),
                )
            )

    # 2. The same question asked of note quality, which does not answer.
    top_q, tables_q = shared(quality, 0)
    if tables_q and not top_q:
        said.append(
            _t(
                "On whether the note is any good, no model is in the top band of all "
                "{tables} tables and none is in the bottom band of all {tables}. The "
                "quality instrument does not agree with itself from one judge or one "
                "half to the next, and no model can be called better on it."
            ).format(tables=tables_q)
        )

    # 3. Which columns of that instrument can rank anything at all.
    dead, total, alive, worst, judge = _dead_columns(rows)
    if dead:
        said.append(
            _t(
                "Part of why: under {judge}, {dead} of its {total} columns are the same "
                "for every model, so they order nothing. Of the {moving} that do move, "
                "the one no model does well on is {alive} -- the best reaches {worst} "
                "out of 5. The other judge separates more of them, and that the two "
                "disagree about which columns work is itself the finding."
            ).format(
                judge=judge,
                dead=dead,
                total=total,
                moving=total - dead,
                alive=_join_words(alive) or "-",
                worst=f"{worst:.2f}",
            )
        )

    # 4. The finding that changes how the tables below are read.
    length = _payload("czech-length.json")
    tail = length.get("tail") or {}
    # The SOAP tracks by name. This was "everything that is not PDSQI", and the
    # Deepsy entries -- where the check comes out false -- were being counted
    # into the same total, so `hit == len(checks)` stopped holding and the whole
    # paragraph silently disappeared. The finding is true of the four SOAP
    # tables and was going unsaid because it is not true of two others.
    checks = [
        found
        for track in SOAP_CRITERIA_TRACKS
        for found in (tail.get(track) or {}).get("judges", {}).values()
    ]
    hit = sum(1 for found in checks if found["all_in_the_tail"])
    if checks and hit == len(checks):
        said.append(
            _t(
                "Read the bottom of those tables carefully: the three models that write "
                "the longest notes take the last three places in all {total} of them. "
                "Each criterion asks whether there is a fault anywhere in a note, and a "
                "longer note has more places to hide one. On the quality instrument, "
                "rating the very same notes, those three models are not at the bottom."
            ).format(total=len(checks))
        )

    # 4a. And where it does not hold, said rather than allowed to mute the line
    #     above. On Deepsy the three longest-writing models are a different
    #     three -- the rosters differ -- and they do not all land in the last
    #     three places. A rule that holds on one format and not the other is a
    #     result, and it is also the reason the two are not counted together.
    deepsy_checks = [
        found
        for track in DEEPSY_CRITERIA_TRACKS
        for found in (tail.get(track) or {}).get("judges", {}).values()
    ]
    if checks and deepsy_checks and not any(f["all_in_the_tail"] for f in deepsy_checks):
        said.append(
            _t(
                "That pattern is not a law: on the {total} Deepsy tables the three "
                "longest-writing models -- a different three, because the two formats "
                "were not asked of the same set of models -- do not all land in the "
                "last three places under either judge. Length and rank travel together "
                "on the SOAP halves and more loosely here, which is one more reason the "
                "two formats are counted apart rather than added up."
            ).format(total=len(deepsy_checks))
        )

    # 4b. How big that is, and what is left of the ordering once it is
    #     handicapped. Prints whether or not the sentence above did: the tail
    #     claim holds on the SOAP halves and not on Deepsy, and the size holds
    #     everywhere. A reader who is told a column is entangled with length
    #     and not by how much has been warned and not informed.
    fits = [
        block
        for judges in (length.get("adjusted") or {}).values()
        for block in judges.values()
        if block.get("interval_90")
    ]
    handicap = length.get("handicapped") or {}
    if fits and handicap:
        sizes = sorted(abs(block["slope_per_100_words"]) for block in fits)
        said.append(
            _t(
                "Part of what those language tables measure is length, and how much was "
                "measured rather than argued: each extra hundred words costs {low} to "
                "{high} hundredths of a point, under every "
                "judge on both halves. Subtracting it does not give an order that holds "
                "still, so none is printed. What survives a handicap that never lets the "
                "shorter writer win is {survived} of {decided} decided pairs."
            ).format(
                low=f"{sizes[0] * 100:.0f}",
                high=f"{sizes[-1] * 100:.0f}",
                survived=sum(block["survived"] for block in handicap.values()),
                decided=sum(block["decided"] for block in handicap.values()),
            )
        )

    # 5. Whether the English leaderboard says anything about this.
    join = _payload("czech-join.json").get("judges", {})
    if join:
        measure = next(iter(join.values())).get("ranking_measure")
        if measure:
            label = measure
            for measures in MEASURE_TABLES.values():
                if measure in measures:
                    label = measures[measure]["label"]
                    break
            said.append(
                _t(
                    "And the English leaderboard does not predict this. The same "
                    "instrument asked in both languages transfers; the single measure "
                    "the English page ranks by -- {measure} -- does not. A model's "
                    "standing there says nothing about the Czech it writes."
                ).format(measure=_t(label))
            )

    if not said:
        return ""
    body = "".join(f"<p>{html.escape(sentence)}</p>" for sentence in said)
    heading = _t("What the Czech track found, in {count} short paragraphs").format(count=len(said))
    return f"<h2>{heading}</h2>{body}"


def _payload(name: str) -> dict:
    """One of the precomputed local payloads, or nothing if it was not built."""
    path = REPO / "local" / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _length_signs() -> dict[str, str]:
    """How the length coefficients actually run, counted per note format.

    Three sentences in this document said length costs points on EVERY one of
    these criteria, and one of them was the reason given for not pooling the two
    formats -- so the claim was worst exactly where it was load-bearing.
    Section 4 measures otherwise: on the SOAP halves most coefficients run
    against length, on the Deepsy ones fewer do, and the coefficients that hold
    positive under BOTH judges are in the Deepsy format. A uniform penalty is
    not what was measured.

    Counted from `local/czech-length.json` rather than typed, for the reason
    every other figure here is: a sentence carrying its own number is a sentence
    the next run makes quietly false, and this one had already gone false twice.
    Only the four criteria tracks, because a PDSQI column is a different
    instrument and `succinct` is *supposed* to fall with length.
    """
    blocks = _payload("czech-length.json").get("czech") or {}
    counts = {"soap": [0, 0], "deepsy": [0, 0]}
    positive: list[str] = []
    for name, tracks in (("soap", SOAP_CRITERIA_TRACKS), ("deepsy", DEEPSY_CRITERIA_TRACKS)):
        for track in tracks:
            judges = (blocks.get(track) or {}).get("judges") or {}
            seen: dict[str, list[float]] = {}
            for found in judges.values():
                for key, value in (found.get("correlations") or {}).items():
                    seen.setdefault(key, []).append(value)
            for key, values in sorted(seen.items()):
                counts[name][0] += sum(1 for value in values if value < 0)
                counts[name][1] += len(values)
                # Under BOTH judges, never under one: the reading rule this
                # document applies everywhere else. One judge alone is a fact
                # about that judge and this document has a section for those.
                if len(values) > 1 and all(value > 0 for value in values):
                    label = MEASURE_TABLES.get(track, {}).get(key, {}).get("label", key)
                    positive.append(f"{_t(label)} ({_t(TRACK_SWITCH_LABELS.get(track, track))})")
    return {
        "against": str(counts["soap"][0] + counts["deepsy"][0]),
        "total": str(counts["soap"][1] + counts["deepsy"][1]),
        "soap_against": str(counts["soap"][0]),
        "soap_total": str(counts["soap"][1]),
        "deepsy_against": str(counts["deepsy"][0]),
        "deepsy_total": str(counts["deepsy"][1]),
        "positive": _join_words(positive) if positive else _t("no column at all"),
    }


def _dead_columns(rows: list[results.Row]) -> tuple[int, int, list[str], float, str]:
    """How many quality columns are the same for every model, and what is left.

    Counted on the real half, where the instrument has the fewest columns and
    the question "can this rank anything" is sharpest. The best score on the
    surviving column is returned with it, because "one column still works" and
    "and every model fails it" are one finding rather than two.
    """
    track = results.TRACK_CZECH_REAL_PDSQI
    latest = [row for row in results.latest(rows) if row.is_scored and row.track == track]
    if not latest:
        return 0, 0, [], 0.0, ""
    newest = max(row.judge_prompt_version for row in latest)
    latest = [row for row in latest if row.judge_prompt_version == newest]
    judges = sorted({row.judge_model or "" for row in latest})
    if not judges:
        return 0, 0, [], 0.0, ""
    here = [row for row in latest if (row.judge_model or "") == judges[0]]
    varying = _varying(track, here)
    dead = len(COLUMNS[track]) - len(varying)
    labels = MEASURE_TABLES[track]
    # The strongest of the surviving columns, and the best any model reached on
    # it -- across both judges, because a ceiling one judge sees and the other
    # does not is not a ceiling.
    ranking = [key for key in varying if labels[key]["scale"] == "1-5"]
    if not ranking:
        return dead, len(COLUMNS[track]), [], 0.0, judges[0]
    key = min(
        ranking,
        key=lambda k: max(row.metrics.headline.get(k, 0) for row in latest),
    )
    best = max(row.metrics.headline.get(key, 0) for row in latest)
    return dead, len(COLUMNS[track]), [_t(labels[key]["label"])], best, judges[0]


def _length_by_model(data: dict) -> str:
    """How many words each model writes, per corpus. One row per model.

    This was missing, and its absence made the section unreadable: the only
    table in it was a grid of correlations whose columns are the two judges'
    names, so it looked like a statement about how long the JUDGES write. The
    number a reader wants first is the plain one -- this model writes 289 words,
    that one writes 812 -- and every claim the section makes rests on it.

    Medians, and the count behind each is the notes that parsed. A model with
    fewer notes on a corpus is shown with that count rather than dropped, so a
    short row is visible as thin rather than as absent.
    """
    czech = data.get("czech") or {}
    deepsy = data.get("deepsy") or {}
    corpora = [
        (results.TRACK_CZECH_REAL, czech.get(results.TRACK_CZECH_REAL)),
        (results.TRACK_CZECH_TRANSLATED, czech.get(results.TRACK_CZECH_TRANSLATED)),
        (results.TRACK_DEEPSY_REAL, deepsy.get(results.TRACK_DEEPSY_REAL)),
        (results.TRACK_DEEPSY_TRANSLATED, deepsy.get(results.TRACK_DEEPSY_TRANSLATED)),
    ]
    corpora = [(track, block) for track, block in corpora if block]
    if not corpora:
        return ""

    def cell(block: dict, system: str, most: int) -> str:
        """The median, and the count when it rests on less than the corpus.

        A median of three answers is not a median, and while a corpus is still
        being generated some rows rest on three. Printing the bare number would
        put one model's provisional length beside another's finished one and
        invite the reader to compare them.

        **A whole note, for every column.** The Deepsy block records a median
        per section, because that is the unit its word limit applies to, and
        this table's own lead calls every column "one note". Printing the
        section here showed glm-5.2 at 406 beside its 812-word SOAP note when
        its Deepsy note is 1182, so the table appeared to refute the paragraph
        six above it -- and the paragraph was the one that was right.
        """
        by_note = block.get("by_note") or {}
        if system in by_note:
            return f"<td>{by_note[system]}</td>"
        found = block["by_system"].get(system)
        if found is None:
            return "<td class='dash'>&mdash;</td>"
        if not isinstance(found, dict):
            return f"<td>{found}</td>"
        if found["answers"] < most:
            return (
                f"<td>{found['median']} <span class='dash'>({found['answers']}/{most})</span></td>"
            )
        return f"<td>{found['median']}</td>"

    systems = sorted({s for _, block in corpora for s in block["by_system"]})
    head = "".join(
        f"<th>{html.escape(_t(TRACK_TITLES.get(track, track)))}</th>" for track, _ in corpora
    )
    body = []
    for system in systems:
        cells = ""
        for _track, block in corpora:
            most = max(
                (v["answers"] for v in block["by_system"].values() if isinstance(v, dict)),
                default=0,
            )
            cells += cell(block, system, most)
        body.append(f"<tr><td>{html.escape(system)}</td>{cells}</tr>")

    english = data.get("english") or {}
    human = (data.get("human") or {}).get("human")
    extra = []
    if english:
        block = next(iter(english.values()))
        for system, value in sorted(block["by_system"].items()):
            extra.append((system, value))

    note = ""
    if human:
        # Which models beat the therapist, on any corpus, read off the same
        # table. The sentence used to assert that none did, nine rows above a
        # row that does.
        # From the value the cell prints, not from `by_system`. The Deepsy
        # blocks record a median PER SECTION there, whose largest value is 428,
        # so no Deepsy model could ever clear 750 and the sentence named one
        # model where the table above it shows six.
        over = sorted(
            {
                system
                for _track, block in corpora
                for system in block["by_system"]
                for value in [
                    (block.get("by_note") or {}).get(system)
                    or (
                        block["by_system"][system]["median"]
                        if isinstance(block["by_system"][system], dict)
                        else block["by_system"][system]
                    )
                ]
                if value and value > human["median"]
            }
        )
        tail = (
            _t(LENGTH_TABLE_OVER).format(names=_join_words(over))
            if over
            else _t(LENGTH_TABLE_UNDER)
        )
        line = _t(LENGTH_TABLE_HUMAN).format(human=human["median"], over=tail)
        note = f"<p class='dash'>{html.escape(line)}</p>"
    return (
        f"<h3>{_t('How long each model writes')}</h3>"
        + f"<p>{html.escape(_t(LENGTH_TABLE_LEAD))}</p>"
        + f"<table><thead><tr><th>{_t('Model')}</th>{head}</tr></thead>"
        + f"<tbody>{''.join(body)}</tbody></table>"
        + note
    )


def _formats() -> str:
    """The same models and sessions in two note formats, and what separates them.

    This is what the Deepsy track was built to answer, and the answer arrives
    with a confound it cannot shake off. Both halves are printed because
    printing only the first would be the flattering one.

    Written from `local/czech-length.json` and the rows, so the two halves of
    the finding are computed from the same run rather than remembered from two.
    """
    payload = _payload("czech-length.json")
    czech = payload.get("czech") or {}
    if not czech:
        return ""

    rows, _refused = results.drawable(results.load(results.LOCAL_ROWS_PATH))
    latest = [row for row in results.latest(rows) if row.is_scored]
    keys = czech_scorer.CRITERION_KEYS

    def mean_of(track: str, judge: str) -> dict[str, float]:
        found = {}
        for row in latest:
            if row.track != track or row.judge_model != judge:
                continue
            values = [row.metrics.headline[k] for k in keys if k in row.metrics.headline]
            if values:
                found[row.system_id] = sum(values) / len(values)
        return found

    pairs = (
        (results.TRACK_CZECH_REAL, results.TRACK_DEEPSY_REAL),
        (results.TRACK_CZECH_TRANSLATED, results.TRACK_DEEPSY_TRANSLATED),
    )
    judges = sorted(
        {
            row.judge_model or ""
            for row in latest
            if row.track in {results.TRACK_DEEPSY_REAL, results.TRACK_DEEPSY_TRANSLATED}
        }
    )
    if not judges:
        return ""

    lines, every_drop, total_worse, total_models = [], [], 0, 0
    shared_models = 0
    for soap_track, deepsy_track in pairs:
        for judge in judges:
            soap, deepsy = mean_of(soap_track, judge), mean_of(deepsy_track, judge)
            shared = sorted(set(soap) & set(deepsy))
            if len(shared) < 5:
                continue
            a = sum(soap[m] for m in shared) / len(shared)
            b = sum(deepsy[m] for m in shared) / len(shared)
            worse = sum(1 for m in shared if deepsy[m] < soap[m])
            every_drop.append(b - a)
            total_worse += worse
            total_models += len(shared)
            shared_models = max(shared_models, len(shared))
            lines.append(
                f"<tr><td>{html.escape(_t(TRACK_TITLES.get(soap_track, soap_track)))}</td>"
                f"<td>{html.escape(judge)}</td><td>{len(shared)}</td>"
                f"<td>{a:.2f}</td><td>{b:.2f}</td><td>{b - a:+.2f}</td>"
                f"<td>{worse}/{len(shared)}</td></tr>"
            )
    if not lines:
        return ""

    # The confound, measured from the same payload.
    soap_words = (czech.get(results.TRACK_CZECH_REAL) or {}).get("by_system", {})
    deepsy_words = _deepsy_words(payload)
    both = sorted(set(soap_words) & set(deepsy_words))
    longer = sum(1 for m in both if deepsy_words[m] > soap_words[m])

    head = (
        f"<tr><th>{_t('Corpus')}</th><th>{_t('Judge')}</th><th>{_t('Models')}</th>"
        f"<th>SOAP</th><th>Deepsy</th><th>{_t('difference')}</th>"
        f"<th>{_t('worse in Deepsy')}</th></tr>"
    )
    return (
        f"<h2>{_t('The same models, the same sessions, two note formats')}</h2>"
        # The count the table below actually compares on: the two rosters differ,
        # so it is their intersection and not either track's model count.
        + f"<p>{html.escape(_t(FORMATS_LEAD).format(models=shared_models))}</p>"
        + f"<table><thead>{head}</thead><tbody>{''.join(lines)}</tbody></table>"
        + "<div class='warn'><p>"
        + html.escape(
            _t(FORMATS_CONFOUND).format(
                longer=longer,
                models=len(both),
                # The roster the criteria table above compares on, which is not
                # the roster the word counts intersect to: the sentence said
                # "ten models" as a word, beside a placeholder holding eleven.
                compared=shared_models,
                soap=int(sorted(soap_words[m] for m in both)[len(both) // 2]),
                deepsy=int(sorted(deepsy_words[m] for m in both)[len(both) // 2]),
                **_length_signs(),
            )
        )
        + "</p></div>"
    )


def _deepsy_words(payload: dict) -> dict[str, int]:
    """Words in a whole Deepsy note: the three sections of one session, added.

    Read from `by_note` rather than derived. The first version multiplied a
    section's median by three, which is not the median of the sums, and it
    printed "11 of 11 models write more, 762 words against 538" where the truth
    is 9 of 11 and 662 -- two wrong numbers inside a caveat, which is the shape
    this document has spent the night removing.
    """
    block = (payload.get("deepsy") or {}).get(results.TRACK_DEEPSY_REAL) or {}
    return dict(block.get("by_note") or {})


FORMATS_LEAD = (
    "{models} models wrote from the same sessions twice, on both corpora: once as a "
    "SOAP note, "
    "which is what TN-Eval asks for and what makes the English comparison possible, "
    "and once in the format the Deepsy application actually writes. The same six "
    "criteria, the same judges, the same rubric version -- only the format differs. "
    "Every one of the four comparisons goes the same way."
)
FORMATS_CONFOUND = (
    "Do not read that as the Deepsy format producing worse Czech. It might, and "
    "these numbers cannot say so, because the two things move together: a Deepsy "
    "note is LONGER -- {longer} of {models} models write more in it, a median of "
    "{deepsy} words against {soap} -- and this document measures below that length "
    "runs against most of these criteria, {soap_against} of the {soap_total} "
    "criterion-and-judge coefficients on the SOAP halves and {deepsy_against} of "
    "{deepsy_total} in the Deepsy format, because each asks whether there is a fault "
    "ANYWHERE in it. Format and length point the same way here and {compared} models "
    "cannot separate them."
)


def _length() -> str:
    """How long a note the models write, and whether the tables reward it.

    Written by `tools/czech_length.py`. It is here rather than in the method
    because it is a result: **the two languages pull in opposite directions.**
    English completeness rises with length under both judges, and every Czech
    language criterion falls with it under both. A reader who does not know that
    will read the bottom of the Czech table as "this model writes bad Czech"
    when part of what it says is "this model writes a lot".

    The correlations are printed without p-values on purpose. Eleven or sixteen
    points make a threshold theatre; the reading rule this document uses
    everywhere else -- believe a column that says the same thing under both
    judges -- is the honest test and is the one stated beside the table.
    """
    path = REPO / "local" / "czech-length.json"
    if not path.exists():
        return ""
    data = json.loads(path.read_text(encoding="utf-8"))

    parts = [f"<h2>{_t('How long the notes are, and whether length is rewarded')}</h2>"]

    # --- what was asked for -------------------------------------------------
    asked = data.get("instructions", {})
    deepsy_limit = (asked.get("deepsy") or {}).get("limit_words")
    if asked:
        quiet = sum(1 for found in asked.values() if not found.get("has_limit"))
        parts.append(
            "<p>"
            + html.escape(
                _t(LENGTH_ASKED).format(limit=deepsy_limit, quiet=quiet, families=len(asked))
            )
            + "</p>"
        )

    # --- the human anchor ---------------------------------------------------
    human = (data.get("human") or {}).get("human")
    english = data.get("english") or {}
    if human and english:
        block = next(iter(english.values()))
        parts.append(
            "<p>"
            + html.escape(
                _t(LENGTH_HUMAN).format(
                    human=human["median"],
                    n=human["n"],
                    low=block["min"],
                    high=block["max"],
                    systems=block["systems"],
                    share_low=f"{block['min'] / human['median']:.0%}",
                    share_high=f"{block['max'] / human['median']:.0%}",
                )
            )
            + "</p>"
        )

    # --- the one prompt that set a limit ------------------------------------
    for _track, block in (data.get("deepsy") or {}).items():
        sections = block.get("sections") or {}
        if not sections:
            continue
        worst = min(sections.items(), key=lambda kv: kv[1]["share_of_target"])
        parts.append(
            "<p>"
            + html.escape(
                _t(LENGTH_DEEPSY).format(
                    limit=block["limit_words"],
                    over=block["over_limit"],
                    answers=block["answers"],
                    section=_t(DEEPSY_SECTION_LABELS.get(worst[0], worst[0])),
                    share=f"{worst[1]['share_of_target']:.0%}",
                )
            )
            + "</p>"
        )
        break

    # --- how long each model writes -----------------------------------------
    parts.append(_length_by_model(data))

    # --- what length buys ---------------------------------------------------
    table = _length_table(data)
    if table:
        parts.append("<p>" + html.escape(_t(LENGTH_BUYS).format(**_length_signs())) + "</p>")
        parts.append(table)
        warning = _length_warning(data)
        if warning:
            parts.append(f"<div class='warn'><p>{html.escape(warning)}</p></div>")
    effect = _length_effect(data)
    if effect:
        parts.append(effect)
    return "\n".join(parts)


#: Two paragraphs and a table, written from `tools/czech_length.py`. They answer
#: the question a reader has as soon as the correlations above are on the page:
#: fine, so take the length out. The first says how large the effect is, the
#: second says why the obvious correction is not printed, and the table is what
#: is left when nothing is fitted at all.
LENGTH_SIZE = (
    "How large is it? Fitting each judge's composite of the criteria against the "
    "model's median note length costs {low} to {high} hundredths of a point per "
    "hundred words, across the four track-and-judge combinations. Drawing the "
    "{systems} models again with replacement {resamples} times, the ninety per cent "
    "interval clears zero on all four and the sign reverses in at most {wrong} of the "
    "draws. The direction is settled: on this corpus a longer note scores lower on "
    "Czech."
)
LENGTH_NO_ADJUSTED = (
    "So why is there no length-adjusted column here? It was computed, and it will not "
    "hold still. Subtracting what length predicts and re-ranking gives an order whose "
    "safest position -- the last place -- survives redrawing the same models only "
    "{holds} of the time. A well-measured slope and a dependable order are different "
    "things: the slope is one number fitted to every model at once, while the adjusted "
    "order is {systems} small residuals competing with each other. The second reason "
    "would apply even if it held: length was not assigned to the models, they chose "
    "it. A model may write long BECAUSE it summarises badly, and then removing what "
    "length predicts removes the result along with the artefact."
)
LENGTH_HANDICAP = (
    "What can be said without fitting anything is in the table. A pair of models "
    "counts as decided when one beats the other by more than {separation} on the "
    "composite under BOTH judges, and it survives the handicap when the winner also "
    "wrote at least as many words as the loser -- so the longer note had more places "
    "for a fault to be found and had fewer of them anyway. That leaves {survived} of "
    "the {decided} decided pairs, counting the two halves separately. What survives "
    "is a partial order and not a ranking, "
    "and how little of it there is is the finding."
)

#: Short column headings for the handicap table. `TRACK_TITLES` names the corpus
#: and the client, which is right everywhere else and over a two-word cell would
#: be the widest thing in the document.
HANDICAP_COLUMNS = {
    results.TRACK_CZECH_REAL: "on the real sessions",
    results.TRACK_CZECH_TRANSLATED: "on the translated ones",
}


def _length_effect(data: dict) -> str:
    """How large the length effect is, and what survives being handicapped by it.

    **Every number here is read from the payload and none is typed.** The
    interval, the share of draws that reverse the sign and the stability of the
    adjusted last place are what `czech_length.adjusted` measured; the pairs are
    what `czech_length.handicapped` counted. If a rebuild moves them, this moves.

    The paragraph about the adjusted column exists because the column does not.
    A reader who has just been told that length explains a third of the variance
    between models will ask why it was not simply subtracted, and the answer --
    it was, and the result will not hold still -- is a finding rather than an
    omission. Saying nothing would leave them to assume nobody tried.
    """
    fits = [
        block
        for judges in (data.get("adjusted") or {}).values()
        for block in judges.values()
        if block.get("interval_90")
    ]
    parts: list[str] = []
    if fits:
        sizes = sorted(abs(block["slope_per_100_words"]) for block in fits)
        parts.append(
            "<p>"
            + html.escape(
                _t(LENGTH_SIZE).format(
                    low=f"{sizes[0] * 100:.0f}",
                    high=f"{sizes[-1] * 100:.0f}",
                    systems=max(block["systems"] for block in fits),
                    resamples=f"{max(block['resamples'] for block in fits):,}",
                    wrong=f"{max(block['wrong_sign'] for block in fits):.0%}",
                )
            )
            + "</p>"
        )
        held = [block["last_place_holds"] for block in fits if "last_place_holds" in block]
        if held:
            parts.append(
                "<p>"
                + html.escape(
                    _t(LENGTH_NO_ADJUSTED).format(
                        holds=f"{min(held):.0%}–{max(held):.0%}",
                        systems=max(block["systems"] for block in fits),
                    )
                )
                + "</p>"
            )
    table = _handicap_table(data)
    if table:
        blocks = data.get("handicapped") or {}
        parts.append(
            "<p>"
            + html.escape(
                _t(LENGTH_HANDICAP).format(
                    separation=next(iter(blocks.values()))["separation"],
                    survived=sum(block["survived"] for block in blocks.values()),
                    decided=sum(block["decided"] for block in blocks.values()),
                )
            )
            + "</p>"
        )
        parts.append(table)
    return "\n".join(parts)


def _handicap_table(data: dict) -> str:
    """One row per surviving pair, both halves in the same table.

    Merged rather than drawn twice: most surviving pairs hold on both halves,
    and two tables would print each of those twice for no reader who benefits.
    A dash is not a defeat. It means the pair was not separated on that half, or
    was separated in the direction length would explain.
    """
    blocks = data.get("handicapped") or {}
    order = [track for track in results.TRACKS if track in blocks]
    seen: dict[tuple[str, str], dict[str, dict]] = {}
    for track in order:
        for pair in blocks[track]["pairs"]:
            seen.setdefault((pair["winner"], pair["loser"]), {})[track] = pair
    if not seen:
        return ""
    head = "".join(
        f"<th>{html.escape(_t(HANDICAP_COLUMNS.get(track, track)))}</th>" for track in order
    )
    rows = []
    for (winner, loser), found in sorted(
        seen.items(), key=lambda kv: (-len(kv[1]), kv[0][0], kv[0][1])
    ):
        cells = []
        for track in order:
            pair = found.get(track)
            if pair:
                cell = html.escape(
                    _t("{margin} · {winner} vs {loser} words").format(
                        margin=f"+{pair['margin']:.2f}",
                        winner=pair["winner_words"],
                        loser=pair["loser_words"],
                    )
                )
            else:
                cell = "–"
            cells.append(f"<td>{cell}</td>")
        rows.append(
            f"<tr><td>{html.escape(winner)}</td><td>{html.escape(loser)}</td>"
            + "".join(cells)
            + "</tr>"
        )
    return (
        "<table class='handicap'><thead><tr>"
        f"<th>{html.escape(_t('Beats'))}</th>"
        f"<th>{html.escape(_t('this model'))}</th>{head}"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _length_warning(data: dict) -> str:
    """The caveat, with its own evidence counted rather than asserted.

    It claims two things a run could make false: that the longest writers sit at
    the bottom of the language tables, and that they do not on PDSQI-9. Both are
    counted from `tools/czech_length.py`'s tail block, and if the first stops
    holding in every table that checked it, the sentence is not printed at all.
    A caveat that survives its own evidence going away is not a caveat.

    **One note format at a time, in both halves of it.** This filtered on "not
    PDSQI", which swept the Deepsy tables in the moment they were measured: the
    claim came out "4 times out of 8", read as half the time, when the split is
    4 of 4 on the SOAP halves and 0 of 4 on Deepsy. "Half the time" is the one
    reading the data does not support, and the 4-0 / 0-4 split is the finding.

    The word counts are SOAP-only for the same reason. Pooled, the range ran
    from a 812-word SOAP note to a 127-word *section* of a Deepsy note --
    crossing the format, the corpus and the unit at once, and inflating a 3.2x
    spread to 6.4x inside a paragraph arguing about the bottom of the SOAP
    tables.
    """
    tail = data.get("tail") or {}

    def counted(tracks: tuple[str, ...]) -> tuple[int, int]:
        found = [
            check
            for track in tracks
            for check in ((tail.get(track) or {}).get("judges") or {}).values()
        ]
        return sum(1 for check in found if check["all_in_the_tail"]), len(found)

    hit, total = counted(SOAP_CRITERIA_TRACKS)
    if not total or not hit:
        return ""
    lengths = [
        value
        for track in SOAP_CRITERIA_TRACKS
        for value in ((data.get("czech") or {}).get(track) or {}).get("by_system", {}).values()
    ]
    if not lengths:
        return ""
    said = _t(LENGTH_WARNING).format(
        longest=max(lengths),
        shortest=min(lengths),
        hit=hit,
        total=total,
    )
    hit_d, total_d = counted(DEEPSY_CRITERIA_TRACKS)
    if total_d:
        said += " " + _t(LENGTH_WARNING_DEEPSY).format(hit=hit_d, total=total_d)
    return said


#: How each Deepsy section is named to a reader. The keys are the application's
#: own, in English, and a Czech clinical team should not have to read them.
DEEPSY_SECTION_LABELS = {
    "data": "the data section",
    "clinical_hypotheses": "the hypotheses section",
    "plan": "the plan section",
}

#: Below this a column is not entangled enough with length to be worth a row.
#: **Both judges must agree on the direction and at least one must reach this**,
#: rather than both reaching it. Requiring both dropped English completeness --
#: +0.24 and +0.56, two judges saying the same thing at different strengths --
#: which is exactly the row the paragraph above the table is about. A rule that
#: hides the example its own prose cites is the wrong rule.
LENGTH_ENTANGLED = 0.40

#: Columns where moving against length is the measure working, not failing.
#: `succinct` asks whether the note says it in as few words as it can; a note
#: that is twice as long and no fuller SHOULD score lower. Printed in the same
#: table because the reader needs to see it is not entangled by accident, and
#: marked because otherwise it reads as one more broken column.
LENGTH_BY_DESIGN = ("succinct", "conciseness")


def _length_table(data: dict) -> str:
    """Only the columns that move with length, and only where both judges agree.

    Everything else would be a wall of coefficients a reader cannot act on. A
    column that moves under one judge and not the other is a fact about that
    judge, and this document has a section for those already.
    """
    lines = []
    blocks = [(_t("English · TN-Eval SOAP"), data.get("english") or {})]
    for track, block in (data.get("czech") or {}).items():
        judges = {name: found["correlations"] for name, found in block["judges"].items()}
        blocks.append((_t(TRACK_TITLES.get(track, track)), judges))

    for title, judges in blocks:
        if len(judges) < 2:
            continue
        names = sorted(judges)
        first = judges[names[0]]
        first = first.get("correlations", first) if isinstance(first, dict) else {}
        for key in sorted(first):
            values = []
            for name in names:
                found = judges[name]
                found = found.get("correlations", found)
                values.append(found.get(key))
            if any(v is None for v in values):
                continue
            if max(abs(v) for v in values) < LENGTH_ENTANGLED:
                continue
            if len({v > 0 for v in values}) != 1:
                continue
            label = key
            for measures in MEASURE_TABLES.values():
                if key in measures:
                    label = measures[key]["label"]
                    break
            mark = ""
            if key in LENGTH_BY_DESIGN:
                mark = f" <span class='dash'>({_t('by design')})</span>"
            cells = "".join(f"<td>{v:+.2f}</td>" for v in values)
            lines.append(
                f"<tr><td>{html.escape(title)}</td>"
                f"<td>{html.escape(_t(label))}{mark}</td>{cells}</tr>"
            )
    if not lines:
        return ""
    judges = sorted({n for _, j in blocks for n in j})
    head = "".join(f"<th>{html.escape(n)}</th>" for n in judges)
    return (
        f"<table><thead><tr><th>{_t('Track')}</th><th>{_t('Column')}</th>"
        f"{head}</tr></thead><tbody>{''.join(lines)}</tbody></table>"
    )


#: The caption's second clause, printed only where a model in the table wrote
#: fewer notes than the corpus holds. The first clause says "over at most N
#: sessions" because N is the union of what the models between them wrote --
#: `czech_variance.bands` pairs each pair on the sessions BOTH of them wrote --
#: and printing it as "over 10 sessions" stated a corpus as if it were every
#: model's denominator, over tables holding a model with six.
BAND_SHORTFALL = "a pair is compared on the sessions both models wrote, and {names} wrote fewer"


def _bands(rows: list[results.Row]) -> str:
    """The models grouped, because ordering eleven of them over ten notes is
    mostly ordering noise.

    A ranking invites the one reading it cannot support -- is the fourth better
    than the fifth -- and no caveat beside it declines the invitation. Bands
    say the same measurement without making the offer: within a band nothing
    separates the models, between bands something does.

    A band starts where the gap from the band's best exceeds what resampling
    the sessions can rule out, so the width of a band is the measurement's own
    resolution rather than a choice about presentation.

    The caption takes `rows` for one clause: how many notes each banded model
    actually wrote. The session count in the payload is the union across
    models, which is the corpus and not anybody's denominator.
    """
    path = REPO / "local" / "czech-variance.json"
    if not path.exists():
        return ""
    data = json.loads(path.read_text(encoding="utf-8")).get("bands") or {}
    if not data:
        return ""

    counts = _wrote(rows)
    blocks = []
    for track in results.LOCAL_TRACKS:
        judges = data.get(track) or {}
        if not judges:
            continue
        for judge_model in sorted(judges):
            grouped = judges[judge_model]
            rows_html = "".join(
                f"<tr><td>{number}</td>"
                f"<td>{band['high']:.2f}&ndash;{band['low']:.2f}</td>"
                f"<td class='sub'>{html.escape(', '.join(band['models']))}</td></tr>"
                for number, band in enumerate(grouped["bands"], start=1)
            )
            # Only models this table draws. A model the endpoint refused wrote
            # nothing and is in no band, and naming it here would explain a row
            # that is not on the page.
            drawn = {model for band in grouped["bands"] for model in band["models"]}
            short = [
                f"{system} {count}"
                for system, count in sorted((counts.get(track) or {}).get("wrote", {}).items())
                if system in drawn and count < grouped["sessions"]
            ]
            caption = (
                f"{_t('a band is')} {grouped['threshold']:.2f} "
                f"{_t('wide, over at most')} {grouped['sessions']} {_t('sessions')}"
            )
            if short:
                caption += " &middot; " + html.escape(
                    _t(BAND_SHORTFALL).format(names=_join_words(short))
                )
            blocks.append(
                f"<h3>{html.escape(_t(TRACK_TITLES.get(track, track)))} "
                f"<span class='dash'>&mdash; {_t('who is ahead')}</span> "
                f"<span class='dash'>&middot; {html.escape(judge_model)}</span></h3>"
                f"<p class='sub'>{caption}</p>"
                f"<table><thead><tr><th>{_t('Band')}</th><th>{_t('Score')}</th>"
                f"<th>{_t('Models')}</th></tr></thead><tbody>{rows_html}</tbody></table>"
            )

    if not blocks:
        return ""
    # Counted, not typed. This lead sat above four tables of eleven models and
    # said "eleven"; it now sits above six, two of which have twelve, and a
    # count typed into a sentence is a count a later run makes quietly false.
    # The largest table's roster, because the claim is about the widest ordering
    # the reader is offered.
    widest = max(
        (
            sum(len(band["models"]) for band in g["bands"])
            for judges in data.values()
            for g in judges.values()
        ),
        default=0,
    )
    notes = max(
        (g["sessions"] for judges in data.values() for g in judges.values()),
        default=0,
    )
    return (
        f"<h2>{_t('Bands, not places')}</h2>"
        + "<p>"
        + html.escape(
            _t(
                "As many as {models} models over {notes} notes cannot be put in order, "
                "and a table that prints them in one invites a comparison it cannot "
                "support. These are the same numbers grouped instead: within a band "
                "nothing separates the models, between bands something does. A band "
                "ends where the gap exceeds what resampling the sessions can rule out, "
                "so its width is the measurement's own resolution."
            ).format(models=widest, notes=notes)
        )
        + "</p>"
        + "".join(blocks)
    )


def _dominance(rows: list[results.Row]) -> str:
    """The only claim about "better" this project makes, and it was missing.

    `docs/methodology.md` states it: the ranking is a shape, not an order, and
    the one comparison that survives two judges is **dominance** -- at least as
    good on every measure under both of them, and strictly better on one. It is
    the strongest thing in the document and it was the thing not in it, which is
    how a reader ends up comparing adjacent rows instead.

    Computed over the criteria a model was scored on under both judges. A pair
    where either judge has no value for a criterion is simply not compared on
    it, rather than being counted either way.

    **Inside one note format, never across the two.** Each track gets its own
    block. The two formats were not asked of the same models, a Deepsy note is
    written to a different prompt, and length does not weigh on them alike --
    `_length_signs` counts how differently -- so a pair read across the two
    formats would be reporting those differences as a verdict.
    """
    latest = [row for row in results.latest(rows) if row.is_scored]
    blocks = []
    for track in (
        results.TRACK_CZECH_REAL,
        results.TRACK_CZECH_TRANSLATED,
        results.TRACK_DEEPSY_REAL,
        results.TRACK_DEEPSY_TRANSLATED,
    ):
        here = [row for row in latest if row.track == track]
        if not here:
            continue
        newest = max(row.judge_prompt_version for row in here)
        tables = {}
        for row in here:
            if row.judge_prompt_version == newest:
                tables.setdefault(row.judge_model or "", {})[row.system_id] = row.metrics.headline
        if len(tables) < 2:
            continue

        systems = sorted(set.intersection(*(set(t) for t in tables.values())))
        # The columns this track's table actually draws, not every criterion the
        # scorer knows. They are the same six on all four criteria tracks today,
        # but reading them from `COLUMNS` is what keeps a pair from being judged
        # on a column the reader was never shown.
        compared = [key for key, _ in COLUMNS[track]]
        found = []
        for first in systems:
            for second in systems:
                if first == second:
                    continue
                at_least, strictly = True, False
                for table in tables.values():
                    for key in compared:
                        a = table[first].get(key)
                        b = table[second].get(key)
                        if a is None or b is None:
                            continue
                        if a < b - 1e-9:
                            at_least = False
                            break
                        if a > b + 1e-9:
                            strictly = True
                    if not at_least:
                        break
                if at_least and strictly:
                    found.append((first, second))

        title = html.escape(_t(TRACK_TITLES.get(track, track)))
        if not found:
            blocks.append(
                f"<h3>{title}</h3><p>"
                + html.escape(
                    _t(
                        "No model here is at least as good as another on every "
                        "criterion under both judges."
                    )
                )
                + "</p>"
            )
            continue
        beaten = defaultdict(list)
        for first, second in found:
            beaten[first].append(second)
        items = "".join(
            f"<dt>{html.escape(winner)}</dt><dd>{html.escape(_t('is at least as good as'))} "
            f"{html.escape(', '.join(sorted(losers)))}</dd>"
            for winner, losers in sorted(beaten.items(), key=lambda kv: -len(kv[1]))
        )
        pairs = len(systems) * (len(systems) - 1) // 2
        blocks.append(
            f"<h3>{title}</h3>"
            f"<p>{len(found)} {_t('of')} {pairs} "
            + html.escape(_t("possible pairs."))
            + f"</p><dl>{items}</dl>"
        )

    if not blocks:
        return ""
    return (
        f"<h2>{_t('The only claim about better that survives')}</h2>"
        + "<p>"
        + html.escape(
            _t(
                "Two judges order the models differently, so a position in a table is "
                "not a claim. What survives both of them is dominance: one model at "
                "least as good as another on every criterion, under each judge "
                "separately, and strictly better on at least one. Everything not "
                "listed here is a pair this project cannot separate. Each block "
                "below is one note format, and a pair holds only inside it: the two "
                "formats were not asked of the same models, a Deepsy note is written to "
                "a different prompt, and length does not weigh on them alike -- it runs "
                "against {soap_against} of the {soap_total} criterion-and-judge "
                "coefficients on the SOAP halves and against {deepsy_against} of "
                "{deepsy_total} in the Deepsy format. A pair read across the two would "
                "be reporting those differences as a verdict."
            ).format(**_length_signs())
        )
        + "</p>"
        + "".join(blocks)
    )


def _variance(rows: list[results.Row]) -> str:
    """How far apart two rows must be before their order means anything.

    Written by `tools/czech_variance.py`. It belongs above the caveats rather
    than among them, because it is not a caveat: it is a number a reader applies
    to the table in front of them, and without it the invitation a table of
    proportions makes -- compare these two neighbouring rows -- is one nobody
    can decline.

    The louder half is the columns where sessions vary more than models do.
    There the ordering is a fact about which ten transcripts were drawn, and no
    threshold rescues it.
    """
    path = REPO / "local" / "czech-variance.json"
    if not path.exists():
        return ""
    data = json.loads(path.read_text(encoding="utf-8"))
    tracks = data.get("tracks") or {}
    if not tracks:
        return ""

    counts = _wrote(rows)
    blocks, unreadable = [], []
    for track, judges in tracks.items():
        names = sorted(judges)
        body = []
        for criterion in czech_scorer.CRITERION_KEYS:
            cells = []
            drawn = False
            for name in names:
                entry = judges[name].get(criterion) or {}
                spread, gaps = entry.get("spread"), entry.get("gaps")
                if not gaps:
                    cells.append("<td class='dash'>--</td><td class='dash'>--</td>")
                    continue
                drawn = True
                ratio = (spread or {}).get("ratio")
                if ratio is not None and ratio < 1:
                    # Translated. These two lists name a track and a column
                    # inside a warning box, and drew them raw -- so the Czech
                    # document warned in Czech and then listed what it was
                    # warning about in English, in the caveat, which is where
                    # the reader who most needs it stops reading.
                    unreadable.append(
                        f"{_t(TRACK_TITLES.get(track, track))} / "
                        f"{_t(MEASURE_TABLES[track][criterion]['label'])} / {name}"
                    )
                share = f"{gaps['separable']}/{gaps['pairs']}"
                cells.append(f"<td>{share}</td><td>{gaps['threshold']:.2f}</td>")
            if drawn:
                label = _t(MEASURE_TABLES[track][criterion]["label"])
                body.append(f"<tr><td>{html.escape(label)}</td>" + "".join(cells) + "</tr>")
        if not body:
            continue
        head = "".join(
            f"<th>{html.escape(name)}: {_t('pairs apart')}</th>"
            f"<th>{html.escape(name)}: {_t('gap needed')}</th>"
            for name in names
        )
        blocks.append(
            f"<h3>{html.escape(_t(TRACK_TITLES.get(track, track)))} "
            f"<span class='dash'>&mdash; {_t('how far apart is far enough')}</span></h3>"
            f"<table><thead><tr><th>{_t('Criterion')}</th>{head}</tr></thead>"
            f"<tbody>{''.join(body)}</tbody></table>"
        )

    if not blocks:
        return ""

    thin = []
    for track, judges in tracks.items():
        for name, block in judges.items():
            for criterion, entry in block.items():
                gaps = entry.get("gaps")
                if gaps and gaps["share"] < UNREADABLE:
                    thin.append(
                        f"{_t(MEASURE_TABLES[track][criterion]['label'])} "
                        f"({_t(TRACK_TITLES.get(track, track))}, {name}, "
                        f"{gaps['separable']}/{gaps['pairs']})"
                    )
    thin_note = ""
    if thin:
        thin_note = (
            "<div class='warn'><p><strong>"
            + html.escape(_t("These columns do not order the models either."))
            + "</strong> "
            + html.escape(
                _t(
                    "Fewer than a quarter of the model pairs come apart, so the "
                    "sequence of rows is mostly the order chance put them in. The "
                    "column may still be worth reading as a level -- how often the "
                    "fault appears at all -- but not as a ranking:"
                )
            )
            + f" {html.escape('; '.join(sorted(set(thin))))}.</p></div>"
        )

    warning = ""
    if unreadable:
        warning = (
            "<div class='warn'><p><strong>"
            + html.escape(_t("These columns order the transcripts, not the models."))
            + "</strong> "
            + html.escape(
                _t(
                    "The sessions differ from each other more than the models do, so "
                    "whatever order the rows come out in is a fact about which "
                    "transcripts were drawn. No threshold rescues them; do not read them:"
                )
            )
            + f" {html.escape('; '.join(sorted(set(unreadable))))}.</p></div>"
        )
    lead = html.escape(
        _t(
            "Ten notes per model at most. The sessions were resampled two thousand "
            "times and paired on the transcript, so a pair of models is compared only "
            "on the sessions both of them wrote and a pair with fewer than five in "
            "common is not compared at all. Each pair is then read on the middle 95% "
            "of the result. Two "
            "numbers per column: how many of the model pairs come out apart, and "
            "how large a gap it takes. A difference smaller than that is the same "
            "reading printed twice, whichever way round it fell."
        )
    )
    # Which models that applies to, rather than left as a possibility. The
    # sentence used to say the pairing was safe "because every model wrote from
    # all ten"; two Deepsy models wrote nine and one banded SOAP model wrote six.
    short = []
    for track in tracks:
        names = [
            f"{system} {count}"
            for system, count in sorted((counts.get(track) or {}).get("wrote", {}).items())
            if 0 < count < (counts.get(track) or {})["corpus"]
        ]
        if names:
            short.append(
                f"{_t(TRACK_SWITCH_LABELS.get(track, track))} — "
                f"{_join_words(names)} {_t('of')} {counts[track]['corpus']}"
            )
    if short:
        lead += " " + html.escape(
            _t("Where a model wrote fewer than the corpus holds, that is where: {short}.").format(
                short="; ".join(short)
            )
        )
    return (
        f"<h2>{_t('How far apart is far enough?')}</h2>"
        + f"<p>{lead}</p>"
        + "".join(blocks)
        + warning
        + thin_note
    )


def _anchor() -> str:
    """The one figure this track has that the other three do not.

    Written by `tools/czech_anchor.py` from the filled rating sheet. Absent
    until somebody fills one in, and the section simply does not appear rather
    than appearing empty -- a heading with no number under it reads as a
    measurement that failed.

    Three things travel with the figure and none of them is optional. How the
    ratings were made, because "one native speaker rated twenty notes" would be
    a larger claim than the truth. That one rater gives no ceiling, so the
    number is not an accuracy. And the count of questions that have no answer
    on disk, because a rate computed over the answered ones is only as good as
    how few were not.
    """
    path = REPO / "local" / "czech-anchor.json"
    if not path.exists():
        return ""
    data = json.loads(path.read_text(encoding="utf-8"))
    judges = sorted(data.get("judges", {}))
    if not judges:
        return ""

    keys = [key for key, _ in COLUMNS[results.TRACK_CZECH_REAL]]
    body = []
    for key in keys:
        cells = []
        for name in judges:
            entry = data["judges"][name]["criteria"].get(key)
            if not entry or entry["rate"] is None:
                cells.append(f"<td class='dash'>{_t('not answered yet')}</td>")
            else:
                gap = (
                    f" <span class='dash'>({entry['unanswered']} {_t('unanswered')})</span>"
                    if entry["unanswered"]
                    else ""
                )
                cells.append(f"<td>{entry['rate']:.2f}{gap}</td>")
        label = _t(MEASURE_TABLES[results.TRACK_CZECH_REAL][key]["label"])
        body.append(f"<tr><td>{html.escape(label)}</td>" + "".join(cells) + "</tr>")

    totals = []
    for name in judges:
        rate = data["judges"][name].get("rate")
        totals.append(
            f"<td><strong>{rate:.2f}</strong></td>" if rate else "<td class='dash'>--</td>"
        )
    body.append(f"<tr><td><strong>{_t('All questions')}</strong></td>" + "".join(totals) + "</tr>")

    head = "".join(f"<th>{html.escape(name)}</th>" for name in judges)
    return (
        f"<h2>{_t('How often a judge and one native speaker said the same thing')}</h2>"
        f"<p>{html.escape(_t(data.get('method', '')))}</p>"
        f"<div class='warn'><p>{html.escape(_t(data.get('ceiling', '')))}</p></div>"
        f"<table><thead><tr><th>{_t('Criterion')}</th>{head}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
        f"<p class='sub'>{data.get('notes_rated', 0)} "
        + html.escape(
            _t(
                "notes, drawn by a hash of the session and the model so that no "
                "score could influence which ones were rated."
            )
        )
        + "</p>"
    )


def _pdsqi_control() -> str:
    """Whether a quality column CAN come back below 5, from the damaged notes.

    Written by `tools/czech_pdsqi_control.py`. It answers the one question the
    tables cannot: three of these six columns give every model the same value,
    and a flat column is either a property of the task -- every model writes
    into the structure the prompt dictates, so a question about structure has
    nothing to separate -- or a property of the instrument, which would mean the
    figures are not measurements at all and should be withdrawn.

    Nothing already measured tells those apart, because nothing already measured
    contains a badly organised note. One invented note and three damaged copies
    do, and the prediction for each was written into the tool before it was run.
    """
    path = REPO / "local" / "czech-pdsqi-control.json"
    if not path.exists():
        return ""
    runs = json.loads(path.read_text(encoding="utf-8"))
    if not runs:
        return ""

    judges = sorted(runs)
    first = runs[judges[0]]
    keys = [key for key in first["clean"] if first["clean"][key] is not None]
    labels = MEASURE_TABLES[results.TRACK_CZECH_REAL_PDSQI]

    lines = []
    for name in ("clean",) + tuple(first["variants"]):
        cells = ""
        for judge_model in judges:
            run = runs[judge_model]
            answers = run["clean"] if name == "clean" else run["variants"].get(name, {})
            for key in keys:
                value = answers.get(key)
                cells += (
                    "<td class='dash'>&mdash;</td>" if value is None else f"<td>{value:.0f}</td>"
                )
        lines.append(f"<tr><td>{_t(CONTROL_NOTES.get(name, name))}</td>{cells}</tr>")

    head = ""
    for _judge_model in judges:
        for key in keys:
            head += f"<th>{html.escape(_t(labels[key]['label']))}</th>"
    band = "".join(f"<th colspan='{len(keys)}'>{html.escape(name)}</th>" for name in judges)

    # The verdict, computed. A column that moves under both judges on the
    # variant built to attack it is doing its job; one that does not is the
    # finding, and either way the sentence is read off the numbers rather than
    # written under them.
    works, blind = [], []
    for key in keys:
        attacked = [name for name, targets in first.get("expected", {}).items() if key in targets]
        if not attacked:
            continue
        moved = []
        for judge_model in judges:
            run = runs[judge_model]
            for name in attacked:
                before = run["clean"].get(key)
                after = run["variants"].get(name, {}).get(key)
                if before is not None and after is not None:
                    moved.append(after < before)
        label = _t(labels[key]["label"])
        (works if moved and all(moved) else blind).append(label)

    verdict = ""
    if works:
        verdict = f"<p>{html.escape(_t(CONTROL_WORKS).format(columns=_join_words(works)))}</p>"
    if blind:
        verdict += (
            "<div class='warn'><p>"
            + html.escape(_t(CONTROL_BLIND).format(columns=_join_words(blind)))
            + "</p></div>"
        )

    return (
        f"<h3>{_t('Can a quality column come back below 5?')}</h3>"
        + f"<p>{html.escape(_t(CONTROL_LEAD))}</p>"
        + f"<table><thead><tr><th></th>{band}</tr><tr><th>{_t('Note')}</th>{head}</tr></thead>"
        + f"<tbody>{''.join(lines)}</tbody></table>"
        + verdict
        + f"<p class='dash'>{html.escape(_t(CONTROL_CAVEAT))}</p>"
    )


#: What each damaged note is, to a reader who will not open the tool.
CONTROL_NOTES = {
    "clean": "the clean note",
    "shuffled": "same sentences, wrong sections",
    "truncated": "first section only, no assessment or plan",
    "padded": "every sentence said three times",
}

CONTROL_LEAD = (
    "One invented note, and three copies each damaged in one named way. No model "
    "and no session is involved: the question is not who writes well but whether "
    "the instrument can see a fault at all. What each variant was expected to move "
    "was written down before it was asked."
)
CONTROL_WORKS = (
    "It can, and this settles the flat columns: {columns} all drop under both "
    "judges on the note built to attack them. The judge is looking. These eleven "
    "models score the same because they write into the same dictated four-part "
    "structure and genuinely do not differ, not because the question goes "
    "unanswered -- so those columns stay in the tables, as an honest measurement "
    "of something that does not vary here."
)
CONTROL_BLIND = (
    "{columns} did not move even on the note built to attack them. A column whose "
    "value does not change when the fault it names is put in front of it is not "
    "measuring that fault, and its figures in the tables above should be read as "
    "unmeasured rather than as full marks."
)
CONTROL_CAVEAT = (
    "The damage is deliberate and extreme -- every sentence in the wrong section, "
    "a note with no plan at all. This says the instrument responds, not that it "
    "tells two ordinary notes apart. And no person has yet rated any of these "
    "notes on this instrument, so nothing here says a 5 is what a clinician would "
    "give."
)


def _controls() -> str:
    """What each column detects, from the planted-error runs.

    A table of proportions says which model scored higher. It cannot say whether
    the column measures what its heading claims -- for that somebody has to put
    a known fault in front of the judge and see whether it comes back. The
    result belongs beside the numbers rather than in a file the reader would
    have to be told about.
    """
    found = sorted(REPO.joinpath("local").glob("czech-control*.json"))
    if not found:
        return ""

    runs = [json.loads(path.read_text(encoding="utf-8")) for path in found]
    keys = [key for key, _ in COLUMNS[results.TRACK_CZECH_REAL]]

    rows = []
    for run in runs:
        cells = []
        for key in keys:
            detected = run["variants"].get(key, {}).get(key)
            false_alarm = run["clean"].get(key)
            if detected and not false_alarm:
                cells.append("<td>found it</td>")
            elif detected and false_alarm:
                cells.append("<td><strong>also fires on a clean note</strong></td>")
            else:
                cells.append("<td><strong>did not find it</strong></td>")
        rows.append(f"<tr><td>{html.escape(run['judge_model'])}</td>{''.join(cells)}</tr>")

    unreliable = sorted(
        {
            key
            for run in runs
            for key in keys
            if run["clean"].get(key) or not run["variants"].get(key, {}).get(key)
        }
    )
    verdict = (
        "<div class='warn'><p><strong>"
        + html.escape(", ".join(unreliable))
        + "</strong>: "
        + html.escape(
            _t(
                "at least one judge reports this fault in a note that does not have "
                "it, or misses it in a note that does. Read that column as a question "
                "rather than as an answer -- the disagreement is the finding."
            )
        )
        + "</p></div>"
        if unreliable
        else "<p>"
        + html.escape(
            _t(
                "Every criterion found its own fault under every judge, and none fired "
                "on the clean note."
            )
        )
        + "</p>"
    )

    head = "".join(
        f"<th>{html.escape(_t(MEASURE_TABLES[results.TRACK_CZECH_REAL][k]['label']))}</th>"
        for k in keys
    )
    return (
        f"<h2>{_t('Does each column detect what it claims?')}</h2>"
        + "<p>"
        + html.escape(
            _t(
                "One clean note and {variants} variants, each carrying exactly one "
                "deliberate fault of one kind. This is the only check that can tell a "
                "column that measures something from a column that produces numbers."
            ).format(variants=len(keys))
        )
        + "</p>"
        + f"<table><thead><tr><th>{_t('Judge')}</th>{head}</tr></thead>"
        + f"<tbody>{''.join(rows)}</tbody></table>"
        + verdict
    )


def _same_rubric_cutoff(groups: dict, newest: str) -> str:
    """The scoring time of the newest rubric version, for every group in it.

    Two judges finish minutes apart, so "newest" cannot be a single timestamp
    without dropping whichever judge finished first. What is wanted is the
    newest *rubric*: find the version the newest row belongs to, then keep
    every group scored under that version whenever it ran.
    """
    version = None
    for drawn in groups.values():
        if max(row.scored_at or "" for row in drawn) == newest:
            version = drawn[0].judge_prompt_version
            break
    if version is None:
        return ""
    return min(
        max(row.scored_at or "" for row in drawn)
        for drawn in groups.values()
        if drawn[0].judge_prompt_version == version
    )


def build(rows: list[results.Row]) -> str:
    """One table per comparability group -- all six fields of it, not two.

    The rule was stated here and half-implemented: the grouping keyed on the
    track and the judge, which are two of the six fields
    `results.COMPARABILITY_KEYS` names. It held while there was one rubric.
    When `quotes` became a count the rubric became `czech-criteria-v2`, and a
    table keyed on two fields put both versions under one heading -- every
    model twice, from two instruments, exactly the thing the comment above it
    warned about.

    Keyed on `Row.comparability_key()` now, so the six fields decide. A group
    that differs from another only in its rubric version gets its own table and
    its own heading saying which.
    """
    by_group: dict[tuple, list[results.Row]] = defaultdict(list)
    for row in results.latest(rows):
        if row.is_scored:
            by_group[row.comparability_key()].append(row)

    # Said once, before the tables they govern, rather than under each of them.
    # Four copies of one caveat is what teaches a reader to skip the boxes --
    # including the ones that are genuinely different.
    two_judges = False
    withdrawn_from: dict[str, set[str]] = {}
    drawn_instruments: list[tuple[tuple, str]] = []

    sections = []
    for track in results.LOCAL_TRACKS:
        groups = {key: drawn for key, drawn in by_group.items() if drawn[0].track == track}
        if not groups:
            continue
        sections.append(
            f"<h2>{html.escape(_t(TRACK_TITLES.get(track, track)))}</h2>"
            f"<p class='sub'>"
            f"{html.escape(re.sub(r'[*]{2}', '', _t(TRACK_BLURBS.get(track, ''))))}</p>"
        )
        # Only the newest rubric is drawn. An older one is named instead, which
        # is what the published English page does with a superseded harness:
        # drawing both would put two instruments side by side under one track
        # and invite the reader to compare them, and the older is superseded
        # rather than alternative. Newest by when it was scored, not by how its
        # version string sorts.
        newest = max(max(row.scored_at or "" for row in drawn) for drawn in groups.values())
        current = {
            key: drawn
            for key, drawn in groups.items()
            if max(row.scored_at or "" for row in drawn) >= _same_rubric_cutoff(groups, newest)
        }
        withdrawn = {
            drawn[0].judge_prompt_version for key, drawn in groups.items() if key not in current
        }
        ordered = sorted(current.values(), key=lambda drawn: drawn[0].judge_model or "")
        # One table a track, with both judges in every cell, when there are two.
        # Twelve tables for six tracks made a reader flip between two grids to
        # compare one model, and the judges' disagreement -- the only control
        # this track has -- was the thing that flipping hid.
        if len(ordered) > 1:
            first = ordered[0][0]
            # Per judge, not summed over them. Both judges read the SAME notes,
            # so adding their rows counted every note once per judge and every
            # header said twice what exists -- "208 notes" over a corpus of 110,
            # with the true 104 printed in this document's own "What it took"
            # table further down. `_scale` had it right and this did not.
            notes = sum(row.n_sessions_scored for group in ordered for row in group) // len(ordered)
            sections.append(
                f"<p class='sub'>{len(ordered[0])} {_t('models')}, {notes} {_t('notes')}, "
                f"{_t('rubric')} {html.escape(first.judge_prompt_version)}</p>"
                + _merged_table(track, ordered)
            )
            two_judges = True
        else:
            for drawn in ordered:
                first = drawn[0]
                notes = sum(row.n_sessions_scored for row in drawn)
                sections.append(
                    f"<p class='sub'><strong>{_t('Judged by')} "
                    f"{html.escape(first.judge_model or 'unknown')}</strong> &middot; "
                    f"{len(drawn)} {_t('models')}, {notes} {_t('notes')}, "
                    f"{_t('rubric')} {html.escape(first.judge_prompt_version)}</p>"
                    + _table(track, drawn)
                )
        for version in withdrawn:
            withdrawn_from.setdefault(version, set()).add(_t(TRACK_TITLES.get(track, track)))
        # One definition list per instrument. Four of the six tracks ask the
        # same six criteria and printed the same list four times.
        signature = tuple(COLUMNS[track])
        if signature not in {sig for sig, _ in drawn_instruments}:
            drawn_instruments.append((signature, track))

    # --- the caveats and the definitions, once each -------------------------
    once = []
    if two_judges:
        once.append(
            "<div class='warn'><p>"
            + html.escape(
                _t(
                    "Two judges, two tables, and they are not averaged. Where "
                    "they disagree about a model is the only control this track "
                    "has, so the disagreement is the thing to read."
                )
            )
            + "</p></div>"
        )
    for version, tracks in sorted(withdrawn_from.items()):
        once.append(
            "<div class='warn'><p>"
            + html.escape(_t("Not drawn:"))
            + f" {html.escape(_join_words(sorted(tracks)))} "
            + html.escape(_t("were also scored under"))
            + f" {html.escape(version)}"
            + html.escape(
                _t(
                    ", an earlier version of the rubric. Those rows are a "
                    "different instrument rather than an earlier attempt at this "
                    "one, so they are named here and not placed beside these. "
                    "They remain in the local record."
                )
            )
            + "</p></div>"
        )
    for _signature, track in drawn_instruments:
        once.append(
            f"<h3>{_t('What each column is')} &mdash; "
            f"{html.escape(_t(INSTRUMENT_OF.get(track, TRACK_TITLES.get(track, track))))}</h3>"
            + _definitions(track)
        )
    sections.extend(once)

    # Both dictionaries, because a caveat's figures come from two places: the
    # corpora it describes and the run that produced the notes. Neither is
    # typed into the sentence -- a caveat carrying a stale number is worse than
    # no caveat, because it is the paragraph a reader trusts.
    figures = {**_corpus_sizes(), **_written_figures(rows)}
    limits = "".join(
        f"<h3>{html.escape(_t(title))}</h3><p>{html.escape(_t(body).format(**figures))}</p>"
        for title, body in LIMITS
    )

    return f"""<!doctype html>
<html lang="{LANG}"><head><meta charset="utf-8">
<title>{_t(TITLE)}</title><style>{STYLE}</style></head><body>
<h1>{_t(HEADLINE)}</h1>
<p class="sub">{_t(SUBTITLE)}</p>

<div class="summary">{_conclusion(rows)}</div>

<p>{_intro(rows)}</p>
<p>{_t(INTRO_SECOND)}</p>

<div class="warn"><p><strong>{_t(NOT_PUBLIC)}</strong> {_t(NOT_PUBLIC_WHY)}</p></div>

{"".join(sections)}

{_halves(rows)}

{_bands(rows)}

{_variance(rows)}

{_dominance(rows)}

{_verdicts(rows)}

{_controls()}

{_pdsqi_control()}

{_anchor()}

{_join()}

{_external()}

{_formats()}

{_length()}

<h2>{_t("What these numbers cannot be used for")}</h2>
{limits}

<h2>{_t("How it was measured")}</h2>
<p>{_t(METHOD_CORPORA).format(**figures)} <strong>{_t("They are not the same size:")}</strong>
{_t(METHOD_SIZE)}</p>
{_corpus()}
{_scale(rows)}
<p><strong>{_t("No judge is ever shown a real session.")}</strong> {_t(METHOD_BOUNDARY)}</p>
<p>{_t(METHOD_CRITERIA)}</p>
<p>{_t(METHOD_PDSQI)}</p>

<footer>{_t(FOOTER)}</footer>
</body></html>
"""


def main(argv: list[str] | None = None) -> int:
    global LANG

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument(
        "--language",
        choices=i18n.LANGUAGES,
        default=i18n.DEFAULT_LANG,
        help=(
            "which language to write the document in. Czech is for the readers it is "
            "handed to; a missing translation stops the run rather than leaving one "
            "paragraph in English"
        ),
    )
    args = parser.parse_args(argv)
    LANG = args.language

    if not args.source.exists():
        print(f"{args.source} is not there. Run `tnb score-czech` first.", file=sys.stderr)
        return 1

    rows = results.load(args.source)
    if not rows:
        print(f"{args.source} is empty.", file=sys.stderr)
        return 1

    rows, disallowed = results.drawable(rows)
    for line in disallowed:
        print(f"  not drawn: {line}", file=sys.stderr)

    problems = check_no_clinical_text(rows)
    if problems:
        print("Refusing to write: a row carries something that is not a score.", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(build(rows), encoding="utf-8")
    scored = sum(1 for row in results.latest(rows) if row.is_scored)
    print(f"wrote {args.target}  ({scored} scored row(s) from {len(rows)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
