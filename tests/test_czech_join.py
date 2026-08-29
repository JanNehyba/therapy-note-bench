"""The English-to-Czech join, and the two ways nine points can lie.

Offline: the correlations here are computed over lists written in this file.
"""

from __future__ import annotations

import sys

import pytest

from tnb.config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tools"))

import czech_join  # noqa: E402


def test_a_flat_column_is_not_correlated_with_anything():
    """Every model scoring 5.00 is the shape that put `organized` on the English
    page reporting a perfect judge agreement. A correlation over it is decided
    by whichever single model is not at the ceiling, or by nothing at all."""
    varied = [1.0, 2.0, 3.0, 4.0, 5.0]
    flat = [5.0] * 5

    assert czech_join.correlate(flat, varied) is None
    assert czech_join.correlate(varied, flat) is None
    assert czech_join.correlate(flat, flat) is None
    assert czech_join.correlate(varied, varied) is not None


def test_too_few_points_is_not_a_correlation():
    assert czech_join.correlate([1.0, 2.0], [1.0, 2.0]) is None


def test_the_p_value_is_exact_at_this_sample_size():
    """Nine models is 362,880 relabellings and they are all enumerated. An
    approximation would be defensible and would also mean the number moves
    between runs, which invites re-running until it is small."""
    a = [float(n) for n in range(9)]
    result = czech_join.correlate(a, a)

    assert result["exact"] is True
    assert result["n"] == 9
    assert result["rho"] == 1.0
    # Two of 362,880 orderings reach |rho| = 1: the identity and the reversal.
    assert result["p"] < 0.001


def test_a_reversed_ordering_is_as_significant_as_an_identical_one():
    """The test is two-tailed. "English predicts the opposite of Czech" would be
    a finding, not a null result, and hiding it behind a one-tailed test would
    be choosing the direction after seeing the data."""
    a = [float(n) for n in range(9)]
    forward = czech_join.correlate(a, a)
    backward = czech_join.correlate(a, list(reversed(a)))

    assert backward["rho"] == -1.0
    assert backward["p"] == forward["p"]


def test_noise_does_not_come_back_significant():
    """The guard against the thing nine points do best. This ordering was not
    chosen to fail -- it is what a middling shuffle looks like."""
    a = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
    b = [3.0, 7.0, 1.0, 9.0, 4.0, 2.0, 8.0, 5.0, 6.0]
    result = czech_join.correlate(a, b)

    assert abs(result["rho"]) < 0.5
    assert result["p"] > 0.05


def test_ties_are_ranked_at_their_average_and_not_dropped():
    """A Czech column where three models print the same value still ranks the
    others. Dropping the tied rows would silently shrink an already small n."""
    a = [1.0, 2.0, 2.0, 2.0, 5.0, 6.0]
    b = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    result = czech_join.correlate(a, b)

    assert result["n"] == 6, "no row was dropped for being tied"
    assert result["rho"] > 0.8


def test_the_confound_is_written_down_rather_than_left_to_the_reader():
    """The English scores are over 50 conversations and the Czech over the ten
    that were translated. It cannot be removed without recomputing the English
    side, so it is stated."""
    assert "two standings" in czech_join.CONFOUND
    assert "50 AnnoMI conversations" in czech_join.CONFOUND
    assert "both judges" in czech_join.READING
    assert "unmeasured" in czech_join.READING


# --- the briefing's grouping ------------------------------------------------


def _row(**over):
    """A minimal scored Czech row."""
    from tnb import results

    fields = {
        "track": results.TRACK_CZECH_REAL,
        "system_id": "a-model",
        "system_type": "model",
        "system_label": "a-model",
        "provider": "einfra",
        "harness_version": "0.6.0",
        "prompt_version": "czech-soap-v1",
        "judge_model": "gemini-3.1-pro-preview",
        "judge_prompt_version": "czech-criteria-v1",
        # A group that names a judge and records no settings for it is
        # withdrawn rather than drawn, so the fixture has to record some.
        "judge_settings": {"model": "gemini-3.1-pro-preview", "thinking_budget": 2048},
        "n_sessions_attempted": 10,
        "n_sessions_generated": 10,
        "n_sessions_scored": 10,
        "metrics": results.Metrics(headline={"diacritics": 1.0}),
    }
    fields.update(over)
    return results.Row(**fields)


