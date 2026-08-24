"""Several providers, and the thing that goes wrong when you forget them.

A model id is only unique inside one endpoint. Two providers serving
`qwen3.5-122b` can be serving two different builds — a different quantisation,
different weights, a different system prompt — so the provider is part of a
model's identity here, in the cache path and in the result row. Merging them
would put two models under one name and nobody would see it.
"""

from __future__ import annotations

import pytest

from tnb import generation, results
from tnb.config import DEFAULT_POLICY_PATH, GenerationPolicy, Provider, load_policy
from tnb.datasets.base import Session, Turn
from tnb.providers import openai_compatible as client
from tnb.tasks import TASKS

SESSION = Session(id="7", source="tneval", turns=(Turn("therapist", "How was your week?"),))
NOTE = '{"Subjective": "s", "Objective": "o", "Assessment": "a", "Plan": "p"}'


def _provider(name: str, **overrides) -> Provider:
    base = {
        "name": name,
        "base_url": f"https://{name}.invalid/v1",
        "token_env": f"{name.upper()}_TOKEN",
        "generation": GenerationPolicy(concurrency=1),
    }
    return Provider(**{**base, **overrides})


def _job(provider: str, model_id: str = "qwen3.5-122b") -> generation.Job:
    return next(iter(generation.build_jobs(provider, [model_id], TASKS["soap"], [SESSION])))


# --- configuration ----------------------------------------------------------


def test_the_shipped_policy_configures_einfra():
    einfra = load_policy(DEFAULT_POLICY_PATH).get("einfra")
    assert einfra.base_url.startswith("https://")
    assert einfra.token_env == "EINFRA_API_TOKEN"
    assert einfra.discovery.aliases["command-a"] == "gemma4"


def test_a_provider_inherits_the_shared_generation_block_and_may_override_it():
    """Rate limits belong to an endpoint, not to the benchmark."""
    einfra = load_policy(DEFAULT_POLICY_PATH).get("einfra")
    assert einfra.generation.max_tokens == 4096, "inherited from the shared block"
    assert einfra.generation.concurrency == 2, "set on the provider"


def test_an_unknown_provider_name_says_what_is_configured():
    with pytest.raises(RuntimeError, match="Unknown provider"):
        load_policy(DEFAULT_POLICY_PATH).get("nope")


def test_a_provider_without_a_token_is_skipped_rather_than_fatal(monkeypatch):
    """The point of several providers is that one can be unavailable."""
    from tnb.config import Policy

    monkeypatch.setenv("A_TOKEN", "set")
    monkeypatch.delenv("B_TOKEN", raising=False)
    policy = Policy(providers=(_provider("a"), _provider("b")))

    assert [provider.name for provider in policy.resolve(None)] == ["a"]


