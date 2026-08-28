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
from tnb.report import COLUMNS, MEASURE_TABLES, TRACK_BLURBS, TRACK_TITLES
from tnb.scoring import czech as czech_scorer

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
dl { margin: .6rem 0 0; }
dt { font-weight: 600; font-family: "Source Sans 3", system-ui, sans-serif;
     font-size: .85rem; margin-top: .7rem; }
dd { margin: .1rem 0 0; color: var(--muted); font-size: .9rem; }
.warn { border-left: 3px solid var(--accent); padding: .1rem 0 .1rem .9rem; margin: 1rem 0; }
.warn p { margin: .4rem 0; }
footer { margin-top: 3rem; padding-top: .8rem; border-top: 1px solid var(--rule);
         color: var(--muted); font-size: .8rem; }
code { font-family: ui-monospace, monospace; font-size: .9em; }
@media print {
  body { max-width: none; padding: 0; font-size: 10pt; }
  h2 { break-after: avoid; } table { break-inside: auto; }
  tr { break-inside: avoid; } .warn { break-inside: avoid; }
}
"""

#: The document's own sentences, named so they can be translated. Inlined in
#: the template they could not be: an f-string cannot carry a call around a
#: paragraph without becoming unreadable, and a paragraph that cannot be wrapped
#: is a paragraph that stays English.
TITLE = "Czech note quality"
HEADLINE = "Does an English leaderboard say anything about clinical Czech?"
SUBTITLE = "therapy-note-bench \u00b7 Czech track \u00b7 measured, not published"
INTRO = (
    "The benchmark this belongs to scores model-written psychotherapy notes on two "
    "English corpora. A model's standing there is a statement about English. This "
    "track asks whether it carries over: the same models write notes in Czech, from "
    "real sessions and from translated ones, and two instruments are asked about the "
    "result. Seven yes/no criteria ask whether the Czech is right. PDSQI-9, a "
    "published instrument, asks whether the note is any good -- because the criteria "
    "cannot: a flawless Czech sentence about nothing passes all seven."
)
NOT_PUBLIC = "These numbers are not on the public site and this document is not a publication."
NOT_PUBLIC_WHY = (
    "They were measured from confidential clinical material and the decision to "
    "publish anything from them has not been made. The transcripts were de-identified "
    "before any model saw them, and no transcript text appears in this document or in "
    "any file it was built from."
)
METHOD_CORPORA = (
    "Two halves, both read only from a directory that is not in version control. "
    "Every model wrote a note from every transcript, on e-INFRA."
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
    "every one of the seven asks about the absence of a fault and an empty note would "
    "pass all seven."
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
        "Every model wrote a note from every transcript, which is what makes the "
        "comparison between models valid at all -- the first attempt gave each model a "
        "different session and could not tell a worse model from a harder session. But "
        "ten notes per model is a small number, and the real half is one client with "
        "one therapist. Read the ordering, not the gaps between neighbours.",
    ),
    (
        "The two halves differ by more than language, and mostly by size",
        "A real session runs to a median of 5,266 words and 113 turns; a translated "
        "AnnoMI conversation to 699 words and 52 turns. Seven times the material, so "
        "the summarising is a harder task before any question of Czech arises. They "
        "differ in topic too -- AnnoMI is motivational interviewing about substance "
        "use and the real sessions are not -- and in who transcribed them. A model "
        "that does worse on one half may be doing worse at length, at motivational "
        "interviewing, or at Czech, and these numbers cannot separate the three.",
    ),
    (
        "Nothing here says whether a note is true",
        "The criteria ask about the Czech and nothing else. A fluent, correctly typeset, "
        "entirely invented note passes all seven. Whether the note says what the session "
        "contained is a different measurement and this is not it.",
    ),
    (
        "The instrument has never been checked against a person",
        "These seven criteria are this repository's own, because no published Czech "
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
    """
    columns = COLUMNS[track]
    measures = MEASURE_TABLES[track]
    head = "".join(f"<th>{html.escape(_t(measures[key]['label']))}</th>" for key, _ in columns)
    body, thin = [], []
    for row in sorted(rows, key=lambda r: r.system_id):
        complete = row.n_sessions_scored - row.n_sessions_partial
        cells = "".join(
            f"<td>{_fmt(row.metrics.headline.get(key), digits)}</td>" for key, digits in columns
        )
        if row.n_sessions_partial:
            count = f"<strong>{complete}</strong> {_t('of')} {row.n_sessions_scored}"
            if complete < THIN * row.n_sessions_scored:
                thin.append(f"{row.system_id} ({complete} {_t('of')} {row.n_sessions_scored})")
        else:
            count = str(complete)
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
        f"<table><thead><tr><th>{_t('Model')}</th>"
        f"<th>{_t('Notes in the mean')}</th>"
        f"{head}</tr></thead><tbody>{''.join(body)}</tbody></table>{warning}"
    )


