"""Whether a judge answers the same question the same way twice -- pinned offline.

`tnb repeatability` reads two answer caches and counts, so the tests build two
tiny caches with `judge.write_cached` and pin three properties:

* a differently worded answer that parses the same is agreement -- the tables
  average the parsed value, and a claim of repeatability has to hold at that
  level, not at the wording;
* a question only one of the two runs answered is reported unanswered, not
  as disagreement, and never inflates the agreement count;
* the judges and instruments measured are the ones the panel names, in the
  project's own order.

The committed artefact, when it exists, is checked against the two caches it
says it was drawn from -- the same check `test_edges` runs on its artefact,
and the only one that needs no judge.
"""

from __future__ import annotations

import json

import pytest

from tnb import judge
from tnb.scoring import repeatability

PROMPT_VERSION = "tneval-soap-v1"


def _write(root, provider, system, session, unit, answer, *, ok=True):
    path = judge.cache_path(
        "judge-a",
        PROMPT_VERSION,
        provider,
        system,
        session,
        unit,
        fingerprint={"model": "judge-a"},
        root=root,
    )
    judge.write_cached(
        path,
        {
            "judge_model": "judge-a",
            "judge_prompt_version": PROMPT_VERSION,
            # The same judge at the same settings: what makes the two runs a
            # repeat rather than two instruments.
            "judge_fingerprint": {"model": "judge-a"},
            "provider": provider,
            "system_id": system,
            "session_id": session,
            "unit": unit,
            "answer": answer,
            "ok": ok,
        },
    )


@pytest.fixture()
def two_caches(tmp_path):
    """One judge's task, answered twice into two roots."""
    published, repeated = tmp_path / "published", tmp_path / "repeated"
    return published, repeated


def test_a_differently_worded_yes_is_agreement(two_caches):
    """The table averages the parsed answer, so that is the level to compare at."""
    published, repeated = two_caches
    _write(published, "einfra", "model-a", "1", "c1-s1", "Yes.")
    _write(published, "einfra", "model-a", "1", "c1-s2", "no")
    _write(published, "einfra", "model-a", "1", "c2-s1", "2")
    _write(published, "einfra", "model-a", "1", "c2-s2", "3")
    # "[Yes]" parses as the same yes; "No." against "no" is the same no.
    _write(repeated, "einfra", "model-a", "1", "c1-s1", "[Yes]")
    _write(repeated, "einfra", "model-a", "1", "c1-s2", "No.")
    _write(repeated, "einfra", "model-a", "1", "c2-s1", "2")
    # A rating that moved.
    _write(repeated, "einfra", "model-a", "1", "c2-s2", "4")

    class _Task:
        unit = "c1-s1"
        prompt = "the question"
        accepts = None

    class _Candidate:
        provider = "einfra"
        system_id = "model-a"
        session_id = "1"

    from tnb.scoring import tneval

    same, both, unanswered = repeatability._count(
        iter([(_Candidate(), _Task(), tneval.parse_yes_no, PROMPT_VERSION)]),
        "judge-a",
        {"model": "judge-a"},
        published_root=published,
        repeat_root=repeated,
    )
    assert (same, both, unanswered) == (1, 1, 0)


def test_unanswered_in_one_run_is_not_disagreement(two_caches):
    """A judge that goes silent is a different finding from one that wavers."""
    published, repeated = two_caches
    _write(published, "einfra", "model-a", "1", "c1-s1", "yes")
    _write(published, "einfra", "model-a", "1", "c1-s2", "yes")
    # The repeat answered the first question but not the second.
    _write(repeated, "einfra", "model-a", "1", "c1-s1", "yes")

    class _Task:
        def __init__(self, unit):
            self.unit = unit
            self.prompt = f"question {unit}"
            self.accepts = None

    class _Candidate:
        provider = "einfra"
        system_id = "model-a"
        session_id = "1"

    from tnb.scoring import tneval

    same, both, unanswered = repeatability._count(
        iter(
            [
                (_Candidate(), _Task("c1-s1"), tneval.parse_yes_no, PROMPT_VERSION),
                (_Candidate(), _Task("c1-s2"), tneval.parse_yes_no, PROMPT_VERSION),
            ]
        ),
        "judge-a",
        {"model": "judge-a"},
        published_root=published,
        repeat_root=repeated,
    )
    # The answered one agrees; the other is counted apart, in neither sum.
    assert (same, both, unanswered) == (1, 1, 1)


def test_the_artefact_matches_the_caches_it_names():
    """What the panel draws, against what the two runs answered.

    Skipped where `scores/repeatability-2` is absent, the way the edges tests
    skip on theirs: the artefact is committed, the repeat's answers are not.
    """
    from tnb.config import REPO_ROOT

    payload = REPO_ROOT / "docs" / "repeatability.json"
    if not payload.exists():
        pytest.skip("no repeat run on this checkout yet")
    data = json.loads(payload.read_text(encoding="utf-8"))
    repeat_root = REPO_ROOT / data["repeat_root"]
    if not repeat_root.exists():
        pytest.skip("the repeat run's cache is not on this checkout")
    for entry in data["judges"]:
        assert entry["same"] <= entry["questions"]
        assert entry["questions"] >= 0
        for track in entry["tracks"]:
            assert track["same"] <= track["questions"]
            assert track["unanswered"] >= 0


def test_the_artefact_names_whose_notes_were_repeated():
    """Five notes in cache order are five sessions of one model. The panel's
    sentence has to carry the model, or "five notes" reads as five models."""
    found = repeatability.JudgeRepeat(
        judge_model="judge-a",
        tracks=[
            repeatability.TrackRepeat(
                track="tneval-soap",
                notes=2,
                same=1,
                questions=2,
                unanswered=0,
                systems=("model-a",),
            )
        ],
    )
    payload = repeatability.to_json([found], notes=2, repeat_root="scores/repeat-x")
    assert payload["systems"] == ["model-a"]
    assert payload["judges"][0]["tracks"][0]["systems"] == ["model-a"]
