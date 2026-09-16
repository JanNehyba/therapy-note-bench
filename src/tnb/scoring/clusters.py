"""What the dominance test costs when the conversations are not independent.

`edges` resamples conversations: one draw takes 50 of them with replacement and
asks whether the winner still wins. That treats each conversation as one
independent piece of evidence, and the 50 AnnoMI conversations are transcripts
of 43 videos: five videos carry more than one conversation, twelve
conversations sit in those five, and a draw can take one of them without its
relatives and count a dependency as independent evidence. Gen-2's import
adapter already records this dependency for its own
cases; the audit of 2026-09-15 (A12) asked what it does to Gen-1's published
groups, and asked for the answer as a separate analysis rather than as a quiet
change to the tables.

So this module runs the same test twice on the same means and the same
per-conversation values: once drawing conversations, once drawing whole videos.
What it writes is the comparison -- how many claims survive each way, and every
claim whose verdict depends on the choice.

**It is a sensitivity analysis, and it replaces nothing.** `docs/edges-*.json`
stays as it is, the Group column on the page keeps being drawn from it, and
this artefact says which of those groups rest on a claim that the clustered
draw does not keep. Clustering costs precision -- 43 things to draw instead of
50 -- so a claim that stops holding may have stopped for that reason alone, and
the artefact reports the loss in draws beside the loss in claims rather than
calling the difference an error.

**The iCARE track is not clustered here.** Its 40 sessions come from iHOPE and
this repository has no video ancestry for them; a cluster map nobody can
establish would be a guess, and the artefact says so instead of inventing one.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

from tnb import results
from tnb.scoring import edges

#: Where the AnnoMI transcript-to-video mapping is read from. Fetched at run
#: time into the ignored `data/`, like every other corpus here.
ANNOMI = "AnnoMI-full.csv"

#: Tracks whose conversations come from AnnoMI, and therefore from videos.
CLUSTERED_TRACKS = (results.TRACK_TNEVAL, results.TRACK_PDSQI)


def artefact_path(track: str, docs_dir: Path | None = None) -> Path:
    from tnb import report

    # Deliberately not `edges-<track>-...`: the tests glob that name for the
    # published dominance artefacts and check every one of them against the
    # table, which this file is not and would fail.
    return (docs_dir or report.DOCS_DIR) / f"clustered-edges-{track}.json"


def load(track: str, docs_dir: Path | None = None) -> dict | None:
    path = artefact_path(track, docs_dir)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def video_clusters(sessions: set[str], path: Path | None = None) -> dict[str, str]:
    """Conversation to video, for the conversations asked about.

    The same dependency Gen-2's `legacy.annomi_video_groups` records, computed
    here so that Gen-1 keeps no dependency on the Gen-2 core, and hashed the
    same way so the two can be compared. A conversation whose video is missing
    or ambiguous is left out of the map rather than guessed at, and
    `draw_plan` then treats it as its own cluster, which is the conservative
    reading: it assumes no dependency it cannot see.
    """
    from tnb.datasets.base import fetch
    from tnb.datasets.tneval import ANNOMI_URL

    found: dict[str, set[str]] = {key: set() for key in sessions}
    with fetch(ANNOMI_URL, ANNOMI).open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["transcript_id"] in found and row.get("video_url"):
                found[row["transcript_id"]].add(row["video_url"])
    return {
        key: "annomi-video:" + hashlib.sha256(next(iter(value)).encode("utf-8")).hexdigest()
        for key, value in found.items()
        if len(value) == 1
    }


def compare(loose: dict, clustered: dict) -> dict:
    """The two runs, side by side, claim by claim."""
    keyed = {(edge["winner"], edge["loser"]): edge for edge in clustered["edges"]}
    changed, unchanged = [], 0
    for edge in loose["edges"]:
        other = keyed.get((edge["winner"], edge["loser"]))
        if other is None:
            continue
        if edge["holds"] != other["holds"]:
            changed.append(
                {
                    "winner": edge["winner"],
                    "loser": edge["loser"],
                    "n_shared": edge["n_shared"],
                    "n_drawn_clustered": other["n_drawn"],
                    "p_holds_conversations": edge["p_holds"],
                    "p_holds_clusters": other["p_holds"],
                    "kept_by_conversations_only": edge["holds"],
                }
            )
        else:
            unchanged += 1
    return {
        "tested": len(loose["edges"]),
        "verdict_unchanged": unchanged,
        "verdict_changed": len(changed),
        "changed": sorted(changed, key=lambda row: (row["winner"], row["loser"])),
        "holds": {
            "conversations": sum(1 for edge in loose["edges"] if edge["holds"]),
            "clusters": sum(1 for edge in clustered["edges"] if edge["holds"]),
        },
        "layers": {"conversations": loose["layers"], "clusters": clustered["layers"]},
        "undominated": {
            "conversations": len(loose["undominated"]),
            "clusters": len(clustered["undominated"]),
        },
    }


def build_track(
    track: str,
    *,
    rows: list[results.Row] | None = None,
    samples: int = edges.SAMPLES,
    cache_root: Path | None = None,
    docs_dir: Path | None = None,
) -> dict | None:
    """Both runs and their comparison, or None when the track cannot be clustered."""
    from tnb import report

    if track not in CLUSTERED_TRACKS:
        return None
    current = report.current_rows(rows if rows is not None else results.load())
    by_judge = edges.published(current, track)
    if len(by_judge) < 2:
        return None
    per_session = {
        judge_model: edges.LOADERS[track](judge_model, cache_root=cache_root)
        for judge_model in by_judge
    }
    sessions = {
        session
        for scores in per_session.values()
        for system in scores.values()
        for column in system.values()
        for session in column
    }
    clusters = video_clusters(sessions)
    if not clusters:
        return None
    loose = edges.examine(track, report.COLUMNS[track], by_judge, per_session, samples=samples)
    clustered = edges.examine(
        track,
        report.COLUMNS[track],
        by_judge,
        per_session,
        samples=samples,
        clusters=clusters,
    )
    unmapped = sorted(sessions - set(clusters))
    sizes: dict[str, int] = {}
    for session in sessions & set(clusters):
        sizes[clusters[session]] = sizes.get(clusters[session], 0) + 1
    return {
        "track": track,
        "built": dt.date.today().isoformat(),
        "samples": samples,
        "seed": clustered["seed"],
        "threshold": clustered["threshold"],
        "clustering": {
            "by": "AnnoMI source video",
            "conversations": len(sessions),
            "clusters": len(sizes) + len(unmapped),
            "videos": len(sizes),
            # The dependency itself, counted two ways: how many videos carry
            # more than one conversation, and how many conversations sit in
            # them. Both, because "seven fewer things to draw" and "twelve
            # conversations are not independent" are different sentences and a
            # reader needs the second one.
            "videos_with_more_than_one": sum(1 for count in sizes.values() if count > 1),
            "conversations_sharing_a_video": sum(count for count in sizes.values() if count > 1),
            "unmapped_conversations": len(unmapped),
            "source": ANNOMI,
        },
        "comparison": compare(loose, clustered),
        "reading": (
            "A sensitivity analysis of the published dominance test, not a replacement "
            "for it. Drawing whole videos removes a dependency and costs precision at "
            "the same time, so a claim that stops holding may have stopped for either "
            "reason; the artefact reports both and decides neither."
        ),
        "not_clustered": {
            results.TRACK_ICARE: "iHOPE sessions have no video ancestry in this repository; "
            "a cluster map would be a guess"
        },
    }


def write(track: str, found: dict, docs_dir: Path | None = None) -> Path:
    path = artefact_path(track, docs_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(found, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
