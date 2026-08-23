"""The TN-Eval track: 50 AnnoMI conversations with therapist-written notes.

Two sources are joined here. AnnoMI supplies the transcripts; TN-Eval-Data
supplies, for each conversation, a therapist-written note plus rubric and Likert
ratings from two human annotators and two LLM judges. Those human ratings are
the calibration anchor described in ``docs/methodology.md`` — they are what makes
it possible to check the judge against a person before trusting a leaderboard.
"""

from __future__ import annotations

import csv
import json

from tnb.datasets.base import Session, Turn, fetch

ANNOMI_URL = "https://github.com/uccollab/AnnoMI/raw/refs/heads/main/AnnoMI-full.csv"
NOTES_URL = (
    "https://raw.githubusercontent.com/amazon-science/TN-Eval-Data/main/data/notes_part{part}.json"
)
NOTE_PARTS = range(1, 11)

#: Speaker labels TN-Eval writes into the prompt. Reproduced exactly so our
#: generations are comparable with their published numbers.
THERAPIST_LABEL = "therapist"
CLIENT_LABEL = "client"


def _load_notes() -> dict[str, dict]:
    """The 50 released conversations, keyed by AnnoMI transcript id."""
    notes: dict[str, dict] = {}
    for part in NOTE_PARTS:
        path = fetch(NOTES_URL.format(part=part), f"tneval_notes_part{part}.json")
        for entry in json.loads(path.read_text(encoding="utf-8")):
            notes[str(entry["id"])] = entry
    return notes


def _load_transcripts(wanted: set[str]) -> dict[str, list[Turn]]:
    """Read AnnoMI and rebuild the turn sequence for the wanted transcripts.

    AnnoMI-full carries one row per (utterance, annotator), so the same
    utterance appears several times. TN-Eval deduplicates before grouping; we do
    the same, keyed on utterance_id, so the transcript we send to a model is the
    transcript they sent to theirs.
    """
    path = fetch(ANNOMI_URL, "AnnoMI-full.csv")
    seen: dict[str, set[int]] = {}
    turns: dict[str, list[tuple[int, Turn]]] = {}

    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            transcript_id = str(row["transcript_id"])
            if transcript_id not in wanted or row["mi_quality"] != "high":
                continue

            utterance_id = int(row["utterance_id"])
            if utterance_id in seen.setdefault(transcript_id, set()):
                continue
            seen[transcript_id].add(utterance_id)

            speaker = "therapist" if row["interlocutor"] == "therapist" else "client"
            turns.setdefault(transcript_id, []).append(
                (utterance_id, Turn(speaker=speaker, text=row["utterance_text"]))
            )

    return {
        transcript_id: [turn for _, turn in sorted(items, key=lambda pair: pair[0])]
        for transcript_id, items in turns.items()
    }


def load(limit: int | None = None) -> list[Session]:
    """Load the TN-Eval track.

    The conversation ids come from TN-Eval's own released data rather than from
    a rule. Their paper describes the set as "the first 50 conversations from the
    high-quality split", but the released ids run to 129 and skip several along
    the way, so reconstructing the selection by sorting and slicing would pair
    notes with the wrong transcripts. The ids are in the data; we use them.
    """
    notes = _load_notes()
    transcripts = _load_transcripts(set(notes))

    missing = sorted(set(notes) - set(transcripts))
    if missing:
        raise RuntimeError(
            f"AnnoMI has no high-quality transcript for TN-Eval ids {missing}. "
            "The upstream corpus may have changed; delete data/ and re-fetch."
        )

    sessions = [
        Session(
            id=transcript_id,
            source="tneval",
            turns=tuple(transcripts[transcript_id]),
            reference=None,  # reference-free protocol: the rubric needs no gold note
            meta={
                "mi_quality": entry["mi_quality"],
                "human_note": entry["human"]["note"],
                "human_ratings": {
                    key: value for key, value in entry["human"].items() if key != "note"
                },
                "model_notes": {
                    key: value
                    for key, value in entry.items()
                    if key not in {"id", "mi_quality", "human"}
                },
            },
        )
        for transcript_id, entry in sorted(notes.items(), key=lambda pair: int(pair[0]))
    ]
    return sessions[:limit] if limit else sessions
