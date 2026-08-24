"""Loading and validating the provider policy.

``models.yaml`` holds rules, never a model list. See ``docs/methodology.md``
for why: no provider guarantees that a model version stays available, so a
pinned list would rot within weeks.

A *provider* is one OpenAI-compatible endpoint, its credentials, and the rules
for turning its ``/v1/models`` into a benchmark set. There can be several. Which
provider served a model is part of that model's identity in the results, not a
footnote: the same name on two endpoints can be two different things —
different quantisation, different weights, a different system prompt — and a
table that merged them would compare two models under one row.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = REPO_ROOT / "models.yaml"


@dataclass(frozen=True)
class DiscoveryPolicy:
    """Rules for turning one endpoint's model list into a benchmark set."""

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
    #: Providers rate-limit per API key rather than per model, so this is a
    #: ceiling over the whole run against one provider. Six concurrent requests
    #: drew HTTP 429 on a third of calls against e-INFRA; two is well behaved.
    concurrency: int = 2
    timeout_s: int = 180
    retries: int = 3
    #: 429 is routine rather than exceptional. Waits grow as backoff_s * attempt.
    backoff_s: int = 6


@dataclass(frozen=True)
class Provider:
    """One endpoint: where to reach it, how to authenticate, what to benchmark.

    Everything the harness needs to talk to a backend lives here, so adding a
    second provider is a stanza in ``models.yaml`` rather than a code change.
    """

    name: str
    base_url: str
    token_env: str
    #: What to tell someone whose token is missing or rejected. Providers differ
    #: in how a key is obtained, and "401" on its own helps nobody.
    token_help: str = ""
    discovery: DiscoveryPolicy = field(default_factory=DiscoveryPolicy)
    generation: GenerationPolicy = field(default_factory=GenerationPolicy)

    def token(self) -> str:
        """Read the API token, with an error message that says what to do."""
        value = os.environ.get(self.token_env, "").strip()
        if not value:
            raise RuntimeError(
                f"{self.token_env} is not set for provider '{self.name}'."
                + (f" {self.token_help}" if self.token_help else "")
            )
        return value

    def has_token(self) -> bool:
        return bool(os.environ.get(self.token_env, "").strip())


@dataclass(frozen=True)
class Policy:
    """Every configured provider, in the order ``models.yaml`` lists them."""

    providers: tuple[Provider, ...] = ()

    def get(self, name: str) -> Provider:
        for provider in self.providers:
            if provider.name == name:
                return provider
        known = ", ".join(provider.name for provider in self.providers) or "none configured"
        raise RuntimeError(f"Unknown provider '{name}'. Configured in models.yaml: {known}.")

    def resolve(self, names: str | None) -> list[Provider]:
        """Turn a comma-separated ``--providers`` value into providers.

        With no names, every provider that has a token. A provider configured
        but not credentialled is skipped rather than failing the run: the point
        of several providers is that one can be unavailable.
        """
        if names:
            return [self.get(name.strip()) for name in names.split(",") if name.strip()]

        usable = [provider for provider in self.providers if provider.has_token()]
        if not usable:
            missing = ", ".join(provider.token_env for provider in self.providers)
            raise RuntimeError(
                f"No provider has a token. Set one of: {missing} (see .env.example)."
            )
        return usable


def _discovery(raw: dict) -> DiscoveryPolicy:
    return DiscoveryPolicy(
        exclude=tuple(re.compile(pattern, re.IGNORECASE) for pattern in raw.get("exclude", [])),
        exclude_aliases=bool(raw.get("exclude_aliases", True)),
        aliases=dict(raw.get("aliases") or {}),
        max_models=int(raw.get("max_models", 20)),
    )


def _generation(raw: dict, defaults: GenerationPolicy) -> GenerationPolicy:
    """Provider-level generation settings, falling back to the shared block.

    Rate limits belong to a provider, not to the benchmark, so a slow endpoint
    can be given a lower concurrency without changing anyone else's.
    """
    return replace(
        defaults,
        **{
            field_name: type(getattr(defaults, field_name))(raw[field_name])
            for field_name in GenerationPolicy.__dataclass_fields__
            if field_name in raw
        },
    )


def load_policy(path: Path | None = None) -> Policy:
    """Read ``models.yaml`` into a :class:`Policy`."""
    path = path or DEFAULT_POLICY_PATH
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    defaults = _generation(raw.get("generation") or {}, GenerationPolicy())

    providers = []
    for entry in raw.get("providers") or []:
        env_url = os.environ.get(entry.get("base_url_env", ""), "").strip()
        providers.append(
            Provider(
                name=entry["name"],
                base_url=env_url or entry["base_url"],
                token_env=entry["token_env"],
                token_help=entry.get("token_help", ""),
                discovery=_discovery(entry.get("discovery") or {}),
                generation=_generation(entry.get("generation") or {}, defaults),
            )
        )

    if not providers:
        raise RuntimeError(f"{path.name} configures no providers under 'providers:'.")
    return Policy(providers=tuple(providers))
