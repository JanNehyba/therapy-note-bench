"""Optional adapters to the host checkout. Importing the core needs no ``tnb``."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import asdict, replace
from pathlib import Path

from .schema import Case, Model, Source, Turn, require


def annomi_video_groups(path: Path, wanted: set[str]) -> dict[str, str]:
    """Known video dependencies, not inferred client or therapist identities."""
    videos: dict[str, set[str]] = {key: set() for key in wanted}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["transcript_id"] in wanted and row.get("video_url"):
                videos[row["transcript_id"]].add(row["video_url"])
    require(
        all(len(v) == 1 for v in videos.values()), "AnnoMI video ancestry is missing or ambiguous"
    )
    return {
        key: "annomi-video:" + hashlib.sha256(next(iter(value)).encode("utf-8")).hexdigest()
        for key, value in videos.items()
    }


def import_cases(
    corpus: str,
    limit: int | None = None,
    czech_root: Path | None = None,
    groups: dict | None = None,
) -> list[Case]:
    """No filenames enter a case. Unknown Czech ancestry stays in a pilot cluster."""
    groups = groups or {}
    require(limit is None or limit > 0, "Import limit must be positive")
    if corpus in ("tneval", "ihope"):
        from tnb.datasets import ihope, tneval

        sessions = tneval.load(limit=limit) if corpus == "tneval" else ihope.load(limit=limit)
        video_groups = {}
        if corpus == "tneval":
            from tnb.datasets.base import CACHE_DIR

            video_groups = annomi_video_groups(
                CACHE_DIR / "AnnoMI-full.csv", {s.id for s in sessions}
            )
        cases = []
        for s in sessions:
            turns = tuple(Turn(f"t{i:05d}", t.speaker, t.text) for i, t in enumerate(s.turns))
            group = groups.get(s.id, {})
            cases.append(
                Case(
                    s.id,
                    corpus,
                    "en",
                    "public_demo",
                    group.get("group_id", video_groups.get(s.id, corpus + ":" + s.id)),
                    group.get("split", "pilot"),
                    0,
                    (Source("current", "session", 0, turns),),
                    ("local", "einfra", "openai", "vertex"),
                    group.get("translation_group"),
                )
            )
        return cases
    require(corpus in ("czech-real", "czech-translated"), "Unknown corpus adapter")
    if czech_root is None:
        from tnb.config import REPO_ROOT

        czech_root = REPO_ROOT
    root = czech_root.resolve() / "data" / "czech"
    directory = root / ("anonymised" if corpus == "czech-real" else "translated")
    require(directory.is_dir(), "The specified Czech corpus directory is unavailable")
    cases = []
    for path in sorted(directory.glob("*.txt"))[:limit]:
        raw = path.read_text(encoding="utf-8-sig")
        turns = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            require(line.startswith(("T: ", "K: ")), "Unrecognized Czech speaker line")
            turns.append(
                Turn(
                    f"t{len(turns):05d}",
                    "therapist" if line.startswith("T: ") else "client",
                    line[3:].strip(),
                )
            )
        key = ("cz-r-" if corpus == "czech-real" else "cz-t-") + hashlib.sha256(
            path.read_bytes()
        ).hexdigest()[:16]
        group = groups.get(key, {})
        actual = corpus == "czech-real"
        split = group.get("split", "pilot")
        require(
            split == "pilot" or bool(group.get("group_id")),
            "Non-pilot Czech cases need explicit client provenance",
        )
        require(
            actual or split == "pilot" or bool(group.get("translation_group")),
            "Confirmatory translated cases need their original-source group",
        )
        index = group.get("session_index", 0)
        cases.append(
            Case(
                key,
                corpus,
                "cs",
                "native_real" if actual else "translated_demo",
                group.get(
                    "group_id",
                    "czech:single-client-pilot" if actual else "annomi:unresolved-ancestry",
                ),
                split,
                index,
                (Source("current", "session", index, tuple(turns)),),
                ("local", "einfra") if actual else ("local", "einfra", "openai", "vertex"),
                group.get("translation_group"),
            )
        )
    require(bool(cases), "No Czech sessions found")
    return cases


class HostBackend:
    """Reuse the host's provider dialects; exactly one billed attempt per reserve."""

    def __init__(
        self,
        provider_name: str,
        model: str,
        family: str,
        max_tokens: int = 8192,
        effort: str | None = None,
        discover: bool = True,
    ):
        from dotenv import load_dotenv

        from tnb.config import REPO_ROOT, load_policy
        from tnb.providers import openai_compatible as client

        load_dotenv(REPO_ROOT / ".env")
        provider = load_policy().get(provider_name)
        generation = replace(provider.generation, max_tokens=max_tokens, retries=0, concurrency=1)
        if effort is not None:
            generation = replace(generation, effort=effort)
        self.provider = replace(provider, generation=generation)
        self.client = client
        if discover:
            available = client.discover(self.provider)
            require(
                any(m.id == model and m.included for m in available),
                "Requested model is not in the provider's included discovery snapshot",
            )
        self.identity = Model(
            provider_name,
            model,
            family,
            {
                "max_tokens": max_tokens,
                "temperature": generation.temperature,
                "effort": generation.effort,
                "dialect": asdict(generation.dialect),
                "timeout_s": generation.timeout_s,
                "retries": 0,
            },
        )

    def complete(self, prompt: str) -> str:
        result = self.client.complete(
            self.provider,
            self.identity.model,
            prompt,
            max_tokens=self.identity.settings["max_tokens"],
        )
        require(result.ok, "Model completion failed or was truncated")
        return result.text
