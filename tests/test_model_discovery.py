"""Model discovery must survive e-INFRA renaming things underneath us.

Everything here runs offline against a recorded payload shape. No test in this
repository calls e-INFRA or the judge API.
"""

from __future__ import annotations

from tnb.config import DEFAULT_POLICY_PATH, load_policy
from tnb.providers.einfra import apply_policy, looks_like_alias

# Shaped like a real /v1/models response, using the ids the CERIT-SC docs listed
# on 2026-08-23 plus the moving aliases e-INFRA maintains alongside them.
SAMPLE_PAYLOAD = [
    {"id": "glm-5.2", "object": "model"},
    {"id": "DeepSeek-V4-Flash", "object": "model"},
    {"id": "kimi-k3", "object": "model"},
    {"id": "qwen3.5-int4", "object": "model"},
    {"id": "gpt-oss-120b", "object": "model"},
    {"id": "gemma4", "object": "model"},
    {"id": "mistral-medium-3.5", "object": "model"},
    {"id": "whisper-large-v3", "object": "model"},
    {"id": "nomic-embed-text", "object": "model"},
    {"id": "glm", "object": "model"},
    {"id": "kimi", "object": "model"},
    {"id": "deepseek", "object": "model"},
]


def _classify() -> dict[str, str | None]:
    policy = load_policy(DEFAULT_POLICY_PATH)
    return {m.id: m.excluded_by for m in apply_policy(SAMPLE_PAYLOAD, policy.discovery)}


def test_generative_models_are_benchmarked():
    verdicts = _classify()
    for model_id in ("glm-5.2", "DeepSeek-V4-Flash", "kimi-k3", "gpt-oss-120b", "gemma4"):
        assert verdicts[model_id] is None, f"{model_id} should be benchmarked"


def test_non_generative_models_are_dropped():
    verdicts = _classify()
    assert verdicts["whisper-large-v3"] is not None
    assert verdicts["nomic-embed-text"] is not None


def test_moving_aliases_are_dropped():
    """An alias points at a different model over time, so a row for it would
    silently compare two models across runs."""
    verdicts = _classify()
    for alias in ("glm", "kimi", "deepseek"):
        assert verdicts[alias] == "alias:unversioned"


def test_alias_heuristic_keeps_versioned_ids():
    assert looks_like_alias("glm")
    assert looks_like_alias("deepseek")
    assert not looks_like_alias("glm-5.2")
    assert not looks_like_alias("gemma4")
    assert not looks_like_alias("gpt-oss-120b")


def test_exclusion_reason_is_recorded_not_swallowed():
    """A model that vanishes from the table must be explainable."""
    verdicts = _classify()
    assert verdicts["whisper-large-v3"].startswith("exclude:")


def test_unknown_future_model_is_included_by_default():
    """The whole point: a model nobody has heard of yet still gets benchmarked."""
    verdicts = {
        m.id: m.excluded_by
        for m in apply_policy(
            [{"id": "glm-5.3"}, {"id": "DeepSeek-V4"}],
            load_policy(DEFAULT_POLICY_PATH).discovery,
        )
    }
    assert verdicts == {"glm-5.3": None, "DeepSeek-V4": None}