def test_one_table_per_comparability_group_not_per_judge():
    """Two rubric versions under one heading print every model twice, from two
    instruments. The briefing keyed its tables on the track and the judge --
    two of the six fields `COMPARABILITY_KEYS` names -- and that held only
    while there was one rubric. `quotes` becoming a count made a second."""
    import re

    import czech_brief

    rows = [
        _row(judge_prompt_version="czech-criteria-v1", scored_at="2026-08-28T10:00:00Z"),
        _row(judge_prompt_version="czech-criteria-v2", scored_at="2026-08-28T12:00:00Z"),
        _row(
            system_id="b-model",
            judge_prompt_version="czech-criteria-v2",
            scored_at="2026-08-28T12:00:00Z",
        ),
    ]
    page = czech_brief.build(rows)

    tables = re.findall(r"<tbody>(.*?)</tbody>", page, re.S)
    assert tables, "something was drawn"
    for body in tables:
        models = re.findall(r"<tr><td>([a-z0-9.\-]+)</td>", body)
        assert len(models) == len(set(models)), "a model appears twice in one table"


def test_the_rubric_a_table_was_measured_with_is_always_named():
    """It used to be printed only when two versions were on the page, which is
    the wrong way round: a reader cannot tell from a lone table which
    instrument produced it, and that is exactly when they would assume."""
    import czech_brief

    page = czech_brief.build([_row(), _row(system_id="b-model")])
    assert "rubric czech-criteria-v1" in page
    assert "Not drawn" not in page, "nothing was superseded"


def test_two_rubric_versions_do_not_collide_into_one_table_id():
    """`report.build` asserts that table ids are distinct, and the id was built
    from four things where six decide a group. Two rubric versions of one track
    under one judge produced one id, and the page stopped rather than drawing
    them -- which is the assert doing its job and the id not doing its own.

    The older version is no longer drawn beside the newer, so this exercises the
    id rather than the page: the property that matters is that the version is
    part of the id at all, and it would matter again the moment two versions are
    both current -- which is what a second corpus at a new rubric would be.
    """
    from tnb import report

    def table_of(version: str) -> dict:
        row = _row(judge_prompt_version=version)
        return {
            "track": row.track,
            "versions": {
                "judge_model": row.judge_model,
                "judge_prompt_version": row.judge_prompt_version,
                "harness_version": row.harness_version,
                "prompt_version": row.prompt_version,
                "judge_settings": row.judge_settings,
            },
        }

    first = report._table_id(table_of("czech-criteria-v1"))
    second = report._table_id(table_of("czech-criteria-v2"))

    assert first != second
    assert "czech-criteria-v1" in first
    assert "czech-criteria-v2" in second


def test_a_superseded_rubric_is_named_by_the_tables_too():
    """The briefing named the older rubric and the tables drew it, from the same
    file on the same morning: four tables a track, two judge buttons each
    carrying the same words, and nothing saying which held the older questions.
    """
    from tnb import report, results

    old = _row(judge_prompt_version="czech-criteria-v1", scored_at="2026-08-28T10:00:00Z")
    new = _row(judge_prompt_version="czech-criteria-v2", scored_at="2026-08-28T12:00:00Z")
    groups = results.comparable_groups(results.latest([old, new]))
    drawn, gone = report._current_groups(groups)

    assert len(drawn) == 1
    assert next(iter(drawn.values()))[0].judge_prompt_version == "czech-criteria-v2"
    assert len(gone) == 1 and gone[0]["reasons"] == ["rubric"]
    assert gone[0]["current_judge_prompt_version"] == "czech-criteria-v2"


