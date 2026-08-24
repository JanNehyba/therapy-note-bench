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

from tnb import results
from tnb.config import REPO_ROOT
from tnb.results import Row

DOCS_DIR = REPO_ROOT / "docs"
DATA_PATH = DOCS_DIR / "leaderboard.json"
PAGE_PATH = DOCS_DIR / "index.html"
README_PATH = REPO_ROOT / "README.md"

LEADERBOARD_MARKERS = ("<!-- LEADERBOARD:BEGIN -->", "<!-- LEADERBOARD:END -->")

#: Column order per track: (key, heading, how many decimals).
#:
#: Reproduced from what each protocol actually measures -- see
#: docs/methodology.md. Faithfulness carries an asterisk because TN-Eval measured
#: near-zero human agreement on the Likert scales; TRACE carries a dagger
#: because the authors' human ratings were never published.
COLUMNS: dict[str, tuple[tuple[str, str, int], ...]] = {
    results.TRACK_TNEVAL: (
        ("completeness", "Completeness", 3),
        ("conciseness", "Conciseness", 3),
        ("faithfulness", "Faithfulness*", 2),
    ),
    results.TRACK_ICARE: (
        ("rouge_l", "ROUGE-L", 3),
        ("bertscore", "BERTScore", 3),
        ("trace", "TRACE†", 2),
        ("temporal", "Temporal", 3),
    ),
}

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

#: Order the sections of a row's breakdown so a reader sees SOAP in SOAP order
#: rather than alphabetically.
SECTION_ORDER = ("subjective", "objective", "assessment", "plan")


def _sort_key(row: Row, track: str):
    """Best first on the track's leading metric; unscored rows last."""
    if not row.is_scored:
        return (1, 0.0, row.system_id)
    leading = COLUMNS[track][0][0]
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
        tables.append(
            {
                "track": track,
                "title": TRACK_TITLES.get(track, track),
                "blurb": TRACK_BLURBS.get(track, ""),
                "versions": {
                    "harness_version": harness_version,
                    "prompt_version": prompt_version,
                    "judge_model": judge_model,
                    "judge_prompt_version": judge_prompt_version,
                },
                "scored": any(row.is_scored for row in group),
                "columns": [
                    {"key": key_, "label": label, "digits": digits}
                    for key_, label, digits in COLUMNS[track]
                ],
                "rows": [
                    _render_row(row) for row in sorted(group, key=lambda r: _sort_key(r, track))
                ],
            }
        )

    tables.sort(
        key=lambda table: (
            table["track"] != results.TRACK_TNEVAL,
            table["versions"]["prompt_version"],
        )
    )
    return {"tables": tables, "generated_from": str(results.ROWS_PATH.name)}


def _render_row(row: Row) -> dict:
    return {
        "system_id": row.system_id,
        "label": row.label,
        "system_type": row.system_type,
        "provider": row.provider,
        "n_attempted": row.n_sessions_attempted,
        "n_generated": row.n_sessions_generated,
        "n_scored": row.n_sessions_scored,
        "n_failed": row.n_failed,
        "failure_reasons": row.failure_reasons,
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


def render_readme_section(data: dict) -> str:
    """The shop window: e-INFRA models only, headline numbers only.

    Anyone who wants the breakdown follows the link to the page. Putting 23
    criteria in a README is how a README stops being read.
    """
    if not data["tables"]:
        return "*No runs yet. The first run will populate this section automatically.*"

    blocks: list[str] = []
    for table in data["tables"]:
        models = [row for row in table["rows"] if row["system_type"] == "model"]
        if not models:
            continue

        columns = table["columns"]
        multi_provider = len({row["provider"] for row in models}) > 1
        header = ["Model"]
        if multi_provider:
            header.append("Provider")
        header += [column["label"] for column in columns] + ["Sessions"]
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
            coverage = f"{row['n_generated']}/{row['n_attempted']}"
            if row["n_failed"]:
                coverage += f" ({row['n_failed']} unusable)"
            cells.append(coverage)
            lines.append("| " + " | ".join(cells) + " |")
        blocks.append("\n".join(lines))

    if not any(table["scored"] for table in data["tables"]):
        blocks.append(
            "*Notes are generated; no scores yet. The judge runs in phase 3 and this "
            "table fills in then.* See the "
            "[full leaderboard](https://jannehyba.github.io/therapy-note-bench/) for "
            "per-section detail, the reference systems and the published numbers."
        )
    else:
        blocks.append(
            "See the [full leaderboard](https://jannehyba.github.io/therapy-note-bench/) "
            "for per-section detail, the reference systems and the published numbers."
        )
    return "\n\n".join(blocks)


def update_readme(section: str, path: Path | None = None) -> bool:
    """Replace the marked block. Returns whether anything changed."""
    path = path or README_PATH
    begin, end = LEADERBOARD_MARKERS
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


def write(rows: list[Row], *, docs_dir: Path | None = None, readme: Path | None = None) -> dict:
    """Write all three artefacts. Returns the data that was rendered."""
    docs_dir = docs_dir or DOCS_DIR
    data = build(rows)

    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / DATA_PATH.name).write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    (docs_dir / PAGE_PATH.name).write_text(render_page(data), encoding="utf-8")
    update_readme(render_readme_section(data), readme)
    return data


def render_page(data: dict) -> str:
    """The standalone page: the data inlined, no build step, no dependency."""
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return PAGE_TEMPLATE.replace("__DATA__", payload)


PAGE_TEMPLATE = (Path(__file__).parent / "templates" / "leaderboard.html").read_text(
    encoding="utf-8"
)
