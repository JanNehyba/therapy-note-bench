"""The result row, which decides what the leaderboard is allowed to say.

`results/` is append-only, so a row written with the wrong shape cannot be fixed
later -- only superseded, leaving a stale table beside the good one. These tests
pin the two rules no renderer is allowed to reinvent: what may be compared with
what, and that a metric is never collapsed to one number.
"""

from __future__ import annotations

import json

import pytest

from tnb import generation, results
from tnb.config import GenerationPolicy, Provider
from tnb.datasets.base import Session, Turn
from tnb.providers import openai_compatible as einfra
from tnb.results import Metrics, Row
from tnb.tasks import TASKS


def _row(**overrides) -> Row:
    base = {
        "track": results.TRACK_TNEVAL,
        "system_id": "gemma4",
        "system_type": "model",
        "prompt_version": "tneval-soap-v1",
        "n_sessions_attempted": 50,
        "n_sessions_generated": 50,
    }
    return Row(**{**base, **overrides})


# --- the shape --------------------------------------------------------------


def test_a_row_survives_a_round_trip(tmp_path):
    path = tmp_path / "rows.jsonl"
    written = _row(metrics=Metrics(headline={"completeness": 0.61}))
    results.append([written], path)

    (read_back,) = results.load(path)
    assert read_back == written
    assert read_back.row_id == written.row_id


def test_appending_never_rewrites(tmp_path):
    """The file is the history. A second run adds a line; it does not edit one."""
    path = tmp_path / "rows.jsonl"
    results.append([_row()], path)
    results.append([_row(n_sessions_generated=42)], path)

    assert len(path.read_text(encoding="utf-8").strip().splitlines()) == 2
    assert len(results.load(path)) == 2


def test_the_newest_row_wins_when_rendering(tmp_path):
    """Both stay in the file; the table shows today's number."""
    path = tmp_path / "rows.jsonl"
    results.append([_row(n_sessions_generated=50)], path)
    results.append([_row(n_sessions_generated=42)], path)

    (current,) = results.latest(results.load(path))
    assert current.n_sessions_generated == 42


def test_a_row_from_a_newer_harness_still_loads():
    """Append-only means an old checkout has to read a newer file, not crash."""
    payload = _row().to_dict() | {"a_field_from_the_future": True}
    assert results.from_dict(payload).system_id == "gemma4"


def test_a_typo_in_the_track_is_refused():
    """Silently accepting 'tneval' would create a second, invisible table."""
    with pytest.raises(ValueError, match="Unknown track"):
        _row(track="tneval")


def test_a_typo_in_the_system_type_is_refused():
    with pytest.raises(ValueError, match="Unknown system_type"):
        _row(system_type="human")


# --- what may be compared with what -----------------------------------------


def test_two_judges_never_share_a_table():
    """docs/methodology.md: changing the referee starts a new table rather than
    rewriting the old one."""
    groups = results.comparable_groups(
        [
            _row(judge_model="claude-opus-5", judge_prompt_version="v1"),
            _row(judge_model="some-other-judge", judge_prompt_version="v1"),
        ]
    )
    assert len(groups) == 2


def test_two_prompt_versions_never_share_a_table():
    groups = results.comparable_groups(
        [_row(prompt_version="tneval-soap-v1"), _row(prompt_version="tneval-soap-v2")]
    )
    assert len(groups) == 2


def test_the_two_tracks_are_never_one_ranking():
    """They measure different things on different scales; averaging them would
    throw away the disagreement the iCARE paper reports as a finding."""
    groups = results.comparable_groups(
        [_row(), _row(track=results.TRACK_ICARE, prompt_version="icare-zeroshot-v1")]
    )
    assert len(groups) == 2


def test_rows_that_agree_on_everything_do_share_a_table():
    groups = results.comparable_groups([_row(), _row(system_id="glm-5.2")])
    assert len(groups) == 1
    assert len(next(iter(groups.values()))) == 2


def test_an_unscored_row_and_a_scored_one_are_different_measurements():
    """A coverage row has no judge. It must not sit in the same ranking as a
    scored row and read as a model that scored zero."""
    groups = results.comparable_groups(
        [_row(), _row(judge_model="claude-opus-5", judge_prompt_version="v1")]
    )
    assert len(groups) == 2


# --- metrics are never one number -------------------------------------------


def test_a_row_with_no_metrics_is_valid():
    """This is what makes the page publishable before the judge has run."""
    row = _row()
    assert row.metrics.is_empty()
    assert not row.is_scored


