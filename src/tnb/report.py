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

from tnb import corpus, results
from tnb.config import REPO_ROOT
from tnb.results import Row
from tnb.scoring import concordance, pdsqi
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
}


#: Which measures each track's judge actually decides. Only these can be
#: compared *between* two judges: on the iCARE track four of the five columns
#: are computed from the note and the expert note alone, so they are identical
#: under every judge, and "the judges agree perfectly on ROUGE-L" would dress a
#: tautology as a finding.
JUDGE_MEASURES: dict[str, tuple[str, ...]] = {
    results.TRACK_TNEVAL: rubric.JUDGE_MEASURES,
    results.TRACK_ICARE: icare_scorer.JUDGE_MEASURES,
    # Every one of the eight. Unlike iCARE, nothing here is computed from the
    # text alone, so all eight columns are a judge's opinion and all eight can
    # be compared between two of them.
    results.TRACK_PDSQI: pdsqi.JUDGE_MEASURES,
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
    return {
        "key": key,
        "label": meta["label"],
        "scale": meta["scale"],
        "definition": definition,
        "caveat": meta["caveat"],
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
    results.TRACK_PDSQI: "PDSQI-9 · the same notes, rated for quality",
}

#: The same tracks, short enough to be a button. Separate from the titles rather
#: than sliced out of them: a title is a sentence and a slice of a sentence is
#: whatever survived the punctuation.
TRACK_SWITCH_LABELS = {
    results.TRACK_TNEVAL: "TN-Eval SOAP",
    results.TRACK_ICARE: "iCARE / iHOPE",
    results.TRACK_PDSQI: "PDSQI-9 quality",
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
        "August 2026, sixteen months later."
    ),
    results.TRACK_PDSQI: (
        "A published instrument, asked about the very notes the rubric above scores "
        "for coverage. Eight attributes, reported separately and never averaged, "
        "because the instrument reports them that way."
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
        "Read the two. Tingling in the stomach and butterflies in the stomach are "
        "the same symptom; palpitations and a rapid heartbeat are the same symptom; "
        "trembling hands appear in both. The model also records how long each has "
        "lasted and when it happens, which the expert note does not. It shares "
        "almost no *words* with the clinician, and a metric that counts shared "
        "words scores it accordingly."
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
LICENCES = [
    {
        "source": "TN-Eval (code)",
        "url": "https://github.com/amazon-science/TN-Eval",
        "used_for": "SOAP prompt, the five scoring prompts, the 23-item rubric",
        "licence": "Apache-2.0",
        "note": "Reproduced verbatim in this repository, with attribution in NOTICE.",
    },
    {
        "source": "TN-Eval-Data",
        "url": "https://github.com/amazon-science/TN-Eval-Data",
        "used_for": "150 notes and the ratings of two human annotators",
        "licence": "none published",
        "note": (
            "The Apache licence is on the code repository, not this one. Fetched at run "
            "time, never"
            "redistributed."
        ),
    },
    {
        "source": "AnnoMI",
        "url": "https://github.com/uccollab/AnnoMI",
        "used_for": "the 133 transcripts, 50 of which are scored",
        "licence": "none published",
        "note": (
            "Released \u201cto benefit research community\u201d, with a citation "
            "requested. Fetched"
            "at run time."
        ),
    },
    {
        "source": "iCARE",
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

    #: Fields a lane is *not* keyed on. `harness_version` because that is what
    #: this function chooses between. `judge_settings` because a row written
    #: before that field existed records none, and an absent record of the
    #: settings is not a different instrument -- it is the same instrument,
    #: less well described. Leaving it in the lane drew two identical Gemini
    #: tables side by side, one from each side of the commit that added it.
    CHOSEN_BETWEEN = ("harness_version", "judge_settings")

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
        # Newer harness wins; at the same harness, the group that records its
        # judge settings beats the one that does not. Strictly more informative
        # supersedes strictly less, which is the same rule `latest` applies to
        # a re-run.
        return (field(key, "harness_version"), bool(groups[key][0].judge_settings))

    # Only a drawable group can set the bar. A lane whose every group is
    # unpublishable leaves `best` empty for that lane, and nothing there is
    # superseded *by a harness* -- it is withdrawn for the other reason.
    best: dict[tuple, tuple] = {}
    for key in groups:
        if records_its_instrument(key):
            lane = lane_of(key)
            best[lane] = max(best.get(lane, ("", False)), rank(key))

    keep: dict[tuple, list[Row]] = {}
    superseded = []
    for key, group in groups.items():
        harness = field(key, "harness_version")
        lane = lane_of(key)
        current = best.get(lane, ("", False))[0]

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

        if not reasons:
            keep[key] = group
            continue
        superseded.append(
            {
                "track": field(key, "track"),
                "harness_version": harness,
                "current_harness_version": current if "harness" in reasons else "",
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


def build(rows: list[Row], saturations: list[dict] | None = None) -> dict:
    """Shape the rows into the JSON both presentations read.

    `saturations` carries, per judge, which systems that judge's evidence
    cannot tell apart. Optional because a coverage-only build has none, and
    absent is drawn as "not measured for this table" rather than as agreement.

    Groups that disagree on any version field become separate tables rather than
    separate rows in one table. The newest harness per track and judge is drawn;
    older ones are named in `superseded` so a stale number is explainable rather
    than silently gone.
    """
    current = _with_borrowed_reasons(results.latest(rows))
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
                # Every comparability field, so a reader can see exactly what
                # this table's rows had to agree on. Named from the tuple
                # rather than listed here: the list grew a sixth entry once and
                # a hand-written copy would have quietly kept showing five.
                "versions": {
                    name: versions[name] for name in results.COMPARABILITY_KEYS if name != "track"
                },
                "scored": any(row.is_scored for row in group),
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
                "rows": rendered,
                # Drawn only where something to show exists. A column of empty
                # cells is worse than no column: it reads as missing data rather
                # than as a control this provider does not have.
                "has_effort": any(row["effort"] for row in rendered),
                "has_thinking": any(row["thinking_tokens"] for row in rendered),
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

    return {
        "tables": tables,
        # Which one to draw and what may be switched to. Decided here, because
        # every other ordering on this page is.
        "selection": _selection(tables),
        # Not drawn, but named. A number that used to be published and is not
        # any more should be explainable rather than silently gone.
        "superseded": superseded,
        "protocol": protocol(),
        "corpus": corpus.load_or_build(),
        "licences": LICENCES,
        "generated_from": str(results.ROWS_PATH.name),
    }


def protocol() -> dict:
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

    return {
        "sections": sections,
        "criteria": criteria,
        "icare_sections": icare_sections,
    }


def ihope_temporal() -> tuple[int, ...]:
    from tnb.datasets import ihope

    return ihope.TEMPORAL_SECTIONS


def _judges_own_family(row: Row) -> str:
    """The vendor this row's judge shares with the system it scored, or "".

    `docs/limitations.md` has promised since the second judge was added that
    these cells are "marked in the table where they sit", and nothing marked
    them -- not `renderTable`, not the row data it draws from. The effect the
    mark warns about is no longer hypothetical: with the comparison group
    corrected to the vendor that built each model, `gpt-5.6-terra` shows a
    detected self-preference of +0.027 completeness.

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
        "thinking_tokens": row.settings.thinking_tokens,
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
                f"{len(models)} system(s) have written their notes and none has been scored "
                f"yet: {names}."
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
        for column in columns:
            note = f"**{column['label']}** ({column['scale']}) — {column['definition']}"
            if column["caveat"]:
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
        "settings": (
            "the judge's settings were not recorded, so the rows cannot be shown to "
            "have come from one instrument"
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
        track: {**found, "track": track, "track_label": TRACK_TITLES.get(track, track)}
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
