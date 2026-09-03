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

import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from tnb import report, results
from tnb.config import REPO_ROOT
from tnb.results import Metrics, Row, Settings

RUNNER = Path(__file__).parent / "support" / "run_page.js"


def _row(system: str, judge_model: str, value: float, **overrides) -> Row:
    return Row(
        **{
            "track": results.TRACK_TNEVAL,
            "system_id": system,
            "system_type": "model",
            "provider": "einfra",
            "prompt_version": "tneval-soap-v1",
            "judge_model": judge_model,
            "judge_prompt_version": "tneval-rubric-v1",
            # Every row the scorer writes records the judge's settings, and a
            # group that names a judge without them is withdrawn rather than
            # drawn -- so a fixture without one is not a table.
            "judge_settings": {"model": judge_model, "thinking_budget": 256},
            "n_sessions_attempted": 50,
            "n_sessions_generated": 50,
            "n_sessions_scored": 50,
            "metrics": Metrics(
                headline={
                    "completeness": value,
                    "conciseness": value,
                    "faithfulness": value * 5,
                },
                by_section={"subjective": {"completeness": value}},
                detail={"subjective-symptoms": value},
            ),
            **overrides,
        }
    )


def _page_data(tmp_path: Path) -> dict:
    """The payload both pages are drawn from. Split out when the panels moved:
    a panel test now renders whichever of the two pages holds its panel, from
    the same data, so the test is about the panel and not about the split."""
    from tnb import judge

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
    # The SHAPE the page is served, not None. `docs/judges.json` is a wrapper --
    # {notes, separable, judges: [...]} -- and the leaderboard read the wrapper
    # as if it were the list. `.find` is not a function on an object, so the one
    # inline script died on the first table and the published page served a
    # heading and no leaderboard. Every test here passed throughout, because
    # this line handed the page a None the code guards against and never the
    # object it actually gets. A fixture that removes the field under test is
    # not a fixture, it is a hole.
    data["judges"] = _judges_payload(_calibrated(judge.DEFAULT_MODEL, 0.60, 0.50, [0.11, 0.03]))
    data["concordance"] = report.concordance_payload(rows)
    return data


def _page(tmp_path: Path) -> str:
    return report.render_page(_page_data(tmp_path))


def _flat(html: str) -> str:
    """Rendered HTML with its wrapping taken out.

    A sentence in a template literal keeps the template's line breaks, so
    asserting on a phrase that spans one silently fails on a page that says
    exactly the right thing.
    """
    return re.sub(r"\s+", " ", html)


def _still_empty(output: str) -> str:
    """The runner's list of panels that rendered nothing and were not removed.

    Read as its own line. The tests used to take everything after the marker,
    which quietly means "the whole output" whenever no panel is empty -- so the
    assertion passed for the right reason and would have failed for a wrong one
    the moment the runner printed anything else. It then did.
    """
    for line in output.splitlines():
        if line.startswith("empty and not removed:"):
            return line.partition(":")[2].strip()
    return ""


def _run(page: str, tmp_path: Path, panel: str | None = None, search: str = "") -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the page cannot be executed here")

    script = tmp_path / "page.js"
    script.write_text(
        "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", page, re.S)), encoding="utf-8"
    )
    finished = subprocess.run(
        [node, str(RUNNER), str(script), *([panel] if panel else [])],
        # The page reads its mode out of the address, so a test drives it the
        # way a reader would. There is no button to press in this DOM.
        env={**os.environ, "PAGE_SEARCH": search} if search else None,
        capture_output=True,
        text=True,
        # Node writes UTF-8; without this Python decodes it with the
        # locale codec, and every assertion about a rendered string with a
        # non-ASCII character in it compares two different manglings.
        encoding="utf-8",
        timeout=60,
    )
    assert finished.returncode == 0, finished.stdout + finished.stderr
    return finished.stdout


def test_the_page_executes_without_throwing(tmp_path):
    assert "RAN." in _run(_page(tmp_path), tmp_path)


def test_every_panel_with_data_puts_something_on_the_page(tmp_path):
    """A render function that returns early leaves an empty box, which looks
    exactly like a section nobody wrote."""
    data = _page_data(tmp_path)

    # `table-host` and not `tables`: the switch moved inside the section, so
    # `#tables` now holds only `<div id="table-host"></div>` -- 27 characters,
    # under the runner's 40-character floor. The leaderboard itself is in
    # `table-host`, which is what this was always asking about.
    assert "table-host: " in _run(report.render_page(data), tmp_path), (
        "the table host is the leaderboard"
    )

    methods = _run(report.render_methods(data), tmp_path)
    for panel in ("concordance", "protocol-body", "licences-body"):
        assert f"{panel}: " in methods, f"{panel} rendered nothing"


def test_a_panel_with_no_data_removes_itself_rather_than_leaving_an_empty_box(tmp_path):
    """Nothing to say and a heading saying it are different things."""
    data = report.build([_row("x", "a-judge", 0.5)])
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = None
    data["concordance"] = {}

    output = _run(report.render_methods(data), tmp_path)

    assert "concordance" not in _still_empty(output)


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

    output = _run(report.render_methods(data), tmp_path)

    assert "preference: " in output, "the panel rendered nothing"


def _preference_with(neutral: list[str]) -> dict:
    return {
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
                "n_neutral": len(neutral),
                "n_sessions": 50,
                "neutral": neutral,
                "summary": "`gemini-3.1-pro-preview` shows no detectable preference.",
            }
        ],
    }


def _methods_note(tmp_path: Path, neutral: list[str]) -> str:
    data = report.build([_row("x", "a-judge", 0.5)])
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = None
    data["concordance"] = {}
    data["preference"] = _preference_with(neutral)
    return _flat(_run(report.render_methods(data), tmp_path, panel="preference"))


def test_the_contamination_warning_names_only_systems_that_are_in_the_group(tmp_path):
    """It warned about two systems a definition change had already taken out.

    `gemma4` is Google's and `gpt-oss-120b` is OpenAI's under names their model
    families do not share, so while they sat in the group that is supposed to be
    neutral they pulled the estimate toward zero. Both were moved out of it on
    2026-08-26 and the sentence stayed behind, telling a reader to discount a
    result that is sound. Checked against the group rather than remembered.
    """
    clean = ["glm-5", "kimi-k3", "qwen3.5-122b", "therapist"]

    note = _methods_note(tmp_path, clean)
    assert "Reference group — the 4 systems" in note
    assert "gemma4" not in note and "gpt-oss-120b" not in note
    assert "toward zero" not in note, "nothing in this group pulls the answer anywhere"

    note = _methods_note(tmp_path, [*clean, "gemma4"])
    assert "gemma4" in note and "toward zero" in note, "a stray in the group must be named"
    assert "gpt-oss-120b" not in note, "and only the stray that is actually in it"


