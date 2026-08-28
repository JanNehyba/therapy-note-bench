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
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from tnb import results
from tnb.report import COLUMNS, MEASURE_TABLES, TRACK_BLURBS, TRACK_TITLES

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO / "local" / "czech-rows.jsonl"
DEFAULT_TARGET = REPO / "local" / "czech-brief.html"

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
    head = "".join(f"<th>{html.escape(measures[key]['label'])}</th>" for key, _ in columns)
    body, thin = [], []
    for row in sorted(rows, key=lambda r: r.system_id):
        complete = row.n_sessions_scored - row.n_sessions_partial
        cells = "".join(
            f"<td>{_fmt(row.metrics.headline.get(key), digits)}</td>" for key, digits in columns
        )
        if row.n_sessions_partial:
            count = f"<strong>{complete}</strong> of {row.n_sessions_scored}"
            if complete < THIN * row.n_sessions_scored:
                thin.append(f"{row.system_id} ({complete} of {row.n_sessions_scored})")
        else:
            count = str(complete)
        body.append(f"<tr><td>{html.escape(row.system_id)}</td><td>{count}</td>{cells}</tr>")

    warning = ""
    if thin:
        warning = (
            "<div class='warn'><p>These rows are an average of well under all their "
            "notes, because the judge left some questions unanswered and a note is "
            "only counted when every criterion of it was answered: "
            f"{html.escape(', '.join(thin))}. Unanswered questions cluster on the "
            "longer notes, so what is missing is not a random sample of the corpus. "
            "Read these rows as provisional.</p></div>"
        )
    return (
        "<table><thead><tr><th>Model</th><th>Notes in the mean</th>"
        f"{head}</tr></thead><tbody>{''.join(body)}</tbody></table>{warning}"
    )


