"""PDSQI-9 over the Czech notes: the boundary, the two column sets, the rows.

Offline throughout. The one thing worth testing hardest is a negative: a real
session must have no path to the judge's provider, and the tests below assert
that from the corpus name rather than from a flag anybody could pass wrongly.
"""

from __future__ import annotations

import json

import pytest

from tnb import results
from tnb.datasets.base import Session, Turn
from tnb.scoring import czech_pdsqi, pdsqi, pdsqi_run
from tnb.scoring.run import Candidate
from tnb.tasks import czech as czech_task

NOTE = {
    "subjective": "Klientka popisuje napětí před zkouškou.",
    "objective": "V kontaktu spolupracující.",
    "assessment": "Pokračuje práce na úzkosti.",
    "plan": "Nácvik dýchání.",
}

SECRET = "tohle je důvěrná replika ze skutečného sezení"


def _sessions() -> tuple[Session, Session]:
    real = Session(
        id="cz-r-0000abcd",
        source="czech-real",
        turns=(Turn("client", SECRET),),
    )
    translated = Session(
        id="cz-t-0000abcd",
        source="czech-translated",
        turns=(Turn("client", "dobrý den"),),
    )
    return real, translated


def _cache(tmp_path, session: Session, task_name: str) -> None:
    unit = tmp_path / "einfra" / task_name / czech_task.PROMPT_VERSION / "m" / session.id
    unit.mkdir(parents=True)
    (unit / "note.json").write_text(json.dumps({"ok": True, "note": NOTE}), encoding="utf-8")


# --- the boundary ----------------------------------------------------------


def test_a_real_session_transcript_may_never_reach_the_judge():
    assert czech_pdsqi.transcripts_may_leave(czech_task.NAME_REAL) is False
    assert czech_pdsqi.transcripts_may_leave(czech_task.NAME_TRANSLATED) is True


def test_an_unknown_corpus_raises_rather_than_defaulting():
    """Either default is a decision. Silence would make it for whoever adds the
    next corpus, and one of the two directions is a confidentiality breach."""
    with pytest.raises(ValueError, match="not a Czech corpus"):
        czech_pdsqi.transcripts_may_leave("soap")


def test_candidates_from_the_real_corpus_carry_no_transcript(tmp_path):
    """The assertion this whole module exists to make. `conversation` is what
    `pdsqi.build_tasks` would put in a prompt, so an empty one is not caution
    but the absence of a string that could travel."""
    real, _ = _sessions()
    _cache(tmp_path, real, czech_task.NAME_REAL)

    candidates = list(
        czech_pdsqi.from_generations([real], task_name=czech_task.NAME_REAL, cache_dir=tmp_path)
    )
    assert candidates
    for candidate in candidates:
        assert candidate.conversation == ""
        assert SECRET not in candidate.conversation


def test_candidates_from_the_translated_corpus_do_carry_one(tmp_path):
    """AnnoMI is published under CC-BY. Withholding it would cost the two
    attributes that need a session for no protection anyone is owed."""
    _, translated = _sessions()
    _cache(tmp_path, translated, czech_task.NAME_TRANSLATED)

    candidates = list(
        czech_pdsqi.from_generations(
            [translated], task_name=czech_task.NAME_TRANSLATED, cache_dir=tmp_path
        )
    )
    assert candidates
    assert all("dobrý den" in candidate.conversation for candidate in candidates)


def test_no_prompt_built_for_a_real_note_holds_the_session(tmp_path):
    """One step further than the candidate: what the judge would actually be
    sent. Six prompts, and the transcript block in none of them."""
    real, _ = _sessions()
    _cache(tmp_path, real, czech_task.NAME_REAL)
    candidate = next(
        iter(
            czech_pdsqi.from_generations([real], task_name=czech_task.NAME_REAL, cache_dir=tmp_path)
        )
    )

    note = czech_task.render_note(candidate.note)
    tasks = pdsqi.build_tasks(note, None)
    assert len(tasks) == len(pdsqi.NOTE_ONLY_KEYS) == 6
    for task in tasks:
        assert SECRET not in task.prompt


# --- two column sets, on purpose -------------------------------------------


def test_the_real_half_is_asked_six_attributes_and_the_translated_eight():
    assert czech_pdsqi.attribute_keys(czech_task.NAME_REAL) == pdsqi.NOTE_ONLY_KEYS
    assert czech_pdsqi.attribute_keys(czech_task.NAME_TRANSLATED) == pdsqi.ATTRIBUTE_KEYS
    assert len(czech_pdsqi.attribute_keys(czech_task.NAME_REAL)) == 6
    assert len(czech_pdsqi.attribute_keys(czech_task.NAME_TRANSLATED)) == 8