def test_the_self_preference_panel_removes_itself_when_there_is_nothing(tmp_path):
    """A heading over an empty box reads as a section nobody finished."""
    data = report.build([_row("x", "a-judge", 0.5)])
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = None
    data["concordance"] = {}
    data["preference"] = None

    output = _run(report.render_methods(data), tmp_path)

    assert "preference" not in _still_empty(output)


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

    def judge_row(name: str, rubric: float, likert: float, budget: int = 256) -> dict:
        return {
            "judge_model": name,
            "judge_settings": {"model": name, "thinking_budget": budget},
            "other_settings": {},
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

    from tnb.scoring import calibration

    judges = [
        judge_row("gemini-3.1-pro-preview", 0.587, 0.133),
        judge_row("gemini-2.5-flash", 0.550, 0.141),
        judge_row("gemini-3.7-flash", 0.540, 0.091),
        judge_row("gpt-5.6-terra", 0.520, -0.015),
        judge_row("gemini-2.5-pro", 0.574, 0.063),
    ]
    # Computed rather than hand-written, and computed from the same list the
    # page draws -- which is the point of the block: a claim about these rows
    # that a reader checks against these rows.
    return {
        "notes": 150,
        "separable": calibration.separations(judges, "rubric_completeness"),
        "judges": judges,
    }


def _with_judges(tmp_path: Path) -> str:
    from tnb import judge

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
    data["concordance"] = report.concordance_payload(rows)
    # The methods page: this box moved there with the rest of the instrument.
    return report.render_methods(data)


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
    assert "whatTheCalibrationSeparates" in page and "whereTheCeilingIsCleared" in page

    # And what it derives is margin-aware. `gemini-3.1-pro-preview` 0.587 leads
    # `gpt-5.6-terra` 0.520 by 0.067, which clears the 0.05 margin; it leads
    # `gemini-2.5-pro` 0.574 by 0.013, which does not. The page used to say
    # "the newest flash is the worst of the three" -- a gap of 0.0077, a
    # seventh of the margin, and it reversed on the next measurement.
    block = _judges_data()["separable"]
    separated = {(item["better"], item["worse"]) for item in block["separated"]}
    assert ("gemini-3.1-pro-preview", "gpt-5.6-terra") in separated
    assert ("gemini-3.1-pro-preview", "gemini-2.5-pro") not in separated
    assert not any("flash" in better and "flash" in worse for better, worse in separated)


def test_every_key_in_the_page_data_is_read_by_the_page():
    """The fourth instance of one shape, so it becomes a rule.

    `preference`, `judges` and `generated_from` were each computed, written into
    the payload, and consumed by nothing -- the self-preference panel that
    `docs/limitations.md` tells readers to check, the evidence for the panel's
    own composition, and the line saying where the numbers come from. A key
    nobody reads is either a missing panel or dead weight, and both are worth
    failing over.
    """
    # Both pages, and the partials they share. A key read by either is read;
    # a key read by neither still fails. Checking one page would have started
    # passing for the wrong reason the moment a panel moved to the other.
    templates = "".join(
        path.read_text(encoding="utf-8") for path in report.TEMPLATE_DIR.glob("*.html")
    )

    # `write`'s payload, not `build`'s. `saturations` -- the whole list, beside
    # the one the page draws -- was added in `write`, so a test that built its
    # own payload never saw the key it exists to catch.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        docs = Path(tmp)
        readme = docs / "README.md"
        readme.write_text("<!-- LEADERBOARD:BEGIN -->\n<!-- LEADERBOARD:END -->\n", "utf-8")
        data = report.write([_row("x", "a-judge", 0.5)], docs_dir=docs, readme=readme)

    # `.key` rather than `DATA.key`: several panels are rendered by a function
    # that takes the whole payload and reads `data.saturation` inside it, so a
    # literal `DATA.saturation` never appears.
    unread = [key for key in data if f".{key}" not in templates]
    assert not unread, f"in the payload and read by nothing: {unread}"


def test_candidates_measured_at_different_settings_are_flagged(tmp_path):
    """The panel that picks a judge was comparing instruments, not judges.

    `gemini-3.1-pro-preview`'s answers were re-asked at a thinking budget of
    256 and the other Gemini candidates' were still at 128, with the table
    putting the four alphas side by side and saying nothing.
    """
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
    data.update(calibration=None, similarity_example=None, saturation=None, preference=None)
    data["concordance"] = {
        results.TRACK_TNEVAL: concordance.to_json(
            concordance.compare(rows, results.TRACK_TNEVAL, report.COLUMNS[results.TRACK_TNEVAL])
        )
    }

    mixed = _judges_data()
    mixed["judges"][1]["judge_settings"]["thinking_budget"] = 128
    data["judges"] = mixed
    drawn = _run(report.render_methods(data), tmp_path, panel="judges-body")

    # Whitespace-normalised: the sentence wraps in the template, so the
    # rendered HTML carries a newline in the middle of it.
    assert "from others of the same kind" in _flat(drawn)
    assert "thinking_budget 128" in drawn and "thinking_budget 256" in drawn

    # And silent when they agree. Asserted on what the page renders, not on its
    # source: the warning is a string literal in the template either way.
    data["judges"] = _judges_data()
    agreed = _run(report.render_methods(data), tmp_path, panel="judges-body")

    assert "from others of the same kind" not in _flat(agreed)
    assert "thinking_budget 256" in agreed


def test_two_vendors_settings_are_not_reported_as_a_defect(tmp_path):
    """A thinking budget and a reasoning effort are different controls.

    The warning compared whole settings mappings, so a Gemini row beside a GPT
    row could never match and it fired on every table -- including one where
    every candidate of a kind had just been re-measured at a single setting,
    which is what made the flash ordering reverse. It was telling a reader
    about a defect that had been fixed that morning.
    """
    from tnb import report

    data = report.build([_row("x", "a-judge", 0.5)])
    data.update(calibration=None, similarity_example=None, saturation=None, preference=None)
    data["concordance"] = {}

    judges = _judges_data()
    for entry in judges["judges"]:
        if entry["judge_model"].startswith("gpt-"):
            entry["judge_settings"] = {
                "model": entry["judge_model"],
                "backend": "openai",
                "effort": "medium",
                "max_output_tokens": 672,
            }
    data["judges"] = judges

    drawn = _run(report.render_methods(data), tmp_path, panel="judges-body")

    assert "from others of the same kind" not in _flat(drawn)
    assert "different controls" in _flat(drawn), "it says what the difference is instead"


def test_the_methods_page_executes_without_throwing(tmp_path):
    """It shares a payload and a script context with the leaderboard, so a
    helper the leaderboard happens to define first would hide a missing one
    here until the panels moved across."""
    from tnb import report

    data = report.build([_row("gemma4", "a-judge", 0.5)])
    _run(report.render_methods(data), tmp_path)


def test_both_pages_are_written_by_one_run(tmp_path):
    """One payload, two views. A methods page computed separately could describe
    a run the leaderboard is not showing, and being checkable against the
    tables beside it is the whole reason it exists."""
    from tnb import report

    readme = tmp_path / "README.md"
    readme.write_text("<!-- LEADERBOARD:BEGIN -->\n<!-- LEADERBOARD:END -->\n", encoding="utf-8")
    report.write([_row("gemma4", "a-judge", 0.5)], docs_dir=tmp_path, readme=readme)

    page = (tmp_path / report.PAGE_PATH.name).read_text(encoding="utf-8")
    methods = (tmp_path / report.METHODS_PATH.name).read_text(encoding="utf-8")

    assert "const DATA = " in methods
    payload = "const DATA = "
    assert page.split(payload)[1].split("\n")[0] == methods.split(payload)[1].split("\n")[0], (
        "the two pages must be drawn from the same payload, character for character"
    )


def test_a_filter_is_drawn_only_when_it_has_something_to_filter(tmp_path):
    """`Show numbers as published` was static HTML wired to nothing.

    No row in `results/` has ever carried `system_type: published` -- 1001 are
    `model`, 34 `reference-model`, 17 `reference-human`. A reader who ticked it
    and saw no change learned that the page does not work.

    Asserted on the `controls` element's rendered HTML rather than on the
    runner's summary: the first version of this test asked the summary, which
    reports only elements the script reads, and it passed with the defect put
    back.
    """
    from tnb import report

    models_only = report.build([_row("x", "a-judge", 0.5)])
    controls = _run(report.render_page(models_only), tmp_path, panel="controls")

    # Empty, not absent. "not in" alone passes when the element was never
    # written to at all, which is exactly the state the static markup left it
    # in -- so the first version of this assertion held under the defect.
    assert controls.strip() == "", f"expected no controls at all, got {controls!r}"


def test_the_therapist_is_drawn_without_being_asked_for(tmp_path):
    """The therapist's note used to be behind a tick box, unticked.

    It is the only human-written note on the page and the row a reader most
    wants to see, and hiding it by default made the table read as models-only
    and put the most interesting comparison one click away. It is drawn now, and
    no control offers to hide it.
    """
    from tnb import report

    data = report.build(
        [
            _row("x", "a-judge", 0.5),
            _row("therapist", "a-judge", 0.3, system_type="reference-human"),
        ]
    )
    page = report.render_page(data)

    controls = _run(page, tmp_path, panel="controls")
    assert "show-reference" not in controls, "the therapist is not something to opt into"
    assert "show-published" not in controls, "still nothing published to show"

    table = _flat(_run(page, tmp_path, panel="table-host"))
    assert "therapist" in table, "the human note was hidden by default"
    assert "note a human clinician wrote" in table, (
        "the chip says what the row is; a reader also needs to know what that means"
    )


def test_a_row_of_a_type_nothing_offers_to_hide_is_still_shown(tmp_path):
    """The reason the dead control is replaced rather than deleted.

    Deleting it and leaving `rowVisible` to hide the type would lose a row
    silently, which is worse than a switch that does nothing. A `published` row
    brings its own control, and until one exists neither is drawn.
    """
    from tnb import report

    data = report.build(
        [_row("x", "a-judge", 0.5), _row("paper", "a-judge", 0.3, system_type="published")]
    )
    controls = _run(report.render_page(data), tmp_path, panel="controls")

    assert "show-published" in controls


def test_only_one_table_is_drawn_at_a_time(tmp_path):
    """Five comparability groups, one on screen.

    The rule that makes five is untouched -- it is this project's central
    invariant. What changed is that the reader picks one instead of scrolling
    past four, and the page must never draw two sets of rows at once: a reader
    who sorted a column would be sorting one referee's table while looking at
    another's.
    """
    from tnb import report

    data = _page_data(tmp_path)
    assert len(data["tables"]) >= 2, "the fixture must have something to switch between"

    host = _run(report.render_page(data), tmp_path, panel="table-host")

    # `data-table=` marks the grid of model rows. A rendered table also holds
    # nested ones -- the per-row detail and the column legend -- so counting
    # `<table` counts the furniture too.
    assert host.count('data-table="') == 1, "one grid of model rows, whatever the payload holds"


def test_the_heading_does_not_name_the_judge_the_control_names(tmp_path):
    """Two labels for one fact contradict each other the moment one changes.

    The heading said "scored by gemini-3.1-pro-preview" while the control said
    which judge was selected; after a switch the heading would be describing
    the table the reader just left.
    """
    from tnb import report

    data = _page_data(tmp_path)
    host = _run(report.render_page(data), tmp_path, panel="table-host")
    switch = _run(report.render_page(data), tmp_path, panel="switch")

    heading = host.split("</h2>")[0]
    for table in data["tables"]:
        judge = table["versions"]["judge_model"]
        if judge:
            assert judge not in heading, "the heading must not name the judge"

    assert any(t["versions"]["judge_model"] in switch for t in data["tables"]), (
        "and the control must"
    )


def test_two_tables_from_one_judge_are_told_apart_by_their_settings(tmp_path):
    """`gemini-2.5-pro` has two tables: eleven systems answered at a thinking
    budget of 128 and three at 256. Two buttons reading `gemini-2.5-pro` and
    nothing else is a choice the reader cannot make."""
    from tnb import report

    rows = [
        _row("x", "a-judge", 0.5, judge_settings={"model": "a-judge", "thinking_budget": budget})
        for budget in (128, 256)
    ]
    data = report.build(rows)
    assert len(data["tables"]) == 2, "two settings are two instruments"

    switch = _run(report.render_page(data), tmp_path, panel="switch")

    assert "thinking_budget 128" in switch
    assert "thinking_budget 256" in switch


def test_a_judge_with_no_rows_on_this_track_is_not_offered(tmp_path):
    """A disabled button is an offer that cannot be accepted.

    `gemini-2.5-pro` has TN-Eval rows and no iCARE ones. Listing judges per
    track makes the case structurally impossible rather than handled.
    """
    from tnb import report

    rows = [
        _row("x", "judge-a", 0.5),
        _row("x", "judge-b", 0.5),
        _row("x", "judge-a", 0.5, track=results.TRACK_ICARE, prompt_version="icare-zeroshot-v1"),
    ]
    selection = report.build(rows)["selection"]

    by_track = {t["track"]: [j["judge_model"] for j in t["judges"]] for t in selection["tracks"]}

    assert sorted(by_track[results.TRACK_TNEVAL]) == ["judge-a", "judge-b"]
    assert by_track[results.TRACK_ICARE] == ["judge-a"]


def test_the_link_in_the_address_bar_comes_back_to_the_same_table(tmp_path):
    """A reader who sends somebody a link to one judge's table means that one."""
    from tnb import report

    data = _page_data(tmp_path)
    wanted = data["tables"][-1]["id"]
    assert wanted != data["selection"]["default"], "the fixture must not pick the default"

    page = report.render_page(data)
    script = tmp_path / "hash.js"
    body = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", page, re.S))
    script.write_text(f"global.location = {{ hash: '#{wanted}' }};\n" + body, encoding="utf-8")

    finished = subprocess.run(
        [shutil.which("node") or "node", str(RUNNER), str(script), "table-host"],
        capture_output=True,
        text=True,
        # Node writes UTF-8; without this Python decodes it with the
        # locale codec, and every assertion about a rendered string with a
        # non-ASCII character in it compares two different manglings.
        encoding="utf-8",
        timeout=60,
    )
    assert finished.returncode == 0, finished.stdout + finished.stderr

    judge = next(t for t in data["tables"] if t["id"] == wanted)["versions"]["judge_model"]
    switch = _run(page, tmp_path, panel="switch")
    assert judge, "the fixture's last table must be a judged one"
    assert judge in switch


def test_neither_page_leaves_a_panel_as_an_empty_frame(tmp_path):
    """Nothing to say and a heading saying it are different things.

    Six panels used to return early and leave a `<details>` with a summary over
    an empty body, which reads as a section somebody abandoned. This is the
    general form of that rule, over a payload where every panel has nothing.

    `controls` and `switch` are the exceptions and are named rather than
    excused: both are written on every render and are legitimately empty when
    there is one table and nothing to filter. Their margins are collapsed with
    `:empty` in the stylesheet, so an empty one takes no room.
    """
    from tnb import report

    data = report.build([_row("x", "a-judge", 0.5)])
    data.update(
        calibration=None,
        similarity_example=None,
        saturation=None,
        judges=None,
        preference=None,
        concordance={},
        corpus=None,
        licences=None,
        protocol=None,
    )

    ALLOWED = {"controls", "switch"}
    for name, render in (("leaderboard", report.render_page), ("methods", report.render_methods)):
        output = _run(render(data), tmp_path)
        left = _still_empty(output)
        if not left:
            continue
        stayed = {part.strip() for part in left.split(",") if part.strip()}
        assert stayed <= ALLOWED, f"{name} left an empty frame: {sorted(stayed - ALLOWED)}"

    style = (report.TEMPLATE_DIR / "_style.html").read_text(encoding="utf-8")
    assert ".switch:empty" in style and ".controls:empty" in style, (
        "the two that stay must take no room"
    )


def test_the_sentence_under_the_table_names_this_table_s_rank_first(tmp_path):
    """`rank_a` belongs to `judge_a`, and the note printed the pair in that
    fixed order whichever table was on screen.

    Read while looking at the second judge's table, "10th here and 4th there"
    had the two the wrong way round -- a number a reader could check against
    the rows in front of them and find wrong.
    """
    from tnb import report

    data = _page_data(tmp_path)
    found = data["concordance"][results.TRACK_TNEVAL]
    ranking = next(m for m in found["measures"] if m["measure"] == found["anchor_measure"])
    far = ranking["furthest"]
    assert far and far["rank_a"] != far["rank_b"], "the fixture must have a system that moved"

    page = report.render_page(data)
    body = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", page, re.S))

    for table in data["tables"]:
        judge = table["versions"]["judge_model"]
        if judge not in (found["judge_a"], found["judge_b"]):
            continue
        script = tmp_path / "note.js"
        script.write_text(f"global.location = {{ hash: '#{table['id']}' }};\n" + body, "utf-8")
        finished = subprocess.run(
            [shutil.which("node") or "node", str(RUNNER), str(script), "table-host"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        assert finished.returncode == 0, finished.stdout + finished.stderr

        # The sentence used to say "Nth in this table", which was a rank on the
        # measure printed as a row position -- true only where the table is
        # ordered by that measure, and the iCARE table is alphabetical. It says
        # "Nth on <measure> under this judge" now; what this test holds is the
        # part that was a real bug, that the first of the two ranks belongs to
        # the judge the reader is looking at.
        here = far["rank_a"] if judge == found["judge_a"] else far["rank_b"]
        # Whitespace-normalised: the template wraps the sentence, so the rank and
        # the measure are separated by a newline and an indent in the output.
        flat = re.sub(r"\s+", " ", finished.stdout)
        said = re.search(r"(\d+)\w* on [^<]*? under this judge", flat)
        assert said, f"the sentence no longer names a rank under this judge: {flat[-400:]}"
        assert said.group(1) == str(here), (
            f"viewing {judge}, the first rank must be its own: the sentence says "
            f"{said.group(1)} where this judge places it {here}"
        )


def test_every_link_between_the_two_pages_lands_somewhere(tmp_path):
    """The split created cross-page links, and a link to a panel that moves
    again is a dead end a reader finds and nobody else does.

    Checks the file and the anchor: `methods.html#concordance` requires both a
    `methods.html` and an element with that id in it.

    Over what `report.write` produces, and nothing else. It is what a fresh
    checkout has before anyone runs `make figures`, so a link between these two
    must resolve without the other artefacts existing -- and a link *out* to
    one of them is checked against the real `docs/` below.
    """
    from tnb import report

    readme = tmp_path / "README.md"
    readme.write_text("<!-- LEADERBOARD:BEGIN -->\n<!-- LEADERBOARD:END -->\n", encoding="utf-8")
    report.write([_row("x", "a-judge", 0.5)], docs_dir=tmp_path, readme=readme)

    written = {"index.html", "methods.html"}
    pages = {name: (tmp_path / name).read_text(encoding="utf-8") for name in written}

    for name, text in pages.items():
        for target, anchor in _links_in(text, name):
            if target not in written:
                continue  # an artefact from tools/, checked against docs/ below
            assert not anchor or f'id="{anchor}"' in pages[target], (
                f"{name} links to #{anchor} in {target}, which has no such element"
            )


def test_the_published_site_has_no_dead_link():
    """What a reader actually gets: every local href in `docs/` resolves.

    The pages point at `brief.html` and `therapy-note-bench.pdf`, which
    `tools/` writes rather than `tnb report`, so nothing else notices when one
    of them is missing or renamed.
    """
    docs = Path(report.DOCS_DIR)
    published = {p.name: p for p in docs.iterdir() if p.is_file()}
    if "index.html" not in published:
        pytest.skip("the site has not been generated in this checkout")

    text_of = {
        name: path.read_text(encoding="utf-8")
        for name, path in published.items()
        if name.endswith(".html")
    }

    for name, text in text_of.items():
        for target, anchor in _links_in(text, name):
            assert target in published, f"{name} links to {target}, which is not published"
            if anchor:
                assert f'id="{anchor}"' in text_of.get(target, ""), (
                    f"{name} links to #{anchor} in {target}, which has no such element"
                )


def _links_in(text: str, page: str) -> list[tuple[str, str]]:
    """(file, anchor) for every local href in the static markup.

    Scripts are skipped: a `href="${l.url}"` inside a template literal is built
    at run time from the payload and points at a licence's website.
    """
    static = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.S)
    found = []
    for href in re.findall(r'href="([^"]+)"', static):
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target, _, anchor = href.partition("#")
        found.append((target or page, anchor))
    return found


def test_the_concordance_panel_puts_the_tracks_in_the_tables_order(tmp_path):
    """The payload is serialised with sorted keys, so `icare` comes before
    `tneval-soap` whatever order Python built it in -- and the panel trusted
    the key order while the SOAP track leads everywhere else on the site."""
    from tnb import report

    rows = []
    for track, prompt, measure in (
        (results.TRACK_TNEVAL, "tneval-soap-v1", "completeness"),
        (results.TRACK_ICARE, "icare-zeroshot-v1", "trace"),
    ):
        for judge_model, values in (("judge-a", (0.9, 0.5)), ("judge-b", (0.5, 0.9))):
            for system, value in zip(("x", "y"), values, strict=True):
                rows.append(
                    _row(
                        system,
                        judge_model,
                        value,
                        track=track,
                        prompt_version=prompt,
                        metrics=Metrics(headline={measure: value}),
                    )
                )

    data = report.build(rows)
    data["concordance"] = report.concordance_payload(rows, judge_a="judge-a", judge_b="judge-b")
    assert len(data["concordance"]) == 2, "the fixture needs both tracks"

    panel = _run(report.render_methods(data), tmp_path, panel="concordance")

    soap = report.TRACK_TITLES[results.TRACK_TNEVAL]
    icare = report.TRACK_TITLES[results.TRACK_ICARE]
    assert soap in panel and icare in panel, "each section says which track it is"
    assert panel.index(soap) < panel.index(icare), "SOAP leads, as the tables do"
    assert panel.count("Do the two judges agree?") == 1, "one heading over both sections"


def test_our_own_ceiling_is_not_described_as_the_endpoint_refusing(tmp_path):
    """`unreached_reasons` outgrew its heading.

    It used to hold only what the endpoint refused. It now also holds calls
    this harness cut off at its own token ceiling -- which did reach the model,
    and which re-running does not fix. "1 call the endpoint never answered",
    over a list whose one entry reads `truncated at max_tokens=16384`, is a
    heading the line beneath it contradicts.
    """
    from tnb import report

    cut_off = _row(
        "x",
        "a-judge",
        0.5,
        n_sessions_generated=49,
        unreached_reasons={"truncated at max_tokens=16384": 1},
    )
    refused = _row(
        "y",
        "a-judge",
        0.5,
        n_sessions_generated=49,
        unreached_reasons={"HTTP429: rate limit": 1},
    )

    host = _run(report.render_page(report.build([cut_off, refused])), tmp_path, panel="table-host")

    assert "1 call(s) this harness cut off" in host
    assert "1 call(s) the endpoint never answered" in host
    assert "already had its one escalation" in host


def test_the_saturation_tooltip_quotes_the_table_it_names(tmp_path):
    """It said "the table shows 0.550, over all 49 of its own". The table shows
    0.546, over 48.

    The panel was recomputing the figure from the answer cache and labelling it
    with the table's name. It averages every conversation it found answers for;
    the table averages only the notes the judge *finished*, so a note the judge
    started and left part-answered is in one denominator and not the other.
    Three of four systems checked disagreed, and the fourth agreed only because
    it had no partial notes.
    """
    from tnb import report

    scored = _row("kimi-k3", "a-judge", 0.5)
    object.__setattr__(scored, "n_sessions_partial", 2)
    object.__setattr__(
        scored, "metrics", Metrics(headline={"completeness": 0.5459}, by_section={}, detail={})
    )

    data = report.build([scored])
    data.update(calibration=None, similarity_example=None, judges=None, preference=None)
    data["concordance"] = {}
    data["saturation"] = {
        "judge_model": "a-judge",
        "judge_fingerprint": {"model": "a-judge"},
        "ignored_fingerprints": {},
        "sessions": 40,
        "corpus_sessions": 50,
        "narrowed_by": {},
        "criteria": [],
        "verdict_counts": {},
        "still_scoring": [],
        "indistinguishable": [["kimi-k3"]],
        "intervals": [
            {
                "system": "kimi-k3",
                "mean": 0.527,
                # What the panel used to print, and what it must not print now.
                "own_mean": 0.5503,
                "own_sessions": 49,
                "low": 0.488,
                "high": 0.569,
            }
        ],
    }

    body = _flat(_run(report.render_methods(data), tmp_path, panel="saturation-body"))

    assert "the table shows 0.546" in body, "the figure comes from the table"
    assert "0.550" not in body, "and not from a second computation of it"
    assert "48 notes the judge finished" in body, "with the denominator that produced it"


def test_a_filter_is_offered_for_the_table_on_screen_and_not_for_another(tmp_path):
    """The rule was applied per page and the switch made it a per-table question.

    `present` was computed across `DATA.tables` at load, so a reference row in
    *any* table drew the control above *every* table. On the live site that put
    "Show reference systems (therapist-written and the papers' own models)"
    above the iCARE table, which has sixteen model rows and no reference rows at
    all -- the same switch wired to nothing that `show-published` was, one
    switch later.

    Two tables here, and the one drawn first has no reference row. Under the
    defect its control came from the other table.
    """
    from tnb import report

    data = report.build(
        [
            # Two comparability groups: different judges, so two tables.
            _row("x", "a-judge", 0.5),
            _row("y", "a-judge", 0.4),
            _row("x", "b-judge", 0.5),
            _row("therapist", "b-judge", 0.3, system_type="reference-human"),
        ]
    )
    assert len(data["tables"]) == 2, "the fixture is only about two tables"
    drawn_first = data["tables"][0]
    assert not any(row["system_type"] != "model" for row in drawn_first["rows"]), (
        "the table the page opens on must be the one with nothing to filter"
    )

    controls = _run(report.render_page(data), tmp_path, panel="controls")
    assert "show-reference" not in controls, (
        "the control belongs to the other table, not to this one"
    )


def test_the_notes_column_goes_when_every_row_says_the_same_thing(tmp_path):
    """One bit of information over sixteen header cells is not a column.

    On the iCARE table fifteen rows read 40/40 and one reads 39/39. A reader who
    scans that learns nothing fifteen times, so when the rows agree the count
    moves into the row's detail, where the other invariant facts live.
    """
    from tnb import report

    same = report.build([_row(s, "a-judge", 0.5) for s in ("x", "y", "z")])
    drawn = _run(report.render_page(same), tmp_path, panel="table-host")
    assert ">Notes<" not in drawn, "every row wrote the same number of notes"
    assert "which is why there is no Notes column" in drawn, "the fact moves, it does not vanish"


def test_the_notes_column_stays_when_one_row_differs(tmp_path):
    """The mirror, and the reason the column exists at all: the one row that is
    not like the others is exactly what it is for."""
    from tnb import report

    data = report.build(
        [
            _row("x", "a-judge", 0.5),
            _row("y", "a-judge", 0.5),
            _row("z", "a-judge", 0.5, n_sessions_generated=49),
        ]
    )
    drawn = _run(report.render_page(data), tmp_path, panel="table-host")
    assert ">Notes<" in drawn
    assert "49/50" in drawn


def test_an_expanded_row_spans_the_columns_the_table_actually_drew(tmp_path):
    """The colspan is computed from the columns, and hiding one without telling
    it leaves every expanded row a cell short.

    Counted from the rendered header rather than from the formula, so the test
    cannot agree with the bug by using the same arithmetic.
    """
    import re

    from tnb import report

    for rows in (
        [_row(s, "a-judge", 0.5) for s in ("x", "y", "z")],
        [_row("x", "a-judge", 0.5), _row("y", "a-judge", 0.5, n_sessions_generated=49)],
    ):
        drawn = _run(report.render_page(report.build(rows)), tmp_path, panel="table-host")
        headers = len(re.findall(r"<th\b", drawn.split("</thead>")[0]))
        spans = {int(n) for n in re.findall(r'class="detail" hidden><td colspan="(\d+)"', drawn)}
        assert spans == {headers}, f"colspan {spans} against {headers} headers"


def test_the_column_a_phone_keeps_on_screen_is_the_model_s_name(tmp_path):
    """The stylesheet's own comment says "The name column stays put".

    It pinned `:first-child`, which was the name until the Band column went in
    ahead of it. After that, a reader scrolling seventeen columns sideways on a
    phone kept a 2.5rem strip of bare band digits and lost the name -- the exact
    failure the rule was written to prevent. No test can see a selector pointing
    one column over by running the page, so this reads the selector.
    """
    from tnb import report

    style = _flat(report.render_page(report.build([_row("x", "a-judge", 0.5)])))

    assert "table[data-table] th.name, table[data-table] td.name { position: sticky;" in style, (
        "the pinned column is not the name column"
    )
    assert "table[data-table] th.rank, table[data-table] td.rank { position: static;" in style, (
        "the band cell is still pinned as well, and two columns cannot both be at left: 0"
    )
    assert "table[data-table] td:first-child {" not in style, (
        "pinned by position again, which is what put the band cell there"
    )
    assert '<th scope="col" class="name" data-sort="label">' in style, (
        "the heading carries no name class"
    )


def test_nothing_on_the_table_is_explained_only_by_hovering(tmp_path):
    """`title=` is a mouse affordance and this page is read on phones.

    Words, Marks and the reasoning-effort badge were the rest of what a tooltip
    was the only carrier of, after Band. Each says it in the legend now, and
    Marks says the two things a tooltip had no room for: what its badges mean,
    and that -- like Band -- it does not sort. The stripped-tooltip trick again:
    an assertion that can be satisfied by a `title=` proves nothing here.
    """
    from tnb import report

    rows = [
        _row("kimi-k3", "a-judge", 0.55),
        _row("gpt-5.6-sol", "a-judge", 0.44, settings=Settings(effort="high", note_words=300)),
    ]
    drawn = _flat(_run(report.render_page(report.build(rows)), tmp_path, panel="table-host"))
    visible = re.sub(r'title="[^"]*"', "", drawn)

    assert "Median words in this model" in visible, "the Words column is a heading and a number"
    assert "Conditions this row did not share with the others" in visible
    assert "these are labels, not an order" in visible, "Marks never says why it will not sort"
    assert "measured on the methods page" in visible, (
        "the self-preference panel moved and the pointer to it did not"
    )
    assert "in the panel below" not in drawn, "pointing at a panel this page no longer has"
    assert "reasoning-effort setting carries it beside its name" in visible


def test_the_second_figure_in_every_cell_says_what_it_is(tmp_path):
    """`both` sprinkles a triangle and a number into every cell of the table.

    What the second number is lived in the button's `title=`, which is the one
    place a reader who tapped that button cannot look.
    """
    from tnb import report

    data = _page_data(tmp_path)
    drawn = _flat(_run(report.render_page(data), tmp_path, panel="table-host", search="?compare=1"))
    visible = re.sub(r'title="[^"]*"', "", drawn)

    assert "Every figure now carries a second one" in visible
    assert "Nothing is averaged" in visible

    alone = _flat(_run(report.render_page(data), tmp_path, panel="table-host"))
    assert "Every figure now carries a second one" not in alone, (
        "said while no second figure is drawn"
    )


def test_the_completeness_caveat_reads_its_two_figures_off_the_table(tmp_path):
    """A denominator a reader cannot see the consequence of is a word, not a warning.

    The caveat says every rubric item is asked of every note. The half that
    makes that checkable -- how high the column actually goes, and where the
    note a human wrote landed under the same rule -- is computed from the rows
    the sentence is printed under. It used to be typed: the caveat ended "which
    is why every model here scores above the therapist on it", which is a claim
    about the data that no test held to the data and that a re-score could
    falsify without touching a character of it.

    **And the caveat itself was wrong until 2026-09-01**, which this test was
    pinning: it said the denominator is the whole 23-item rubric, where the
    figure is the equal-weighted mean of four section fractions over sections
    of 6, 5, 8 and 4. Recomputed the way the sentence described, seven of the
    nineteen systems change place. The assertion below is the corrected
    arithmetic and refuses the old one by name.
    """
    from tnb import report

    rows = [
        _row("x", "a-judge", 0.55),
        _row("y", "a-judge", 0.44),
        _row("therapist", "a-judge", 0.33, system_type="reference-human"),
    ]
    drawn = _flat(_run(report.render_page(report.build(rows)), tmp_path, panel="table-host"))

    assert "All 23 rubric items are asked of every note" in drawn, (
        "the caveat does not say that no item is excluded as inapplicable"
    )
    # Without the apostrophe: `esc` turns it into an entity in the rendered page.
    assert "equal-weighted mean of the note" in drawn and "four section fractions" in drawn, (
        "the caveat does not say how the figure is computed"
    )
    assert "denominator is the whole 23-item rubric" not in drawn, (
        "the caveat names a denominator the column does not use; recomputed that "
        "way, seven of the nineteen systems change place"
    )
    assert "the highest Completeness is 0.550 out of a possible 1.00" in drawn
    assert "the note a human clinician wrote scores 0.330 by the same rule" in drawn, (
        "the caveat gives the clinician's place in the drawn order, which any sort falsifies, "
        "rather than the figure they scored"
    )


def test_the_calibration_panel_says_whose_notes_the_judge_was_checked_on(tmp_path):
    """One number for the instrument hides whether it is the same instrument on
    every kind of note.

    Human ratings exist for three systems and no others, all three of them at
    the bottom of the table and all writing shorter notes than any ranked model.
    Split by whose note was read, the judge's agreement varies by more than the
    margin this page uses to call two agreement figures separable — and it is
    weakest on the therapist's notes, which is the row the most-quoted
    comparison depends on.
    """
    from tnb import report

    data = report.build([_row("x", "a-judge", 0.5)])
    data["calibration"] = {
        "judge_model": "a-judge",
        "judge_prompt_version": "v1",
        "notes": 150,
        "agreements": [
            {
                "name": "rubric_completeness",
                "statistic": "Cohen's kappa",
                "alpha": 0.60,
                "alpha_humans": 0.50,
                "judge": 0.60,
                "humans": 0.50,
                "n": 3448,
                "alpha_level": "nominal",
            }
        ],
        "per_criterion": [],
        "per_system": [
            {"system": "llama-3.1-70b", "judge": 0.606, "humans": 0.440, "n": 1150},
            {"system": "mistral-large-v2", "judge": 0.632, "humans": 0.523, "n": 1150},
            {"system": "therapist", "judge": 0.554, "humans": 0.544, "n": 1148},
        ],
    }
    drawn = _run(report.render_methods(data), tmp_path, panel="calibration-body")

    assert "Whose notes the judge was checked on" in drawn
    assert "No human has read a note written by any of the models" in drawn
    assert "0.078" in drawn, "the spread across the three, which exceeds the margin"
    assert "therapist" in drawn and "weakest on" in drawn


def test_every_page_offers_a_route_to_the_background_documents():
    """`docs/datasets.md`, `methodology.md`, `landscape.md` and `limitations.md`
    carry everything the tables rest on — where the corpora came from, that two
    of the three publish no licence, that the sessions are counselling
    demonstrations, that the iCARE expert note is 46% empty — and until
    2026-08-27 **not one of them was linked from anywhere on the site**.

    `limitations.md` was named three times and linked zero: prose inside a
    `<code>` tag is a file name, not a route. A reader on the leaderboard had no
    way to reach any of it.
    """
    from tnb import report

    data = report.build([_row("x", "a-judge", 0.5)])
    pages = {"index.html": report.render_page(data), "methods.html": report.render_methods(data)}
    try:
        import sys

        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import brief

        pages["brief.html"] = brief.render(brief.Data.load())
    except Exception:  # the briefing needs the published payload; skip if absent
        pass

    wanted = {"datasets.md", "methodology.md", "landscape.md", "limitations.md"}
    for name, html in pages.items():
        # By the document's own name, local route or absolute. The two pages
        # point at GitHub because this site serves `.md` as `text/markdown`,
        # so a relative link opened the file as unformatted text; `_links_in`
        # skips absolute hrefs by design and would have read that fix as the
        # route disappearing. What this test is for is that a route exists.
        static = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S)
        linked = {
            href.rsplit("/", 1)[-1]
            for href in re.findall(r'href="([^"]+)"', static)
            if href.endswith(".md")
        }
        assert wanted <= linked, f"{name} does not link {sorted(wanted - linked)}"

    for name in wanted:
        assert (REPO_ROOT / "docs" / name).exists(), f"{name} is linked and must exist"


def test_the_length_panel_is_drawn_and_not_merely_computed(tmp_path):
    """Testing `saturation.length_effect` is not testing the page.

    The first version of this change tested the analysis and left the panel
    unwired — removing `lengthEffect(s)` from `renderSaturation` kept every test
    green. Same defect class as the borrowed failure reasons, one commit later.
    """
    from tnb import report

    data = report.build([_row("x", "a-judge", 0.5)])
    data["saturation"] = {
        "judge_model": "a-judge",
        "sessions": 25,
        "corpus_sessions": 50,
        "verdict_counts": {"discriminating": 13},
        "criteria": [],
        "intervals": [],
        "indistinguishable": [["x"]],
        "narrowed_by": {},
        "still_scoring": [],
        "bootstrap": {"samples": 2000, "seed": 1, "paired": True},
        "length_effect": {
            "within_system": [{"system": "x", "rho": 0.35, "n": 49}],
            "within_conversation": {
                "median": 0.122,
                "positive": 31,
                "n": 50,
                "sign_test_p": 0.119,
            },
        },
    }
    drawn = _run(report.render_methods(data), tmp_path, panel="saturation-body")

    assert "Does completeness rise with how much the model wrote?" in drawn
    assert "31 of all 50" in drawn, "the denominator has to say which 50 it is"
    assert "does not survive" in drawn, "p = 0.119 is not a surviving effect"
    assert "publishes the <strong>length</strong>" in drawn or "publishes the" in drawn
    # The verdict above is one judge's, and the panel used to print it in bold
    # one sentence above its own statement that the two judges disagree about
    # it, with nothing to say whose it was.
    assert "a-judge" in drawn, "the panel does not say whose figures these are"


def test_the_panel_says_whether_the_two_leans_differ_from_each_other(tmp_path):
    """Two numbers in one table get compared, and +0.027 beside +0.018 reads as
    "GPT is the more partial judge". Their difference is +0.009 with an interval
    four times its own width, so it licenses nothing -- and the page said so
    nowhere, which left the comparison to be made by eye on two intervals that
    overlap."""
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
                "family": "google",
                "estimate": 0.018,
                "low": -0.010,
                "high": 0.047,
                "detected": False,
                "n_own": 3,
                "n_neutral": 12,
                "n_sessions": 25,
                "summary": "no detectable preference for Google models",
            },
            {
                "judge": "gpt-5.6-terra",
                "family": "openai",
                "estimate": 0.027,
                "low": -0.004,
                "high": 0.058,
                "detected": False,
                "n_own": 4,
                "n_neutral": 12,
                "n_sessions": 25,
                "summary": "no detectable preference for OpenAI models",
            },
        ],
        "difference": {
            "judge_a": "gemini-3.1-pro-preview",
            "judge_b": "gpt-5.6-terra",
            "estimate": 0.0092,
            "low": -0.0389,
            "high": 0.0578,
            "detected": False,
            "summary": "The two leans are not distinguishable from each other.",
        },
    }

    output = _run(report.render_methods(data), tmp_path, "preference")

    assert "not distinguishable from each other" in output, (
        "the difference between the two judges was computed and not drawn"
    )