def test_a_score_keeps_its_breakdown():
    """Both papers compute per section. Storing only the average would discard a
    breakdown the scoring pass already produced."""
    row = _row(
        metrics=Metrics(
            headline={"completeness": 0.61},
            by_section={"subjective": {"completeness": 0.66}, "plan": {"completeness": 0.40}},
            detail={"subjective-chief-complaint": 0.82},
        )
    )
    restored = results.from_dict(json.loads(json.dumps(row.to_dict())))

    assert restored.metrics.headline["completeness"] == 0.61
    assert restored.metrics.by_section["plan"]["completeness"] == 0.40
    assert restored.metrics.detail["subjective-chief-complaint"] == 0.82
    assert restored.is_scored


def test_a_published_number_carries_its_source_and_no_invented_detail():
    """A cell the paper did not print stays missing rather than becoming zero."""
    row = _row(
        system_id="mistral-large-v2",
        system_type="published",
        metrics=Metrics(headline={"completeness": 0.55}),
        source="TN-Eval, ACL 2025 Industry, Table 4",
    )
    assert row.metrics.by_section == {}
    assert row.source


# --- coverage rows from the generation cache --------------------------------

PROVIDER = Provider(
    name="einfra",
    base_url="https://example.invalid/v1",
    token_env="EINFRA_API_TOKEN",
    generation=GenerationPolicy(concurrency=1),
)
NOTE = '{"Subjective": "s", "Objective": "o", "Assessment": "a", "Plan": "p"}'


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(generation, "CACHE_DIR", tmp_path / "generations")
    return tmp_path / "generations"


def _generate(monkeypatch, model_id: str, session_ids: list[str], text: str = NOTE) -> None:
    monkeypatch.setattr(
        einfra,
        "complete",
        lambda provider, model, prompt: einfra.Completion(
            model=model,
            text=text,
            ok=bool(text),
            finish_reason="stop",
            error=None if text else "empty content",
        ),
    )
    sessions = [
        Session(id=sid, source="tneval", turns=(Turn("therapist", "Hi."),)) for sid in session_ids
    ]
    for job in generation.build_jobs("einfra", [model_id], TASKS["soap"], sessions):
        generation.run_job(job, PROVIDER)


def test_indexing_reports_one_row_per_model_and_track(cache, monkeypatch):
    _generate(monkeypatch, "gemma4", ["0", "1", "2"])
    _generate(monkeypatch, "glm-5.2", ["0", "1", "2"])

    rows = results.index_generations(cache)
    assert {row.system_id for row in rows} == {"gemma4", "glm-5.2"}
    assert all(row.track == results.TRACK_TNEVAL for row in rows)
    assert all(row.n_sessions_generated == 3 for row in rows)


def test_indexing_shows_a_model_that_lost_sessions_to_its_output_format(cache, monkeypatch):
    """gpt-oss-120b wrote good notes with a nested Plan and TN-Eval's parser
    could not read 8 of them. The table has to show 42/50, not a low score."""
    _generate(monkeypatch, "gpt-oss-120b", ["0", "1"], text="A nested {note: {a: 1}} answer")

    (row,) = results.index_generations(cache)
    assert row.n_sessions_attempted == 2
    assert row.n_sessions_generated == 0
    assert row.n_failed == 2
    assert "SOAP dictionary" in " ".join(row.failure_reasons)


def test_a_coverage_row_carries_no_judge_and_no_metrics(cache, monkeypatch):
    _generate(monkeypatch, "gemma4", ["0"])
    (row,) = results.index_generations(cache)

    assert row.judge_model is None
    assert row.metrics.is_empty()
    assert row.prompt_version == "tneval-soap-v1"


def test_indexing_an_empty_cache_says_nothing_rather_than_guessing(tmp_path):
    assert results.index_generations(tmp_path / "nothing") == []


# --- what must never reach a published file ---------------------------------


def test_a_providers_error_body_does_not_publish_its_key(monkeypatch):
    """e-INFRA's 429 quotes a hash of the API key that hit the limit, and
    results/ is committed. The reason is worth keeping; the identifier is not."""
    reason = results.normalise_reason(
        'HTTP429: {"error":{"message":"Rate limit exceeded for api_key: '
        "37583a3f93fcc1f6f5e489228f16a6ad204796cecd085e37395d66b7b3b062e2. "
        'Limit type: max_parallel_requests. Current limit: 4"}}'
    )
    assert "37583a3f" not in reason
    assert "Rate limit exceeded" in reason
    assert "max_parallel_requests" in reason