def test_the_two_attributes_that_need_a_session_are_the_two_that_differ():
    real = set(czech_pdsqi.attribute_keys(czech_task.NAME_REAL))
    translated = set(czech_pdsqi.attribute_keys(czech_task.NAME_TRANSLATED))
    assert translated - real == {"accurate", "thorough"}


def test_a_column_that_cannot_be_asked_is_not_declared():
    """An empty heading on the page reads as a model that failed, not as a
    question nobody was allowed to put."""
    measures = czech_pdsqi.measures(czech_task.NAME_REAL)
    assert "accurate" not in measures
    assert "thorough" not in measures
    assert set(measures) == set(pdsqi.NOTE_ONLY_KEYS)


def test_the_real_halfs_metrics_note_says_why_two_columns_are_missing():
    note = czech_pdsqi.metrics_note(czech_task.NAME_REAL)
    assert "could not be put" in note
    assert "not the same as a note that failed them" in note


# --- what the rows say about themselves ------------------------------------


def _scored(track_translated: bool) -> list[pdsqi_run.NoteResult]:
    keys = pdsqi.ATTRIBUTE_KEYS if track_translated else pdsqi.NOTE_ONLY_KEYS
    candidate = Candidate(
        provider="einfra",
        system_id="a-model",
        system_type="model",
        system_label="a-model",
        session_id="cz-r-0000abcd",
        note=dict(NOTE),
        conversation="",
    )
    return [pdsqi_run.NoteResult(candidate=candidate, scored={key: 4.0 for key in keys})]


def test_the_rows_carry_the_czech_presentation_and_not_the_english_one():
    """`pdsqi9-note-v1` names a note joined under English headings. These are
    joined under Czech ones, and two rows that both say `pdsqi9-note-v1` are
    supposed to have been asked the same thing."""
    rows = pdsqi_run.to_rows(
        _scored(False),
        judge_model="a-judge",
        track=results.TRACK_CZECH_REAL_PDSQI,
        prompt_version=czech_task.PROMPT_VERSION,
        judge_prompt_version=czech_pdsqi.JUDGE_PROMPT_VERSION,
        metrics_note=czech_pdsqi.metrics_note(czech_task.NAME_REAL),
    )
    assert [row.track for row in rows] == [results.TRACK_CZECH_REAL_PDSQI]
    assert rows[0].judge_prompt_version == "pdsqi9-note-cs-v1"
    assert rows[0].judge_prompt_version != pdsqi.JUDGE_PROMPT_VERSION
    assert rows[0].prompt_version == czech_task.PROMPT_VERSION


def test_the_default_row_is_still_the_english_soap_track():
    """The parameters were added for this track; the three callers that came
    before must not have moved."""
    rows = pdsqi_run.to_rows(_scored(True), judge_model="a-judge")
    assert rows[0].track == results.TRACK_PDSQI
    assert rows[0].judge_prompt_version == pdsqi.JUDGE_PROMPT_VERSION


def test_the_two_halves_can_never_land_in_one_comparability_group():
    """Six attributes and eight are two instruments. `COMPARABILITY_KEYS`
    compares the track, so this holds without anyone remembering it."""
    real = pdsqi_run.to_rows(
        _scored(False), judge_model="a-judge", track=results.TRACK_CZECH_REAL_PDSQI
    )
    translated = pdsqi_run.to_rows(
        _scored(True), judge_model="a-judge", track=results.TRACK_CZECH_TRANSLATED_PDSQI
    )
    assert real[0].comparability_key() != translated[0].comparability_key()


def test_both_tracks_are_local_and_never_published():
    for track in (results.TRACK_CZECH_REAL_PDSQI, results.TRACK_CZECH_TRANSLATED_PDSQI):
        assert track in results.LOCAL_TRACKS
        assert track not in results.PUBLISHED_TRACKS


def test_neither_track_generates_anything_of_its_own():
    """They rate the notes the two Czech tasks produced. A `TRACK_BY_TASK`
    entry would claim a generation directory that does not exist and report
    every model as having attempted nothing."""
    assert results.TRACK_CZECH_REAL_PDSQI not in results.TRACK_BY_TASK.values()
    assert results.TRACK_CZECH_TRANSLATED_PDSQI not in results.TRACK_BY_TASK.values()
