"""The Czech briefing at half length, for somebody who has never seen this project.

`tools/czech_brief.py` writes for a reader who will check it. Every caveat it
makes is one somebody could otherwise make against it, every figure carries the
file it came from, and the result is thirteen thousand words that answer
questions a newcomer has not thought to ask yet. That document should stay as
it is; it is the record.

This is the other document: what was done, what came out, and what it may not
be used for. It drops the methodological self-defence, the chapters that argue
with alternatives nobody proposed, and every table a reader does not need to
reach the finding. What it keeps is the numbers.

**Nothing here is retyped.** Every figure and every table comes from
`czech_brief` itself -- the same functions, over the same payloads -- so the
short document cannot drift from the long one. If a number changes, it changes
in both or the build fails. That is the whole reason this is a tool and not a
file somebody wrote once.

**Two languages, one dictionary.** New prose is written in English and
translated through `czech_brief_cs.CS`, like everything else here, so a missing
translation stops the build rather than printing one English paragraph into a
Czech document.
"""

from __future__ import annotations

import argparse
import html
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import czech_brief as brief  # noqa: E402

from tnb import i18n, results  # noqa: E402

DEFAULT_SOURCE = REPO / "local" / "czech-rows.jsonl"
DEFAULT_TARGET = REPO / "local" / "czech-short.html"

TITLE = "Czech notes, the short version"
HEADLINE = "How well do language models write Czech therapy notes?"
SUBTITLE = "the short version · measured, not published"

#: Said first, because a reader who does not know what was done cannot read a
#: finding. The figures come from `czech_brief._written_figures`, which is what
#: the long document opens with too.
WHAT_THIS_IS = (
    "Thirteen language models were each asked to write clinical notes from twenty "
    "psychotherapy sessions. Ten of those sessions are real therapy with one client, "
    "recorded, transcribed and de-identified by hand. Ten are public counselling "
    "conversations translated into Czech. Every model wrote from the same sessions, so "
    "no two models are being compared on different material. {written} of the {asked} "
    "notes were written; where one is missing, this document says so rather than "
    "leaving it out of an average."
)
WHAT_WAS_ASKED = (
    "Every note was then read by two other language models, which answered the same "
    "questions about it separately. Two sets of questions were asked. Six ask only "
    "whether the Czech is correct. A published instrument called PDSQI-9 asks something "
    "harder: whether the note is any good clinically. Both, because neither answers the "
    "other -- a flawless Czech sentence about nothing passes all six criteria, and a "
    "note full of insight can be written in bad Czech."
)
WHO_READ = (
    "No clinician has read these notes. Everything below is one machine's account of "
    "what another machine wrote, and the only check on it is that the two readers "
    "answered separately and are never averaged: where they disagree, this document "
    "shows both numbers instead of splitting the difference."
)

FINDINGS_HEADING = "What came out of it"
CORPUS_HEADING = "What the notes were written from"
TABLES_HEADING = "The tables the findings come from"
TRUST_HEADING = "Does the measurement react when a fault is put in on purpose?"
LIMITS_HEADING = "What these numbers may not be used for"

#: The trust question a newcomer asks and the long document answers in a
#: chapter of its own. Kept because a reader who cannot check the instrument
#: has no reason to believe any table under it.
TRUST_LEAD = (
    "A column that never moves may be measuring something these models do not differ "
    "on, or may be measuring nothing. Nothing already scored can tell those apart, "
    "because none of it is a badly written note. So notes were written to be bad: one "
    "clean invented note and one copy per fault, each damaged in exactly one named way, "
    "with the expected answer written down before the readers were asked."
)

#: The long document reaches this over four chapters. A reader who wants the
#: argument has that document; a reader who wants the result has this sentence.
TABLES_LEAD = (
    "Two tables, both on the real sessions. The first asks whether the Czech is right, "
    "the second whether the note is any good. Every cell holds both readers' answers in "
    "the same order, and a cell where they disagree is marked. The long version of this "
    "document draws six more tables -- the translated half, and the same four again in "
    "the other note format -- and says where they differ."
)

LIMITS = (
    (
        "Ten sessions, one client, one therapist.",
        "Everything measured on the real half is also a fact about how those two people "
        "talk. A measure over ten notes per model has eleven possible values, so read "
        "the ends of a table and never the gap between two neighbours.",
    ),
    (
        "Nothing here says a note is true.",
        "The questions ask whether the Czech is right and how the note is built. "
        "Whether what it says actually happened in the session is the question a "
        "clinical team would ask first, and it is the one measurement nobody made -- "
        "answering it means showing a judge the transcript, and no transcript leaves "
        "this machine.",
    ),
    (
        "Longer notes score worse, and that is partly the instrument.",
        "Each of the six criteria asks whether a fault appears ANYWHERE in the note, so "
        "a longer note offers more places for one. Measured rather than guessed: every "
        "hundred words costs a few hundredths of a point, under both readers and on "
        "both halves.",
    ),
    (
        "Two readers agreeing is not evidence that a distinction matters.",
        "It is evidence that the distinction is stable and can be coded. Whether it is "
        "something a psychologist would care about is a question no arrangement of "
        "language models answers.",
    ),
    (
        "These models were what one provider had deployed on one day.",
        "The line-up changed under this project once already. A result here is about "
        "these systems at that moment, not about the companies behind them.",
    ),
)

FOOT = (
    "The long version -- every table, every caveat and the file behind every figure -- "
    "is local/czech-report-cs.pdf. Both are built from the same measurements by the "
    "same code, so no figure here was retyped and none can drift from it."
)