def test_a_superseded_rubric_is_named_and_not_drawn():
    """What the published English page does with an older harness: name it,
    do not put it beside the current one. Drawing both invites a reader to
    compare two instruments as if they were two attempts at one."""
    import czech_brief

    old = _row(judge_prompt_version="czech-criteria-v1", scored_at="2026-08-28T10:00:00Z")
    new = _row(judge_prompt_version="czech-criteria-v2", scored_at="2026-08-28T12:00:00Z")
    page = czech_brief.build([old, new])

    assert page.count("rubric czech-criteria-v2") == 1
    assert "rubric czech-criteria-v1" not in page
    assert "Not drawn" in page and "czech-criteria-v1" in page


def test_both_judges_of_the_current_rubric_survive_finishing_apart():
    """Two judges finish minutes apart, so "newest" cannot be one timestamp
    without dropping whichever finished first. It is the newest *rubric*."""
    import czech_brief

    page = czech_brief.build(
        [
            _row(judge_prompt_version="czech-criteria-v1", scored_at="2026-08-28T10:00:00Z"),
            _row(
                judge_prompt_version="czech-criteria-v2",
                judge_model="gemini-3.1-pro-preview",
                scored_at="2026-08-28T12:00:00Z",
            ),
            _row(
                judge_prompt_version="czech-criteria-v2",
                judge_model="gpt-5.6-terra",
                judge_settings={"model": "gpt-5.6-terra", "effort": "medium"},
                scored_at="2026-08-28T11:55:00Z",
            ),
        ]
    )
    assert "gemini-3.1-pro-preview" in page
    assert "gpt-5.6-terra" in page
    assert page.count("rubric czech-criteria-v2") == 2


# --- the Czech briefing -----------------------------------------------------


def test_the_briefing_renders_in_czech_with_nothing_left_in_english():
    """The document is handed to Czech readers, so it is written in Czech --
    and `_t` raises rather than falling back, because the failure that matters
    is a page that is Czech where a reader looks first and English in the
    caveats, which is where the reader who most needs them stops."""
    import czech_brief

    rows = [_row(), _row(system_id="b-model")]
    before = czech_brief.LANG
    try:
        czech_brief.LANG = "cs"
        page = czech_brief.build(rows)
    finally:
        czech_brief.LANG = before

    # The expected Czech comes from the dictionary rather than being retyped
    # here: a literal would drift from it, and this file would then need to be
    # on the diacritic scanner's allow-list to hold a copy of it.
    from czech_brief_cs import CS

    heading = "Does it separate the models?"
    assert CS[heading] in page, "a table heading is in Czech"
    assert heading not in page


def test_a_missing_translation_stops_the_run_rather_than_leaking_english():
    import czech_brief

    before = czech_brief.LANG
    try:
        czech_brief.LANG = "cs"
        with pytest.raises(czech_brief.Untranslated):
            czech_brief._t("a sentence nobody has translated yet")
    finally:
        czech_brief.LANG = before


def test_english_stays_english_and_costs_no_lookup():
    import czech_brief

    assert czech_brief.LANG == "en"
    assert czech_brief._t("anything at all") == "anything at all"


# --- printing ---------------------------------------------------------------


def test_the_pdf_step_refuses_to_report_a_file_it_did_not_write(tmp_path, monkeypatch):
    """Existence was the whole check, so a locked target -- a PDF open in a
    viewer, which Windows locks -- left the previous document in place and the
    step reported it as this run's output. That happened to a document that had
    already been handed over."""
    import subprocess

    import pdf

    source = tmp_path / "page.html"
    source.write_text("<p>hello</p>", encoding="utf-8")
    target = tmp_path / "out.pdf"
    target.write_bytes(b"the previous document")

    monkeypatch.setattr(pdf, "find_browser", lambda: "chrome")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a[0], 0, "", "could not write"),
    )

    code = pdf.main(["--source", str(source), "--target", str(target)])

    assert code == 1, "a stale file is not a successful print"
    assert target.read_bytes() == b"the previous document", "and it is left alone"
