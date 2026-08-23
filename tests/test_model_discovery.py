"""Model discovery must survive e-INFRA renaming things underneath us.

Everything here runs offline against a recorded payload shape. No test in this
repository calls e-INFRA or the judge API.
"""

from __future__ import annotations

from tnb.config import DEFAULT_POLICY_PATH, load_policy
from tnb.providers.einfra import apply_policy, group_by_fingerprint, looks_like_alias

# The ids `GET /v1/models` actually returned on 2026-08-23.
SAMPLE_PAYLOAD = [
    {"id": model_id}
    for model_id in (
        "agentic",
        "all-proxy-models",
        "auto-llm",
        "auto-llm-heuristic",
        "coder",
        "command-a",
        "deepseek",
        "deepseek-thinking",
        "deepseek-v4-flash",
        "deepseek-v4-flash-thinking",
        "gemma4",
        "glm",
        "glm-5",
        "glm-5.2",
        "gpt-oss-120b",
        "kimi",
        "kimi-k3",
        "mini",
        "mistral-medium-3.5",
        "multilingual-e5-large-instruct",
        "mxbai-embed-large:latest",
        "nomic-embed-text-v1.5",
        "nomic-embed-text-v2-moe",
        "qwen3-embedding-4b",
        "qwen3-reranker-4b",
        "qwen3.5",
        "qwen3.5-122b",
        "qwen3.5-int4",
        "qwen3.8-27b",
        "thinker",
        "whisper-large-v3",
    )
]

EXPECTED_BENCHMARK_SET = {
    "deepseek-v4-flash",
    "deepseek-v4-flash-thinking",
    "gemma4",
    "glm-5",
    "glm-5.2",
    "gpt-oss-120b",
    "kimi-k3",
    "mistral-medium-3.5",
    "qwen3.5-122b",
    "qwen3.5-int4",
    "qwen3.8-27b",
}


def _classify() -> dict[str, str | None]:
    policy = load_policy(DEFAULT_POLICY_PATH)
    return {m.id: m.excluded_by for m in apply_policy(SAMPLE_PAYLOAD, policy.discovery)}


def test_benchmark_set_matches_the_live_endpoint():
    """The 31 ids e-INFRA reported reduce to 11 distinct benchmarkable models."""
    verdicts = _classify()
    included = {model_id for model_id, reason in verdicts.items() if reason is None}
    assert included == EXPECTED_BENCHMARK_SET


def test_non_generative_models_are_dropped():
    verdicts = _classify()
    for model_id in (
        "whisper-large-v3",
        "nomic-embed-text-v1.5",
        "qwen3-embedding-4b",
        "qwen3-reranker-4b",
        "multilingual-e5-large-instruct",
    ):
        assert verdicts[model_id] is not None, f"{model_id} cannot write a note"


def test_verified_duplicates_name_what_they_resolve_to():
    """Fingerprinting proved these are the same model behind two names, so the
    exclusion reason says which one rather than just 'alias'."""
    verdicts = _classify()
    assert verdicts["deepseek"] == "alias:deepseek-v4-flash"
    assert verdicts["mini"] == "alias:gpt-oss-120b"
    assert verdicts["qwen3.5"] == "alias:qwen3.5-int4"
    assert verdicts["thinker"] == "alias:deepseek-v4-flash-thinking"


def test_command_a_is_gemma4_despite_its_name():
    """`command-a` reads like Cohere Command A but returns gemma4's exact output.
    Benchmarking both would have put one model in the table twice."""
    assert _classify()["command-a"] == "alias:gemma4"


def test_unversioned_names_are_dropped_even_when_not_duplicates():
    """`glm` answers differently from both glm-5 and glm-5.2, so it is a real
    model — but the name will point somewhere else after the next deployment."""
    verdicts = _classify()
    for name in ("glm", "kimi", "coder", "agentic", "deepseek-thinking"):
        assert verdicts[name] == "alias:unversioned"


def test_versioned_siblings_are_kept_apart():
    """glm-5 and glm-5.2 fingerprint differently and are two separate rows."""
    verdicts = _classify()
    assert verdicts["glm-5"] is None
    assert verdicts["glm-5.2"] is None


def test_exclusion_reason_is_recorded_not_swallowed():
    """A model that vanishes from the table must be explainable."""
    assert _classify()["whisper-large-v3"].startswith("exclude:")


def test_unknown_future_model_is_included_by_default():
    """The whole point: a model nobody has heard of yet still gets benchmarked."""
    verdicts = {
        m.id: m.excluded_by
        for m in apply_policy(
            [{"id": "glm-5.3"}, {"id": "DeepSeek-V5"}],
            load_policy(DEFAULT_POLICY_PATH).discovery,
        )
    }
    assert verdicts == {"glm-5.3": None, "DeepSeek-V5": None}


def test_alias_heuristic_keeps_versioned_ids():
    assert looks_like_alias("glm")
    assert looks_like_alias("deepseek")
    assert not looks_like_alias("glm-5.2")
    assert not looks_like_alias("gemma4")
    assert not looks_like_alias("gpt-oss-120b")


def test_fingerprint_grouping_prefers_the_versioned_id():
    """A leaderboard row must name a model that still means the same thing
    next month, so the versioned id wins as canonical."""
    groups = group_by_fingerprint(
        {
            "gemma4": "aaaa1111",
            "command-a": "aaaa1111",
            "auto-llm": "aaaa1111",
            "glm-5.2": "bbbb2222",
            "kimi-k3": "cccc3333",
            "qwen3-embedding-4b": "",  # could not chat
        }
    )
    assert groups == {"gemma4": ["auto-llm", "command-a"]}


def test_fingerprint_grouping_ignores_models_that_could_not_answer():
    assert group_by_fingerprint({"a": "", "b": ""}) == {}
