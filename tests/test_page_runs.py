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
from tnb.config import REPO_ROOT
from tnb.results import Metrics, Row

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
    data["judges"] = None
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


def _run(page: str, tmp_path: Path, panel: str | None = None) -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the page cannot be executed here")

    script = tmp_path / "page.js"
    script.write_text(
        "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", page, re.S)), encoding="utf-8"
    )
    finished = subprocess.run(
        [node, str(RUNNER), str(script), *([panel] if panel else [])],
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

    assert "tables: " in _run(report.render_page(data), tmp_path), "the tables are the leaderboard"

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

    output = _run(report.render_methods(data), tmp_path)

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

    output = _run(report.render_methods(data), tmp_path)

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


def test_a_filter_appears_for_the_rows_that_need_one(tmp_path):
    """The mirror: a reference row brings its control with it."""
    from tnb import report

    data = report.build(
        [
            _row("x", "a-judge", 0.5),
            _row("therapist", "a-judge", 0.3, system_type="reference-human"),
        ]
    )
    controls = _run(report.render_page(data), tmp_path, panel="controls")

    assert "show-reference" in controls
    assert "show-published" not in controls, "still nothing published to show"


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
        if "empty and not removed:" not in output:
            continue
        left = output.split("empty and not removed:")[-1].strip()
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
    ranking = next(m for m in found["measures"] if m["measure"] == found["ranking_measure"])
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

        here = far["rank_a"] if judge == found["judge_a"] else far["rank_b"]
        assert f"{here}" in finished.stdout.split("in this table")[0][-12:], (
            f"viewing {judge}, the rank before 'in this table' must be its own"
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
        linked = {target for target, _ in _links_in(html, name) if target.endswith(".md")}
        assert wanted <= linked, f"{name} does not link {sorted(wanted - linked)}"

    for name in wanted:
        assert (REPO_ROOT / "docs" / name).exists(), f"{name} is linked and must exist"
