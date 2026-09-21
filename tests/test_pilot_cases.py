"""The pilot's two conversations are drawn by a recorded rule, not picked.

Protocol 2.2.0 says the pilot runs on two public AnnoMI conversations and their
translations. Which two is a choice that shapes every number the pilot
produces, so it is made by a seeded rule in `draw_pilot_cases.py`, recorded
without any transcript text, and re-derived here on a machine that has the
corpus. The sample the translator check scores candidates on comes from other
conversations, so that no model is measured on the text it will translate.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "research" / "gen2" / "translation"))

import draw_pilot_cases as drawing  # noqa: E402

RECORD = REPO / "research" / "gen2" / "translation" / "pilot-cases.json"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [t for k, v in value.items() for t in _strings(k) + _strings(v)]
    if isinstance(value, list):
        return [t for item in value for t in _strings(item)]
    return []


def test_the_record_names_the_cases_and_carries_no_text():
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert record["version"] == "pilot-cases-v1"
    assert record["seed"] == drawing.SEED and record["rule"] == drawing.RULE
    cases = record["pilot_cases"]
    assert len(cases) == drawing.PILOT_CASES
    assert len({c["video_group"] for c in cases}) == len(cases), "two cuts of one video"
    for case in cases:
        assert HEX64.match(case["digest"]) and case["turns"] > 0 and case["words"] > 0
    q1, q3 = record["turn_count_quartiles"]
    assert all(q1 <= c["turns"] <= q3 for c in cases)
    sample = record["translation_sample"]
    assert sample["turns"] == drawing.SAMPLE_CONVERSATIONS * drawing.SAMPLE_TURNS_EACH
    assert HEX64.match(sample["digest"])
    assert not set(sample["conversations"]) & {c["id"] for c in cases}
    for text in _strings(record):
        assert text.isascii(), "the record is public and carries no transcript"
    assert '"text"' not in json.dumps(record), "a turn's text belongs under local/"


def test_the_record_is_what_the_rule_draws():
    """Re-derived, not trusted, wherever the corpus is."""
    if not (REPO / "data" / "AnnoMI-full.csv").exists():
        pytest.skip("the corpus is fetched at run time and is not on this machine")
    from tnb.datasets import tneval
    from tnb.scoring.clusters import video_clusters

    record = json.loads(RECORD.read_text(encoding="utf-8"))
    sessions = {s.id: s for s in tneval.load()}
    derived, files = drawing.draw(sessions, video_clusters(set(sessions)), today=record["date"])
    assert derived == record
    expected = {f"conversations/{c['id']}.json" for c in record["pilot_cases"]} | {"sample.json"}
    assert set(files) == expected
    sample_ids = {t["conversation"] for t in files["sample.json"]["turns"]}
    assert sample_ids == set(record["translation_sample"]["conversations"])
