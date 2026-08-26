"""A row says how the model was asked, and two settings are two rows.

`GenerationPolicy.effort` carried a docstring claiming *"Part of a system's
identity: the same model at two efforts produces two rows, never an average of
both under one name"* while being in neither `IDENTITY_KEYS` nor
`request_digest`. Switching effort would have returned the old notes from cache
under an unchanged `row_id` and folded two instruments into one line, silently.

These tests are the claim, executed.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from tnb import results
from tnb.config import Dialect, GenerationPolicy, Provider
from tnb.generation import request_digest
from tnb.results import Row, Settings


def _provider(name: str = "test", **generation) -> Provider:
    return Provider(
        name=name,
        base_url="https://example.invalid/v1",
        token_env="TEST_TOKEN",
        generation=replace(GenerationPolicy(), **generation),
    )


def _row(**kwargs) -> Row:
    base = {
        "track": results.TRACK_TNEVAL,
        "system_id": "a-model",
        "system_type": "model",
        "n_sessions_attempted": 50,
    }
    # A row that names a judge and not the judge's settings is withdrawn from
    # the tables rather than drawn, so a fixture that names one gets one -- as
    # every row the scorer writes does. These tests are about the *generation*
    # settings column and would otherwise fail for an unrelated reason.
    if kwargs.get("judge_model") and "judge_settings" not in kwargs:
        kwargs = {**kwargs, "judge_settings": {"model": kwargs["judge_model"]}}
    return Row(**{**base, **kwargs})


# --- the cache key -----------------------------------------------------------


def test_two_efforts_are_two_cache_entries():
    """The defect, stated directly: switching effort must not hit the old cache."""
    low = _provider(effort="low", dialect=Dialect(effort_field="reasoning_effort"))
    high = _provider(effort="high", dialect=Dialect(effort_field="reasoning_effort"))

    assert request_digest("m", "a prompt", low) != request_digest("m", "a prompt", high)


def test_a_provider_with_no_effort_control_keeps_its_existing_keys():
    """8 030 notes were already generated. Adding this field must not orphan them.

    The key is built so an absent effort contributes nothing at all rather than
    an empty string, which is both truthful and what keeps every e-INFRA digest
    byte-identical to the one in its cached record.
    """
    plain = _provider()
    expected = request_digest.__wrapped__ if hasattr(request_digest, "__wrapped__") else None
    assert expected is None  # not memoised; the check below is the real one

    import hashlib
    import json

    before = hashlib.sha256(
        json.dumps(
            {
                "provider": "test",
                "model": "m",
                "prompt": "a prompt",
                "temperature": 0.0,
                "max_tokens": plain.generation.max_tokens,
                "escalate_max_tokens": plain.generation.escalate_max_tokens,
            },
            sort_keys=True,
            ensure_ascii=False,
        ).encode()
    ).hexdigest()

    assert request_digest("m", "a prompt", plain) == before


def test_the_key_records_the_temperature_that_was_sent():
    """OpenAI refuses 0 and substitutes 1. The key must say 1."""
    forced = _provider(temperature=0.0, dialect=Dialect(send_temperature=False))
    honest = _provider(temperature=1.0)

    assert request_digest("m", "p", forced) == request_digest("m", "p", honest)


# --- the row identity --------------------------------------------------------


def test_two_efforts_are_two_rows():
    assert "effort" in results.IDENTITY_KEYS
    low = _row(settings=Settings(effort="low"))
    high = _row(settings=Settings(effort="high"))

    assert low.row_id != high.row_id


def test_two_efforts_still_share_one_table():
    """Different rows, same table: comparing them is the interesting part."""
    assert "effort" not in results.COMPARABILITY_KEYS
    low = _row(settings=Settings(effort="low"))
    high = _row(settings=Settings(effort="high"))

    assert low.comparability_key() == high.comparability_key()
    assert len(results.comparable_groups([low, high])) == 1


def test_the_newer_row_does_not_supersede_the_other_effort():
    """`latest` supersedes by identity, and these are two identities."""
    low = _row(settings=Settings(effort="low"), scored_at="2026-01-01T00:00:00Z")
    high = _row(settings=Settings(effort="high"), scored_at="2026-01-02T00:00:00Z")

    assert len(results.latest([low, high])) == 2


# --- what the row says -------------------------------------------------------


def test_a_row_round_trips_its_settings():
    row = _row(settings=Settings(effort="medium", temperature=1.0, temperature_forced=True))

    restored = results.from_dict(row.to_dict())

    assert restored.settings == row.settings
    assert restored.row_id == row.row_id


def test_a_row_written_before_settings_existed_still_loads():
    """`results/` is append-only; every older row has no settings block."""
    legacy = {
        "track": results.TRACK_TNEVAL,
        "system_id": "old",
        "system_type": "model",
        "n_sessions_attempted": 50,
    }

    row = results.from_dict(legacy)

    assert row.settings.is_empty()
    assert row.settings.summary == ""


def test_the_summary_says_when_the_provider_forced_the_temperature():
    """The caveat is only truthful if it names what actually happened."""
    forced = Settings(effort="medium", temperature=1.0, temperature_forced=True, max_tokens=4096)

    assert "forced by the provider" in forced.summary
    assert "temperature 1" in forced.summary
    assert "effort medium" in forced.summary

    ordinary = Settings(temperature=0.0, max_tokens=4096)
    assert "forced" not in ordinary.summary


def test_notes_written_under_two_settings_report_none_rather_than_one():
    """No single answer is better than an answer true of half the evidence."""
    from tnb.results import _settings_from

    disagreeing = {("low", 0.0, False), ("high", 0.0, False)}
    assert _settings_from(disagreeing, {4096}).is_empty()

    agreeing = {("low", 0.0, False)}
    assert _settings_from(agreeing, {4096, 16384}).max_tokens == 16384


# --- what the page shows -----------------------------------------------------


def test_the_page_gets_the_effort_and_the_mark():
    from tnb import report

    scored = results.Metrics(headline={"completeness": 0.5})
    table = report.build(
        [
            _row(
                system_id="gpt",
                provider="openai",
                judge_model="j",
                judge_prompt_version="v",
                prompt_version="tneval-soap-v1",
                metrics=scored,
                settings=Settings(effort="medium", temperature=1.0, temperature_forced=True),
            ),
            _row(
                system_id="local",
                provider="einfra",
                judge_model="j",
                judge_prompt_version="v",
                prompt_version="tneval-soap-v1",
                metrics=scored,
                settings=Settings(temperature=0.0),
            ),
        ]
    )["tables"][0]

    assert table["has_effort"] is True
    by_id = {row["system_id"]: row for row in table["rows"]}
    assert by_id["gpt"]["effort"] == "medium"
    assert by_id["gpt"]["settings_differ"] is True
    assert by_id["local"]["effort"] == ""
    assert by_id["local"]["settings_differ"] is False


def test_the_effort_column_is_not_drawn_when_nobody_has_one():
    """A column of dashes reads as missing data, not as an absent control."""
    from tnb import report

    table = report.build(
        [
            _row(
                judge_model="j",
                judge_prompt_version="v",
                prompt_version="tneval-soap-v1",
                metrics=results.Metrics(headline={"completeness": 0.5}),
                settings=Settings(temperature=0.0),
            )
        ]
    )["tables"][0]

    assert table["has_effort"] is False


@pytest.mark.parametrize("field", ["effort", "settings", "settings_differ"])
def test_every_rendered_row_carries_the_settings_fields(field):
    from tnb import report

    data = report.build(results.load())
    for table in data["tables"]:
        for row in table["rows"]:
            assert field in row
