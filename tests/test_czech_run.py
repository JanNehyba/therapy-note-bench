"""The Czech runner, and the separation that keeps its rows off the page.

Offline throughout: the judge is a stub, the generation cache is built in a
temporary directory, and nothing reads `data/czech`.
"""

from __future__ import annotations

import json

import pytest

from tnb import results
from tnb.scoring import czech, czech_run
from tnb.scoring.run import Candidate
from tnb.tasks import czech as czech_task

NOTE = {
    "subjective": "Klientka popisuje napětí před zkouškou.",
    "objective": "V kontaktu spolupracující.",
    "assessment": "Pokračuje práce na úzkosti.",
    "plan": "Nácvik dýchání.",
}


def _candidate(system_id: str = "a-model", session_id: str = "cz-r-0000abcd") -> Candidate:
    return Candidate(
        provider="einfra",
        system_id=system_id,
        system_type="model",
        system_label=system_id,
        session_id=session_id,
        note=dict(NOTE),
        conversation="",
    )


def _result(system_id: str = "a-model", **scored: float) -> czech_run.NoteResult:
    values = {key: 1.0 for key in czech.CRITERION_KEYS}
    values.update(scored)
    return czech_run.NoteResult(candidate=_candidate(system_id), scored=values)


# --- the corpus boundary ---------------------------------------------------


def test_from_generations_reads_one_corpus_and_not_the_other(tmp_path):
    """The two halves live in two generation directories precisely so this can.
    A single task would have put both into one track and the design rests on
    their never being averaged."""
    from tnb.datasets.base import Session, Turn

    session = Session(id="cz-r-0000abcd", source="czech-real", turns=(Turn("client", "dobrý den"),))
    for task_name in ("czech-real", "czech-translated"):
        unit = tmp_path / "einfra" / task_name / czech_task.PROMPT_VERSION / "m" / session.id
        unit.mkdir(parents=True)
        (unit / "note.json").write_text(json.dumps({"ok": True, "note": NOTE}), encoding="utf-8")

    real = list(czech_run.from_generations([session], task_name="czech-real", cache_dir=tmp_path))
    both = list(
        czech_run.from_generations([session], task_name="czech-translated", cache_dir=tmp_path)
    )
    assert len(real) == len(both) == 1
    assert real[0].session_id == session.id


def test_a_candidate_never_carries_a_transcript(tmp_path):
    """The field exists because `Candidate` is shared with the English runner.
    Nothing here fills it, and `czech.build_tasks` has nowhere to put it."""
    from tnb.datasets.base import Session, Turn

    secret = "mam strach ze zkousky"
    session = Session(id="cz-r-0000abcd", source="czech-real", turns=(Turn("client", secret),))
    unit = tmp_path / "einfra" / "czech-real" / czech_task.PROMPT_VERSION / "m" / session.id
    unit.mkdir(parents=True)
    (unit / "note.json").write_text(json.dumps({"ok": True, "note": NOTE}), encoding="utf-8")

    candidate = next(
        czech_run.from_generations([session], task_name="czech-real", cache_dir=tmp_path)
    )
    assert candidate.conversation == ""
    for task in czech.build_tasks(czech_task.render_note(candidate.note)):
        assert secret not in task.prompt


# --- what a row says -------------------------------------------------------


def test_the_track_is_a_parameter_and_two_calls_give_two_tracks():
    """No runner before this one took a track. This one serves two, and the
    whole design is that they are never averaged."""
    scored = [_result()]
    real = czech_run.to_rows(scored, track=results.TRACK_CZECH_REAL, judge_model="j")[0]
    translated = czech_run.to_rows(scored, track=results.TRACK_CZECH_TRANSLATED, judge_model="j")[0]

    assert real.track != translated.track
    assert real.comparability_key() != translated.comparability_key()


def test_a_row_refuses_a_track_that_is_not_czech():
    with pytest.raises(ValueError, match="not a Czech track"):
        czech_run.to_rows([_result()], track=results.TRACK_TNEVAL, judge_model="j")


def test_the_row_says_the_instrument_has_no_anchor():
    """Every other track can point at something. This one has to say it cannot,
    on the row, because a metrics_note travels with the number."""
    row = czech_run.to_rows([_result()], track=results.TRACK_CZECH_REAL, judge_model="j")[0]
    assert "no human has rated these notes" in row.metrics_note
    assert "translation" in row.metrics_note


def test_the_denominator_of_each_column_is_published_beside_it():
    """Quotation marks are asked only of a note that quotes something, so that
    column is a mean over fewer notes. Saying so costs one number."""
    quoting = _result()
    silent = _result()
    del silent.scored["quotes"]

    aggregate = czech_run.SystemAggregate(notes=[quoting, silent])
    metrics = aggregate.metrics()

    assert metrics.detail["quotes.notes"] == 1
    assert metrics.detail["diacritics.notes"] == 2
    assert metrics.headline["quotes"] == 1.0


def test_a_partial_note_is_counted_and_left_out_of_the_mean():
    good = _result()
    partial = _result(diacritics=0.0)
    partial.missing = ["register"]

    aggregate = czech_run.SystemAggregate(notes=[good, partial])
    assert aggregate.n_partial == 1
    # The failing note is not in the mean, so the mean is the good one's.
    assert aggregate.metrics().headline["diacritics"] == 1.0


def test_an_empty_note_is_counted_as_partial_and_does_not_vanish():
    """A model that wrote nothing must not lose its worst note. It is not
    scored -- every criterion asks about the absence of a fault -- but it is
    still one of the notes it was asked for."""
    empty = czech_run.NoteResult(candidate=_candidate(), empty=True)
    aggregate = czech_run.SystemAggregate(notes=[_result(), empty])

    assert aggregate.n_empty == 1
    assert aggregate.n_partial == 1
    assert len(aggregate.notes) == 2


# --- measured, not published -----------------------------------------------


def test_the_czech_tracks_are_named_as_local():
    """All four: the seven criteria and PDSQI-9 over the same notes. The
    instrument does not change where the rows may be written -- what makes a
    track local is the corpus it was measured on."""
    assert set(results.LOCAL_TRACKS) == {
        results.TRACK_CZECH_REAL,
        results.TRACK_CZECH_TRANSLATED,
        results.TRACK_CZECH_REAL_PDSQI,
        results.TRACK_CZECH_TRANSLATED_PDSQI,
    }
    assert not set(results.LOCAL_TRACKS) & set(results.PUBLISHED_TRACKS)


def test_the_committed_record_holds_no_czech_row():
    """The whole of the local-only decision, asserted where it can be seen.
    `report.write` reads this file, so a Czech row reaching it is a Czech row
    on the public page."""
    rows = results.load()
    offenders = sorted({row.track for row in rows if row.track in results.LOCAL_TRACKS})
    assert not offenders, f"{offenders} are measured locally and reached the committed record"


def test_the_coverage_sweep_skips_the_local_tracks(tmp_path):
    """`cmd_report` appends whatever `index_generations` returns, so the filter
    belongs at the point that produces the rows rather than one caller away."""
    for task_name in ("soap", "czech-real"):
        unit = tmp_path / "einfra" / task_name / "v1" / "m" / "s1"
        unit.mkdir(parents=True)
        (unit / "note.json").write_text(json.dumps({"ok": True}), encoding="utf-8")

    tracks = {row.track for row in results.index_generations(tmp_path)}
    assert results.TRACK_CZECH_REAL not in tracks
