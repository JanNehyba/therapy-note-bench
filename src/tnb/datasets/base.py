"""The common shape every corpus is normalised into, and the fetch cache.

No corpus is committed to this repository — two of the three upstream sources
publish no licence. Everything is downloaded on first use into ``data/``, which
is gitignored, and its checksum recorded so a run can say which bytes it scored.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from tnb.config import REPO_ROOT

CACHE_DIR = REPO_ROOT / "data"
CHECKSUM_PATH = CACHE_DIR / "checksums.json"


@dataclass(frozen=True)
class Turn:
    """One utterance. ``speaker`` is normalised to 'therapist' or 'client'."""

    speaker: str
    text: str


@dataclass(frozen=True)
class Session:
    """A therapy session, plus its reference note where one exists.

    ``reference`` is None for reference-free tracks. ``meta`` carries whatever
    the source provides that scoring may need — the human note and human
    ratings for TN-Eval, the topic and MI quality for AnnoMI.
    """

    id: str
    source: str
    turns: tuple[Turn, ...]
    reference: str | None = None
    meta: dict = field(default_factory=dict)

    def as_dialogue(self, therapist: str = "therapist", client: str = "client") -> str:
        """Render as ``speaker: text`` lines.

        Speaker labels are a parameter because the two tracks disagree and the
        prompts are reproduced verbatim from their sources: TN-Eval writes
        'therapist'/'client', iHOPE writes 'Therapist'/'Patient'.
        """
        labels = {"therapist": therapist, "client": client}
        return "\n".join(f"{labels[turn.speaker]}: {turn.text}" for turn in self.turns)

    @property
    def word_count(self) -> int:
        return sum(len(turn.text.split()) for turn in self.turns)


def record_checksum(name: str, digest: str) -> None:
    """Record what a corpus was, under a name the run record can publish.

    Public because not every corpus is fetched. A loader reading files already
    on disk has no download to hang this off, and without it its rows carry
    every other corpus's digest and nothing about their own.

    ``name`` reaches `Row.dataset_checksums` and therefore the published page,
    so it is a label for the corpus, never a filename.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    existing: dict[str, str] = {}
    if CHECKSUM_PATH.exists():
        existing = json.loads(CHECKSUM_PATH.read_text(encoding="utf-8"))
    existing[name] = digest
    CHECKSUM_PATH.write_text(json.dumps(existing, indent=2, sort_keys=True), encoding="utf-8")


def fetch(url: str, name: str, *, timeout: float = 120.0) -> Path:
    """Download ``url`` to ``data/name`` once, and return the path.

    A cached file is returned untouched, so a run is reproducible offline and
    an upstream change cannot silently alter results mid-experiment. Delete the
    file to re-download.
    """
    target = CACHE_DIR / name
    if target.exists():
        return target

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()

    target.write_bytes(response.content)
    record_checksum(name, hashlib.sha256(response.content).hexdigest())
    return target


def checksums() -> dict[str, str]:
    """Recorded digests of every cached corpus file, for the run record."""
    if not CHECKSUM_PATH.exists():
        return {}
    return json.loads(CHECKSUM_PATH.read_text(encoding="utf-8"))
