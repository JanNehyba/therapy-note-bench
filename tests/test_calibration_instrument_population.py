"""The instrument a calibration report is built at is decided by the wrong votes.

`dominant_instrument` counted every answer a judge had ever cached. A judge
scores two populations: the 150 notes TN-Eval released human ratings for, which
is all the calibration ever reads, and the leaderboard's nineteen systems, which
it never reads. Those two can sit at different thinking budgets -- and on this
repository they do, because the leaderboard was scored at 128 before the budget
moved and the calibration set was re-asked at 256.

When that happened, `gemini-2.5-pro`'s 30 252 leaderboard answers at 128 voted
out its 3 450 calibration answers at 256. Every pair was filtered, `calibrate`
returned no agreements, and `cmd_judges` -- which appends a report only if it
has agreements -- dropped the judge from `docs/judges.json` without a word. The
printed panel said seven candidates above six rows.

The bug is a silent absence, which is the failure mode this repository treats as
the serious one: nothing raised, nothing logged, one judge simply not there.
"""

from __future__ import annotations

import json
from collections import Counter

from tnb import judge
from tnb.scoring import calibration, tneval


def _answer(root, system_id, session_id, unit, fingerprint, answer="Yes"):
    judge.write_cached(
        judge.cache_path(
            judge.DEFAULT_MODEL,
            tneval.JUDGE_PROMPT_VERSION,
            "tneval",
            system_id,
            session_id,
            unit,
            fingerprint=fingerprint,
            root=root,
        ),
        {
            "ok": True,
            "provider": "tneval",
            "system_id": system_id,
            "session_id": session_id,
            "unit": unit,
            "answer": answer,
            "judge_fingerprint": fingerprint,
        },
    )


def test_notes_the_report_never_reads_cannot_choose_its_instrument(tmp_path):
    """A model the calibration does not pair must not outvote one it does."""
    at_128 = {"thinking_budget": 128}
    at_256 = {"thinking_budget": 256}

    # The calibration set: three answers about the therapist's note at 256.
    for unit in ("subjective.a", "subjective.b", "subjective.c"):
        _answer(tmp_path, "therapist", "9", unit, at_256)
    # The leaderboard: ten answers about a model with no human ratings, at 128.
    for index in range(10):
        _answer(tmp_path, "kimi-k3", str(index), "subjective.a", at_128)

    instrument = calibration.dominant_instrument(judge.DEFAULT_MODEL, root=tmp_path)
    assert instrument is None or instrument == json.dumps(at_256, sort_keys=True), (
        "the instrument was chosen by ten answers about a note the calibration never opens, "
        "which filters out every pair the report is made of"
    )

    seen: Counter = Counter()
    answers = calibration._answers_for(
        "9", "therapist", judge.DEFAULT_MODEL, root=tmp_path, seen=seen, instrument=instrument
    )
    assert len(answers) == 3, (
        "the calibration answers were dropped, so this judge would have produced no "
        "agreements and been left out of the published panel in silence"
    )


def test_two_instruments_inside_the_calibration_set_still_pick_the_larger(tmp_path):
    """Narrowing the population must not cost the rule it was there to apply."""
    at_128 = {"thinking_budget": 128}
    at_256 = {"thinking_budget": 256}

    for unit in ("subjective.a", "subjective.b", "subjective.c"):
        _answer(tmp_path, "therapist", "9", unit, at_128)
    _answer(tmp_path, "therapist", "9", "subjective.a", at_256, answer="No")
    # Louder, and about a note with no human ratings: still not a vote.
    for index in range(50):
        _answer(tmp_path, "kimi-k3", str(index), "subjective.a", at_256)

    instrument = calibration.dominant_instrument(judge.DEFAULT_MODEL, root=tmp_path)
    assert instrument == json.dumps(at_128, sort_keys=True), (
        "the larger set inside the calibration population has to win, and only answers "
        "inside it may vote"
    )

    answers = calibration._answers_for(
        "9", "therapist", judge.DEFAULT_MODEL, root=tmp_path, instrument=instrument
    )
    assert set(answers.values()) == {"Yes"}, "an answer from the other instrument was used"


def test_the_population_is_the_one_the_report_pairs():
    """Named once, so the two places that need it cannot drift apart."""
    from tnb.scoring import run as scoring

    systems = calibration.calibration_systems()
    assert "therapist" in systems, "the human-written note is what the ceiling is measured on"
    for system_id, _label in scoring.REFERENCE_MODELS.values():
        assert system_id in systems, f"{system_id} carries human ratings and is not counted"
    assert "kimi-k3" not in systems, "a leaderboard model has no human ratings to pair with"
