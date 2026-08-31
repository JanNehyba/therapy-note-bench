"""Rendering ``results/rows.jsonl`` into the three things people actually read.

One source, three views:

- ``docs/leaderboard.json`` -- the only data file the presentations load. A
  Hugging Face mirror, if one is ever added, reads this and nothing else.
- ``README.md`` between its existing markers -- the shop window: e-INFRA models,
  headline numbers, nothing to click.
- ``docs/index.html`` -- the leaderboard proper: both tracks, the reference
  systems, the published numbers, sorting, filtering, and a row that expands
  into its per-section and per-criterion breakdown.

Nothing here decides what may be compared. That is
:func:`tnb.results.comparable_groups`, and every view goes through it.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from pathlib import Path

from tnb import corpus, i18n, judge, results
from tnb.config import REPO_ROOT
from tnb.results import Row
from tnb.scoring import concordance, czech_pdsqi, pdsqi
from tnb.scoring import czech as czech_scorer
from tnb.scoring import icare as icare_scorer
from tnb.scoring import tneval as rubric
from tnb.tasks import czech as czech_task
from tnb.tasks import icare, soap

DOCS_DIR = REPO_ROOT / "docs"
DATA_PATH = DOCS_DIR / "leaderboard.json"
PAGE_PATH = DOCS_DIR / "index.html"

#: The leaderboard's sister page. The tables answer "which model"; this one
#: answers "why believe the tables", and the two questions want different
#: amounts of a reader's attention. Eight panels grew above the tables one
#: finding at a time, until the thing a reader came for was below four collapsed
#: boxes.
METHODS_PATH = DOCS_DIR / "methods.html"
README_PATH = REPO_ROOT / "README.md"

LEADERBOARD_MARKERS = ("<!-- LEADERBOARD:BEGIN -->", "<!-- LEADERBOARD:END -->")
CALIBRATION_MARKERS = ("<!-- CALIBRATION:BEGIN -->", "<!-- CALIBRATION:END -->")
CALIBRATION_PATH = DOCS_DIR / "calibration.json"
SATURATION_PATH = DOCS_DIR / "saturation.json"


def saturation_path(judge_model: str, docs_dir: Path | None = None) -> Path:
    """Where one judge's saturation analysis lives.

    One file per judge, because the analysis is of a judge's own answers and
    two judges' are two analyses. The leaderboard already refuses to put two
    judges in one table; the same rule has to hold for what is drawn beside
    them.
    """
    from tnb.generation import _slug

    return (docs_dir or DOCS_DIR) / f"saturation-{_slug(judge_model)}.json"


def load_saturations(docs_dir: Path | None = None) -> list[dict]:
    """Every judge's saturation analysis that has been run.

    Includes the legacy single-file form, so a repository that has not re-run
    the analysis since this was split keeps its panel.
    """
    docs_dir = docs_dir or DOCS_DIR
    found = [_load_json(path) for path in sorted(docs_dir.glob("saturation-*.json"))]
    legacy = _load_json(docs_dir / SATURATION_PATH.name)
    if legacy is not None and not any(
        item and item.get("judge_model") == legacy.get("judge_model") for item in found
    ):
        found.append(legacy)
    return [item for item in found if item]


#: Where the pages are served from. Written once: it appears in the README
#: block, in a table link and in a methods link, and three copies of a URL are
#: three chances for one of them to point at the old host.
SITE_URL = "https://jannehyba.github.io/therapy-note-bench/"

JUDGES_PATH = DOCS_DIR / "judges.json"
PREFERENCE_PATH = DOCS_DIR / "preference.json"

#: The criteria a Czech table draws, which is now all of them. The name
#: stays: a seventh was drawn here once and the next one will be too.
DRAWN_CRITERIA = czech_scorer.CRITERION_KEYS

#: Column order per track: (key, how many decimals).
#:
#: The heading is *not* here. It lives in the track's measure table below,
#: together with the scale and the caveat, so a measure is named in one place
#: and cannot be renamed in a view while the definition keeps the old word.
COLUMNS: dict[str, tuple[tuple[str, int], ...]] = {
    results.TRACK_TNEVAL: (
        ("completeness", 3),
        ("conciseness", 3),
        ("faithfulness", 2),
    ),
    results.TRACK_ICARE: (
        ("rouge_l", 3),
        ("bertscore", 3),
        ("trace", 2),
        ("temporal_past", 3),
        ("temporal_next", 3),
    ),
    # Built from the instrument's own order rather than retyped, so the columns
    # cannot drift out of the order a reader will find in the paper. Seven are
    # 1-5 ratings; the eighth is the fraction of notes free of stigmatising
    # language, which is a proportion and printed like the other proportions.
    results.TRACK_PDSQI: tuple(
        (key, 3 if key == "stigmatizing" else 2) for key in pdsqi.ATTRIBUTE_KEYS
    ),
    # Two decimals, not three. Every column is a share of ten or twenty notes,
    # so the third place is a digit that cannot exist.
    results.TRACK_CZECH_REAL: tuple((key, 2) for key in DRAWN_CRITERIA),
    results.TRACK_CZECH_TRANSLATED: tuple((key, 2) for key in DRAWN_CRITERIA),
    # The Deepsy sections are scored by the same six criteria: the question
    # is whether the Czech is right, and that does not change with the shape
    # the note was asked for. Changing the instrument as well as the format
    # would leave nothing to attribute a difference to.
    results.TRACK_DEEPSY_REAL: tuple((key, 2) for key in DRAWN_CRITERIA),
    results.TRACK_DEEPSY_TRANSLATED: tuple((key, 2) for key in DRAWN_CRITERIA),
    # PDSQI-9 over the same Czech notes, in the instrument's own order. The real
    # half declares six columns and the translated eight: `accurate` and
    # `thorough` need the session, and the real sessions are never sent to the
    # judge. Declaring a column that could not be asked would leave an empty
    # heading, which reads as a model that failed rather than a question nobody
    # was allowed to put.
    results.TRACK_CZECH_REAL_PDSQI: tuple(
        (key, 3 if key == "stigmatizing" else 2)
        for key in czech_pdsqi.attribute_keys(czech_task.NAME_REAL)
    ),
    results.TRACK_CZECH_TRANSLATED_PDSQI: tuple(
        (key, 3 if key == "stigmatizing" else 2)
        for key in czech_pdsqi.attribute_keys(czech_task.NAME_TRANSLATED)
    ),
}

#: Where each track's measure definitions live. Both scorers own their own --
#: the range, the heading and the caveat sit next to the code that produces the
#: number, so a measure cannot be renamed in one place and described in another.
#:
#: This module used to keep a second copy of the iCARE half. It drifted the first
#: time the scorer changed: `temporal` was split into looking back and looking
#: forward there and stayed a single averaged column here.
MEASURE_TABLES = {
    results.TRACK_TNEVAL: rubric.MEASURES,
    results.TRACK_ICARE: icare_scorer.MEASURES,
    results.TRACK_PDSQI: pdsqi.MEASURES,
    results.TRACK_CZECH_REAL: czech_scorer.MEASURES,
    results.TRACK_CZECH_TRANSLATED: czech_scorer.MEASURES,
    results.TRACK_DEEPSY_REAL: czech_scorer.MEASURES,
    results.TRACK_DEEPSY_TRANSLATED: czech_scorer.MEASURES,
    results.TRACK_CZECH_REAL_PDSQI: czech_pdsqi.measures(czech_task.NAME_REAL),
    results.TRACK_CZECH_TRANSLATED_PDSQI: czech_pdsqi.measures(czech_task.NAME_TRANSLATED),
}

#: Which measure each track is ranked by, and the honest `None` where the
#: project refuses to rank.
#:
#: iCARE is `None` on purpose: its three columns are reported side by side
#: *because they disagree*, and naming one of them the ranking would publish a
#: claim the methodology declines to make. `_sort_key` reads this, so what the
#: page says it ranks by and what it is actually sorted by cannot drift apart.
RANKING_MEASURES: dict[str, str | None] = {
    results.TRACK_TNEVAL: rubric.RANKING_MEASURE,
    results.TRACK_ICARE: None,
    # Also None, and for the instrument's own reason: PDSQI-9's authors report
    # its attributes separately, and a mean of seven 1-5 ratings with a yes/no
    # would be a composite nobody validated.
    results.TRACK_PDSQI: pdsqi.RANKING_MEASURE,
    # None again, and for a third reason. Weighting spelling against clinical
    # terminology is a linguistic decision rather than a measurement, and the
    # correlation this track exists to look for is more useful per criterion:
    # English completeness may predict terminology and say nothing about
    # quotation marks.
    results.TRACK_CZECH_REAL: czech_scorer.RANKING_MEASURE,
    results.TRACK_CZECH_TRANSLATED: czech_scorer.RANKING_MEASURE,
    results.TRACK_DEEPSY_REAL: czech_scorer.RANKING_MEASURE,
    results.TRACK_DEEPSY_TRANSLATED: czech_scorer.RANKING_MEASURE,
    # The instrument's reason again, unchanged by the language it is asked in.
    results.TRACK_CZECH_REAL_PDSQI: pdsqi.RANKING_MEASURE,
    results.TRACK_CZECH_TRANSLATED_PDSQI: pdsqi.RANKING_MEASURE,
}


#: Why a track without a ranking column has none. Rendered under the table.
#:
#: **Three tracks are unranked for three different reasons**, and the page used
#: to print iCARE's under all of them: "the source paper found they disagree",
#: which is true of iCARE, is not a statement anybody made about PDSQI-9 or
#: about Czech spelling. The reasons were written as comments beside
#: `RANKING_MEASURES` and never reached a reader.
#:
#: A track whose `RANKING_MEASURES` entry is None and which is missing here
#: falls back to iCARE's sentence, which is how the wrong one got everywhere;
#: `tests/test_report.py` holds every unranked track to having its own.
NOT_RANKED_REASONS: dict[str, str] = {
    results.TRACK_ICARE: (
        "This track is deliberately <strong>not ranked</strong>: its columns measure "
        "different things and the source paper found they disagree. That disagreement "
        "is the result."
    ),
    results.TRACK_PDSQI: (
        "This track is deliberately <strong>not ranked</strong>: PDSQI-9's authors "
        "report its attributes separately, and a mean of them would be a composite "
        "nobody validated."
    ),
    results.TRACK_CZECH_REAL_PDSQI: (
        "This track is deliberately <strong>not ranked</strong>: PDSQI-9's authors "
        "report its attributes separately, and a mean of them would be a composite "
        "nobody validated."
    ),
    results.TRACK_CZECH_TRANSLATED_PDSQI: (
        "This track is deliberately <strong>not ranked</strong>: PDSQI-9's authors "
        "report its attributes separately, and a mean of them would be a composite "
        "nobody validated."
    ),
    results.TRACK_CZECH_REAL: (
        "This track is deliberately <strong>not ranked</strong>: weighting spelling "
        "against clinical terminology is a linguistic decision rather than a "
        "measurement. The correlation this track exists to look for is more useful per "
        "criterion anyway -- English completeness may predict terminology and say "
        "nothing about diacritics."
    ),
    results.TRACK_CZECH_TRANSLATED: (
        "This track is deliberately <strong>not ranked</strong>: weighting spelling "
        "against clinical terminology is a linguistic decision rather than a "
        "measurement. The correlation this track exists to look for is more useful per "
        "criterion anyway -- English completeness may predict terminology and say "
        "nothing about diacritics."
    ),
    results.TRACK_DEEPSY_REAL: (
        "This track is deliberately <strong>not ranked</strong>: weighting spelling "
        "against clinical terminology is a linguistic decision rather than a "
        "measurement. The correlation this track exists to look for is more useful per "
        "criterion anyway -- English completeness may predict terminology and say "
        "nothing about diacritics."
    ),
    results.TRACK_DEEPSY_TRANSLATED: (
        "This track is deliberately <strong>not ranked</strong>: weighting spelling "
        "against clinical terminology is a linguistic decision rather than a "
        "measurement. The correlation this track exists to look for is more useful per "
        "criterion anyway -- English completeness may predict terminology and say "
        "nothing about diacritics."
    ),
}


#: The header a page writes about itself, when it is not the published one.
#:
#: The template's own header is the published page's: "scored on two published
#: protocols -- TN-Eval's SOAP rubric and iCARE's 17 sections". The Czech page
#: is drawn by the same renderer and inherited it, so it opened by naming two
#: instruments no table on it uses, and then offered three links -- the brief,
#: the PDF and the methods page -- to files that do not exist beside it. A dead
#: link on a page nobody published is still a page that lies about itself.
#:
#: `links` is keyed by the id of the paragraph it replaces. None
#: removes the paragraph: there is no local methods page, and an empty one
#: would be worse than none.
PAGE_CZECH = {
    "title": "therapy-note-bench \u2014 Czech track",
    "sub": (
        "Czech psychotherapy notes written by the models e-INFRA CZ deploys, from ten real "
        "sessions and ten AnnoMI conversations translated into Czech. Two independent judges "
        "rate every note: six yes/no criteria about the Czech itself, and PDSQI-9 about "
        "whether the note is any good. <strong>Measured, not published</strong> \u2014 these "
        "tables are not on the public site and the transcripts never leave this machine."
    ),
    "links": {
        "brief-link": (
            '<a href="czech-brief.html">What these numbers can and cannot say \u2192</a> '
            "The same tables with the caveats around them, written to be read by somebody "
            'who was not here. Also as a <a href="czech-report.pdf">PDF</a>.'
        ),
        "methods-link": None,
    },
}

#: Which tracks make a page the Czech one. Membership, not a count: a page that
#: draws a Czech table is the Czech page whatever else is on it.
CZECH_PAGE_TRACKS = frozenset(
    {
        results.TRACK_CZECH_REAL,
        results.TRACK_CZECH_TRANSLATED,
        results.TRACK_CZECH_REAL_PDSQI,
        results.TRACK_CZECH_TRANSLATED_PDSQI,
        results.TRACK_DEEPSY_REAL,
        results.TRACK_DEEPSY_TRANSLATED,
    }
)


#: What the expandable row's second block holds, per track. It is not the same
#: thing on every track and it used to be headed "Rubric criteria" everywhere
#: but iCARE.
#:
#: On the Czech and Deepsy tracks that block is not criteria at all: it is the
#: **denominator**, one entry per criterion saying how many of that model's
#: notes the criterion got an answer for, next to the mean note length. It is
#: the number a reader checks to see whether an average is over ten notes or
#: over nine, which is this repository's oldest failure mode -- and it was
#: printed under the name of an instrument that scores English SOAP notes.
DETAIL_LABELS: dict[str, str] = {
    results.TRACK_TNEVAL: "Rubric criteria",
    results.TRACK_ICARE: "TRACE dimensions",
    results.TRACK_CZECH_REAL: "What each average is over",
    results.TRACK_CZECH_TRANSLATED: "What each average is over",
    results.TRACK_DEEPSY_REAL: "What each average is over",
    results.TRACK_DEEPSY_TRANSLATED: "What each average is over",
}


#: Which tracks each source, corpus profile and protocol section belongs to.
#:
#: **Why this exists at all.** `build` used to attach every one of them to
#: every page, which was harmless while there was one page and it drew every
#: track. There are two now, and the Czech page credited TN-Eval's two human
#: annotators, printed TN-Eval's 23-item rubric under a heading of its own, and
#: profiled the iHOPE corpus -- none of which any Czech table uses. A reader
#: cannot tell a source that was used from one that was merely listed, so
#: listing it is a claim, and it was the wrong one.
#:
#: A source missing from here is drawn on every page, which is the old
#: behaviour and the safe direction: a source over-credited is a nuisance, a
#: source used and not credited is a licence problem.
LICENCE_TRACKS: dict[str, tuple[str, ...]] = {
    "PDSQI-9": (
        results.TRACK_PDSQI,
        results.TRACK_CZECH_REAL_PDSQI,
        results.TRACK_CZECH_TRANSLATED_PDSQI,
    ),
    # The Czech generation prompt is a translation of TN-Eval's SOAP prompt,
    # so the code licence applies to the Czech tables too. The Deepsy tracks
    # use the application's own prompts and are not on this line.
    "TN-Eval (code)": (
        results.TRACK_TNEVAL,
        results.TRACK_PDSQI,
        results.TRACK_CZECH_REAL,
        results.TRACK_CZECH_TRANSLATED,
    ),
    # The 150 rated notes and the therapist's row that comes from them.
    "TN-Eval-Data": (results.TRACK_TNEVAL, results.TRACK_PDSQI),
    "AnnoMI": (
        results.TRACK_TNEVAL,
        results.TRACK_PDSQI,
        results.TRACK_CZECH_TRANSLATED,
        results.TRACK_CZECH_TRANSLATED_PDSQI,
        results.TRACK_DEEPSY_TRANSLATED,
    ),
    "iCARE": (results.TRACK_ICARE,),
    "TheraFuse": (results.TRACK_ICARE,),
}

#: Same idea for the corpus profiles. `corpus.build` measures the two English
#: corpora; everything else it returns -- the fill rate and the seventeen
#: sections -- is iHOPE, so the whole block goes when no iCARE table is drawn.
DATASET_TRACKS: dict[str, tuple[str, ...]] = {
    "tneval": (
        results.TRACK_TNEVAL,
        results.TRACK_PDSQI,
        results.TRACK_CZECH_TRANSLATED,
        results.TRACK_CZECH_TRANSLATED_PDSQI,
        results.TRACK_DEEPSY_TRANSLATED,
    ),
    "icare": (results.TRACK_ICARE,),
}

#: And for the protocol. The four SOAP sections are shown wherever a note is a
#: SOAP note, the Czech translation included; the 23 criteria are TN-Eval's
#: scoring instrument and are shown only where that instrument was used.
PROTOCOL_TRACKS: dict[str, tuple[str, ...]] = {
    "sections": (
        results.TRACK_TNEVAL,
        results.TRACK_PDSQI,
        results.TRACK_CZECH_REAL,
        results.TRACK_CZECH_TRANSLATED,
        results.TRACK_CZECH_REAL_PDSQI,
        results.TRACK_CZECH_TRANSLATED_PDSQI,
    ),
    "criteria": (results.TRACK_TNEVAL,),
    "icare_sections": (results.TRACK_ICARE,),
}


def _used_by(owners: dict[str, tuple[str, ...]], key: str, drawn: set[str]) -> bool:
    """True when a page drawing `drawn` uses `key`, or when nothing is claimed."""
    tracks = owners.get(key)
    return True if tracks is None else bool(set(tracks) & drawn)


#: Which measures each track's judge actually decides. Only these can be
#: compared *between* two judges: on the iCARE track four of the five columns
#: are computed from the note and the expert note alone, so they are identical
#: under every judge, and "the judges agree perfectly on ROUGE-L" would dress a
#: tautology as a finding.
#: The measures a scorer computes and deliberately does not draw. Only TN-Eval
#: has any: the Likert forms of completeness and conciseness, kept out of the
#: table because the rubric forms are the ones with a human anchor. It matters
#: on the concordance panel, which says of the measures it leaves out that they
#: are "computed from the note and the expert note" -- true of iCARE's four and
#: false of these two.
INTERNAL_MEASURES: dict[str, tuple[str, ...]] = {
    results.TRACK_TNEVAL: getattr(rubric, "INTERNAL_MEASURES", ()),
    results.TRACK_ICARE: getattr(icare_scorer, "INTERNAL_MEASURES", ()),
    results.TRACK_PDSQI: getattr(pdsqi, "INTERNAL_MEASURES", ()),
}


JUDGE_MEASURES: dict[str, tuple[str, ...]] = {
    results.TRACK_TNEVAL: rubric.JUDGE_MEASURES,
    results.TRACK_ICARE: icare_scorer.JUDGE_MEASURES,
    # Every one of the eight. Unlike iCARE, nothing here is computed from the
    # text alone, so all eight columns are a judge's opinion and all eight can
    # be compared between two of them.
    results.TRACK_PDSQI: pdsqi.JUDGE_MEASURES,
    # All seven, and it matters more here than anywhere else: this track has no
    # human anchor at all, so two judges disagreeing is the only control it has.
    results.TRACK_CZECH_REAL: czech_scorer.JUDGE_MEASURES,
    results.TRACK_CZECH_TRANSLATED: czech_scorer.JUDGE_MEASURES,
    results.TRACK_DEEPSY_REAL: czech_scorer.JUDGE_MEASURES,
    results.TRACK_DEEPSY_TRANSLATED: czech_scorer.JUDGE_MEASURES,
    # Every attribute the corpus was asked, and no more. Naming one the two
    # judges never answered would ask the concordance panel to compare a column
    # that does not exist on either side.
    results.TRACK_CZECH_REAL_PDSQI: czech_pdsqi.attribute_keys(czech_task.NAME_REAL),
    results.TRACK_CZECH_TRANSLATED_PDSQI: czech_pdsqi.attribute_keys(czech_task.NAME_TRANSLATED),
}


def measure_table(track: str) -> dict[str, dict[str, str]]:
    """The measure definitions for one track, from the scorer that owns them."""
    return MEASURE_TABLES.get(track, {})


def column_meta(track: str, key: str) -> dict:
    """Heading, range, definition and caveat for one column.

    Raises rather than substituting a blank: a column with no documented scale
    is exactly the thing this whole structure exists to prevent, and a silent
    empty string would put it back on the page as a bare number.
    """
    try:
        meta = measure_table(track)[key]
    except KeyError:
        raise KeyError(
            f"column {key!r} on track {track!r} has no entry in the measure table, "
            f"so the page could not say what scale it is on"
        ) from None
    definition = meta["definition"]
    if "{sections}" in definition:
        definition = definition.format(sections=_and_list(ihope_temporal()))
    # How many criteria the rubric holds, counted rather than typed. It is the
    # denominator of every completeness figure on the page, and a caveat naming
    # it has to name whatever `CHECKBOX_MAPPING` actually contains -- a hand-
    # written 23 beside a mapping somebody added a criterion to is the caveat
    # that reads most convincingly and is wrong.
    caveat = meta["caveat"]
    if "{criteria}" in caveat:
        caveat = caveat.format(criteria=len(rubric.CHECKBOX_MAPPING))
    return {
        "key": key,
        "label": meta["label"],
        "scale": meta["scale"],
        "definition": definition,
        "caveat": caveat,
        "ranking": key == RANKING_MEASURES.get(track),
    }


def _and_list(values) -> str:
    values = [str(value) for value in values]
    if len(values) < 2:
        return "".join(values)
    return f"{', '.join(values[:-1])} and {values[-1]}"


#: Titles say what the protocol is, never how many sessions it covers. The
#: count belongs in the Sessions column, where it is whatever was actually run
#: -- a partial run must not sit under a heading claiming the full corpus.
TRACK_TITLES = {
    results.TRACK_TNEVAL: "TN-Eval SOAP · AnnoMI conversations",
    # Both names, and which is which. They are not two things: the repository
    # `proadhikary/iCARE` was last committed 2025-04-28 and preprint v2, dated
    # 2026-08-19, renames the framework *iHOPE* -- so the published code
    # predates the paper describing it, and a reader meets both names in the
    # literature. `docs/datasets.md` has the version mismatch in full. The slash
    # alone said nothing about either.
    results.TRACK_ICARE: "iCARE form on the iHOPE corpus · 17 sections per session",
    # "the same notes" and "the rubric above" are true of a reader who walked
    # here from the first tab and of nobody else. The switch means a reader can
    # land on this table first, and then the one thing the title has to say --
    # which corpus these notes were written from -- was the one thing it did
    # not say. The other two tracks name theirs.
    results.TRACK_PDSQI: "PDSQI-9 · the SOAP notes on AnnoMI, rated for quality",
    results.TRACK_CZECH_REAL: "Czech · ten real sessions, one client",
    results.TRACK_CZECH_TRANSLATED: "Czech · AnnoMI conversations, translated",
    # Named for the instrument first, because that is what separates these two
    # from the two above: the same notes, asked whether they are good notes
    # rather than whether they are good Czech.
    results.TRACK_CZECH_REAL_PDSQI: "PDSQI-9 · the Czech notes from the real sessions",
    results.TRACK_CZECH_TRANSLATED_PDSQI: "PDSQI-9 · the Czech notes from translated AnnoMI",
    results.TRACK_DEEPSY_REAL: "Deepsy format · ten real sessions, one client",
    results.TRACK_DEEPSY_TRANSLATED: "Deepsy format · AnnoMI conversations, translated",
}

#: The same tracks, short enough to be a button. Separate from the titles rather
#: than sliced out of them: a title is a sentence and a slice of a sentence is
#: whatever survived the punctuation.
TRACK_SWITCH_LABELS = {
    results.TRACK_TNEVAL: "TN-Eval SOAP",
    results.TRACK_ICARE: "iCARE / iHOPE",
    results.TRACK_PDSQI: "PDSQI-9 on SOAP",
    results.TRACK_CZECH_REAL: "Czech, real sessions",
    results.TRACK_CZECH_TRANSLATED: "Czech, translated",
    results.TRACK_CZECH_REAL_PDSQI: "PDSQI-9, real sessions",
    results.TRACK_CZECH_TRANSLATED_PDSQI: "PDSQI-9, translated",
    results.TRACK_DEEPSY_REAL: "Deepsy, real sessions",
    results.TRACK_DEEPSY_TRANSLATED: "Deepsy, translated",
}

TRACK_BLURBS = {
    results.TRACK_TNEVAL: (
        "Reference-free. 23 completeness criteria, conciseness scored sentence by "
        "sentence, faithfulness against the full transcript."
    ),
    results.TRACK_ICARE: (
        "Automatic metrics and a TRACE judge side by side, because the source paper "
        "found they disagree. That disagreement is a result, not an error. "
        "iCARE and iHOPE are one project under two names: the code "
        "was released as iCARE in April 2025 and the preprint renamed it iHOPE in "
        "August 2026, sixteen months later. **PDSQI-9 has no columns here**, and "
        "that is deliberate rather than missing: it rates how a clinical note is "
        "written, and these are 17 form fields rather than a written note. It runs "
        "on the SOAP notes, where it can be read against the rubric that scores "
        "the same text."
    ),
    results.TRACK_PDSQI: (
        "A published instrument asked about the same notes as the TN-Eval SOAP "
        "track: the SOAP notes written from the 50 AnnoMI conversations. Not a "
        "third corpus -- one corpus, two instruments, so the two tables can be "
        "read against each other. Eight attributes, reported separately and never "
        "averaged, because the instrument reports them that way and because one "
        "of the eight is a 0-1 column: a mean over it and seven 1-5 scales would "
        "be a number with no unit."
    ),
    results.TRACK_CZECH_REAL: (
        "Six yes/no criteria about the Czech, asked of the note alone. Each column "
        "is the share of notes free of that fault. **Ten sessions with one client, so "
        "adjacent positions are not separable** -- and the generation prompt is a "
        "translation of TN-Eval's rather than a reproduction of anything."
    ),
    results.TRACK_CZECH_TRANSLATED: (
        "The same criteria on notes written from AnnoMI conversations translated into "
        "Czech. **The two halves differ by more than language** -- AnnoMI is "
        "motivational interviewing about substance use and the real sessions are not "
        "-- so a model doing worse here may be doing worse at motivational "
        "interviewing rather than at translated Czech."
    ),
    results.TRACK_CZECH_REAL_PDSQI: (
        "The same Czech notes as the real-session table, asked a published quality "
        "instrument instead of the six language criteria. The criteria cannot say "
        "whether a note is any good -- a flawless Czech sentence about nothing passes "
        "all six -- and this is the half of the question they leave out. **Six "
        "attributes, not eight:** `accurate` and `thorough` can only be answered "
        "by reading the session, and both judges run at Google and at OpenAI -- "
        "outside the university infrastructure the sessions sit on. Asking those "
        "two would mean sending a real session out to them. The columns are absent "
        "because of where the judge is, not because of anything the notes lack."
    ),
    results.TRACK_DEEPSY_REAL: (
        "The same models and the same ten sessions, asked for the note format the "
        "Deepsy application actually writes rather than for SOAP. Three of its eleven "
        "sections, the three with a SOAP counterpart, scored by the same six "
        "criteria. **What changes between this table and the Czech one is the shape "
        "the model was asked for and nothing else**, so a difference between them is "
        "a fact about the format."
    ),
    results.TRACK_DEEPSY_TRANSLATED: (
        "The Deepsy sections on notes written from translated AnnoMI. The same "
        "comparison as the real half, on conversations that are public -- and the "
        "same warning: the two halves differ in length by a factor of seven before "
        "any question of format arises."
    ),
    results.TRACK_CZECH_TRANSLATED_PDSQI: (
        "PDSQI-9 on the notes written from translated AnnoMI. All eight attributes "
        "here: these transcripts are public, so the judge may read the session and "
        "answer whether the note is accurate and thorough. **Eight columns against "
        "the real half's six is two instruments, not one**, and the two tables are "
        "not rows of each other."
    ),
}

#: What a note is compared with, what a human's note is doing in the comparison,
#: and whether the judge can be checked against a person.
#:
#: This is on the page because two readers in a row worked it out only by asking.
#: The two tracks put a human note in opposite roles, and every number below
#: means something different depending on which role it is:
#:
#: - On TN-Eval the therapist's note is **a competitor**. It is scored by the
#:   same protocol as every model and it is a row in the table -- which is why
#:   every model outscores it on completeness. The rubric counts what a note
#:   contains and cannot see what a clinician chose to leave out.
#: - On iCARE the expert note is **the answer key**. It never competes. Two of
#:   the four columns measure how closely a model reproduced it, which is
#:   similarity, not quality.
#: What the corpus is and what a note is, in one line each. Above the table,
#: because every column means something different depending on the answers and
#: two readers in a row worked them out only by asking.
TRACK_TERMS = {
    results.TRACK_TNEVAL: (
        (
            "TN-Eval SOAP",
            "This track. A model reads a counselling transcript and writes a SOAP "
            "note; TN-Eval's published rubric then scores it. Named after the paper "
            "the prompt and the rubric are taken from.",
        ),
        (
            "The transcripts",
            "AnnoMI: 133 publicly released motivational-interviewing sessions, "
            "transcribed and annotated by therapists. 50 of them are scored here.",
        ),
        (
            "SOAP note",
            "The standard clinical note format: subjective, objective, assessment, "
            "plan. Every model writes into the same four headings.",
        ),
    ),
    results.TRACK_PDSQI: (
        (
            "TN-Eval SOAP",
            "This track. A model reads a counselling transcript and writes a SOAP "
            "note; TN-Eval's published rubric then scores it. Named after the paper "
            "the prompt and the rubric are taken from.",
        ),
        (
            "The transcripts",
            "AnnoMI: 133 publicly released motivational-interviewing sessions, "
            "transcribed and annotated by therapists. 50 of them are scored here.",
        ),
        (
            "PDSQI-9",
            "A published instrument for rating how a clinical note is written, "
            "validated on real records with physicians doing the rating.",
        ),
    ),
    results.TRACK_ICARE: (
        (
            "iCARE / iHOPE",
            "This track. A model fills in a 17-field clinical form from a counselling "
            "transcript, and its answers are compared with the form the clinician who "
            "saw the session filled in. One project under two names: released as "
            "iCARE, renamed iHOPE in the preprint.",
        ),
        (
            "The sessions",
            "40 counselling sessions, each with one note written by the clinician "
            "who saw it. That note is the answer key, not an entry.",
        ),
        (
            "The form",
            "17 fields to fill in rather than a note to write, so a blank field is "
            "a different thing from a short sentence.",
        ),
    ),
}


TRACK_DESIGN = {
    results.TRACK_TNEVAL: {
        "scored_against": (
            "The transcript and a 23-item rubric. There is no gold note to copy, "
            "so any new model can be measured without anyone writing one."
        ),
        "human_role": (
            "The therapist's note is scored by the identical protocol and sits in "
            "the table as its own row. It is a competitor, not the answer key."
        ),
        "human_role_short": "competitor",
        "calibrated": True,
        "calibration": (
            "TN-Eval released 150 notes that two therapists had already rated -- 50 "
            "written by a therapist, 50 by Llama 3.1 70B, 50 by Mistral Large V2. "
            "Every judge here answers those same questions about those same notes "
            "first, so how far it agrees with a person is a published number and "
            "not a hope."
        ),
    },
    results.TRACK_ICARE: {
        "scored_against": (
            "An expert note written by the clinician who saw the session. ROUGE-L "
            "and BERTScore measure how closely the model reproduced it; TRACE asks "
            "a judge to rate the note itself, the way the paper's experts did."
        ),
        "human_role": (
            "The expert note is the answer key and never competes. In the source "
            "paper the experts compared models with each other -- a smaller Mistral "
            "was preferred over the model leading on the automatic metrics -- and "
            "the expert note was what those metrics measured against, not an entry."
        ),
        "human_role_short": "answer key",
        "calibrated": False,
        "calibration": (
            "Not possible here. The authors' expert ratings are not in the public "
            "repository, so there is nothing to check this judge against. Two "
            "independent judges score every note instead, and where they disagree "
            "is the only control this track can have."
        ),
    },
    results.TRACK_PDSQI: {
        "scored_against": (
            "The note itself, and for two of the eight attributes the transcript as "
            "well -- accurate and thorough ask whether the note is true and complete, "
            "which cannot be answered without the session. There is no gold note, so "
            "this track is reference-free in the same sense the rubric track is."
        ),
        "human_role": (
            "The therapist's note is scored by the identical protocol and sits in the "
            "table as its own row, exactly as it does on the rubric track. That is "
            "the reason this table exists next to that one: the same notes, two "
            "instruments, and a reader can see where they disagree about who wrote "
            "well."
        ),
        "human_role_short": "competitor",
        # False, and the reason is not the reason iCARE is False. There the
        # ratings exist and are unpublished; here nobody has ever rated *these*
        # notes on this instrument. What PDSQI-9 does publish is a ceiling, which
        # is more than TRACE has and less than a calibration.
        "calibrated": False,
        "calibration": (
            "No human has rated these notes on this instrument, so there is no "
            "agreement figure for this judge. What the instrument publishes instead "
            "is a ceiling: trained physicians agreed with each other at "
            "Krippendorff's alpha 0.575, against the 0.18 two therapists reach on "
            "faithfulness. A judge cannot be asked to agree with a person better "
            "than people agree with each other -- but a ceiling is not a "
            "measurement, and these columns have not been checked against anyone."
        ),
    },
    results.TRACK_CZECH_REAL: {
        "scored_against": (
            "The note alone. Six yes/no questions about the Czech itself -- "
            "diacritics, calques, untranslated English terms, agreement, register, "
            "non-words -- and each column is the share of notes free of that "
            "fault. The judge is never shown the transcript, which is "
            "why a confidential session can be scored at all."
        ),
        "human_role": (
            "None. No human wrote a comparison note in Czech and no human has rated "
            "these notes on these criteria. That is one row this table does not have "
            "and the two English tables do."
        ),
        "human_role_short": "none",
        # False, and worse than either English track. iCARE has an expert note as
        # an answer key and unpublished ratings; PDSQI-9 publishes an inter-rater
        # ceiling. This instrument has neither -- it is one this repository wrote,
        # which is the thing pdsqi.py argues the project does not do. The answer
        # is that no Czech note-quality instrument exists to reproduce, and that
        # is a reason rather than an excuse.
        "calibrated": False,
        "calibration": (
            "Not possible yet, and weaker than either English track. There is no "
            "published Czech note-quality instrument to reproduce, so these criteria "
            "are this repository's own; no human has rated these notes on them, and "
            "unlike PDSQI-9 there is not even a published figure for how well two "
            "people would agree. Two independent judges answer every question, and "
            "where they disagree is the only control this track has -- which is also "
            "why a criterion every model passes is reported as unmeasured rather "
            "than as agreement."
        ),
    },
    results.TRACK_CZECH_TRANSLATED: {
        "scored_against": (
            "The same six criteria as the real-session table, on notes written "
            "from AnnoMI conversations translated into Czech. The translation is "
            "identical for every model, so it cancels when models are compared; it "
            "does not cancel for any claim about how well models write Czech."
        ),
        "human_role": (
            "None. No human wrote a comparison note in Czech and no human has rated "
            "these notes on these criteria. That is one row this table does not have "
            "and the two English tables do."
        ),
        "human_role_short": "none",
        "calibrated": False,
        "calibration": (
            "Not possible yet, for the reasons the real-session table gives. What "
            "this half adds is a join: the same conversations carry English numbers "
            "on the TN-Eval track, so a model's standing there and its Czech here "
            "are about the same sessions. Whether one predicts the other is the "
            "question this track was built to answer."
        ),
    },
    results.TRACK_CZECH_REAL_PDSQI: {
        "scored_against": (
            "The note alone, on six of PDSQI-9's eight attributes. The instrument "
            "and its prompt are reproduced in English; the note is Czech and is "
            "shown with the Czech headings the model wrote, because rendering it "
            "under English ones would rate an artefact nobody produced."
        ),
        "human_role": (
            "None. No human has rated these notes on PDSQI-9, and the therapist "
            "wrote no comparison note here."
        ),
        "human_role_short": "none",
        "calibrated": False,
        "calibration": (
            "Not calibrated. Physicians agree with each other on this instrument at "
            "Krippendorff's alpha 0.575, which is the ceiling any judge would be "
            "read against -- but nobody has rated these notes, so there is no "
            "agreement figure for this table, only the ceiling one would be read "
            "against if it existed."
        ),
    },
    results.TRACK_DEEPSY_REAL: {
        "scored_against": (
            "The note alone, on the same six Czech criteria as the SOAP tracks. "
            "The prompts are reproduced from the Deepsy application word for word, "
            "with its questionnaire blocks removed the way the application removes "
            "them for a client who has filled nothing in."
        ),
        "human_role": (
            "None. Nobody has rated these notes, and the therapist wrote no "
            "comparison note in this format either."
        ),
        "human_role_short": "none",
        "calibrated": False,
        "calibration": (
            "Not calibrated, like the Czech criteria it shares. What this track adds "
            "is not a calibration but a control: the same models and sessions in a "
            "second format, so that what a criterion measures about a model can be "
            "told apart from what it measures about the shape of the note."
        ),
    },
    results.TRACK_DEEPSY_TRANSLATED: {
        "scored_against": (
            "The note alone, on the same six criteria, over the translated AnnoMI conversations."
        ),
        "human_role": "None, in the same two senses as the real half.",
        "human_role_short": "none",
        "calibrated": False,
        "calibration": (
            "Not calibrated. Read against the Czech SOAP table on the same "
            "conversations, which is the comparison this track exists for."
        ),
    },
    results.TRACK_CZECH_TRANSLATED_PDSQI: {
        "scored_against": (
            "The note and the session, on all eight attributes. These transcripts "
            "are AnnoMI translated into Czech and carry nothing confidential, which "
            "is the whole reason `accurate` and `thorough` can be asked here and "
            "not of the real half."
        ),
        "human_role": (
            "None, in the same two senses as the real half: no comparison note and no human rating."
        ),
        "human_role_short": "none",
        "calibrated": False,
        "calibration": (
            "Not calibrated, and read against the same 0.575 ceiling. What this "
            "half adds is the join: the same conversations carry PDSQI-9 numbers in "
            "English on the `pdsqi-soap` track, so a model's quality there and its "
            "quality here are about the same sessions on the same instrument."
        ),
    },
}

#: Why similarity is not quality, shown rather than asserted.
#:
#: Both halves are verbatim from section 6 of held-out session 6, written by the
#: clinician who saw it and by `kimi-k3`. Verbatim matters: an abridged model
#: note shares proportionally more words with the expert and scores 0.238 where
#: the real one scores 0.111, which would have made the point look weaker than
#: it is. The score is computed from these strings on every render, so it cannot
#: drift away from the text beside it.
SIMILARITY_EXAMPLE = {
    "section": "Presenting symptoms",
    "session": "6",
    "model": "kimi-k3",
    "expert": (
        "1. Tingling sensation in stomach 2. Palpitations 3. Trembling hands "
        "4. Restlessness and inability to relax"
    ),
    "generated": (
        "**Presenting Symptoms:**\n\n1. Nervousness/anxiety before and during presentatio"
        "ns at weekly work meetings: few weeks; 2. Butterflies in stomach: few weeks; 3"
        ". Rapid heartbeat (heart beating faster): few weeks; 4. Sweaty palms: few week"
        "s; 5. Shaking/trembling hands: few weeks; 6. Shaky voice with stuttering and t"
        "ripping over words: few weeks; 7. Difficulty concentrating/zoning out during o"
        "thers' presentations due to self-focused attention on physical symptoms: few w"
        "eeks; 8. Persistent worry about negative evaluation by boss (post-presentation"
        " rumination about performance): few weeks; 9. Sadness and disappointment in se"
        "lf following presentations: few weeks; 10. Worry about coworkers' opinions of "
        "her: few weeks\n\n**Chief Complaints:**\n\n1. Nervousness when making presentation"
        "s during undergraduate college years: NA (historical; perceived as normal at t"
        "he time, did not impair performance or grades)"
    ),
    "note": (
        "Tingling in the stomach and butterflies in the stomach are the same symptom, "
        "as are palpitations and a rapid heartbeat; trembling hands appear in both. The "
        "model also records how long each symptom has lasted and when it occurs, which "
        "the expert note does not. It shares almost no *words* with the clinician, and a "
        "word-overlap metric scores it accordingly."
    ),
}


def similarity_example() -> dict:
    """The worked example with its ROUGE-L computed here rather than quoted."""
    from tnb.scoring.icare import rouge_l

    return {
        **SIMILARITY_EXAMPLE,
        "rouge_l": round(rouge_l(SIMILARITY_EXAMPLE["generated"], SIMILARITY_EXAMPLE["expert"]), 3),
    }


#: Order the sections of a row's breakdown so a reader sees SOAP in SOAP order
#: rather than alphabetically.
SECTION_ORDER = ("subjective", "objective", "assessment", "plan")

#: Where every input comes from and what its terms are, checked repository by
#: repository on 2026-08-24 rather than assumed. Published on the page because a
#: reader deciding whether to reuse any of this needs it before the numbers.
#: The published reference for each source, in APA form.
#:
#: Copied from `NOTICE`, which is where the check lives -- repository by
#: repository, 2026-08-24 -- rather than written here from memory. Where NOTICE
#: records "et al." this does too: a nineteen-name author list nobody in this
#: checkout has verified is a fabrication however plausible it looks, and the
#: rule this project holds itself to is that a source is asked, not assumed.
#:
#: Deliberately not in `PAYLOAD_FIELDS` in `tests/test_i18n.py`: a reference is
#: quoted, not authored, and is the same in both languages -- like the rubric
#: text, which is excluded there for the same reason.
LICENCES = [
    {
        "source": "PDSQI-9",
        "cite": (
            "Croxford, E., Gao, Y., Pellegrino, N., et al. (2025). Development and "
            "validation of the Provider Documentation Summarization Quality Instrument "
            "for Large Language Models. arXiv:2501.08977. Adapted from the Physician "
            "Documentation Quality Instrument: Stetson, P. D., Bakken, S., Wrenn, J. O., "
            "& Siegler, E. L. (2012). Applied Clinical Informatics, PMC3347480."
        ),
        "url": "https://arxiv.org/abs/2501.08977",
        "used_for": "the nine attributes and their anchors, eight of which are scored",
        # "arXiv preprint" is a venue, not a licence, and it was printed under a
        # heading that says Licence. `NOTICE` records the terms: CC BY 4.0, which
        # is what permits the verbatim reproduction the note beside it describes.
        "licence": "CC BY 4.0 (arXiv version)",
        "note": (
            "The instrument is reproduced verbatim, anchors included, so a score here "
            "answers the published question and not a rewritten one."
        ),
    },
    {
        "source": "TN-Eval (code)",
        "cite": (
            "Shah, R. S., Xu, L., Liu, Q., Burnsky, J., Bertagnolli, D., & Shivade, C. "
            "(2025). TN-Eval: Rubric and evaluation protocols for measuring the quality "
            "of behavioral therapy notes. ACL 2025, Industry Track."
        ),
        "url": "https://github.com/amazon-science/TN-Eval",
        "used_for": "SOAP prompt, the five scoring prompts, the 23-item rubric",
        "licence": "Apache-2.0",
        "note": "Reproduced verbatim in this repository, with attribution in NOTICE.",
    },
    {
        "source": "TN-Eval-Data",
        "cite": "Described in the TN-Eval paper above; the data repository publishes none.",
        "url": "https://github.com/amazon-science/TN-Eval-Data",
        "used_for": "150 notes and the ratings of two human annotators",
        "licence": "none published",
        "note": (
            "The Apache licence is on the code repository, not this one. Fetched at run "
            "time, never redistributed."
        ),
    },
    {
        "source": "AnnoMI",
        "cite": (
            "Wu, Z., Balloccu, S., Kumar, V., Helaoui, R., Reiter, E., "
            "Reforgiato Recupero, D., & Riboni, D. (2022). Anno-MI: A dataset of "
            "expert-annotated counselling dialogues. ICASSP 2022."
        ),
        "url": "https://github.com/uccollab/AnnoMI",
        "used_for": "the 133 transcripts, 50 of which are scored",
        "licence": "none published",
        "note": (
            "Released \u201cto benefit research community\u201d, with a citation "
            "requested. Fetched at run time."
        ),
    },
    {
        "source": "iCARE",
        "cite": (
            "Adhikary, P. K., Singh, S., Singh, S., Sharma, P., Soni, P., Choudhary, R., "
            "Saxena, C., Chauhan, P., Gupta, S. K., Deb, K. S., Singh, S. M., & "
            "Chakraborty, T. (2026). Clinically grounded AI-scribing in psychotherapy: "
            "Benchmarking LLMs against expert documentation in the iCARE framework. "
            "medRxiv 2025.06.25.25330252 (v2)."
        ),
        "url": "https://github.com/proadhikary/iCARE",
        "used_for": "the 17 section instructions",
        "licence": "none published",
        "note": (
            "No licence file and no statement of terms. The instructions are fetched at run time "
            "and never shown here."
        ),
    },
    {
        "source": "TheraFuse",
        # It does have a paper of its own; this said it did not. Verified at
        # Crossref on 2026-08-31: DOI 10.1109/jbhi.2026.3726138 returns the
        # title, the journal, the year and the six authors below.
        "cite": (
            "Adhikary, P. K., Mukherjee, A., Deb, K. S., Singh, S., Singh, S. M., & "
            "Chakraborty, T. (2026). Discourse-guided summarisation of psychotherapy "
            "dialogues via graph-fused language models. IEEE Journal of Biomedical and "
            "Health Informatics. https://doi.org/10.1109/JBHI.2026.3726138 -- it also "
            "carries the iHOPE corpus described in the iCARE paper above."
        ),
        "url": "https://github.com/ai4mhx/TheraFuse",
        "used_for": "the iHOPE transcripts and expert notes",
        "licence": "MIT badge, no LICENSE file",
        "note": (
            "A badge on a code repository, for a corpus collected elsewhere. Treated as no licence "
            "for the data."
        ),
    },
]


def _sort_key(row: Row, track: str):
    """Best first on the track's leading metric; unscored and unmeasured last.

    A track whose `RANKING_MEASURES` entry is None declines to be ranked -- the
    iCARE columns measure different things and the source paper found they
    disagree. The fallback to the first column overrode that refusal and sorted
    it by ROUGE-L anyway, so a page saying "deliberately not ranked" printed a
    ranking.

    An unmeasured row sorts with the unscored rather than as 0.0. Reading a
    missing measure as the worst possible score published `mistral-large-v2`
    last on a measure nobody had computed for it.
    """
    if not row.is_scored:
        return (1, 0.0, row.system_id)
    leading = RANKING_MEASURES.get(track)
    if leading is None:
        return (0, 0.0, row.system_id)
    value = row.metrics.headline.get(leading)
    if value is None:
        return (1, 0.0, row.system_id)
    return (0, -float(value), row.system_id)


def _ordered_sections(names: list[str]) -> list[str]:
    known = [name for name in SECTION_ORDER if name in names]
    rest = sorted(name for name in names if name not in SECTION_ORDER)
    return known + rest


#: Which instrument a column came from, for a table that draws two. Named
#: rather than inferred from the column key: a reader has to be able to see
#: which three of the eleven are the rubric's without knowing the rubric.
INSTRUMENT_LABELS = {
    results.TRACK_TNEVAL: "TN-Eval rubric",
    results.TRACK_PDSQI: "PDSQI-9",
    results.TRACK_ICARE: "iCARE",
}


def _table_id(table: dict) -> str:
    """A stable, readable name for one comparability group.

    Readable because it goes in the URL: a link to a particular judge's table
    should say which one. Stable because a reader who bookmarks it comes back
    to the same table, so it is derived from what makes the group a group and
    not from its position on the page.
    """
    versions = table["versions"]
    settings = versions.get("judge_settings") or {}
    parts = [
        table["track"],
        versions["judge_model"] or "unjudged",
        # One of the six fields that make a group a group, and it was missing.
        # Two rubric versions of one track under one judge produced two tables
        # with one id, and `build`'s collision assert -- written because the
        # author expected this -- stopped the page rather than drawing them.
        # Adding it changes every existing id, so a deep link into a table
        # bookmarked before this no longer resolves. That cost is paid once; a
        # colliding id is a link that silently goes to the wrong instrument.
        versions.get("judge_prompt_version") or "unrubriced",
        versions["harness_version"] or "0",
    ]
    if settings:
        # Two tables can share a judge and a harness and differ only here --
        # `gemini-2.5-pro` answered eleven systems at a thinking budget of 128
        # and three at 256. A digest rather than the settings themselves: the
        # settings are a mapping and the id has to survive being a URL.
        digest = hashlib.sha256(json.dumps(settings, sort_keys=True).encode("utf-8")).hexdigest()[
            :6
        ]
        parts.append(digest)
    return "-".join(re.sub(r"[^a-z0-9.]+", "-", str(part).lower()).strip("-") for part in parts)


def _settings_label(settings: dict | None, peers: list[dict] | None = None) -> str:
    """How a judge was set, in the fewest words that still say it.

    `model` and `backend` are dropped: the first is already the button's name
    and the second is how we reach it, not how it answered.

    With `peers` -- the other settings this one has to be told apart from --
    only the keys that actually differ are named. The two `gemini-2.5-pro`
    tables differ in one setting and agree on two, and printing all three puts
    `temperature 0` on both buttons to distinguish nothing.
    """
    settings = settings or {}
    interesting = [name for name in sorted(settings) if name not in ("model", "backend")]
    if peers:
        differing = [
            name
            for name in interesting
            if any(peer.get(name) != settings.get(name) for peer in peers)
        ]
        # Everything agrees: two tables the reader cannot tell apart from their
        # settings, which is worth saying rather than labelling both blank.
        interesting = differing or interesting
    return ", ".join(f"{name} {settings[name]}" for name in interesting)


def _selection(tables: list[dict]) -> dict:
    """Which table to draw, and what the reader may switch to.

    Judges are listed per track, so "a judge with no rows on this track" cannot
    be offered -- `gemini-2.5-pro` has TN-Eval rows and no iCARE ones, and a
    disabled button is an offer that cannot be accepted.

    A judge's settings appear on its button only when two tables on the same
    track share that judge's name. Printing them always would put
    `max_output_tokens 288, temperature 0, thinking_budget 256` on every button
    to disambiguate nothing.
    """
    from tnb import judge as judge_module

    tracks: list[dict] = []
    for table in tables:
        track = table["track"]
        found = next((item for item in tracks if item["track"] == track), None)
        if found is None:
            found = {
                "track": track,
                "label": TRACK_SWITCH_LABELS.get(track, track),
                "judges": [],
            }
            tracks.append(found)
        found["judges"].append(
            {
                "judge_model": table["versions"]["judge_model"],
                "label": table["versions"]["judge_model"] or "not yet scored",
                "settings": table["versions"].get("judge_settings") or {},
                "settings_label": "",
                "settings_differ": False,
                "table": table["id"],
                "stale_harness": table["stale_harness"],
            }
        )

    for item in tracks:
        names = [entry["judge_model"] for entry in item["judges"]]
        for entry in item["judges"]:
            entry["settings_differ"] = names.count(entry["judge_model"]) > 1
            peers = [
                other["settings"]
                for other in item["judges"]
                if other is not entry and other["judge_model"] == entry["judge_model"]
            ]
            entry["settings_label"] = (
                _settings_label(entry["settings"], peers) if entry["settings_differ"] else ""
            )
        # Only the labels reach the page; the mappings were scaffolding. Popped
        # after the loop, not inside it: an entry is another entry's peer, and
        # removing one while the rest are still being labelled loses the
        # comparison the labels are made of.
        for entry in item["judges"]:
            entry.pop("settings", None)
        # The judge the leaderboard is ranked by leads, then the panel's second,
        # then whatever else ran. `tables` is already ordered scored-first, so
        # anything not named keeps that order.
        preferred = (judge_module.DEFAULT_MODEL, judge_module.SECOND_JUDGE)
        item["judges"].sort(
            key=lambda entry: (
                preferred.index(entry["judge_model"])
                if entry["judge_model"] in preferred
                else len(preferred)
            )
        )
        item["default"] = item["judges"][0]["table"] if item["judges"] else ""

    return {
        "tracks": tracks,
        "default": tracks[0]["default"] if tracks else "",
    }


#: The two judges the site publishes from. A table from any other judge is
#: named rather than drawn -- see `_current_groups`.
PANEL = (judge.DEFAULT_MODEL, judge.SECOND_JUDGE)


def _current_groups(groups: dict[tuple, list[Row]]) -> tuple[dict[tuple, list[Row]], list[dict]]:
    """Split comparability groups into the ones to draw and the ones to name.

    Every group is a table, and two groups that differ only in `harness_version`
    are the same measurement under two definitions of the measures. Drawing both
    puts a model's old ROUGE-L beside its new one with nothing saying which is
    which -- the reader cannot tell a changed model from a changed metric.

    So the newest harness wins per (track, judge, judge prompt, generation
    prompt), and the rest is reported as a line: what it was, when, and how many
    rows. This is what `build`'s docstring has promised since it was written and
    what the code did not do.
    """

    # Unpacked by name rather than by position: `COMPARABILITY_KEYS` grew a
    # sixth field and every one of these lines broke at once, which is what
    # positional unpacking of a key that is allowed to grow buys.
    def field(key: tuple, name: str):
        return key[results.COMPARABILITY_KEYS.index(name)]

    #: Fields a lane is *not* keyed on -- the ones this function chooses
    #: between rather than separates by.
    #:
    #: `harness_version`, because that is the thing it was written to choose.
    #:
    #: `judge_settings`, because a row written before that field existed records
    #: none, and an absent record of the settings is not a different instrument
    #: -- it is the same instrument, less well described. Leaving it in the lane
    #: drew two identical Gemini tables side by side, one from each side of the
    #: commit that added it.
    #:
    #: `judge_prompt_version`, for the reason a superseded harness is chosen
    #: between: a rubric version is bumped when the questions change, and the
    #: older one is then a previous attempt at the same measurement rather than
    #: a second measurement worth drawing. The Czech tables showed this: two
    #: rubric versions produced four tables per track, two judge buttons each
    #: carrying the same words, and nothing on the page saying which button held
    #: the older questions. It stays in `COMPARABILITY_KEYS` -- two versions
    #: still may not be averaged -- and the older is now named rather than
    #: drawn, which is what the briefing already did and the tables did not.
    CHOSEN_BETWEEN = ("harness_version", "judge_settings", "judge_prompt_version")

    def lane_of(key: tuple) -> tuple:
        return tuple(
            field(key, name) for name in results.COMPARABILITY_KEYS if name not in CHOSEN_BETWEEN
        )

    def records_its_instrument(key: tuple) -> bool:
        """A group that names a judge has to say how that judge was set.

        Two rows that both record nothing are not thereby the same instrument;
        they are two rows that cannot say. The `gemini-2.5-pro` table was
        fourteen rows drawn from two instruments and ranked against each other
        for exactly that reason -- eleven e-INFRA systems answered at
        `thinking_budget` 128, and the therapist and TN-Eval's two reference
        models at 256, which is the very setting the rest of this repository
        argues reorders a leaderboard. Both halves recorded `null`, so the
        comparability key could not tell them apart.

        A group with no judge is generation coverage. It has no settings to
        record and is not a ranking, so the rule does not reach it.

        Read from a row, not from the key: the key holds the *serialised*
        mapping, and `"{}"` is a perfectly truthy string.
        """
        return not field(key, "judge_model") or bool(groups[key][0].judge_settings)

    def rank(key: tuple) -> tuple:
        # Newer harness wins; at the same harness, the newer rubric; at the same
        # rubric, the group that records its judge settings beats the one that
        # does not. Strictly more informative supersedes strictly less, which is
        # the same rule `latest` applies to a re-run.
        return (
            field(key, "harness_version"),
            field(key, "judge_prompt_version"),
            bool(groups[key][0].judge_settings),
        )

    # Only a drawable group can set the bar. A lane whose every group is
    # unpublishable leaves `best` empty for that lane, and nothing there is
    # superseded *by a harness* -- it is withdrawn for the other reason.
    best: dict[tuple, tuple] = {}
    for key in groups:
        if records_its_instrument(key):
            lane = lane_of(key)
            best[lane] = max(best.get(lane, ("", "", False)), rank(key))

    # Only where the panel actually has a table. A candidate judge's rows are the
    # only thing on a track nobody else has scored, and withdrawing them would
    # leave the track blank -- which is worse than an extra button.
    covered_by_panel = {
        field(key, "track")
        for key in groups
        if field(key, "judge_model") in PANEL and records_its_instrument(key)
    }

    keep: dict[tuple, list[Row]] = {}
    superseded = []
    for key, group in groups.items():
        harness = field(key, "harness_version")
        lane = lane_of(key)
        current = best.get(lane, ("", "", False))[0]
        current_rubric = best.get(lane, ("", "", False))[1]

        #: Why this group is not drawn. Both can be true at once, and reporting
        #: only the first produced the line "at harness 0.2.0 ... redefined in
        #: 0.2.0", which contradicts itself and names the wrong cause.
        reasons = []
        if not records_its_instrument(key):
            reasons.append("settings")
        # Every group tied at the best rank is kept, not one of them: two
        # genuinely different judge settings at the same harness are two
        # instruments and both belong on the page.
        if current and rank(key) < best[lane] and harness < current:
            reasons.append("harness")
        # A rubric that was superseded. Bumping `judge_prompt_version` means the
        # questions changed, so the older rows are a previous attempt at this
        # measurement rather than a second measurement -- named, not drawn beside
        # it. Its own reason rather than the harness one, because that rule
        # deliberately keeps two groups at the same harness so two different
        # judge settings can both be shown.
        rubric = field(key, "judge_prompt_version")
        if current_rubric and rubric and rubric < current_rubric:
            reasons.append("rubric")
        # A judge that was tried during calibration and not chosen. Its rows are
        # real and stay in `results/`, but the leaderboard is the panel's, and
        # `gemini-2.5-pro` put two extra tables of 11 and 3 rows behind the judge
        # switch -- two buttons offering a run nobody publishes from, one of them
        # differing from the other only in a thinking budget. `tnb judges` is
        # where the candidates belong, and it draws all of them.
        if (
            field(key, "judge_model")
            and field(key, "judge_model") not in PANEL
            and (field(key, "track") in covered_by_panel)
        ):
            reasons.append("not on the panel")

        if not reasons:
            keep[key] = group
            continue
        superseded.append(
            {
                "track": field(key, "track"),
                "harness_version": harness,
                "current_harness_version": current if "harness" in reasons else "",
                "current_judge_prompt_version": (current_rubric if "rubric" in reasons else ""),
                "judge_model": field(key, "judge_model"),
                "prompt_version": field(key, "prompt_version"),
                "judge_prompt_version": field(key, "judge_prompt_version"),
                "reasons": reasons,
                "rows": len(group),
                "scored_at": max((row.scored_at or "" for row in group), default=""),
            }
        )
    return keep, sorted(superseded, key=lambda item: (item["track"], item["harness_version"]))


def current_rows(rows: list[Row]) -> list[Row]:
    """The rows a table would draw: newest per identity, newest harness per lane.

    Anything reading rows for an analysis has to go through this. Reading them
    raw mixes two definitions of the same measure under one name -- every iCARE
    system appears twice right now, once at each harness -- and a dictionary
    keyed on the system silently keeps whichever came last.
    """
    groups, _superseded = _current_groups(results.comparable_groups(results.latest(rows)))
    return [row for group in groups.values() for row in group]


def _groups_for(versions: dict, saturations: list[dict]) -> dict | None:
    """The indistinguishable groups belonging to one table, or None.

    Matched on the **track**, the judge and the judge's settings. The same judge
    at two thinking budgets is two instruments, and drawing one's groups over the
    other's numbers is the error this file spends most of its comments on -- and
    the track was missing from that list, which is the same error one axis over.
    `saturation` analyses TN-Eval SOAP completeness over AnnoMI conversations and
    nothing else, so both iCARE tables were published with a Rank column ranking
    them by a different corpus on a measure they do not have, scattered over rows
    sorted by name, under a caption reading "over the 25 conversations every
    system here was scored on" -- on a track that ran 40.

    An analysis written before `track` was recorded is TN-Eval's, because that is
    the only thing this module has ever produced.
    """
    for item in saturations:
        if item.get("track", results.TRACK_TNEVAL) != versions.get("track"):
            continue
        if item.get("judge_model") != versions.get("judge_model"):
            continue
        recorded = item.get("judge_fingerprint")
        if recorded and versions.get("judge_settings") and recorded != versions["judge_settings"]:
            continue
        if not item.get("indistinguishable"):
            continue
        return {
            "measure": "completeness",
            "sessions": item.get("sessions"),
            "corpus_sessions": item.get("corpus_sessions"),
            "of": item["indistinguishable"],
        }
    return None


def _with_borrowed_reasons(rows: list[Row]) -> list[Row]:
    """Give a scored row the reason its coverage row already recorded.

    A count of unusable notes travels with the reason it was unusable. That is
    the rule, and `run.to_rows` follows it -- but only for rows written since it
    learned to. `results/` is append-only, so five rows drawn today were scored
    before that and carry `n_failed: 8` with `failure_reasons: {}`. The README
    prints "42/50 (8 unusable)" from them and the page says "8 note(s) missing,
    with no recorded reason", while the reason sits in `results/rows.jsonl` on
    the coverage row for the same model: eight answers that did not contain a
    SOAP dictionary.

    Repaired on the way in rather than fixed by re-scoring, for the reason
    `normalise_reason` is: an append-only file keeps what it was written with,
    and the fix has to be in the reading. It also means a future run that
    forgets to pass `n_unreached` publishes a reason anyway rather than an
    accusation.

    Only ever adds. A row that recorded its own reasons keeps them.
    """
    recorded = {
        (row.provider, row.system_id, row.track): row.failure_reasons
        for row in rows
        if not row.judge_model and row.failure_reasons
    }
    return [
        replace(row, failure_reasons=dict(found))
        if row.n_failed
        and not row.failure_reasons
        and (found := recorded.get((row.provider, row.system_id, row.track)))
        else row
        for row in rows
    ]


def _with_note_words(rows: list[Row]) -> list[Row]:
    """Give a scored row the note length its coverage row measured.

    `Settings.note_words` is a property of what the model wrote, not of the run
    that scored it, so it is measured once by `index_generations` and read from
    there. Borrowed rather than required, for the same reason the failure
    reasons are: `results/` is append-only and every row already on disk was
    written before the field existed.
    """
    measured = {
        (row.provider, row.system_id, row.track): row.settings.note_words
        for row in rows
        if not row.judge_model and row.settings.note_words
    }
    return [
        replace(row, settings=replace(row.settings, note_words=found))
        if row.settings.note_words is None
        and (found := measured.get((row.provider, row.system_id, row.track)))
        else row
        for row in rows
    ]


def _merge_instruments(tables: list[dict]) -> list[dict]:
    """Draw PDSQI-9 beside the rubric, in one table, for the SOAP notes.

    They rate **the same 942 notes** with the same judge at the same settings
    under the same harness: the only comparability field they differ on is
    `judge_prompt_version`, because they ask different questions about one
    corpus. Two tabs made a reader click between them to answer the question
    both were run for -- whether an instrument built to rate clinical notes
    agrees with the rubric that ranks the therapist last -- and a reader who has
    to hold eleven numbers in their head across a page reload does not answer it.

    **Side by side is not averaged in, and the difference is the whole rule.**
    `harness_version` and the six comparability keys are untouched: the rows
    still come from two groups and nothing is combined into a figure. What is
    merged is the drawing. `ranking_measure` stays the rubric's, so the band
    logic keeps reading the measure the saturation analysis was run on, and
    every column carries the instrument it came from so the page can head them
    separately.

    iCARE cannot join and does not: a different corpus, different notes, sixteen
    models against nineteen. Joining on `system_id` there would put two models'
    work in one row.
    """

    def instrument_key(table: dict) -> tuple:
        versions = table["versions"]
        return (
            versions["harness_version"],
            versions["prompt_version"],
            versions["judge_model"],
            json.dumps(versions["judge_settings"], sort_keys=True),
        )

    beside = {
        instrument_key(table): table
        for table in tables
        if table["track"] == results.TRACK_PDSQI and table["scored"]
    }
    absorbed: set[str] = set()
    for table in tables:
        if table["track"] != results.TRACK_TNEVAL or not table["scored"]:
            continue
        other = beside.get(instrument_key(table))
        if other is None:
            continue

        for column in table["columns"]:
            column.setdefault("instrument", INSTRUMENT_LABELS[table["track"]])
        added = []
        for column in other["columns"]:
            added.append({**column, "instrument": INSTRUMENT_LABELS[other["track"]]})
        table["columns"] = table["columns"] + added

        by_system = {row["system_id"]: row for row in other["rows"]}
        for row in table["rows"]:
            found = by_system.get(row["system_id"])
            # A system the second instrument has not rated keeps its dashes. It
            # is not dropped and its rubric figures are not touched: one
            # instrument having finished and the other not is a fact about the
            # run, not about the model.
            if found:
                row["headline"] = {**row["headline"], **(found.get("headline") or {})}

        # Both judge prompts, so the provenance line names what was actually
        # asked. A merged table that reported one of them would say the eight
        # PDSQI columns came from the rubric's prompt.
        table["judge_prompt_versions"] = [
            table["versions"]["judge_prompt_version"],
            other["versions"]["judge_prompt_version"],
        ]
        table["merged_from"] = [table["track"], other["track"]]
        # Both instruments named above the table they share. The terms came from
        # the absorbing track alone, so PDSQI-9 wrote eight of the eleven
        # columns and was defined nowhere a reader would meet it.
        known = {term["term"] for term in table.get("terms") or []}
        table["terms"] = (table.get("terms") or []) + [
            term for term in other.get("terms") or [] if term["term"] not in known
        ]
        # Both instruments named above the table they share. The terms came from
        # the absorbing track alone, so PDSQI-9 wrote eight of the eleven
        # columns and was defined nowhere a reader would meet it.
        known = {term["term"] for term in table.get("terms") or []}
        table["terms"] = (table.get("terms") or []) + [
            term for term in other.get("terms") or [] if term["term"] not in known
        ]
        table["title"] = "SOAP notes on AnnoMI · two instruments, the same notes"
        # Was three sentences establishing that eleven columns from two
        # instruments is a deliberate arrangement. A reader can see that it is
        # eleven columns. What they cannot see is that adding them up is
        # meaningless, so that is what the line says now.
        table["blurb"] = (
            "The first three columns count what a note contains — TN-Eval's "
            "rubric. The other eight rate how it is written — PDSQI-9. "
            "**Nothing is averaged across them**: different questions on "
            "different scales, and neither instrument publishes a total either."
        )
        absorbed.add(other["id"])

    return [table for table in tables if table["id"] not in absorbed]


def build(
    rows: list[Row],
    saturations: list[dict] | None = None,
    *,
    source: str | None = None,
) -> dict:
    """Shape the rows into the JSON both presentations read.

    `saturations` carries, per judge, which systems that judge's evidence
    cannot tell apart. Optional because a coverage-only build has none, and
    absent is drawn as "not measured for this table" rather than as agreement.

    Groups that disagree on any version field become separate tables rather than
    separate rows in one table. The newest harness per track and judge is drawn;
    older ones are named in `superseded` so a stale number is explainable rather
    than silently gone.
    """
    current = _with_note_words(_with_borrowed_reasons(results.latest(rows)))
    tables = []

    saturations = saturations or []
    groups, superseded = _current_groups(results.comparable_groups(current))
    newest_harness = max(
        (row.harness_version for group in groups.values() for row in group), default=""
    )
    for group in groups.values():
        # From a row rather than from the key: `comparability_key` serialises a
        # mapping so the tuple stays hashable, and the page needs the mapping.
        # Every row in the group agrees on these fields -- that is what makes it
        # a group -- so the first one speaks for all of them.
        versions = {name: getattr(group[0], name) for name in results.COMPARABILITY_KEYS}
        track = versions["track"]
        if track not in COLUMNS:
            continue
        rendered = [_render_row(row) for row in sorted(group, key=lambda r: _sort_key(r, track))]
        tables.append(
            {
                "track": track,
                "title": TRACK_TITLES.get(track, track),
                "blurb": TRACK_BLURBS.get(track, ""),
                "design": TRACK_DESIGN.get(track, {}),
                "terms": [
                    {"term": term, "gloss": gloss} for term, gloss in TRACK_TERMS.get(track, ())
                ],
                # Every comparability field, so a reader can see exactly what
                # this table's rows had to agree on. Named from the tuple
                # rather than listed here: the list grew a sixth entry once and
                # a hand-written copy would have quietly kept showing five.
                "versions": {
                    name: versions[name] for name in results.COMPARABILITY_KEYS if name != "track"
                },
                "scored": any(row.is_scored for row in group),
                # When this group was last judged. Per group and not per page:
                # four switchable tables carry different dates, and a
                # page-level string would be a second copy of the run line.
                #
                # Omitted entirely when no row in the group carries one --
                # 1133 of 2161 rows on disk carry none, and dating a group from
                # the subset that happens to have a date is the shape this
                # project refuses everywhere else.
                "scored_at": max((row.scored_at or "") for row in group)[:10],
                # Which systems this evidence cannot tell apart, from the
                # saturation analysis of *this* table's judge at *these*
                # settings. None when nobody has run it for this table, and
                # the table then says so rather than reading as a strict
                # ranking -- a first row that looks like a winner is the whole
                # thing this is here to stop.
                "groups": _groups_for(versions, saturations),
                # True when this table's measures are defined by an older
                # harness than the newest one on the page. A judge that was
                # tried and not re-run keeps its table -- a different judge is
                # a different table, which is this project's rule -- but the
                # reader has to be told its columns may not mean the same thing
                # as the columns above it.
                "stale_harness": versions["harness_version"] != newest_harness,
                "columns": [
                    {**column_meta(track, key_), "digits": digits}
                    for key_, digits in COLUMNS[track]
                ],
                "ranking_measure": RANKING_MEASURES.get(track),
                "detail_label": DETAIL_LABELS.get(track, "Rubric criteria"),
                "not_ranked_reason": NOT_RANKED_REASONS.get(
                    track, NOT_RANKED_REASONS[results.TRACK_ICARE]
                ),
                "rows": rendered,
                # Drawn only where something to show exists. A column of empty
                # cells is worse than no column: it reads as missing data rather
                # than as a control this provider does not have.
                "has_effort": any(row["effort"] for row in rendered),
                "has_words": any(row["note_words"] for row in rendered),
            }
        )

    # A system with a score has no business appearing in the "not yet scored"
    # table as a row of dashes: it *is* scored, and showing it twice reads as a
    # missing measurement rather than as two version sets. Its coverage row
    # stays in results/ -- this only decides what the page draws.
    scored_systems = {
        (table["track"], table["versions"]["prompt_version"], row["provider"], row["system_id"])
        for table in tables
        if table["scored"]
        for row in table["rows"]
        if row["scored"]
    }
    for table in tables:
        if table["scored"]:
            continue
        table["rows"] = [
            row
            for row in table["rows"]
            if (
                table["track"],
                table["versions"]["prompt_version"],
                row["provider"],
                row["system_id"],
            )
            not in scored_systems
        ]
    tables = [table for table in tables if table["rows"]]

    for table in tables:
        # Two tables can carry the same title and differ only in whether a judge
        # has seen them. Saying so in the heading stops the page reading as a
        # duplicate -- which is exactly how it read before.
        judge = table["versions"]["judge_model"]
        table["subtitle"] = f"scored by {judge}" if judge else "not yet scored"

    # Scored tables lead. A queue of systems nobody has judged yet is context,
    # not a leaderboard, and printing it above the numbers is how a reader ends
    # up asking why the benchmark is empty when it is not.
    tables.sort(
        key=lambda table: (
            table["track"] != results.TRACK_TNEVAL,
            not table["scored"],
            table["versions"]["prompt_version"],
        )
    )
    for table in tables:
        table["id"] = _table_id(table)
    # Two tables with one id would silently draw the same one twice, and the
    # reader would see a switch that does nothing.
    assert len({table["id"] for table in tables}) == len(tables), "table ids collide"

    # After the ids, because absorbing a table is done by id, and before
    # `_selection`, which decides what the switch offers.
    tables = _merge_instruments(tables)

    # Withdrawn groups count too. `superseded` names a track on the page --
    # "this was published and is not any more" -- and a reader who reads that
    # name still needs to know what it was measured with. A page that names
    # PDSQI-9 and links nothing is the same gap as one that credits a source
    # it never used, pointing the other way.
    drawn = {table["track"] for table in tables}
    drawn |= {entry["track"] for entry in superseded if entry.get("track")}
    return {
        "tables": tables,
        # Which one to draw and what may be switched to. Decided here, because
        # every other ordering on this page is.
        "selection": _selection(tables),
        # Not drawn, but named. A number that used to be published and is not
        # any more should be explainable rather than silently gone.
        "superseded": superseded,
        "protocol": protocol(drawn),
        "corpus": _corpus_for(drawn),
        "licences": [
            licence for licence in LICENCES if _used_by(LICENCE_TRACKS, licence["source"], drawn)
        ],
        # The file these numbers came out of, not the published one. The
        # Czech page is built from a different record and used to name
        # `rows.jsonl` anyway, which is the one claim a provenance line
        # must never get wrong.
        "generated_from": source or str(results.ROWS_PATH.name),
        # None on the published page, which keeps the header the template
        # was written with.
        "page": PAGE_CZECH if drawn & CZECH_PAGE_TRACKS else None,
    }


def _corpus_for(drawn: set[str]) -> dict | None:
    """The corpus profile, with the datasets this page does not use removed.

    Everything in the profile other than `datasets` describes iHOPE -- the fill
    rate, the seventeen sections and their headings -- so a page with no iCARE
    table keeps the dataset medians and drops the rest rather than printing a
    corpus nothing on it was measured on.
    """
    profile = corpus.load_or_build()
    if not profile:
        return profile
    datasets = {
        name: block
        for name, block in (profile.get("datasets") or {}).items()
        if _used_by(DATASET_TRACKS, name, drawn)
    }
    if _used_by(DATASET_TRACKS, "icare", drawn):
        return {**profile, "datasets": datasets}
    return {"datasets": datasets} if datasets else None


def protocol(drawn: set[str] | None = None) -> dict:
    """What a note is and what the judge is asked, straight from the source.

    Both come out of the modules that hold TN-Eval's own wording, so the page
    can never drift from what was actually sent to the models and the judge.
    """
    sections = []
    for line in soap.PROMPT_TEMPLATE_SOAP.splitlines():
        if line.startswith("- ") and ":" in line:
            name, _, description = line[2:].partition(":")
            sections.append({"name": name.strip(), "description": description.strip()})

    criteria = []
    for key, text in rubric.CHECKBOX_MAPPING.items():
        section, _, _slug = key.partition("-")
        title, _, description = text.partition(":")
        criteria.append(
            {
                "key": key,
                "section": section,
                "title": title.strip(),
                "description": description.strip(),
            }
        )

    icare_sections = [
        {
            "number": number,
            "title": title,
            "description": description,
            "temporal": number in ihope_temporal(),
        }
        for number, (title, description) in enumerate(icare.SECTIONS, start=1)
    ]

    # Empty rather than absent: the page checks the length and skips the
    # block, and a missing key would be a TypeError in the renderer instead.
    here = drawn if drawn is not None else set(results.TRACKS)
    return {
        "sections": sections if _used_by(PROTOCOL_TRACKS, "sections", here) else [],
        "criteria": criteria if _used_by(PROTOCOL_TRACKS, "criteria", here) else [],
        "icare_sections": (
            icare_sections if _used_by(PROTOCOL_TRACKS, "icare_sections", here) else []
        ),
    }


def ihope_temporal() -> tuple[int, ...]:
    from tnb.datasets import ihope

    return ihope.TEMPORAL_SECTIONS


def _judges_own_family(row: Row) -> str:
    """The vendor this row's judge shares with the system it scored, or "".

    `docs/limitations.md` has promised since the second judge was added that
    these cells are "marked in the table where they sit", and nothing marked
    them -- not `renderTable`, not the row data it draws from.

    What the mark warns about is a lean, not a verdict. Each judge rates its own
    vendor about 0.02 completeness higher -- +0.018 for `gemini-3.1-pro-preview`
    and +0.027 for `gpt-5.6-terra` -- and once the models are resampled as well
    as the conversations, neither interval clears zero, so `preference.py`
    reports `detected: false` for both. This docstring used to call the +0.027
    "detected", which was true only of an earlier estimator that resampled
    conversations alone and so treated four models as the whole of OpenAI.

    The row is marked, never dropped. A missing row would be the worse
    distortion, and a reader who can see which cells to discount can do the
    arithmetic the panel does not do for them.
    """
    from tnb.scoring.preference import family_of

    if not row.judge_model:
        return ""
    family = family_of(row.judge_model)
    return family if family and family_of(row.system_id) == family else ""


def _render_row(row: Row) -> dict:
    return {
        "system_id": row.system_id,
        "label": row.label,
        "system_type": row.system_type,
        "provider": row.provider,
        "effort": row.settings.effort,
        # In its own column, not only in the row's detail. Two models compared
        # on one line spent 1620 and 13 tokens thinking before writing, and a
        # reader who cannot see that is comparing two different experiments.
        # A column, not a caveat. Completeness counts coverage, so a longer note
        # covers more; publishing the length lets a reader see that for
        # themselves without the page asserting a correlation that turned out to
        # hold under one judge and not the other.
        "note_words": row.settings.note_words,
        "settings": row.settings.summary,
        # A row produced under conditions the rest of the table did not share is
        # marked in place rather than dropped or silently normalised -- WMT's
        # convention for systems that used extra resources. The forced
        # temperature on the GPT family is exactly this case.
        "settings_differ": bool(row.settings.temperature_forced),
        # Empty unless the judge and the system it scored come from one vendor.
        "judges_own_family": _judges_own_family(row),
        "n_attempted": row.n_sessions_attempted,
        "n_generated": row.n_sessions_generated,
        "n_scored": row.n_sessions_scored,
        # How many of those the headline actually rests on. Without it the page
        # said "the scores above are over the N finished so far" with an N that
        # counted notes the judge started and did not finish.
        "n_partial": row.n_sessions_partial,
        "n_complete": row.n_sessions_scored - row.n_sessions_partial,
        "n_failed": row.n_failed,
        "failure_reasons": row.failure_reasons,
        "unreached_reasons": row.unreached_reasons,
        "n_unreached": sum(row.unreached_reasons.values()),
        "headline": row.metrics.headline,
        "by_section": row.metrics.by_section,
        # The order, carried beside the mapping rather than in it. A mapping's
        # key order survives no serialiser -- this payload is written with
        # `sort_keys=True`, which is what makes a re-run produce no diff -- and
        # SOAP is an acronym whose letters are the sequence.
        "section_order": _ordered_sections(list(row.metrics.by_section)),
        "detail": row.metrics.detail,
        "metrics_note": row.metrics_note,
        "source": row.source,
        "scored": row.is_scored,
        "generated_at": row.generated_at,
        "scored_at": row.scored_at,
    }


# --- README -----------------------------------------------------------------


def _ranking_label(table: dict) -> str:
    """The heading of the column a table is ordered by, read from the table."""
    for column in table["columns"]:
        if column["key"] == table["ranking_measure"]:
            return column["label"]
    return table["ranking_measure"] or ""


def _readme_tables(data: dict) -> tuple[list[dict], list[dict]]:
    """One table per track to print, and the rest to name.

    Five tables filled 157 of the README's 385 lines -- the complaint the split
    answered on the site, left standing in the view most people read. A file
    cannot have a switch, so it shows the judge the site opens with and says
    where the others are.

    The choice is `selection`'s, not a second rule here: the site and the README
    must open on the same table or a reader following the link finds different
    numbers from the ones they came for.
    """
    by_id = {table["id"]: table for table in data["tables"]}
    opening = {
        track["default"]
        for track in data.get("selection", {}).get("tracks", [])
        if track.get("default")
    } or {table["id"] for table in data["tables"]}

    drawn = [table for table in data["tables"] if table["id"] in opening]
    named = [table for table in data["tables"] if table["id"] not in opening]
    # A table of nothing but reference rows is not printed by the loop below
    # either, so naming it would advertise an empty grid.
    named = [
        table for table in named if any(row["system_type"] == "model" for row in table["rows"])
    ]
    return (drawn or list(by_id.values()), named)


def render_readme_section(data: dict) -> str:
    """The shop window: e-INFRA models only, headline numbers only.

    Anyone who wants the breakdown follows the link to the page. Putting 23
    criteria in a README is how a README stops being read.

    A table with nothing scored in it is written out as a sentence rather than
    as a grid of dashes under score headings -- the same reason the page draws a
    queue instead of a scoreboard, applied to the view that was missed when the
    page was fixed.
    """
    if not data["tables"]:
        return "*No runs yet. The first run will populate this section automatically.*"

    drawn, named = _readme_tables(data)

    blocks: list[str] = []
    for table in drawn:
        models = [row for row in table["rows"] if row["system_type"] == "model"]
        if not models:
            continue

        if not table["scored"]:
            names = ", ".join(f"`{row['label']}`" for row in models)
            blocks.append(
                f"**{table['title']}** — *waiting for the judge.* "
                f"Notes are written and nothing is scored yet. Systems waiting: "
                f"{len(models)}, namely {names}."
            )
            continue

        columns = table["columns"]
        multi_provider = len({row["provider"] for row in models}) > 1
        header = ["Model"]
        if multi_provider:
            header.append("Provider")
        # The range goes in the heading. This table puts a 0-1 fraction beside a
        # 1-5 rating, and a reader with no scale has no reason to think 4.98 and
        # 0.65 are not the same kind of number.
        header += [f"{column['label']} ({column['scale']})" for column in columns]
        header += ["Notes", "Scored"]
        # The judge's name is part of the title here, not a footnote. Three
        # tables read "TN-Eval SOAP - AnnoMI conversations" and carried
        # different numbers for the same model, and README is the view nobody
        # scrolls back up in to find out why.
        lines = [
            f"**{table['title']}** — {_judge_line(table)}",
            "",
            "| " + " | ".join(header) + " |",
            "|" + "---|" * len(header),
        ]
        for row in models:
            cells = [f"`{row['label']}`"]
            if multi_provider:
                cells.append(row["provider"])
            for column in columns:
                value = row["headline"].get(column["key"])
                cells.append("—" if value is None else f"{value:.{column['digits']}f}")
            written = f"{row['n_generated']}/{row['n_attempted']}"
            # Two different gaps, named apart. "unusable" is the model's own
            # doing; "unreached" is the endpoint refusing, and charging that to
            # the model is what published glm-5 as "39/40 (1 unusable)" over a
            # rate limit. The JSON and the page have said both since; README
            # could only ever say the accusation.
            gaps = []
            if row["n_failed"]:
                gaps.append(f"{row['n_failed']} unusable")
            if row["n_unreached"]:
                gaps.append(f"{row['n_unreached']} unreached")
            if gaps:
                written += f" ({', '.join(gaps)})"
            cells.append(written)
            cells.append(_scored_cell(row))
            lines.append("| " + " | ".join(cells) + " |")

        # The caveat travels with the table rather than with a footnote marker
        # further down the file. README is the view most people read and the one
        # nobody scrolls, so a column that must not be read as a ranking says so
        # right here, under the numbers it applies to.
        lines.append("")
        lines.append(
            f"*Ordered by **{_ranking_label(table)}**. Every other column is context.*"
            if table["ranking_measure"]
            else "*Deliberately not ranked: these columns measure different things and "
            "the source paper found they disagree.*"
        )
        # A caveat every column of one instrument shares is that instrument's,
        # not the column's. PDSQI-9's 47 words were repeated under all eight of
        # its columns here, exactly as they were on the page. Said once, in the
        # same place and by the same rule, so the two views agree.
        shared: dict[str, str] = {}
        for name in {c["instrument"] for c in columns if c.get("instrument") and c["caveat"]}:
            same = [c["caveat"] for c in columns if c.get("instrument") == name and c["caveat"]]
            if len(same) > 1 and len(set(same)) == 1:
                shared[name] = same[0]
        said: set[str] = set()
        for column in columns:
            instrument = column.get("instrument") or ""
            if instrument in shared and instrument not in said:
                said.add(instrument)
                lines.append(f"- **{instrument} columns** — {shared[instrument]}")
            note = f"**{column['label']}** ({column['scale']}) — {column['definition']}"
            if column["caveat"] and shared.get(instrument) != column["caveat"]:
                note += f" {column['caveat']}"
            lines.append(f"- {note}")
        blocks.append("\n".join(lines))

    # Above the link, below the tables: it changes how the tables should be
    # read, and a README reader who stops at the first table has still seen the
    # numbers. Saying it here is the least this view can do.
    for track, found in (data.get("concordance") or {}).items():
        blocks.append(f"**Do the two judges agree?** ({TRACK_TITLES.get(track, track)})")
        blocks.append(found["summary"])

    # Named, not drawn. A number that was published and is not any more
    # should be explainable; a reader who remembers a different figure needs
    # to see that the measure changed, not wonder whether the model did.
    for gone in data.get("superseded", []):
        blocks.append(f"*{_superseded_sentence(gone)}*")

    # Named, with a link each. Nothing is hidden by printing one table per
    # track -- it is moved to the page, which has a switch, from a file that
    # cannot have one.
    if named:
        lines = [
            f"- **{table['title']}**, {_judge_line(table)} — [open it]({SITE_URL}#{table['id']})"
            for table in named
        ]
        blocks.append(
            "**Also scored, and not printed here.** Two judges are two instruments and "
            "two tables; the site draws one at a time and this file cannot, so it shows "
            "the one the site opens with.\n" + "\n".join(lines)
        )

    blocks.append(
        f"See the [full leaderboard]({SITE_URL}) for per-section detail, the reference "
        f"systems and the published numbers, and "
        f"[how it was measured]({SITE_URL}methods.html) for the judge, the corpora and "
        f"what the two judges disagree about."
    )
    return "\n\n".join(blocks)


def _judge_line(table: dict) -> str:
    """Which instrument scored this table, name and settings both.

    Measured on this benchmark: the same judge at a thinking budget of 128 and
    of 256 moved completeness by +0.017 on every system. "scored by
    gemini-3.1-pro-preview" names two instruments the same way.
    """
    settings = ", ".join(
        f"{key} {value}"
        for key, value in sorted((table["versions"].get("judge_settings") or {}).items())
        if key != "model"
    )
    line = table["subtitle"] + (f" ({settings})" if settings else "")
    if table.get("stale_harness"):
        line += (
            f" — measured by harness `{table['versions']['harness_version']}`, "
            f"whose columns may not mean what the newer tables' columns mean"
        )
    return line


def _superseded_reasons(gone: dict) -> list[str]:
    """The clauses that say why, one per reason, in Markdown.

    A group can be withdrawn for both reasons at once. Reporting only the first
    printed "at harness `0.2.0` ... redefined in `0.2.0`", which contradicts
    itself and blames the wrong thing.
    """
    said = {
        "harness": (
            f"the measures were redefined in `{gone.get('current_harness_version')}` "
            "and the two are not comparable"
        ),
        "rubric": (
            "the questions were rewritten in "
            f"`{gone.get('current_judge_prompt_version')}`, so these rows answer an "
            "earlier version of them"
        ),
        "settings": (
            "the judge's settings were not recorded, so the rows cannot be shown to "
            "have come from one instrument"
        ),
        "not on the panel": (
            "this judge was tried during calibration and is not one of the two the "
            "leaderboard publishes from -- every candidate is compared against the two "
            "human annotators under *Which judge* on the methods page"
        ),
    }
    # Older rows carry no `reasons`; before this field existed there was only one.
    return [said[name] for name in gone.get("reasons") or ["harness"] if name in said]


def _superseded_sentence(gone: dict) -> str:
    """Why a group of rows stopped being drawn, in one sentence.

    A group with no judge is coverage -- what was generated, before anything was
    scored -- and calling those "scored by None" was both ugly and untrue.
    """
    what = f"scored by `{gone['judge_model']}`" if gone["judge_model"] else "of generation coverage"
    return (
        f"{gone['rows']} {gone['track']} row(s) {what} at harness "
        f"`{gone['harness_version']}` are no longer shown: "
        # "; and" rather than "and": each reason already contains one, and two
        # joined by a third read as a single run-on clause.
        f"{'; and '.join(_superseded_reasons(gone))}. They stay in `results/rows.jsonl`."
    )


def _scored_cell(row: dict) -> str:
    """Judging progress, which is not the same thing as generation coverage.

    A model that wrote every note but is half-way through being judged must not
    read as a model that failed to write them.
    """
    if row["n_scored"] >= row["n_generated"]:
        return f"{row['n_scored']}"
    return f"{row['n_scored']} of {row['n_generated']} *(judging)*"


def update_readme(
    section: str, path: Path | None = None, markers: tuple[str, str] | None = None
) -> bool:
    """Replace one marked block. Returns whether anything changed."""
    path = path or README_PATH
    begin, end = markers or LEADERBOARD_MARKERS
    existing = path.read_text(encoding="utf-8")

    head, marker, rest = existing.partition(begin)
    if not marker:
        raise RuntimeError(f"{path.name} has no {begin} marker.")
    _, end_marker, tail = rest.partition(end)
    if not end_marker:
        raise RuntimeError(f"{path.name} has no {end} marker.")

    updated = f"{head}{begin}\n{section}\n{end}{tail}"
    if updated == existing:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def _load_json(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def load_calibration(docs_dir: Path | None = None) -> dict | None:
    """The last calibration, if one has been run. The page shows it above all else."""
    path = (docs_dir or DOCS_DIR) / CALIBRATION_PATH.name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write(rows: list[Row], *, docs_dir: Path | None = None, readme: Path | None = None) -> dict:
    """Write all three artefacts. Returns the data that was rendered."""
    docs_dir = docs_dir or DOCS_DIR
    saturations = load_saturations(docs_dir)
    data = build(rows, saturations)
    data["calibration"] = load_calibration(docs_dir)
    data["similarity_example"] = similarity_example()
    # The panel shows one, and it is the judge the leaderboard is ranked by
    # rather than whichever file sorted first.
    from tnb import judge as judge_module

    data["saturation"] = next(
        (item for item in saturations if item.get("judge_model") == judge_module.DEFAULT_MODEL),
        saturations[0] if saturations else None,
    )
    data["judges"] = _load_json(docs_dir / JUDGES_PATH.name)
    data["preference"] = _load_json(docs_dir / PREFERENCE_PATH.name)
    # Computed here rather than cached in docs/, because it is a statement about
    # the rows being rendered right now. A stale copy of "the judges disagree
    # about 11 of 19" beside a table where they no longer do is worse than none.
    # From the rows a table would draw, not from every row in the file. Two
    # harness versions carry two definitions of the same column.
    data["concordance"] = concordance_payload(rows)

    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / DATA_PATH.name).write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    (docs_dir / PAGE_PATH.name).write_text(render_page(data), encoding="utf-8")
    (docs_dir / METHODS_PATH.name).write_text(render_methods(data), encoding="utf-8")
    update_readme(render_readme_section(data), readme)
    return data


#: Characters that are legal in JSON and fatal inside a <script> element.
#:
#: `json.dumps` does not escape `<`, so a string containing a closing script tag
#: ends the block early and the rest of the page never runs. That string is not
#: hypothetical: `failure_reasons` keys are provider error bodies kept verbatim,
#: and one HTML error page from e-INFRA would blank the whole leaderboard rather
#: than fail loudly. U+2028 and U+2029 are the same problem in JavaScript, where
#: they are line terminators inside a string literal.
_INLINE_ESCAPES = {
    "<": "\\u003c",
    ">": "\\u003e",
    "&": "\\u0026",
    " ": "\\u2028",
    " ": "\\u2029",
}


def _inline(data: dict) -> str:
    """The payload, safe to sit inside a `<script>` element."""
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
    for char, escape in _INLINE_ESCAPES.items():
        payload = payload.replace(char, escape)
    return payload


def concordance_payload(rows: list[Row], **overrides) -> dict:
    """What the two judges' tables say when read together, per track.

    Computed rather than cached: it is a statement about the rows being
    rendered right now, and a stale "the judges disagree about 11 of 19" beside
    a table where they no longer do is worse than none.

    From the rows a table would draw, not every row in the file: two harness
    versions carry two definitions of the same column.

    A function rather than four lines inside `write`, because three tests built
    their own copy of those four lines -- so a field added here reached the
    page and not them, and the test that checks the page's labelling failed for
    want of a label rather than for want of the labelling.
    """
    drawn = current_rows(rows)
    return {
        # The track's own title travels with it. The panel draws one section
        # per track and named neither, which was invisible with one track and
        # is two unlabelled tables with two.
        track: {
            **found,
            "track": track,
            "track_label": TRACK_TITLES.get(track, track),
            # Whether the measures this panel leaves out are computed without a
            # judge. On iCARE they are -- ROUGE-L, BERTScore and the two
            # temporal columns come from the note and the expert note -- and
            # the panel says so. On TN-Eval the excluded pair is the Likert
            # forms of two drawn columns, which are a judge's opinion kept out
            # of the table, so the same sentence printed there was false; on
            # PDSQI-9 nothing is excluded at all and it had no referent.
            "excluded_are_computed": bool(
                set(MEASURE_TABLES.get(track, {})) - set(JUDGE_MEASURES.get(track) or ())
            )
            and not INTERNAL_MEASURES.get(track),
        }
        for track in COLUMNS
        if (
            found := concordance.to_json(
                concordance.compare(
                    drawn,
                    track,
                    COLUMNS[track],
                    judge_measures=JUDGE_MEASURES.get(track),
                    ranking_measure=RANKING_MEASURES.get(track),
                    **overrides,
                )
            )
        )
    }


def _localise(page: str) -> str:
    """The Czech lookup, inlined the same way the payload is.

    Not part of the payload, on purpose: `docs/leaderboard.json` is also the
    mirror API, and a machine reading the numbers has no use for a second
    language's wording of the caveats. It is a property of the page.
    """
    return page.replace("__I18N__", _inline(i18n.dictionary()))


def render_page(data: dict) -> str:
    """The standalone page: the data inlined, no build step, no dependency."""
    return _localise(PAGE_TEMPLATE.replace("__DATA__", _inline(data)))


def render_methods(data: dict) -> str:
    """The same payload, drawn as the method behind the tables.

    One payload rather than two. A methods page computed separately could
    describe a run the leaderboard is not showing, and the whole reason this
    page exists is to be checkable against the tables beside it.
    """
    page = METHODS_TEMPLATE
    # Read here rather than at import: `tools/figures.py` may run after this
    # module was imported, and the page should pick up the newer drawing.
    for marker, name in FIGURE_MARKERS.items():
        if marker in page:
            page = page.replace(marker, _figure(name))
    return _localise(page.replace("__DATA__", _inline(data)))


TEMPLATE_DIR = Path(__file__).parent / "templates"

#: Fragments both pages need, inserted at the marker each is named for. Shared
#: rather than copied: the leaderboard and the methods page draw the same tables
#: with the same escaping and the same number formatting, and two copies of a
#: stylesheet drift the first time one of them is edited.
#:
#: Assembly is two `str.replace` calls, the same build step `__DATA__` already
#: uses. No new dependency and no new file format -- each page stays a single
#: self-contained HTML file once rendered.
PARTIALS = {
    "__STYLE__": "_style.html",
    "__HELPERS__": "_helpers.html",
}


#: Figures the pages inline, by marker. Written by `tools/figures.py`, which is
#: not part of this package -- so a page that wants one gets it when it exists
#: and nothing when it does not, the same contract `load_calibration` has.
#:
#: Inlined rather than linked: the pages are single files that open from
#: anywhere, and an `<img src>` would end that. Substituted here rather than
#: carried in the payload, because the payload is also `docs/leaderboard.json`
#: and a mirror API has no business holding a drawing.
FIGURE_MARKERS = {"__FIGURE_ROOM_LEFT__": "room-left.svg"}


def _figure(name: str) -> str:
    """One published figure, or nothing at all."""
    path = DOCS_DIR / "figures" / name
    if not path.exists():
        return ""
    svg = path.read_text(encoding="utf-8")
    return svg[svg.index("<svg") :]


def _assemble(name: str) -> str:
    """One template with its partials inlined, ready for `__DATA__`."""
    text = (TEMPLATE_DIR / name).read_text(encoding="utf-8")
    for marker, partial in PARTIALS.items():
        if marker in text:
            text = text.replace(marker, (TEMPLATE_DIR / partial).read_text(encoding="utf-8"))
    return text


PAGE_TEMPLATE = _assemble("leaderboard.html")
METHODS_TEMPLATE = _assemble("methods.html")