def test_the_agreement_table_does_not_print_a_correlation_it_has_disowned(tmp_path):
    """The prose stopped quoting `organized`; the table went on printing 1.000.

    Eighteen of nineteen systems sat on 5.00, so the correlation was decided by
    the one that did not, and the row beside it read "0 of 19 placed
    differently" -- perfect agreement, from a column with nothing in it. A
    reader checking the sentence against the table would have found the table
    contradicting it.
    """
    data = _page_data(tmp_path)
    payload = dict(data["concordance"])
    track = next(iter(payload))
    entry = dict(payload[track])
    measures = [dict(m) for m in entry["measures"]]
    measures[0] = {
        **measures[0],
        "measure": "organized",
        "rho": 1.0,
        "moved": 0,
        "n_systems": 19,
        "tied": 18,
        "rankable": False,
        "furthest": None,
    }
    entry["measures"] = measures
    payload[track] = entry
    data["concordance"] = payload

    output = _flat(_run(report.render_methods(data), tmp_path, "concordance"))

    assert "1.000" not in output.split("organized")[1][:200], (
        "a measure that cannot order the systems still published a rank correlation"
    )
    assert "18 of 19 systems print the same number" in output
    assert "does not order them" in output


def test_a_row_with_part_answered_notes_says_why_its_sections_do_not_add_up(tmp_path):
    """Open a row and the four section figures do not average to the number
    above them. Nothing said why.

    They answer different questions: the row averages each note's own sections
    first, a section averages the notes that have it, and a part-answered note
    enters one denominator and not the other. Measured across the published
    tables, 34 rows with no partial notes agree to five decimal places and all
    18 rows with partial notes differ -- up to 0.029 on the therapist's row,
    which is visible at the precision printed.
    """
    from tnb import report

    partial = _row("x", "a-judge", 0.5)
    partial = replace(partial, n_sessions_partial=3, n_sessions_scored=50)
    partial = replace(
        partial,
        metrics=results.Metrics(
            headline={"completeness": 0.5},
            by_section={"plan": {"completeness": 0.6}, "subjective": {"completeness": 0.4}},
        ),
    )
    data = report.build([partial])

    host = _flat(_run(report.render_page(data), tmp_path, panel="table-host"))

    assert "will not average to the figure in the row above" in host
    assert "3 part-answered notes" in host, "the count is the size of the gap"


