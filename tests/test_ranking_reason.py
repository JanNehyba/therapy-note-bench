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
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.test_page_runs import RUNNER, _flat, _judges_payload, _row, _run
from tnb import judge, report
from tnb.results import Metrics


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


def _tensions_drawn(tmp_path: Path, by_judge: dict[str, dict[str, dict[str, float]]]) -> str:
    """A SOAP table for both judges, over the columns the caller invents.

    The concordance the note quantifies is computed by `report.build` from the
    same rows, so here the sentence and the grid behind it cannot be built from
    different numbers.
    """
    rows = [
        _row(
            system,
            judge_model,
            headline.get("completeness", 0.5),
            metrics=Metrics(headline=headline),
        )
        for judge_model, systems in by_judge.items()
        for system, headline in systems.items()
    ]
    data = report.build(rows)
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    # What `write` computes for every page it serves: the two judges' tables,
    # read together. Set by hand here for the same reason the panels above are
    # nulled -- the helper renders the page, it does not run the pipeline.
    data["concordance"] = report.concordance_payload(rows)
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


def test_do_not_predict_each_other_carries_the_number_behind_it(tmp_path):
    """One pair coupled under both judges, one read differently by each.

    "The columns do not predict each other" was the only claim in the ranking
    note with no figure anywhere on the page behind it. The concordance panel
    tabulates the pairs; this counts them into the sentence itself.
    """
    drawn = _tensions_drawn(
        tmp_path,
        {
            judge.DEFAULT_MODEL: {
                # completeness and conciseness agree with each other; faithfulness
                # agrees with both -- until the second judge reverses it.
                "x": {"completeness": 0.9, "conciseness": 0.9, "faithfulness": 0.3},
                "y": {"completeness": 0.5, "conciseness": 0.5, "faithfulness": 0.2},
                "z": {"completeness": 0.1, "conciseness": 0.1, "faithfulness": 0.1},
            },
            judge.SECOND_JUDGE: {
                "x": {"completeness": 0.9, "conciseness": 0.9, "faithfulness": 0.1},
                "y": {"completeness": 0.5, "conciseness": 0.5, "faithfulness": 0.2},
                "z": {"completeness": 0.1, "conciseness": 0.1, "faithfulness": 0.3},
            },
        },
    )
    assert "(1 of 3 rankable column pairs move together under both judges)" in drawn, (
        "the claim that the columns do not predict each other is printed without "
        "the pair count the concordance already holds"
    )


def test_a_table_whose_pairs_never_rank_keeps_the_unquantified_sentence(tmp_path):
    """Two columns everybody ties on rank nothing, so there is no denominator.

    A clause without one would be a number pretending to a pair count, and a
    tie is not a relation: the same sentence stands, without the parenthesis.
    """
    drawn = _tensions_drawn(
        tmp_path,
        {
            judge.DEFAULT_MODEL: {
                "x": {"completeness": 0.9, "conciseness": 0.5, "faithfulness": 0.5},
                "y": {"completeness": 0.5, "conciseness": 0.5, "faithfulness": 0.5},
                "z": {"completeness": 0.1, "conciseness": 0.5, "faithfulness": 0.5},
            },
            judge.SECOND_JUDGE: {
                "x": {"completeness": 0.5, "conciseness": 0.5, "faithfulness": 0.5},
                "y": {"completeness": 0.9, "conciseness": 0.5, "faithfulness": 0.5},
                "z": {"completeness": 0.1, "conciseness": 0.5, "faithfulness": 0.5},
            },
        },
    )
    assert "the columns do not predict each other. Under the other weightings" in drawn, (
        "the ranking note went missing entirely"
    )
    assert "rankable column pairs" not in drawn, (
        "a pair count was drawn over pairs that tie too heavily to rank"
    )