def _definitions(track: str) -> str:
    measures = MEASURE_TABLES[track]
    items = []
    for key, _digits in COLUMNS[track]:
        measure = measures[key]
        items.append(
            f"<dt>{html.escape(measure['label'])} "
            f"<span class='dash'>({measure['scale']})</span></dt>"
            f"<dd>{html.escape(measure['definition'])}</dd>"
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
            f"<tr><td>{html.escape(label)}</td><td>{len(sessions)}</td>"
            f"<td>{words[middle]:,}</td><td>{words[0]:,}&ndash;{words[-1]:,}</td>"
            f"<td>{turns[middle]}</td>"
            f"<td class='sub'>{html.escape(note)}</td></tr>"
        )
    if not rows:
        return ""
    return (
        "<h3>The two corpora</h3>"
        "<table><thead><tr><th>Half</th><th>Sessions</th><th>Words, median</th>"
        "<th>Words, range</th><th>Turns, median</th><th></th></tr></thead>"
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
                f"tells {n - worst_tied} of {n} apart"
                if separates
                else f"<strong>cannot rank</strong> — {worst_tied} of {n} share one value"
            )
            lines.append(
                f"<tr><td>{html.escape(MEASURE_TABLES[track][key]['label'])}</td>"
                f"<td>{verdict}</td>"
                f"<td class='sub'>{html.escape(WHAT_IT_CATCHES.get(key, ''))}</td></tr>"
            )
        if lines:
            blocks.append(
                f"<h3>{html.escape(TRACK_TITLES.get(track, track))}</h3>"
                "<table><thead><tr><th>Column</th><th>Does it separate the models?</th>"
                "<th>What is behind the number</th></tr></thead>"
                f"<tbody>{''.join(lines)}</tbody></table>"
            )

    if not blocks:
        return ""
    return (
        "<h2>What is behind each number</h2>"
        "<p>A column that gives most models the same value cannot rank them, however "
        "confidently it is printed, and the first thing worth knowing about any column "
        "here is whether it separates anything at all. That half is counted from the "
        "rows. The second half — what the column actually catches, and how far two "
        "judges and one native speaker agreed about it — is written down rather than "
        "computed, because no arithmetic supplies it.</p>" + "".join(blocks)
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
                    cells.append("<td class='dash'>flat</td>")
                    continue
                strong = "<strong>" if entry["p"] < 0.05 else ""
                close = "</strong>" if entry["p"] < 0.05 else ""
                cells.append(
                    f"<td>{strong}{entry['rho']:+.2f}{close}"
                    f" <span class='dash'>p={entry['p']:.3f}</span></td>"
                )
            label = labels.get(key, {}).get("label", key)
            rows.append(f"<tr><td>{html.escape(label)}</td>" + "".join(cells) + "</tr>")
        head = "".join(f"<th>{html.escape(name)}</th>" for name in judges)
        return (
            f"<h3>{html.escape(heading)}</h3><p>{html.escape(lead)}</p>"
            f"<table><thead><tr><th>Attribute</th>{head}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )

    flat = sorted({key for name in judges for key in data["judges"][name].get("flat", [])})
    ranking = data["judges"][judges[0]].get("ranking_measure", "the ranking measure")
    systems = len(data["judges"][judges[0]].get("systems", []))

    return (
        "<h2>Does the English leaderboard predict the Czech?</h2>"
        f"<p>The two tables share {systems} models. Whether a standing in one predicts a "
        "standing in the other has two answers, and which one a reader gets depends on "
        "which English number they were looking at. Bold is a correlation that survives "
        "an exact permutation test at p &lt; 0.05.</p>"
        + block(
            "same_instrument",
            "Asked the same question, quality transfers",
            "PDSQI-9 on the English notes against PDSQI-9 on the Czech ones. Same "
            "attributes, same anchors, same judge; only the language of the note differs.",
        )
        + block(
            "leaderboard_ranking",
            "Asked the leaderboard's own measure, it does not",
            f"English {ranking} -- what the page sorts by, so what a position means -- "
            "against the Czech quality columns. Nothing here survives the test, and the "
            "two judges do not agree even on the sign.",
        )
        + (
            f"<p class='sub'>Flat on one side and therefore not correlated: "
            f"{html.escape(', '.join(flat))}.</p>"
            if flat
            else ""
        )
        + f"<div class='warn'><p>{html.escape(data.get('confound', ''))} "
        f"{html.escape(data.get('reading', ''))}</p></div>"
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
                cells.append("<td class='dash'>not answered yet</td>")
            else:
                gap = (
                    f" <span class='dash'>({entry['unanswered']} unanswered)</span>"
                    if entry["unanswered"]
                    else ""
                )
                cells.append(f"<td>{entry['rate']:.2f}{gap}</td>")
        label = MEASURE_TABLES[results.TRACK_CZECH_REAL][key]["label"]
        counted = (
            " <span class='dash'>(counted, not judged)</span>"
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
    body.append("<tr><td><strong>All questions</strong></td>" + "".join(totals) + "</tr>")

    head = "".join(f"<th>{html.escape(name)}</th>" for name in judges)
    return (
        "<h2>How often a judge and one native speaker said the same thing</h2>"
        f"<p>{html.escape(data.get('method', ''))}</p>"
        f"<div class='warn'><p>{html.escape(data.get('ceiling', ''))}</p></div>"
        f"<table><thead><tr><th>Criterion</th>{head}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
        f"<p class='sub'>{data.get('notes_rated', 0)} notes, drawn by a hash of the session "
        "and the model so that no score could influence which ones were rated.</p>"
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
        + "</strong>: at least one judge reports this fault in a note that does not "
        "have it, or misses it in a note that does. Read that column as a question "
        "rather than as an answer -- the disagreement is the finding.</p></div>"
        if unreliable
        else "<p>Every criterion found its own fault under every judge, and none "
        "fired on the clean note.</p>"
    )

    head = "".join(
        f"<th>{html.escape(MEASURE_TABLES[results.TRACK_CZECH_REAL][k]['label'])}</th>"
        for k in keys
    )
    return (
        "<h2>Does each column detect what it claims?</h2>"
        "<p>One clean note and seven variants, each carrying exactly one "
        "deliberate fault of one kind. This is the only check that can tell a "
        "column that measures something from a column that produces numbers.</p>"
        f"<table><thead><tr><th>Judge</th>{head}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>" + verdict
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
            f"<h2>{html.escape(TRACK_TITLES.get(track, track))}</h2>"
            f"<p class='sub'>{html.escape(re.sub(r'[*]{2}', '', TRACK_BLURBS.get(track, '')))}</p>"
        )
        # Newest first, so a superseded rubric sits below the one in use.
        ordered = sorted(
            groups.values(),
            key=lambda drawn: (drawn[0].judge_prompt_version, drawn[0].judge_model or ""),
            reverse=True,
        )
        versions = {drawn[0].judge_prompt_version for drawn in ordered}
        for drawn in ordered:
            first = drawn[0]
            notes = sum(row.n_sessions_scored for row in drawn)
            rubric = (
                f" <span class='dash'>· rubric {html.escape(first.judge_prompt_version)}</span>"
                if len(versions) > 1
                else ""
            )
            sections.append(
                f"<h3>Judged by {html.escape(first.judge_model or 'unknown')}{rubric}</h3>"
                f"<p>{len(drawn)} models, {notes} notes.</p>" + _table(track, drawn)
            )
        if len({drawn[0].judge_model for drawn in ordered}) > 1:
            sections.append(
                "<div class='warn'><p>Two judges, two tables, and they are not "
                "averaged. Where they disagree about a model is the only control "
                "this track has, so the disagreement is the thing to read.</p></div>"
            )
        if len(versions) > 1:
            sections.append(
                "<div class='warn'><p>More than one version of the rubric is shown. "
                "They are separate tables because they are separate instruments -- "
                f"{html.escape(', '.join(sorted(versions)))} -- and a model's rows "
                "under two of them are not two measurements of one thing. The newest "
                "is first.</p></div>"
            )
        sections.append("<h3>What each column is</h3>" + _definitions(track))

    limits = "".join(
        f"<h3>{html.escape(title)}</h3><p>{html.escape(body)}</p>" for title, body in LIMITS
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Czech note quality</title><style>{STYLE}</style></head><body>
<h1>Does an English leaderboard say anything about clinical Czech?</h1>
<p class="sub">therapy-note-bench &middot; Czech track &middot; measured, not published</p>

<p>The benchmark this belongs to scores model-written psychotherapy notes on two
English corpora. A model's standing there is a statement about English. This
track asks whether it carries over: the same models write notes in Czech, from
real sessions and from translated ones, and two instruments are asked about the
result. Seven yes/no criteria ask whether the Czech is right. PDSQI-9, a
published instrument, asks whether the note is any good -- because the criteria
cannot: a flawless Czech sentence about nothing passes all seven.</p>

<div class="warn"><p><strong>These numbers are not on the public site and this
document is not a publication.</strong> They were measured from confidential
clinical material and the decision to publish anything from them has not been
made. The transcripts were de-identified before any model saw them, and no
transcript text appears in this document or in any file it was built from.</p></div>

{"".join(sections)}

{_verdicts(rows)}

{_join()}

{_anchor()}

{_controls()}

<h2>What these numbers cannot be used for</h2>
{limits}

<h2>How it was measured</h2>
<p>Two halves, both read only from a directory that is not in version control.
Every model wrote a note from every transcript, on e-INFRA. <strong>They are not
the same size:</strong> a real session runs seven times longer than a translated
AnnoMI conversation, so the two halves differ in how hard the summarising is
before language is considered at all.</p>
{_corpus()}
<p><strong>No judge is ever shown a real session.</strong> What leaves for the
judge's provider is the note a model wrote, which is what lets a confidential
session be scored at all. The one place a transcript is sent is the PDSQI table
on the translated half: those transcripts are AnnoMI, published under CC-BY, and
sending them buys the two attributes -- is the note accurate, is it thorough --
that cannot be answered without the session. The real half is asked the other
six and those two columns are absent from it, because the question could not be
put rather than because a note failed.</p>
<p>Each criterion is one question, answered yes or no, asked in its own call. A
column is the share of notes free of that fault, so higher is better throughout.
A judge that answered neither yes nor no is recorded as not having answered --
never as "no fault" -- and a note with no content is not asked at all, because
every one of the seven asks about the absence of a fault and an empty note would
pass all seven.</p>
<p>PDSQI-9 is reproduced in English, word for word, because a translated
instrument is a different instrument with nothing validating it. The note it
rates is Czech and is shown with the Czech headings the model wrote. Seven of
its eight attributes are rated 1 to 5 and the eighth is a yes/no; they are
reported separately and never averaged, which is how the instrument's own
authors report them.</p>

<footer>Generated by <code>tools/czech_brief.py</code> from
<code>local/czech-rows.jsonl</code>. Both are gitignored.</footer>
</body></html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args(argv)

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