def test_a_row_with_no_part_answered_notes_says_nothing_of_the_kind(tmp_path):
    """Because there it does add up, and a caveat over a sum that is right
    teaches a reader to distrust a correct number."""
    from tnb import report

    whole = _row("x", "a-judge", 0.5)
    whole = replace(
        whole,
        n_sessions_partial=0,
        metrics=results.Metrics(
            headline={"completeness": 0.5},
            by_section={"plan": {"completeness": 0.5}, "subjective": {"completeness": 0.5}},
        ),
    )
    data = report.build([whole])

    host = _flat(_run(report.render_page(data), tmp_path, panel="table-host"))

    assert "will not average to the figure" not in host


def _calibrated(name: str, judge: float, humans: float, scales: list[float]) -> dict:
    """One `docs/judges.json` entry. Wrap it with `_judges_payload` before use."""
    return {
        "judge_model": name,
        "agreements": [
            {"name": "rubric_completeness", "judge": judge, "humans": humans},
            *({"name": f"likert_{n}", "judge": v, "humans": v} for n, v in enumerate(scales)),
        ],
    }


def _judges_payload(*entries: dict) -> dict:
    """The payload the page is actually served.

    `docs/judges.json` is a WRAPPER -- {notes, separable, judges: [...]} -- and
    `report.build` attaches the whole file. Two tests here handed the page a
    bare list instead, which is the shape the leaderboard's own lookup assumed,
    so the test and the bug agreed with each other and the published page threw
    `.find is not a function` on the first table and drew nothing at all.

    A helper rather than a literal in each test, so the next one cannot get it
    wrong in a way that agrees with a mistake in the template.
    """
    return {"notes": 150, "separable": {"margin": 0.05, "groups": []}, "judges": list(entries)}


