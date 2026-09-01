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
import functools
import html
import json
import re
import sys
from collections import defaultdict
from decimal import Decimal
from itertools import combinations
from pathlib import Path
from typing import NamedTuple

from tnb import i18n, results
from tnb.report import (
    COLUMNS,
    DRAWN_CRITERIA,
    MEASURE_TABLES,
    TRACK_BLURBS,
    TRACK_SWITCH_LABELS,
    TRACK_TITLES,
)
from tnb.scoring import czech as czech_scorer
from tnb.tasks import TASKS
from tnb.tasks import deepsy as deepsy_task

sys.path.insert(0, str(Path(__file__).resolve().parent))
from czech_brief_cs import CS  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO / "local" / "czech-rows.jsonl"
DEFAULT_TARGET = REPO / "local" / "czech-brief.html"


def default_target(language: str) -> Path:
    """Where the document goes when `--target` is not given.

    It has to depend on the language. When it did not, `--language cs` wrote
    over `czech-brief.html` -- the English document -- and left the Czech one
    stale at whatever hour it was last built by hand. Nothing failed and both
    files existed, so the only way to notice was to open the English one and
    find Czech in it.
    """
    if language == i18n.DEFAULT_LANG:
        return DEFAULT_TARGET
    return DEFAULT_TARGET.with_name(f"{DEFAULT_TARGET.stem}-{language}.html")


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
/* The page this becomes. `tools/pdf.py` prints through Chrome, and without a
   @page rule Chrome picks the paper and the margins from whatever the machine
   printed to last -- so the document that goes to the team was a different
   shape depending on who made it. `tools/brief.py` has said A4 since it was
   written and this file never did. */