@pytest.mark.skipif(
    not (report.DOCS_DIR / "index.html").exists(), reason="the page has not been built"
)
def test_the_published_tables_carry_the_pair_counts_their_concordance_holds(tmp_path):
    """Published, because this is the one claim in the ranking note that used
    to have no figure anywhere behind it.

    The count is read from `docs/leaderboard.json` -- the artefact the table is
    drawn from -- for the table the page opens on, which is the only one the
    runner's address selects. What this pins is that the page still says the
    number, not that any particular pair agrees.
    """
    payload = json.loads((report.DOCS_DIR / "leaderboard.json").read_text(encoding="utf-8"))
    track = payload["tables"][0]["track"]
    rankable = [t for t in payload["concordance"][track]["tensions"] if t["rankable"]]
    assert rankable, "the published payload holds no rankable pair, so there is nothing to draw"
    together = sum(1 for t in rankable if t["agrees"])
    sentence = (
        f"({together} of {len(rankable)} rankable column pairs move together under both judges)"
    )

    drawn = _flat(
        _run(
            (report.DOCS_DIR / "index.html").read_text(encoding="utf-8"),
            tmp_path,
            panel="table-host",
        )
    )
    # The failure carries what the page actually said. This passes on Windows
    # and fails on Linux, and an assertion that reports only the string it
    # wanted leaves the difference to be guessed at -- which it was, for a day.
    nearby = ""
    if sentence not in drawn:
        at = drawn.find("rankable column pairs")
        if at >= 0:
            nearby = " | the page says: ..." + drawn[max(0, at - 120) : at + 160] + "..."
        else:
            held = [(t["first"], t["second"], t["rankable"]) for t in rankable]
            nearby = f" | the page never says 'rankable column pairs'; payload holds {held}"
    assert sentence in drawn, (
        f"{sentence} is the count docs/leaderboard.json holds, and the published table "
        f"does not say it{nearby}"
    )


def test_the_page_sees_the_concordance_the_payload_holds(tmp_path):
    """What the page's own script has, against what the file it was built from
    has.

    Two tests fail on Linux and pass on Windows on the same committed page: the
    clause counting rankable column pairs is not drawn, and a figure the methods
    page computes is not on it. Both come from `concordance.tensions`, and the
    runner reports no error, so the page runs and simply does not have them.
    That is a claim about what the script sees, and this is the only test that
    asks it.
    """
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the published page cannot be executed here")
    source = (report.DOCS_DIR / "index.html").read_text(encoding="utf-8")
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", source, re.S)
    if not scripts:
        pytest.skip("the published page carries no script")

    probe = (
        "console.log('PROBE ' + JSON.stringify({"
        "  keys: Object.keys(DATA.concordance || {}),"
        "  tables: (DATA.tables || []).map(t => t.track),"
        "  tensions: Object.entries(DATA.concordance || {}).map("
        "    ([k, v]) => [k, (v.tensions || []).length,"
        "                 (v.tensions || []).filter(t => t.rankable).length]),"
        "  node: process.version,"
        "}));"
    )
    script = tmp_path / "probe.js"
    script.write_text("\n".join(scripts) + "\n" + probe, encoding="utf-8")
    finished = subprocess.run(
        [node, str(RUNNER), str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    line = next(
        (ln for ln in (finished.stdout or "").splitlines() if ln.startswith("PROBE ")), None
    )
    assert line, f"the probe did not run: {(finished.stdout or '') + (finished.stderr or '')}"
    seen = json.loads(line[len("PROBE ") :])

    payload = json.loads((report.DOCS_DIR / "leaderboard.json").read_text(encoding="utf-8"))
    held = {
        track: [
            len(entry.get("tensions") or []),
            sum(1 for t in entry.get("tensions") or [] if t["rankable"]),
        ]
        for track, entry in (payload.get("concordance") or {}).items()
    }
    got = {track: [total, rankable] for track, total, rankable in seen["tensions"]}

    assert sorted(seen["keys"]) == sorted(held), (
        f"the script has concordance for {sorted(seen['keys'])} and the payload holds "
        f"{sorted(held)} (node {seen['node']})"
    )
    assert got == held, (
        f"the script counts {got} tensions and the payload holds {held} (node {seen['node']})"
    )