def test_the_table_says_what_earned_the_ranking_column_its_job(tmp_path):
    """The page said which column orders the table and never said why that one.

    It is the only measure with a human anchor: on the rubric the judge agrees
    with a trained therapist more closely than two therapists agree with each
    other, while on the 1-5 scales those two barely agree at all. A reader who
    is told "ordered by completeness" and not told that has no way to know the
    choice was earned rather than arbitrary -- and asked exactly that.

    The two figures were written into the sentence, so the same 0.60 was drawn
    under `gpt-5.6-terra`'s table, where the judge and a therapist agree at
    0.52. Both clear the therapists' ceiling, so the argument held either way
    and only the number was wrong -- which is the kind that survives a reading.
    """
    from tnb import report

    data = report.build([_row("x", "a-judge", 0.5)])
    data["judges"] = _judges_payload(
        _calibrated("a-judge", 0.61, 0.50, [0.13, 0.19, 0.18]),
        _calibrated("another-judge", 0.52, 0.50, [0.11, 0.17, 0.16]),
    )
    host = _flat(_run(report.render_page(data), tmp_path, panel="table-host"))

    assert "checked against people" in host
    assert "0.61" in host and "0.50" in host, "the reader needs the two numbers, not the claim"
    assert "0.13" in host and "0.19" in host, "and the ceiling on the scales it did not pick"
    assert "0.52" not in host, "that is the other judge's agreement, and this is not its table"


