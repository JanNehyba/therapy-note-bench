"""The iCARE track: iHOPE sessions with expert gold notes in 17 sections.

The transcripts and gold notes are read from TheraFuse rather than from the
iCARE repository the paper cites. Both publish the same corpus, but TheraFuse
ships it as two JSON files with dialogue and note already joined, while iCARE
spreads it over 174 directories of CSV pairs. Verified equivalent: 134 + 40 =
174, with test ids matching the iCARE split directories exactly.
See ``docs/datasets.md``.
"""

from __future__ import annotations

import json
import re

from tnb.datasets.base import Session, Turn, fetch

THERAFUSE_URL = (
    "https://raw.githubusercontent.com/ai4mhx/TheraFuse/main/data/graph_{split}_aiims.json"
)
INSTRUCTIONS_URL = "https://raw.githubusercontent.com/proadhikary/iCARE/main/instructions.json"

#: Speaker labels the iHOPE dialogues use, kept for prompt fidelity.
THERAPIST_LABEL = "Therapist"
CLIENT_LABEL = "Patient"

#: The 17 sections, in the order the doctors' prompts are stored.
SECTION_COUNT = 17

#: Sections 5 and 17 -- past-session and next-session details. The paper reports
#: that every model failed at these, so they get their own leaderboard column
#: instead of being averaged into the rest. One-based, as the paper numbers them.
TEMPORAL_SECTIONS = (5, 17)

_TURN_SPLIT = re.compile(r"\s*;\s*")
_SPEAKER = re.compile(r"^(Therapist|Patient|Client)\s*:\s*(.*)$", re.IGNORECASE | re.DOTALL)


def load_instructions() -> list[str]:
    """The 17 section prompts, approved by clinicians at AIIMS Delhi.

    Used verbatim: the point is to measure models on their task, not on ours.
    """
    path = fetch(INSTRUCTIONS_URL, "icare_instructions.json")
    prompts = json.loads(path.read_text(encoding="utf-8"))["doctors_prompts"]
    if len(prompts) != SECTION_COUNT:
        raise RuntimeError(
            f"Expected {SECTION_COUNT} iCARE section prompts, found {len(prompts)}. "
            "Upstream changed; the temporal-section indices need rechecking."
        )
    return list(prompts)


def _parse_dialogue(text: str) -> list[Turn]:
    """Split ``Therapist: ... ; Patient: ...`` into turns.

    Segments without a speaker prefix are appended to the previous turn rather
    than dropped -- they are continuations produced by semicolons inside an
    utterance, and losing them would quietly shorten the transcript.
    """
    turns: list[Turn] = []
    for segment in _TURN_SPLIT.split(text):
        segment = segment.strip()
        if not segment:
            continue

        match = _SPEAKER.match(segment)
        if match:
            speaker = "therapist" if match.group(1).lower() == "therapist" else "client"
            turns.append(Turn(speaker=speaker, text=match.group(2).strip()))
        elif turns:
            previous = turns[-1]
            turns[-1] = Turn(previous.speaker, f"{previous.text}; {segment}")
        else:
            turns.append(Turn("client", segment))
    return turns


def load(split: str = "test", limit: int | None = None) -> list[Session]:
    """Load iHOPE sessions. ``split`` is 'test' (40), 'train' (134) or 'all'.

    The benchmark scores the held-out test split, matching the paper.

    One session upstream carries an empty gold note. It is dropped rather than
    scored against nothing, and the drop is recorded in the returned metadata so
    a count of 39 is explainable rather than mysterious.
    """
    splits = ("test", "train") if split == "all" else (split,)

    kept: list[tuple[str, dict]] = []
    dropped: list[str] = []
    for part in splits:
        path = fetch(THERAFUSE_URL.format(split=part), f"ihope_{part}.json")
        for entry in json.loads(path.read_text(encoding="utf-8")):
            if (entry.get("summary") or "").strip():
                kept.append((part, entry))
            else:
                dropped.append(str(entry["id"]))

    # Built only once `dropped` is final, so every session reports the same
    # complete list rather than however much had been found when it was created.
    sessions = [
        Session(
            id=str(entry["id"]),
            source="ihope",
            turns=tuple(_parse_dialogue(entry["dialogue"])),
            reference=entry["summary"].strip(),
            meta={"split": part, "dropped_empty_reference": tuple(dropped)},
        )
        for part, entry in kept
    ]
    sessions.sort(key=lambda session: int(session.id))
    return sessions[:limit] if limit else sessions