def _groups(rows: list[results.Row]) -> dict[str, list[list[results.Row]]]:
    """The drawable groups per track, the way `czech_brief.build` finds them.

    Copied in shape rather than in code because `build` does more than this --
    it also decides which rubric version is current and names the withdrawn
    ones. A short document draws only the newest, and says so in one sentence
    instead of a panel.
    """
    by_key: dict[tuple, list[results.Row]] = defaultdict(list)
    for row in results.latest(rows):
        if row.is_scored:
            by_key[row.comparability_key()].append(row)

    out: dict[str, list[list[results.Row]]] = {}
    for track in results.LOCAL_TRACKS:
        groups = {key: drawn for key, drawn in by_key.items() if drawn[0].track == track}
        if not groups:
            continue
        newest = max(max(row.scored_at or "" for row in drawn) for drawn in groups.values())
        cutoff = brief._same_rubric_cutoff(groups, newest)
        current = [
            drawn
            for drawn in groups.values()
            if max(row.scored_at or "" for row in drawn) >= cutoff
        ]
        out[track] = sorted(current, key=lambda drawn: drawn[0].judge_model or "")
    return out


def _findings(rows: list[results.Row]) -> str:
    """The findings, taken from the long document rather than restated.

    `_conclusion` writes them from the payloads and there is exactly one place
    they should be authored. Its two paragraphs about which count each name
    rests on go: they answer "can I quote this" and this document's answer to
    that is the last section.
    """
    body = brief._conclusion(rows)
    if not body:
        return ""
    # Its own heading goes: this document has already given the section one,
    # and two headings in a row is how a reader learns to skip both.
    body = body[body.index("</h2>") + len("</h2>") :] if "</h2>" in body else body
    parts = body.split("<p>")
    kept = [p for n, p in enumerate(parts) if n not in _DROPPED]
    return "<p>".join(kept)


#: Which of the eleven paragraphs a newcomer does not need. Indices into the
#: split above, where 0 is the heading. Three go: the two about how many notes
#: each named model rests on, which is a checking question, and the one warning
#: that two model names differ by a suffix, which matters to somebody reading
#: the tables closely and not to somebody reading the finding.
_DROPPED = (3, 4, 5)


def _limits() -> str:
    items = "".join(
        f"<dt>{html.escape(brief._t(claim))}</dt><dd>{html.escape(brief._t(why))}</dd>"
        for claim, why in LIMITS
    )
    return f"<dl class='measures'>{items}</dl>"


def build(rows: list[results.Row]) -> str:
    groups = _groups(rows)
    figures = brief._written_figures(rows)

    # Four tables, not eight. The real half under both instruments answers
    # "which model"; the translated half answers "does it hold up when the
    # material changes", which is the question a reader asks next and the one a
    # single table cannot answer. The Deepsy format is left to the long
    # document: it is a fourth answer to a question already answered twice.
    tables = ""
    for track in (
        results.TRACK_CZECH_REAL,
        results.TRACK_CZECH_REAL_PDSQI,
        results.TRACK_CZECH_TRANSLATED,
        results.TRACK_CZECH_TRANSLATED_PDSQI,
    ):
        if groups.get(track):
            tables += brief._merged_table(track, groups[track], lead=True)

    return f"""<!doctype html>
<html lang="{brief.LANG}"><head><meta charset="utf-8">
<title>{brief._t(TITLE)}</title><style>{brief.STYLE}</style></head><body>
<h1>{brief._t(HEADLINE)}</h1>
<p class="sub">{brief._t(SUBTITLE)}</p>

<p>{html.escape(brief._t(WHAT_THIS_IS).format(**figures))}</p>
<p>{html.escape(brief._t(WHAT_WAS_ASKED))}</p>
<div class="warn"><p>{html.escape(brief._t(WHO_READ))}</p></div>

{brief._glossary()}

<h2>{brief._t(CORPUS_HEADING)}</h2>
{brief._corpus(rows)}

<h2>{brief._t(FINDINGS_HEADING)}</h2>
{_findings(rows)}

<h2>{brief._t(TABLES_HEADING)}</h2>
<p>{html.escape(brief._t(TABLES_LEAD))}</p>
{tables}

<h2>{brief._t(TRUST_HEADING)}</h2>
<p>{html.escape(brief._t(TRUST_LEAD))}</p>
{brief._controls()}

{brief._categories(rows)}

<h2>{brief._t(LIMITS_HEADING)}</h2>
{_limits()}

<p class="note">{html.escape(brief._t(FOOT))}</p>
</body></html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=None)
    parser.add_argument("--language", choices=i18n.LANGUAGES, default=i18n.DEFAULT_LANG)
    args = parser.parse_args(argv)

    brief.LANG = args.language
    target = args.target or (
        DEFAULT_TARGET
        if args.language == i18n.DEFAULT_LANG
        else DEFAULT_TARGET.with_name(f"{DEFAULT_TARGET.stem}-{args.language}.html")
    )

    if not args.source.exists():
        print(f"{args.source} is not there. Run `tnb score-czech` first.", file=sys.stderr)
        return 1
    rows = results.load(args.source)
    rows, _disallowed = results.drawable(rows)
    if not rows:
        print(f"{args.source} has nothing drawable in it.", file=sys.stderr)
        return 1

    # The same refusal the long document makes, for the same reason: this one
    # is the copy more likely to be forwarded, so it is the one that must not
    # carry a sentence of a session.
    problems = brief.check_no_clinical_text(rows)
    if problems:
        print("Refusing to write: a row carries something that is not a score.", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    page = build(rows)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")
    print(f"wrote {target}  ({len(page.split())} words of markup)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
