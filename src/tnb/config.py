"""Loading and validating the model-selection policy.

``models.yaml`` holds rules, never a model list. See ``docs/methodology.md``
for why: e-INFRA does not guarantee that any model version stays available, so
a pinned list would rot within weeks.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = REPO_ROOT / "models.yaml"
DEFAULT_BASE_URL = "https://llm.ai.e-infra.cz/v1"


@dataclass(frozen=True)
class DiscoveryPolicy:
    """Rules for turning the endpoint's model list into a benchmark set."""

    exclude: tuple[re.Pattern[str], ...] = ()
    exclude_aliases: bool = True
    #: Verified duplicates: alias id -> the concrete model it resolves to.
    #: Established by fingerprinting, not by guessing. See models.yaml.
    aliases: dict[str, str] = field(default_factory=dict)
    max_models: int = 20


@dataclass(frozen=True)
class GenerationPolicy:
    temperature: float = 0.0
    max_tokens: int = 2048
    #: Second-chance budget for a call that stopped on `length` with nothing
    #: usable in it -- a reasoning model that thought until it ran out.
    escalate_max_tokens: int = 0
    concurrency: int = 2
    timeout_s: int = 180
    retries: int = 3
    #: e-INFRA rate-limits per API key, so 429 is routine rather than
    #: exceptional. Waits grow as backoff_s * attempt.
    backoff_s: int = 6


@dataclass(frozen=True)
class Policy:
    provider: str = "einfra"
    base_url: str = DEFAULT_BASE_URL
    token_env: str = "EINFRA_API_TOKEN"
    discovery: DiscoveryPolicy = field(default_factory=DiscoveryPolicy)
    generation: GenerationPolicy = field(default_factory=GenerationPolicy)

    def token(self) -> str:
        """Read the API token, with an error message that says what to do."""
        value = os.environ.get(self.token_env, "").strip()
        if not value:
            raise RuntimeError(
                f"{self.token_env} is not set. Get a token at "
                "https://chat.ai.e-infra.cz -> Account -> API keys "
                "(needs a MetaCentrum account or Masaryk University affiliation), "
                "then put it in .env or export it."
            )
        return value


def load_policy(path: Path | None = None) -> Policy:
    """Read ``models.yaml`` into a :class:`Policy`."""
    path = path or DEFAULT_POLICY_PATH
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    discovery_raw = raw.get("discovery") or {}
    generation_raw = raw.get("generation") or {}

    base_url = os.environ.get(raw.get("base_url_env", "EINFRA_BASE_URL"), "").strip()

    return Policy(
        provider=raw.get("provider", "einfra"),
        base_url=base_url or DEFAULT_BASE_URL,
        token_env=raw.get("token_env", "EINFRA_API_TOKEN"),
        discovery=DiscoveryPolicy(
            exclude=tuple(
                re.compile(pattern, re.IGNORECASE) for pattern in discovery_raw.get("exclude", [])
            ),
            exclude_aliases=bool(discovery_raw.get("exclude_aliases", True)),
            aliases=dict(discovery_raw.get("aliases") or {}),
            max_models=int(discovery_raw.get("max_models", 20)),
        ),
        generation=GenerationPolicy(
            temperature=float(generation_raw.get("temperature", 0.0)),
            max_tokens=int(generation_raw.get("max_tokens", 2048)),
            escalate_max_tokens=int(generation_raw.get("escalate_max_tokens", 0)),
            concurrency=int(generation_raw.get("concurrency", 2)),
            timeout_s=int(generation_raw.get("timeout_s", 180)),
            retries=int(generation_raw.get("retries", 3)),
            backoff_s=int(generation_raw.get("backoff_s", 6)),
        ),
    )
