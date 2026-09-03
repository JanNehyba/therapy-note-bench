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

from tnb import corpus, judge, results
from tnb.config import REPO_ROOT, write_published
from tnb.results import Row
from tnb.scoring import calibration, composite, concordance, edges, pdsqi
from tnb.scoring import icare as icare_scorer
from tnb.scoring import tneval as rubric
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


def load_roster(docs_dir: Path | None = None) -> dict | None:
    """What the endpoints served when they were last asked, or None.

    None where `tnb roster` has never run, and then the page says nothing about
    any endpoint rather than implying every row is current. An absence of the
    check is not a clean bill.
    """
    return _load_json((docs_dir or DOCS_DIR) / ROSTER_PATH.name)


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
#: Whether the judges answer the same question the same way twice. Written by
#: `tnb repeatability`, which reads two answer caches and asks nobody; read
#: here like the two above, and absent until the repeat has been run.
REPEATABILITY_PATH = DOCS_DIR / "repeatability.json"

#: What the endpoints served, and when they were asked. Written by `tnb roster`,
#: which needs three credentials; read here, which must not, because `make test`
#: is offline and `tnb report` runs in it.
ROSTER_PATH = DOCS_DIR / "roster.json"

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
        # Two decimals: each is a share of 34 or 11 sessions, so the third
        # place is a digit that cannot exist, and printing it let two rows
        # that differ by one session look further apart than they are.
        ("temporal_past", 2),
        ("temporal_next", 2),
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
}

#: Every table is ordered the same way: by the mean of each system's places over
#: the columns of its own instrument (`scoring.composite`). One rule for all
#: three tracks, named per track so that a fourth track has to say so here.
ORDERINGS: dict[str, str] = {
    results.TRACK_TNEVAL: composite.RULE,
    results.TRACK_ICARE: composite.RULE,
    results.TRACK_PDSQI: composite.RULE,
}

#: The one column per track that has been checked against people, or None.
#: This used to be the sort key. It orders nothing now -- the order is a mean
#: of places over every column -- but it is still the only column with a human
#: anchor, and the page says so beside it rather than letting a reader assume
#: the whole table has one.
ANCHORED_MEASURES: dict[str, str | None] = {
    results.TRACK_TNEVAL: rubric.RANKING_MEASURE,
    results.TRACK_ICARE: icare_scorer.RANKING_MEASURE,
    # None for the instrument's own reason: nobody has rated these notes on
    # PDSQI-9, so no column of it has a human beside it.
    results.TRACK_PDSQI: pdsqi.RANKING_MEASURE,
}


#: Unranked tracks whose rows are ordered by dominance instead of by name.
#:
#: Empty. iCARE and PDSQI-9 were ordered this way for one day, 2026-09-01, and
#: taken back off the same day: the relation the order was read from -- at
#: least as good on every column under both judges -- had never been tested,
#: and when it was, a substantial share of its edges did not survive resampling
#: the conversations. The constant stays so the day an edges artefact exists
#: the ordering has one place to be switched back on, from tested layers and
#: with nothing breaking ties; an empty set is a truer statement of what is
#: ordered by dominance today than a deleted one.
DOMINANCE_ORDERED: frozenset[str] = frozenset()


#: What the expandable row's second block holds, per track. It is not the same
#: thing on every track and it used to be headed "Rubric criteria" everywhere
#: but iCARE.
#:
#: A block headed for one instrument and filled from another is the failure
#: this label exists to prevent: a reader who trusts the heading reads the
#: wrong denominator, and the denominator -- whether an average is over ten
#: notes or over nine -- is this repository's oldest failure mode.
DETAIL_LABELS: dict[str, str] = {
    results.TRACK_TNEVAL: "Rubric criteria",
    results.TRACK_ICARE: "TRACE dimensions",
}


#: Which tracks each source, corpus profile and protocol section belongs to.
#:
#: **Why this exists at all.** `build` used to attach every one of them to
#: every page, which is harmless only while every page draws every track. A
#: page that credits TN-Eval's two human annotators, prints its 23-item rubric
#: and profiles the iHOPE corpus while drawing none of them is making a claim,
#: because a reader cannot tell a source that was used from one merely listed.
#:
#: A source missing from here is drawn on every page, which is the old
#: behaviour and the safe direction: a source over-credited is a nuisance, a
#: source used and not credited is a licence problem.
LICENCE_TRACKS: dict[str, tuple[str, ...]] = {
    "PDSQI-9": (results.TRACK_PDSQI,),
    "TN-Eval (code)": (
        results.TRACK_TNEVAL,
        results.TRACK_PDSQI,
    ),
    # The 150 rated notes and the therapist's row that comes from them.
    "TN-Eval-Data": (results.TRACK_TNEVAL, results.TRACK_PDSQI),
    "AnnoMI": (
        results.TRACK_TNEVAL,
        results.TRACK_PDSQI,
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
    ),
    "icare": (results.TRACK_ICARE,),
}