def test_normalising_keeps_two_identical_failures_countable():
    """Raw bodies carry request ids and reset timestamps, so every failure would
    look unique and the count would be meaningless."""
    first = results.normalise_reason("HTTP429: key abcdef0123456789abcdef, resets soon")
    second = results.normalise_reason("HTTP429: key 0123456789abcdef0123456789, resets soon")
    assert first == second


def test_a_missing_error_still_says_something():
    assert results.normalise_reason(None) == "unknown error"


# --- whose fault was it -------------------------------------------------------


@pytest.mark.parametrize(
    "error",
    [
        'HTTP429: {"error":{"message":"Rate limit exceeded for api_key: ..."}}',
        "HTTP503: upstream unavailable",
        "ReadTimeout: timed out",
        "ConnectError: connection refused",
    ],
)
def test_a_call_that_never_reached_the_model_is_not_the_models_fault(error):
    """glm-5 was published as "39/40, 1 unusable" over a rate limit.

    That is a fact about a shared academic endpoint refusing a fourth parallel
    request, and nothing at all about glm-5's ability to write a note. It is the
    same libel `to_rows` already guards against, arriving by a different route.
    """
    assert results.is_infrastructure_failure(error) is True


@pytest.mark.parametrize(
    "error",
    [
        "answer did not contain a SOAP dictionary",
        "empty content",
        "HTTP400: unsupported value",
        "",
        None,
    ],
)
def test_a_model_that_answered_badly_is_the_models_fault(error):
    """A 400 is us or the model, not the endpoint being busy. So is a bad shape."""
    assert results.is_infrastructure_failure(error) is False


def test_the_two_kinds_are_counted_separately(tmp_path):
    """A reader comparing scores has to know which kind of gap they are looking at."""
    model_dir = tmp_path / "einfra" / "icare" / "v1" / "a-model"
    for session, error in (("1", None), ("2", "empty content"), ("3", "HTTP429: rate limit")):
        unit = model_dir / session
        unit.mkdir(parents=True)
        (unit / "note.json").write_text(
            json.dumps({"ok": error is None, "error": error}), encoding="utf-8"
        )

    row = results.index_generations(tmp_path)[0]

    assert row.n_sessions_generated == 1
    assert list(row.failure_reasons) == ["empty content"], "the model's own failure"
    assert list(row.unreached_reasons) == ["HTTP429: rate limit"], "the endpoint's"
    assert row.unreached_reasons["HTTP429: rate limit"] == 1


def test_a_rate_limit_message_never_carries_the_key_to_the_page():
    """e-INFRA's 429 body quotes the API key back at us. It is gitignored where
    it lands, and redacted before it can reach anything published."""
    raw = (
        'HTTP429: {"error":{"message":"Rate limit exceeded for api_key: '
        "37583a3f93fcc1f6f5e489228f16a6ad204796cecd085e37395d66b7b3b062e2"
        '. Limit type: max_parallel_requests"}}'
    )

    cleaned = results.normalise_reason(raw)

    assert "37583a3f" not in cleaned
    assert "Rate limit exceeded" in cleaned, "the useful part survives"


def test_a_rate_limited_session_is_not_charged_to_the_model(tmp_path):
    """The count had to be split, not just the reasons.

    glm-5 was published as "39/40 (1 unusable)" over an e-INFRA rate limit. The
    first fix separated `failure_reasons` from `unreached_reasons` but left the
    infrastructure branch decrementing the same counter, so the accusation
    survived — and with an empty failure_reasons the page rendered it as
    "1 note missing, with no recorded reason".
    """
    model_dir = tmp_path / "einfra" / "icare" / "v1" / "glm-5"
    for session, error in (("1", None), ("2", "empty content"), ("3", "HTTP429: rate limit")):
        unit = model_dir / session
        unit.mkdir(parents=True)
        (unit / "note.json").write_text(
            json.dumps({"ok": error is None, "error": error}), encoding="utf-8"
        )

    row = results.index_generations(tmp_path)[0]

    assert row.n_sessions_attempted == 3
    assert row.n_sessions_generated == 1, "neither the failure nor the rate limit produced a note"
    assert row.n_failed == 1, "only the model's own failure"
    assert sum(row.unreached_reasons.values()) == 1
    assert list(row.failure_reasons) == ["empty content"]


def test_the_headline_denominator_reaches_the_row(tmp_path):
    """`n_partial` was computed in both tracks and had nowhere to go."""
    row = results.Row(
        track=results.TRACK_TNEVAL,
        system_id="m",
        system_type="model",
        n_sessions_attempted=50,
        n_sessions_scored=50,
        n_sessions_partial=7,
    )

    restored = results.from_dict(row.to_dict())

    assert restored.n_sessions_partial == 7, "a row must survive the round trip carrying it"