def test_the_table_says_which_column_is_sorting_it_from_the_first_paint(tmp_path):
    """The header was clickable and said so only by turning the cursor.

    It carried a static "ranks" badge on the ranking column instead, which says
    which column the table *arrived* sorted by and goes on saying it after a
    reader sorts by another one. The badge is gone and the state is on the
    table, so the arrow can follow the click.
    """
    from tnb import report

    data = report.build([_row("x", "a-judge", 0.5)])
    host = _flat(_run(report.render_page(data), tmp_path, panel="table-host"))

    assert 'data-sorted="place"' in host, "the table does not say what sorted it"
    assert 'data-descending="1"' in host, "and which way round"
    assert 'class="ranks"' not in host.split("<tbody>")[0], "the badge outlived its job"


def test_a_wide_table_gets_a_scrollbar_a_reader_can_reach(tmp_path):
    """The only sideways scrollbar was under the table, a screen down from the
    columns it moves. The strip above it is the same bar, synced both ways.

    Only its presence and its place are checked here. Whether the two stay in
    step is a scroll event against a real layout, and the runner has neither --
    so that half is not covered by any test and is not claimed to be.
    """
    from tnb import report

    data = report.build([_row("x", "a-judge", 0.5)])
    host = _flat(_run(report.render_page(data), tmp_path, panel="table-host"))

    assert 'class="scroll-top"' in host, "no scrollbar above the table"
    assert host.index('class="scroll-top"') < host.index('class="scroll"'), (
        "the second scrollbar is below the table, where the first one already is"
    )
    assert 'aria-hidden="true"' in host, "an empty strip must not be read out as content"


def test_the_leaderboard_links_the_instruments_it_names(tmp_path):
    """A PDSQI-9 column with no way from this page to PDSQI-9.

    The licences table has always carried the links and it is on the other
    page, so a reader looking at a column had to know the methods page existed
    before they could find out what the column was. Drawn from the same list,
    so a source cannot be credited on one page and missing from the other.
    """
    data = _page_data(tmp_path)
    sources = _flat(_run(report.render_page(data), tmp_path, panel="sources"))

    # The page's own list, not the whole registry: a page credits the sources
    # its tables use, and this asserts none of those is missing from it.
    assert data["licences"], "the page credits nothing at all"
    for entry in data["licences"]:
        assert entry["url"] in sources, f"{entry['source']} is credited nowhere on this page"
        assert entry["source"] in sources


def test_both_judges_can_be_read_off_one_row(tmp_path):
    """Two judges were two tables, so "do these two agree about this row" meant
    opening two tabs and subtracting by hand.

    The second figure is the other judge's own score written as a distance, not
    an average of the two: this project does not average two instruments, and a
    single blended number would be exactly that.
    """
    data = _page_data(tmp_path)
    host = _flat(_run(report.render_page(data), tmp_path, panel="table-host", search="?compare=1"))

    # `_page_data` gives system x 0.9 under the first judge and 0.5 under the
    # second, so the distance is four tenths and it points down.
    assert "0.900" in host, "the judge whose table this is still owns the column"
    assert "0.400" in host, "the other judge's distance is not drawn"
    assert "▾" in host, "a gap with no direction is half a comparison"
    assert "0.700" not in host, "that is the mean of the two, which is not a number here"


def test_one_judge_at_a_time_stays_the_default(tmp_path):
    """The published ranking is one judge's ranking and has to read as that."""
    data = _page_data(tmp_path)
    host = _flat(_run(report.render_page(data), tmp_path, panel="table-host"))

    assert "0.900" in host
    assert 'class="gap' not in host, "the comparison drew itself without being asked"