#: And for the protocol. The four SOAP sections are shown wherever a note is a
#: SOAP note; the 23 criteria are TN-Eval's scoring instrument and are shown
#: only where that instrument was used.
PROTOCOL_TRACKS: dict[str, tuple[str, ...]] = {
    "sections": (
        results.TRACK_TNEVAL,
        results.TRACK_PDSQI,
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
    # All six, and it matters more here than anywhere else: this track has no
    # human anchor at all, so two judges disagreeing is the only control it has.
    # Every attribute the corpus was asked, and no more. Naming one the two
    # judges never answered would ask the concordance panel to compare a column
    # that does not exist on either side.
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
        "anchored": key == ANCHORED_MEASURES.get(track),
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
}

#: The same tracks, short enough to be a button. Separate from the titles rather
#: than sliced out of them: a title is a sentence and a slice of a sentence is
#: whatever survived the punctuation.
TRACK_SWITCH_LABELS = {
    results.TRACK_TNEVAL: "TN-Eval SOAP",
    results.TRACK_ICARE: "iCARE / iHOPE",
    results.TRACK_PDSQI: "PDSQI-9 on SOAP",
}

TRACK_BLURBS = {
    results.TRACK_TNEVAL: (
        "Reference-free. 23 completeness criteria, conciseness scored sentence by "
        "sentence, faithfulness against the full transcript (Shah et al., 2025)."
    ),
    results.TRACK_ICARE: (
        "Automatic metrics and a TRACE judge side by side, because the source paper "
        "found they disagree (Adhikary, Singh, et al., 2026). That disagreement is a "
        "result, not an error. "
        "iCARE and iHOPE are one project under two names: the code "
        "was released as iCARE in April 2025 and the preprint renamed it iHOPE in "
        "August 2026, sixteen months later. **PDSQI-9 has no columns here**, and "
        "that is deliberate rather than missing: it rates how a clinical note is "
        "written, and these are 17 form fields rather than a written note. It runs "
        "on the SOAP notes, where it can be read against the rubric that scores "
        "the same text."
    ),
    results.TRACK_PDSQI: (
        "A published instrument (Croxford et al., 2025) asked about the same notes as "
        "the TN-Eval SOAP track: the SOAP notes written from the 50 AnnoMI conversations. Not a "
        "third corpus -- one corpus, two instruments, so the two tables can be "
        "read against each other. Eight attributes, reported separately: the "
        "ratings themselves are never averaged, because the instrument reports them "
        "that way and because one of the eight is a 0-1 column, and a mean over it "
        "and seven 1-5 scales would be a number with no unit. The order is a mean "
        "of places, which has the same unit on every column."
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
            "the prompt and the rubric are taken from (Shah et al., 2025).",
        ),
        (
            "The transcripts",
            "AnnoMI (Wu et al., 2022): 133 publicly released motivational-interviewing sessions, "
            "transcribed and annotated by therapists. They are demonstration "
            "sessions, not recordings of clinical practice. 50 are scored here.",
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
            "the prompt and the rubric are taken from (Shah et al., 2025).",
        ),
        (
            "The transcripts",
            "AnnoMI (Wu et al., 2022): 133 publicly released motivational-interviewing sessions, "
            "transcribed and annotated by therapists. They are demonstration "
            "sessions, not recordings of clinical practice. 50 are scored here.",
        ),
        (
            "PDSQI-9",
            "A published instrument for rating how a clinical note is written, "
            "validated on real records with physicians doing the rating (Croxford et al., 2025).",
        ),
    ),
    results.TRACK_ICARE: (
        (
            "iCARE / iHOPE",
            "This track. A model fills in a 17-field clinical form from a counselling "
            "transcript, and its answers are compared with the form an expert "
            "clinician filled in from the same session. One project under two names: "
            "released as iCARE, renamed iHOPE in the preprint (Adhikary, Singh, et al., 2026).",
        ),
        (
            "The sessions",
            "40 counselling demonstrations, each with one form an expert clinician "
            "filled in from it afterwards -- not the clinician who conducted it, who "
            "is not part of this corpus. That form is the answer key, not an entry.",
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
            "An expert note written from the session by a clinician who was not in "
            "it. ROUGE-L and BERTScore measure how closely the model reproduced it; "
            "TRACE asks a judge to rate the note itself, the way the paper's experts "
            "did."
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
    # The name the form uses. The page lists the seventeen sections a few
    # panels above and calls this one `Presenting complaints (symptoms)`, as
    # does the fill-rate table; the example called it something else and read
    # as an eighteenth.
    "section": "Presenting complaints (symptoms)",
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
#: Deliberately not a translated field -- when the page had a Czech mirror this
#: was the one exception it named, and the reason survives it: a reference is
#: quoted, not authored, and is the same in both languages -- like the rubric
#: text, which is excluded there for the same reason.
LICENCES = [
    {
        "source": "PDSQI-9",
        # Bibliographic data read from Crossref on 2026-09-02, not from memory:
        # the paper had appeared in JAMIA by then, with nineteen authors, and the
        # entry here had cited the arXiv preprint with three of them.
        "cite": (
            "Croxford, E., Gao, Y., Pellegrino, N., Wong, K., Wills, G., First, E., "
            "Schnier, M., Burton, K., Ebby, C., Gorski, J., Kalscheur, M., Khalil, S., "
            "Pisani, M., Rubeor, T., Stetson, P., Liao, F., Goswami, C., Patterson, B., "
            "& Afshar, M. (2025). Development and validation of the provider "
            "documentation summarization quality instrument for large language models. "
            "Journal of the American Medical Informatics Association, 32(6), 1050\u20131060. "
            "https://doi.org/10.1093/jamia/ocaf068"
        ),
        "url": "https://arxiv.org/abs/2501.08977",
        "used_for": "the nine attributes and their anchors, eight of which are scored",
        # "arXiv preprint" is a venue, not a licence, and it was printed under a
        # heading that says Licence. `NOTICE` records the terms: CC BY 4.0, which
        # is what permits the verbatim reproduction the note beside it describes.
        "licence": "CC BY 4.0 (arXiv version)",
        "note": (
            "The instrument is reproduced verbatim, anchors included, so a score here "
            "answers the published question and not a rewritten one. The wording is the "
            "arXiv version's, which is CC BY 4.0; the instrument is itself an adaptation "
            "of PDQI-9 (Stetson et al., 2012)."
        ),
    },
    {
        "source": "TN-Eval (code)",
        "cite": (
            "Shah, R. S., Xu, L., Liu, Q., Burnsky, J., Bertagnolli, A., & Shivade, C. "
            "(2025). TN-Eval: Rubric and evaluation protocols for measuring the quality "
            "of behavioral therapy notes. In Proceedings of the 63rd Annual Meeting of "
            "the Association for Computational Linguistics (Volume 6: Industry Track) "
            "(pp. 179\u2013199). Association for Computational Linguistics. "
            "https://doi.org/10.18653/v1/2025.acl-industry.14"
        ),
        "url": "https://github.com/amazon-science/TN-Eval",
        "used_for": "SOAP prompt, the five scoring prompts, the 23-item rubric",
        "licence": "Apache-2.0",
        "note": "Reproduced verbatim in this repository, with attribution in NOTICE.",
    },
    {
        "source": "TN-Eval-Data",
        "cite": "The data release of Shah et al. (2025); it carries no reference of its own.",
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
            "expert-annotated counselling dialogues. In ICASSP 2022 \u2013 2022 IEEE "
            "International Conference on Acoustics, Speech and Signal Processing (ICASSP) "
            "(pp. 6177\u20136181). IEEE. https://doi.org/10.1109/ICASSP43922.2022.9746035"
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
        # Twelve authors, as medRxiv lists them for both versions (read from its
        # API on 2026-09-02); Crossref carries eleven for the same DOI and a
        # different order, and the archive's own record is the one to follow.
        "cite": (
            "Adhikary, P. K., Singh, S., Singh, S., Sharma, P., Soni, P., Choudhary, R., "
            "Saxena, C., Chauhan, P., Gupta, S. K., Deb, K. S., Singh, S. M., & "
            "Chakraborty, T. (2026). Clinically grounded AI-scribing in psychotherapy: "
            "Benchmarking LLMs against expert documentation in the iCARE framework "
            "(Version 2) [Preprint]. medRxiv. https://doi.org/10.1101/2025.06.25.25330252"
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
            "Health Informatics. Advance online publication. "
            "https://doi.org/10.1109/JBHI.2026.3726138"
        ),
        "url": "https://github.com/ai4mhx/TheraFuse",
        "used_for": "the iHOPE transcripts and expert notes",
        "licence": "MIT badge, no LICENSE file",
        "note": (
            "A badge on a code repository, for a corpus collected elsewhere. Treated as no licence "
            "for the data. The repository carries the iHOPE corpus the iCARE paper describes."
        ),
    },
]


def _length_effects(track: str, rendered: list[dict]) -> dict | None:
    """How a text-overlap column moves with note length, on this table.

    ROUGE-L rewards using the expert's words, and a longer note has more
    chances to; the page prints the correlation beside the Words column rather
    than asserting it in prose, because on the rubric track the same claim --
    completeness rises with length -- held under one judge and not the other.
    Spearman over the rows that have both figures; None where fewer than three
    do or where the track has no such column.
    """
    if not any(key == "rouge_l" for key, _ in COLUMNS[track]):
        return None
    pairs = [
        (row["note_words"], row["headline"]["rouge_l"])
        for row in rendered
        if row["note_words"] and row["headline"].get("rouge_l") is not None
    ]
    if len(pairs) < 3:
        return None
    rho = calibration.spearman([words for words, _ in pairs], [value for _, value in pairs])
    return {"rouge_l": {"rho": None if rho is None else round(rho, 3), "n": len(pairs)}}


def _reconcile_roster(roster: dict | None, rows: list[Row]) -> dict | None:
    """The roster against the rows: a model with notes on disk is not "never asked".

    `tnb roster` compares the endpoints with the tables it can see and names
    the models it finds nowhere. A model whose notes have been generated and
    not yet judged has rows -- coverage rows -- and no table, and the page
    called it "never been asked to write a note" while its notes sat in
    `generations/`. Sorted here into three: still never asked, generated and
    awaiting the judge, or scored (and then not named at all).
    """
    if not roster:
        return roster
    scored = {(row.provider, row.system_id) for row in rows if row.is_scored}
    generated = {(row.provider, row.system_id) for row in rows if not row.is_scored}
    never: list[dict] = []
    awaiting: list[dict] = []
    for entry in roster.get("never_asked") or []:
        key = (entry.get("provider"), entry.get("system_id"))
        if key in scored:
            continue
        (awaiting if key in generated else never).append(entry)
    return {**roster, "never_asked": never, "awaiting_judge": awaiting}


def _placed(group: list[Row], track: str) -> tuple[dict, dict, dict | None]:
    """The order of one table, its sensitivity, and the tested groups if they exist.

    The order is `composite.order` over the scored rows' headlines. The groups
    are the layers of `docs/edges-<track>.json`, and they are absent -- not
    empty -- when that artefact has not been built, so nothing downstream can
    draw a group nobody tested.
    """
    scores = {row.system_id: dict(row.metrics.headline) for row in group if row.is_scored}
    ordering = composite.order(scores, COLUMNS[track])
    reference = [row.system_id for row in group if row.is_scored and row.system_type != "model"]
    sensitivity = composite.sensitivity(scores, COLUMNS[track], reference=reference)
    return ordering, sensitivity, edges.load(track)


def _sort_key(row: Row, ordering: dict):
    """Placed rows by place, then scored rows no place could be given, then unscored.

    An unplaced row is one missing a column -- a measure nobody computed for it
    -- and it sorts after the placed rows, in name order, rather than as the
    worst score: reading a missing measure as 0.0 once published
    `mistral-large-v2` last on a measure nobody had computed for it.
    """
    if not row.is_scored:
        return (2, 0, 0.0, row.system_id)
    placed = ordering["systems"].get(row.system_id)
    if placed is None:
        return (1, 0, 0.0, row.system_id)
    return (0, placed["place"], placed["mean_place"], row.system_id)


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
    #: a second measurement worth drawing. Two rubric versions otherwise produce
    #: two tables per track and two judge buttons carrying the same words, with
    #: nothing on the page saying which button holds the older questions. It
    #: stays in `COMPARABILITY_KEYS` -- two versions
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
            # Which of these bands rest on a comparison the bootstrap cannot
            # call. Carried whole rather than summarised here: the page names
            # the systems, and a count with no names is not something a reader
            # can act on. `None` on an analysis written before it was measured.
            "near_the_cut": item.get("near_the_cut"),
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


def _masthead(tables: list[dict]) -> dict:
    """What the sentence under the title can say and have checked.

    Built from the drawn tables, which is what the page itself reads, so the
    masthead cannot state a number the tables below it disagree with.

    `notes` counts only the tracks whose notes were written for them --
    `results.NOTE_TRACKS`. PDSQI-9 rates the SOAP notes the rubric already
    scored, so adding the three tracks up would count every SOAP note twice and
    the masthead would claim a third more work than was done. `sessions` is the
    same rule applied to the corpora: 50 AnnoMI conversations and 40 iHOPE
    sessions, not 140.
    """
    scored = [table for table in tables if table["scored"]]
    models, judges, instruments = set(), set(), set()
    sessions = {}
    for table in scored:
        judges.add(table["versions"].get("judge_model"))
        instruments.add(INSTRUMENT_LABELS.get(table["track"]))
        for row in table["rows"]:
            if row.get("system_type") != "model":
                continue
            models.add(row["system_id"])
            if table["track"] not in results.NOTE_TRACKS:
                continue
            sessions[table["track"]] = max(
                sessions.get(table["track"], 0), row.get("n_attempted") or 0
            )
    # One judge's table per track, not both: two judges scored the same notes,
    # and a note counted once per table is a note counted twice.
    per_track = {}
    for table in scored:
        if table["track"] in results.NOTE_TRACKS:
            per_track.setdefault(table["track"], table)
    written = sum(
        (row.get("n_generated") or 0)
        for table in per_track.values()
        for row in table["rows"]
        if row.get("system_type") == "model"
    )
    return {
        "models": len(models),
        "notes": written,
        "sessions": sum(sessions.values()),
        "judges": len(judges - {None, ""}),
        "instruments": len(instruments - {None}),
    }


def build(
    rows: list[Row],
    saturations: list[dict] | None = None,
    *,
    source: str | None = None,
    roster: dict | None = None,
) -> dict:
    """Shape the rows into the JSON both presentations read.

    `saturations` carries, per judge, which systems that judge's evidence
    cannot tell apart. Optional because a coverage-only build has none, and
    absent is drawn as "not measured for this table" rather than as agreement.

    `roster` carries what the endpoints served when `tnb roster` last asked
    them. Optional for the same reason and drawn the same way: without it the
    page says nothing about any endpoint, rather than implying every row can
    still be re-asked.

    Groups that disagree on any version field become separate tables rather than
    separate rows in one table. The newest harness per track and judge is drawn;
    older ones are named in `superseded` so a stale number is explainable rather
    than silently gone.
    """
    current = _with_note_words(_with_borrowed_reasons(results.latest(rows)))
    tables = []

    saturations = saturations or []
    # {system_id: the day the endpoint was asked and did not offer it}. Keyed on
    # the system rather than on (provider, system) because a row carries one of
    # each and the roster records the pair, so the pair is checked when it is
    # built and the row only has to find itself.
    withdrawn = {
        # Keyed on the pair. `models.yaml` says the same id on two endpoints can
        # be two different builds and this benchmark never merges them, so one
        # endpoint's withdrawal must not mark the other endpoint's row.
        (entry["provider"], entry["system_id"]): (roster or {}).get("asked", "")
        for entry in (roster or {}).get("withdrawn", [])
    }
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
        ordering, sensitivity, tested = _placed(group, track)
        group_of = {
            system: number
            for number, layer in enumerate((tested or {}).get("layers") or [], start=1)
            for system in layer
        }
        rendered = [
            _render_row(
                row,
                withdrawn=withdrawn,
                ordering=ordering,
                groups=group_of if tested else None,
            )
            for row in sorted(group, key=lambda r: _sort_key(r, ordering))
        ]
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
                # Every column names the instrument that asked for it. The
                # legend groups a caveat shared by all of an instrument's
                # columns under the instrument's name, and two SOAP-note tables
                # sit under one switch; a reader who flips between them should
                # not have to remember which eight columns were whose.
                # `judged` says whether the judge named above decided this
                # column or whether it was computed from the note and the
                # expert note. Four of iCARE's five columns are the second
                # kind: byte-identical under every judge, because no judge was
                # ever asked. The page needs it for the two-judge comparison,
                # which drew "= 0.000" beside ROUGE-L and so told a reader the
                # judges had agreed exactly on a number neither of them
                # produced -- the tautology `icare.JUDGE_MEASURES` exists to
                # keep off the concordance panel, printed eighteen times a
                # table instead.
                "columns": [
                    {
                        **column_meta(track, key_),
                        "digits": digits,
                        "instrument": INSTRUMENT_LABELS[track],
                        "judged": key_ in JUDGE_MEASURES.get(track, ()),
                    }
                    for key_, digits in COLUMNS[track]
                ],
                # How the rows are ordered and what the choice does. A place is
                # a statement about this table, never about a note: it is not a
                # measure and it never enters a headline.
                "ordering": {
                    "rule": ordering["rule"],
                    "columns": ordering["columns"],
                    "placed": len(ordering["systems"]),
                    "unplaced": [
                        {"system_id": system, "missing": missing}
                        for system, missing in sorted(ordering["unplaced"].items())
                    ],
                    "sensitivity": sensitivity,
                },
                # The one column checked against people, if any. Not the sort
                # key any more; still the only anchor, and named as that.
                "anchor_measure": ANCHORED_MEASURES.get(track),
                # The layers of the tested dominance graph -- only where the
                # artefact exists. A table without this key draws no Group
                # column, and a Group column is never drawn from an untested
                # relation: that was built and taken down once already.
                **(
                    {
                        "groups_tested": {
                            "layers": tested["layers"],
                            "undominated": tested["undominated"],
                            "threshold": tested["threshold"],
                            "samples": tested["samples"],
                            "counts": tested["counts"],
                            "systems": tested["systems"],
                            "source": edges.artefact_path(track).name,
                        }
                    }
                    if tested
                    else {}
                ),
                "detail_label": DETAIL_LABELS.get(track, "Rubric criteria"),
                "rows": rendered,
                # How ROUGE-L moves with note length on this table, where the
                # track has that column and enough rows carry a length.
                **(
                    {"length_effects": effects}
                    if (effects := _length_effects(track, rendered))
                    else {}
                ),
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
    # up asking why the benchmark is empty when it is not. Among the scored
    # tables the rubric track opens the page because it is the one whose judge
    # is checked against people: PDSQI-9 is a second instrument on the same
    # notes, and iCARE's TRACE has no human anchor. The switch draws the rest.
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

    # Withdrawn groups count too. `superseded` names a track on the page --
    # "this was published and is not any more" -- and a reader who reads that
    # name still needs to know what it was measured with. A page that names
    # PDSQI-9 and links nothing is the same gap as one that credits a source
    # it never used, pointing the other way.
    drawn = {table["track"] for table in tables}
    drawn |= {entry["track"] for entry in superseded if entry.get("track")}
    return {
        "tables": tables,
        # What the endpoints served, read against these rows: a model with
        # notes and no scores is awaiting the judge, not never asked.
        "roster": _reconcile_roster(roster, current),
        # Which one to draw and what may be switched to. Decided here, because
        # every other ordering on this page is.
        "selection": _selection(tables),
        # Not drawn, but named. A number that used to be published and is not
        # any more should be explainable rather than silently gone.
        "superseded": superseded,
        "protocol": protocol(drawn),
        # The four counts the masthead states. Drawn from the tables rather
        # than written into the template: the sentence under the title used to
        # name the three instruments and nothing countable, and every number on
        # this page that was typed has gone stale at least once.
        "masthead": _masthead(tables),
        "corpus": _corpus_for(drawn),
        "licences": [
            licence for licence in LICENCES if _used_by(LICENCE_TRACKS, licence["source"], drawn)
        ],
        # The file these numbers came out of. A page built from one record
        # and naming another is the one claim a provenance line must never
        # get wrong, so it is passed in rather than assumed.
        "generated_from": source or str(results.ROWS_PATH.name),
        # None on the published page, which keeps the header the template
        # was written with.
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
    and +0.017 for `gpt-5.6-terra`, both from `docs/preference.json` -- and once
    the models are resampled as well
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


def _render_row(
    row: Row,
    *,
    withdrawn: dict[tuple[str, str], str] | None = None,
    ordering: dict | None = None,
    groups: dict[str, int] | None = None,
) -> dict:
    placed = ((ordering or {}).get("systems") or {}).get(row.system_id)
    return {
        "system_id": row.system_id,
        # Where this row sits in its table's order, and the places it is the
        # mean of. None for a row missing a column, which is then named in
        # `unplaced_because` rather than placed last.
        "place": placed["place"] if placed else None,
        "mean_place": placed["mean_place"] if placed else None,
        "places": placed["places"] if placed else None,
        "unplaced_because": ((ordering or {}).get("unplaced") or {}).get(row.system_id),
        # The tested group, present only when the table has groups at all. A
        # system outside the compared population -- missing a column under
        # either judge -- carries None and the page says why.
        **({"group": groups.get(row.system_id)} if groups is not None else {}),
        # The day an endpoint was asked for this model and did not offer it.
        # Absent for every row where that has not happened, which is not the
        # same as a row that was checked and is fine: `roster` being absent
        # leaves this empty for everybody.
        "withdrawn_on": (withdrawn or {}).get((row.provider, row.system_id)),
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
        grouped = bool(table.get("groups_tested"))
        header = ["Place", "Model"]
        if grouped:
            header.append("Group")
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
            # The own-family mark, which `docs/limitations.md` promises is
            # carried "in the table where they sit". The page drew it and this
            # table did not, so the README -- the surface most people read
            # first, and the one that travels into other documents -- showed a
            # judge's own vendor's rows with nothing on them.
            own = row.get("judges_own_family") or ""
            label = f"`{row['label']}`" + (f" *(judge's own {own})*" if own else "")
            cells = ["—" if row["place"] is None else str(row["place"]), label]
            if grouped:
                cells.append("—" if row.get("group") is None else str(row["group"]))
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
        lines.append(_order_caveat(table))
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

    # The finding the three tables above cannot state between them, in the file
    # that prints only one of them and has no switch to correct a reader with.
    # Sentences and not the grid: this view already refuses to print five of
    # the six tables, and an 18-by-7 table of ranks is exactly what
    # `_readme_tables` exists to keep out. The profile itself is a link.
    profile = _orders_sentences(data.get("orders"))
    if profile:
        blocks.append(profile)

    # Named, not drawn. A number that was published and is not any more
    # should be explainable; a reader who remembers a different figure needs
    # to see that the measure changed, not wonder whether the model did.
    #
    # As a table, and one row per reason rather than per group: the 47 groups
    # withdrawn on 2026-09-02 carried 14 distinct reasons between them, and
    # printing each group as its own sentence put 47 near-identical paragraphs
    # under the tables -- the same clause about redefined measures nineteen
    # times over. A reader scrolling past that learns less than one who reads a
    # table, not more.
    withdrawn = _withdrawn_table(data.get("superseded", []))
    if withdrawn:
        blocks.append(withdrawn)

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


def _order_caveat(table: dict) -> str:
    """The order, the groups and the anchor, in three sentences under the table.

    Every figure in them is read off the payload the table was drawn from --
    the sensitivity block, the tested groups and the anchor -- so the README and
    the page cannot say different things about the same rows.
    """
    ordering = table["ordering"]
    sens = ordering["sensitivity"]
    labels = {row["system_id"]: row["label"] for row in table["rows"]}
    first = ", ".join(f"`{labels.get(s, s)}`" for s in sens["first_under_any"])
    parts = [
        f"*Ordered by **mean place** over the {len(ordering['columns'])} columns of this "
        f"instrument, every column counting once — a convention, not a measurement: the columns "
        f"do not predict each other. Under the other weightings tried (each column counted twice, "
        f"and the reference rows removed) first place is held by {first}; at most "
        f"{sens['most_moved']} of {sens['n_systems']} systems change place and none by more than "
        f"{sens['furthest']} ([how the order was built]({SITE_URL}methods.html#ordering)). Places "
        f"are among all {len(table['rows'])} rows of the table, the reference systems included, "
        f"so the models' places can have gaps.*"
    ]
    tested = table.get("groups_tested")
    if tested:
        parts.append(
            f"*Group: what the evidence separates. A system stands above another only when it is "
            f"at least as good on every column under both judges in {tested['threshold']:.2f} of "
            f"the resampled conversations; {len(tested['layers'])} group(s) for "
            f"{len(tested['systems'])} systems, {len(tested['undominated'])} of them beaten by no "
            f"tested comparison ([how the comparisons were tested]"
            f"({SITE_URL}methods.html#groups)).*"
        )
    anchor = table.get("anchor_measure")
    if anchor:
        label = next((c["label"] for c in table["columns"] if c["key"] == anchor), anchor)
        parts.append(
            f"***{label}** is the only column checked against people; it counts once in the "
            f"order, like every other.*"
        )
    return " ".join(parts)


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


def _orders_sentences(profile: dict | None) -> str:
    """What the three instruments do to each other, for the README.

    Every figure read off the payload, none typed: the shape that has gone
    stale here before is a sentence with a number in it that nothing recomputes.
    Returns "" when there is no profile, so the block simply does not appear
    rather than appearing with a hole in it.
    """
    if not profile:
        return ""
    bands = {band["kind"]: band for band in profile["bands"]}
    wide = {band["kind"]: band for band in profile["jackknife"]["bands"]}
    inside, inside_wide = bands.get("same_instrument"), wide.get("same_instrument")
    across = [band for kind, band in bands.items() if kind != "same_instrument"]
    if not inside or not across:
        return ""

    def signed(value: float) -> str:
        return f"{value:+.3f}".replace("-", "\u2212")

    def name(track: str) -> str:
        found = next((c for c in profile["columns_drawn"] if c["track"] == track), None)
        return found["instrument"] if found else track

    def pair(kind: str, joiner: str = " against ") -> str:
        return joiner.join(name(track) for track in kind.split("/"))

    apart = min(
        (band for band in profile["jackknife"]["bands"] if band["kind"] != "same_instrument"),
        key=lambda band: band["high"],
    )
    same_notes = next((band for band in across if band.get("same_corpus")), None)
    pooled = profile["dominance"]["pooled"]
    top = sum(
        1 for row in profile["rows"] if row["top_group"] == len(profile["instruments_tested"])
    )

    said = [
        f"**Is there one ranking? Only as a profile.** "
        f"[All six rankings, one row per model]({SITE_URL}) puts every one of the "
        f"{len(profile['population'])} models beside the rank each of the "
        f"{profile['tables']} tables gives it, and adds nothing up. A total over the three "
        f"instruments would have to say what a SOAP rubric is worth against a 17-field form, "
        f"which is a clinical judgement and not a measurement these numbers can be asked for.",
        f"The two judges rank one instrument alike at Spearman {signed(inside['low'])} to "
        f"{signed(inside['high'])}; two different instruments reach "
        f"{signed(min(band['low'] for band in across))} to "
        f"{signed(max(band['high'] for band in across))}. "
        f"{pair(apart['kind'])} reaches {signed(bands[apart['kind']]['low'])} to "
        f"{signed(bands[apart['kind']]['high'])}, which is no relation at all.",
    ]
    if same_notes:
        said.append(
            f"It is not the corpora that differ: {pair(same_notes['kind'], ' and ')} are scored "
            f"on the identical notes from the identical conversations, and their orders still "
            f"agree only {signed(same_notes['low'])} to {signed(same_notes['high'])}."
        )
    if inside_wide:
        said.append(
            f"Only the wider claim is published, because the sharper one does not survive: "
            f"with each of the {profile['jackknife']['refits']} models left out in turn, one "
            f"instrument under two judges never falls below {signed(inside_wide['low'])} and "
            f"{pair(apart['kind'])} never rises above {signed(apart['high'])}, so those two "
            f"bands never meet."
        )
    measured = [
        f"{judge['across_instruments']['median_abs_rho']:.3f} against "
        f"{judge['within_instrument']['median_abs_rho']:.3f} under `{judge['judge_model']}`"
        for judge in profile["columns"]
        if judge["across_instruments"]["median_abs_rho"] is not None
        and judge["within_instrument"]["median_abs_rho"] is not None
    ]
    if measured:
        said.append(
            "**And the disagreement is not the instruments measuring different things.** "
            "Between individual columns, where no ordering rule is involved, columns of "
            "different instruments predict each other about as well as columns of the same "
            "one: median |rho| " + "; ".join(measured) + ". Whatever separates the six orders "
            "happens in the averaging of places, not in the measurements."
        )
    controls = "; ".join(
        f"{name(track)} separates {one['dominating']} of {one['pairs']} on {one['legs']}"
        for track, one in sorted(
            profile["dominance"]["per_instrument"].items(), key=lambda item: item[1]["legs"]
        )
    )
    said.append(
        f"Pooled over all three instruments nothing is separated at all: no model is at least "
        f"as good as another on every one of the {pooled['legs']} column-legs under both "
        f"judges, {pooled['dominating']} of {pooled['pairs']} ordered pairs. Part of that is "
        f"arithmetic rather than a finding, and the same count inside one instrument shows it "
        f"({controls}). {top} of the {len(profile['rows'])} models are left undominated by "
        f"every instrument, which is this benchmark's honest answer to \u201cwhich model\u201d."
    )
    return "\n\n".join(said)


def _withdrawn_table(superseded: list[dict]) -> str:
    """Every withdrawn group, one row per distinct reason, in Markdown.

    Grouped on the track, the judge and the reasons -- which is what the reader
    is being told -- with the harness versions it happened at listed in the row.
    The row count is summed, so nothing is lost by the grouping: the totals add
    up to the same number of rows as the sentences did.
    """
    if not superseded:
        return ""
    grouped: dict[tuple, list[dict]] = {}
    for gone in superseded:
        key = (
            gone["track"],
            gone["judge_model"] or "",
            tuple(gone.get("reasons") or ["harness"]),
        )
        grouped.setdefault(key, []).append(gone)
    lines = [
        f"**Rows that were published and are no longer shown** — "
        f"{sum(gone['rows'] for gone in superseded)} in "
        f"{len(superseded)} group(s), every one still in `results/rows.jsonl`.",
        "",
        "| Rows | Track | Judge | At harness | Why |",
        "|---|---|---|---|---|",
    ]
    for (track, judged_by, _), gones in sorted(grouped.items()):
        versions = sorted({gone["harness_version"] for gone in gones})
        why = "; and ".join(_superseded_reasons(gones[0]))
        lines.append(
            f"| {sum(gone['rows'] for gone in gones)} | {track} | "
            f"{'`' + judged_by + '`' if judged_by else '*generation coverage*'} | "
            f"{', '.join('`' + version + '`' for version in versions)} | {why} |"
        )
    return "\n".join(lines)


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
    if row["n_scored"] < row["n_generated"]:
        return f"{row['n_scored']} of {row['n_generated']} *(judging)*"
    # Started is not finished. A note the judge began and left part-answered is
    # out of the figures, and a cell saying 50 over a figure computed from 44
    # was the README's version of the denominator fault this repository keeps
    # finding.
    if row.get("n_partial"):
        return f"{row['n_complete']} of {row['n_scored']} *({row['n_partial']} part-answered)*"
    return f"{row['n_scored']}"


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
    write_published(path, updated)
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
    data = build(rows, saturations, roster=load_roster(docs_dir))
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
    data["repeatability"] = _load_json(docs_dir / REPEATABILITY_PATH.name)
    # The tested comparisons, whole, for the methods page; the tables carry
    # only the layers.
    data["edges"] = {
        track: found for track in COLUMNS if (found := edges.load(track, docs_dir)) is not None
    }
    # The six tables' orders read against each other. Recomputed and compared
    # rather than trusted: `orders.matches` rebuilds the artefact from the
    # tables being drawn and refuses it on a single rank out of place. That is
    # affordable because the computation is free, and it is the guard the
    # tested-edges artefact still has to do without.
    data["orders"] = _orders_for(data["tables"], docs_dir)
    # Computed here rather than cached in docs/, because it is a statement about
    # the rows being rendered right now. A stale copy of "the judges disagree
    # about 11 of 19" beside a table where they no longer do is worse than none.
    # From the rows a table would draw, not from every row in the file. Two
    # harness versions carry two definitions of the same column.
    data["concordance"] = concordance_payload(rows)
    # Which instrument each comparison was made with. `track_label` describes
    # the corpus and the form; a column headed "beats outright" has to name the
    # instrument, because the same nineteen systems give a different answer
    # under the rubric's three columns and under PDSQI-9's eight.
    for track, found in data["concordance"].items():
        found["instrument"] = INSTRUMENT_LABELS.get(track, track)
        # How far the two judges agree on the order the page now draws, which
        # is a different question from how they agree on any one column.
        found["ordering"] = _ordering_agreement(
            data["tables"], track, found["judge_a"], found["judge_b"], data["orders"]
        )

    docs_dir.mkdir(parents=True, exist_ok=True)
    write_published(
        docs_dir / DATA_PATH.name,
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )
    write_published(docs_dir / PAGE_PATH.name, render_page(data))
    write_published(docs_dir / METHODS_PATH.name, render_methods(data))
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
    "\u2028": "\\u2028",
    "\u2029": "\\u2029",
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
                    anchor_measure=ANCHORED_MEASURES.get(track),
                    **overrides,
                )
            )
        )
    }


def _profile_rho(profile: dict | None, track: str) -> float | None:
    """The two judges' agreement on one instrument, over the models alone.

    Read off `docs/orders.json`, which is where that population's orders are
    built. Absent while the profile is absent, because a figure the page cannot
    show the working for is one it should not print.
    """
    if not profile:
        return None
    tracks = {order["table"]: order["track"] for order in profile["orders"]}
    for pair in profile["agreement"]:
        if pair["kind"] == "same_instrument" and tracks.get(pair["a"]) == track:
            return pair["rho"]
    return None


def _orders_for(tables: list[dict], docs_dir: Path) -> dict | None:
    """The profile, from the committed artefact and only while it still fits.

    `None` rather than absent, like every other optional panel: the key has to
    exist for a template to read it, and a template that reads it is what says
    the payload has no key nobody draws.

    The instrument's label is attached here rather than stored in the artefact.
    A data file that carries English is a wording nobody proof-reads beside the
    paragraph it lands in, and one that can only be corrected by re-running a
    command.
    """
    import statistics

    from tnb.scoring import orders

    found = orders.load(docs_dir)
    if not orders.matches(found, tables):
        return None

    by_id = {table["id"]: table for table in tables}
    for order in found["orders"]:
        order["instrument"] = INSTRUMENT_LABELS.get(order["track"], order["track"])
        order["title"] = by_id[order["table"]]["title"]

    # Which cross-instrument pairs read the same notes. `DATASET_TRACKS`
    # already groups the tracks by corpus, and the page needs it: "the two
    # instruments disagree" is a much stronger sentence about a pair that
    # scored the identical notes than about a pair that did not, and picking
    # the pair by its correlation alone put the claim on the wrong one.
    corpus_of = {track: corpus for corpus, tracks in DATASET_TRACKS.items() for track in tracks}
    for band in found["bands"] + found["jackknife"]["bands"]:
        tracks = band["kind"].split("/")
        band["same_corpus"] = len(tracks) == 2 and corpus_of.get(tracks[0]) == corpus_of.get(
            tracks[1]
        )

    # The six columns in the order the switch offers the tables, so a reader
    # who has used the switch meets the same sequence here.
    drawn = [order["table"] for table in tables if (order := _order_of(found, table["id"]))]
    found["columns_drawn"] = [
        {
            "table": order["table"],
            "track": order["track"],
            "instrument": order["instrument"],
            "judge_model": order["judge_model"],
            "title": order["title"],
        }
        for table_id in drawn
        if (order := _order_of(found, table_id))
    ]

    # Every ordering decision in Python, the rule this page has kept since the
    # tables were built: the template draws what it was handed.
    #
    # Primarily by how many instruments leave the system undominated, which is
    # evidence and not a convention. Then by the middle of its six ranks, which
    # is a convention and is declared as one -- it settles the twelve rows the
    # first key ties, and it settles nothing else. The span is printed before
    # it so the reader meets the range before the middle: one model runs from
    # first to last, and no middle number describes that.
    labels = {}
    for table in tables:
        for row in table["rows"]:
            labels.setdefault(row["system_id"], row["label"])
    rows = []
    for system in found["population"]:
        ranks = [order["ranks"][system] for order in found["orders"]]
        by_table = {order["table"]: order["ranks"][system] for order in found["orders"]}
        rows.append(
            {
                "system_id": system,
                "label": labels.get(system, system),
                "top_group": found["undominated"][system],
                "ranks": [by_table[column["table"]] for column in found["columns_drawn"]],
                "best": min(ranks),
                "worst": max(ranks),
                "median": round(statistics.median(ranks), 1),
            }
        )
    # **One key, and it is the one on screen.** Ordered by top group first and
    # then by the median, the table read as broken to anybody who did not know
    # what the first column was: a row with a median of 6.0 sat below one with
    # 16.0, correctly, and nothing about that was visible. How many instruments
    # leave a model undominated is still the honest answer to "which model" and
    # it is still published -- as a sentence, and in `docs/edges-<track>.json`
    # -- but it is not what puts the rows in an order a reader is asked to read
    # down.
    rows.sort(key=lambda row: (row["median"], row["label"]))
    found["rows"] = rows
    found["widest"] = max(rows, key=lambda row: (row["worst"] - row["best"], row["label"]))
    return found


def _order_of(found: dict, table_id: str) -> dict | None:
    """One table's entry in the artefact, or None when it holds no such table."""
    return next((order for order in found["orders"] if order["table"] == table_id), None)


def _ordering_agreement(
    tables: list[dict],
    track: str,
    judge_a: str,
    judge_b: str,
    profile: dict | None = None,
) -> dict | None:
    """Spearman between the two judges' mean places, how many systems hold a
    different place under the two, and who moved furthest -- over the systems
    both judges placed. None until both tables exist."""
    by_judge: dict[str, dict[str, dict]] = {}
    for table in tables:
        judge_model = table["versions"].get("judge_model")
        if table["track"] != track or not table["scored"] or judge_model not in (judge_a, judge_b):
            continue
        by_judge[judge_model] = {
            row["system_id"]: row for row in table["rows"] if row.get("place") is not None
        }
    if judge_a not in by_judge or judge_b not in by_judge:
        return None
    shared = sorted(set(by_judge[judge_a]) & set(by_judge[judge_b]))
    if len(shared) < 3:
        return None
    rho = calibration.spearman(
        [by_judge[judge_a][s]["mean_place"] for s in shared],
        [by_judge[judge_b][s]["mean_place"] for s in shared],
    )
    # The same question over the models alone -- taken from the profile rather
    # than computed a second time here. It is not the same arithmetic: the
    # profile re-derives each order without the reference rows, so the places
    # themselves move, and recomputing it here from mean places that still
    # count those rows would put a third figure for one quantity on the page.
    # One owner, and the sentence beside each names its population.
    models = [s for s in shared if by_judge[judge_a][s]["system_type"] == "model"]
    rho_models = _profile_rho(profile, track)
    moved = [s for s in shared if by_judge[judge_a][s]["place"] != by_judge[judge_b][s]["place"]]
    furthest = max(
        shared, key=lambda s: abs(by_judge[judge_a][s]["place"] - by_judge[judge_b][s]["place"])
    )
    return {
        "rho": None if rho is None else round(rho, 3),
        "n_systems": len(shared),
        "rho_models": rho_models,
        "n_models": len(models),
        "moved": len(moved),
        "furthest": {
            "system": by_judge[judge_a][furthest]["label"],
            "place_a": by_judge[judge_a][furthest]["place"],
            "place_b": by_judge[judge_b][furthest]["place"],
        }
        if moved
        else None,
    }


def render_page(data: dict) -> str:
    """The standalone page: the data inlined, no build step, no dependency."""
    return PAGE_TEMPLATE.replace("__DATA__", _inline(data))


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
    return page.replace("__DATA__", _inline(data))


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