@page { size: A4; margin: 17mm 15mm 15mm; }
@page :first { margin-top: 15mm; }
:root { --ink:#14161a; --muted:#5b6270; --rule:#d8dce3; --accent:#1c4e80; }
* { box-sizing: border-box; }
/* `print-color-adjust` here rather than `!important` on each tinted block. The
   browser drops backgrounds when it prints, to save ink; saying once that this
   document means its colours is the supported way to ask for them, and the
   alternative is one `!important` per block that a reader of the stylesheet
   has to recognise as a workaround rather than as a decision. */
body { font: 11pt/1.5 "Source Serif 4", Georgia, serif; color: var(--ink);
       max-width: 52rem; margin: 0 auto; padding: 2.5rem 1.5rem 4rem;
       -webkit-print-color-adjust: exact; print-color-adjust: exact; }
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
/* The three tinted blocks: the summary a reader who reads nothing else should
   read, the findings that close a chapter, and the closing summary at the end.
   One rule for the shape and one line each for the tint, because they are the
   same kind of thing and a reader who learns the shape once should not have to
   learn it three times. The finding carries a rule down its left edge so that
   it reads as a conclusion rather than as a second introduction -- at the same
   weight as the summary, which is the point of it: what a chapter concluded is
   not a smaller claim than what the front page promised. */
.summary, .finding, .closing { border: 1px solid var(--rule); border-radius: 3px;
           padding: .2rem 1.1rem 1rem; margin: 1.4rem 0 1.8rem; }
.summary { background: #f4f6f9; }
.finding { background: #f2f6f2; border-left: 3px solid var(--accent); }
.closing { background: #f7f6f2; }
.summary h2, .finding h2, .closing h2 { margin-top: 1.2rem; border-bottom: none; }
.summary h3, .finding h3, .closing h3 { margin-top: 1rem; }
.summary p:last-child, .finding p:last-child, .closing p:last-child { margin-bottom: 0; }
.warn p { margin: .4rem 0; }
/* A figure is inline SVG, drawn at a fixed canvas size and scaled to whatever
   width the page has. Without the `width: 100%` it prints at its own pixel
   width and runs off the paper; without `height: auto` it keeps the pixel
   height and the drawing distorts. */
figure { margin: 1.2rem 0 1.4rem; break-inside: avoid; }
figure svg { width: 100%; height: auto; }
figcaption { font-size: .82rem; color: var(--muted); margin-top: .4rem; }
/* `summary` the element, not `.summary` the tinted block above -- HTML gave
   them the same word. Every toggle in this document is written open, because a
   closed one prints as a bare heading with its contents gone, so the marker is
   the only thing saying there is anything to collapse at all. */
details { margin: .8rem 0 1.2rem; padding: .1rem 0 .1rem .9rem;
          border-left: 1px solid var(--rule); }
details > summary { font-weight: 600; font-family: "Source Sans 3", system-ui, sans-serif;
          font-size: .85rem; cursor: pointer; margin: .2rem 0 .4rem; }
details > summary::marker { color: var(--muted); }
footer { margin-top: 3rem; padding-top: .8rem; border-top: 1px solid var(--rule);
         color: var(--muted); font-size: .8rem; }
code { font-family: ui-monospace, monospace; font-size: .9em; }
@media print {
  body { max-width: none; padding: 0; font-size: 10pt; }
  /* `rem` is the ROOT font size and the root has none set, so a table sized in
     rem printed at the browser default -- about 10.2pt beside 10pt of prose,
     on paper 15mm narrower than the screen it was laid out for. The widest
     table lost its last two columns off the right edge of the Czech print,
     where the headings are long words. In `em` the tables scale with the
     printed body, which is what the screen rule meant all along. */
  table { font-size: .85em; }
  th, td { padding: .3rem .35rem; }
  h2 { break-after: avoid; } table { break-inside: auto; }
  tr { break-inside: avoid; } .warn { break-inside: avoid; }
  .summary, .finding, .closing { break-inside: avoid; }
  details { break-inside: avoid; }
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
    "PDSQI-9 was put to {pdsqi_formats}. Both, "
    "because neither answers the other: a flawless Czech sentence about nothing "
    "passes all six criteria, and a note full of insight can be written in bad "
    "Czech."
)
#: Every word the summary uses before anything defines it, defined before the
#: summary. The eleven paragraphs open with "in the top band of all 4 tables
#: bands cover -- the SOAP halves, both judges", which is five terms deep and
#: none of them had been introduced: the column definitions and the corpus
#: description sat two screens below, under the tables they belong to. A reader
#: who has never seen this project met the findings first and the vocabulary
#: after, and the findings are unreadable in that order.
#:
#: Short entries on purpose. This is the thing a reader glances back at, not a
#: chapter, and every entry that grew past two sentences moved into the chapter
#: it belongs to.
GLOSSARY_HEADING = "What each word here means"
GLOSSARY = (
    (
        "a note",
        "What a model writes after reading one session transcript. It is the thing "
        "being measured; nothing here measures the therapy.",
    ),
    (
        "a judge",
        "Another language model, which reads a note and answers the questions about "
        "it. There are two, from two different vendors, and they answer separately "
        "and are never averaged. They are not people, and where they disagree is "
        "the only check this study has.",
    ),
    (
        "a criterion",
        "One yes/no question about a note. Six of them, all about whether the Czech "
        "itself is right -- diacritics, calques, untranslated terms, agreement, "
        "register, non-words. A column is the share of notes free of that fault.",
    ),
    (
        "PDSQI-9",
        "A published instrument that asks something else: whether the note is any "
        "good clinically. Eight attributes, and on the real sessions six of them: "
        "`accurate` and `thorough` need the transcript, which never leaves e-INFRA.",
    ),
    (
        "SOAP and Deepsy",
        "Two note formats. SOAP has four sections and every model has seen "
        "thousands of them. Deepsy is the form the Deepsy application really "
        "writes: eleven sections, and no model has seen it before. They are never "
        "pooled.",
    ),
    (
        "the two halves",
        "The two sets of sessions. One is real therapy with one client, transcribed "
        "and de-identified by hand and never published. The other is public "
        "counselling conversations translated into Czech. Every model wrote from "
        "both, so two models are never compared on different sessions.",
    ),
    (
        "a track",
        "One format on one half -- SOAP on the real sessions, SOAP on the "
        "translated ones, and the same two for Deepsy. Four in all, and each is "
        "judged twice, which is where the eight tables come from.",
    ),
    (
        "a band",
        "A group of models this measurement cannot tell apart. It is not a rank: "
        "inside a band nothing separates them, and the band ends where the "
        "difference is bigger than resampling the sessions can explain away. A "
        "narrow band means the measurement resolves finely, not that a model is "
        "good.",
    ),
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
#: Printed only where there are Deepsy rows to be printed about. It says which
#: notes an instrument was never put to, and a document with no Deepsy rows in
#: it would be naming a gap that is not there.
#:
#: It used to be a clause of the method's footnote, three screens past the last
#: Deepsy table. It is the only sentence in the document saying that not one
#: quality figure anywhere in it describes a Deepsy note, and a reader who has
#: just read two Deepsy tables is the reader who needs to know that -- so it is
#: printed in the Deepsy chapter, beside the tables it is about.
SCALE_NO_PDSQI = (
    "The {deepsy} notes in the Deepsy format were read against the criteria only. "
    "PDSQI-9 was never asked about a Deepsy note, so no quality figure anywhere in "
    "this document is about one."
)
METHOD_CORPORA = (
    "Two halves, both read only from a directory that is not in version control. Every "
    "model was asked for a note from every transcript, on e-INFRA -- that is the design, "
    "and {written} of the {asked} notes are the outcome. Which models wrote fewer, and "
    "how many fewer, is named in the first of the caveats above."
)
#: Where each step ran, which is the confidentiality boundary and was the lead
#: paragraph of a table counting notes and calls. The table is gone -- the
#: three-views chapter counts the notes and the calls where a reader has a
#: reason to care -- and this is the half of it that was not arithmetic.
METHOD_WHERE = (
    "Where each step ran is the confidentiality boundary of this whole project. Every "
    "note was written on e-INFRA, the infrastructure that also holds the sessions, so no "
    "transcript ever left it to be summarised. Only the notes went anywhere else: each "
    "was put to two judges, one question at a time, on Google's and OpenAI's endpoints."
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

#: The caveat whose evidence exists, so that its own paragraph can carry it.
#: Matched by its title rather than by position, because the list is reordered
#: whenever a reader's first question changes.
RATER_LIMIT = "Almost nothing here has been checked against a person"

LIMITS = [
    (
        "Ten sessions, and they are all one client",
        "Every model was asked for a note from every transcript, and that is what makes "
        "comparing them valid at all -- the first attempt gave each model a different "
        "session, and it could not tell a worse model from a harder session. The asking "
        "held; the answering did not always. {written} of the {asked} notes came back, "
        "and where a model wrote fewer it is named: {short}. But ten notes per model is "
        "a small number. One note falling the other way moves a share by a tenth, which "
        "is wider than most of the gaps between neighbouring rows in these tables, so "
        "two models a few hundredths apart are not two models an extra week of "
        "measurement would keep apart. And the real half is ten sessions with one "
        "client and one therapist: everything measured there is also a fact about that "
        "therapist's way of working and that client's way of talking. Read the ordering. "
        "Do not read the gaps between neighbours.",
    ),
    (
        "The two halves differ by more than language, and mostly by size",
        "A real session runs to a median of {real_words} words and {real_turns} turns; a "
        "translated AnnoMI conversation to {other_words} words and {other_turns} turns -- "
        "{ratio} times the material to read before a word of Czech is written. "
        "Summarising the longer one is a harder task on its own. They differ in subject "
        "as well: AnnoMI is motivational interviewing about substance use, the real "
        "sessions are not, and the two were transcribed by different hands to different "
        "conventions. So a model that does worse on one half may be doing worse at "
        "length, at motivational interviewing, or at Czech, and nothing here separates "
        "the three. The one thing the two halves are good for is the comparison between "
        "them: a fault that appears on both is the model's, and a fault that appears "
        "only on the translated half belongs to the text it was given.",
    ),
    (
        "Nothing here says whether a note is true",
        "This is the caveat to read first if these numbers are going anywhere near a "
        "clinic. The six criteria ask about the Czech and nothing else -- are the "
        "diacritics right, is this phrase a literal translation from English, is the "
        "register a clinician's. A note that is fluent, correctly typeset and entirely "
        "invented passes all six of them. The quality instrument does not close the gap "
        "either: the two attributes that would ask whether the note is accurate and "
        "whether it is thorough are exactly the ones that cannot be asked about a real "
        "session here, because answering them means putting the transcript in front of a "
        "judge and no transcript leaves the machine that holds it. So no number anywhere "
        "in this document is evidence that a note says what happened in the session. For "
        "a clinical team that is the first question, and it is the one measurement "
        "nobody here has made.",
    ),
    (
        RATER_LIMIT,
        "These six criteria are this repository's own. No published Czech note-quality "
        "instrument exists to reproduce, so they were written for this track -- and "
        "unlike PDSQI-9 there is not even a published figure saying how often two people "
        "answering them would agree with each other. What stands in for that here is two "
        "independent judges answering every question separately, which is why this "
        "document prints both of them in every cell and marks the cells where they "
        "differ: the disagreement is the control.",
    ),
]

#: The sentence that keeps the caveat above from being an absolute. One native
#: speaker has answered these questions, and a caveat saying nobody has would
#: be false against a payload this same document reads six paragraphs earlier.
#: Written as a whole sentence with the figures read from that payload, never
#: typed: what the anchor covers is exactly as narrow as the numbers say.
RATER_MEASURED = (
    "One exception, and it is small enough to state exactly. A native speaker has "
    "answered all {criteria} questions about {notes} of these notes, and the two judges "
    "answered as he did on {low} and {high} of them. That is a comparison and not a "
    "ceiling: with one rater there is no second person to say how far two people would "
    "have agreed with each other, so where a judge and he differ, nothing here says "
    "which of them was right. The count for each criterion is in the criterion-by-"
    "criterion chapter above, and it is all there is -- nobody has rated a note in the "
    "Deepsy format, a note from the translated half, or any note at all on PDSQI-9."
)


def _rater_limit() -> str:
    """What one native speaker actually covered, from the payload that holds it.

    Empty when there is no anchor in this checkout, and then the caveat above
    stands unqualified -- which is correct, because in that checkout nobody has
    rated anything.
    """
    path = REPO / "local" / "czech-anchor.json"
    if not path.exists():
        return ""
    data = json.loads(path.read_text(encoding="utf-8"))
    rates = [
        block["rate"] for block in data.get("judges", {}).values() if block.get("rate") is not None
    ]
    criteria = {
        key for block in data.get("judges", {}).values() for key in block.get("criteria", {})
    }
    if not rates or not criteria or not data.get("notes_rated"):
        return ""
    return _t(RATER_MEASURED).format(
        criteria=len(criteria),
        notes=data["notes_rated"],
        low=f"{min(rates):.0%}",
        high=f"{max(rates):.0%}",
    )


def _limits(figures: dict[str, str]) -> str:
    """The four caveats, and the one measurement one of them has to answer to.

    Four rather than six. The fifth was the reason SOAP is not what a Czech
    psychologist writes, which is not a caveat but the reason the Deepsy chapter
    exists, and it opens that chapter now. The sixth warned that two judges
    agreeing about a column every model passes says nothing -- a warning about
    the separability tables, which this document no longer draws.

    Each of the four is longer than it was. A caveat a reader skims is a caveat
    that did not happen, and these were four lines each in a chapter a reader
    reaches after twenty pages of tables.
    """
    out = []
    for title, body in LIMITS:
        out.append(
            f"<h3>{html.escape(_t(title))}</h3><p>{html.escape(_t(body).format(**figures))}</p>"
        )
        # Its own paragraph, not a tail on the one above: it is the one place
        # in this chapter where something WAS measured, and a reader skimming
        # bold headings and first lines should be able to find it.
        if title == RATER_LIMIT:
            measured = _rater_limit()
            if measured:
                out.append(f"<p>{html.escape(measured)}</p>")
    return "".join(out)


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
    medians = []
    halves = (("real", czech_task.load_real), ("other", czech_task.load_translated))
    for prefix, load in halves:
        try:
            sessions = load()
        except (RuntimeError, OSError):
            sessions = []
        if not sessions:
            return dict.fromkeys(
                ("real_words", "real_turns", "other_words", "other_turns", "ratio"), "?"
            )
        words = sorted(session.word_count for session in sessions)
        turns = sorted(len(session.turns) for session in sessions)
        medians.append(words[len(words) // 2])
        out[f"{prefix}_words"] = _grouped(words[len(words) // 2])
        out[f"{prefix}_turns"] = _grouped(turns[len(turns) // 2])
    # How many times longer one half is than the other, for the caveat that
    # says so. It said "Seven times the material" in a typed sentence while
    # the corpora block three chapters above printed the measured 7.5.
    out["ratio"] = _decimal(medians[0] / medians[1], 1) if medians[1] else "?"
    return out


def _fmt(value, digits: int) -> str:
    if value is None:
        return '<span class="dash">--</span>'
    return f"{value:.{digits}f}"


def _decimal(value: float, digits: int) -> str:
    """A decimal inside a sentence, in the reader's language.

    English writes 7.5 and Czech writes 7,5. The tables print a full stop in
    both languages, which is a convention a grid of figures can carry; a Czech
    sentence saying a session runs "7.5krat" longer reads as a typo.
    `czech_crosscheck` normalises the separator before comparing the two
    documents, so they still print the same set of figures.
    """
    text = f"{value:.{digits}f}"
    return text if LANG == "en" else text.replace(".", ",")


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
    """A definition without the sentence all of them end with.

    Two repairs, and both were only visible once the definitions moved above
    the tables and became the first thing a reader meets.

    **The tail is matched in the language the definition is written in.** The
    list of tails is English and the definition arrives translated, so in Czech
    nothing ever matched: the English list lost its six repetitions and the
    Czech list kept all six -- and the Czech list is the one that goes to the
    readers this document is written for. Each tail is now also looked up
    through `_t`, which means a missing Czech tail stops the build rather than
    printing the sentence six times again.

    **And the cut lands mid-sentence.** "PDSQI-9 item 2, rated 1 to 5." leaves
    a comma standing where the full stop was, in both languages. Eight
    definitions ended on a hanging comma.
    """
    for tail in _SHARED_TAILS:
        for ending in (tail.strip(), _t(tail).strip()):
            if text.endswith(ending):
                kept = text[: -len(ending)].rstrip(" ,;")
                return kept if kept.endswith(".") else kept + "."
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


def _dominance_wins(systems: list[str], keys, tables: dict) -> dict[str, int]:
    """How many other systems each one dominates outright.

    The mirror of `_dominance_places`, and not derivable from it. Being beaten
    by nobody and beating nobody are both common here and mean opposite things:
    the first says no evidence puts anyone above you, the second says no
    evidence puts you above anyone. A table showing only the first reads as
    though everybody tied for first.
    """

    def beats(system: str) -> int:
        return sum(
            1 for other in systems if other != system and _dominates(system, other, keys, tables)
        )

    return {system: beats(system) for system in systems}


#: Which half's composite a PDSQI track's band was built from. The criteria
#: tracks band on `DRAWN_CRITERIA`; the PDSQI tracks band on a set
#: computed per half by `tools/czech_variance.py` and recorded in the payload,
#: because the real half cannot ask the two attributes that need the session.
_PDSQI_HALF = {
    results.TRACK_CZECH_REAL_PDSQI: "real",
    results.TRACK_DEEPSY_REAL_PDSQI: "real",
    results.TRACK_CZECH_TRANSLATED_PDSQI: "translated",
    results.TRACK_DEEPSY_TRANSLATED_PDSQI: "translated",
}


def _band_shares(track: str, rows_by_judge: dict) -> dict[str, list[tuple[str, float]]]:
    """Per judge, what fraction of the band each composite column supplies.

    A mean weights a column by how far it spreads, so the share is the column's
    range over the sum of the ranges. A column every model scores the same on
    has a range of zero and supplies nothing -- it is in the mean and cannot
    move anything in it.

    Computed from the rows the table already holds rather than from a payload,
    so it cannot fall out of step with the numbers printed beside it.
    """
    half = _PDSQI_HALF.get(track)
    if half is None:
        keys = list(DRAWN_CRITERIA)
    else:
        keys = list((_payload("czech-variance.json").get("composites") or {}).get(half) or [])
    if not keys:
        return {}

    out: dict[str, list[tuple[str, float]]] = {}
    for judge, by_system in rows_by_judge.items():
        spread = {}
        for key in keys:
            values = [
                row.metrics.headline[key]
                for row in by_system.values()
                if row.metrics.headline.get(key) is not None
            ]
            spread[key] = (max(values) - min(values)) if values else 0.0
        total = sum(spread.values())
        if not total:
            continue
        out[judge] = sorted(((key, spread[key] / total) for key in keys), key=lambda kv: -kv[1])
    return out


def _merged_table(track: str, groups: list[list[results.Row]], *, lead: bool = False) -> str:
    """One table for a track, with every judge's value in every cell.

    Twelve tables became six. Nothing is averaged: the two numbers sit side by
    side, so a model the judges disagree about shows it in the cell rather than
    on another page.

    Rows are ordered by dominance and models nothing separates share a place.
    Within a shared place they are ordered by `_rank_of` -- the mean of the
    columns that vary -- with the name only as the final tie-break.

    **The caption used to say that within a place the order is alphabetical, and
    that was not true of the sort beside it.** The key has always been
    `(place, -index, name)`. A reader who believed the caption would have read
    the four models sharing the top place as unordered when they are not, and
    would have been unable to reproduce the published order from the rule they
    were given.

    `lead` says whether this table has to name its own two judges. Normally it
    does not, because every table on the page holds the same pair and
    `_how_to_read` names them once above all of them. It is set only where that
    is not true -- two tracks judged by different pairs -- and there one
    sentence above the page could not be true of both.
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
    # The same columns, deliberately: a model that beats another on the
    # varying columns and loses on a flat one has not lost anywhere a
    # reader can see, and the two halves of the order must be computed
    # over one set or they contradict each other.
    wins = _dominance_wins(systems, varying or keys, tables)

    def index_of(system: str) -> float:
        found = [
            _rank_of(track, rows_by_judge[judge][system], varying)
            for judge in judges
            if system in rows_by_judge[judge]
        ]
        return sum(found) / len(found) if found else -1.0

    ordered = sorted(systems, key=lambda s: (places[s], -index_of(s), s))

    # The band a model falls in, folded into the table it is a grouping of. It
    # had a panel of its own -- twelve more tables, the same models, on another
    # page -- and a reader comparing one model had to hold both layouts at once.
    numbers = _band_numbers(track)
    banded = _banded(numbers, judges, systems)
    head = (
        f"<th>{_t('Order')}</th>"
        + f"<th>{_t('Beats')}</th>"
        + (f"<th>{_t('Band')}</th>" if banded else "")
        + "".join(f"<th>{html.escape(_t(measures[key]['label']))}</th>" for key, _ in columns)
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
            joined = _pair(values)
            css = " class='differ'" if differ else ""
            cells.append(f"<td{css}>{joined}</td>")
        index = _pair(
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
            notes = f"{_pair(complete)} {_t('of')} {corpus}"
        band = _band_cell(numbers, judges, system) if banded else ""
        # How many systems this one beats outright. One number, not a pair: it
        # is already defined across both judges, so splitting it per judge would
        # be a different and weaker claim in the same column.
        beats = f"<td>{wins[system]}</td>"
        body.append(
            f"<tr{mark}><td>{html.escape(system)}</td><td>{notes}</td>"
            f"<td><strong>{index}</strong></td>{beats}{band}{''.join(cells)}</tr>"
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
    # What the two judges in a cell are, what the notes column counts and what
    # range the numbers run over is said once above all the tables, by
    # `_how_to_read`. What is left here is what this table alone can say.
    order_line = _t(MERGED_ORDER).format(places=len(set(shared)), systems=len(systems), tied=ties)
    warning = ""
    if thin:
        warning = (
            "<div class='warn'><p>"
            + html.escape(_t(THIN_ROWS))
            + f" {html.escape(', '.join(thin))}.</p></div>"
        )
    caption = f"{_t(ROWS_ARE_MODELS)} {order_line}"
    if lead:
        caption = f"{_t(MERGED_LEAD).format(judges=_join_words(judges))} {caption}"

    # What the Band column actually rests on. Naming the columns is not enough:
    # one of them can supply most of the band, and a column every model scores
    # the same on supplies none of it while still sitting in the mean.
    shares = _band_shares(track, rows_by_judge) if banded else {}
    weights = ""
    if shares:
        said = []
        for judge in judges:
            ranked = shares.get(judge)
            if not ranked:
                continue
            top, share = ranked[0]
            mute = [key for key, part in ranked if part <= 0]
            piece = _t(BAND_SHARE).format(
                judge=judge,
                measure=_t(measures[top]["label"]) if top in measures else top,
                share=f"{share * 100:.0f}",
            )
            if mute:
                phrase = BAND_SHARE_MUTE_ONE if len(mute) == 1 else BAND_SHARE_MUTE
                piece += " " + _t(phrase).format(
                    n=len(mute),
                    total=len(ranked),
                    measures=_join_words(
                        [_t(measures[key]["label"]) if key in measures else key for key in mute]
                    ),
                )
            said.append(piece)
        # Which of the composite's columns are measured on a different ruler from
        # the rest. Read from `MEASURE_TABLES`, where every measure's scale is
        # already recorded, rather than inferred from the values.
        scale_line = ""
        by_scale: dict[str, list[str]] = {}
        for key, _part in next(iter(shares.values())):
            scale = (measures.get(key) or {}).get("scale")
            if scale:
                by_scale.setdefault(scale, []).append(key)
        if len(by_scale) > 1:
            main = max(by_scale, key=lambda k: len(by_scale[k]))
            odd = [key for scale, keys in by_scale.items() if scale != main for key in keys]
            odd_scale = next(scale for scale in by_scale if scale != main)
            scale_line = " " + _t(BAND_SHARE_SCALE).format(
                odd=_join_words(
                    [_t(measures[key]["label"]) if key in measures else key for key in odd]
                ),
                verb=_t("is") if len(odd) == 1 else _t("are"),
                odd_scale=odd_scale,
                main=main,
            )

        # And whether those numbers come back the same when the judge is asked
        # again. Only for the halves that were actually asked twice.
        repeat_line = ""
        measured = (_payload("czech-repeatability.json").get("halves") or {}).get(track)
        if measured:
            parts = []
            for judge in judges:
                block = (measured.get(judge) or {}).get("attributes") or {}
                if not block:
                    continue
                worst_key = min(block, key=lambda k: block[k]["identical_share"])
                worst = block[worst_key]
                overall = sum(c["identical"] for c in block.values()) / sum(
                    c["n"] for c in block.values()
                )
                piece = _t(REPEAT_JUDGE).format(
                    judge=judge,
                    share=f"{overall:.0%}",
                    notes=(measured.get(judge) or {}).get("notes", "?"),
                )
                if worst["identical_share"] >= 1.0:
                    piece += f" — {_t(REPEAT_PERFECT)}"
                else:
                    label = _t(measures[worst_key]["label"]) if worst_key in measures else worst_key
                    piece += " — " + _t(REPEAT_WORST).format(
                        measure=label,
                        share=f"{worst['identical_share']:.0%}",
                        median=f"{worst['median_abs']:.2f}",
                        worst=f"{worst['max_abs']:.2f}",
                    )
                parts.append(piece)
            if parts:
                repeat_line = (
                    "<p class='note'>"
                    + html.escape(f"{_t(REPEAT_LEAD)} {'; '.join(parts)}.")
                    + "</p>"
                )
        elif track in DEEPSY_PDSQI_TRACKS:
            repeat_line = "<p class='note'>" + html.escape(_t(REPEAT_ABSENT)) + "</p>"

        if said:
            # Joined with a semicolon and closed with a stop: the two judges'
            # clauses ran into each other and into the sentence after them,
            # which read as one sentence saying something neither says.
            weights = (
                "<p class='note'>"
                + html.escape(
                    f"{_t(BAND_SHARE_LEAD)} {'; '.join(said)}.{scale_line} {_t(BAND_SHARE_ORDER)}"
                )
                + "</p>"
            )

    return (
        f"<p class='sub'>{html.escape(caption)}</p>" + f"<table><thead><tr><th>{_t('Model')}</th>"
        f"<th>{_t('Notes in the mean')}</th>{head}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>{weights}{repeat_line}{warning}"
    )


#: Whether the judge gives the same answer twice, said under the table whose
#: numbers depend on it. Measured by `tools/czech_repeatability.py`, which asks
#: both judges the same questions a second time into a cache root of its own.
#:
#: **This is the one measurement here that checks the instrument rather than the
#: models**, and until now it reached no reader: the tool wrote a payload and
#: nothing read it.
REPEAT_LEAD = "Asked a second time, the same judge about the same notes:"
REPEAT_JUDGE = "{judge} repeated {share} of its answers on {notes} notes"
REPEAT_WORST = (
    "its least repeatable column is {measure}, identical on {share} of them, with a "
    "median shift of {median} and a worst of {worst} on a scale of 1 to 5"
)
REPEAT_PERFECT = "every column identically"
#: The halves nobody asked twice. Said rather than left to the reader to assume
#: the SOAP answer carries -- which is the mistake the planted-error control was
#: repaired for making.
REPEAT_ABSENT = (
    "The Deepsy halves were not asked twice, so nothing here says whether a judge "
    "repeats itself on them."
)


#: What the Band column rests on, said under the table it is drawn in.
#:
#: **Naming the columns was not enough.** The document already lists the
#: measures a band is built from, which reads as though they share the work.
#: They do not: a mean weights each column by how far it happens to spread, and
#: on one of these tables a single column supplies 78% of everything separating
#: the models while two supply nothing at all. Spread is a fact about how widely
#: the judge graded, not about what matters clinically, so that weighting is
#: nobody's decision -- which is exactly why it has to be printed.
BAND_SHARE_LEAD = "What the Band column rests on, measured rather than assumed:"
#: The per-cent sign lives in the sentence, not in the number: Czech sets a
#: space before it and English does not, and a preformatted "81%" forces one
#: language to be wrong.
BAND_SHARE = "under {judge}, {measure} supplies {share}% of what separates the models"
BAND_SHARE_MUTE = (
    "and {n} of the {total} sit in the mean supplying none of it, because every model "
    "scores the same on them ({measures})"
)
#: The same, for the one table where exactly one column is mute. A count that is
#: sometimes 1 and sometimes 3 needs both, and "1 of the 6 sit" is the kind of
#: sentence a reader stops at.
BAND_SHARE_MUTE_ONE = (
    "and 1 of the {total} sits in the mean supplying none of it, because every model "
    "scores the same on it ({measures})"
)
#: The consequence, and the reason a reader must not read a low Band cell as a
#: verdict. The rows are ordered by dominance, which has no weights at all; the
#: Band column is the weighted mean above. They can disagree, and on the Deepsy
#: real table they do: a model no other model beats sits in the bottom band,
#: because it writes long notes and the column that punishes that supplies most
#: of the band.
#: The part of the weighting that is not the judge's habit but the instrument's
#: units. Said separately from the shares because it is a different kind of
#: fault: a column can be given more say by spreading more, which is accidental,
#: or by being measured on a longer ruler, which is structural and would go away
#: if the columns were rescaled onto one range before the mean -- which is what
#: HELM did when it moved its leaderboard back from win rates to a mean.
BAND_SHARE_SCALE = (
    "The columns are also not on one ruler: {odd} {verb} scored {odd_scale} while the "
    "rest run {main}, so the same disagreement counts for less on {odd} than on any "
    "other column, whatever it measures. Nothing here rescales them before the mean."
)
BAND_SHARE_ORDER = (
    "The row order is not built this way: a model is above another only when it is at "
    "least as good on every column under both judges, which uses no weights at all. The "
    "two therefore disagree on some rows, and neither is the corrective for the other -- "
    "they fail in opposite directions. A mean lets one wide column decide the order; an "
    "every-column rule lets one narrow cell veto it, so a model beaten on eleven of "
    "twelve cells can still be beaten by nobody on the strength of the twelfth. Read the "
    "two together, and where they disagree read the columns themselves."
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
#: **The whole rule, because there is nowhere else to read it.** The chapter
#: that defined dominance is gone, and this caption uses the word over all six
#: tables -- so the clause it was missing, that the model above must also be
#: better on at least one column, moved here. `_dominates` has always required
#: it; the caption said only half of what the sort does.
MERGED_ORDER = (
    "The rows are ordered by dominance -- a model is above another only when it is "
    "at least as good on every column under BOTH judges, and better than it on at "
    "least one -- so models the evidence cannot separate share a place, and "
    "{systems} models fall into {places} places of which {tied} hold more than one. "
    "Within a place the rows are ordered by the mean of the columns that vary, "
    "which puts a row somewhere without claiming the evidence separates it."
)

#: The Band column, explained once above the tables that carry it. It replaces
#: a panel of twelve tables that drew the same grouping the score tables draw,
#: over again and on another page, so that a reader comparing one model had to
#: hold two layouts in mind at once.
#:
#: **The second sentence is the one that has to be there.** A band is keyed on
#: the track AND the judge, and the score table holds both judges in every
#: cell, so the Band cell holds two numbers and they can be 1 and 3. Read as a
#: rank -- which is what a single small integer beside a model's name looks
#: like -- it is exactly the ordering this document spends a page declining to
#: print, and it would be an ordering two judges do not agree on.
#: What the Beats column counts, said where it is read. Without this a 0 reads
#: as a mark out of twelve. It is not a mark: it says no evidence puts this
#: model above any other, which on a table whose columns disagree with each
#: other is the ordinary case. The column exists because the `Order` column
#: carries the mirror -- how many beat IT -- and that one is 0 for almost
#: everybody here, so a reader seeing only it would read the table as a
#: twelve-way tie for first.
BEATS_COLUMN = (
    "The Beats column counts how many of the other models this one beats outright: at "
    "least as good on every column of this table, under both judges, and better on at "
    "least one. Nothing is weighted and nothing is averaged, so no column is quietly "
    "given more say than another -- which matters here, because the columns are on "
    "different scales and do not agree with each other."
)
BEATS_COLUMN_ZERO = (
    "A 0 is not a low score. It says the evidence does not place that model above any "
    "other, and a model can be beaten by nobody and beat nobody at once. Where most of "
    "a column is 0, that is the finding: these measures do not separate these models."
)
BAND_COLUMN = (
    "The Band column groups the models rather than ordering them: within a band nothing "
    "separates them, and a band ends where the gap exceeds what resampling the sessions "
    "can rule out, so a band's width is this measurement's own resolution."
)
BAND_TWO_JUDGES = (
    "Like every other cell it holds one value per judge, so a model can be in band 1 "
    "under one judge and band 3 under the other; a marked Band cell is that "
    "disagreement, and the number in it is not a rank."
)

#: The other reason a band is provisional, and it applies to a full row as much
#: as to a thin one. The boundary is drawn at a threshold the resampling
#: reproduces only so far, and a model whose gap sits inside that is drawn in a
#: band because the table has to draw it somewhere -- not because it was placed
#: there. `czech_variance.THRESHOLD_JITTER` carries the measurement.
#:
#: It is the only sentence anywhere saying a band boundary reproduces to about
#: a hundredth, so without it the Band column would claim a precision its own
#: payload denies.
BAND_UNRESOLVED = (
    "A band boundary is drawn at a threshold that resampling the sessions reproduces "
    "only to about {jitter}. These models sit within that of one, so this measurement "
    "does not place them: a different resample puts them in the next band along."
)


def _band_numbers(track: str) -> dict[str, dict[str, int]]:
    """Which band each model falls in on this track, per judge.

    Read through `_payload`, which returns nothing when `local/` has not been
    built -- the tables have to draw from rows alone, and a page built from
    fixture rows has no payload beside it. A `json.loads` here would stop the
    document rather than draw it without the column.
    """
    judges = (_payload("czech-variance.json").get("bands") or {}).get(track) or {}
    return {
        judge: {
            model: number
            for number, band in enumerate(grouped["bands"], start=1)
            for model in band["models"]
        }
        for judge, grouped in judges.items()
    }


def _banded(numbers: dict[str, dict[str, int]], judges: list[str], systems) -> bool:
    """Whether a Band column would say anything about the models in this table.

    Not merely whether the payload has bands for the track. A column of dashes
    is an absence dressed as a measurement, and it is what a page built before
    the bands were recomputed -- or from rows the payload has never seen --
    would otherwise draw.
    """
    drawn = set(systems)
    return any(numbers.get(judge, {}).keys() & drawn for judge in judges)


#: The separator inside a cell that holds one value per judge. Non-breaking,
#: because such a cell is a single reading under two instruments rather than
#: two words, and a break between them is what put `4.32 /` and `3.72` on
#: different lines of the Czech print -- where the PDF text layer then emitted
#: the row's first lines before its second ones and glued a neighbouring `--`
#: onto the number. See `tests/test_judge_pair_cannot_break.py`.
JUDGE_PAIR = "&nbsp;/&nbsp;"


def _pair(values) -> str:
    """One cell's worth of per-judge values, joined so they cannot separate."""
    return JUDGE_PAIR.join(str(value) for value in values)


def _band_cell(numbers: dict[str, dict[str, int]], judges: list[str], system: str) -> str:
    """One Band cell: a number per judge, marked where they differ.

    Marked by the same rule and the same class as every score cell, because it
    is the same kind of fact. A model in no band under a judge -- it wrote
    nothing that judge could place -- shows the dash the score columns show,
    rather than a number borrowed from the other judge.
    """
    values = [str(numbers.get(judge, {}).get(system, "--")) for judge in judges]
    differ = len({v for v in values if v != "--"}) > 1
    css = " class='differ'" if differ else ""
    return f"<td{css}>{_pair(values)}</td>"


def _band_unresolved(tracks: list[str]) -> str:
    """The one warn box saying how far a band boundary can be trusted.

    Per track and judge, because the models it moves are not the same ones
    twice. Nothing is claimed when a payload was written before this was
    measured: a table with no `unresolved` key is not a table where nothing
    moves.
    """
    data = _payload("czech-variance.json").get("bands") or {}
    named, jitter = [], 0.0
    for track in tracks:
        for judge_model, grouped in sorted((data.get(track) or {}).items()):
            if not grouped.get("unresolved"):
                continue
            jitter = max(jitter, grouped.get("jitter") or 0.0)
            named.append(
                f"{_t(TRACK_SWITCH_LABELS.get(track, track))} / {judge_model}: "
                + _join_words(sorted(grouped["unresolved"]))
            )
    if not named:
        return ""
    return (
        "<div class='warn'><p>"
        + html.escape(_t(BAND_UNRESOLVED).format(jitter=f"{jitter:.2f}"))
        + f" {html.escape('; '.join(named))}.</p></div>"
    )


def _band_agreement(tracks: list[str]) -> tuple[int, int]:
    """Over every table that draws bands: how many models the judges place apart.

    Returns `(differ, total)` -- how many of the models these tables place are
    given different bands by the two judges in at least one table, out of how
    many are placed by both judges everywhere they appear.

    Counted per model rather than per cell, because that is the question a
    reader has: not "how often do the two judges differ" but "is the band I am
    reading about this model one both of them gave it". A model one judge could
    not place at all -- it wrote nothing that judge could band -- is counted in
    neither figure and left out of the total, because a band nobody gave it is
    not a band the two judges agreed or disagreed about.
    """
    placed: dict[str, list[bool]] = {}
    unplaced: set[str] = set()
    for track in tracks:
        numbers = _band_numbers(track)
        judges = sorted(numbers)
        if len(judges) < 2:
            continue
        for system in set().union(*(set(numbers[judge]) for judge in judges)):
            found = [numbers[judge].get(system) for judge in judges]
            if any(band is None for band in found):
                unplaced.add(system)
                continue
            placed.setdefault(system, []).append(len(set(found)) == 1)
    agreed = {system: seen for system, seen in placed.items() if system not in unplaced}
    return sum(1 for seen in agreed.values() if not all(seen)), len(agreed)


#: Who the rows are, above every one of the score tables. Ten words, and they
#: are not decoration: the person this document was written for read the model
#: column as the list of people whose sessions these were, and came away
#: believing a model had generated the transcripts. The heading names a corpus,
#: the first column names models, and nothing between them said which was
#: which. It is repeated over each table rather than said once with the rest of
#: the caption, because it is the sentence that stops a misreading of the table
#: directly under it.
ROWS_ARE_MODELS = (
    "Each row is one language model. People wrote and transcribed the sessions; the "
    "models wrote the notes from them."
)

#: How a scale line is attached to the instrument it describes when more than
#: one instrument is on the page. Not put through `_t`: it is punctuation
#: joining two already-translated halves, and an em dash is an em dash in both
#: languages. A colon would do the same job and the scale line contains one.
SCALE_OF = "{names} — {line}"


def _how_to_read(tracks: list[str], judges: list[str], *, banded: bool) -> str:
    """The half of the table caption that is the same under all of them.

    Three things used to be printed under every score table: how the two judges
    share a cell, what the notes column counts, and what range the numbers are
    on. Six tables, six copies, six hundred words -- and a reader who learns
    that the caption is the same one they already read stops reading captions,
    including the per-table line below each table that says the rows are
    ordered by dominance and neighbours may not be compared.

    So the invariant half is said once, here, above the tables it governs. What
    stays with each table is what differs between them: how many places that
    table's models fall into, and which columns put it in that order.

    `judges` is empty when no table holds two of them, and then the sentence
    about the two-judge cell is not printed -- it would be describing a layout
    that is not on the page. `banded` says the same about the Band column,
    which is drawn only where `local/czech-variance.json` has been built.
    """
    said = []
    if judges:
        said.append(_t(MERGED_LEAD).format(judges=_join_words(judges)))
    said.append(_t(NOTES_COLUMN))
    # Two sentences, because the second is the one that has to be there: a
    # column that is 0 for most rows is read as a score unless it is told
    # not to be.
    said.append(_t(BEATS_COLUMN))
    said.append(_t(BEATS_COLUMN_ZERO))
    # One line per scale actually drawn, named by the instrument it belongs to.
    # The criteria tables are all shares from 0 to 1 and the PDSQI tables mix a
    # Likert range with one share, so a single sentence covering both would
    # have to be vaguer than either of them is.
    by_line: dict[str, list[str]] = {}
    for track in tracks:
        # The instrument without its variant, the same name the definition
        # block above uses. Naming the variants here gave "PDSQI-9, without the
        # session and PDSQI-9, with the session" for one scale both of them
        # share, under a heading that had just called the whole thing PDSQI-9.
        name = _t(INSTRUMENT_FAMILY.get(track, TRACK_TITLES.get(track, track)))
        by_line.setdefault(_scale_line(track), []).append(name)
    for line, names in by_line.items():
        if len(by_line) == 1:
            said.append(line)
            continue
        # The instrument names are written lower case because they are read
        # inside a sentence elsewhere, and here one opens a sentence. Safe to
        # recase, unlike a model id: `deepseek-v4-flash` is deployed under that
        # spelling and does not become `Deepseek-v4-flash` after a full stop.
        label = _join_words(list(dict.fromkeys(names)))
        said.append(SCALE_OF.format(names=label[:1].upper() + label[1:], line=line))
    if banded:
        said.append(_t(BAND_COLUMN))
        if judges:
            said.append(_t(BAND_TWO_JUDGES))
    return f"<p class='sub'>{html.escape(' '.join(said))}</p>"


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
    judges = [rows[0].judge_model or "?"]
    numbers = _band_numbers(track)
    banded = _banded(numbers, judges, [row.system_id for row in rows])
    head = (
        f"<th>{_t('Order')}</th>"
        + (f"<th>{_t('Band')}</th>" if banded else "")
        + "".join(f"<th>{html.escape(_t(measures[key]['label']))}</th>" for key, _ in columns)
    )
    body, thin = [], []
    for row in sorted(rows, key=lambda r: (-_rank_of(track, r, varying), r.system_id)):
        complete = row.n_sessions_scored - row.n_sessions_partial
        index = _rank_of(track, row, varying)
        band = _band_cell(numbers, judges, row.system_id) if banded else ""
        cells = f"<td><strong>{index:.2f}</strong></td>{band}" + "".join(
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
        f"<p class='sub'>{html.escape(_t(ROWS_ARE_MODELS))} "
        f"{html.escape(_sort_line(track, varying))}</p>"
        + f"<table><thead><tr><th>{_t('Model')}</th>"
        f"<th>{_t('Notes in the mean')}</th>"
        f"{head}</tr></thead><tbody>{''.join(body)}</tbody></table>{warning}"
    )


def _definitions(track: str) -> str:
    """What each column of one instrument means.

    No scale line at the top any more: `_how_to_read` prints it above the
    tables, once per instrument on the page, and printing it here as well put
    the same sentence twice on one screen.
    """
    measures = MEASURE_TABLES[track]
    items = []
    for key, _digits in COLUMNS[track]:
        measure = measures[key]
        items.append(
            f"<dt>{html.escape(_t(measure['label']))}</dt>"
            f"<dd>{html.escape(_trim(_t(measure['definition'])))}</dd>"
        )
    return "<dl>" + "".join(items) + "</dl>"


#: The instrument a track's columns belong to, with the variant dropped. Two
#: tables whose columns are one a subset of the other are one instrument asked
#: twice, so they share a definition list and what separates them is written
#: under it rather than being left for a reader to find by counting columns.
INSTRUMENT_FAMILY = {
    **dict.fromkeys(SOAP_CRITERIA_TRACKS + DEEPSY_CRITERIA_TRACKS, "the six Czech criteria"),
    results.TRACK_CZECH_REAL_PDSQI: "PDSQI-9",
    results.TRACK_CZECH_TRANSLATED_PDSQI: "PDSQI-9",
    results.TRACK_DEEPSY_REAL_PDSQI: "PDSQI-9",
    results.TRACK_DEEPSY_TRANSLATED_PDSQI: "PDSQI-9",
}

#: Why the real-session PDSQI table is short of two columns, said where the
#: columns are defined.
#:
#: **It is an absence with a reason and it is written as one.** Read as "the
#: other table also asks about accuracy" it becomes the shape `CLAUDE.md`
#: rules out: a gap smoothed into a difference of emphasis. The judge cannot
#: answer whether a note is accurate or thorough without reading the session
#: beside it, a real session is confidential and never leaves for a judge's
#: provider, and so the question was never put. There is no number there --
#: not a low one, and nothing about those two columns is a verdict on any note.
ABSENT_NO_TRANSCRIPT = (
    "One difference between the PDSQI tables, and it is an absence with a reason. Some "
    "of these attributes cannot be answered from the note alone: the judge has to read "
    "the session beside it. A real session is confidential and never leaves for a "
    "judge's provider, while the AnnoMI conversations are published under CC-BY and can "
    "be sent -- so on the real sessions those questions were never put. What is missing "
    "there is the question and not an answer a note did badly on, and the columns are "
    "absent rather than low: {columns}."
)
#: The same shape where nothing here records the reason. The gap is still
#: named: a reader who counts the columns will find it, and the conclusion to
#: head off is that a note scored badly on the one that is not there.
ABSENT_UNEXPLAINED = (
    "These columns are absent from one of these tables and this document does not "
    "record why. An absent column is a question that was not put, never a note that "
    "answered it badly: {columns}."
)
#: Which table lacks a column its instrument names, and why. Keyed on the
#: table, because the reason is a fact about the corpus rather than about the
#: instrument and cannot be derived from the columns.
ABSENT_BECAUSE = {
    results.TRACK_CZECH_REAL_PDSQI: ABSENT_NO_TRANSCRIPT,
    results.TRACK_DEEPSY_REAL_PDSQI: ABSENT_NO_TRANSCRIPT,
}


def _column_blocks(tracks: list[str]) -> list[tuple[str, str, list[str]]]:
    """One definition block per instrument: its name, the table with the fullest
    column list, and every table the block covers.

    Six tables drew three lists between them and two of the three were the same
    seven definitions with two added. What a reader needed was not the list
    twice; it was the difference, which nothing said.
    """
    by_family: dict[str, list[str]] = {}
    for track in tracks:
        by_family.setdefault(INSTRUMENT_FAMILY.get(track, track), []).append(track)

    blocks: list[tuple[str, str, list[str]]] = []
    for family, members in by_family.items():
        keys = {track: {key for key, _ in COLUMNS[track]} for track in members}
        widest = max(members, key=lambda track: len(keys[track]))
        # Folded only where the tables really are one instrument asked twice.
        # Two that share a name and disagree about a column are two
        # instruments, and describing one as the other minus something would
        # be false of both.
        if all(keys[track] <= keys[widest] for track in members):
            blocks.append((family, widest, members))
            continue
        drawn: list[str] = []
        for track in members:
            if not any(keys[track] == keys[other] for other in drawn):
                drawn.append(track)
                blocks.append((family, track, [track]))
    return blocks


def _column_definitions(tracks: list[str]) -> str:
    """The column definitions, above the tables they explain rather than below.

    They used to sit under all six tables, which is where a reader arrives
    after having already read a grid of decimals whose column headings meant
    nothing to them. Written open, always: a closed `<details>` prints to PDF
    as a bare heading with its contents gone.
    """
    out = []
    for family, widest, members in _column_blocks(tracks):
        body = _definitions(widest)
        full = [key for key, _ in COLUMNS[widest]]
        for track in members:
            here = {key for key, _ in COLUMNS[track]}
            missing = [key for key in full if key not in here]
            if not missing:
                continue
            labels = _join_words([_t(MEASURE_TABLES[widest][key]["label"]) for key in missing])
            body += (
                "<p>"
                + html.escape(
                    _t(ABSENT_BECAUSE.get(track, ABSENT_UNEXPLAINED)).format(columns=labels)
                )
                + "</p>"
            )
        out.append(
            f"<details open><summary>{html.escape(_t('What each column is'))} &mdash; "
            f"{html.escape(_t(family))}</summary>{body}</details>"
        )
    return "".join(out)


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
    "positive under BOTH judges are {positive}. The chart below says the same thing "
    "without the coefficients. Each dot is one model: its median note length across "
    "the bottom, the six criteria averaged up the side, one panel for each half of "
    "the corpus. The two judges are drawn in separate colours and never averaged, so "
    "a model they disagree about appears as two dots at different heights instead of "
    "as one number somewhere between them. The dashed line is the straight line that "
    "best fits one judge's dots -- drawn rather than described, because a slope is "
    "easier to argue with when the points it was fitted to are on the page beside it."
)

#: What to look at in the chart, said under the chart. The picture carries its
#: own title, subtitle and source line, so the caption says the one thing they
#: do not.
LENGTH_FIGURE_CAPTION = (
    "Two panels, one for each half of the corpus, and one colour for each judge. The "
    "thing to look at is whether the two dashed lines in a panel fall the same way: a "
    "slope one judge sees and the other does not would be a fact about that judge "
    "rather than about length."
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
    "The same test in the Deepsy format comes out {hit} of its {total} table-and-judge "
    "combinations, and the "
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
#:
#: **And no judge-against-judge figure either, for a worse reason.** Five of
#: those were written here too -- "the same way on 79% of notes", "differently
#: on a quarter", "67%, the lowest of the six" -- and every one of them was
#: measured under `czech-criteria-v1` while the tables above the paragraph draw
#: `czech-criteria-v2`. Under the rubric actually drawn, diacritics is 83% and
#: not 79%, register 70% and not 75%, the judges differ on a third of the
#: agreement notes and not a quarter. All five are appended from the payload now,
#: and the payload carries the rubric it was measured under so the pairing cannot
#: come apart again.
#:
#: **Two of the five were right, and the sentence deleted with them was true.**
#: This comment used to say that calque's 67% was "a tie with agreement rather
#: than the lowest of anything". It is not: under `czech-criteria-v2` calque is
#: 68/102 and agreement 71/104, which is 66.7% against 68.3% -- 1.6 points apart,
#: and the document prints them as 67 and 68. Calque is the lowest of the six.
#: `untranslated`'s typed 87% also survives v2, which reads 86.5%. So three of
#: the five figures were wrong under the drawn rubric and two were not, and
#: whether those two were *measured* under v1 cannot be told from a number that
#: both rubrics produce. Reading the correction back off the data is the check
#: the correction itself skipped.
#:
#: The ranking is therefore back, and computed rather than typed -- which is what
#: the rest of this change was for.
#:
#: What is left here is the half a computation cannot supply, and only where
#: there is one. Two criteria have no entry: everything the document had to say
#: about diacritics was the figure, and everything it had to say about non-words
#: was a hand-typed ranking of the rater figures `_rater` prints properly.
#:
#: **One entry per Czech criterion and nothing else.** `_catch` is asked only
#: about `czech.CRITERION_KEYS`, so a key outside them is prose no reader can
#: reach -- and it is worse than dead code, because the reachability check in
#: `tests/test_czech_dictionary.py` is textual: an English sentence sitting
#: here keeps its Czech twin alive and current-looking in `czech_brief_cs.py`
#: long after the chapter that printed it was deleted. Nine PDSQI entries did
#: exactly that, carrying nine Czech translations of claims about a table this
#: dictionary no longer describes.
WHAT_IT_CATCHES = {
    "calque": (
        "Read this column as a flag rather than as a score. Whether a Czech phrase "
        "is a literal translation from English is a judgement people make "
        "differently, and the count below shows that rather than hiding it."
    ),
    "untranslated": (
        "The fault it catches is unambiguous: an English term left sitting in a Czech sentence."
    ),
    "agreement": ("Catches real grammatical faults."),
    "register": ("Catches colloquial words where clinical ones belong."),
}


#: The one track these hand-written verdicts and the rater figure were measured
#: on. Everything in `WHAT_IT_CATCHES` about how often the judges agree, and
#: every number in `local/czech-anchor.json`, comes from the ten real Czech
#: sessions scored by the criteria. Printed under the PDSQI and Deepsy tables it
#: said something measured elsewhere about a table it was not measured on -- on
#: the Deepsy notes `untranslated` agrees on 63% and was being described as 87%
#: and "reliable", which inverts the row's verdict.
ANCHORED_ON = results.TRACK_CZECH_REAL


def _catch(key: str, track: str) -> str:
    """What a column catches, in this run's language, or nothing.

    **Only under the track it was measured on.** These sentences quote judge
    agreement and a native speaker's; both were measured on the real Czech
    sessions under the criteria rubric, and nobody has rated a Deepsy note or a
    translated one by hand at all. Importing them would be reporting one
    table's number under another's heading -- on the Deepsy notes `untranslated`
    agrees on 63% and was being described as 87% and "reliable".

    **Empty rather than "not measured on this track".** That filler was written
    for a table cell, where a blank says neither "measured and unremarkable"
    nor "never measured" and something had to fill thirty-six of them. In a
    paragraph the sentence simply is not there, and the paragraph reads as a
    paragraph with one fewer sentence rather than as one ending in a shrug.
    The gap is named where a reader meets it: the lead above these paragraphs
    says what the agreement figures were measured on and where they were not
    measured at all. There is no longer a table of them anywhere -- these six
    sentences are the only place the anchor appears.

    **The written half no longer gates the measured ones.** It did, and two
    criteria then had to keep a hand-written sentence in order to be allowed to
    print their own measurements. Each of the three parts is now asked for
    separately and prints if it has something to say.
    """
    if track != ANCHORED_ON:
        return ""
    written = WHAT_IT_CATCHES.get(key, "")
    parts = [_t(written) if written else "", _judges_agree(key), _rater(key)]
    return " ".join(part for part in parts if part).strip()


#: How often the two judges said the same thing about one criterion, from
#: `local/czech-anchor.json`. The unanswered notes are named beside the rate
#: instead of being folded into it: a note only one judge answered is a call
#: the endpoint refused, and charging it to the judges as a disagreement is the
#: shape this repository has met over and over.
JUDGES_AGREE = (
    "The two judges answered the same way on {agreed} of the {compared} notes both of "
    "them answered, {rate}% of them."
)
#: Written so the count is never the subject of the sentence. "A further 1 were
#: answered" and its Czech equivalent both need a different word for one, two
#: and five, and the number here is a placeholder that will be any of them.
JUDGES_AGREE_GAP = (
    "Notes only one of the two answered are left out of that count rather than counted "
    "against it: {unanswered} of them."
)
#: When the payload was measured under a rubric these tables do not draw. The
#: figure is dropped and the mismatch is named, because the alternative is what
#: this document did for a whole rebuild: print `czech-criteria-v1` agreement
#: beside `czech-criteria-v2` levels, in the same sentence, with nothing saying
#: they were two different instruments.
JUDGES_AGREE_STALE = (
    "How often the two judges answered the same way is not printed here: the answers "
    "on disk were counted under {measured} and these tables draw {drawn}. Re-run "
    "tools/czech_anchor.py."
)


#: Appended to the agreement sentence of whichever criterion the judges agree
#: about least, when one of them is alone at the bottom.
JUDGES_AGREE_LOWEST = "That is the lowest of the six."


def _judges_agree(key: str) -> str:
    """How often the two judges said the same thing, or why it is not printed.

    Read from the payload rather than written into `WHAT_IT_CATCHES`, and read
    with its rubric, because the rubric is half of what the figure means. The
    five that were written here were all `czech-criteria-v1` figures standing
    beside `czech-criteria-v2` levels, in the same sentence, and nothing in the
    document could have noticed: an agreement rate carries no mark saying which
    instrument produced it.

    Silent when there is no payload -- a checkout without `local/` draws the
    chapter without this sentence -- and loud when there is one measured under
    another rubric, which is the case a silence would hide.
    """
    between = _payload("czech-anchor.json").get("between_judges") or {}
    if not between:
        return ""
    if between.get("rubric") != czech_scorer.JUDGE_PROMPT_VERSION:
        return _t(JUDGES_AGREE_STALE).format(
            measured=between.get("rubric") or "?", drawn=czech_scorer.JUDGE_PROMPT_VERSION
        )
    found = (between.get("criteria") or {}).get(key) or {}
    if not found.get("compared"):
        return ""
    said = _t(JUDGES_AGREE).format(
        agreed=found["agreed"],
        compared=found["compared"],
        rate=_decimal(100 * found["agreed"] / found["compared"], 0),
    )
    if found.get("unanswered"):
        said += " " + _t(JUDGES_AGREE_GAP).format(unanswered=found["unanswered"])
    if _is_lowest(key, between):
        said += " " + _t(JUDGES_AGREE_LOWEST)
    return said


def _is_lowest(key: str, between: dict) -> bool:
    """Whether this criterion is the one the two judges agree about least.

    Computed, not typed. A hand-written "the lowest of the six" is a claim about
    every other column, and it was hand-written once and then deleted on the
    grounds that it was a tie -- which the same payload refutes: the two lowest
    are 1.6 points apart and the document prints them as different integers.
    A ranking that is derived cannot drift from the numbers printed beside it.

    Ties return False for every member. Where two columns genuinely cannot be
    ordered, naming either of them the lowest would be the invention this exists
    to prevent.
    """
    rates = {
        name: found["agreed"] / found["compared"]
        for name, found in (between.get("criteria") or {}).items()
        if found.get("compared")
    }
    if len(rates) < 2 or key not in rates:
        return False
    ordered = sorted(rates.values())
    return rates[key] == ordered[0] and ordered[0] < ordered[1]


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


#: What the corpora are, above the table that counts them. A reader who has
#: never seen this project meets a column of model names first, and this is the
#: paragraph that says what those models were given. The one claim in it that
#: the whole comparison rests on is the first: every model was asked for a note
#: from every transcript, so no two models are ever being compared on different
#: sessions.
CORPORA_LEAD = (
    "Every model was asked for a note from every one of these transcripts, in both "
    "halves, so no two models are ever compared on sessions of different difficulty. "
    "One half is recordings of real therapy with a single client, transcribed and "
    "de-identified by hand and never released. The other is public counselling "
    "conversations from the AnnoMI corpus, translated into spoken Czech for this track."
)
#: Who translated the half that was translated, and what that does and does
#: not contaminate. It was recorded in one handoff file and in no document
#: anybody outside this repository would ever read, and it bears directly on
#: the one claim this whole track exists to make.
#:
#: **Both halves of it, or neither.** Comparing the models with each other the
#: translation cancels, because every model read the same translated text.
#: The absolute claim -- "these models write bad Czech" -- it does not touch,
#: because a clumsiness the translation put into the transcript can come back
#: out of the note. Saying only the first is an excuse; saying only the second
#: is a reason to throw the half away, and it is neither.
TRANSLATION_CANCELS = (
    "The same translated text went to every model, and that matters in two opposite "
    "ways. Comparing the models with each other, the translation cancels: whatever it "
    "did to the Czech, it did equally to all of them, so a difference between two "
    "models on this half is still a difference between the models. For an absolute "
    'claim -- "these models write bad Czech" -- it does not cancel at all, because '
    "clumsiness the translation put into a transcript can come back out of the note "
    "written from it. That is what the real half is for: a fault that shows on both "
    "halves is the model's, and one that shows only on the translated half is the "
    "input's."
)
#: The version printed while the translator is outside every family on the
#: tables. Which families those are is discovered at run time and never typed
#: here, so the claim is checked against the rows rather than asserted.
TRANSLATED_BY_OUTSIDER = (
    "The translating was done by Claude, which is itself a language model, and anyone "
    "reading these numbers should know that before they read them. It was picked for "
    "being an outsider: no model in any table here, and neither judge, belongs to the "
    "family that wrote this Czech, so nothing is being marked on prose its own "
    "relatives produced."
)
#: And the version printed when that stops being true. Not silence: the reader
#: who was told the translator is an outsider is the reader who has to be told
#: when it is not.
TRANSLATED_BY_INSIDER = (
    "The translating was done by Claude, which is itself a language model, and anyone "
    "reading these numbers should know that before they read them. It was picked for "
    "being an outsider, and that no longer holds: a model from the same family is in "
    "the tables below, so on this half it is being scored on Czech its own family "
    "wrote. Read its translated column against its real-session column rather than on "
    "its own."
)
#: The translator's family, matched against the model ids and judge names the
#: tables actually draw. A substring rather than a list of ids, because ids are
#: discovered at run time and a list typed here would go stale silently.
TRANSLATOR_FAMILY = "claude"

#: The size difference, with the multiple computed from the same medians the
#: table prints. It was a typed "seven times" in the method section, three
#: screens away from the two medians it is the ratio of.
CORPORA_SIZE = (
    "The two halves are nothing like the same size: by the median word count a real "
    "session runs about {ratio} times as long as a translated conversation. The longer "
    "half is a harder summarising task before any question of Czech arises, so every "
    "comparison between the halves in this document is comparing that too."
)


def _translator(drawn: list[results.Row]) -> str:
    """Who translated the AnnoMI half, and whether the choice still holds.

    The translator was picked for being outside every family on the tables, so
    that no model would be marked on Czech its own relatives wrote. Whether
    that is still true is a fact about the rows, not about the sentence: models
    are discovered at run time here, and a paragraph naming the families it
    considered would be one deployment away from being false while still
    reading as a reassurance.
    """
    names = {row.system_id.lower() for row in drawn}
    names |= {(row.judge_model or "").lower() for row in drawn}
    inside = any(TRANSLATOR_FAMILY in name for name in names)
    return (
        f"<p>{html.escape(_t(TRANSLATED_BY_INSIDER if inside else TRANSLATED_BY_OUTSIDER))}</p>"
        f"<p>{html.escape(_t(TRANSLATION_CANCELS))}</p>"
    )


def _corpus(drawn: list[results.Row]) -> str:
    """What the two halves are, counted rather than asserted.

    The sentence this replaces said "ten real sessions ... plus ten AnnoMI
    conversations translated into spoken Czech", which is true and hides the
    thing a reader most needs: **the real sessions are several times longer.**
    Summarising an hour of talk and summarising ten minutes of it are not the
    same task, so any sentence comparing the two halves is comparing that too --
    and the multiple is divided out of the table's own medians rather than
    written into the prose, where it would go stale on the next corpus.

    Counts only -- session totals, medians, ranges. No transcript text reaches
    this document, which `check_no_clinical_text` asserts separately.
    """
    from tnb.tasks import czech as czech_task

    rows, medians = [], []
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
        medians.append(words[middle])
        rows.append(
            f"<tr><td>{html.escape(_t(label))}</td><td>{len(sessions)}</td>"
            f"<td>{_grouped(words[middle])}</td>"
            f"<td>{_grouped(words[0])}&ndash;{_grouped(words[-1])}</td>"
            f"<td>{turns[middle]}</td>"
            f"<td class='sub'>{html.escape(_t(note))}</td></tr>"
        )
    if not rows:
        return ""
    # Only when both halves loaded and the shorter one is not empty. One half
    # on its own has nothing to be a multiple of, and a ratio printed from one
    # median and a guess is the kind of number this document exists to avoid.
    size = ""
    if len(medians) == 2 and medians[1]:
        size = (
            "<p>"
            + html.escape(_t(CORPORA_SIZE).format(ratio=_decimal(medians[0] / medians[1], 1)))
            + "</p>"
        )
    return (
        f"<details open><summary>{_t('The two corpora')}</summary>"
        f"<p>{html.escape(_t(CORPORA_LEAD))}</p>"
        + _translator(drawn)
        + (
            f"<table><thead><tr><th>{_t('Half')}</th><th>{_t('Sessions')}</th>"
            f"<th>{_t('Words, median')}</th><th>{_t('Words, range')}</th>"
            f"<th>{_t('Turns, median')}</th><th></th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>{size}</details>"
        )
    )


#: The two PDSQI tables, named the way the two criteria pairs above are, and
#: for the same reason: a filter that says what a track is *not* quietly pools
#: whatever is added next.
PDSQI_TRACKS = (results.TRACK_CZECH_REAL_PDSQI, results.TRACK_CZECH_TRANSLATED_PDSQI)
#: The same instrument over the Deepsy notes. Separate from the tuple above
#: rather than added to it: that one labels a chapter `PDSQI-9 on the same
#: SOAP notes` and drives the three-views comparison, and a Deepsy table
#: inside it would make the label false.
DEEPSY_PDSQI_TRACKS = (
    results.TRACK_DEEPSY_REAL_PDSQI,
    results.TRACK_DEEPSY_TRANSLATED_PDSQI,
)


def _cells(rows: list[results.Row], tracks: tuple[str, ...]) -> dict[tuple[str, str], dict]:
    """One cell per track and judge: each column's mean over the models drawn.

    The newest rubric per track, which is what the tables draw. Four cells stay
    four cells: nothing here is averaged across judges or across halves, so the
    only kind of finding these boxes can state is one that holds in all of
    them. A mean of four tables would be a number this document has spent a
    page declining to take.
    """
    latest = [row for row in results.latest(rows) if row.is_scored]
    out: dict[tuple[str, str], dict] = {}
    for track in tracks:
        here = [row for row in latest if row.track == track]
        if not here:
            continue
        newest = max(row.judge_prompt_version for row in here)
        here = [row for row in here if row.judge_prompt_version == newest]
        for judge in sorted({row.judge_model or "" for row in here}):
            found = {}
            for key, _digits in COLUMNS[track]:
                values = [
                    row.metrics.headline[key]
                    for row in here
                    if (row.judge_model or "") == judge and key in row.metrics.headline
                ]
                if values:
                    found[key] = sum(values) / len(values)
            if found:
                out[(track, judge)] = found
    return out


def _extremes(cells: dict, keys: set[str]) -> tuple[list[str], dict[str, list[float]]]:
    """The columns that are lowest in EVERY cell, and every column's values.

    Intersected rather than averaged. A column that is the weakest in three of
    four cells and second weakest in the fourth is not the weakest, and calling
    it that would be taking the mean of four tables in order to report which
    one of them to believe.
    """
    lowest: list[set[str]] = []
    values: dict[str, list[float]] = {}
    for found in cells.values():
        here = {key: value for key, value in found.items() if key in keys}
        if not here:
            continue
        floor = min(here.values())
        lowest.append({key for key, value in here.items() if value == floor})
        for key, value in here.items():
            values.setdefault(key, []).append(value)
    worst = sorted(set.intersection(*lowest)) if lowest else []
    return worst, values


def _at_the_ceiling(rows: list[results.Row], tracks: tuple[str, ...]) -> list[str]:
    """Columns where every model in every one of these tables prints the top.

    Not "the highest column", which every table has whether or not it means
    anything. This is the stronger fact and the one worth a sentence: nobody
    can score below it, so the column separates nothing and never could.
    """
    latest = [row for row in results.latest(rows) if row.is_scored]
    seen: dict[str, set[bool]] = {}
    for track in tracks:
        here = [row for row in latest if row.track == track]
        if not here:
            continue
        newest = max(row.judge_prompt_version for row in here)
        here = [row for row in here if row.judge_prompt_version == newest]
        measures = MEASURE_TABLES[track]
        for judge in sorted({row.judge_model or "" for row in here}):
            for key, digits in COLUMNS[track]:
                top = float(measures[key]["scale"].split("-")[-1])
                printed = {
                    f"{row.metrics.headline[key]:.{digits}f}"
                    for row in here
                    if (row.judge_model or "") == judge and key in row.metrics.headline
                }
                if printed:
                    seen.setdefault(key, set()).add(printed == {f"{top:.{digits}f}"})
    return sorted(key for key, answers in seen.items() if answers == {True})


class Halves(NamedTuple):
    """Which half each column is ahead on, and the three ways it can be neither.

    The three used to be one list under one sentence, and the sentence was the
    split. So a box announced that "the two judges do not both point the same
    way on Synthesized" three lines under its own paragraph saying every model
    scores 5.00 on Synthesized in all four tables: the judges point the same
    way there, at nothing. They are different findings and they read
    differently -- a split says the question is one people answer differently,
    a column flat under both says the halves are the same there, and a column
    flat under one says only that one judge saw something.
    """

    #: Ahead on the second track of the pair, under every judge.
    ahead_other: list[str]
    #: Ahead on the first, under every judge.
    ahead_real: list[str]
    #: One judge says one half, the other says the other.
    split: list[str]
    #: Neither judge sees a difference at all.
    flat_both: list[str]
    #: One judge sees a difference and the other sees none.
    flat_one: list[str]


def _halves_split(cells: dict, tracks: tuple[str, str], keys: list[str]) -> Halves:
    """Which half each column is ahead on, under every judge that read both.

    A difference smaller than the last digit the table prints is not a
    difference a reader can see, and it counts for neither half: two columns of
    5.00 are not the translated half winning by a rounding error. A column the
    judges do not both put on the same side is not put on either, because the
    reading rule everywhere else in this document is to believe what both
    judges say -- but which way it failed is a fact of its own, so the three
    ways are kept apart rather than swept into one list.

    A genuine split wins over a flat judge when both are present: two judges
    pointing opposite ways is the stronger fact, and it is the one this
    document reports.
    """
    real_track, other_track = tracks
    judges = sorted(
        {judge for track, judge in cells if track == real_track}
        & {judge for track, judge in cells if track == other_track}
    )
    digits = dict(COLUMNS[real_track])
    found = Halves([], [], [], [], [])
    for key in keys:
        signs = []
        for judge in judges:
            here = cells[(real_track, judge)].get(key)
            there = cells[(other_track, judge)].get(key)
            if here is None or there is None:
                signs = []
                break
            step = 0.5 * 10 ** -digits.get(key, 2)
            signs.append(0 if abs(there - here) < step else (1 if there > here else -1))
        if not signs:
            continue
        if all(sign > 0 for sign in signs):
            found.ahead_other.append(key)
        elif all(sign < 0 for sign in signs):
            found.ahead_real.append(key)
        elif any(sign > 0 for sign in signs) and any(sign < 0 for sign in signs):
            found.split.append(key)
        elif all(sign == 0 for sign in signs):
            found.flat_both.append(key)
        else:
            found.flat_one.append(key)
    return found


def _shared_keys(tracks: tuple[str, str]) -> list[str]:
    """The columns both halves of a chapter have, in the first half's order."""
    other = {key for key, _digits in COLUMNS[tracks[1]]}
    return [key for key, _digits in COLUMNS[tracks[0]] if key in other]


def _labels(track: str, keys: list[str]) -> str:
    """Column names, in the reader's language, joined the way a sentence needs."""
    return _join_words([_t(MEASURE_TABLES[track][key]["label"]) for key in keys])


def _halves_rest(track: str, halves: Halves) -> list[str]:
    """The columns that landed on neither half, each under the sentence it earns.

    In a fixed order, worst first: a genuine split between the judges is a
    finding, one judge seeing what the other does not is weaker, and both
    judges seeing nothing is not a disagreement at all. Each sentence prints
    only where there is a column for it, so a chapter whose columns all landed
    on one half or the other says nothing here rather than three empty
    sentences.
    """
    return [
        _t(sentence).format(names=_labels(track, keys))
        for sentence, keys in (
            (HALVES_REST, halves.split),
            (HALVES_FLAT_ONE, halves.flat_one),
            (HALVES_FLAT_BOTH, halves.flat_both),
        )
        if keys
    ]


def _rosters(rows: list[results.Row], tracks: tuple[str, ...]) -> set[str]:
    """Every model these tracks drew, on the rubric each of them draws."""
    latest = [row for row in results.latest(rows) if row.is_scored]
    found: set[str] = set()
    for track in tracks:
        here = [row for row in latest if row.track == track]
        if not here:
            continue
        newest = max(row.judge_prompt_version for row in here)
        found |= {row.system_id for row in here if row.judge_prompt_version == newest}
    return found


def _box(title: str, said: list[str], *, kind: str = "finding", level: int = 3) -> str:
    """A chapter's closing box, in the same shape each time it closes one.

    The document had no place where a chapter said what it came to. It had a
    summary at the front and thirty tables after it, and the reader who worked
    through two tables of decimals was handed a third with nothing in between
    saying what the first two had shown. A box at the end of each chapter is
    that sentence, and it is the same shape in all three so that a reader who
    learns to look for it once finds it again.

    `kind` and `level` are how the box that closes the whole document uses the
    same shape as the three that close a chapter: a different tint, and a
    heading at the weight of the summary on the front page rather than of a
    section inside a chapter. It closes nothing smaller than the document, so
    it should not look like it does.
    """
    body = "".join(f"<p>{html.escape(text)}</p>" for text in said if text)
    if not body:
        return ""
    return f"<div class='{kind}'><h{level}>{html.escape(_t(title))}</h{level}>{body}</div>"


#: Said in every box that compares two halves, because the disagreement is the
#: same kind of fact each time: a column the two judges push in opposite
#: directions has no answer between the halves, and averaging over it would
#: manufacture one.
#:
#: **Three sentences where there was one.** This one was printed over every
#: column that landed on neither half, and two of the three ways that happens
#: are not a disagreement at all. It told a reader that the judges did not both
#: point the same way on Synthesized, three lines under the same box saying
#: every model scores 5.00 on Synthesized in every one of these tables.
HALVES_REST = (
    "The two judges point opposite ways on {names}, so between the halves there is no "
    "answer there at all."
)
#: A column both judges read as the same on both halves. Not a disagreement and
#: not a result about either half: it is the halves being indistinguishable
#: there, to the last digit the tables print.
HALVES_FLAT_BOTH = (
    "Neither judge sees any difference between the halves on {names}: to the last digit "
    "these tables print, the two halves are the same there."
)
#: And the third way. One judge saw a difference and the other saw none, which
#: is weaker than a split -- nobody contradicted anybody -- and still not an
#: answer, because one judge alone is not what this document reads.
HALVES_FLAT_ONE = (
    "On {names} one judge sees a difference between the halves and the other sees none, "
    "so there is nothing there that both of them say."
)
#: The confound, said under both criteria chapters. It is the same confound,
#: it is not a small one, and a box that printed the comparison without it
#: would be handing a clinical team the one sentence they would remember.
HALVES_GUARD = (
    "It does not follow that the models write better Czech on either half. The two "
    "differ in size, in topic and in who transcribed them, so a model that does worse "
    "on one may be doing worse at length, at motivational interviewing or at Czech, "
    "and nothing measured here separates the three."
)
#: When the tables do not agree on which column is weakest. It has never
#: printed on the data this document was built from, and it is written and
#: translated anyway: the alternative is a silence that reads as agreement.
WORST_UNSETTLED = (
    "Which fault survives most often is not the same in all {tables} table-and-judge "
    "combinations, so none is named here: the weakest column changes with the table "
    "and with the judge."
)

BOX_A_TITLE = "What these two tables come to"
BOX_A_WORST = (
    "One fault survives more often than any other, and it is the same one in all "
    "{tables} table-and-judge combinations -- both halves, both judges. It is "
    "{worst}: averaged over the models, between {low} and {high} of the notes are free "
    "of it, where 1.00 "
    "would mean every note was clean and 0.00 that none was."
)
BOX_A_HALVES = (
    "Between the two halves, the translated conversations come out ahead on {other} of "
    "the {total} criteria under both judges, and the real sessions on {real}."
)

BOX_B_TITLE = "What the two quality tables come to"
BOX_B_CEILING = (
    "In all {tables} table-and-judge combinations, every model scores {value} on "
    "{names} -- the top of the scale. That is a ceiling rather than a result: an "
    "attribute no model can fail cannot tell the models apart, and it should not be "
    "read as one they all did well on."
)
BOX_B_WORST = (
    "The attribute every model does worst on is {worst}, in all {tables} "
    "table-and-judge combinations: {low} to {high} out of 5, averaged over the models "
    "in each of them."
)
BOX_B_WORST_UNSETTLED = (
    "These {tables} table-and-judge combinations do not agree on which attribute the "
    "models do worst on, so none is named here."
)
BOX_B_HALVES = (
    "Between the two halves, on the {total} attributes both of them were asked: the "
    "translated conversations come out ahead on {other} under both judges, and the "
    "real sessions on {real}."
)
BOX_B_ABSENT = (
    "Two attributes are missing from the real half rather than low. {names} can only "
    "be answered by reading the session, and a real session is never sent to a judge, "
    "so there is no number rather than a poor one. Nothing about the notes is being "
    "left out."
)

BOX_C_TITLE = "What the two Deepsy tables come to"
BOX_C_WORST_SAME = (
    "The fault that survives most often in the Deepsy notes is {worst}, with between "
    "{low} and {high} of them free of it. It is the same fault that survives most "
    "often in the SOAP notes above, so what these models get wrong in Czech is not a "
    "fact about the format they were asked for."
)
BOX_C_WORST_OTHER = (
    "The fault that survives most often in the Deepsy notes is {worst}, with between "
    "{low} and {high} of them free of it. In the SOAP notes above it is {soap} "
    "instead, so what a model gets wrong changes with the shape it was asked for."
)
BOX_C_HALVES = (
    "Between the two halves of the Deepsy notes, the translated conversations come out "
    "ahead on {other} of the {total} criteria under both judges, and the real sessions "
    "on {real}."
)
BOX_C_WORST_UNSETTLED = (
    "No single fault dominates the Deepsy notes the way {soap} does the SOAP ones. "
    "Which column is weakest changes with the table and with the judge, so none "
    "is named here."
)
BOX_C_GUARD = (
    "That comparison carries the same confound as the one on the SOAP halves: the two "
    "halves differ in size, in topic and in who transcribed them, and nothing measured "
    "here separates any of the three from Czech."
)
BOX_C_ROSTER = (
    "One thing to carry into any comparison with the tables above: these two tables "
    "hold {here} models and the SOAP tables hold {there}, because what e-INFRA had "
    "deployed changed between the two runs. Anything read across the two formats holds "
    "for the {shared} models they share, and for those only."
)


def _worst_sentences(rows: list[results.Row], tracks: tuple[str, ...], keys: set[str]) -> tuple:
    """The weakest column of a chapter, its range, and how many cells agree.

    Returns `(worst, low, high, tables)` with `worst` empty when the cells do
    not agree on one -- which is a finding of its own and gets its own sentence
    rather than a silence.
    """
    cells = _cells(rows, tracks)
    if not cells:
        return "", "", "", 0
    worst, values = _extremes(cells, keys)
    if len(worst) != 1:
        return "", "", "", len(cells)
    key = worst[0]
    digits = dict(COLUMNS[tracks[0]]).get(key, 2)
    found = sorted(values[key])
    label = _t(MEASURE_TABLES[tracks[0]][key]["label"])
    return label, _decimal(found[0], digits), _decimal(found[-1], digits), len(cells)


def _box_a(rows: list[results.Row]) -> str:
    """What the two Czech criteria tables came to, computed from them.

    It absorbs the chapter this document used to end on -- "Real sessions or
    translated ones?" -- whose lead paragraph typed out "four of the six
    criteria under both judges" and "each judge alone gives it five, but not
    the same five" over a table that computed exactly those numbers and could
    have said them. That shape is the one this repository keeps finding, and
    finding it in its own briefing was overdue.
    """
    tracks = SOAP_CRITERIA_TRACKS
    cells = _cells(rows, tracks)
    if not cells:
        return ""
    said = []

    keys = _shared_keys(tracks)
    worst, low, high, tables = _worst_sentences(rows, tracks, set(keys))
    if worst:
        said.append(_t(BOX_A_WORST).format(tables=tables, worst=worst, low=low, high=high))
    else:
        said.append(_t(WORST_UNSETTLED).format(tables=tables))

    halves = _halves_split(cells, tracks, keys)
    said.append(
        _t(BOX_A_HALVES).format(
            other=len(halves.ahead_other), total=len(keys), real=len(halves.ahead_real)
        )
    )
    said += _halves_rest(tracks[0], halves)
    said.append(_t(HALVES_GUARD))
    return _box(BOX_A_TITLE, said)


def _box_b(rows: list[results.Row]) -> str:
    """What the two quality tables came to. The ceiling is the finding."""
    tracks = PDSQI_TRACKS
    cells = _cells(rows, tracks)
    if not cells:
        return ""
    said = []

    measures = MEASURE_TABLES[tracks[0]]
    likert = {key for key, _digits in COLUMNS[tracks[0]] if measures[key]["scale"] == "1-5"}
    likert |= {
        key
        for key, _digits in COLUMNS[tracks[1]]
        if MEASURE_TABLES[tracks[1]][key]["scale"] == "1-5"
    }

    ceiling = _at_the_ceiling(rows, tracks)
    if ceiling:
        track = tracks[0] if ceiling[0] in dict(COLUMNS[tracks[0]]) else tracks[1]
        digits = dict(COLUMNS[track])[ceiling[0]]
        top = float(MEASURE_TABLES[track][ceiling[0]]["scale"].split("-")[-1])
        said.append(
            _t(BOX_B_CEILING).format(
                tables=len(cells),
                value=_decimal(top, digits),
                names=_labels(track, ceiling),
            )
        )

    worst, low, high, tables = _worst_sentences(rows, tracks, likert)
    if worst:
        said.append(_t(BOX_B_WORST).format(tables=tables, worst=worst, low=low, high=high))
    else:
        said.append(_t(BOX_B_WORST_UNSETTLED).format(tables=tables))

    keys = _shared_keys(tracks)
    halves = _halves_split(cells, tracks, keys)
    said.append(
        _t(BOX_B_HALVES).format(
            other=len(halves.ahead_other), total=len(keys), real=len(halves.ahead_real)
        )
    )
    said += _halves_rest(tracks[0], halves)

    # The columns the real half was never asked, named as an absence with its
    # reason. A reader comparing a six-column table with an eight-column one
    # reads the two missing columns as something the notes failed at.
    only_other = [key for key, _digits in COLUMNS[tracks[1]] if key not in set(keys)]
    if only_other:
        said.append(_t(BOX_B_ABSENT).format(names=_labels(tracks[1], only_other)))
    return _box(BOX_B_TITLE, said)


def _box_c(rows: list[results.Row]) -> str:
    """What the two Deepsy tables came to, and what carries across to the SOAP ones."""
    tracks = DEEPSY_CRITERIA_TRACKS
    cells = _cells(rows, tracks)
    if not cells:
        return ""
    said = []

    keys = _shared_keys(tracks)
    worst, low, high, tables = _worst_sentences(rows, tracks, set(keys))
    soap, _low, _high, _tables = _worst_sentences(
        rows, SOAP_CRITERIA_TRACKS, set(_shared_keys(SOAP_CRITERIA_TRACKS))
    )
    if worst and soap == worst:
        said.append(_t(BOX_C_WORST_SAME).format(worst=worst, low=low, high=high))
    elif worst and soap:
        said.append(_t(BOX_C_WORST_OTHER).format(worst=worst, low=low, high=high, soap=soap))
    elif worst:
        said.append(_t(BOX_A_WORST).format(tables=tables, worst=worst, low=low, high=high))
    elif soap:
        said.append(_t(BOX_C_WORST_UNSETTLED).format(soap=soap))
    else:
        said.append(_t(WORST_UNSETTLED).format(tables=tables))

    halves = _halves_split(cells, tracks, keys)
    said.append(
        _t(BOX_C_HALVES).format(
            other=len(halves.ahead_other), total=len(keys), real=len(halves.ahead_real)
        )
    )
    said += _halves_rest(tracks[0], halves)
    said.append(_t(BOX_C_GUARD))

    # The two rosters, because they are not the same roster and the chapter
    # above it is the one a reader will compare these tables with.
    here = _rosters(rows, tracks)
    there = _rosters(rows, SOAP_CRITERIA_TRACKS)
    if here and there:
        said.append(
            _t(BOX_C_ROSTER).format(here=len(here), there=len(there), shared=len(here & there))
        )
    return _box(BOX_C_TITLE, said)


# --- the box that closes the document ---------------------------------------
#: Box D, and it is not a fourth chapter box. The three above say what two
#: tables came to; this says what the whole document comes to for the person
#: who has to act on it, and it is last on purpose. A reader handed fifteen
#: chapters of measurement is owed one page saying what may be done with them.
#: Every figure in it is read from the payloads the chapters were drawn from.
CLOSING_TITLE = "Where this leaves a team choosing a model"

CLOSING_RUN = (
    "Everything above is one run. {models} models -- whichever ones e-INFRA had "
    "deployed the week it was measured -- were asked for {asked} notes, wrote "
    "{written} of them from {sessions} sessions, and every note that came back was "
    "read by both judges. Nothing here is averaged over runs, over judges or over the "
    "two halves. And the list of models is a deployment rather than a field: rebuilt "
    "after the next one, this document would hold different names, and in places a "
    "different model behind the same name."
)

#: How far the Band column can be leant on, counted rather than warned about.
#: The tables mark a cell where the two judges disagree and nothing anywhere
#: says how often that happens, so a reader who saw three marked cells could
#: reasonably think it was three.
CLOSING_BANDS = (
    "The finest distinction that survives both judges is a band and not a place -- and "
    "even the band moves: of the {total} models these tables place, {differ} are put in "
    "different bands by the two judges somewhere. Two models inside one band are two "
    "models this measurement did not tell apart, and two models a band apart under one "
    "judge may be that judge."
)
#: The other outcome, written and translated although this data does not reach
#: it. A silence where the judges agreed everywhere would read as though the
#: count had been left out for being embarrassing.
CLOSING_BANDS_AGREE = (
    "The finest distinction that survives both judges is a band and not a place, and "
    "here the two of them agree: every one of the {total} models these tables place is "
    "put in the same band by both. Two models inside one band are still two models this "
    "measurement did not tell apart."
)

#: What somebody could go and do, which is the half the caveats chapter does
#: not carry: it says what may not be concluded, and this says what would have
#: to be measured for more to be concludable. Each sentence prints only while
#: the gap it names is still a gap.
CLOSING_NEXT = (
    "What would let this document say more is more measuring, and what is missing is "
    "short enough to list."
)
CLOSING_NEXT_CORPUS = (
    "The real half of these {sessions} sessions is one client and one therapist, so "
    "everything measured there is also a fact about how those two people talk; more "
    "sessions, with other clients and other therapists, is what would lift that."
)
CLOSING_NEXT_RATER = (
    "One Czech reader has checked {notes} of these notes by hand, and one reader cannot "
    "say how far two would have agreed -- a second would turn every place where a judge "
    "and he differ into a figure rather than an open question."
)
CLOSING_NEXT_DEEPSY = (
    "And PDSQI-9 has never been put to a note in the Deepsy format: those {deepsy} "
    "notes are already written, so asking would cost no generation at all, and it is "
    "the only way to find out whether the format a clinic would actually use produces "
    "a note worth filing."
)

CLOSING_READING = (
    "Until then, the reading this document has taken throughout is the one to keep. "
    "Decide first which of the three questions the choice is really about -- is the "
    "Czech right, is the note worth filing, does the Deepsy format work -- because none "
    "of the three answers the other two. Then read the ordering, read it as bands "
    "rather than as places, and do not read the gaps between neighbours."
)


def _sessions(rows: list[results.Row]) -> int:
    """How many distinct sessions the whole run rests on.

    Counted per half and across formats, never by adding the tracks up: the
    same transcripts are written twice, once in each note format, so a sum over
    the four criteria tracks reports forty sessions where there are twenty.
    """
    wrote = _wrote(rows)
    halves = (
        (results.TRACK_CZECH_REAL, results.TRACK_DEEPSY_REAL),
        (results.TRACK_CZECH_TRANSLATED, results.TRACK_DEEPSY_TRANSLATED),
    )
    return sum(
        max((wrote[track]["corpus"] for track in tracks if track in wrote), default=0)
        for tracks in halves
    )


def _closing(rows: list[results.Row], tracks: list[str]) -> str:
    """Box D: what the whole document comes to, for somebody who has to act on it."""
    figures = _written_figures(rows)
    sessions = _sessions(rows)
    if not sessions or not figures.get("models"):
        return ""
    said = [_t(CLOSING_RUN).format(sessions=sessions, **figures)]

    differ, total = _band_agreement(tracks)
    if total:
        said.append(
            _t(CLOSING_BANDS if differ else CLOSING_BANDS_AGREE).format(differ=differ, total=total)
        )

    # One paragraph rather than four, because they are one thought: the list
    # is what a reader would have to commission, and it is short.
    missing = [_t(CLOSING_NEXT), _t(CLOSING_NEXT_CORPUS).format(sessions=sessions)]
    rated = _payload("czech-anchor.json").get("notes_rated")
    if rated:
        missing.append(_t(CLOSING_NEXT_RATER).format(notes=rated))
    # Asked of the constants that decide what a track is rather than typed: the
    # day a Deepsy note is rated on PDSQI-9 there is a track in both of those
    # tuples, and this sentence stops printing by itself.
    if int(figures["deepsy"]) and not set(tracks) & set(DEEPSY_PDSQI_TRACKS):
        missing.append(_t(CLOSING_NEXT_DEEPSY).format(deepsy=figures["deepsy"]))
    said.append(" ".join(missing))

    said.append(_t(CLOSING_READING))
    return _box(CLOSING_TITLE, said, kind="closing", level=2)


#: The three moves a criterion can be watched over. Written as pairs rather
#: than derived from "every track against every other": that would print six
#: comparisons of which three are the other three read backwards, and two of
#: the six -- the real SOAP half against the translated Deepsy one, and its
#: mirror -- change the corpus and the format at once and so measure neither.
#: Each name is a phrase rather than a label with an arrow in it, because it
#: has to read inside a sentence -- "the two judges do not both point the same
#: way from SOAP to Deepsy on the real half" -- as well as in the list of three.
CRITERION_MOVES = (
    (
        "from the real sessions to the translated ones",
        (results.TRACK_CZECH_REAL, results.TRACK_CZECH_TRANSLATED),
    ),
    (
        "from SOAP to Deepsy on the real half",
        (results.TRACK_CZECH_REAL, results.TRACK_DEEPSY_REAL),
    ),
    (
        "from SOAP to Deepsy on the translated half",
        (results.TRACK_CZECH_TRANSLATED, results.TRACK_DEEPSY_TRANSLATED),
    ),
)

#: What one move can come out as. Four words, translated whole and dropped into
#: a list after a colon rather than into a sentence frame: a Czech verdict
#: inside a frame has to decline, and no one frame fits all four.
MOVE_UP = "up"
MOVE_DOWN = "down"
MOVE_FLAT = "no change"
MOVE_SPLIT = "the judges differ"


def _moved(cells: dict, key: str, pair: tuple[str, str], step: float) -> str:
    """Which way a criterion goes between two tables, under every judge.

    A change smaller than the last digit the tables print is no change: the
    reader cannot see it, and a verdict resting on it would be a verdict about
    rounding. Where the judges do not both point the same way the answer is
    that they do not, which is a finding and not a missing one.
    """
    first, second = pair
    judges = sorted(
        {judge for track, judge in cells if track == first}
        & {judge for track, judge in cells if track == second}
    )
    signs = []
    for judge in judges:
        here = cells[(first, judge)].get(key)
        there = cells[(second, judge)].get(key)
        if here is None or there is None:
            return ""
        signs.append(0 if abs(there - here) < step else (1 if there > here else -1))
    if not signs:
        return ""
    if all(sign > 0 for sign in signs):
        return MOVE_UP
    if all(sign < 0 for sign in signs):
        return MOVE_DOWN
    if all(sign == 0 for sign in signs):
        return MOVE_FLAT
    return MOVE_SPLIT


def _unreadable_at(key: str) -> tuple[list[tuple[str, str, int, int]], int]:
    """Where this criterion cannot order the models, from the resampling.

    `tools/czech_variance.py` counts, for every pair of models, whether
    resampling the sessions leaves the gap between them in the same direction.
    A column that separates a quarter of its pairs orders the rest by accident,
    and this is the payload that says so rather than the prose guessing.
    """
    tracks = _payload("czech-variance.json").get("tracks") or {}
    found, measured = [], 0
    for track in SOAP_CRITERIA_TRACKS + DEEPSY_CRITERIA_TRACKS:
        for judge, criteria in sorted((tracks.get(track) or {}).items()):
            gaps = (criteria.get(key) or {}).get("gaps") or {}
            share, pairs = gaps.get("share"), gaps.get("pairs")
            if share is None or not pairs:
                continue
            measured += 1
            if share < UNREADABLE:
                found.append((track, judge, gaps.get("separable", 0), pairs))
    return found, measured


#: Below this, a criterion does not count as falling with note length.
#: **Both judges must reach it and both must fall**, never one: a coefficient
#: one judge sees and the other does not is a fact about that judge, and this
#: document has a chapter for those. It lived beside a grid of coefficients in
#: the length chapter and was the rule for printing a row there; that grid is
#: gone and the criterion paragraphs are the only thing left that asks the
#: question, so the number lives with them. 0.40 is a line and not a law: what
#: it buys is that "this one is entangled with length" is decided the same way
#: for all six rather than by eye.
LENGTH_ENTANGLED = 0.40


def _length_against(key: str) -> list[tuple[str, float, float]]:
    """Tracks where this criterion falls with note length under BOTH judges.

    Both, never one. A coefficient one judge sees and the other does not is a
    fact about that judge, and this document has a section for those.
    """
    blocks = _payload("czech-length.json").get("czech") or {}
    found = []
    for track in SOAP_CRITERIA_TRACKS + DEEPSY_CRITERIA_TRACKS:
        judges = (blocks.get(track) or {}).get("judges") or {}
        values = [
            value
            for block in judges.values()
            if (value := (block.get("correlations") or {}).get(key)) is not None
        ]
        if len(values) > 1 and all(value <= -LENGTH_ENTANGLED for value in values):
            found.append((track, min(values), max(values)))
    return found


CRITERIA_TITLE = "Criterion by criterion"
CRITERIA_LEAD = (
    "The six criteria one at a time. A table can say what a column scored and it cannot "
    "say what the column is worth, and the second half is what a reader needs before "
    "acting on the first. Each paragraph gives the same four things in the same order: "
    "the level, under both judges in every table that has the criterion; the direction, "
    "which way the criterion moves from one table to the next; where it breaks down; "
    "and what it is actually catching."
)
#: The two rules the six paragraphs run on, said once above them rather than in
#: each. The first was a clause inside the "where it breaks down" sentence and
#: printed five times running; the second was nowhere at all, because it had
#: been a table cell reading "not measured on this track" and there is no cell
#: to put it in any more.
CRITERIA_READING = (
    "Every pair of numbers is the two judges, in the order the tables print them, and "
    "they are never averaged: where the two point in opposite directions that is said "
    "rather than smoothed, because a mean of two judges pointing opposite ways is a "
    "number neither of them stated. And the last sentence of each paragraph -- what the "
    "criterion catches, and how often the two judges and one native speaker said the "
    "same thing -- was measured on the ten real Czech sessions under these six criteria "
    "and nowhere else. Nobody has read a Deepsy note or a translated one against a "
    "person at all."
)
CRITERIA_ORDER = (
    "The order is computed rather than chosen. The criterion whose value changes most "
    "between one table and the next comes first, because that is the order in which one "
    "number about a criterion would mislead a reader furthest -- a column that reads the "
    "same everywhere can be summarised and a column that does not, cannot."
)
CRITERION_LEVEL = "The level: {items}."
CRITERION_DIRECTION = "The direction: {items}."
BREAK_SPLIT = "Where it breaks down: the two judges do not both point the same way {names}."
BREAK_UNSEPARABLE = (
    "Where it breaks down: on {where} the resampling can tell only {separable} of the "
    "{pairs} pairs of models apart, so the order this column puts them in there is not "
    "one to read, and it is that thin in {places} of the {total} table-and-judge "
    "combinations."
)
BREAK_LENGTH = (
    "Where it breaks down: on {names} the column falls as a model writes longer notes, "
    "under both judges, between {low} and {high}, and whether that is the fault or the "
    "length is not something this document can separate."
)
BREAK_LEVEL = (
    "Nothing breaks it here: the judges point the same way in every comparison, the "
    "resampling can tell the models apart, and length does not predict it."
)


def _criterion_paragraph(key: str, cells: dict, digits: int) -> str:
    """One criterion: how high, which way, where it fails, and what it catches.

    Four sentences and not one of them typed. The chapter this replaces was a
    table whose middle column counted ties and whose right-hand column carried
    a paragraph written by hand -- which is the arrangement that let a sentence
    measured on the real Czech sessions sit beside a Deepsy row and describe it.
    In prose the sentence can say which table it came from.

    `digits` is the column's own printed precision, and it decides two things:
    how the level is written and what counts as a change rather than as
    rounding. The two have to be the same number or the paragraph can report a
    direction its own figures do not show.
    """
    step = 0.5 * 10**-digits
    label = _t(MEASURE_TABLES[results.TRACK_CZECH_REAL][key]["label"])
    said = []

    items = "; ".join(
        f"{_t(TRACK_SWITCH_LABELS.get(track, track))} "
        + " / ".join(
            _decimal(cells[(track, judge)][key], digits)
            for judge in sorted(judge for other, judge in cells if other == track)
            if key in cells[(track, judge)]
        )
        for track in SOAP_CRITERIA_TRACKS + DEEPSY_CRITERIA_TRACKS
        if any(other == track and key in found for (other, _j), found in cells.items())
    )
    if items:
        said.append(_t(CRITERION_LEVEL).format(items=items))

    moves = [(name, _moved(cells, key, pair, step)) for name, pair in CRITERION_MOVES]
    moves = [(name, verdict) for name, verdict in moves if verdict]
    if moves:
        said.append(
            _t(CRITERION_DIRECTION).format(
                items="; ".join(f"{_t(name)}, {_t(verdict)}" for name, verdict in moves)
            )
        )

    said.append(_breaks(key, moves))
    said.append(_catch(key, ANCHORED_ON))
    body = " ".join(part for part in said if part)
    return f"<p><strong>{html.escape(label)}</strong> &mdash; {html.escape(body)}</p>"


def _breaks(key: str, moves: list[tuple[str, str]]) -> str:
    """The one thing that most limits what this criterion can be read for.

    In a fixed order, and the order is the point. A split between the judges
    comes first because it is a finding rather than a shortcoming: it says the
    question itself is one people answer differently, and averaging over it
    would hide exactly that. Only where the judges agree is it worth asking
    whether the column can order the models, then whether it is measuring
    length, and only when none of those bites is the level the thing to report.
    """
    split = [name for name, verdict in moves if verdict == MOVE_SPLIT]
    if split:
        return _t(BREAK_SPLIT).format(names=_join_words([_t(name) for name in split]))

    unreadable, measured = _unreadable_at(key)
    if unreadable:
        track, judge, separable, pairs = min(unreadable, key=lambda found: found[2] / found[3])
        return _t(BREAK_UNSEPARABLE).format(
            where=f"{_t(TRACK_SWITCH_LABELS.get(track, track))} / {judge}",
            separable=separable,
            pairs=pairs,
            places=len(unreadable),
            total=measured,
        )

    against = _length_against(key)
    if against:
        return _t(BREAK_LENGTH).format(
            names=_join_words([_t(TRACK_SWITCH_LABELS.get(t, t)) for t, _lo, _hi in against]),
            low=_decimal(min(low for _t2, low, _high in against), 2),
            high=_decimal(max(high for _t2, _low, high in against), 2),
        )

    return _t(BREAK_LEVEL)


def _criteria_prose(rows: list[results.Row]) -> str:
    """The six criteria in prose, most movable first, nothing typed.

    It replaces a table with three columns -- the criterion, whether it can
    rank, and a hand-written sentence about what it catches -- and the table
    was the wrong shape twice over. Its middle column answered one question
    about a column that has four things worth knowing, and its right-hand
    column had a cell for every track while its sentences were measured on one,
    which is why thirty-six of those cells said "not measured on this track"
    and nothing else.

    The ordering is the finding the table could not carry: a criterion that
    reads the same in every context can be summarised in one number and one
    that swings by a third of the scale cannot, so the swing decides which
    paragraph a reader meets first.
    """
    cells = _cells(rows, SOAP_CRITERIA_TRACKS + DEEPSY_CRITERIA_TRACKS)
    if not cells:
        return ""
    digits = dict(COLUMNS[results.TRACK_CZECH_REAL])
    keys = [
        key for key in czech_scorer.CRITERION_KEYS if any(key in found for found in cells.values())
    ]
    if not keys:
        return ""

    # How far a criterion travels between contexts, per judge and then the
    # worse of them. Per judge because the two judges disagreeing is a
    # different fact with its own sentence below, and a range taken over both
    # at once would let that disagreement decide the order of the chapter.
    def travel(key: str) -> float:
        widest = 0.0
        for judge in sorted({judge for _track, judge in cells}):
            values = [
                found[key]
                for (_track, other), found in cells.items()
                if other == judge and key in found
            ]
            if len(values) > 1:
                widest = max(widest, max(values) - min(values))
        return widest

    ordered = sorted(keys, key=lambda key: (-travel(key), key))
    paragraphs = [_criterion_paragraph(key, cells, digits.get(key, 2)) for key in ordered]
    return (
        f"<h2>{_t(CRITERIA_TITLE)}</h2>"
        + f"<p>{html.escape(_t(CRITERIA_LEAD))}</p>"
        + f"<p>{html.escape(_t(CRITERIA_ORDER))}</p>"
        + f"<p>{html.escape(_t(CRITERIA_READING))}</p>"
        + "".join(paragraphs)
    )


#: The chapter both outside comparisons live in. They were two chapters with a
#: caveat box each, and the two boxes said the same thing twice: that the number
#: on the outside was not measured here. One chapter, one box.
OUTSIDE_TITLE = "What the numbers from outside say"
OUTSIDE_LEAD = (
    "Two numbers about these models exist outside this document, and both are the kind "
    "of thing somebody reaches for instead of running a benchmark: this project's own "
    "English leaderboard, and a published index of general capability. This chapter "
    "asks what either one tells a reader about the Czech notes. Each half opens with "
    "its chart, because a chart is the part of this that can be read without "
    "arithmetic, and the tables under it ask the same question one column at a time. "
    "Bold in those tables marks a correlation that survives an exact permutation test "
    "at p < 0.05; the rest failed it and are printed anyway, because how little there "
    "is to see is the result here, and dropping the weak cells would flatter it."
)
JOIN_LEAD = (
    "{systems} models, and whether a standing in one language predicts a standing in "
    "the other has two answers -- which one a reader gets depends on which English "
    "number they happened to be looking at."
)
JOIN_RANKING_LEAD = (
    "The English page sorts by one measure -- {measure} -- and a position on that page "
    "means what that measure says. Here it stands against the Czech quality columns. "
    "Nothing survives the test, and the two judges do not agree even on the sign."
)
JOIN_FIGURE_CAPTION = (
    "One block per judge, one line per model: its place among these models on the "
    "English notes, joined to the place the same instrument gave it in Czech. A level "
    "grey line is a model that kept its place. Each model is counted once under each "
    "judge, so the count in the title is over placings rather than over models. And a "
    "place is not a measurement -- two models a hundredth apart are drawn a whole "
    "place apart -- which is the point of drawing it: a leaderboard hands a reader a "
    "place, and this is what that place is worth in the other language."
)
EXTERNAL_LEAD = (
    "Nothing in this repository records how big a model is, how it was trained or when "
    "it shipped, so this half has to come from outside it. The index used here is a "
    "published one that scores models on general capability -- the kind of number a "
    "team reads before choosing one. The question is whether it says anything about "
    "the notes, and whether it says the same thing in both languages."
)
EXTERNAL_FIGURE_CAPTION = (
    "On the left the English notes, on the right the Czech ones, one dot per model and "
    "one colour per judge. The vertical axis runs the whole of PDSQI-9, from 1 to 5, "
    "rather than the part these models occupy, so how little of the instrument is in "
    "use is visible before the slope across it is read. Each judge's correlation and "
    "the number of models behind it are both in the legend, and the second number "
    "matters as much as the first."
)
#: The one caveat, where there were two. The first two sentences are the two
#: weak joins, one per half; the rest is the provenance of the outside index,
#: which is the half that came from somebody else entirely.
OUTSIDE_CAVEAT_LEAD = (
    "Neither of the outside numbers in this chapter was measured by this project, and "
    "each is joined to it at a weak point."
)
OUTSIDE_MATCH = (
    "The capability index is a published third-party score, and the join to it is "
    "nothing but the model's name: a name on this endpoint is not evidence about which "
    "model is behind it, and this project's first working rule exists because one id "
    "there returned another model's output."
)
OUTSIDE_UNMATCHED = "Models whose name does not identify a variant are absent rather than guessed:"


#: The external index carries its version and its release date in one label --
#: "Artificial Analysis Intelligence Index v4.1.1, released 2026-08-06" -- and
#: that label is data rather than a template, so `_t` never sees it and the word
#: "released" printed in English inside the Czech document. The name and the
#: version are the instrument's own and are reproduced verbatim; only the word
#: joining them to the date is ours, so only that is translated.
INDEX_RELEASED = "{name}, released {date}"


def _index_version(label: str) -> str:
    """The index label with its one English connector translated.

    Returns the label unchanged when it does not carry the connector: a version
    string this does not recognise is reproduced as it stands rather than guessed
    at, which is the same rule the rest of this document applies to anything it
    did not measure.
    """
    name, sep, date = label.partition(", released ")
    if not sep:
        return label
    return _t(INDEX_RELEASED).format(name=name, date=date)


def _outside() -> str:
    """Both outside comparisons under one heading, with one caveat under both.

    They were two chapters, each ending in a warn box, and the two boxes
    overlapped on the thing that matters most in either: the number on the
    outside was measured somewhere else, by somebody else, on something else.
    Said twice, a caveat teaches a reader to skip caveats.

    Each half now opens with its chart. The tables are correlation grids with a
    p-value in every cell, which is the form the answer has and not a form a
    clinical reader can act on; the charts carry the same two answers in a
    shape that can be read, and the tables stay under them for anyone who wants
    the coefficient.
    """
    halves = [half for half in (_join(), _external()) if half]
    if not halves:
        return ""
    return (
        f"<h2>{html.escape(_t(OUTSIDE_TITLE))}</h2>"
        + f"<p>{html.escape(_t(OUTSIDE_LEAD))}</p>"
        + "".join(halves)
        + _outside_caveat()
    )


def _outside_caveat() -> str:
    """The one warn box the chapter ends on, built from what is in this checkout.

    Each sentence is printed only where the thing it warns about is: a document
    built without the external payload does not carry a sentence about a name
    match nobody made, and the unmatched models are named only when there are
    any -- a colon with nothing after it reads as a list that went missing.
    """
    join = _payload("czech-join.json")
    external = _payload("czech-external.json")
    if not join and not external:
        return ""
    said = [f"<strong>{html.escape(_t(OUTSIDE_CAVEAT_LEAD))}</strong>"]
    confound = join.get("confound") or ""
    if confound:
        said.append(html.escape(_t(confound)))
    if external:
        said.append(html.escape(_t(OUTSIDE_MATCH)))
        unmatched = ", ".join(external.get("unmatched") or [])
        if unmatched:
            said.append(html.escape(_t(OUTSIDE_UNMATCHED)) + f" {html.escape(unmatched)}.")
        version, fetched = external.get("index_version", ""), external.get("fetched", "")
        if version or fetched:
            said.append(
                html.escape(
                    _t(
                        "The external score is versioned like the measures here are, "
                        "so it is recorded with the version and the day it was read:"
                    )
                )
                + f" {html.escape(_index_version(version))}, {html.escape(fetched)}."
            )
    reading = join.get("reading") or ""
    if reading:
        said.append(html.escape(_t(reading)))
    return "<div class='warn'><p>" + " ".join(said) + "</p></div>"


def _measure_label(key: str) -> str:
    """The name this document has already given a measure, from its payload key.

    A payload records `organized`; the tables three pages above call it
    Usporadanost (spelled here without its diacritics, because this file carries
    no Czech). Printing the key inside a sentence gives one measure two names
    with nothing to tell a reader it is one measure -- and worse in the Czech
    document, where the sentence around the key is Czech and the key is not.

    Every measure table is searched, because a payload names columns from both
    instruments: the flat attributes are PDSQI-9 and the measure the English
    page ranks by is not. A key no table has a label for goes to `_t` as it
    stands, which stops a Czech build rather than printing English -- a key with
    no label is a column this document has never drawn, and guessing is worse
    than stopping.
    """
    for measures in MEASURE_TABLES.values():
        if key in measures:
            return _t(measures[key]["label"])
    return _t(key)


def _join() -> str:
    """The question the track was built for, answered in the document that leaves.

    Written by `tools/czech_join.py`. Two tables, because there are two answers:
    the same instrument asked in both languages transfers, and the measure the
    English page actually ranks by does not. Printing only the first would be
    the more flattering half.

    A cell carries its p-value because nine models invite over-reading, and the
    two judges sit side by side because the reading rule is "believe a column
    that says the same thing under both". Both of those are said once for the
    whole chapter now, above it, rather than once per half.

    The chart comes before the tables because it answers the same question in
    the form a reader asked it: not "what is the rank correlation of Thorough"
    but "does a model that is third in English stay third in Czech".
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
        # The claim opens its own paragraph instead of standing as a heading
        # over it. Under a chapter these two are halves of a half, and a third
        # level of heading over a six-row table reads as more structure than
        # there is.
        return (
            f"<p><strong>{html.escape(heading)}.</strong> {html.escape(lead)}</p>"
            f"<table><thead><tr><th>{_t('Attribute')}</th>{head}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )

    flat = sorted(
        {_measure_label(key) for name in judges for key in data["judges"][name].get("flat", [])}
    )
    ranking = data["judges"][judges[0]].get("ranking_measure")
    ranking = _measure_label(ranking) if ranking else _t("the ranking measure")
    systems = len(data["judges"][judges[0]].get("systems", []))

    return (
        f"<h3>{_t('Does the English leaderboard predict the Czech?')}</h3>"
        + f"<p>{html.escape(_t(JOIN_LEAD).format(systems=systems))}</p>"
        + _figure("join", JOIN_FIGURE_CAPTION)
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
            _t(JOIN_RANKING_LEAD).format(measure=ranking),
        )
        + (
            f"<p class='sub'>{_t('Flat on one side and therefore not correlated:')} "
            f"{html.escape(', '.join(flat))}.</p>"
            if flat
            else ""
        )
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
    matched are named rather than quietly dropped. All three are now in the
    chapter's one caveat box, under both halves, and in the chart's own
    footnote -- a picture has to carry its provenance wherever it is looked at.
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
                f"<p><strong>{html.escape(_t(heading))}:</strong> "
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
            f"<p><strong>{html.escape(_t(heading))}</strong></p>"
            f"<table><thead><tr><th>{_t('Measured here')}</th>{head}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )
    if not blocks:
        return ""

    return (
        f"<h3>{_t('Does general capability predict any of this?')}</h3>"
        + f"<p>{html.escape(_t(EXTERNAL_LEAD))}</p>"
        + _figure("external", EXTERNAL_FIGURE_CAPTION)
        + "".join(blocks)
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
    # Which note formats the quality instrument was actually put to, counted
    # rather than typed. The sentence used to say "only to the SOAP notes" and
    # went on saying it after PDSQI-9 was put to the Deepsy notes and given two
    # tables in the same document -- a claim about the run that was not read
    # from the run.
    formats = sorted(
        {
            "SOAP" if row.track in PDSQI_TRACKS else "Deepsy"
            for row in results.latest(rows)
            if row.is_scored and row.track in PDSQI_TRACKS + DEEPSY_PDSQI_TRACKS
        }
    )
    # How many models wrote every session they were asked for on the SOAP
    # tracks, which is what the short document's opening claims. It used to
    # claim all of them did -- and then said, two sentences later, that some
    # notes are missing. Both cannot be true, and the counted one is this.
    soap_blocks = [b for t, b in found.items() if t in SOAP_CRITERIA_TRACKS]
    soap_models = {m for b in soap_blocks for m in b["wrote"]}
    full = sum(
        1 for m in soap_models if all(b["wrote"].get(m, 0) == b["corpus"] for b in soap_blocks)
    )
    return {
        "models": str(len(models)),
        "full": str(full),
        "written": str(written),
        "asked": str(asked),
        "soap": str(soap),
        "deepsy": str(written - soap),
        "short": "; ".join(short),
        "pdsqi_formats": (
            _t("the notes in both formats")
            if len(formats) > 1
            else _t("the {format} notes only").format(format=formats[0])
            if formats
            else _t("no notes yet")
        ),
    }


def _thinnest_banded(models: list[str], tracks: tuple[str, ...]) -> str:
    """Of these models, the one placed on the fewest complete notes, and where.

    A band names a model as ahead; it does not say how much is behind the name.
    On the Deepsy tables the model in the top band under both judges is also the
    one the judge left the most notes part-answered on -- so the summary named a
    winner and the count that qualifies it was in a payload nothing read.

    Complete means answered on every criterion the band averages, which is the
    same quantity the score tables count in their notes column. Returns an empty
    string when every one of these models has its table's full corpus, because
    then there is nothing to qualify.
    """
    coverage = _payload("czech-variance.json").get("coverage") or {}
    worst = None
    for track in tracks:
        for judge_model, cover in sorted((coverage.get(track) or {}).items()):
            sessions = cover.get("sessions") or 0
            for model in models:
                block = (cover.get("systems") or {}).get(model)
                if not block or not sessions:
                    continue
                complete = block["notes"] - block["partial"]
                if complete >= sessions:
                    continue
                if worst is None or complete / sessions < worst[0]:
                    worst = (complete / sessions, model, complete, sessions, track, judge_model)
    if worst is None:
        return ""
    _share, model, complete, sessions, track, judge_model = worst
    return (
        f"{model}, {complete} {_t('of')} {sessions} "
        f"({_t(TRACK_SWITCH_LABELS.get(track, track))}, {judge_model})"
    )


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
    said: list[tuple[str, str]] = []

    def _say(name: str, sentence: str) -> None:
        """One paragraph, under a name the short document can ask for."""
        said.append((name, sentence))

    bands = _payload("czech-variance.json").get("bands", {})
    # Named tracks, not "everything that is not PDSQI". That filter was written
    # when the only criteria tracks were the two SOAP halves, and it silently
    # swept the Deepsy tables into the same intersection the moment they were
    # banded -- pooling two note formats into one "all N tables" claim, which
    # section 4 of this document spends a page refusing to do.
    soap = {t: j for t, j in bands.items() if t in SOAP_CRITERIA_TRACKS}
    deepsy = {t: j for t, j in bands.items() if t in DEEPSY_CRITERIA_TRACKS}
    # Named, not `endswith("-pdsqi")`. That filter was written when the only
    # PDSQI tables were the two SOAP halves, and it swept the Deepsy pair in
    # the moment they were banded -- turning `all {tables} combinations` from
    # four into eight and pooling two note formats into one claim. The
    # objection is the one section 1b makes: three models were asked in only
    # one of the two formats, so an intersection across both would demote a
    # model for a question nobody put to it.
    quality = {t: j for t, j in bands.items() if t in PDSQI_TRACKS}
    quality_deepsy = {t: j for t, j in bands.items() if t in DEEPSY_PDSQI_TRACKS}

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
        _say(
            "soap-ranking",
            _t(
                "On writing correct Czech, {top} in the top band of all {tables} "
                "table-and-judge combinations the bands cover -- the SOAP halves, both "
                "judges. {bottom} in the bottom band of all {tables}. Between those two "
                "ends the tables disagree with each other, so nothing else here is a "
                "ranking."
            ).format(top=end(top), bottom=end(bottom, lead=True), tables=tables),
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
        _say(
            "deepsy-ranking",
            _t(
                "The Deepsy format was asked the same question over its own {tables} "
                "table-and-judge combinations, and it is counted separately rather than "
                "pooled with the four above: {top} in the top band of all of them and "
                "{bottom} in the bottom "
                "band of all of them. The two formats are not added together because "
                "not every model was asked in both, because a Deepsy note is written to "
                "a different prompt and comes out a different shape, and because the "
                "one native-speaker anchor this project has was measured on SOAP notes "
                "alone. Length does not settle it either way: it runs against "
                "{soap_against} of the {soap_total} criterion-and-judge coefficients on "
                "the SOAP halves and against {deepsy_against} of {deepsy_total} in the "
                "Deepsy format, so it is not the uniform penalty one number could stand "
                "for."
            ).format(top=end(top_d), bottom=end(bottom_d), tables=tables_d, **_length_signs()),
        )

    # 1b-tail. What is behind the names just given. A band says a model is
    #     ahead and says nothing about how much of the corpus put it there, and
    #     on the Deepsy tables the model in the top band under both judges is
    #     also the one the judge left the most notes part-answered on. Counted
    #     per format and never pooled, for the reason 1b gives.
    behind = [
        (label, _thinnest_banded(models, tracks))
        for label, models, tracks in (
            (_t("the SOAP halves"), top, SOAP_CRITERIA_TRACKS),
            (_t("the Deepsy format"), top_d, DEEPSY_CRITERIA_TRACKS),
        )
        if models
    ]
    named = [f"{label} — {found}" for label, found in behind if found]
    if named:
        _say(
            "how-thin",
            _t(
                "Those names do not all rest on the same amount, and the thinnest of "
                "them is worth reading beside the claim: {named}. That count is the "
                "notes answered on every criterion the band averages, out of the "
                "sessions its table has, and the notes column of the tables below "
                "prints it beside every row it applies to."
            ).format(named="; ".join(named)),
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
            # Withdrawn, or merely failed? The error on disk cannot tell them
            # apart -- it is the same HTTP 400 either way -- so the answer comes
            # from `tools/czech_roster.py`, which asks the endpoint what it
            # still serves and writes it down. A retryable gap and a permanent
            # one read identically in the tables and mean opposite things: one
            # closes on the next run, the other never does, and somebody spent
            # the endpoint's quota this morning finding that out.
            gone = set(_payload("czech-roster.json").get("withdrawn") or {}) & set(refused)
            _say(
                "who-is-missing",
                _t(
                    "One caution about that second count. {subject} in the bottom band "
                    "of all {tables} SOAP table-and-judge combinations and in no Deepsy "
                    "band at all -- not "
                    "because of anything written, but because e-INFRA answered {calls} "
                    "of the calls asking for those notes with an error and returned no "
                    "note. Adding the two counts together would have removed it from "
                    "the bottom of the table on the strength of an outage."
                    if not gone
                    else "One caution about that second count. {subject} in the bottom "
                    "band of all {tables} SOAP table-and-judge combinations and in no "
                    "Deepsy band at all -- not because of anything written, but because "
                    "e-INFRA answered {calls} of the calls asking for those notes with "
                    "an error and returned no note. The endpoint no longer serves it at "
                    "all, so this is not a gap that will close on a later run: the "
                    "question can no longer be put. Adding the two counts together "
                    "would have removed it from the bottom of the table on the strength "
                    "of a model being retired."
                ).format(
                    subject=end(sorted(refused), lead=True),
                    tables=tables,
                    calls=sum(refused.values()),
                ),
            )
            # And the name one suffix away, when the bands list one. The two
            # paragraphs above and below this one say `glm-5.3-flash` is in no
            # Deepsy band and then list `glm-5.3` in one, which reads as a
            # contradiction to anybody not counting characters. Computed by
            # prefix rather than typed, so it appears only while both names are
            # actually on the page.
            banded_soap = {
                model
                for judges in soap.values()
                for grouped in judges.values()
                for band in grouped["bands"]
                for model in band["models"]
            }
            near = sorted(
                {
                    model
                    for model in banded_deepsy - banded_soap
                    for name in refused
                    if name.startswith(f"{model}-") or model.startswith(f"{name}-")
                }
            )
            if near:
                _say(
                    "who-is-missing-also",
                    _t(
                        "Read the two names carefully: {refused} and {near} differ by "
                        "one suffix and are different models. {near} is in the Deepsy "
                        "bands above and in none of the SOAP ones."
                    ).format(refused=_join_words(sorted(refused)), near=_join_words(near)),
                )

    # 2. The same question asked of note quality, which does not answer.
    top_q, tables_q = shared(quality, 0)
    if tables_q and not top_q:
        _say(
            "soap-quality",
            _t(
                "On whether the note is any good, no model is in the top band of all "
                "{tables} table-and-judge combinations and none is in the bottom band "
                "of all {tables}. The "
                "quality instrument does not agree with itself from one judge or one "
                "half to the next, and no model can be called better on it."
            ).format(tables=tables_q),
        )

    # 2b. The same instrument over the notes the application actually writes,
    #     counted over its own tables for the reason 1b gives and never added to
    #     the four above. This is the newest measurement in the document and the
    #     only one that speaks to the format a reader might actually deploy.
    top_qd, tables_qd = shared(quality_deepsy, 0)
    bottom_qd, _ = shared(quality_deepsy, -1)
    # How wide the band that membership is shared with. "In the top band of all
    # four" reads as a distinction held with nobody; on one of these four the
    # top band holds two thirds of the roster, so the same sentence means very
    # different things across the tables it intersects over.
    widths = sorted(
        len(grouped["bands"][0]["models"])
        for judges_here in quality_deepsy.values()
        for grouped in judges_here.values()
    )
    rosters = sorted(
        len({m for band in grouped["bands"] for m in band["models"]})
        for judges_here in quality_deepsy.values()
        for grouped in judges_here.values()
    )
    if tables_qd:
        composites = _payload("czech-variance.json").get("composites") or {}
        _say(
            "deepsy-quality",
            _t(
                "The same instrument was put to the notes in the Deepsy format over "
                "{tables} table-and-judge combinations of its own: {top} in the top "
                "band of all of them and {bottom} in the bottom band of all of them. "
                "It is counted separately from the four above and not added to them, "
                "for the reason the criteria are: not every model was asked in both "
                "formats. Every half's band is built from the columns that exist "
                "there and separate models, the same set for both formats and both "
                "judges: {real} on the real half, {translated} on the translated "
                "one. The real half cannot ask `accurate` or `thorough` -- they need "
                "the session, and the real sessions never leave e-INFRA. Read the "
                "membership with the width beside it: across those {tables} the top "
                "band runs from {narrowest} models to {widest} of the {roster} placed, "
                "so on the widest of them being in it separates almost nobody."
            ).format(
                top=end(top_qd),
                bottom=end(bottom_qd),
                tables=tables_qd,
                real=_join_words(composites.get("real") or []) or "-",
                translated=_join_words(composites.get("translated") or []) or "-",
                narrowest=widths[0],
                widest=widths[-1],
                roster=rosters[-1],
            ),
        )

    # 3. Which columns of that instrument can rank anything at all.
    dead, total, alive, worst, judge = _dead_columns(rows)
    if dead:
        _say(
            "dead-columns",
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
            ),
        )

        # And whether the person who checked this instrument checked the part of
        # it the tables rest on. Printed only when the answer is no.
        rated_notes, rated = _human_pdsqi()
        anchored_track = results.TRACK_CZECH_REAL_PDSQI
        here = [r for r in rows if r.track == anchored_track and r.judge_model == judge]
        flat = {key for key, _ in COLUMNS[anchored_track]} - set(_varying(anchored_track, here))
        carries = "succinct"
        if rated and set(rated) <= flat and carries not in rated:
            measures = MEASURE_TABLES.get(anchored_track, {})

            def label(key: str) -> str:
                return _t(measures[key]["label"]) if key in measures else key

            _say(
                "anchor-misses",
                _t(ANCHOR_MISSES).format(
                    notes=rated_notes,
                    rated=_join_words([label(k) for k in rated]),
                    judge=judge,
                    verb=_t("is") if len(rated) == 1 else _t("are"),
                    carries=label(carries),
                ),
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
        _say(
            "length",
            _t(
                "Read the bottom of those tables carefully: the three models that write "
                "the longest notes take the last three places in all {total} "
                "table-and-judge combinations of them. "
                "Each criterion asks whether there is a fault anywhere in a note, and a "
                "longer note has more places to hide one. On the quality instrument, "
                "rating the very same notes, those three models are not at the bottom."
            ).format(total=len(checks)),
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
        _say(
            "length-exceptions",
            _t(
                "That pattern is not a law: in the {total} Deepsy table-and-judge "
                "combinations the three "
                "longest-writing models -- a different three, because the two formats "
                "were not asked of the same set of models -- do not all land in the "
                "last three places under either judge. Length and rank travel together "
                "on the SOAP halves and more loosely here, which is one more reason the "
                "two formats are counted apart rather than added up."
            ).format(total=len(deepsy_checks)),
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
        _say(
            "length-size",
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
            ),
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
            _say(
                "english-leaderboard",
                _t(
                    "And the English leaderboard does not predict this. The same "
                    "instrument asked in both languages transfers; the single measure "
                    "the English page ranks by -- {measure} -- does not. A model's "
                    "standing there says nothing about the Czech it writes."
                ).format(measure=_t(label)),
            )

    if not said:
        return ""
    # The name travels with the paragraph. `czech_short` drops three of these
    # and used to drop them by position, which is only correct while the list
    # has a fixed length -- and it does not: 1c writes a second paragraph only
    # when there is a second thing to say. The day it wrote one, the short
    # document began dropping the quality finding instead.
    body = "".join(f'<p data-part="{name}">{html.escape(sentence)}</p>' for name, sentence in said)
    heading = _t("What the Czech track found, in {count} short paragraphs").format(count=len(said))
    return f"<h2>{heading}</h2>{body}"


def _glossary() -> str:
    """The vocabulary, above the findings that use it.

    A definition list rather than prose: a reader glances back at this, and
    prose is the wrong shape for something read out of order. It is authored
    rather than computed, which is the exception in this document -- but the
    numbers in it would be the count of tracks and tables, and those are said
    with their figures where they are drawn.
    """
    items = "".join(
        f"<dt>{html.escape(_t(term))}</dt><dd>{html.escape(_t(meaning))}</dd>"
        for term, meaning in GLOSSARY
    )
    return f"<h2>{_t(GLOSSARY_HEADING)}</h2><dl class='measures'>{items}</dl>"


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


#: The gap between what a person checked and what the tables rest on. Printed
#: only while it is true, and computed from the ratings file rather than typed,
#: so it stops printing the day somebody rates a note on the column that
#: carries the band.
ANCHOR_MISSES = (
    "And the one human check on this instrument does not reach them: a person rated "
    "{notes} notes on {rated}, which under {judge} {verb} exactly the columns that are "
    "the same for every model. {carries}, which supplies most of what the real half's "
    "band is built from, has never been rated by a person at all."
)


def _human_pdsqi() -> tuple[int, list[str]]:
    """How many notes a person rated on PDSQI-9, and on which attributes.

    Fifteen answers over five notes sit in `local/czech-pdsqi-answers.json` and
    nothing in this repository read them until now -- the file's own name is
    the only mention of it in any source file.
    """
    found = _payload("czech-pdsqi-answers.json").get("answers") or []
    notes = {(a.get("system"), a.get("session")) for a in found if a.get("attribute")}
    return len(notes), sorted({a["attribute"] for a in found if a.get("attribute")})


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

    **No heading of its own any more.** It was a chapter four sections after
    the last Deepsy table, so the comparison and the tables it compares were
    separated by everything this document says about length, dominance and the
    English leaderboard. It is now the middle of the Deepsy chapter, between
    the figure that draws the same finding and the two tables it is drawn from,
    and `_deepsy_chapter` supplies the heading.
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
        f"<h3>{_t('The same models, the same sessions, two note formats')}</h3>"
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

    There is no grid of correlations here any more, and no p-values either.
    Eleven or sixteen points make a threshold theatre, and two columns of
    coefficients headed with the judges' names is the thing a reader of this
    section could not act on. The chart says it better: one dot a model, one
    panel a half of the corpus, one colour a judge -- so the reading rule this
    document applies everywhere else, believe what both judges say and distrust
    what only one of them says, is something a reader can carry out by eye.
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
    # Guarded on the coefficients themselves rather than on a table that no
    # longer exists. The paragraph is about them, so it prints when there are
    # any: left gated on `if table:` with the table deleted, this paragraph and
    # the caveat under it would have gone silently.
    signs = _length_signs()
    if int(signs["total"]):
        parts.append("<p>" + html.escape(_t(LENGTH_BUYS).format(**signs)) + "</p>")
        parts.append(_figure("length", LENGTH_FIGURE_CAPTION))
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
    "So what can be said about which model is better, without fitting anything at "
    "all? Take the models two at a time. A pair counts as decided when one of them "
    "beats the other by more than {separation} on the composite of the six criteria "
    "under BOTH judges -- one judge on its own decides nothing here. A decided pair "
    "then survives the handicap when the winner also wrote at least as many words as "
    "the loser: the longer note offered more places for a fault to be found and had "
    "fewer of them anyway, so length is not what won it. {survived} of the {decided} "
    "decided pairs survive, counting the two halves of the corpus separately. That is "
    "a partial order and not a ranking: it says which model beats which, and about "
    "most pairs it says nothing at all. It also reaches only part of the field -- "
    "{winners} models ever appear on the winning side of a surviving pair and "
    "{losers} on the losing side, and a model can be in both lists, beaten by one "
    "model and beating another. How little of this there is is the finding."
)


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
                    # `_grouped`, not a comma. A comma is the Czech DECIMAL
                    # separator, so "4,000 times" printed to a Czech reader
                    # reads as four -- and this sentence is about how many
                    # resamples the interval rests on.
                    resamples=_grouped(max(block["resamples"] for block in fits)),
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
    # On the pairs the payload counted, not on a table that no longer exists.
    # This paragraph is the only place in the document that says what "decided"
    # and "survives the handicap" mean, and the summary at the top prints the
    # same two counts -- so with it gone that summary would have no backing.
    # Nothing is said when nothing was decided: "0 of 0 pairs" is an absence
    # dressed as a measurement.
    blocks = data.get("handicapped") or {}
    decided = sum(block["decided"] for block in blocks.values())
    if decided:
        pairs = [pair for block in blocks.values() for pair in block["pairs"]]
        parts.append(
            "<p>"
            + html.escape(
                _t(LENGTH_HANDICAP).format(
                    separation=_decimal(next(iter(blocks.values()))["separation"], 2),
                    survived=sum(block["survived"] for block in blocks.values()),
                    decided=decided,
                    winners=len({pair["winner"] for pair in pairs}),
                    losers=len({pair["loser"] for pair in pairs}),
                )
            )
            + "</p>"
        )
    return "\n".join(parts)


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


#: The three views this document takes of one question, in the order it takes
#: them. Each is the pair of tracks it was measured on, the real half first and
#: the translated half second -- the order every other block here uses.
PERSPECTIVES = (
    ("the six Czech criteria on the SOAP notes", SOAP_CRITERIA_TRACKS),
    ("PDSQI-9 on the same SOAP notes", PDSQI_TRACKS),
    ("the six Czech criteria on the Deepsy notes", DEEPSY_CRITERIA_TRACKS),
)

PERSPECTIVES_TITLE = "Three views of one question"
PERSPECTIVES_LEAD = (
    "This document has now asked one question three times over, and a reader who has come "
    "this far is holding three sets of tables with nothing saying whether they are three "
    "answers or one answer printed three ways. The question is the same every time: which "
    "of these models writes a note worth having. What changes is what is asked about the "
    "note, and which note was written. This chapter says what differs between the three, "
    "what follows from that, whether any one of them could be dropped, and what keeping all "
    "three costs."
)
PERSPECTIVES_DIFFER = "What differs between them"
PERSPECTIVE_CRITERIA_SOAP = (
    "Six yes/no questions about the Czech itself, put to the note each model wrote in the "
    "SOAP format from both halves of the corpus: {models} models, {notes} notes. It cannot "
    "say whether a note is any good. A flawless Czech sentence about nothing passes all six "
    "of them."
)
PERSPECTIVE_QUALITY = (
    "A published instrument asking whether the note is worth filing -- whether it is useful, "
    "whether it is organised, whether it says what it says in as few words as it can. It "
    "reads the notes the criteria have already read, {notes} of them from {models} models, "
    "and writes none of its own."
)
PERSPECTIVE_QUALITY_HALVES = (
    "Its two halves are not even the same questions: {missing} of its attributes cannot be "
    "asked about a real session, because answering them means reading the transcript and no "
    "transcript is ever sent to a judge. On that half those attributes are missing rather "
    "than low."
)
PERSPECTIVE_DEEPSY = (
    "The same six questions about the Czech, put to the note format the Deepsy application "
    "actually writes: {models} models, {notes} notes. Same criteria as the first view with a "
    "different note under them, so where those two disagree it is the note that changed."
)
PERSPECTIVES_ROSTER = (
    "Those are not the same models, and that on its own forbids adding the three together. "
    "{shared} of them are in all three views and {only} are in some views and not others -- "
    "either the endpoint refused those notes or that view never asked for them. An average "
    "over three views would be an average over three different fields of models, which is a "
    "statement about who was present rather than about who writes well."
)

PERSPECTIVES_FOLLOWS = "What follows from that"
FOLLOWS_LEAD = (
    "If the three were saying one thing, they would put the models in one order. The order "
    "each view uses is the one its own tables print -- by dominance, which needs no scale "
    "and can therefore be compared between instruments that do not share one -- and how far "
    "two orders agree is a rank correlation over the models both views hold. There are "
    "{comparisons} of those: each pair of views, on each half of the corpus, under each "
    "judge separately. A correlation of 1 would mean the two put every model in the same "
    "place; 0 would mean that knowing one order tells a reader nothing about the other."
)
FOLLOWS_RANGE = (
    "The pair that agrees most -- {closest} -- stays between {closest_low} and "
    "{closest_high} across its comparisons. The pair that agrees least -- {furthest} -- runs "
    "from {furthest_low} to {furthest_high}."
)
FOLLOWS_ONE_PAIR = (
    "There is one pair of views to compare here -- {pair} -- and it runs between {low} and "
    "{high} across its comparisons."
)

PERSPECTIVES_REDUNDANT = "Is any one of them redundant?"
REDUNDANT_TEST = (
    "Here is the test this chapter applies, written out so that a reader who disagrees with "
    "it can say where. A view is redundant when two things are true at once: it puts the "
    "models in the same order as some other view -- under both judges and on both halves, "
    "not on average -- and it separates no pair of models that the other view leaves "
    "together. The first half asks whether it says anything different; the second asks "
    "whether it says anything more. Failing either one is enough to keep it."
)
REDUNDANT_ORDER_NO = (
    "The first half: no two views put the models in the same order. The closest any single "
    "comparison comes is {best}, where an identical order would be 1."
)
REDUNDANT_ORDER_YES = (
    "The first half: {pairs} put the models in the same order, under both judges and on both "
    "halves. No other pair of views does."
)
REDUNDANT_EXTRA_NO = (
    "The second half: every view separates pairs of models that the others leave together. "
    "The view that adds fewest still adds {fewest} of them, counted over the models the two "
    "views share, and the one that adds most adds {most}."
)
REDUNDANT_EXTRA_YES = (
    "The second half: {names} separates no pair of models that some other view does not "
    "separate as well."
)
REDUNDANT_KEEP_ALL = (
    "So none of the three can be dropped, and it fails on both halves of the test rather "
    "than on a technicality: the views do not agree about the order, and each of them "
    "separates models the others cannot. That is not a comfortable result. It means this "
    "document holds three answers to one question with no honest way of reducing them to "
    "one, and a team choosing a model has to decide first which of the three they are "
    "choosing on."
)
REDUNDANT_DROP = (
    "So one of them can be dropped: {redundant} adds nothing that {other} does not already "
    "say. It puts the models in the same order, under both judges and on both halves, and it "
    "separates no pair of models that the other one leaves together."
)

PERSPECTIVES_COST = "What keeping all three costs"
COST_TEXT = (
    "Keeping a view costs whatever its notes cost to write, and only two of the three write "
    "any. The SOAP notes took {soap_calls} calls to e-INFRA for {soap_notes} notes. The "
    "quality view cost no generation at all -- it reads those same notes, so keeping it "
    "costs nothing that was not already spent. The Deepsy notes took {deepsy_calls} calls "
    "for {deepsy_notes} notes, because that format is asked for one section at a time and a "
    "note there is three answers rather than one. Set against three orders that will not "
    "reduce to one, that is the cheap half of the problem."
)


def _view(latest: list[results.Row], tracks: tuple[str, ...]) -> dict[int, dict]:
    """One view, keyed by which half of the corpus each part of it is.

    Keyed rather than listed because two views are compared half against half,
    and a run that scored the translated half of one view and both halves of
    another would otherwise have compared the translated half of the first with
    the real half of the second and called the difference a disagreement.
    """
    halves = {}
    for index, track in enumerate(tracks):
        here = [row for row in latest if row.track == track]
        if not here:
            continue
        newest = max(row.judge_prompt_version for row in here)
        here = [row for row in here if row.judge_prompt_version == newest]
        tables: dict[str, dict[str, dict]] = {}
        for row in here:
            tables.setdefault(row.judge_model or "", {})[row.system_id] = row.metrics.headline
        if not tables:
            continue
        halves[index] = {
            "track": track,
            "tables": tables,
            "keys": [key for key, _ in COLUMNS[track]],
            # The models every judge scored, which is what the table draws and
            # therefore what an order over it can be about.
            "systems": sorted(set.intersection(*(set(t) for t in tables.values()))),
            "notes": sum(row.n_sessions_scored for row in here) // len(tables),
        }
    return halves


def _separates(half: dict) -> set[tuple[str, str]]:
    """The pairs of models this half puts in an order, by the document's rule.

    Dominance under both judges -- the same relation `_merged_table` sorts by,
    so "separates" here means exactly what "is above" means in the tables.
    """
    found = set()
    for first, second in combinations(half["systems"], 2):
        if _dominates(first, second, half["keys"], half["tables"]) or _dominates(
            second, first, half["keys"], half["tables"]
        ):
            found.add((first, second))
    return found


def _agreement(first: dict, second: dict) -> list[float]:
    """How far two halves of two views agree about the order, one rho per judge.

    Spearman through `czech_join.correlate` rather than a second implementation
    of it: that function already carries this project's rules about what a
    correlation over a flat column is worth and about how its p-value is
    computed. Imported inside the call because it is the only thing here that
    needs it and because `tools/czech_join.py` reaches into the judge module at
    import time.

    **This is the slow part of the build.** Each call permutes the models to
    get a p-value, and there are a dozen of them: the document builds in eight
    seconds without this chapter and in about a minute with it. That is what a
    chapter whose whole claim is a set of correlations costs, and the
    alternative -- a rho with no idea how easily chance produces it -- is the
    thing this document refuses everywhere else.
    """
    from czech_join import correlate

    shared = sorted(set(first["systems"]) & set(second["systems"]))
    if len(shared) < 3:
        return []
    out = []
    for judge in sorted(set(first["tables"]) & set(second["tables"])):
        left = _dominance_places(shared, first["keys"], {judge: first["tables"][judge]})
        right = _dominance_places(shared, second["keys"], {judge: second["tables"][judge]})
        found = correlate([left[name] for name in shared], [right[name] for name in shared])
        if found:
            out.append(found["rho"])
    return out


def _extra_pairs(first: dict[int, dict], second: dict[int, dict]) -> int:
    """How many model pairs the first view separates that the second does not.

    Over the models the two share, half against matching half, summed. A pair
    separated on one half and not the other still counts: it is something one
    view knows about those two models and the other does not.
    """
    count = 0
    for index in sorted(set(first) & set(second)):
        left, right = first[index], second[index]
        shared = set(left["systems"]) & set(right["systems"])
        mine = {pair for pair in _separates(left) if pair[0] in shared and pair[1] in shared}
        count += len(mine - _separates(right))
    return count


def _perspectives(rows: list[results.Row]) -> str:
    """Three views of one question, and whether any of them is spare.

    The document asks one thing three times -- is this good Czech, is it a good
    note, and what happens in the format the application really writes -- and
    it never said whether those are three answers or one answer three times. A
    reader who arrives here holding three sets of tables and no such sentence
    will average them in their head.

    Every claim is computed, the verdict included. The test for a spare view is
    printed rather than applied silently, and both halves of it can come out
    either way: a run where two views agreed about the order and one of them
    separated nothing the other did would print that instead.
    """
    latest = [row for row in results.latest(rows) if row.is_scored]
    views = [(name, tracks, _view(latest, tracks)) for name, tracks in PERSPECTIVES]
    views = [entry for entry in views if entry[2]]
    if len(views) < 2:
        return ""

    rosters = {
        name: {system for half in halves.values() for system in half["systems"]}
        for name, _tracks, halves in views
    }
    shared_all = set.intersection(*rosters.values())
    every = set.union(*rosters.values())

    blurbs = {
        SOAP_CRITERIA_TRACKS: PERSPECTIVE_CRITERIA_SOAP,
        PDSQI_TRACKS: PERSPECTIVE_QUALITY,
        DEEPSY_CRITERIA_TRACKS: PERSPECTIVE_DEEPSY,
    }

    # --- what differs -------------------------------------------------------
    said = [
        f"<h2>{html.escape(_t(PERSPECTIVES_TITLE))}</h2>",
        f"<p>{html.escape(_t(PERSPECTIVES_LEAD))}</p>",
        f"<h3>{html.escape(_t(PERSPECTIVES_DIFFER))}</h3>",
    ]
    for name, tracks, halves in views:
        line = _t(blurbs[tracks]).format(
            models=len(rosters[name]),
            notes=_grouped(sum(half["notes"] for half in halves.values())),
        )
        # Which questions one half could not be asked, where the two halves of
        # a view do not hold the same columns. Named as an absence with a
        # reason and never as a low score: the PDSQI attributes missing on the
        # real sessions are missing because a transcript may not be sent.
        if 0 in halves and 1 in halves:
            missing = set(halves[1]["keys"]) - set(halves[0]["keys"])
            if missing and tracks == PDSQI_TRACKS:
                line += " " + _t(PERSPECTIVE_QUALITY_HALVES).format(missing=len(missing))
        # The names are written lower case because `_join_words` reads them
        # inside a sentence two blocks below; here one opens a paragraph. Safe
        # to recase, unlike a model id -- `deepseek-v4-flash` is deployed under
        # that spelling and does not become `Deepseek-v4-flash` after a stop.
        title = _t(name)
        said.append(
            f"<p><strong>{html.escape(title[:1].upper() + title[1:])}.</strong> "
            f"{html.escape(line)}</p>"
        )
    said.append(
        "<p>"
        + html.escape(
            _t(PERSPECTIVES_ROSTER).format(
                shared=len(shared_all), only=len(every) - len(shared_all)
            )
        )
        + "</p>"
    )

    # --- what follows -------------------------------------------------------
    agreed: dict[tuple[str, str], list[float]] = {}
    for (first, _ft, left), (second, _st, right) in combinations(views, 2):
        rhos = [
            rho
            for index in sorted(set(left) & set(right))
            for rho in _agreement(left[index], right[index])
        ]
        if rhos:
            agreed[(first, second)] = rhos
    if agreed:
        said.append(f"<h3>{html.escape(_t(PERSPECTIVES_FOLLOWS))}</h3>")
        said.append(
            "<p>"
            + html.escape(_t(FOLLOWS_LEAD).format(comparisons=sum(map(len, agreed.values()))))
            + "</p>"
        )
        # Ordered by the weakest comparison a pair makes rather than by its
        # best one: a pair that agrees perfectly under one judge and not at all
        # under the other has not agreed, which is this document's rule
        # everywhere else.
        order = sorted(agreed, key=lambda pair: min(agreed[pair]))
        if len(order) > 1:
            worst, best = order[0], order[-1]
            said.append(
                "<p>"
                + html.escape(
                    _t(FOLLOWS_RANGE).format(
                        closest=_join_words([_t(best[0]), _t(best[1])]),
                        closest_low=_decimal(min(agreed[best]), 2),
                        closest_high=_decimal(max(agreed[best]), 2),
                        furthest=_join_words([_t(worst[0]), _t(worst[1])]),
                        furthest_low=_decimal(min(agreed[worst]), 2),
                        furthest_high=_decimal(max(agreed[worst]), 2),
                    )
                )
                + "</p>"
            )
        else:
            only = order[0]
            said.append(
                "<p>"
                + html.escape(
                    _t(FOLLOWS_ONE_PAIR).format(
                        pair=_join_words([_t(only[0]), _t(only[1])]),
                        low=_decimal(min(agreed[only]), 2),
                        high=_decimal(max(agreed[only]), 2),
                    )
                )
                + "</p>"
            )

    # --- is any one of them redundant ---------------------------------------
    said.append(f"<h3>{html.escape(_t(PERSPECTIVES_REDUNDANT))}</h3>")
    said.append(f"<p>{html.escape(_t(REDUNDANT_TEST))}</p>")

    same_order = [pair for pair, rhos in agreed.items() if all(rho >= 1.0 - 1e-9 for rho in rhos)]
    if same_order:
        said.append(
            "<p>"
            + html.escape(
                _t(REDUNDANT_ORDER_YES).format(
                    pairs=_join_words([f"{_t(a)} / {_t(b)}" for a, b in same_order])
                )
            )
            + "</p>"
        )
    elif agreed:
        said.append(
            "<p>"
            + html.escape(
                _t(REDUNDANT_ORDER_NO).format(
                    best=_decimal(max(max(rhos) for rhos in agreed.values()), 2)
                )
            )
            + "</p>"
        )

    extra = {
        (first, second): _extra_pairs(left, right)
        for first, _ft, left in views
        for second, _st, right in views
        if first != second
    }
    fewest = {
        first: min(count for (one, _other), count in extra.items() if one == first)
        for first, _tracks, _halves in views
    }
    spare = sorted(name for name, count in fewest.items() if count == 0)
    if spare:
        said.append(
            "<p>"
            + html.escape(
                _t(REDUNDANT_EXTRA_YES).format(names=_join_words([_t(name) for name in spare]))
            )
            + "</p>"
        )
    else:
        said.append(
            "<p>"
            + html.escape(
                _t(REDUNDANT_EXTRA_NO).format(
                    fewest=min(fewest.values()), most=max(fewest.values())
                )
            )
            + "</p>"
        )

    # The verdict, and it can come out either way. A view is spare only when it
    # fails both halves of the test against the SAME other view.
    dropped = next(
        (
            (one, other)
            for pair in same_order
            for one, other in (pair, pair[::-1])
            if extra.get((one, other)) == 0
        ),
        None,
    )
    if dropped:
        said.append(
            "<p>"
            + html.escape(_t(REDUNDANT_DROP).format(redundant=_t(dropped[0]), other=_t(dropped[1])))
            + "</p>"
        )
    else:
        said.append(f"<p>{html.escape(_t(REDUNDANT_KEEP_ALL))}</p>")

    # --- what keeping them costs --------------------------------------------
    # `_calls` reads the number of answers a note costs off the task, and
    # returns a dash for a track that rated notes somebody else wrote. That
    # dash is the finding in this block rather than a gap in it: the quality
    # view generated nothing.
    cost = {}
    for _name, tracks, halves in views:
        calls = [_calls(half["track"], half["notes"]) for half in halves.values()]
        cost[tracks] = (
            sum(half["notes"] for half in halves.values()),
            sum(int(call) for call in calls) if all(call.isdigit() for call in calls) else None,
        )
    soap, deepsy = cost.get(SOAP_CRITERIA_TRACKS), cost.get(DEEPSY_CRITERIA_TRACKS)
    if soap and soap[1] and deepsy and deepsy[1] and cost.get(PDSQI_TRACKS, (0, 1))[1] is None:
        said.append(f"<h3>{html.escape(_t(PERSPECTIVES_COST))}</h3>")
        said.append(
            "<p>"
            + html.escape(
                _t(COST_TEXT).format(
                    soap_calls=_grouped(soap[1]),
                    soap_notes=_grouped(soap[0]),
                    deepsy_calls=_grouped(deepsy[1]),
                    deepsy_notes=_grouped(deepsy[0]),
                )
            )
            + "</p>"
        )
    return "".join(said)


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

    **The grid of scores is gone and the verdict it supported is not.** Four
    scores a column, over an invented note nobody will ever read, is a table a
    reader cannot check anything against; what they can act on is which columns
    moved when the fault was put in front of them, and that sentence was already
    computed from the same numbers rather than written under them.
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
    if not works and not blind:
        return ""

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
        + "<p>"
        + html.escape(_t(PDSQI_CONTROL_LEAD).format(variants=len(first["variants"])))
        + "</p>"
        + verdict
        + f"<p class='dash'>{html.escape(_t(CONTROL_CAVEAT))}</p>"
    )


#: The lead the deleted grid used to caption. The count of damaged copies is
#: read from the payload rather than written, and the kinds of damage are given
#: as examples rather than as a list, so a fifth variant makes the sentence
#: incomplete instead of making it false.
PDSQI_CONTROL_LEAD = (
    "The same question has to be put to the quality instrument a different way. "
    "Several of its columns come back with the same score for every model in this "
    "document, and how many of them depends on which judge is asked. A column that "
    "never moves is either measuring something these models genuinely do not differ "
    "on or measuring nothing at all, and nothing already scored can tell those apart, "
    "because nothing already scored is a badly written note. So one was written: an "
    "invented note with no model and no session behind it, and copies of it -- "
    "{variants} of them -- each damaged in one named way, sentences put into the wrong "
    "section or a note cut off before it reaches a plan. What each copy was expected "
    "to move was written down before the judge was asked, and what follows is which "
    "columns actually moved."
)
CONTROL_WORKS = (
    "It can, and this settles the flat columns: {columns} all drop under both "
    "judges on the note built to attack them. The judge is looking. The models score "
    "the same on those columns because they write into the same dictated four-part "
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
#: The three things one cell of the control table can say. Constants rather than
#: literals inside the branch, because two of the three print only when a
#: criterion fails: written and translated in advance, so the day one does fail
#: the Czech reader is told so in Czech rather than the document falling into
#: English in the one cell that changed.
CONTROL_FOUND = "found it"
CONTROL_FALSE_ALARM = "also fires on a clean note"
CONTROL_MISSED = "did not find it"
CONTROL_CAVEAT = (
    "The damage is deliberate and extreme -- every sentence in the wrong section, "
    "a note with no plan at all. This says the instrument responds, not that it "
    "tells two ordinary notes apart. And no person has yet rated any of these "
    "notes on this instrument, so nothing here says a 5 is what a clinician would "
    "give."
)


#: What to call each note format where a control names one. The runs record
#: `soap` or `deepsy`; a reader should not have to know those are the strings
#: the tool writes.
FORMAT_NAMES = {"soap": "the SOAP notes", "deepsy": "the Deepsy notes"}


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
                cells.append(f"<td>{html.escape(_t(CONTROL_FOUND))}</td>")
            elif detected and false_alarm:
                cells.append(f"<td><strong>{html.escape(_t(CONTROL_FALSE_ALARM))}</strong></td>")
            else:
                cells.append(f"<td><strong>{html.escape(_t(CONTROL_MISSED))}</strong></td>")
        # The format as well as the judge. Four runs labelled by judge alone
        # give two rows saying `gemini-3.1-pro-preview` and two saying
        # `gpt-5.6-terra`, with nothing to say which note each read.
        who = run["judge_model"]
        # A run written before the tool could render anything else was a SOAP
        # run. Defaulting it keeps every row labelled the same way rather than
        # leaving two rows with a format and two without.
        fmt = run.get("format") or "soap"
        label = f"{who} · {_t(FORMAT_NAMES.get(fmt, fmt))}"
        rows.append(f"<tr><td>{html.escape(label)}</td>{''.join(cells)}</tr>")

    # Per format, never pooled. `calque` fires on a clean note under one judge
    # and one format only; one shared set would mark it unreliable on the SOAP
    # tables as well, where both judges answered it correctly -- which is the
    # pooling this document refuses everywhere else, arriving through a glob.
    by_format: dict[str, list[str]] = {}
    for run in runs:
        fmt = run.get("format") or "soap"
        bad = [
            key
            for key in keys
            if run["clean"].get(key) or not run["variants"].get(key, {}).get(key)
        ]
        if bad:
            by_format[fmt] = sorted(set(by_format.get(fmt, [])) | set(bad))
    unreliable = sorted({key for keys_here in by_format.values() for key in keys_here})
    named = "; ".join(
        f"{_t(FORMAT_NAMES.get(fmt, fmt))}: {', '.join(keys_here)}"
        for fmt, keys_here in sorted(by_format.items())
    )
    verdict = (
        "<div class='warn'><p><strong>"
        + html.escape(named)
        + "</strong>. "
        + html.escape(
            _t(
                "In the format named, at least one judge reports this fault in a note "
                "that does not have it, or misses it in a note that does. Read that "
                "column as a question rather than as an answer, IN THAT FORMAT ONLY -- "
                "a column can be sound on one note format and not on the other, and "
                "here one is."
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
    # Both controls under one heading. They ask the same question of the two
    # instruments -- can this column see the fault it names -- and they were
    # two chapters with a third between them.
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
        + _pdsqi_control()
    )


#: The six candidate categories, in the order the panel prints them, with the
#: heading each gets. The keys are the ones `tools/czech_graduate.py` writes.
CATEGORY_LABELS = (
    ("restatement", "Restatement"),
    ("clinical_hypothesis", "Clinical hypothesis"),
    ("client_quotation", "Client quotation"),
    ("unsupported_observation", "Unsupported observation"),
    ("verbal_expression", "Verbal expression"),
    ("declines_to_judge", "Declines to judge"),
)

CATEGORIES_LEAD = (
    "The six criteria ask whether a fault appears ANYWHERE in a note, so a longer "
    "note offers more places for one and the columns scale with length. These six "
    "ask about one sentence at a time. Each note was cut into sentences -- {units} "
    "of them across {notes} notes -- and two coders from two vendors were asked the "
    "same yes/no question about every one. A cell is the share of the ANSWERED "
    "verdicts that are yes, so a model that writes twice as much is not twice as "
    "likely to be marked."
)

#: How much of the grid the two coders actually both answered. Printed rather
#: than assumed: the lead used to claim they answered every sentence, and for two
#: notes that was not true -- the second coder returned nothing for 54 of 3367.
CATEGORIES_COVERAGE = (
    "Both coders answered {both} of the {units} sentences. The second coder "
    "returned nothing for {gap}, so those carry one reading rather than two, and "
    "the share for the models they belong to leans on the first coder."
)

CATEGORIES_GATES = (
    "Only {passed} of the {total} passed the gates that decide whether a column is "
    "possible: does it vary, does it belong to the model rather than the session, "
    "do the coders agree, is its evidence real, is it separable from length, and "
    "does it fire on a sentence written to carry it. The others are printed as "
    "description and are not measures. {failed} fall outside the 20-80% band a "
    "column needs to tell ten notes per model apart."
)

#: Gate 7, said where a reader meets the numbers it licenses. Computed from the
#: control payload rather than written, so a category that stops firing cannot
#: leave a sentence behind saying it did.
#:
#: The last clause is the part that matters and it is the part that was got
#: wrong. The gate first ran as a note-level question -- did the category appear
#: anywhere in the clean note -- and read five of six as false alarms. The clean
#: note is an ordinary therapy note, so it restates, quotes, describes speech and
#: formulates, and five of the six are in it by construction. The verdict was
#: about the stimulus, not the coders, and the number below is the unit-level one.
CATEGORIES_CONTROL = (
    "Gate 7 was run. One sentence was written for each category and planted in an "
    "invented note, and {fired} of {total} were marked on the planted sentence by "
    "both coders. Adding that one sentence changed {moved} of the {compared} "
    "verdicts on the sentences around it, so a coder is reading one sentence at a "
    "time rather than the note it sits in. The note the variants are built from is "
    "an ordinary therapy note and carries five of the six categories itself, which "
    "is why there is no note-level negative control here and why none of that is a "
    "false alarm."
)

#: The overlap gate 7 found, printed because it is the one it was built to look
#: for. `restatement` and `clinical_hypothesis` were written as near-mirrors --
#: the same content, once reported and once interpreted -- and a category firing
#: on both would mean the pair is not being separated.
CATEGORIES_OVERLAP = (
    "Two pairs share a planted sentence: {pairs}. Both are overlaps the codebook "
    "declares, and the pair that had to stay apart did: nothing marked as "
    "restatement was also marked as a clinical hypothesis."
)

CATEGORIES_CAVEAT = (
    "No person has read these notes as a clinician. Two models agreeing is "
    "evidence that a distinction is stable and codeable, and no evidence at all "
    "that it matters. Nothing here says a higher number is worse."
)

CATEGORIES_SOURCE = (
    "Source: local/czech-graduation-{track}.json, from local/czech-codes.jsonl. "
    "Coders gemini-3.1-pro-preview and deepseek-v4-flash, prompt czech-open-v1, "
    "temperature 0. The row order is the one the PDSQI-9 table above prints."
)

CATEGORIES_THIN = "A model with fewer than ten notes is marked: its share rests on less."

#: What a cell says when the coders never answered for that model. An empty cell
#: would read as zero, which is the one thing it must not.
CATEGORY_UNANSWERED = "not answered"


def _percent(part: int, whole: int) -> int:
    """A share as a whole percent, rounded half-up.

    Python's `round` is banker's rounding, which sends an exact half to the even
    neighbour: 41.5 became 42 and 4.5 became 4 in the same table row, so a reader
    checking either by hand disagreed with one of them. Half-up is the rule a
    reader applies, and applying two different rules in one row is worse than
    applying the less principled one consistently.
    """
    return int(Decimal(100 * part) / Decimal(whole) + Decimal("0.5")) if whole else 0


#: Why there are two corpora at all, said once above both tables. It is the
#: sentence a reader needs before the second table means anything: without it a
#: second set of numbers looks like a repeat rather than the control it is.
CATEGORIES_WHY_TWO = (
    "There are two corpora so that a difference can be told apart from its cause. "
    "The same eleven models wrote from real sessions with one client and from "
    "public counselling conversations translated into Czech. A category that "
    "behaves the same on both is telling you about the models. One that behaves "
    "differently is telling you about the material, and this chapter is where "
    "that shows."
)

#: What the second table is, and the two readings its result allows. Printed
#: whichever way the numbers fall, because the reading is not a function of
#: whether the result was the hoped-for one.
CATEGORIES_SECOND = (
    "The same six questions, on notes written from ten public counselling "
    "conversations translated into Czech -- {units} sentences across {notes} "
    "notes. These transcripts are a seventh the length of a real session, they "
    "are motivational interviewing about substance use rather than therapy with "
    "one client, and somebody else transcribed them. A category that weakens "
    "here may be weakening because of any of those, or because it was partly "
    "chance on the other half. These numbers cannot tell those apart."
)

#: Said when a category passes on one corpus and not the other, with the two
#: numbers that differ, because "it passed" and "it passed on one half" are
#: different claims and only the second one is true.
CATEGORIES_SPLIT = (
    "{name} passes every decided gate on the real sessions and fails on the "
    "translated ones: the share of its variation belonging to the model rather "
    "than to the session falls from {high} to {low}, where a column needs 0.40 "
    "and three times the session's share. It is a measure of the real half, and "
    "saying it is a measure would be saying more than was found."
)


def _categories_table(rows: list[results.Row], track: str, lead: str) -> str:
    """One corpus's table of the six categories.

    A separate instrument from the six criteria and from PDSQI-9, and it is here
    rather than in a file of its own because a reader who has just been told the
    criteria are entangled with length should see the measure that is not, on the
    same models, without changing document.

    It returns "" when the payload is absent, like every other panel that reads
    one: a briefing built on a machine that has not run the coder panel should be
    a briefing without this chapter, not one with an empty heading.
    """
    payload = REPO / "local" / f"czech-graduation-{track}.json"
    if not payload.is_file():
        return ""
    data = json.loads(payload.read_text(encoding="utf-8"))
    by_model = data.get("by_model") or {}
    graded = data.get("categories") or {}
    if not by_model or not graded:
        return ""

    keys = [key for key, _ in CATEGORY_LABELS if key in by_model]
    if not keys:
        return ""

    # The same row order the PDSQI table above prints, recomputed rather than
    # copied: two orders that drift apart are worse than one that is derived.
    track = results.TRACK_CZECH_REAL_PDSQI
    groups = [
        [row for row in rows if row.track == track and row.judge_model == judge]
        for judge in sorted({row.judge_model for row in rows if row.track == track})
    ]
    order = list(by_model[keys[0]])
    # `groups` is empty when no row carries the PDSQI track, and `all([])` is
    # True -- which took `set.intersection()` with no arguments and crashed the
    # whole briefing. The panel is meant to degrade to the alphabetical order
    # there, not to take the document down with it.
    if groups and all(groups):
        by_judge = {g[0].judge_model or "?": {r.system_id: r for r in g} for g in groups}
        systems = sorted(set.intersection(*(set(v) for v in by_judge.values())))
        varying = _varying(track, [r for g in groups for r in g])
        tables = {
            judge: {s: by_judge[judge][s].metrics.headline for s in systems} for judge in by_judge
        }
        places = _dominance_places(systems, varying or [k for k, _ in COLUMNS[track]], tables)

        def index_of(system: str) -> float:
            found = [
                _rank_of(track, by_judge[judge][system], varying)
                for judge in by_judge
                if system in by_judge[judge]
            ]
            return sum(found) / len(found) if found else -1.0

        order = sorted(systems, key=lambda s: (places[s], -index_of(s), s))

    thin = False
    body = []
    for system in order:
        cells = []
        for key in keys:
            entry = by_model[key].get(system)
            if entry is None or entry["rate"] is None:
                cells.append(f"<td>{_t(CATEGORY_UNANSWERED)}</td>")
                continue
            value = f"{_percent(entry['present'], entry['verdicts'])}&nbsp;%"
            cells.append(
                f"<td><strong>{value}</strong></td>"
                if key == "restatement"
                else f"<td>{value}</td>"
            )
        first = by_model[keys[0]].get(system) or {}
        notes = first.get("notes")
        sentences = first.get("sentences")
        mark = ""
        if notes is not None and notes < 10:
            thin = True
            mark = " *"
        body.append(
            f"<tr><td>{html.escape(system)}</td>{''.join(cells)}"
            f"<td>{sentences if sentences is not None else ''}</td>"
            f"<td>{notes if notes is not None else ''}{mark}</td></tr>"
        )

    head = "".join(
        f"<th>{html.escape(_t(label))}</th>" for key, label in CATEGORY_LABELS if key in by_model
    )
    units = sum((by_model[keys[0]][s] or {}).get("sentences") or 0 for s in by_model[keys[0]])
    # How many of those sentences carry a reading from every coder. A share
    # pooled over coders is not wrong where one of them is silent, but it is
    # weighted, and a reader is owed the number rather than the word "two".
    both = sum((by_model[keys[0]][s] or {}).get("both_coders") or 0 for s in by_model[keys[0]])
    notes_total = sum((by_model[keys[0]][s] or {}).get("notes") or 0 for s in by_model[keys[0]])
    passed = [k for k in keys if str(graded.get(k, {}).get("verdict", "")).startswith("would")]
    failed = [
        _t(label)
        for key, label in CATEGORY_LABELS
        if key in graded and graded[key]["gates"]["1_varies"]["passed"] is False
    ]

    return (
        f"<p>{html.escape(_t(lead).format(units=units, notes=notes_total))}</p>"
        + f"<table><thead><tr><th>{_t('Model')}</th>{head}"
        + f"<th>{_t('Sentences')}</th><th>{_t('Notes')}</th></tr></thead>"
        + f"<tbody>{''.join(body)}</tbody></table>"
        + (f"<p class='note'>{html.escape(_t(CATEGORIES_THIN))}</p>" if thin else "")
        + (
            "<p class='note'>"
            + html.escape(_t(CATEGORIES_COVERAGE).format(both=both, units=units, gap=units - both))
            + "</p>"
            if both and both < units
            else ""
        )
        + "<p>"
        + html.escape(
            _t(CATEGORIES_GATES).format(
                passed=len(passed), total=len(keys), failed=", ".join(failed) or _t("None")
            )
        )
        + "</p>"
        + f"<div class='warn'><p>{html.escape(_t(CATEGORIES_CAVEAT))}</p></div>"
        + f"<p class='note'>{html.escape(_t(CATEGORIES_SOURCE).format(track=track))}</p>"
    )


def _categories(rows: list[results.Row]) -> str:
    """Both corpora, one table each, with the reason there are two of them.

    Never one table over both. The two halves differ by a factor of seven in
    transcript length, in topic and in who transcribed them, and this repository
    refuses to pool them everywhere else. A category that behaves differently on
    the two is the finding the second corpus exists to produce, and pooling would
    average it away.

    The split verdict is computed, not written: whether a category passes on one
    half and not the other is read off the two payloads, so it cannot disagree
    with the tables under it.
    """
    real = _categories_table(rows, results.TRACK_CZECH_REAL, CATEGORIES_LEAD)
    if not real:
        return ""
    translated = _categories_table(rows, results.TRACK_CZECH_TRANSLATED, CATEGORIES_SECOND)

    split = ""
    if translated:
        graded = {
            track: (
                json.loads(
                    (REPO / "local" / f"czech-graduation-{track}.json").read_text(encoding="utf-8")
                )
                or {}
            ).get("categories")
            or {}
            for track in (results.TRACK_CZECH_REAL, results.TRACK_CZECH_TRANSLATED)
        }
        said = []
        for key, label in CATEGORY_LABELS:
            here = graded[results.TRACK_CZECH_REAL].get(key) or {}
            there = graded[results.TRACK_CZECH_TRANSLATED].get(key) or {}
            if not here or not there:
                continue
            if str(here.get("verdict", "")).startswith("would") and not str(
                there.get("verdict", "")
            ).startswith("would"):
                said.append(
                    _t(CATEGORIES_SPLIT).format(
                        name=_t(label),
                        high=_decimal((here["variance"] or {}).get("model", 0), 2),
                        low=_decimal((there["variance"] or {}).get("model", 0), 2),
                    )
                )
        if said:
            split = "<div class='warn'><p>" + html.escape(" ".join(said)) + "</p></div>"

    return (
        f"<h2>{_t('What the models write, one sentence at a time')}</h2>"
        + f"<p>{html.escape(_t(CATEGORIES_WHY_TWO))}</p>"
        + f"<h3>{_t('Czech · ten real sessions, one client')}</h3>"
        + real
        + (
            f"<h3>{_t('Czech · AnnoMI conversations, translated')}</h3>" + translated
            if translated
            else ""
        )
        + split
        + _planted_control()
    )


def _planted_control() -> str:
    """What gate 7 found, drawn once for both corpora because it is about neither.

    Its stimulus is an invented note belonging to no session and no model, so
    the answer is a fact about the instrument and would be the same sentence
    printed twice if it went under each table.

    Returns "" when the control has not been run. The chapter then says nothing
    about gate 7 rather than saying it is unmeasured in a document whose tables
    already print its verdict, and the graduation payload keeps its own NOT RUN.
    """
    payload = REPO / "local" / "czech-category-control.json"
    if not payload.is_file():
        return ""
    data = json.loads(payload.read_text(encoding="utf-8")) or {}
    verdicts = data.get("verdicts") or {}
    stability = data.get("stability") or {}
    if not verdicts or not stability:
        return ""

    fired = sum(1 for by in verdicts.values() if by and all(c["found_it"] for c in by.values()))
    # The coder that moved most, not the average of the two: the claim is that
    # no coder reads a sentence by its neighbours, and an average would let one
    # that does hide behind one that does not.
    worst = max(
        (s for s in stability.values() if s.get("verdicts_compared")),
        key=lambda s: s["verdicts_changed"],
        default=None,
    )
    if worst is None:
        return ""

    labels = dict(CATEGORY_LABELS)
    pairs = sorted(
        {
            " + ".join(sorted((_t(labels.get(name, name)), _t(labels.get(other, other)))))
            for name, by in verdicts.items()
            for coder in by.values()
            for other in coder.get("also_fired_on_it", ())
        }
    )
    said = _t(CATEGORIES_CONTROL).format(
        fired=fired,
        total=len(verdicts),
        moved=worst["verdicts_changed"],
        compared=worst["verdicts_compared"],
    )
    if pairs:
        said += " " + _t(CATEGORIES_OVERLAP).format(pairs="; ".join(pairs))
    return f"<p>{html.escape(said)}</p>"


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


@functools.cache
def _figure_data():
    """Everything the four figures read, opened once for the whole run.

    `czech_figures.Data.load` reads the local rows and three payloads off disk.
    Four figures in two language builds is eight passes over the same files,
    and none of it can change while one document is being written.
    """
    # Imported at the moment of use rather than at the top of this file, so
    # that a checkout without the figures' payloads still builds its tables.
    from czech_figures import Data

    return Data.load()


def _figure(name: str, caption: str) -> str:
    """One figure, inline, with the caption this document gives it.

    Empty when the payload behind the figure is not in this checkout, which is
    what every other payload-backed block here does: a document built from
    fixture rows draws its tables and simply has no picture.

    The SVG carries its own title, subtitle and source line, so the caption
    under it says what to look at instead of repeating them.
    """
    from czech_figures import CZECH_FIGURES

    # `_t` is handed to the figure rather than fetched by it. This module is run
    # as a script, so it is `__main__`; a figure that did `from czech_brief
    # import _t` got a second copy of this module whose `LANG` was still "en",
    # and every chart in the Czech document was drawn in English.
    drawn = CZECH_FIGURES[name](_figure_data(), _t)
    if not drawn:
        return ""
    return f"<figure>{drawn}<figcaption>{html.escape(_t(caption))}</figcaption></figure>"


def _track_block(track: str, ordered: list[list[results.Row]], *, lead: bool, level: int) -> str:
    """One track: its heading, the sentence saying what it is, and its table.

    `level` is 2 where the track is a chapter of its own and 3 where it is half
    of one. The two Deepsy halves share a chapter, and a second `<h2>` inside it
    would tell a reader the chapter had ended and another had begun.

    One table a track, with both judges in every cell, when there are two.
    Twelve tables for six tracks made a reader flip between two grids to
    compare one model, and the judges' disagreement -- the only control this
    track has -- was the thing that flipping hid.
    """
    tag = f"h{level}"
    out = [
        f"<{tag}>{html.escape(_t(TRACK_TITLES.get(track, track)))}</{tag}>"
        f"<p class='sub'>"
        f"{html.escape(re.sub(r'[*]{2}', '', _t(TRACK_BLURBS.get(track, ''))))}</p>"
    ]
    if len(ordered) > 1:
        first = ordered[0][0]
        # Per judge, not summed over them. Both judges read the SAME notes, so
        # adding their rows counted every note once per judge and every header
        # said twice what exists -- "208 notes" over a corpus of 110, against a
        # true 104. The deleted "what it took" table had it right and this did
        # not; the three-views chapter counts the same notes the same way.
        notes = sum(row.n_sessions_scored for group in ordered for row in group) // len(ordered)
        out.append(
            f"<p class='sub'>{len(ordered[0])} {_t('models')}, {notes} {_t('notes')}, "
            f"{_t('rubric')} {html.escape(first.judge_prompt_version)}</p>"
            + _merged_table(track, ordered, lead=lead)
        )
    else:
        for drawn in ordered:
            first = drawn[0]
            notes = sum(row.n_sessions_scored for row in drawn)
            out.append(
                f"<p class='sub'><strong>{_t('Judged by')} "
                f"{html.escape(first.judge_model or 'unknown')}</strong> &middot; "
                f"{len(drawn)} {_t('models')}, {notes} {_t('notes')}, "
                f"{_t('rubric')} {html.escape(first.judge_prompt_version)}</p>"
                + _table(track, drawn)
            )
    return "".join(out)


#: The Deepsy chapter's own prose. A reader outside this project has never
#: heard the word, and the two Deepsy tables used to arrive under two headings
#: that assumed it -- "Deepsy format · ten real sessions" -- with the one
#: paragraph explaining the format four sections further on.
DEEPSY_TITLE = "The note format the Deepsy application actually writes"
DEEPSY_WHAT = (
    "Every table so far has been about SOAP -- subjective, objective, assessment, "
    "plan. That is the format TN-Eval published, and reusing it is what lets the "
    "English numbers be read beside the Czech ones. It is not the format the Deepsy "
    "application writes. Deepsy asks the model for a note in named sections, one call "
    "per section, in its own words; {sections} of those sections are measured here, "
    "and they are not a preference. They are the ones that have a SOAP counterpart: "
    "the data section is SOAP's subjective and objective together, the "
    "hypotheses section is its assessment, and the plan section is its plan. The "
    "application writes more sections than these, and the rest either work from the "
    "previous note rather than from a transcript or need data this benchmark does "
    "not supply."
)
#: The two differences that show up in every number below, so they are stated
#: before the numbers rather than after them. The ceiling is read from the
#: payload that measured compliance with it: it is the application's figure and
#: not ours, and a run against a changed prompt would change it.
DEEPSY_CEILING = (
    "Two things this format does that SOAP does not. It sets a ceiling of {limit} "
    "words a section, which its own prompt calls invalid to exceed. And it asks for "
    "the answer as structured data rather than as prose, so a reply that does not "
    "parse is a failure rather than a poor note. Both are the application's "
    "decisions, reproduced from its own prompt files rather than retyped."
)
DEEPSY_WHY = (
    "That is why this chapter is here, and it is worth reading before the tables "
    "above are taken too literally. SOAP is not what a Czech psychologist writes. "
    "The prompt behind every table so far is a translation of TN-Eval's, so that the "
    "task is the same task in another language, and it reproduces no Czech "
    "documentation standard because there is none to reproduce -- which makes those "
    "notes formally artificial, equally so for every model, and that equality is "
    "what keeps the comparison between them fair rather than what makes them less "
    "artificial. Here the same models write from the same sessions and the only "
    "thing that changes is the shape they were asked for. The figure below shows "
    "what came of that, and the paragraph under it names the one thing the "
    "comparison cannot hold still."
)
#: What this chapter does not answer, said in the chapter rather than in a
#: method footnote three pages later. `SCALE_NO_PDSQI` follows it and carries
#: the count.
DEEPSY_NO_QUALITY = (
    "This chapter says nothing about whether a Deepsy note is a good note. The six "
    "criteria ask whether the Czech is right, and the instrument that asks whether a "
    "note is worth filing was never put to these."
)
#: What replaces `DEEPSY_NO_QUALITY` once the quality tables exist. It does not
#: state a result: the result is two tables and a conclusion sentence, and a
#: third statement of it here would be a fourth place to keep in step.
DEEPSY_HAS_QUALITY = (
    "This chapter says nothing about whether a Deepsy note is a good note, but the "
    "document now does."
)
DEEPSY_HAS_QUALITY_WHERE = (
    "The six criteria here ask whether the Czech is right. PDSQI-9, which asks whether "
    "a note is worth filing, was put to these same notes under both judges and has two "
    "tables of its own further down. On the real half it answers on six of its eight "
    "attributes rather than all eight, because `accurate` and `thorough` need the "
    "session and the real sessions never leave e-INFRA."
)
DEEPSY_FIGURE_CAPTION = (
    "Four panels rather than one average: the comparison was made on both halves of "
    "the corpus and under both judges, and that all four go the same way is the "
    "finding. Read the slope of the lines; which line is which model is in the "
    "tables below."
)


def _deepsy_chapter(
    rows: list[results.Row],
    entries: list[tuple[str, list[list[results.Row]], set[str]]],
    figures: dict[str, str],
    shared_judges: list[str],
) -> str:
    """Both Deepsy halves under one heading, with the explanation they needed.

    They were two chapters, and the comparison that gives them their point --
    the same models and sessions in two formats -- was a third, four sections
    later. A reader met "Deepsy format · ten real sessions, one client" as a
    heading with no sentence anywhere above it saying what Deepsy is.

    The order is the order a reader needs it in: what the format is, why it is
    in this document, what this chapter cannot answer, the picture, the table
    the picture draws, then the two tables everything else came from, and the
    box saying what they came to.
    """
    limit = ((_payload("czech-length.json").get("instructions") or {}).get("deepsy") or {}).get(
        "limit_words"
    )
    said = [_t(DEEPSY_WHAT).format(sections=len(deepsy_task.SECTIONS))]
    if limit:
        said.append(_t(DEEPSY_CEILING).format(limit=_grouped(int(limit))))
    said.append(_t(DEEPSY_WHY))

    out = [f"<h2>{html.escape(_t(DEEPSY_TITLE))}</h2>"]
    out += [f"<p>{html.escape(text)}</p>" for text in said]
    # Printed only while it is true. Both sentences say the quality instrument
    # was never put to a Deepsy note, and on 2026-09-01 it was -- over both
    # halves and under both judges. A document that names a gap it has since
    # closed is worse than one that never named it: the reader takes the
    # sentence as current and stops looking for the tables.
    asked = any(row.track in DEEPSY_PDSQI_TRACKS and row.is_scored for row in rows)
    if not asked:
        out.append(
            "<div class='warn'><p><strong>"
            + html.escape(_t(DEEPSY_NO_QUALITY))
            + "</strong> "
            + html.escape(_t(SCALE_NO_PDSQI).format(**figures))
            + "</p></div>"
        )
    else:
        out.append(
            "<div class='warn'><p><strong>"
            + html.escape(_t(DEEPSY_HAS_QUALITY))
            + "</strong> "
            + html.escape(_t(DEEPSY_HAS_QUALITY_WHERE))
            + "</p></div>"
        )
    out.append(_figure("formats", DEEPSY_FIGURE_CAPTION))
    out.append(_formats())
    for track, ordered, _withdrawn in entries:
        out.append(_track_block(track, ordered, lead=not shared_judges, level=3))
    out.append(_box_c(rows))
    return "".join(out)


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

    # Which tables will be drawn, decided before any of them is. The caption
    # above them names the judges every cell holds and the scales the columns
    # run on, and neither can be written until it is known what is on the page:
    # a run with one judge must not be handed a sentence about two.
    plan: list[tuple[str, list[list[results.Row]], set[str]]] = []
    for track in results.LOCAL_TRACKS:
        groups = {key: drawn for key, drawn in by_group.items() if drawn[0].track == track}
        if not groups:
            continue
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
        plan.append((track, ordered, withdrawn))

    # The judges named in the shared caption, and only when every merged table
    # holds the same pair. Two tracks judged by different pairs would make one
    # sentence naming a pair false of half the page, so then nothing is named
    # and the disagreement mark speaks for itself.
    pairs = {
        tuple(group[0].judge_model or "?" for group in ordered)
        for _track, ordered, _withdrawn in plan
        if len(ordered) > 1
    }
    shared_judges = sorted(next(iter(pairs))) if len(pairs) == 1 else []

    drawn_tracks = [track for track, _ordered, _withdrawn in plan]
    banded = any(
        _banded(_band_numbers(track), [group[0].judge_model or "?"], [r.system_id for r in group])
        for track, ordered, _withdrawn in plan
        for group in ordered
    )
    # Said once, before the tables they govern, rather than under each of them.
    # Four copies of one caveat is what teaches a reader to skip the boxes --
    # including the ones that are genuinely different.
    two_judges = any(len(ordered) > 1 for _track, ordered, _withdrawn in plan)
    withdrawn_from: dict[str, set[str]] = {}
    for track, _ordered, withdrawn in plan:
        for version in withdrawn:
            withdrawn_from.setdefault(version, set()).add(_t(TRACK_TITLES.get(track, track)))

    # Both dictionaries, because a caveat's figures come from two places: the
    # corpora it describes and the run that produced the notes. Neither is
    # typed into the sentence -- a caveat carrying a stale number is worse than
    # no caveat, because it is the paragraph a reader trusts. Read here rather
    # than at the end because the Deepsy chapter needs one of them too.
    figures = {**_corpus_sizes(), **_written_figures(rows)}

    sections = []
    if plan:
        # What the tables were measured on, and what their columns mean, above
        # the tables rather than under them. Both used to sit below all six: a
        # reader met an eight-column grid of decimals and could find out what
        # the headings meant only after having already read them. Written open,
        # always -- a closed toggle prints to PDF as a bare heading with its
        # contents gone.
        sections.append(
            f"<h2>{_t('What was measured, and on what')}</h2>"
            + _corpus([row for _t2, ordered, _w in plan for group in ordered for row in group])
            + _column_definitions(drawn_tracks)
        )
        sections.append(
            f"<h2>{_t('How to read the tables')}</h2>"
            + _how_to_read(drawn_tracks, shared_judges, banded=banded)
        )
    # The two Deepsy halves are one chapter and every other track is one of its
    # own. They are drawn where the second of them falls, which is last, so the
    # order of the document does not depend on this branch.
    deepsy_plan = [entry for entry in plan if entry[0] in DEEPSY_CRITERIA_TRACKS]
    # The box that closes a chapter, drawn under the last table in it. Keyed on
    # the last track actually drawn rather than on the one that comes last by
    # design: a run that scored only half a chapter still gets its conclusion,
    # and the box itself decides what it can say with one half.
    closing = {}
    for chapter, box in ((SOAP_CRITERIA_TRACKS, _box_a), (PDSQI_TRACKS, _box_b)):
        drawn_here = [track for track in drawn_tracks if track in chapter]
        if drawn_here:
            closing[drawn_here[-1]] = box
    for track, ordered, _withdrawn in plan:
        if track in DEEPSY_CRITERIA_TRACKS:
            if track == deepsy_plan[-1][0]:
                sections.append(_deepsy_chapter(rows, deepsy_plan, figures, shared_judges))
            continue
        sections.append(_track_block(track, ordered, lead=not shared_judges, level=2))
        if track in closing:
            sections.append(closing[track](rows))

    # --- the caveats and the definitions, once each -------------------------
    # How far a band boundary can be trusted, under the tables that draw one.
    # It is the only sentence in the document giving that figure, so the Band
    # column would otherwise claim a precision the payload behind it denies.
    once = [_band_unresolved(drawn_tracks)] if banded else []
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
    sections.extend(once)

    return f"""<!doctype html>
<html lang="{LANG}"><head><meta charset="utf-8">
<title>{_t(TITLE)}</title><style>{STYLE}</style></head><body>
<h1>{_t(HEADLINE)}</h1>
<p class="sub">{_t(SUBTITLE)}</p>

<p>{_intro(rows)}</p>
<p>{_t(INTRO_SECOND)}</p>

{_glossary()}

<div class="summary">{_conclusion(rows)}</div>

<div class="warn"><p><strong>{_t(NOT_PUBLIC)}</strong> {_t(NOT_PUBLIC_WHY)}</p></div>

{"".join(sections)}

{_criteria_prose(rows)}



{_controls()}

{_categories(rows)}

{_outside()}

{_length()}

{_perspectives(rows)}

<h2>{_t("What these numbers cannot be used for")}</h2>
{_limits(figures)}

<h2>{_t("How it was measured")}</h2>
<p>{_t(METHOD_CORPORA).format(**figures)}</p>
<p>{_t(METHOD_WHERE)}</p>
<p><strong>{_t("No judge is ever shown a real session.")}</strong> {_t(METHOD_BOUNDARY)}</p>
<p>{_t(METHOD_CRITERIA)}</p>
<p>{_t(METHOD_PDSQI)}</p>

{_closing(rows, drawn_tracks)}

<footer>{_t(FOOTER)}</footer>
</body></html>
"""


def main(argv: list[str] | None = None) -> int:
    global LANG

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=None)
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
    target = args.target or default_target(LANG)

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

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build(rows), encoding="utf-8")
    scored = sum(1 for row in results.latest(rows) if row.is_scored)
    print(f"wrote {target}  ({scored} scored row(s) from {len(rows)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
