"""The reason the table gives for its own order, and whether it survives being resampled.

The leaderboard orders by completeness and gives one reason: the judge agrees
with a trained therapist more closely than the two therapists agree with each
other. Under `gemini-3.1-pro-preview` that lead is +0.096 kappa; under
`gpt-5.6-terra` it is +0.017, and resampling the 150 rated notes puts it between
-0.012 and +0.047. The sentence was drawn in identical words under both, because
at two decimal places 0.60-against-0.50 and 0.52-against-0.50 are the same
shape -- and a reader had no way to see that one of the two published judges
does not establish the claim its own table rests on.

The interval is measured in `calibration`, published in `docs/judges.json` and
only drawn here, like every other ordering decision on this page.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_page_runs import _flat, _judges_payload, _row, _run
from tnb import judge, report


def _with_margin(margin: float, low: float, high: float) -> dict:
    """One `docs/judges.json` entry carrying a measured margin."""
    return {
        "judge_model": judge.DEFAULT_MODEL,
        "agreements": [
            {
                "name": "rubric_completeness",
                "judge": 0.52,
                "humans": 0.50,
                "statistic": "Cohen's kappa",
                "margin": margin,
                "margin_low": low,
                "margin_high": high,
                "margin_draws": 2000,
                "clears_ceiling": low > 0,
            },
            {"name": "likert_completeness", "judge": 0.30, "humans": 0.13},
            {"name": "likert_conciseness", "judge": 0.02, "humans": 0.19},
        ],
    }


def _drawn(tmp_path: Path, entry: dict) -> str:
    rows = [
        _row("kimi-k3", judge.DEFAULT_MODEL, 0.55),
        _row("gemma4", judge.DEFAULT_MODEL, 0.45),
    ]
    data = report.build(rows)
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = _judges_payload(entry)
    return _flat(_run(report.render_page(data), tmp_path, panel="table-host"))


def test_a_lead_that_clears_zero_is_drawn_with_its_interval(tmp_path):
    drawn = _drawn(tmp_path, _with_margin(0.096, 0.068, 0.123))
    assert "0.096" in drawn and "0.068" in drawn and "0.123" in drawn, (
        "the lead over the therapists' own agreement is published without the interval "
        "that says whether it is a lead at all"
    )
    assert "does not clear zero" not in drawn, "a measured lead reported as unmeasured"


def test_a_lead_that_does_not_clear_zero_says_so(tmp_path):
    drawn = _drawn(tmp_path, _with_margin(0.017, -0.012, 0.047))
    assert "does not clear zero" in drawn, (
        "the table gives this inequality as the only reason for the column it orders by, "
        "and under this judge the notes do not establish it"
    )
    # A real minus sign, not a hyphen: the figure is negative and the page is
    # read, not parsed.
    assert "−0.012" in drawn, "the lower end of the interval is not drawn"
    assert "0.047" in drawn


def test_a_panel_written_before_the_margin_existed_draws_no_clause(tmp_path):
    """An older `docs/judges.json` has no margin, and a missing number is not a zero."""
    entry = {
        "judge_model": judge.DEFAULT_MODEL,
        "agreements": [
            {"name": "rubric_completeness", "judge": 0.52, "humans": 0.50},
            {"name": "likert_completeness", "judge": 0.30, "humans": 0.13},
        ],
    }
    drawn = _drawn(tmp_path, entry)
    assert "Ordered by" in drawn, "the ranking note went missing entirely"
    assert "does not clear zero" not in drawn and "Resampling" not in drawn, (
        "a clause was drawn from a margin nobody measured"
    )


@pytest.mark.skipif(
    not (report.DOCS_DIR / "judges.json").exists(), reason="the panel has not been written yet"
)
def test_the_published_panel_carries_an_interval_for_every_judge_it_draws():
    """Published, because the two judges the site draws disagree about this."""
    panel = json.loads((report.DOCS_DIR / "judges.json").read_text(encoding="utf-8"))
    drawn = {judge.DEFAULT_MODEL, judge.SECOND_JUDGE}
    for entry in panel["judges"]:
        if entry["judge_model"] not in drawn:
            continue
        found = next(a for a in entry["agreements"] if a["name"] == "rubric_completeness")
        assert found.get("margin") is not None, f"{entry['judge_model']} has no measured margin"
        assert found.get("margin_low") is not None and found.get("margin_high") is not None, (
            f"{entry['judge_model']} has a margin and no interval, which is a point estimate "
            "presented as a finding"
        )
        assert found["margin_low"] <= found["margin"] <= found["margin_high"], (
            "the interval does not contain the figure it is an interval for"
        )
        assert found["clears_ceiling"] == (found["margin_low"] > 0), (
            "the verdict and the interval it is read from disagree"
        )