def test_a_judge_with_no_published_calibration_gets_no_borrowed_figure(tmp_path):
    """The sentence names its gap rather than printing another judge's number.

    An absence is never a measurement: a table whose judge was never put in
    front of the two therapists has no anchor to quote, and quoting the judge
    that was is how one judge's 0.60 came to stand under another's table.
    """
    from tnb import report

    data = report.build([_row("x", "a-judge", 0.5)])
    data["judges"] = _judges_payload(
        _calibrated("a-different-judge", 0.61, 0.50, [0.13, 0.19, 0.18])
    )
    host = _flat(_run(report.render_page(data), tmp_path, panel="table-host"))

    assert "is not published here" in host
    assert "only column checked against people" not in host
    assert "0.61" not in host, "the figure belongs to a judge that did not write this table"


def test_a_judge_tried_and_not_chosen_is_named_rather_than_drawn(tmp_path):
    """`gemini-2.5-pro` was a calibration candidate. It put two extra tables of
    11 and 3 rows behind the judge switch -- two buttons offering a run nobody
    publishes from, one differing from the other only in a thinking budget.

    Withdrawn only where a panel judge has scored the same track: a candidate's
    rows are the only thing on a track nobody else has scored, and withdrawing
    them there would leave the track blank, which is worse than an extra button.
    """
    from tnb import judge, report

    panel = _row("x", judge.DEFAULT_MODEL, 0.5)
    candidate = _row("x", "gemini-2.5-pro", 0.4)

    both = report.build([panel, candidate])
    drawn = {t["versions"]["judge_model"] for t in both["tables"] if t["scored"]}
    assert drawn == {judge.DEFAULT_MODEL}, "a candidate judge was offered beside the panel"
    assert any(
        "tried during calibration" in report._superseded_sentence(gone)
        for gone in both["superseded"]
    ), "and the reader is not told where it went"

    alone = report.build([candidate])
    drawn = {t["versions"]["judge_model"] for t in alone["tables"] if t["scored"]}
    assert drawn == {"gemini-2.5-pro"}, "the only judge on a track is drawn, panel or not"


def test_the_blurb_is_not_measured_in_characters():
    """A measure in `ch` shrinks with the font size, and the blurb is set at
    .9rem -- so `max-width: 68ch` came out around half the card, next to a table
    and a lede that both run its full width. It read as a broken column.

    Pinned because the fix is invisible in the rendered HTML: the runner has no
    layout engine, so nothing else here would notice it coming back.
    """
    style = (REPO_ROOT / "src" / "tnb" / "templates" / "_style.html").read_text(encoding="utf-8")

    for selector in ("p.blurb", "footer"):
        rule = next(
            (line for line in style.splitlines() if line.strip().startswith(f"{selector} {{")),
            None,
        )
        assert rule, f"{selector} has no rule to check"
        assert "ch;" not in rule, (
            f"{selector} is measured in characters again: at this font size that is about "
            "half the card, beside a full-width table"
        )


def test_the_published_page_keeps_the_header_it_was_written_with(tmp_path):
    """The header is the template's, and nothing in the payload can say otherwise.

    There used to be a `page` block a payload could carry to rewrite the title,
    the sub-line and the links, and one page used it. It is gone, and this
    asserts the removal rather than the old behaviour: a payload that could
    carry a header would put the published page's own words through the same
    substitution and let a typo there change what `docs/` says.
    """
    data = _page_data(tmp_path)
    assert "page" not in data, "the payload can still carry a header of its own"
    summary = _run(report.render_page(data), tmp_path)
    assert "THREW" not in summary
    # Nothing writes to the two header nodes, so they are neither replaced nor
    # removed. That is the whole assertion. It named `methods-link` until that
    # node was taken off the page on purpose; `brief-link` is the same kind of
    # node -- static prose above the tables that no render function touches --
    # and asserting the removed one would have passed for the wrong reason.
    removed = next((line for line in summary.splitlines() if line.startswith("removed:")), "")
    assert "brief-link" not in removed, "the published page dropped its briefing link"
    assert "e-INFRA" not in _flat(_run(report.render_page(data), tmp_path, panel="page-sub"))


def test_the_published_page_actually_runs(tmp_path):
    """The strongest form of this file's question, asked of the real artefact.

    Every other test here builds a payload from fixtures. This one executes the
    script out of `docs/index.html` exactly as it was published, because the
    failure it exists for is one no fixture reproduced: `docs/judges.json` is a
    wrapper object, the leaderboard read it as a list, and the inline script
    died on the first table. The site served a title, three link boxes and no
    leaderboard -- for long enough that a reader reported it -- while this file
    was green, because `_page_data` set that field to None.

    Skipped rather than guessed when the page has not been built.
    """
    page = REPO_ROOT / "docs" / "index.html"
    if not page.exists():
        pytest.skip("docs/index.html is not built in this checkout")

    scripts = re.findall(r"<script[^>]*>(.*?)</script>", page.read_text(encoding="utf-8"), re.S)
    script = tmp_path / "published.js"
    script.write_text("\n".join(scripts), encoding="utf-8")

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the page cannot be executed here")
    finished = subprocess.run(
        [node, str(RUNNER), str(script)], capture_output=True, text=True, timeout=120
    )
    output = finished.stdout + finished.stderr
    assert "THREW" not in output, f"the published page throws: {output}"
    assert "table-host:" in output, f"the published page drew no table: {output}"


def test_the_leaderboard_draws_no_band_column_and_the_payload_keeps_the_bands(tmp_path):
    """The bands are a measurement and stay published; the column beside a
    different order does not. Three answers to "where does this row stand" sat
    on one table and disagreed by construction; the Band was computed on 25 of
    50 conversations under one judge and 42 under the other, seven of its
    deciding comparisons sit within three standard errors of the cut, and it did
    not follow the sort. The methods page keeps every one of those facts."""
    rows = [_row("kimi-k3", "a-judge", 0.55), _row("gemma4", "a-judge", 0.45)]
    saturations = [
        {
            "track": results.TRACK_TNEVAL,
            "judge_model": "a-judge",
            "judge_fingerprint": {"model": "a-judge", "thinking_budget": 256},
            "sessions": 50,
            "corpus_sessions": 50,
            "indistinguishable": [["kimi-k3"], ["gemma4"]],
        }
    ]
    data = report.build(rows, saturations)
    table = next(t for t in data["tables"] if t["track"] == results.TRACK_TNEVAL)
    assert table.get("groups"), "the bands left the payload; they are a measurement and stay"
    drawn = _flat(_run(report.render_page(data), tmp_path, panel="table-host"))
    assert '<td class="rank' not in drawn and 'class="rank"' not in drawn, (
        "a Band cell is still drawn on the leaderboard"
    )
    assert "share a Band" not in drawn and "Band on" not in drawn
    # With the band column gone the table still says what separates the rows:
    # the tested groups where docs/edges-<track>.json exists, and that nothing
    # has been tested where it does not.
    assert (
        "beaten by no tested comparison" in drawn or "has not been tested for this table" in drawn
    ), "with the band column gone the table must still say what the evidence separates"


def test_no_table_is_laid_out_as_a_grid():
    """`.grid` is `display: grid` for the definition pairs inside an opened row.

    A `<table class="grid">` on the methods page took that rule, and a table
    laid out as a grid came out 2952px wide inside an 1888px window and dragged
    the whole document sideways. The runner has no layout engine, so this reads
    the templates rather than the page.
    """
    for name in ("leaderboard.html", "methods.html"):
        text = (REPO_ROOT / "src" / "tnb" / "templates" / name).read_text(encoding="utf-8")
        assert '<table class="grid"' not in text, f"{name}: a table laid out as a grid"


def _icare_two_judges() -> list[Row]:
    """One iCARE table per judge: the same automatic figures, a different TRACE.

    Which is not a fixture convenience -- it is what the rows on disk look
    like. ROUGE-L, BERTScore and the two temporal columns are computed from the
    note and the expert note, so re-scoring a note with another judge cannot
    move them.
    """
    automatic = {"rouge_l": 0.19, "bertscore": 0.82, "temporal_past": 1.0, "temporal_next": 0.36}
    return [
        _row(
            system,
            judge_model,
            0.5,
            track=results.TRACK_ICARE,
            prompt_version="icare-zeroshot-v1",
            judge_prompt_version="icare-trace-v1",
            metrics=Metrics(headline={**automatic, "trace": trace}),
        )
        for judge_model, traces in (
            ("judge-a", {"x": 4.98, "y": 4.76}),
            ("judge-b", {"x": 4.02, "y": 3.59}),
        )
        for system, trace in traces.items()
    ]


def test_a_column_no_judge_decided_carries_no_second_figure(tmp_path):
    """`both` used to write a delta into every cell of the iCARE table.

    Four of its five columns are computed from the note and the expert note, so
    both judges' tables hold the same number and the delta read `= 0.000` --
    the two judges agreeing perfectly, eighteen rows at a time, about a figure
    neither of them produced. It is the tautology `icare.JUDGE_MEASURES` keeps
    off the concordance panel, and it made the one real comparison on the table
    look like the odd one out.
    """
    from tnb import report

    data = report.build(_icare_two_judges())
    data["calibration"] = None
    data["similarity_example"] = None
    data["saturation"] = None
    data["judges"] = None
    host = _flat(_run(report.render_page(data), tmp_path, panel="table-host", search="?compare=1"))
    visible = re.sub(r'title="[^"]*"', "", host)

    assert "4.98" in visible and "0.96" in visible, "TRACE is compared, and it is the point"
    # `=` is how the delta writes "the two judges landed on the same number",
    # and 0.000 is the only figure it could ever carry on these four columns.
    # Matched with its sign because 0.000 is also a legend's example of what
    # ROUGE-L does to a correct paraphrase.
    assert "=0.000" not in visible, (
        "a delta of zero on a column no judge answered reads as perfect agreement"
    )
    # One gap per row, on the one column a judge decided.
    assert visible.count('class="gap') == 2, "a second figure appeared on an unjudged column"
    # And the heading says why the others have none, rather than leaving four
    # columns looking short of a number.
    assert visible.count("same under both judges") == 4
    assert "Only TRACE carries a second figure" in visible