def _definitions(track: str) -> str:
    measures = MEASURE_TABLES[track]
    items = []
    for key, _digits in COLUMNS[track]:
        measure = measures[key]
        items.append(
            f"<dt>{html.escape(_t(measure['label']))} "
            f"<span class='dash'>({measure['scale']})</span></dt>"
            f"<dd>{html.escape(_t(measure['definition']))}</dd>"
        )
    return "<dl>" + "".join(items) + "</dl>"


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


#: What a column catches once it has met a hundred real notes, in words.
#:
#: The verdict beside each one in the table is computed from the rows; this is
#: the half a computation cannot supply. Both halves are on the page because a
#: reader handed "0.67" without either will supply their own reading, and theirs
#: will be more generous than the evidence.
WHAT_IT_CATCHES = {
    "diacritics": (
        "Reliable. The two judges answered the same way on 79% of notes and one "
        "native speaker agreed with them on 18 of 20."
    ),
    "calque": (
        "The weakest column here, and it should be read as a flag rather than a "
        "score. The two judges agree on only 67% of notes -- the lowest of the "
        "seven -- and a native speaker agreed with them on 11 of 20 and 7 of 20. "
        "Whether a Czech phrase is a literal translation from English is a "
        "judgement people make differently, and these numbers show that rather "
        "than hiding it."
    ),
    "untranslated": (
        "Reliable, and the fault it catches is unambiguous: an English term sitting "
        "in a Czech sentence. Judges agree on 87% of notes, the native speaker on "
        "19 of 20."
    ),
    "agreement": (
        "Catches real grammatical faults, but the two judges answer differently on "
        "a quarter of notes. A gap of one or two notes between models is inside "
        "that noise."
    ),
    "register": (
        "Catches colloquial words where clinical ones belong. Judges agree on 75% "
        "of notes; the native speaker agreed with the first judge on 19 of 20 and "
        "with the second on 15."
    ),
    "quotes": (
        "Exact. It is not a judgement at all any more -- the characters in the note "
        "are counted. It became a count after a native speaker and a judge disagreed "
        "on nearly half the notes and neither was wrong: the question named only the "
        "straight double mark, and 45 of the 75 notes that quote anything use an "
        "apostrophe instead. The question now names both."
    ),
    "nonword": (
        "The strongest agreement with a person of the seven: 20 of 20 against the "
        "first judge, 17 against the second."
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


def _catch(key: str) -> str:
    """What a column catches, in this run's language, or nothing.

    A column with no sentence written for it renders an empty cell rather than
    raising: the verdict beside it is still counted and still worth reading, and
    a missing sentence is a gap in the prose rather than in the measurement.
    """
    written = WHAT_IT_CATCHES.get(key, "")
    return _t(written) if written else ""


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
            f"<td>{words[middle]:,}</td><td>{words[0]:,}&ndash;{words[-1]:,}</td>"
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


def _verdicts(rows: list[results.Row]) -> str:
    """Which columns tell the models apart, counted rather than asserted.

    The tie count is the largest group of systems printing the same value, taken
    on whichever judge ties worst -- `concordance.MeasureAgreement.rankable`'s
    rule, applied here so the briefing states it in the same terms the page
    does. A column on which most systems are indistinguishable cannot rank them,
    whatever the rest of the table does.
    """
    latest = [row for row in results.latest(rows) if row.is_scored]
    blocks = []
    for track in results.LOCAL_TRACKS:
        here = [row for row in latest if row.track == track]
        if not here:
            continue
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
                f"<td class='sub'>{html.escape(_catch(key))}</td></tr>"
            )
        if lines:
            blocks.append(
                f"<h3>{html.escape(_t(TRACK_TITLES.get(track, track)))}</h3>"
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
                "because no arithmetic supplies it."
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


def _bands() -> str:
    """The models grouped, because ordering eleven of them over ten notes is
    mostly ordering noise.

    A ranking invites the one reading it cannot support -- is the fourth better
    than the fifth -- and no caveat beside it declines the invitation. Bands
    say the same measurement without making the offer: within a band nothing
    separates the models, between bands something does.

    A band starts where the gap from the band's best exceeds what resampling
    the sessions can rule out, so the width of a band is the measurement's own
    resolution rather than a choice about presentation.
    """
    path = REPO / "local" / "czech-variance.json"
    if not path.exists():
        return ""
    data = json.loads(path.read_text(encoding="utf-8")).get("bands") or {}
    if not data:
        return ""

    blocks = []
    for track in results.LOCAL_TRACKS:
        judges = data.get(track) or {}
        if not judges:
            continue
        for judge_model in sorted(judges):
            grouped = judges[judge_model]
            rows = "".join(
                f"<tr><td>{number}</td>"
                f"<td>{band['high']:.2f}&ndash;{band['low']:.2f}</td>"
                f"<td class='sub'>{html.escape(', '.join(band['models']))}</td></tr>"
                for number, band in enumerate(grouped["bands"], start=1)
            )
            blocks.append(
                f"<h3>{html.escape(_t(TRACK_TITLES.get(track, track)))} "
                f"<span class='dash'>&middot; {html.escape(judge_model)}</span></h3>"
                f"<p class='sub'>{_t('a band is')} {grouped['threshold']:.2f} "
                f"{_t('wide, over')} {grouped['sessions']} {_t('sessions')}</p>"
                f"<table><thead><tr><th>{_t('Band')}</th><th>{_t('Score')}</th>"
                f"<th>{_t('Models')}</th></tr></thead><tbody>{rows}</tbody></table>"
            )

    if not blocks:
        return ""
    return (
        f"<h2>{_t('Bands, not places')}</h2>"
        + "<p>"
        + html.escape(
            _t(
                "Eleven models over ten notes cannot be put in order, and a table that "
                "prints them in one invites a comparison it cannot support. These are "
                "the same numbers grouped instead: within a band nothing separates the "
                "models, between bands something does. A band ends where the gap "
                "exceeds what resampling the sessions can rule out, so its width is "
                "the measurement's own resolution."
            )
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
    """
    latest = [row for row in results.latest(rows) if row.is_scored]
    blocks = []
    for track in (results.TRACK_CZECH_REAL, results.TRACK_CZECH_TRANSLATED):
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
        found = []
        for first in systems:
            for second in systems:
                if first == second:
                    continue
                at_least, strictly = True, False
                for table in tables.values():
                    for key in czech_scorer.CRITERION_KEYS:
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
                "listed here is a pair this project cannot separate."
            )
        )
        + "</p>"
        + "".join(blocks)
    )


def _variance() -> str:
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

    blocks, unreadable = [], []
    for track, judges in tracks.items():
        names = sorted(judges)
        rows = []
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
                    unreadable.append(
                        f"{TRACK_TITLES.get(track, track)} / "
                        f"{MEASURE_TABLES[track][criterion]['label']} / {name}"
                    )
                share = f"{gaps['separable']}/{gaps['pairs']}"
                cells.append(f"<td>{share}</td><td>{gaps['threshold']:.2f}</td>")
            if drawn:
                label = _t(MEASURE_TABLES[track][criterion]["label"])
                rows.append(f"<tr><td>{html.escape(label)}</td>" + "".join(cells) + "</tr>")
        if not rows:
            continue
        head = "".join(
            f"<th>{html.escape(name)}: {_t('pairs apart')}</th>"
            f"<th>{html.escape(name)}: {_t('gap needed')}</th>"
            for name in names
        )
        blocks.append(
            f"<h3>{html.escape(_t(TRACK_TITLES.get(track, track)))}</h3>"
            f"<table><thead><tr><th>{_t('Criterion')}</th>{head}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
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
                        f"{MEASURE_TABLES[track][criterion]['label']} "
                        f"({TRACK_TITLES.get(track, track)}, {name}, "
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
                    "The ten sessions differ from each other more than the eleven models "
                    "do, so whatever order the rows come out in is a fact about which "
                    "transcripts were drawn. No threshold rescues them; do not read them:"
                )
            )
            + f" {html.escape('; '.join(sorted(set(unreadable))))}.</p></div>"
        )
    return (
        f"<h2>{_t('How far apart is far enough?')}</h2>"
        + "<p>"
        + html.escape(
            _t(
                "Ten notes per model. The sessions were resampled two thousand times, "
                "paired on the transcript because every model wrote from all ten, and "
                "each pair of models compared on the middle 95% of the result. Two "
                "numbers per column: how many of the model pairs come out apart, and "
                "how large a gap it takes. A difference smaller than that is the same "
                "reading printed twice, whichever way round it fell."
            )
        )
        + "</p>"
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
        counted = (
            f" <span class='dash'>({_t('counted, not judged')})</span>"
            if (data["judges"][judges[0]]["criteria"].get(key, {}).get("computed"))
            else ""
        )
        body.append(f"<tr><td>{html.escape(label)}{counted}</td>" + "".join(cells) + "</tr>")

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
                "One clean note and seven variants, each carrying exactly one "
                "deliberate fault of one kind. This is the only check that can tell a "
                "column that measures something from a column that produces numbers."
            )
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
        for drawn in ordered:
            first = drawn[0]
            notes = sum(row.n_sessions_scored for row in drawn)
            sections.append(
                f"<h3>{_t('Judged by')} "
                f"{html.escape(first.judge_model or 'unknown')}</h3>"
                f"<p>{len(drawn)} {_t('models')}, {notes} {_t('notes')}, "
                f"{_t('rubric')} {html.escape(first.judge_prompt_version)}.</p>"
                + _table(track, drawn)
            )
        if len({drawn[0].judge_model for drawn in ordered}) > 1:
            sections.append(
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
        if withdrawn:
            sections.append(
                "<div class='warn'><p>"
                + html.escape(_t("Not drawn: this track was also scored under"))
                + f" {html.escape(', '.join(sorted(withdrawn)))}"
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
        sections.append(f"<h3>{_t('What each column is')}</h3>" + _definitions(track))

    limits = "".join(
        f"<h3>{html.escape(_t(title))}</h3><p>{html.escape(_t(body))}</p>" for title, body in LIMITS
    )

    return f"""<!doctype html>
<html lang="{LANG}"><head><meta charset="utf-8">
<title>{_t(TITLE)}</title><style>{STYLE}</style></head><body>
<h1>{_t(HEADLINE)}</h1>
<p class="sub">{_t(SUBTITLE)}</p>

<p>{_t(INTRO)}</p>

<div class="warn"><p><strong>{_t(NOT_PUBLIC)}</strong> {_t(NOT_PUBLIC_WHY)}</p></div>

{"".join(sections)}

{_verdicts(rows)}

{_bands()}

{_dominance(rows)}

{_variance()}

{_join()}

{_anchor()}

{_controls()}

<h2>{_t("What these numbers cannot be used for")}</h2>
{limits}

<h2>{_t("How it was measured")}</h2>
<p>{_t(METHOD_CORPORA)} <strong>{_t("They are not the same size:")}</strong>
{_t(METHOD_SIZE)}</p>
{_corpus()}
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
