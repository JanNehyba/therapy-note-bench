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

import json
from pathlib import Path

from tnb import corpus, results
from tnb.config import REPO_ROOT
from tnb.results import Row
from tnb.scoring import tneval as rubric
from tnb.tasks import icare, soap

DOCS_DIR = REPO_ROOT / "docs"
DATA_PATH = DOCS_DIR / "leaderboard.json"
PAGE_PATH = DOCS_DIR / "index.html"
README_PATH = REPO_ROOT / "README.md"

LEADERBOARD_MARKERS = ("<!-- LEADERBOARD:BEGIN -->", "<!-- LEADERBOARD:END -->")
CALIBRATION_MARKERS = ("<!-- CALIBRATION:BEGIN -->", "<!-- CALIBRATION:END -->")
CALIBRATION_PATH = DOCS_DIR / "calibration.json"
SATURATION_PATH = DOCS_DIR / "saturation.json"
JUDGES_PATH = DOCS_DIR / "judges.json"

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
        ("temporal", 3),
    ),
}

#: The iCARE measures. Same shape as `tneval.MEASURES`, which owns the TN-Eval
#: ones -- each carries the heading, the range, what it counts, and what a
#: reader must not conclude from it.
ICARE_MEASURES: dict[str, dict[str, str]] = {
    "rouge_l": {
        "label": "ROUGE-L",
        "scale": "0-1",
        "definition": (
            "Longest-common-subsequence overlap with the expert note. Rewards using "
            "the same words in the same order."
        ),
        "caveat": (
            "Cannot tell a good paraphrase from a wrong answer. The source paper "
            "found it disagrees with what clinicians preferred."
        ),
    },
    "bertscore": {
        "label": "BERTScore",
        "scale": "0-1",
        "definition": "Embedding similarity to the expert note. Tolerates paraphrase.",
        "caveat": "A fluent note about the wrong session still scores well.",
    },
    "trace": {
        "label": "TRACE",
        "scale": "1-5",
        "definition": (
            "Trustworthiness, relevance, accuracy, comprehensiveness and expression, averaged."
        ),
        "caveat": (
            "A re-implementation with no human anchor: the authors never published "
            "their ratings, so unlike the TN-Eval track this number is not "
            "calibrated against anybody."
        ),
    },
    "temporal": {
        "label": "Temporal",
        "scale": "0-1",
        "definition": "Sections {sections} only -- what happened last time, what happens next.",
        "caveat": (
            "Kept out of the average. The source paper reports every model it tested "
            "failing here, so a low number is the expected result, not a surprise."
        ),
    },
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
}


def measure_table(track: str) -> dict[str, dict[str, str]]:
    """The measure definitions for one track. Unknown tracks get nothing."""
    return rubric.MEASURES if track == results.TRACK_TNEVAL else ICARE_MEASURES


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
    results.TRACK_ICARE: "iCARE / iHOPE · 17 sections per session",
}

TRACK_BLURBS = {
    results.TRACK_TNEVAL: (
        "Reference-free. 23 completeness criteria, conciseness scored sentence by "
        "sentence, faithfulness against the full transcript."
    ),
    results.TRACK_ICARE: (
        "Automatic metrics and a TRACE judge side by side, because the source paper "
        "found they disagree. That disagreement is a result, not an error."
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
    """Best first on the track's leading metric; unscored rows last."""
    if not row.is_scored:
        return (1, 0.0, row.system_id)
    leading = RANKING_MEASURES.get(track) or COLUMNS[track][0][0]
    return (0, -float(row.metrics.headline.get(leading, 0.0)), row.system_id)


def _ordered_sections(names: list[str]) -> list[str]:
    known = [name for name in SECTION_ORDER if name in names]
    rest = sorted(name for name in names if name not in SECTION_ORDER)
    return known + rest


def build(rows: list[Row]) -> dict:
    """Shape the rows into the JSON both presentations read.

    Groups that disagree on any version field become separate tables rather than
    separate rows in one table. The newest group per track is `current`; older
    ones stay in `superseded` so a stale number is explainable rather than
    silently gone.
    """
    current = results.latest(rows)
    tables = []

    for key, group in results.comparable_groups(current).items():
        track, harness_version, prompt_version, judge_model, judge_prompt_version = key
        if track not in COLUMNS:
            continue
        rendered = [_render_row(row) for row in sorted(group, key=lambda r: _sort_key(r, track))]
        tables.append(
            {
                "track": track,
                "title": TRACK_TITLES.get(track, track),
                "blurb": TRACK_BLURBS.get(track, ""),
                "design": TRACK_DESIGN.get(track, {}),
                "versions": {
                    "harness_version": harness_version,
                    "prompt_version": prompt_version,
                    "judge_model": judge_model,
                    "judge_prompt_version": judge_prompt_version,
                },
                "scored": any(row.is_scored for row in group),
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
    return {
        "tables": tables,
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


def _render_row(row: Row) -> dict:
    return {
        "system_id": row.system_id,
        "label": row.label,
        "system_type": row.system_type,
        "provider": row.provider,
        "effort": row.settings.effort,
        "settings": row.settings.summary,
        # A row produced under conditions the rest of the table did not share is
        # marked in place rather than dropped or silently normalised -- WMT's
        # convention for systems that used extra resources. The forced
        # temperature on the GPT family is exactly this case.
        "settings_differ": bool(row.settings.temperature_forced),
        "n_attempted": row.n_sessions_attempted,
        "n_generated": row.n_sessions_generated,
        "n_scored": row.n_sessions_scored,
        "n_failed": row.n_failed,
        "failure_reasons": row.failure_reasons,
        "unreached_reasons": row.unreached_reasons,
        "n_unreached": sum(row.unreached_reasons.values()),
        "headline": row.metrics.headline,
        "by_section": {
            section: row.metrics.by_section[section]
            for section in _ordered_sections(list(row.metrics.by_section))
        },
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

    blocks: list[str] = []
    for table in data["tables"]:
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
        lines = [
            f"**{table['title']}**",
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
            if row["n_failed"]:
                written += f" ({row['n_failed']} unusable)"
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

    blocks.append(
        "See the [full leaderboard](https://jannehyba.github.io/therapy-note-bench/) "
        "for per-section detail, the reference systems and the published numbers."
    )
    return "\n\n".join(blocks)


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
    data = build(rows)
    data["calibration"] = load_calibration(docs_dir)
    data["similarity_example"] = similarity_example()
    data["saturation"] = _load_json(docs_dir / SATURATION_PATH.name)
    data["judges"] = _load_json(docs_dir / JUDGES_PATH.name)

    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / DATA_PATH.name).write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    (docs_dir / PAGE_PATH.name).write_text(render_page(data), encoding="utf-8")
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


def render_page(data: dict) -> str:
    """The standalone page: the data inlined, no build step, no dependency."""
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
    for char, escape in _INLINE_ESCAPES.items():
        payload = payload.replace(char, escape)
    return PAGE_TEMPLATE.replace("__DATA__", payload)


PAGE_TEMPLATE = (Path(__file__).parent / "templates" / "leaderboard.html").read_text(
    encoding="utf-8"
)