def test_a_table_whose_judge_decided_every_column_still_compares_all_of_them(tmp_path):
    """The gate is `judged`, not the track. On the rubric the judge answers
    every column, so every column keeps its second figure."""
    from tnb import report

    data = _page_data(tmp_path)
    host = _flat(_run(report.render_page(data), tmp_path, panel="table-host", search="?compare=1"))
    visible = re.sub(r'title="[^"]*"', "", host)

    assert "Every figure now carries a second one" in visible
    assert "same under both judges" not in visible, "said where nothing is exempt"


# --- are the committed pages the ones the code produces today? ----------------


def test_the_published_pages_and_readme_are_current(tmp_path):
    """`docs/index.html`, `docs/methods.html` and the README block, rebuilt.

    `docs/brief.html` got this test on 2026-09-03 and the two pages it sits
    beside did not, which left the larger hole: `tnb report` writes all three,
    so a rebuild that is not committed leaves the site serving a page the
    repository can no longer produce, and nothing failed.

    Rendered into a copy of `docs/` so the artefacts the build reads -- the
    saturation files, the calibration, the judges, the preference, the edges --
    are the published ones and only the output is new.
    """
    rows = results.load()
    if not rows:
        pytest.skip("no rows in results/ in this checkout")
    docs = REPO_ROOT / "docs"
    if not (docs / "leaderboard.json").exists():
        pytest.skip("nothing published in this checkout")

    for path in docs.glob("*.json"):
        shutil.copy(path, tmp_path / path.name)
    readme = tmp_path / "README.md"
    shutil.copy(REPO_ROOT / "README.md", readme)

    report.write(rows, docs_dir=tmp_path, readme=readme)

    for name in (report.PAGE_PATH.name, report.METHODS_PATH.name):
        assert (tmp_path / name).read_text(encoding="utf-8") == (docs / name).read_text(
            encoding="utf-8"
        ), f"docs/{name} is stale against results/ — run `uv run tnb report`"
    assert readme.read_text(encoding="utf-8") == (REPO_ROOT / "README.md").read_text(
        encoding="utf-8"
    ), "the README block is stale against results/ — run `uv run tnb report`"


def test_the_published_pdf_is_the_print_of_the_published_briefing():
    """The hole one level under the briefing's own freshness test.

    `docs/therapy-note-bench.pdf` is committed and is what leaves this
    repository for people who never open the site. Comparing two PDFs byte for
    byte says nothing -- Chrome stamps them -- so `tools/pdf.py` records the
    digest of the page it printed, and this compares that against the page as
    committed. It fails exactly when the brief was rebuilt and the PDF was not.
    """
    docs = REPO_ROOT / "docs"
    brief_html, pdf = docs / "brief.html", docs / "therapy-note-bench.pdf"
    if not pdf.exists() or not brief_html.exists():
        pytest.skip("no briefing or no PDF in this checkout")

    stamp = pdf.with_suffix(pdf.suffix + ".sha256")
    assert stamp.exists(), "the PDF carries no record of what it was printed from — run `make pdf`"
    printed = stamp.read_text(encoding="utf-8").split()[0]
    assert printed == hashlib.sha256(brief_html.read_bytes()).hexdigest(), (
        "docs/therapy-note-bench.pdf was printed from a different brief.html — run `make pdf`"
    )


def test_the_main_page_makes_no_standing_invitation_to_the_methods_page():
    """One link removed on purpose, five kept on purpose.

    The paragraph under the tables was the only thing that sent a reader who
    had asked no question to a page of answers. It is gone. The five links
    inside sentences are not, and that is the half worth pinning: each sits in
    the claim it supports -- how the order was built, how the comparisons were
    tested, the calibration, the licences, the withdrawn rows -- so a reader
    checking one number still reaches the panel that answers for it. Removing
    those too would look like the same edit going one step further, and would
    leave five published claims pointing at nothing.
    """
    template = REPO_ROOT / "src" / "tnb" / "templates" / "leaderboard.html"
    page = template.read_text(encoding="utf-8")

    assert 'id="methods-link"' not in page, "the standing invitation to the methods page is back"
    assert ">How this was measured →</a>" not in page, "its wording is back under another id"

    anchors = sorted(set(re.findall(r'href="methods\.html(#[a-z]+)"', page)))
    assert anchors == ["#calibration", "#groups", "#licences", "#ordering", "#withdrawn"], (
        f"the links that carry a claim to its evidence have changed: {anchors}"
    )


def test_the_documents_are_linked_where_a_browser_renders_them():
    """A relative `.md` href on this page opens as unformatted text.

    GitHub Pages serves `docs/*.md` as `text/markdown`, so all five of these
    opened with their hashes and pipes showing -- checked with `curl` against
    the published site on 2026-09-03. The blob URL renders the same file. This
    fails if a relative one comes back, and it also fails if a link points at a
    document this repository does not have.
    """
    template = REPO_ROOT / "src" / "tnb" / "templates" / "leaderboard.html"
    page = template.read_text(encoding="utf-8")

    bare = sorted(set(re.findall(r'href="([a-z][a-z-]*\.md)"', page)))
    assert not bare, f"linked as raw markdown, which the site serves as text: {bare}"

    blob = sorted(
        re.findall(
            r'href="https://github\.com/JanNehyba/therapy-note-bench/blob/main/docs/([a-z-]+\.md)"',
            page,
        )
    )
    assert blob == [
        "datasets.md",
        "landscape.md",
        "limitations.md",
        "methodology.md",
        "models-snapshot.md",
    ], f"the five documents the footer introduces have changed: {blob}"
    for name in blob:
        assert (REPO_ROOT / "docs" / name).exists(), (
            f"{name} is linked and is not in this repository"
        )


def test_the_masthead_draws_the_counts_it_was_given(tmp_path):
    """The sentence under the title, as a reader sees it.

    `test_docs_figures.py` binds the counts to the tables; this binds the
    sentence to the counts. The static fallback in the template says the same
    thing without them, so a payload with no masthead leaves prose rather than
    a hole -- and that is the only reason the fallback exists.
    """
    data = _page_data(tmp_path)
    data["masthead"] = {
        "models": 4,
        "notes": 1234,
        "sessions": 90,
        "judges": 2,
        "instruments": 3,
    }
    # Whitespace-normalised: the tag returns the sentence with the template's
    # own wrapping in it, which a browser collapses and a substring match does
    # not.
    drawn = " ".join(_run(report.render_page(data), tmp_path, panel="page-sub").split())

    assert "1,234" in drawn, "the note count is not drawn, or not with a thousands separator"
    assert ">4</strong> psychotherapy session notes" not in drawn, "the two counts are swapped"
    assert "<strong>4</strong> models" in drawn
    assert "three published instruments" in drawn
    assert "two independent LLM judges" in drawn, (
        "a reader who does not know this repository reads 'judge' as a person"
    )


def test_the_tables_apparatus_folds_and_its_findings_do_not(tmp_path):
    """Eleven blocks stood between the leaderboard table and the next section:
    how the order was built, an endpoint note, the Group definition and six
    column glosses. A reader wanting to know which model met all of it first.

    What stays in the open is about rows they can see -- which of them are not
    models under test, and how far the other judge moves them. The rest folds,
    the same way the profile table's apparatus does.
    """
    drawn = _run(_page(tmp_path), tmp_path, panel="table-host")
    if "<details" not in drawn:
        pytest.skip("this payload draws no apparatus to fold away")

    head, _, folded = drawn.partition("<details")
    after_table = head[head.rfind("</table>") :]

    assert "agree on the shape of this ranking" in after_table, (
        "the finding about the two judges is folded away"
    )
    for apparatus in ("Ordered by", '<dl class="measures">'):
        assert apparatus in folded, f"{apparatus!r} is drawn in the open rather than folded"
    assert "<summary>" in folded
    assert '<dl class="measures">' not in after_table, (
        "the column glossary is drawn twice, or was never folded"
    )


def test_the_open_notes_say_which_kind_of_judge(tmp_path):
    """ "The two judges agree" reads as two people to anybody who has not seen
    this repository, and this note is one of the two that stay in the open.
    """
    drawn = _run(_page(tmp_path), tmp_path, panel="table-host")
    head = drawn.partition("<details")[0]
    after_table = head[head.rfind("</table>") :]
    if "judge" not in after_table.lower():
        pytest.skip("the open notes mention no judge in this payload")
    assert "LLM judge" in after_table, "the open notes say 'judge' with nothing saying what kind"


def test_the_reference_note_says_why_they_are_ranked_once(tmp_path):
    """ "Scored by the identical protocol" was said inside each half of the
    sentence and then again for both -- three times in four lines.
    """
    drawn = _run(_page(tmp_path), tmp_path, panel="table-host")
    head = drawn.partition("<details")[0]
    after_table = head[head.rfind("</table>") :]
    if "Not every row is a model under test" not in after_table:
        pytest.skip("this payload draws no reference rows")
    assert after_table.count("identical protocol") == 1, (
        "the reason the reference rows are ranked is restated within its own sentence"
    )
