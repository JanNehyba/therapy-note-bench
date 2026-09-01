"""Two budgets of one judge no longer share a filename.

**This is the fix for a measurement that vanished the moment it was made.** The
answer cache used to key on (judge, prompt version, provider, system, session,
unit) and on nothing else, so raising the thinking budget from 128 to 256 and
re-asking wrote the new answers over the old ones. `scores/` is gitignored, so
nothing could be restored, and the published "budget 128 against 256"
comparison -- nineteen systems, mean +0.017 completeness -- can no longer be
re-derived by anyone: not from `results/rows.jsonl`, in any revision, and not
from the cache, where all 51 000 surviving `gemini-3.1-pro-preview` answers to
the SOAP rubric carry a fingerprint of budget 256.

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
from collections import Counter

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


#: Callers allowed to build a settings-free path, each for a stated reason.
#: `calibration` walks the directory itself rather than reading one answer, and
#: `backfill_digests` is a one-shot migration over the pre-2026-08-31 layout,
#: which is the only layout it is meant to see.
MAY_OMIT_THE_FINGERPRINT = {
    "src/tnb/scoring/calibration.py": "takes the parent directory and reads every instrument in it",
    "tools/backfill_digests.py": "a migration over records written before instruments existed",
}


def _calls_without_a_fingerprint(source: str) -> int:
    """`judge.cache_path(...)` calls that name no instrument.

    Only this cache's function. A tool with a `cache_path` of its
    own for the coder's answers, which has nothing to do with the judge's, and
    matching on the bare name alone reported it.
    """
    import ast

    try:
        tree = ast.parse(source)
    except SyntaxError:
        # A file caught half-written. `ruff` and every import in the suite
        # already fail loudly on that; this check has nothing to add and
        # should not turn red for somebody else's unsaved buffer.
        return 0
    imported = any(
        isinstance(node, ast.ImportFrom)
        and (node.module or "").endswith("judge")
        and any(alias.name == "cache_path" for alias in node.names)
        for node in ast.walk(tree)
    )

    found = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            if node.func.attr != "cache_path":
                continue
        elif isinstance(node.func, ast.Name) and imported:
            if node.func.id != "cache_path":
                continue
        else:
            continue
        if not any(word.arg == "fingerprint" for word in node.keywords):
            found += 1
    return found


def test_every_caller_asks_for_its_own_instrument():
    """Writers AND readers. A reader that leaves the fingerprint off is worse.

    The writers were checked from the first version of this test, because one
    that forgets writes to the shared path again and re-opens the hole. The
    readers were not, and two of them were left looking under the settings-free
    path while the scorer had moved to the instrument's. `legacy_path` only
    strips an instrument component, so
    there is no lookup in that direction: they would have found nothing, and
    the partial case fails quietly rather than loudly.
    """
    from tnb.config import REPO_ROOT

    missing = {}
    for where in ("src/tnb", "tools"):
        for path in sorted((REPO_ROOT / where).rglob("*.py")):
            relative = path.relative_to(REPO_ROOT).as_posix()
            if relative in MAY_OMIT_THE_FINGERPRINT:
                continue
            count = _calls_without_a_fingerprint(path.read_text(encoding="utf-8"))
            if count:
                missing[relative] = count
    assert not missing, (
        "cache_path called without a fingerprint, so this code reads or writes "
        f"the settings-free path while the scorers use the instrument's: {missing}.\n"
        "Pass `fingerprint=config.fingerprint()`, or add the file to "
        "MAY_OMIT_THE_FINGERPRINT with the reason it is exempt."
    )


def test_the_exemptions_are_still_the_files_they_name():
    """An allow-list nobody rereads becomes a list of what slipped through."""
    from tnb.config import REPO_ROOT

    for relative in MAY_OMIT_THE_FINGERPRINT:
        path = REPO_ROOT / relative
        assert path.exists(), f"{relative} is exempted from the fingerprint rule and does not exist"
        assert _calls_without_a_fingerprint(path.read_text(encoding="utf-8")), (
            f"{relative} no longer calls cache_path without a fingerprint; "
            "drop it from MAY_OMIT_THE_FINGERPRINT rather than leaving a dead exemption"
        )


def test_the_superseded_copy_does_not_win_the_saturation_panel(tmp_path):
    """A re-ask leaves two answers for one slot, and the newer one has to win.

    The instrument directory is additive: the fresh answer goes under it and
    the answer it replaced stays where it was. Both carry the same fingerprint
    -- the settings did not change, the note did -- so grouping by fingerprint
    cannot tell them apart, and `rglob` reached the superseded copy last for
    every provider sorting before `i-`. The published saturation panel then
    described a note that no longer exists.
    """
    from tnb import judge
    from tnb.scoring import saturation, tneval

    where = (judge.DEFAULT_MODEL, tneval.JUDGE_PROMPT_VERSION, "einfra", "kimi-k3", "42")
    unit = "subjective.rubric_completeness.subjective-symptoms"
    fingerprint = {"thinking_budget": 256}

    for path, answer in (
        (judge.cache_path(*where, unit, root=tmp_path), "Yes"),
        (judge.cache_path(*where, unit, fingerprint=fingerprint, root=tmp_path), "No"),
    ):
        judge.write_cached(
            path,
            {
                "ok": True,
                "provider": "einfra",
                "system_id": "kimi-k3",
                "session_id": "42",
                "unit": unit,
                "answer": answer,
                "judge_fingerprint": fingerprint,
            },
        )

    answers = saturation.load_answers(root=tmp_path)
    assert answers[("kimi-k3", "42")][unit] == "No", (
        "the settings-free copy is the judgement of the note that was replaced; "
        "the instrument's copy is the current one and has to be the one read"
    )


def test_one_report_never_averages_two_instruments(tmp_path):
    """The calibration panel picks an instrument before it makes a single pair.

    It used to read the settings-free directory and every instrument directory
    into one dict, so a question answered at two budgets resolved to whichever
    hash sorted last. Different questions about one note could then come from
    different instruments, and `judge_settings` -- published in
    `docs/judges.json` beside the agreement figures -- named whichever settings
    were commonest on disk, which could be the ones that produced none of the
    answers used.
    """
    from tnb import judge
    from tnb.scoring import calibration, tneval

    at_128 = {"thinking_budget": 128}
    at_256 = {"thinking_budget": 256}
    where = (judge.DEFAULT_MODEL, tneval.JUDGE_PROMPT_VERSION, "tneval", "therapist", "9")

    # Three questions answered at 128, one of them re-asked at 256: the shape of
    # a re-scoring run interrupted part way through.
    for unit, fingerprint, answer in (
        ("subjective.a", at_128, "Yes"),
        ("subjective.b", at_128, "Yes"),
        ("subjective.c", at_128, "Yes"),
        ("subjective.a", at_256, "No"),
    ):
        judge.write_cached(
            judge.cache_path(*where, unit, fingerprint=fingerprint, root=tmp_path),
            {
                "ok": True,
                "provider": "tneval",
                "system_id": "therapist",
                "session_id": "9",
                "unit": unit,
                "answer": answer,
                "judge_fingerprint": fingerprint,
            },
        )

    instrument = calibration.dominant_instrument(judge.DEFAULT_MODEL, root=tmp_path)
    assert instrument == json.dumps(at_128, sort_keys=True), "the larger set has to win"

    seen: Counter = Counter()
    answers = calibration._answers_for(
        "9", "therapist", judge.DEFAULT_MODEL, root=tmp_path, seen=seen, instrument=instrument
    )
    assert set(answers.values()) == {"Yes"}, "an answer from the other instrument was used"
    assert sum(seen.values()) == 4, "`seen` still records what was on disk, used or not"
    assert calibration._the_settings_used(instrument, seen) == at_128, (
        "the published settings must be the ones the figures came from"
    )
