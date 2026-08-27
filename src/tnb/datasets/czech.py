"""The Czech tracks: real clinical sessions, and AnnoMI conversations translated.

Both halves live in ``data/czech``, which is gitignored. The real transcripts
are confidential clinical material from a single client and are never committed,
never quoted in a document or a commit message, and never put on the published
page. Scores may be published; text may not. See ``docs/datasets.md``.

Two decisions here are load-bearing rather than stylistic.

**A session's id is a digest of its own bytes, not its filename.** The files are
named after clinical record numbers, and a filename travels further than it
looks: into the generation and judge cache directory names, into progress
output, into the summary printed after a failed call. A digest carries the one
thing a run needs -- which bytes were scored -- and names nobody. The map back
to filenames is written to ``data/czech/ids.json``, inside the gitignored
directory, so a bad note can still be traced by hand.

**The recorded checksum is one aggregate per half, never one per file.** Every
row copies the whole checksum file into ``Row.dataset_checksums``, including
rows belonging to the two English tracks, so a per-file entry would publish ten
record numbers on the leaderboard page.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tnb.datasets.base import CACHE_DIR, Session, Turn, record_checksum

CORPUS_DIR = CACHE_DIR / "czech"

#: The de-identified transcripts, and the only ones anything here will read.
#:
#: The originals sit one directory up, named after clinical record numbers, and
#: `tools/anonymise_czech.py` writes this directory from them. Reading the
#: originals is refused rather than merely avoided -- see `_refuse_originals`.
#: Names, Prague districts, countries and the recording identifier spoken in the
#: first turn are all gone; what is left is the session.
REAL_DIR = CORPUS_DIR / "anonymised"
TRANSLATED_DIR = CORPUS_DIR / "translated"

#: Where the digest ids map back to the files they were taken from. Inside
#: ``data/``, so it is gitignored like the transcripts themselves.
IDS_PATH = CORPUS_DIR / "ids.json"

#: The corpus labels. These reach `Row.dataset_checksums` and the page, so they
#: are names of corpora and carry nothing about a client, a date or a file.
REAL = "czech-real"
TRANSLATED = "czech-translated"

#: Speaker prefixes the transcripts use, one turn per line, blank lines between.
THERAPIST_PREFIX = "T: "
CLIENT_PREFIX = "K: "

_ID_PREFIXES = {REAL: "cz-r-", TRANSLATED: "cz-t-"}


def _parse(text: str, *, corpus: str, session_id: str) -> tuple[Turn, ...]:
    """Turn one transcript into turns, or refuse.

    A line this does not recognise raises rather than being dropped: a silently
    skipped line is a shorter transcript that still looks like a whole one. The
    message names the corpus and the session so the file can be found, and
    reproduces neither the line nor the filename -- an error string is printed
    to stdout and, on failure, filed into a row.
    """
    turns: list[Turn] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith(THERAPIST_PREFIX):
            turns.append(Turn("therapist", line[len(THERAPIST_PREFIX) :].strip()))
        elif line.startswith(CLIENT_PREFIX):
            turns.append(Turn("client", line[len(CLIENT_PREFIX) :].strip()))
        else:
            raise RuntimeError(
                f"{corpus} session {session_id}: line {number} begins with neither "
                f"{THERAPIST_PREFIX!r} nor {CLIENT_PREFIX!r}. The line is not repeated "
                "here because this corpus is confidential; open the file listed in "
                f"{IDS_PATH} under that id."
            )

    if not turns:
        raise RuntimeError(f"{corpus} session {session_id}: no turns were found.")
    return tuple(turns)


def _write_ids(corpus: str, names: dict[str, str]) -> None:
    """Record id -> filename for this half, leaving the other half alone."""
    existing: dict[str, dict[str, str]] = {}
    if IDS_PATH.exists():
        existing = json.loads(IDS_PATH.read_text(encoding="utf-8"))
    existing[corpus] = names
    IDS_PATH.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )


def _refuse_originals(directory: Path) -> None:
    """Refuse to read the transcripts as they came off the recording.

    The de-identified copies live one level down, so a hand that points this
    at `data/czech` rather than `data/czech/anonymised` gets a corpus that
    still names a client, a district and a hospital -- and gets it silently,
    because both directories parse. Refusing is one comparison and it is the
    difference between a rule and a habit.
    """
    if directory.resolve() == CORPUS_DIR.resolve():
        raise RuntimeError(
            f"{CORPUS_DIR} holds the transcripts as recorded, names and all. "
            f"The de-identified corpus is {REAL_DIR}; run tools/anonymise_czech.py "
            "if it is not there."
        )


def _load_dir(directory: Path, *, corpus: str, limit: int | None) -> list[Session]:
    _refuse_originals(directory)
    if not directory.is_dir():
        raise RuntimeError(
            f"{corpus} was not found at {directory}. This track reads a local corpus "
            "rather than fetching one; see docs/datasets.md."
        )

    paths = sorted(path for path in directory.glob("*.txt") if path.is_file())
    if not paths:
        raise RuntimeError(
            f"{corpus} at {directory} holds no .txt transcript. Refusing rather than "
            "returning nothing: an empty corpus generates no calls and a run that "
            "measured nothing looks exactly like a run that succeeded."
        )

    prefix = _ID_PREFIXES[corpus]
    sessions: list[Session] = []
    names: dict[str, str] = {}
    digests: list[str] = []

    for path in paths:
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        session_id = f"{prefix}{digest[:8]}"
        if session_id in names:
            raise RuntimeError(
                f"{corpus}: two files have identical contents and so share the id "
                f"{session_id}. Scoring both would count one session twice."
            )

        names[session_id] = path.name
        digests.append(digest)
        sessions.append(
            Session(
                id=session_id,
                source=corpus,
                turns=_parse(payload.decode("utf-8"), corpus=corpus, session_id=session_id),
                reference=None,
                meta={"corpus": corpus},
            )
        )

    # Over every file on disk, not over the slice `limit` returns. This names
    # the corpus a run was pointed at; how much of it a run used is already on
    # the row as `n_sessions_attempted`. `fetch` records a whole file the same
    # way for the same reason.
    record_checksum(corpus, hashlib.sha256("\n".join(sorted(digests)).encode()).hexdigest())
    _write_ids(corpus, names)

    sessions.sort(key=lambda session: session.id)
    return sessions[:limit] if limit else sessions


def load_real(limit: int | None = None) -> list[Session]:
    """The real Czech clinical sessions, de-identified, from ``data/czech/anonymised``."""
    return _load_dir(REAL_DIR, corpus=REAL, limit=limit)


def load_translated(limit: int | None = None) -> list[Session]:
    """The AnnoMI conversations translated into Czech, from ``data/czech/translated``."""
    return _load_dir(TRANSLATED_DIR, corpus=TRANSLATED, limit=limit)
