"""Content-addressed private artifacts and an explicit, resumable call budget."""

from __future__ import annotations

import json
import math
import os
import subprocess
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .schema import Case, Model, ValidationError, digest, plain, require


class Backend(Protocol):
    identity: Model

    def complete(self, prompt: str) -> str: ...


def protect_root(root: Path) -> Path:
    """Keep raw artifacts out of publishable paths in either checkout."""
    root = root.resolve()
    for parent in (root, *root.parents):
        if (parent / ".git").exists():
            relative = root.relative_to(parent)
            require(
                bool(relative.parts)
                and relative.parts[0] in ("local", "data", "scores", "generations"),
                "Raw gen-2 artifacts must live in a private artifact directory",
            )
            ignored = subprocess.run(
                ["git", "check-ignore", "--quiet", "--", str(root)],
                cwd=parent,
                capture_output=True,
                check=False,
            )
            require(ignored.returncode == 0, "Private artifact root is not actually gitignored")
            break
    return root


class Store:
    def __init__(self, root: Path):
        self.root = protect_root(root)

    def path(self, kind: str, key: str) -> Path:
        require(kind.isidentifier(), "Invalid artifact kind")
        return self.output_path(kind, digest(key) + ".json")

    def output_path(self, kind: str, name: str) -> Path:
        require(kind.isidentifier() and Path(name).name == name, "Invalid artifact path")
        path = self.root / kind / name
        require(
            path.resolve().is_relative_to(self.root), "Artifact destination escapes private root"
        )
        return path

    def get(self, kind: str, key: str) -> dict | list | None:
        path = self.path(kind, key)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def put(self, kind: str, key: str, value: object) -> Path:
        path = self.path(kind, key)
        payload = plain(value)
        if path.exists():
            require(
                json.loads(path.read_text(encoding="utf-8")) == payload,
                "Artifact identity collision; existing evidence will not be overwritten",
            )
            return path
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix("." + uuid.uuid4().hex + ".tmp")
        try:
            with temporary.open("x", encoding="utf-8") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                # Atomic publication without replacing a concurrent writer's file.
                os.link(temporary, path)
            except FileExistsError:
                require(
                    json.loads(path.read_text(encoding="utf-8")) == payload,
                    "Concurrent artifact identity collision",
                )
        finally:
            temporary.unlink(missing_ok=True)
        return path

    def all(self, kind: str) -> list[dict]:
        self.output_path(kind, "path-check.json")
        return [
            json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((self.root / kind).glob("*.json"))
        ]


@dataclass
class Budget:
    max_calls: int
    max_usd: float | None = None
    input_usd_per_million: float | None = None
    output_usd_per_million: float | None = None
    calls: int = 0
    reserved_usd: float = 0.0

    def reserve(self, prompt: str, output_tokens: int) -> None:
        require(self.max_calls > 0 and self.calls < self.max_calls, "Call budget exhausted")
        cost = 0.0
        if self.max_usd is not None:
            require(math.isfinite(self.max_usd) and self.max_usd >= 0, "Invalid dollar budget")
            rates = (self.input_usd_per_million, self.output_usd_per_million)
            require(
                all(r is not None and math.isfinite(r) and r >= 0 for r in rates),
                "A dollar ceiling needs explicit input and output prices",
            )
            # UTF-8 bytes are a conservative token bound. Reserve before every
            # HTTP attempt; neither failure nor truncation makes a request free.
            cost = (len(prompt.encode("utf-8")) * rates[0] + output_tokens * rates[1]) / 1e6
            require(self.reserved_usd + cost <= self.max_usd, "Dollar budget exhausted")
        self.calls += 1
        self.reserved_usd += cost


class Runner:
    def __init__(
        self,
        backend: Backend,
        store: Store,
        budget: Budget,
        max_input_chars: int = 200_000,
        replicate_id: str = "primary",
    ):
        self.backend, self.store, self.budget = backend, store, budget
        self.max_input_chars = max_input_chars
        require(bool(replicate_id), "A replicate needs an explicit identifier")
        self.replicate_id = replicate_id

    @property
    def identity(self) -> Model:
        return self.backend.identity

    def ask(
        self, case: Case, stage: str, prompt: str, validate: Callable[[dict], object] | None = None
    ) -> dict:
        case.authorize(self.identity.provider)
        require(
            len(prompt) <= self.max_input_chars, "Context exceeds configured limit; no truncation"
        )
        key = digest(
            {
                "case": case.revision,
                "model": self.identity,
                "stage": stage,
                "prompt": prompt,
                "max_input_chars": self.max_input_chars,
                "replicate_id": self.replicate_id,
            }
        )
        cached = self.store.get("calls", key)
        if cached is not None:
            if validate:
                validate(cached["answer"])
            return cached["answer"]
        maximum = self.identity.settings.get("max_tokens")
        require(type(maximum) is int and maximum > 0, "Backend must declare its output token limit")
        self.budget.reserve(prompt, maximum)
        try:
            text = self.backend.complete(prompt)
            answer = json.loads(text)
            require(isinstance(answer, dict), "Backend returned no JSON object")
            if validate:
                validate(answer)
        except Exception as exc:
            # Do not cache a failure as a measurement, or echo response bodies.
            raise ValidationError("Backend call failed or returned invalid JSON") from exc
        self.store.put(
            "calls",
            key,
            {
                "stage": stage,
                "replicate_id": self.replicate_id,
                "model": plain(self.identity),
                "prompt_digest": digest(prompt),
                "answer": answer,
            },
        )
        return answer
