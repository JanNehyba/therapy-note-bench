"""An answer from one judge instrument may not silently replace another's.

Offline. Every record here is written in this file.

The incident: a scoring run started without `--thinking-budget` took the default
256 where the stored answers had been asked at 2048. `load_cached` correctly
refused all 1 272 of them, because a different budget is a different instrument
-- that is why `judge_settings` is one of `results.COMPARABILITY_KEYS`. The run
then re-asked every question and `write_cached` overwrote 943 good answers with
answers nobody wanted. `scores/` is gitignored, so there was nothing to restore.
"""

from __future__ import annotations

import json

import pytest

from tnb import judge

AT_2048 = {"model": "a-judge", "thinking_budget": 2048, "max_output_tokens": 2080}
AT_256 = {"model": "a-judge", "thinking_budget": 256, "max_output_tokens": 288}


def _record(fingerprint: dict, answer: str) -> dict:
    return {
        "judge_model": fingerprint["model"],
        "judge_prompt_version": "some-rubric-v1",
        "judge_fingerprint": fingerprint,
        "answer": answer,
        "ok": True,
    }


def test_a_different_budget_cannot_overwrite_an_answer(tmp_path):
    """The exact shape of the incident, in one call."""
    path = tmp_path / "answer.json"
    judge.write_cached(path, _record(AT_2048, "ano"))

    with pytest.raises(judge.Reinstrumented) as raised:
        judge.write_cached(path, _record(AT_256, "ne"))

    # The message has to carry both fingerprints, because the question a reader
    # asks next is "which one is on disk and which one am I asking with".
    assert "2048" in str(raised.value) and "256" in str(raised.value)
    assert json.loads(path.read_text(encoding="utf-8"))["answer"] == "ano"


def test_the_same_instrument_answering_again_is_free(tmp_path):
    """Re-asking is ordinary: `--force` does it, and so does the next run after
    a truncated answer, which `load_cached` refuses to treat as cached."""
    path = tmp_path / "answer.json"
    judge.write_cached(path, _record(AT_2048, "ano"))
    judge.write_cached(path, _record(AT_2048, "ne"))

    assert json.loads(path.read_text(encoding="utf-8"))["answer"] == "ne"


def test_re_instrumenting_on_purpose_is_still_possible(tmp_path):
    """Measuring at a new budget is a real thing to want. It starts a new table
    by the project's own rules, so it has to be said out loud -- but saying it
    has to work, or the guard would be a wall rather than a check."""
    path = tmp_path / "answer.json"
    judge.write_cached(path, _record(AT_2048, "ano"))
    judge.write_cached(path, _record(AT_256, "ne"), allow_reinstrument=True)

    assert json.loads(path.read_text(encoding="utf-8"))["answer"] == "ne"


def test_a_record_with_no_fingerprint_is_not_guessed_at(tmp_path):
    """Answers written before fingerprints were recorded exist. Refusing them
    would block a re-ask over data the guard cannot judge, and `load_cached`
    already treats a missing digest as unknown rather than as wrong."""
    path = tmp_path / "answer.json"
    path.write_text(json.dumps({"answer": "ano", "ok": True}), encoding="utf-8")

    judge.write_cached(path, _record(AT_2048, "ne"))

    assert json.loads(path.read_text(encoding="utf-8"))["answer"] == "ne"


def test_every_runner_passes_the_escape_hatch():
    """Every scorer writes to this cache. A guard all but one route around is
    not a guard, and the one left out would be found by an incident rather than
    by a test.

    Found rather than listed. A named list was four entries and is now three;
    the next scorer added would not have been on it, and a guard that silently
    stops covering the newest writer is the failure this test is about.
    """
    import ast
    from pathlib import Path

    from tnb.config import REPO_ROOT

    runners = sorted((REPO_ROOT / "src" / "tnb" / "scoring").glob("*run.py"))
    assert len(runners) >= 3, f"only {len(runners)} scorer(s) found -- the glob stopped matching"

    missing = []
    for path in runners:
        source = path.read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.Call):
                continue
            target = getattr(node.func, "attr", None)
            if target != "write_cached":
                continue
            if not any(word.arg == "allow_reinstrument" for word in node.keywords):
                missing.append(path.stem)
    assert not missing, f"write_cached called without the guard's escape hatch in: {missing}"
    assert Path(REPO_ROOT / "src" / "tnb" / "judge.py").exists()
