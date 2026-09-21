"""The Czech translator is an instrument, and this is what holds it to that.

Ten Czech translations exist in this project with no record of the model, the
prompt or the settings behind them, so a difference measured between the
languages could be a difference between translators (audit A11). Decision D4
supersedes them and requires a recorded instrument, chosen by a measured check.

Pinned here: nothing translates before an instrument is recorded; an instrument
is recorded only for a model the check measured, never for a judge of the
pilot, and never on a back-translator that is the candidate itself; a
conversation whose turns do not map one for one is a failure and not a pair;
the round trip is reported with the number of turns it could compare; unmarked
review turns are never counted as agreement; and no transcript text reaches a
tracked record.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

import translate_annomi_cs as tool  # noqa: E402

EN = [
    {"speaker": "therapist", "text": "What brings you here today?"},
    {"speaker": "client", "text": "I have been drinking more than I want to."},
    {"speaker": "therapist", "text": "More than you want to. Say more about that."},
    {"speaker": "client", "text": "Every evening, and I promised myself I would stop."},
]
CS = {
    "What brings you here today?": "Co vas sem dnes privadi?",
    "I have been drinking more than I want to.": "Piju vic, nez bych chtel.",
    "More than you want to. Say more about that.": "Vic, nez byste chtel. Povezte mi o tom vic.",
    "Every evening, and I promised myself I would stop.": "Kazdy vecer, a slibil jsem si, "
    "ze prestanu.",
}
BACK = {v: k for k, v in CS.items()}


@pytest.fixture
def source(tmp_path) -> Path:
    path = tmp_path / "conversation-1.json"
    path.write_text(json.dumps({"turns": EN}), encoding="utf-8")
    return path


def _turns() -> list[tool.Turn]:
    return [tool.Turn(i, t["speaker"], t["text"]) for i, t in enumerate(EN, start=1)]


def _answer(prompt: str, table: dict, *, drop: int | None = None, mangle=None) -> str:
    """A translator that looks up each line, so a test can break one thing."""
    out = []
    for turn in tool.parse_numbered(prompt):
        if turn.index == drop:
            continue
        text = table.get(turn.text, turn.text)
        speaker = turn.speaker
        if mangle and turn.index == mangle[0]:
            text, speaker = mangle[1], mangle[2]
        out.append(f"{turn.index} | {speaker} | {text}")
    return "Sure, here it is:\n" + "\n".join(out)


def good(model: str, prompt: str) -> str:
    table = CS if "| therapist | What brings" in prompt else BACK
    return _answer(prompt, table)


# --- the metric --------------------------------------------------------------


def test_the_round_trip_metric_counts_characters_not_words():
    assert tool.chrf("identical text", "identical text") == 1.0
    assert tool.chrf("", "anything") == 0.0
    inflected = tool.chrf("terapeutovi", "terapeut")
    unrelated = tool.chrf("uplne jine slovo", "terapeut")
    assert inflected > unrelated, "an inflected form must not read as a different word"


def test_an_untranslated_turn_is_named_rather_than_scored():
    source = _turns()
    same = [tool.Turn(t.index, t.speaker, t.text) for t in source]
    check = tool.check_structure(source, same)
    assert not check.ok
    assert check.untranslated == [1, 2, 3, 4]
    assert "untranslated" in " ".join(check.problems)


# --- structure ---------------------------------------------------------------


def test_a_translation_that_loses_a_turn_is_a_failure_not_a_repair():
    source = _turns()
    result = tool.parse_numbered(_answer(tool.numbered(source), CS, drop=3))
    check = tool.check_structure(source, result)
    assert not check.ok and check.turns_out == 3
    assert any("turn count" in p for p in check.problems)
    assert any("turn 3 is missing" in p for p in check.problems)


def test_a_translation_that_changes_a_speaker_is_a_failure():
    source = _turns()
    result = tool.parse_numbered(
        _answer(tool.numbered(source), CS, mangle=(2, CS[EN[1]["text"]], "therapist"))
    )
    check = tool.check_structure(source, result)
    assert not check.ok and any("changed speaker" in p for p in check.problems)


def test_prose_around_the_lines_is_dropped_and_the_turns_survive():
    source = _turns()
    result = tool.parse_numbered(good("m", tool.numbered(source)))
    assert [t.index for t in result] == [1, 2, 3, 4]
    assert tool.check_structure(source, result).ok


def test_the_round_trip_says_how_many_turns_it_could_compare():
    source = _turns()
    partial = [tool.Turn(1, "therapist", "What brings you here today?")]
    trip = tool.round_trip(source, partial)
    assert trip["compared_turns"] == 1 and trip["of_turns"] == 4
    assert trip["mean_chrf"] == 1.0
    assert tool.round_trip(source, [])["mean_chrf"] is None


# --- selecting and recording --------------------------------------------------


def _check(tmp_path, source) -> dict:
    args = tool.argparse.Namespace(
        sample=source,
        provider="einfra",
        candidates=["model-a", "model-b"],
        back_translator="model-back",
        workspace=tmp_path / "work",
    )
    return tool.cmd_select(args, call=good)


def test_the_check_measures_every_candidate_and_decides_nothing(tmp_path, source):
    check = _check(tmp_path, source)
    assert [row["model"] for row in check["candidates"]] == ["model-a", "model-b"]
    for row in check["candidates"]:
        assert row["structure"]["ok"]
        assert row["round_trip"]["compared_turns"] == 4
    assert "chosen" not in json.dumps(check) and "winner" not in json.dumps(check)
    assert check["metric"]["name"] == "chrF"
    assert "not a measurement of it" in check["metric"]["means"]


def test_a_structural_failure_keeps_the_text_that_failed_under_local(tmp_path, source):
    """glm-5.3 "changed every speaker" in the first live check and nothing kept
    what it had written, so the failure could be named and not read."""

    def call(model: str, prompt: str) -> str:
        if model == "model-a":
            return _answer(prompt, CS).replace("| therapist |", "| Terapeut |")
        return good(model, prompt)

    args = tool.argparse.Namespace(
        sample=source,
        provider="einfra",
        candidates=["model-a", "model-b"],
        back_translator="model-back",
        workspace=tmp_path / "work",
    )
    check = tool.cmd_select(args, call=call)
    rows = {row["model"]: row for row in check["candidates"]}
    assert not rows["model-a"]["structure"]["ok"]
    kept = tmp_path / "work" / "selection-model-a.failed.txt"
    assert kept.exists() and "Terapeut" in kept.read_text(encoding="utf-8")
    assert not (tmp_path / "work" / "selection-model-b.failed.txt").exists()
    with pytest.raises(SystemExit, match="only be written under local"):
        tool.write_raw(tool.REPO / "docs" / "leak.txt", "x")


def test_a_candidate_may_not_be_its_own_back_translator(tmp_path, source):
    args = tool.argparse.Namespace(
        sample=source,
        provider="einfra",
        candidates=["model-a"],
        back_translator="model-a",
        workspace=tmp_path / "work",
    )
    with pytest.raises(SystemExit, match="both a candidate and the back-translator"):
        tool.cmd_select(args, call=good)


def _record(check, **kwargs):
    payload = {
        "provider": "einfra",
        "model": "model-a",
        "settings": {"temperature": 0.0},
        "check": check,
        "check_digest": tool.digest(check),
        "judges": ["gemini-3.1-pro-preview", "gpt-5.6-terra"],
        "reason": "highest round trip of the measured candidates with no structural failure",
    }
    return tool.instrument_record(**{**payload, **kwargs})


def test_an_instrument_is_recorded_only_for_a_measured_model(tmp_path, source):
    check = _check(tmp_path, source)
    record = _record(check)
    assert record["model"] == "model-a"
    assert record["prompt_digest"] == tool.prompt_digest("en->cs")
    assert record["back_translation_check"]["digest"] == tool.digest(check)
    assert record["back_translation_check"]["measurement"]["model"] == "model-a"
    assert record["status"] == "recorded_before_use"
    assert "historical" in record["supersedes"]
    with pytest.raises(SystemExit, match="was not measured"):
        _record(check, model="model-never-tried")


def test_a_candidate_that_fails_is_a_row_of_the_check_not_the_end_of_it(tmp_path, source):
    """The first candidate on e-INFRA truncated at the note budget and the run stopped
    before the second was asked; a check that measures one candidate measures none."""

    def call(model: str, prompt: str) -> str:
        if model == "model-a":
            raise tool.ModelFailure("model-a returned no usable answer: truncated at max_tokens")
        if model == "model-back" and "model-c" in prompt:
            raise tool.ModelFailure("model-back returned no usable answer: empty")
        return good(model, prompt)

    args = tool.argparse.Namespace(
        sample=source,
        provider="einfra",
        candidates=["model-a", "model-b", "model-c"],
        back_translator="model-back",
        workspace=tmp_path / "work",
    )
    check = tool.cmd_select(args, call=call, settings={"max_tokens": 16384, "temperature": 0.0})
    rows = {row["model"]: row for row in check["candidates"]}
    assert set(rows) == {"model-a", "model-b", "model-c"}
    assert rows["model-a"]["failed"]["stage"] == "forward" and rows["model-a"]["round_trip"] is None
    assert rows["model-b"]["round_trip"]["compared_turns"] == 4 and "failed" not in rows["model-b"]
    assert check["settings"]["max_tokens"] == 16384
    with pytest.raises(SystemExit, match="measurement failed"):
        _record(check, model="model-a")
    record = _record(check, model="model-b", settings=check["settings"])
    assert record["settings"]["max_tokens"] == 16384


def test_a_judge_of_this_pilot_may_not_translate_for_it(tmp_path, source):
    check = _check(tmp_path, source)
    with pytest.raises(SystemExit, match="may not also be its translator"):
        _record(check, model="model-a", judges=["model-a"])


def test_the_back_translator_may_not_be_recorded_as_the_translator(tmp_path, source):
    check = _check(tmp_path, source)
    check["candidates"].append({"model": "model-back", "structure": {}, "round_trip": {}})
    with pytest.raises(SystemExit, match="cannot check its own translation"):
        _record(check, model="model-back")


# --- translating --------------------------------------------------------------


def test_nothing_translates_before_an_instrument_is_recorded(tmp_path):
    with pytest.raises(SystemExit, match="No translation instrument is recorded"):
        tool.load_instrument(tmp_path / "absent.json")


def test_a_run_records_the_instrument_and_separates_failures(tmp_path, source):
    instrument = tmp_path / "instrument.json"
    instrument.write_text(
        json.dumps(
            {
                "provider": "einfra",
                "model": "model-a",
                "prompt_digest": tool.prompt_digest("en->cs"),
            }
        ),
        encoding="utf-8",
    )
    broken = tmp_path / "conversation-2.json"
    broken.write_text(json.dumps({"turns": EN}), encoding="utf-8")

    def call(prompt: str) -> str:
        # The second conversation comes back a turn short; the first is fine.
        call.seen += 1
        return _answer(prompt, CS, drop=2 if call.seen == 2 else None)

    call.seen = 0
    args = tool.argparse.Namespace(
        conversations=[source, broken],
        instrument=instrument,
        workspace=tmp_path / "work",
    )
    record = tool.cmd_translate(args, call=call)
    assert record["usable"] == ["conversation-1"]
    assert record["failed"] == ["conversation-2"]
    failed = next(r for r in record["conversations"] if r["conversation"] == "conversation-2")
    assert failed["translation_digest"] is None
    assert not (tmp_path / "work" / "conversation-2.cs.json").exists()
    assert (tmp_path / "work" / "conversation-1.cs.json").exists()
    assert record["model"] == "model-a"

    # A call that returns nothing usable is a failed conversation, not a crash.
    dead = tmp_path / "conversation-3.json"
    dead.write_text(json.dumps({"turns": EN}), encoding="utf-8")

    def refuses(prompt: str) -> str:
        raise tool.ModelFailure("model-a returned no usable answer: truncated")

    args.conversations = [dead]
    record = tool.cmd_translate(args, call=refuses)
    assert record["failed"] == ["conversation-3"] and record["usable"] == []
    assert "truncated" in record["conversations"][0]["check"]["problems"][0]
    assert not (tmp_path / "work" / "conversation-3.cs.json").exists()


def test_a_translation_is_never_written_where_this_repository_publishes(tmp_path):
    """The corpus rule as a rule about commits: inside the checkout, only the
    ignored `local/` may hold transcript text."""
    for escape in ("docs/leak.json", "research/gen2/translation/leak.json", "leak.json"):
        with pytest.raises(SystemExit, match="only be written under local"):
            tool.write_local(REPO / escape, _turns(), None)
    tool.write_local(REPO / "local" / "gen2-translation-test" / "ok.json", _turns(), None)
    (REPO / "local" / "gen2-translation-test" / "ok.json").unlink()
    (REPO / "local" / "gen2-translation-test").rmdir()


def test_no_tracked_record_carries_transcript_text(tmp_path, source):
    check = _check(tmp_path, source)
    record = _record(check)
    for blob in (json.dumps(check, ensure_ascii=False), json.dumps(record, ensure_ascii=False)):
        for turn in EN:
            assert turn["text"] not in blob
        for czech in CS.values():
            assert czech not in blob


# --- the human review ---------------------------------------------------------


def test_the_review_sheet_shows_the_way_there_and_back():
    source = _turns()
    cs = tool.parse_numbered(_answer(tool.numbered(source), CS))
    en = tool.parse_numbered(_answer(tool.numbered(cs), BACK))
    rows = tool.review_rows(source, cs, en, every=2)
    assert [row["turn"] for row in rows] == [1, 3]
    assert rows[0]["original"] == EN[0]["text"]
    assert rows[0]["translation"] == CS[EN[0]["text"]]
    assert rows[0]["back_translation"] == EN[0]["text"]
    assert rows[0]["verdict"] == ""


def test_an_unmarked_review_turn_is_not_agreement():
    sheet = [
        {"turn": 1, "original": "a", "translation": "b", "verdict": "same_meaning"},
        {"turn": 3, "original": "c", "translation": "d", "verdict": ""},
    ]
    review = tool.import_review(sheet, reviewer="investigator", conversation="conversation-1")
    assert review["turns_offered"] == 2 and review["turns_marked"] == 1
    assert review["verdicts"]["same_meaning"] == 1
    assert sum(review["verdicts"].values()) == 1
    assert "never counted as agreement" in review["rule"]
    assert set(review["marked_turns"]) == {"1"}


def test_a_pair_needs_a_verified_structure_and_a_human_who_read_it():
    """Audit A11: two files named alike are not an EN/CS pair."""
    translations = {
        "instrument_digest": "abc",
        "model": "model-a",
        "conversations": [
            {
                "conversation": "reviewed",
                "source_digest": "s1",
                "translation_digest": "t1",
                "check": {"ok": True},
            },
            {
                "conversation": "unreviewed",
                "source_digest": "s2",
                "translation_digest": "t2",
                "check": {"ok": True},
            },
            {
                "conversation": "broken",
                "source_digest": "s3",
                "translation_digest": None,
                "check": {"ok": False},
            },
            {
                "conversation": "sheet-came-back-blank",
                "source_digest": "s4",
                "translation_digest": "t4",
                "check": {"ok": True},
            },
        ],
    }
    reviews = [
        {
            "conversation": "reviewed",
            "reviewer": "investigator",
            "turns_marked": 6,
            "turns_offered": 8,
            "verdicts": {"same_meaning": 5, "shifted": 1},
        },
        {
            "conversation": "sheet-came-back-blank",
            "reviewer": "investigator",
            "turns_marked": 0,
            "turns_offered": 8,
            "verdicts": {},
        },
    ]
    groups = tool.translation_groups(translations, reviews)
    assert set(groups["established"]) == {"reviewed"}
    assert groups["established"]["reviewed"]["translation_group"] == "translation:reviewed"
    assert groups["established"]["reviewed"]["review"]["verdicts"]["shifted"] == 1
    withheld = {row["conversation"]: row["reason"] for row in groups["not_established"]}
    assert set(withheld) == {"unreviewed", "broken", "sheet-came-back-blank"}
    assert "one for one" in withheld["broken"]
    assert "no human meaning review" in withheld["unreviewed"]
    assert "unmarked" in withheld["sheet-came-back-blank"]


def test_a_reviewed_pair_keeps_the_shifted_meaning_it_was_given():
    """A verdict of shifted meaning is a finding about the pair, not a reason
    to drop it silently: the contrast has to be able to report it."""
    translations = {
        "instrument_digest": "abc",
        "model": "model-a",
        "conversations": [
            {
                "conversation": "c1",
                "source_digest": "s",
                "translation_digest": "t",
                "check": {"ok": True},
            }
        ],
    }
    reviews = [
        {
            "conversation": "c1",
            "reviewer": "investigator",
            "turns_marked": 4,
            "turns_offered": 4,
            "verdicts": {"same_meaning": 1, "shifted": 2, "lost": 1},
        }
    ]
    groups = tool.translation_groups(translations, reviews)
    assert groups["established"]["c1"]["review"]["verdicts"]["lost"] == 1
    assert "hid them" in groups["note"]


def test_an_invented_verdict_is_refused():
    sheet = [{"turn": 1, "original": "a", "translation": "b", "verdict": "looks_fine"}]
    with pytest.raises(SystemExit, match="Unknown verdict"):
        tool.import_review(sheet, reviewer="investigator", conversation="conversation-1")