def test_no_token_anywhere_names_the_variables_to_set(monkeypatch):
    from tnb.config import Policy

    monkeypatch.delenv("A_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="A_TOKEN"):
        Policy(providers=(_provider("a"),)).resolve(None)


def test_a_missing_token_error_says_where_to_get_one(monkeypatch):
    monkeypatch.delenv("A_TOKEN", raising=False)
    provider = _provider("a", token_help="Get one at https://example.org.")
    with pytest.raises(RuntimeError, match="https://example.org"):
        provider.token()


# --- identity ---------------------------------------------------------------


def test_the_same_model_id_on_two_providers_is_two_rows():
    """Not one row that silently averages two different builds."""
    rows = [
        results.Row(
            track=results.TRACK_TNEVAL,
            system_id="qwen3.5-122b",
            system_type="model",
            provider=name,
            prompt_version="tneval-soap-v1",
            n_sessions_attempted=50,
        )
        for name in ("einfra", "some-other-host")
    ]
    assert rows[0].row_id != rows[1].row_id
    assert len(results.latest(rows)) == 2


def test_two_providers_still_share_one_table():
    """Comparing them is the point; only their identity differs, not their
    comparability. Same protocol, same prompt version, same judge."""
    rows = [
        results.Row(
            track=results.TRACK_TNEVAL,
            system_id="qwen3.5-122b",
            system_type="model",
            provider=name,
            prompt_version="tneval-soap-v1",
            n_sessions_attempted=50,
        )
        for name in ("einfra", "some-other-host")
    ]
    assert len(results.comparable_groups(rows)) == 1


def test_a_row_written_before_providers_existed_still_loads():
    """results/ is append-only: the old `einfra-model` type is translated on the
    way in rather than edited on disk."""
    row = results.from_dict(
        {
            "track": results.TRACK_TNEVAL,
            "system_id": "gemma4",
            "system_type": "einfra-model",
            "n_sessions_attempted": 50,
        }
    )
    assert row.system_type == "model"


# --- the cache --------------------------------------------------------------


def test_two_providers_do_not_share_a_cache_file(tmp_path, monkeypatch):
    """The failure this prevents: one provider's notes overwriting another's,
    leaving a benchmark that silently measured the wrong endpoint."""
    monkeypatch.setattr(generation, "CACHE_DIR", tmp_path / "generations")
    first, second = _job("einfra"), _job("some-other-host")

    assert first.path() != second.path()
    assert "einfra" in first.path().parts
    assert "some-other-host" in second.path().parts


def test_a_note_from_one_provider_is_not_a_cache_hit_for_another(tmp_path, monkeypatch):
    monkeypatch.setattr(generation, "CACHE_DIR", tmp_path / "generations")
    monkeypatch.setattr(
        client,
        "complete",
        lambda provider, model, prompt: client.Completion(
            model=model, text=NOTE, ok=True, finish_reason="stop"
        ),
    )
    einfra, other = _provider("einfra"), _provider("some-other-host")

    assert generation.run_job(_job("einfra"), einfra).status == "generated"
    assert generation.run_job(_job("einfra"), einfra).status == "cached"
    assert generation.run_job(_job("some-other-host"), other).status == "generated"


def test_the_request_digest_separates_providers():
    """Even at identical prompt, model and budget: a different endpoint is a
    different experiment."""
    einfra, other = _provider("einfra"), _provider("some-other-host")
    assert generation.request_digest("qwen3.5-122b", "prompt", einfra) != generation.request_digest(
        "qwen3.5-122b", "prompt", other
    )


def test_indexing_keeps_the_providers_apart(tmp_path, monkeypatch):
    monkeypatch.setattr(generation, "CACHE_DIR", tmp_path / "generations")
    monkeypatch.setattr(
        client,
        "complete",
        lambda provider, model, prompt: client.Completion(
            model=model, text=NOTE, ok=True, finish_reason="stop"
        ),
    )
    for name in ("einfra", "some-other-host"):
        generation.run_job(_job(name), _provider(name))

    rows = results.index_generations(tmp_path / "generations")
    assert sorted(row.provider for row in rows) == ["einfra", "some-other-host"]
    assert {row.system_id for row in rows} == {"qwen3.5-122b"}


def test_the_old_cache_layout_is_refused_with_the_move_that_fixes_it(tmp_path, monkeypatch):
    """A cache written before providers had their own level looks empty to the
    new code. Re-generating 8000 notes to fix a rename is not acceptable, so it
    stops and prints the move instead."""
    monkeypatch.setattr(generation, "CACHE_DIR", tmp_path / "generations")
    (tmp_path / "generations" / "soap").mkdir(parents=True)

    with pytest.raises(RuntimeError, match="mv generations/soap"):
        generation.check_cache_layout()


def test_a_provider_shaped_cache_passes_the_check(tmp_path, monkeypatch):
    monkeypatch.setattr(generation, "CACHE_DIR", tmp_path / "generations")
    (tmp_path / "generations" / "einfra" / "soap").mkdir(parents=True)
    generation.check_cache_layout()
