"""Draw the pilot's two English conversations and the translator check's sample.

Protocol 2.2.0 froze the pilot over two public AnnoMI conversations and their
Czech translations. Which two would otherwise be chosen by whoever ran the
first translation, so the choice is made here by a rule with a seed, written
to a tracked record, and re-derived by the test suite on any machine that has
the corpus. The rule is a convention and is declared as one: it keeps the
pilot away from the shortest and the longest material and away from two
conversations cut from one AnnoMI video, and it decides nothing else.

The back-translation sample the translator check measures candidates on is
drawn from other conversations, so that the check never scores a model on the
very text it will later translate.

Conversation text is written under the ignored `local/` only; the tracked
record carries identifiers, the rule, counts and digests.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

SEED = 20260921
PILOT_CASES = 2
SAMPLE_CONVERSATIONS = 4
SAMPLE_TURNS_EACH = 10
REPO = Path(__file__).resolve().parents[3]
RECORD = Path(__file__).resolve().parent / "pilot-cases.json"
WORKSPACE = REPO / "local" / "gen2-translation"

RULE = [
    "turn count between the 25th and 75th percentile of the 50 (inclusive), so the pilot "
    "is neither the shortest nor the longest material",
    "shuffled with the seed; the first two from distinct AnnoMI videos are the pilot cases",
    "the back-translation sample draws ten turns each from four other conversations outside "
    "the pilot videos, seed plus one",
]


def digest(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _turns(session) -> list[dict]:
    return [{"speaker": t.speaker, "text": t.text} for t in session.turns]


def draw(
    sessions: dict, clusters: dict[str, str], *, seed: int = SEED, today: str
) -> tuple[dict, dict]:
    """The tracked record and the local files, from the sessions and their video groups.

    Pure: the same sessions, groups and seed give the same record, which is
    what lets a test on another machine re-derive it.
    """
    lengths = sorted(len(s.turns) for s in sessions.values())
    q1, q3 = lengths[len(lengths) // 4], lengths[3 * len(lengths) // 4]
    middle = sorted(sid for sid, s in sessions.items() if q1 <= len(s.turns) <= q3)
    random.Random(seed).shuffle(middle)
    pilot: list[str] = []
    for sid in middle:
        if clusters.get(sid) in {clusters.get(p) for p in pilot}:
            continue
        pilot.append(sid)
        if len(pilot) == PILOT_CASES:
            break
    pilot_videos = {clusters.get(p) for p in pilot}
    others = [
        sid
        for sid in sorted(sessions)
        if sid not in pilot and clusters.get(sid) not in pilot_videos
    ]
    random.Random(seed + 1).shuffle(others)
    sample_from = others[:SAMPLE_CONVERSATIONS]

    files: dict[str, dict] = {}
    cases = []
    for sid in pilot:
        body = {"id": sid, "turns": _turns(sessions[sid])}
        files[f"conversations/{sid}.json"] = body
        cases.append(
            {
                "id": sid,
                "video_group": clusters.get(sid),
                "turns": len(sessions[sid].turns),
                "words": sessions[sid].word_count,
                "digest": digest(body),
            }
        )
    sample = []
    for sid in sample_from:
        turns = sessions[sid].turns
        picked = random.Random(seed + 2 + int(sid)).sample(range(len(turns)), SAMPLE_TURNS_EACH)
        for i in sorted(picked):
            sample.append(
                {
                    "conversation": sid,
                    "index": i,
                    "speaker": turns[i].speaker,
                    "text": turns[i].text,
                }
            )
    files["sample.json"] = {"turns": sample}
    record = {
        "version": "pilot-cases-v1",
        "date": today,
        "seed": seed,
        "source": "AnnoMI conversations released through TN-Eval (50)",
        "rule": RULE,
        "turn_count_quartiles": [q1, q3],
        "pilot_cases": cases,
        "translation_sample": {
            "conversations": sample_from,
            "turns": len(sample),
            "digest": digest(sample),
        },
        "note": "Text stays under local/; this record carries identifiers, counts and "
        "digests only.",
    }
    return record, files


def main() -> None:
    from tnb.datasets import tneval
    from tnb.scoring.clusters import video_clusters

    sessions = {s.id: s for s in tneval.load()}
    record, files = draw(sessions, video_clusters(set(sessions)), today="2026-09-21")
    for rel, body in files.items():
        path = WORKSPACE / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    RECORD.write_bytes((json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    sample_turns = record["translation_sample"]["turns"]
    print(len(record["pilot_cases"]), "pilot cases;", sample_turns, "sample turns")


if __name__ == "__main__":
    main()
