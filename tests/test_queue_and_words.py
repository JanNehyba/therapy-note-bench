"""The page's account of what is written, what is waiting and how long the notes are.

Three defects an audit of 2026-09-02 found, each a sentence the page said
about a row that the rows themselves contradicted: a model with notes on disk
called "never asked"; a queue entry that hid the calls the endpoint never
answered; and an iCARE table with no Words column because a coverage row
counted words from a field that track never fills.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.test_page_runs import _flat, _judges_payload, _row, _run
from tnb import judge, report, results
from tnb.results import Metrics, Row, Settings
from tnb.tasks import icare


def _coverage(system: str, *, unreached: dict[str, int] | None = None) -> Row:
    """A row `index_generations` would write: notes on disk, nothing scored."""
    return Row(
        track=results.TRACK_TNEVAL,
        system_id=system,
        system_type="model",
        provider="einfra",
        prompt_version="tneval-soap-v1",
        n_sessions_attempted=50,
        n_sessions_generated=48,
        unreached_reasons=dict(unreached or {}),
    )


def _roster(**overrides) -> dict:
    return {
        "asked": "2026-09-01",
        "serves": {"einfra": ["gemma4", "glm-5.3", "qwen3.8-flash-next"]},
        "unreachable": {},
        "withdrawn": [],
        "never_asked": [
            {"provider": "einfra", "system_id": "glm-5.3"},
            {"provider": "einfra", "system_id": "qwen3.8-flash-next"},
        ],
        "exempt": ["therapist"],
        **overrides,
    }


def test_a_model_with_notes_on_disk_is_awaiting_the_judge_not_never_asked(tmp_path: Path):
    rows = [_row("gemma4", judge.DEFAULT_MODEL, 0.45), _coverage("glm-5.3")]
    data = report.build(rows, roster=_roster())

    assert [e["system_id"] for e in data["roster"]["awaiting_judge"]] == ["glm-5.3"]
    assert [e["system_id"] for e in data["roster"]["never_asked"]] == ["qwen3.8-flash-next"]

    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = _judges_payload()
    drawn = _flat(_run(report.render_page(data), tmp_path, panel="table-host"))
    assert "waiting for the judge" in drawn and "glm-5.3" in drawn
    assert "qwen3.8-flash-next" in drawn and "question nobody put" in drawn


def test_a_scored_model_is_not_named_by_the_roster_at_all():
    data = report.build(
        [_row("glm-5.3", judge.DEFAULT_MODEL, 0.5)],
        roster=_roster(never_asked=[{"provider": "einfra", "system_id": "glm-5.3"}]),
    )
    assert data["roster"]["never_asked"] == [] and data["roster"]["awaiting_judge"] == []


def test_the_queue_names_the_calls_the_endpoint_never_answered(tmp_path: Path):
    data = report.build([_coverage("glm-5.3", unreached={"HTTP 429": 2})])
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = _judges_payload()
    data["roster"] = None
    drawn = _flat(_run(report.render_page(data), tmp_path, panel="table-host"))
    assert "2 unreached" in drawn, "the queue hides the calls the endpoint refused"


def test_an_icare_coverage_row_counts_words_per_session(tmp_path: Path):
    """Seventeen records per session, each a section; the note's length is
    their sum, and the row's figure the median over sessions."""
    root = tmp_path / "einfra" / icare.NAME / icare.PROMPT_VERSION / "mymodel"
    for session, per_section in enumerate((3, 5, 40)):
        for unit in ("1", "2"):
            path = root / str(session)
            path.mkdir(parents=True, exist_ok=True)
            (path / f"{unit}.json").write_text(
                json.dumps(
                    {
                        "ok": True,
                        "generated_at": "2026-01-01T00:00:00Z",
                        "effort": "",
                        "temperature": 0,
                        "temperature_forced": False,
                        "max_tokens": 4096,
                        "text": " ".join(["w"] * per_section),
                    }
                ),
                encoding="utf-8",
            )

    settings = results.settings_by_system(tmp_path, track=results.TRACK_ICARE)
    assert settings[("einfra", "mymodel")].note_words == 10, "median of 6, 10 and 80"


def _icare_scored(system: str, rouge: float, words: int) -> Row:
    return Row(
        track=results.TRACK_ICARE,
        system_id=system,
        system_type="model",
        provider="einfra",
        prompt_version="icare-v1",
        judge_model=judge.DEFAULT_MODEL,
        judge_prompt_version="icare-trace-v1",
        judge_settings={"model": judge.DEFAULT_MODEL, "thinking_budget": 256},
        settings=Settings(note_words=words),
        n_sessions_attempted=40,
        n_sessions_generated=40,
        n_sessions_scored=40,
        metrics=Metrics(
            headline={
                "rouge_l": rouge,
                "bertscore": 0.8,
                "trace": 3.0,
                "temporal_past": 1.0,
                "temporal_next": 0.2,
            }
        ),
    )


def test_the_icare_table_prints_how_rouge_moves_with_length(tmp_path: Path):
    rows = [
        _icare_scored("a", 0.30, 100),
        _icare_scored("b", 0.25, 200),
        _icare_scored("c", 0.20, 300),
    ]
    data = report.build(rows)
    table = next(t for t in data["tables"] if t["track"] == results.TRACK_ICARE)
    assert table["has_words"]
    assert table["length_effects"]["rouge_l"] == {"rho": -1.0, "n": 3}

    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = _judges_payload()
    data["roster"] = None
    drawn = _flat(_run(report.render_page(data), tmp_path, panel="table-host"))
    assert "ROUGE-L falls as notes get longer" in drawn and "−1.00" in drawn.replace(
        "-1.00", "−1.00"
    )
    assert "Completeness counts coverage" not in drawn, "the rubric's sentence on the iCARE table"


def test_a_rubric_table_says_nothing_about_rouge_and_length():
    data = report.build([_row("x", judge.DEFAULT_MODEL, 0.5)])
    assert "length_effects" not in data["tables"][0]
