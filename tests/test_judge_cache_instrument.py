"""Two budgets of one judge no longer share a filename.

**This is the fix for a measurement that vanished the moment it was made.** The
answer cache used to key on (judge, prompt version, provider, system, session,
unit) and on nothing else, so raising the thinking budget from 128 to 256 and
re-asking wrote the new answers over the old ones. `scores/` is gitignored, so
nothing could be restored, and the published "budget 128 against 256"
comparison -- nineteen systems, mean +0.017 completeness -- can no longer be
re-derived by anyone: not from `results/rows.jsonl`, in any revision, and not
from the cache, where all 65 902 surviving `gemini-3.1-pro-preview` answers
carry a fingerprint of budget 256.

`Reinstrumented` was added after that and stops the accidental case. It cannot
stop the deliberate one, because re-measuring at a new budget is exactly what
`--reinstrument` is for. Separating the instruments on disk is what does.

The other half of the change matters as much and is tested here too: the
66 000 answers already on disk had to stay usable. They sit at the old
settings-free path, and re-asking them to gain a directory level would have
cost a day of quota to learn nothing.
"""

from __future__ import annotations

import json

from tnb import judge

FINGERPRINT_256 = {
    "model": "gemini-3.1-pro-preview",
    "thinking_budget": 256,
    "max_output_tokens": 288,
    "temperature": 0,
}
FINGERPRINT_128 = {**FINGERPRINT_256, "thinking_budget": 128}

WHERE = ("gemini-3.1-pro-preview", "tneval-rubric-v1", "vertex", "kimi-k3", "7", "subjective.x")


def _answer(fingerprint: dict, text: str) -> dict:
    return {"ok": True, "judge_fingerprint": fingerprint, "answer": text, "unit": WHERE[-1]}


def test_two_budgets_of_one_judge_do_not_share_a_file(tmp_path):
    """The incident, replayed: ask at 128, raise the budget, ask again."""
    at_128 = judge.cache_path(*WHERE, fingerprint=FINGERPRINT_128, root=tmp_path)
    at_256 = judge.cache_path(*WHERE, fingerprint=FINGERPRINT_256, root=tmp_path)

    assert at_128 != at_256, "a budget change still lands on the same filename"

    judge.write_cached(at_128, _answer(FINGERPRINT_128, "yes"))
    judge.write_cached(at_256, _answer(FINGERPRINT_256, "no"))

    assert judge.load_cached(at_128, FINGERPRINT_128)["answer"] == "yes"
    assert judge.load_cached(at_256, FINGERPRINT_256)["answer"] == "no"


def test_an_answer_written_before_the_change_is_still_used(tmp_path):
    """No re-asking to gain a directory level.

    The old path is read-only from here on: this asserts it is *read*, not that
    anything writes there again.
    """
    legacy = judge.cache_path(*WHERE, root=tmp_path)
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(json.dumps(_answer(FINGERPRINT_256, "kept")), encoding="utf-8")

    fresh = judge.cache_path(*WHERE, fingerprint=FINGERPRINT_256, root=tmp_path)
    assert not fresh.exists()

    found = judge.load_cached(fresh, FINGERPRINT_256)
    assert found is not None and found["answer"] == "kept"


def test_a_legacy_answer_from_another_instrument_is_still_refused(tmp_path):
    """The fallback reads an older path; it does not relax the fingerprint check.

    An answer asked at 128 must not be served to a run asking at 256 merely
    because it sits at the settings-free path.
    """
    legacy = judge.cache_path(*WHERE, root=tmp_path)
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(json.dumps(_answer(FINGERPRINT_128, "wrong budget")), encoding="utf-8")

    fresh = judge.cache_path(*WHERE, fingerprint=FINGERPRINT_256, root=tmp_path)
    assert judge.load_cached(fresh, FINGERPRINT_256) is None


def test_the_instrument_directory_is_recognised_again(tmp_path):
    """`legacy_path` has to find exactly the component `cache_path` added."""
    fresh = judge.cache_path(*WHERE, fingerprint=FINGERPRINT_256, root=tmp_path)
    assert judge.legacy_path(fresh) == judge.cache_path(*WHERE, root=tmp_path)
    # And an old path has no older path behind it.
    assert judge.legacy_path(judge.cache_path(*WHERE, root=tmp_path)) is None


def test_every_runner_asks_for_its_own_instrument():
    """Four scorers write to this cache. One that leaves the fingerprint off
    writes to the shared path again and re-opens the hole for its own track."""
    import ast

    from tnb.config import REPO_ROOT

    missing = []
    for name in ("czech_run", "pdsqi_run", "run", "icare_run"):
        source = (REPO_ROOT / "src" / "tnb" / "scoring" / f"{name}.py").read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.Call):
                continue
            if getattr(node.func, "attr", None) != "cache_path":
                continue
            if not any(word.arg == "fingerprint" for word in node.keywords):
                missing.append(name)
    assert not missing, f"cache_path called without a fingerprint in: {sorted(set(missing))}"
