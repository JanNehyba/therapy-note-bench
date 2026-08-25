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
