"""The Czech loader, offline against synthetic fixtures.

Nothing here reads `data/czech`. That directory holds confidential clinical
transcripts, and a test that needed them would be a test nobody else could run.
The fixtures are invented, and each one says so in its own first line.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tnb.datasets import base, czech

FIXTURES = Path(__file__).parent / "fixtures" / "czech"


@pytest.fixture
def offline_czech(monkeypatch, tmp_path):
    """Serve both halves from fixtures, and keep checksums out of the real file."""
    monkeypatch.setattr(czech, "CORPUS_DIR", FIXTURES / "real")
    monkeypatch.setattr(czech, "TRANSLATED_DIR", FIXTURES / "translated")
    monkeypatch.setattr(czech, "IDS_PATH", tmp_path / "ids.json")
    monkeypatch.setattr(base, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(base, "CHECKSUM_PATH", tmp_path / "checksums.json")


def test_both_halves_load_with_their_own_labels(offline_czech):
    real = czech.load_real()
    translated = czech.load_translated()

    assert [session.source for session in real] == [czech.REAL]
    assert [session.source for session in translated] == [czech.TRANSLATED]
    assert real[0].meta["corpus"] == czech.REAL


def test_a_session_carries_no_reference(offline_czech):
    """There is no gold Czech note anywhere, which is what makes this track
    cheap: the rubric is judged from the note alone."""
    assert all(session.reference is None for session in czech.load_real())


def test_the_turns_are_read_in_order_and_nothing_is_dropped(offline_czech):
    turns = czech.load_real()[0].turns
    assert [turn.speaker for turn in turns[:4]] == [
        "therapist",
        "client",
        "therapist",
        "client",
    ]
    assert len(turns) == 8
    assert turns[0].text.startswith("SYNTHETIC-FIXTURE")
    assert not any(turn.text.startswith(("T:", "K:")) for turn in turns)


def test_diacritics_survive_the_read(offline_czech):
    """The corpus is UTF-8 and the whole track measures Czech spelling. A
    mis-decoded read would score every model on the loader's mistake."""
    text = " ".join(turn.text for turn in czech.load_real()[0].turns)
    assert "dařilo" in text
    assert '„nech to bejt"' in text


def test_the_id_is_a_digest_and_not_the_record_number(offline_czech, tmp_path):
    """The fixture is deliberately named like a clinical record. A filename
    travels into cache directory names, progress output and error messages;
    a digest carries which bytes were scored and names nobody."""
    session = czech.load_real()[0]
    names = json.loads((tmp_path / "ids.json").read_text(encoding="utf-8"))

    assert names[czech.REAL][session.id] == "999001.txt"
    assert session.id.startswith("cz-r-")
    assert "999001" not in session.id
    assert "999" not in session.id


def test_the_two_halves_get_different_id_prefixes(offline_czech):
    assert czech.load_real()[0].id.startswith("cz-r-")
    assert czech.load_translated()[0].id.startswith("cz-t-")


def test_the_id_is_stable_across_loads(offline_czech):
    """Cache paths are built from it. An id that moved would orphan every note
    already generated."""
    assert [s.id for s in czech.load_real()] == [s.id for s in czech.load_real()]


def test_one_checksum_per_half_and_no_filename_in_it(offline_czech, tmp_path):
    """Every row copies the whole checksum file, English rows included. A
    per-file entry would publish ten record numbers on the page."""
    czech.load_real()
    czech.load_translated()
    recorded = base.checksums()

    assert sorted(recorded) == [czech.REAL, czech.TRANSLATED]
    assert "999001" not in json.dumps(recorded)


def test_writing_one_half_leaves_the_other_alone(offline_czech, tmp_path):
    czech.load_real()
    czech.load_translated()
    names = json.loads((tmp_path / "ids.json").read_text(encoding="utf-8"))
    assert sorted(names) == [czech.REAL, czech.TRANSLATED]


def test_the_checksum_describes_the_corpus_not_the_slice(offline_czech):
    """`limit` slices what is returned; it does not change what the corpus was.
    How much of it a run used is on the row as n_sessions_attempted."""
    czech.load_real()
    whole = base.checksums()[czech.REAL]
    czech.load_real(limit=1)
    assert base.checksums()[czech.REAL] == whole


def test_a_missing_corpus_raises_rather_than_returning_nothing(monkeypatch, tmp_path):
    """An empty list generates no calls, and a run that measured nothing looks
    exactly like a run that succeeded."""
    monkeypatch.setattr(czech, "CORPUS_DIR", tmp_path / "absent")
    with pytest.raises(RuntimeError, match="reads a local corpus"):
        czech.load_real()


def test_an_empty_corpus_directory_raises(monkeypatch, tmp_path):
    (tmp_path / "empty").mkdir()
    monkeypatch.setattr(czech, "CORPUS_DIR", tmp_path / "empty")
    with pytest.raises(RuntimeError, match="no .txt transcript"):
        czech.load_real()


def test_an_unexpected_line_raises_and_repeats_neither_the_line_nor_the_file(monkeypatch, tmp_path):
    """Put the bug back: a dropped line is a shorter transcript that still looks
    whole. And the message is printed to stdout, so it must not carry content."""
    corpus = tmp_path / "broken"
    corpus.mkdir()
    (corpus / "555002.txt").write_text(
        "T: dobrý den\n\nSPEAKER 3: klientka pláče\n\nK: dobrý den\n", encoding="utf-8"
    )
    monkeypatch.setattr(czech, "CORPUS_DIR", corpus)
    monkeypatch.setattr(czech, "IDS_PATH", tmp_path / "ids.json")

    with pytest.raises(RuntimeError) as caught:
        czech.load_real()

    message = str(caught.value)
    assert "line 3" in message
    assert "klientka pláče" not in message
    assert "555002" not in message


def test_two_identical_transcripts_are_refused(monkeypatch, tmp_path):
    """Same bytes, same digest, same id -- and one session counted twice."""
    corpus = tmp_path / "twins"
    corpus.mkdir()
    for name in ("a.txt", "b.txt"):
        (corpus / name).write_text("T: dobrý den\n\nK: dobrý den\n", encoding="utf-8")
    monkeypatch.setattr(czech, "CORPUS_DIR", corpus)
    monkeypatch.setattr(czech, "IDS_PATH", tmp_path / "ids.json")

    with pytest.raises(RuntimeError, match="share the id"):
        czech.load_real()
