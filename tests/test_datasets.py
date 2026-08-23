"""Dataset adapters, exercised offline against slices of the real corpora.

Fixtures were cut from the actual upstream files, so their quirks are real
quirks: `annomi_sample.csv` includes a transcript annotated by all ten AnnoMI
annotators, and `ihope_sample.json` includes a session with an empty gold note.
No test here reaches the network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tnb.datasets import ihope, tneval
from tnb.datasets.base import Session, Turn

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def offline_tneval(monkeypatch):
    """Serve AnnoMI and the TN-Eval notes from fixtures instead of GitHub."""

    def fake_fetch(url: str, name: str, **_):
        if name == "AnnoMI-full.csv":
            return FIXTURES / "annomi_sample.csv"
        if name.startswith("tneval_notes_part1."):
            return FIXTURES / "tneval_notes_sample.json"
        # Parts 2-10 are not in the fixture; serve an empty list.
        empty = FIXTURES / "_empty.json"
        empty.write_text("[]", encoding="utf-8")
        return empty

    monkeypatch.setattr(tneval, "fetch", fake_fetch)


@pytest.fixture
def offline_ihope(monkeypatch):
    monkeypatch.setattr(ihope, "fetch", lambda url, name, **_: FIXTURES / "ihope_sample.json")


# --- TN-Eval ---------------------------------------------------------------


def test_tneval_loads_the_conversations_the_notes_name(offline_tneval):
    sessions = tneval.load()
    assert [s.id for s in sessions] == ["0", "7"]
    assert all(s.source == "tneval" for s in sessions)


def test_tneval_collapses_repeated_annotator_rows(offline_tneval):
    """AnnoMI-full has one row per (utterance, annotator). Transcript 7 is rated
    by all ten, so without deduplication its transcript would repeat every line
    ten times and the model would score a very different conversation."""
    raw_rows = FIXTURES.joinpath("annomi_sample.csv").read_text(encoding="utf-8")
    assert raw_rows.count(",7,") >= 10, "fixture must keep the repeated annotator rows"

    sessions = {s.id: s for s in tneval.load()}
    # Five utterances, each recorded by ten annotators, must yield five turns.
    # Deduplication is keyed on utterance id, not on text: repeated text is
    # legitimate here, because the client really does say "Yeah." twice.
    assert len(sessions["7"].turns) == 5


def test_tneval_keeps_turns_in_transcript_order(offline_tneval):
    turns = {s.id: s.turns for s in tneval.load()}["7"]
    assert turns[0].speaker == "therapist"
    assert turns[1].speaker == "client"


def test_tneval_carries_the_human_calibration_anchor(offline_tneval):
    """The human ratings are the reason a judge can be checked against a person.
    If they stop arriving, calibration silently becomes impossible."""
    session = tneval.load()[0]
    assert set(session.meta["human_note"]) == {"subjective", "objective", "assessment", "plan"}
    assert "metrics_human" in session.meta["human_ratings"]
    assert session.meta["model_notes"]


def test_tneval_is_reference_free(offline_tneval):
    """The rubric protocol scores against the transcript, not a gold note."""
    assert all(session.reference is None for session in tneval.load())


def test_tneval_refuses_to_pair_a_note_with_a_missing_transcript(monkeypatch):
    """Silently dropping a conversation would shrink the benchmark without
    anyone noticing; a wrong pairing would be worse."""

    def fake_fetch(url: str, name: str, **_):
        if name == "AnnoMI-full.csv":
            return FIXTURES / "annomi_sample.csv"
        if name.startswith("tneval_notes_part1."):
            path = FIXTURES / "_ghost.json"
            path.write_text(
                json.dumps([{"id": "99999", "mi_quality": "high", "human": {"note": {}}}]),
                encoding="utf-8",
            )
            return path
        path = FIXTURES / "_empty.json"
        path.write_text("[]", encoding="utf-8")
        return path

    monkeypatch.setattr(tneval, "fetch", fake_fetch)
    with pytest.raises(RuntimeError, match="99999"):
        tneval.load()


def test_tneval_limit(offline_tneval):
    assert len(tneval.load(limit=1)) == 1


# --- iHOPE -----------------------------------------------------------------


def test_ihope_drops_the_session_with_an_empty_gold_note(offline_ihope):
    sessions = ihope.load("test")
    assert "999" not in {s.id for s in sessions}
    assert all(session.reference for session in sessions)


def test_ihope_records_what_it_dropped(offline_ihope):
    """A count of 39 instead of 40 has to be explainable from the run record."""
    sessions = ihope.load("test")
    assert sessions[0].meta["dropped_empty_reference"] == ("999",)


def test_ihope_dropped_list_is_complete_for_every_session(offline_ihope):
    """The drop happens after some sessions are already built, so each one must
    still report the final list rather than a snapshot of it."""
    dropped = {s.meta["dropped_empty_reference"] for s in ihope.load("test")}
    assert dropped == {("999",)}


def test_ihope_parses_speakers(offline_ihope):
    session = ihope.load("test")[0]
    assert {turn.speaker for turn in session.turns} <= {"therapist", "client"}
    assert all(turn.text for turn in session.turns)


def test_ihope_keeps_semicolons_inside_an_utterance():
    """Segments with no speaker prefix are continuations. Dropping them would
    quietly shorten the transcript the model is asked to summarise."""
    turns = ihope._parse_dialogue("Therapist: One; two; three ; Patient: Yes.")
    assert len(turns) == 2
    assert turns[0].text == "One; two; three"
    assert turns[1].text == "Yes."


def test_ihope_sessions_are_sorted_numerically(offline_ihope):
    ids = [int(s.id) for s in ihope.load("test")]
    assert ids == sorted(ids)


# --- Session ---------------------------------------------------------------


def test_dialogue_labels_differ_per_track():
    """The two sources' prompts are reproduced verbatim and disagree on speaker
    labels, so the label is a parameter rather than a constant."""
    session = Session(
        id="x",
        source="test",
        turns=(Turn("therapist", "Hello."), Turn("client", "Hi.")),
    )
    assert session.as_dialogue() == "therapist: Hello.\nclient: Hi."
    assert session.as_dialogue("Therapist", "Patient") == "Therapist: Hello.\nPatient: Hi."
    assert session.word_count == 2
