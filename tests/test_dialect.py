"""Providers disagree about how the same request is spelled.

Every backend here speaks the OpenAI chat-completions shape and each one of
these differences is a 400 from a live endpoint rather than a warning, so the
request body is built by a function that can be checked without a network call.

The values are not guesses. They were established by sending the request and
reading what came back — including the verbatim refusal quoted below.
"""

from __future__ import annotations

from dataclasses import replace

from tnb.config import Dialect, GenerationPolicy, Provider, load_policy
from tnb.providers.openai_compatible import build_request


def _provider(**generation) -> Provider:
    return Provider(
        name="test",
        base_url="https://example.invalid/v1",
        token_env="TEST_TOKEN",
        generation=replace(GenerationPolicy(), **generation),
    )


def test_the_default_dialect_is_what_e_infra_already_accepts():
    """An existing stanza must need no dialect block to keep working."""
    body = build_request(_provider(temperature=0.0, max_tokens=4096), "m", "hi", 4096)

    assert body["max_tokens"] == 4096
    assert body["temperature"] == 0.0
    assert "max_completion_tokens" not in body
    assert "reasoning_effort" not in body


def test_openai_reasoning_models_want_max_completion_tokens():
    """`max_tokens` is rejected outright by that family."""
    provider = _provider(dialect=Dialect(max_tokens_field="max_completion_tokens"))

    body = build_request(provider, "gpt-5.6-luna", "hi", 4096)

    assert body["max_completion_tokens"] == 4096
    assert "max_tokens" not in body


def test_a_provider_that_forces_its_temperature_is_sent_none_at_all():
    """Omitted, not defaulted.

    OpenAI's refusal is verbatim: "Unsupported value: 'temperature' does not
    support 0 with this model. Only the default (1) value is supported." It
    rejects the field, not merely the value, so sending `temperature: 1` is not
    a workaround — the field has to be absent.
    """
    provider = _provider(temperature=0.0, dialect=Dialect(send_temperature=False))

    body = build_request(provider, "gpt-5.6-luna", "hi", 4096)

    assert "temperature" not in body


def test_the_row_records_the_temperature_that_was_actually_used():
    """1, not the 0 that was configured and refused.

    A model generated at a different temperature is a differently-configured
    system. Recording the requested value would make the caveat on the page a
    lie in the one place it matters.
    """
    forced = _provider(temperature=0.0, dialect=Dialect(send_temperature=False))
    ordinary = _provider(temperature=0.0)

    assert forced.generation.effective_temperature == 1.0
    assert ordinary.generation.effective_temperature == 0.0


def test_effort_is_sent_only_where_the_provider_has_the_control():
    provider = _provider(effort="medium", dialect=Dialect(effort_field="reasoning_effort"))

    assert build_request(provider, "gpt-5.6-luna", "hi", 4096)["reasoning_effort"] == "medium"


def test_effort_configured_without_a_field_to_put_it_in_is_not_smuggled_through():
    """e-INFRA has no such control; inventing a field would 400 the whole run."""
    provider = _provider(effort="medium")

    assert "reasoning_effort" not in build_request(provider, "m", "hi", 4096)
    assert "effort" not in build_request(provider, "m", "hi", 4096)


def test_a_field_with_no_effort_set_is_left_off():
    provider = _provider(dialect=Dialect(effort_field="reasoning_effort"))

    assert "reasoning_effort" not in build_request(provider, "m", "hi", 4096)


def test_the_prompt_still_goes_as_one_user_turn():
    """Both source papers prompt this way and the dialect must not change it."""
    body = build_request(_provider(), "m", "write a note", 4096)

    assert body["messages"] == [{"role": "user", "content": "write a note"}]
    assert "system" not in {message["role"] for message in body["messages"]}


# --- how a stanza reaches the dialect ----------------------------------------


def test_a_dialect_block_overrides_only_the_fields_it_names(tmp_path):
    """Nested, so a provider that changes one field keeps the shared rest."""
    (tmp_path / "models.yaml").write_text(
        "generation:\n"
        "  temperature: 0.0\n"
        "  max_tokens: 4096\n"
        "providers:\n"
        "  - name: openai\n"
        "    base_url: https://api.openai.com/v1\n"
        "    token_env: OPENAI_API_KEY\n"
        "    generation:\n"
        "      effort: medium\n"
        "      dialect:\n"
        "        max_tokens_field: max_completion_tokens\n"
        "        send_temperature: false\n"
        "        effort_field: reasoning_effort\n",
        encoding="utf-8",
    )

    provider = load_policy(tmp_path / "models.yaml").providers[0]

    assert provider.generation.dialect.max_tokens_field == "max_completion_tokens"
    assert provider.generation.dialect.send_temperature is False
    assert provider.generation.dialect.effort_field == "reasoning_effort"
    # Inherited, not reset by the presence of the block.
    assert provider.generation.dialect.forced_temperature == 1.0
    assert provider.generation.max_tokens == 4096


def test_the_existing_stanza_is_unchanged_by_all_of_this():
    """e-INFRA declares no dialect and must behave exactly as before."""
    einfra = next(p for p in load_policy().providers if p.name == "einfra")

    assert einfra.generation.dialect == Dialect()
    assert einfra.generation.effort == ""
    assert einfra.generation.effective_temperature == einfra.generation.temperature
    assert "max_tokens" in build_request(einfra, "m", "hi", 4096)
