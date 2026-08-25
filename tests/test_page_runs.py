"""Does the published page actually run, or does it only contain the words?

Every other test about the page asserts on the HTML string. That cannot see the
failure that matters: the page is one inline script, so a runtime error in any
render function leaves a blank page with no error anywhere a reader would look.
A missing key, a null where an array was expected, a template literal closed in
the wrong place -- all silent.

So the script is extracted and executed against a DOM small enough to stub and
loud enough to fail. Skipped, not guessed, where node is absent.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tnb import report, results
from tnb.results import Metrics, Row

RUNNER = Path(__file__).parent / "support" / "run_page.js"


def _row(system: str, judge_model: str, value: float) -> Row:
    return Row(
        track=results.TRACK_TNEVAL,
        system_id=system,
        system_type="model",
        provider="einfra",
        prompt_version="tneval-soap-v1",
        judge_model=judge_model,
        judge_prompt_version="tneval-rubric-v1",
        n_sessions_attempted=50,
        n_sessions_generated=50,
        n_sessions_scored=50,
        metrics=Metrics(
            headline={"completeness": value, "conciseness": value, "faithfulness": value * 5},
            by_section={"subjective": {"completeness": value}},
            detail={"subjective-symptoms": value},
        ),
    )


def _page(tmp_path: Path) -> str:
    from tnb import judge
    from tnb.scoring import concordance

    rows = [
        _row(system, judge_model, value)
        for judge_model, scores in (
            (judge.DEFAULT_MODEL, {"x": 0.9, "y": 0.5, "z": 0.1}),
            (judge.SECOND_JUDGE, {"x": 0.5, "y": 0.1, "z": 0.9}),
        )
        for system, value in scores.items()
    ]
    data = report.build(rows)
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = None
    data["concordance"] = {
        results.TRACK_TNEVAL: concordance.to_json(
            concordance.compare(
                rows,
                results.TRACK_TNEVAL,
                [key for key, _ in report.COLUMNS[results.TRACK_TNEVAL]],
                ranking_measure=report.RANKING_MEASURES.get(results.TRACK_TNEVAL),
            )
        )
    }
    return report.render_page(data)


def _run(page: str, tmp_path: Path) -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the page cannot be executed here")

    script = tmp_path / "page.js"
    script.write_text(
        "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", page, re.S)), encoding="utf-8"
    )
    finished = subprocess.run(
        [node, str(RUNNER), str(script)], capture_output=True, text=True, timeout=60
    )
    assert finished.returncode == 0, finished.stdout + finished.stderr
    return finished.stdout


def test_the_page_executes_without_throwing(tmp_path):
    assert "RAN." in _run(_page(tmp_path), tmp_path)


def test_every_panel_with_data_puts_something_on_the_page(tmp_path):
    """A render function that returns early leaves an empty box, which looks
    exactly like a section nobody wrote."""
    output = _run(_page(tmp_path), tmp_path)

    for panel in ("tables", "concordance", "protocol-body", "licences-body"):
        assert f"{panel}: " in output, f"{panel} rendered nothing"


def test_a_panel_with_no_data_removes_itself_rather_than_leaving_an_empty_box(tmp_path):
    """Nothing to say and a heading saying it are different things."""
    data = report.build([_row("x", "a-judge", 0.5)])
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = None
    data["concordance"] = {}

    output = _run(report.render_page(data), tmp_path)

    assert "concordance" not in output.split("empty and not removed:")[-1]


def test_the_self_preference_panel_draws_when_there_is_an_effect_to_report(tmp_path):
    """`docs/limitations.md` tells the reader to check this panel before reading
    either table. It said that while the module had no caller and the page had
    no panel."""
    data = report.build([_row("x", "a-judge", 0.5)])
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = None
    data["concordance"] = {}
    data["preference"] = {
        "measure": "completeness",
        "judge_a": "gemini-3.1-pro-preview",
        "judge_b": "gpt-5.6-terra",
        "effects": [
            {
                "judge": "gemini-3.1-pro-preview",
                "family": "gemini",
                "estimate": 0.006,
                "low": -0.008,
                "high": 0.019,
                "detected": False,
                "n_own": 2,
                "n_neutral": 12,
                "n_sessions": 50,
                "summary": "`gemini-3.1-pro-preview` shows no detectable preference.",
            }
        ],
    }

    output = _run(report.render_page(data), tmp_path)

    assert "preference: " in output, "the panel rendered nothing"


def test_the_self_preference_panel_removes_itself_when_there_is_nothing(tmp_path):
    """A heading over an empty box reads as a section nobody finished."""
    data = report.build([_row("x", "a-judge", 0.5)])
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = None
    data["concordance"] = {}
    data["preference"] = None

    output = _run(report.render_page(data), tmp_path)

    assert "preference" not in output.split("empty and not removed:")[-1]


def test_the_saturation_panel_names_the_judge_that_produced_it(tmp_path):
    """`docs/saturation.json` was published from `gemini-2.5-pro` -- a judge
    that was tried and not chosen -- beside two tables scored by two others,
    and the panel said nothing about which one it was."""
    data = report.build([_row("x", "a-judge", 0.5)])
    data["calibration"] = None
    data["similarity_example"] = None
    data["judges"] = None
    data["concordance"] = {}
    data["preference"] = None
    data["saturation"] = {
        "judge_model": "gemini-2.5-pro",
        "judge_fingerprint": {"model": "gemini-2.5-pro", "thinking_budget": 128},
        "ignored_fingerprints": {},
        "sessions": 42,
        "corpus_sessions": 50,
        "criteria": [],
        "intervals": [],
        "indistinguishable": [],
        "narrowed_by": {},
        "still_scoring": [],
        "verdict_counts": {},
        "bootstrap": {},
    }

    page = report.render_page(data)
    _run(page, tmp_path)

    assert "judge_fingerprint" in page
    assert "thinking_budget" in page


def _judges_data() -> dict:
    """Six candidate judges, the shape `tnb judges` writes."""

    def judge_row(name: str, rubric: float, likert: float) -> dict:
        return {
            "judge_model": name,
            "rubric_beats_likert": "True",
            "agreements": [
                {
                    "name": "rubric_completeness",
                    "alpha": str(rubric),
                    "alpha_humans": "0.504",
                    "alpha_level": "nominal",
                    "statistic": "Cohen's kappa",
                    "judge": str(rubric),
                    "humans": "0.504",
                    "n": "3450",
                },
                {
                    "name": "likert_faithfulness",
                    "alpha": str(likert),
                    "alpha_humans": "0.179",
                    "alpha_level": "ordinal",
                    "statistic": "Spearman",
                    "judge": str(likert),
                    "humans": "0.179",
                    "n": "150",
                },
            ],
        }

    return {
        "notes": 150,
        "judges": [
            judge_row("gemini-3.1-pro-preview", 0.587, 0.133),
            judge_row("gemini-2.5-flash", 0.550, 0.141),
            judge_row("gemini-3.7-flash", 0.540, 0.091),
            judge_row("gpt-5.6-terra", 0.520, -0.015),
            judge_row("gemini-2.5-pro", 0.574, 0.063),
        ],
    }


def _with_judges(tmp_path: Path) -> str:
    from tnb import judge
    from tnb.scoring import concordance

    rows = [
        _row(system, judge_model, value)
        for judge_model, scores in (
            (judge.DEFAULT_MODEL, {"x": 0.9, "y": 0.5}),
            (judge.SECOND_JUDGE, {"x": 0.5, "y": 0.9}),
        )
        for system, value in scores.items()
    ]
    data = report.build(rows)
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["preference"] = None
    data["judges"] = _judges_data()
    data["concordance"] = {
        results.TRACK_TNEVAL: concordance.to_json(
            concordance.compare(
                rows,
                results.TRACK_TNEVAL,
                [key for key, _ in report.COLUMNS[results.TRACK_TNEVAL]],
            )
        )
    }
    return report.render_page(data)


def test_only_the_two_panel_judges_are_marked_as_being_in_the_panel(tmp_path):
    """`results/` also holds a full pass by `gemini-2.5-pro`, which was tried
    and not chosen. Marking every judge with a table as "in the panel" is the
    confusion this box exists to clear up."""
    page = _with_judges(tmp_path)
    _run(page, tmp_path)

    assert "pair.judge_a, pair.judge_b" in page, "the pair comes from the comparison"
    assert "DATA.tables.map(t => t.versions.judge_model)" not in page


def test_the_judge_box_claims_are_derived_from_its_own_table(tmp_path):
    """The prose named `gpt-5.6-sol` as evidence and `docs/judges.json` does not
    contain it -- a claim a reader could not check against the numbers beside
    it. Every sentence there is now computed from the rows it sits under."""
    page = _with_judges(tmp_path)
    _run(page, tmp_path)

    assert "gpt-5.6-sol" not in page.split("renderJudges")[-1]
    assert "notReleaseOrder" in page and "whereTheCeilingIsCleared" in page
