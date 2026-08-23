"""Discovery against the e-INFRA CZ OpenAI-compatible endpoint.

The live ``GET /v1/models`` response is the only authority on what can be
benchmarked. Documentation drifts; aliases move. Everything here exists to turn
that response into a reproducible benchmark set without ever pinning a list.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from tnb.config import DiscoveryPolicy, Policy


@dataclass(frozen=True)
class DiscoveredModel:
    """One model as the endpoint reported it, plus why we kept or dropped it."""

    id: str
    raw: dict
    excluded_by: str | None = None

    @property
    def included(self) -> bool:
        return self.excluded_by is None


def looks_like_alias(model_id: str) -> bool:
    """Heuristic for e-INFRA's moving aliases (``glm``, ``kimi``, ``deepseek``).

    Those aliases carry no version marker, which is exactly what makes them
    unusable in a leaderboard: the model behind the name changes silently, so a
    row labelled ``glm`` would compare two different models across runs.
    Concrete ids always carry a digit somewhere (``glm-5.2``, ``gemma4``,
    ``gpt-oss-120b``), so "no digit" is a reliable enough signal. Anything this
    heuristic gets wrong can be corrected with ``alias_ids`` in models.yaml.
    """
    return not any(char.isdigit() for char in model_id)


def fetch_models(policy: Policy, *, timeout: float = 30.0) -> list[dict]:
    """Fetch the raw ``/v1/models`` payload. Raises on auth or network failure."""
    response = httpx.get(
        f"{policy.base_url.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {policy.token()}"},
        timeout=timeout,
    )
    if response.status_code == 401:
        raise RuntimeError(
            "e-INFRA rejected the token (401). Check EINFRA_API_TOKEN; keys are "
            "issued per account at https://chat.ai.e-infra.cz -> Account -> API keys."
        )
    response.raise_for_status()
    return list(response.json().get("data", []))


def apply_policy(raw_models: list[dict], discovery: DiscoveryPolicy) -> list[DiscoveredModel]:
    """Classify every reported model as included or excluded, and say why.

    Exclusions are recorded rather than silently dropped: a run record that says
    which models were skipped, and on what rule, is the difference between
    "nothing was deployed" and "we filtered it out".
    """
    results: list[DiscoveredModel] = []
    for entry in raw_models:
        model_id = entry.get("id", "")
        if not model_id:
            continue

        reason: str | None = None
        for pattern in discovery.exclude:
            if pattern.search(model_id):
                reason = f"exclude:{pattern.pattern}"
                break

        if reason is None and model_id in discovery.alias_ids:
            reason = "alias:listed"
        if reason is None and discovery.exclude_aliases and looks_like_alias(model_id):
            reason = "alias:unversioned"

        results.append(DiscoveredModel(id=model_id, raw=entry, excluded_by=reason))

    return sorted(results, key=lambda model: model.id.lower())


def discover(policy: Policy) -> list[DiscoveredModel]:
    """Fetch and classify in one step."""
    return apply_policy(fetch_models(policy), policy.discovery)
