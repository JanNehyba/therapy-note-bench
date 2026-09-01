"""What the endpoints serve, against what the tables draw.

Two silences the page had no way to break. A model the endpoint has withdrawn
keeps its row forever: it cannot be generated again, scored again or measured
on anything added later, so its figures are frozen and read exactly like the
figures beside them, which are not. And a model the endpoint serves that has
never been asked is simply missing, which reads as a poor result rather than as
a question nobody put.

Measured on 2026-09-01: `qwen3.5-122b` appears 71 times in
`docs/leaderboard.json` and e-INFRA no longer serves it; `glm-5.3` and
`qwen3.8-flash-next` are served and `results/rows.jsonl` holds no row for
either.

The third case is the one that has to be got right rather than merely covered:
a provider this machine has no credential for is not a provider serving
nothing, and reporting its rows as withdrawn would invent a withdrawal out of
our own missing password.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.test_page_runs import _flat, _judges_payload, _row, _run
from tnb import judge, report


def _roster(**overrides) -> dict:
    return {
        "asked": "2026-09-01",
        "serves": {"einfra": ["gemma4", "glm-5.3"]},
        "unreachable": {},
        "withdrawn": [{"provider": "einfra", "system_id": "qwen3.5-122b"}],
        "never_asked": [{"provider": "einfra", "system_id": "glm-5.3"}],
        "exempt": ["therapist"],
        **overrides,
    }


def _data(roster: dict | None) -> dict:
    rows = [
        _row("qwen3.5-122b", judge.DEFAULT_MODEL, 0.55),
        _row("gemma4", judge.DEFAULT_MODEL, 0.45),
    ]
    data = report.build(rows, roster=roster)
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = _judges_payload()
    data["roster"] = roster
    return data


def test_a_withdrawn_model_is_marked_and_not_dropped(tmp_path: Path):
    drawn = _flat(_run(report.render_page(_data(_roster())), tmp_path, panel="table-host"))
    assert "qwen3.5-122b" in drawn, (
        "the row was removed; those measurements were made and deleting them "
        "publishes a smaller table than the evidence supports"
    )
    assert "withdrawn" in drawn, "a row nobody can ask again reads like every other row"
    assert "2026-09-01" in drawn, (
        "'no longer served' is only true as of a day, and the page gives none"
    )


def test_a_model_nobody_asked_is_named_as_a_question_not_a_result(tmp_path: Path):
    drawn = _flat(_run(report.render_page(_data(_roster())), tmp_path, panel="table-host"))
    assert "glm-5.3" in drawn, (
        "a model the endpoint serves and this benchmark has never asked is absent from the "
        "table, and an absent model reads as a bad result"
    )
    assert "question nobody put" in drawn


def test_a_provider_nobody_could_ask_is_named_and_its_rows_left_alone(tmp_path: Path):
    """Our missing password is not their withdrawal."""
    roster = _roster(
        serves={},
        unreachable={"einfra": "no EINFRA_API_TOKEN"},
        withdrawn=[],
        never_asked=[],
    )
    drawn = _flat(_run(report.render_page(_data(roster)), tmp_path, panel="table-host"))
    assert "could not be asked" in drawn, "a provider nobody reached is not mentioned at all"
    assert "withdrawn" not in drawn, (
        "rows were marked withdrawn because this machine had no credential for their endpoint"
    )


def test_no_roster_says_nothing_rather_than_that_everything_agrees(tmp_path: Path):
    """An absence of the check is not a clean bill."""
    drawn = _flat(_run(report.render_page(_data(None)), tmp_path, panel="table-host"))
    assert "withdrawn" not in drawn
    assert "never been asked" not in drawn and "could not be asked" not in drawn
    assert "qwen3.5-122b" in drawn, "the table stopped drawing rows when no roster was present"


def test_a_row_is_marked_only_where_the_roster_says_so():
    """The mark is a fact about one system, not a property of the table."""
    data = report.build(
        [_row("qwen3.5-122b", judge.DEFAULT_MODEL, 0.55), _row("gemma4", judge.DEFAULT_MODEL, 0.4)],
        roster=_roster(),
    )
    marked = {
        row["system_id"]: row.get("withdrawn_on")
        for table in data["tables"]
        for row in table["rows"]
    }
    assert marked["qwen3.5-122b"] == "2026-09-01"
    assert marked["gemma4"] is None, "a served model was marked as withdrawn"


def test_the_published_roster_never_reports_a_reference_row_as_withdrawn():
    """The therapist's note and TN-Eval's two are not served by any endpoint.

    They have no provider to be withdrawn from, and a comparison that forgot to
    exempt them would report all three as gone on the first run.
    """
    path = report.ROSTER_PATH
    if not path.exists():
        return
    roster = json.loads(path.read_text(encoding="utf-8"))
    gone = {entry["system_id"] for entry in roster.get("withdrawn", [])}
    for system in ("therapist", "llama-3.1-70b", "mistral-large-v2"):
        assert system not in gone, f"{system} is not served by any endpoint and cannot be withdrawn"
    assert set(roster.get("exempt", ())) >= {"therapist"}, (
        "the reference rows are not recorded as exempt, so a later reader cannot tell "
        "they were considered"
    )


def test_the_published_roster_and_the_published_tables_agree_about_what_is_marked():
    """The artefact and the page cannot drift: one is drawn from the other."""
    if not report.ROSTER_PATH.exists() or not report.DATA_PATH.exists():
        return
    roster = json.loads(report.ROSTER_PATH.read_text(encoding="utf-8"))
    payload = json.loads(report.DATA_PATH.read_text(encoding="utf-8"))
    gone = {entry["system_id"] for entry in roster.get("withdrawn", [])}
    marked = {
        row["system_id"]
        for table in payload["tables"]
        for row in table["rows"]
        if row.get("withdrawn_on")
    }
    drawn = {row["system_id"] for table in payload["tables"] for row in table["rows"]}
    assert marked == (gone & drawn), (
        f"the roster says {sorted(gone & drawn)} is withdrawn and the tables mark {sorted(marked)}"
    )


def test_one_endpoints_withdrawal_does_not_mark_another_endpoints_row():
    """`models.yaml` says the same id on two endpoints can be two builds.

    Nothing merges them anywhere else in this benchmark, and the mark was keyed
    on the id alone, so a withdrawal recorded against one provider would have
    stamped "withdrawn" on a row still being served by the other.
    """
    rows = [
        _row("shared-id", judge.DEFAULT_MODEL, 0.5, provider="einfra"),
        _row("shared-id", judge.DEFAULT_MODEL, 0.4, provider="openai"),
    ]
    data = report.build(
        rows, roster=_roster(withdrawn=[{"provider": "einfra", "system_id": "shared-id"}])
    )
    marked = {
        (row["provider"], row.get("withdrawn_on"))
        for table in data["tables"]
        for row in table["rows"]
    }
    assert ("einfra", "2026-09-01") in marked
    assert ("openai", None) in marked, (
        "the row from the endpoint that still serves this id was marked as withdrawn"
    )


def test_asking_nobody_is_not_a_clean_result(monkeypatch, capsys):
    """Exit 0 from a gate means the tables and the endpoints agree.

    A run that reached no provider has established nothing at all, and returning
    0 would let a publish proceed on the strength of a missing credential. An
    unreadable catalogue is not an empty catalogue.
    """
    import argparse

    from tnb import cli

    class _Provider:
        name = "einfra"
        token_env = "EINFRA_API_TOKEN"

        def has_token(self):
            return False

    class _Policy:
        providers = (_Provider(),)

    monkeypatch.setattr(cli, "load_policy", lambda: _Policy())
    code = cli.cmd_roster(argparse.Namespace(dry_run=True))
    assert code == 2, (
        f"returned {code}; 0 reads as 'the tables and the endpoints agree' and 1 reads as "
        "'they disagree', and neither was established"
    )
    assert "nothing is claimed" in capsys.readouterr().err
