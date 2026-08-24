"""Rendering rows into a table people will quote.

The failure mode this guards against is not a crash — it is a table that looks
right and says something false: two judges in one ranking, a model's missing
sessions rounded away, or a paper's number sorted next to ours.
"""

from __future__ import annotations

import json

import pytest

from tnb import report, results
from tnb.results import Metrics, Row


def _row(**overrides) -> Row:
    base = {
        "track": results.TRACK_TNEVAL,
        "system_id": "gemma4",
        "system_type": "model",
        "provider": "einfra",
        "prompt_version": "tneval-soap-v1",
        "n_sessions_attempted": 50,
        "n_sessions_generated": 50,
    }
    return Row(**{**base, **overrides})


def _scored(system_id: str, completeness: float, **overrides) -> Row:
    judged = {
        "judge_model": "claude-opus-5",
        "judge_prompt_version": "tneval-rubric-v1",
        "n_sessions_scored": 50,
        "metrics": Metrics(headline={"completeness": completeness}),
    }
    return _row(system_id=system_id, **{**judged, **overrides})


# --- what may share a table -------------------------------------------------


def test_two_judges_render_as_two_tables():
    """Not two rows in one. A reader who sorts that column would be comparing
    two different referees."""
    data = report.build(
        [
            _scored("gemma4", 0.6),
            _scored("glm-5.2", 0.7, judge_model="some-other-judge"),
        ]
    )
    assert len(data["tables"]) == 2


def test_both_tracks_render_and_tneval_comes_first():
    data = report.build(
        [_row(), _row(track=results.TRACK_ICARE, prompt_version="icare-zeroshot-v1")]
    )
    assert [table["track"] for table in data["tables"]] == [
        results.TRACK_TNEVAL,
        results.TRACK_ICARE,
    ]


def test_each_track_gets_its_own_columns():
    """iCARE reports ROUGE-L, BERTScore, TRACE and temporal side by side; the
    source paper found the first two disagree with expert preference."""
    data = report.build([_row(track=results.TRACK_ICARE, prompt_version="icare-zeroshot-v1")])
    keys = [column["key"] for column in data["tables"][0]["columns"]]
    assert keys == ["rouge_l", "bertscore", "trace", "temporal"]


# --- ordering and coverage --------------------------------------------------


def test_the_best_model_is_first_and_unscored_rows_sink():
    data = report.build([_scored("a", 0.4), _scored("b", 0.9), _scored("c", 0.6)])
    assert [row["label"] for row in data["tables"][0]["rows"]] == ["b", "c", "a"]


def test_a_partial_run_is_never_hidden_by_the_heading():
    """The title says what the protocol is; the count says what was run. A
    3-session smoke must not appear under a heading claiming 40."""
    data = report.build(
        [
            _row(
                track=results.TRACK_ICARE,
                prompt_version="icare-zeroshot-v1",
                n_sessions_attempted=3,
                n_sessions_generated=3,
            )
        ]
    )
    table = data["tables"][0]
    assert "3" not in table["title"] and "40" not in table["title"]
    assert table["rows"][0]["n_attempted"] == 3


def test_a_models_lost_sessions_reach_the_table_with_their_reason():
    """gpt-oss-120b's low count is a format failure, not a clinical one, and a
    reader has to be able to see that before comparing scores."""
    data = report.build(
        [
            _row(
                system_id="gpt-oss-120b",
                n_sessions_generated=42,
                n_failed=8,
                failure_reasons={"answer did not contain a SOAP dictionary": 8},
            )
        ]
    )
    row = data["tables"][0]["rows"][0]
    assert (row["n_generated"], row["n_attempted"], row["n_failed"]) == (42, 50, 8)
    assert row["failure_reasons"]["answer did not contain a SOAP dictionary"] == 8


# --- the breakdown ----------------------------------------------------------


def test_a_row_carries_its_section_and_criterion_breakdown_to_the_page():
    row = _scored(
        "gemma4",
        0.6,
        metrics=Metrics(
            headline={"completeness": 0.6},
            by_section={"plan": {"completeness": 0.4}, "subjective": {"completeness": 0.8}},
            detail={"subjective-chief-complaint": 0.9},
        ),
    )
    rendered = report.build([row])["tables"][0]["rows"][0]

    assert list(rendered["by_section"]) == ["subjective", "plan"], "SOAP order, not alphabetical"
    assert rendered["detail"]["subjective-chief-complaint"] == 0.9


def test_an_unscored_table_says_so():
    data = report.build([_row()])
    assert data["tables"][0]["scored"] is False


# --- README -----------------------------------------------------------------


def test_the_readme_shows_models_only_and_says_where_the_rest_is():
    """The papers' numbers and the therapist baseline belong on the page; a
    README with 23 criteria in it stops being read."""
    section = report.render_readme_section(
        report.build(
            [
                _scored("gemma4", 0.6),
                _scored("therapist", 0.8, system_type="reference-human"),
                _scored("mistral-large-v2", 0.5, system_type="published"),
            ]
        )
    )
    assert "gemma4" in section
    assert "therapist" not in section
    assert "mistral-large-v2" not in section
    assert "full leaderboard" in section


def test_the_readme_prints_a_dash_rather_than_a_zero_for_a_missing_score():
    """A model that has not been judged has no score. Zero is a claim."""
    section = report.render_readme_section(report.build([_row()]))
    assert "—" in section
    assert "0.000" not in section


def test_the_readme_edit_touches_only_the_marked_block(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Title\n\nbefore\n\n<!-- LEADERBOARD:BEGIN -->\nold\n<!-- LEADERBOARD:END -->\n\nafter\n",
        encoding="utf-8",
    )
    report.update_readme("new table", readme)

    updated = readme.read_text(encoding="utf-8")
    assert "before" in updated and "after" in updated
    assert "old" not in updated and "new table" in updated


def test_a_readme_without_markers_fails_loudly(tmp_path):
    """Silently appending a table to the end of a README is worse than failing."""
    readme = tmp_path / "README.md"
    readme.write_text("# Title\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="marker"):
        report.update_readme("x", readme)


# --- the page ---------------------------------------------------------------


def test_the_page_is_self_contained_and_carries_its_data(tmp_path):
    page = report.render_page(report.build([_scored("gemma4", 0.61)]))
    assert "__DATA__" not in page
    assert "gemma4" in page
    assert "<script src" not in page and "<link" not in page, "no external requests"


def test_the_page_keeps_the_caveats_attached_to_the_numbers():
    """Faithfulness has near-zero human agreement and TRACE has no human anchor
    at all. Both have to be visible next to the column, not in a doc nobody
    opens."""
    page = report.render_page(report.build([_row()]))
    assert "Krippendorff" in page
    assert "no human anchor" in page


def test_rendering_twice_produces_the_same_bytes(tmp_path):
    """A report that churns on every run makes its own diffs unreadable and
    turns every workflow run into a commit."""
    rows = [_scored("gemma4", 0.61)]
    readme = tmp_path / "README.md"
    readme.write_text("<!-- LEADERBOARD:BEGIN -->\nx\n<!-- LEADERBOARD:END -->\n", encoding="utf-8")

    report.write(rows, docs_dir=tmp_path / "docs", readme=readme)
    first = (tmp_path / "docs" / "index.html").read_bytes()
    first_json = (tmp_path / "docs" / "leaderboard.json").read_bytes()

    report.write(rows, docs_dir=tmp_path / "docs", readme=readme)
    assert (tmp_path / "docs" / "index.html").read_bytes() == first
    assert (tmp_path / "docs" / "leaderboard.json").read_bytes() == first_json


def test_the_json_is_the_only_thing_a_mirror_would_need():
    """A Hugging Face Space, if one is ever added, reads this file and nothing
    else — so it has to carry the versions and the coverage, not just scores."""
    data = report.build([_scored("gemma4", 0.61)])
    payload = json.loads(json.dumps(data))
    table = payload["tables"][0]

    assert table["versions"]["judge_model"] == "claude-opus-5"
    assert table["versions"]["prompt_version"] == "tneval-soap-v1"
    assert table["rows"][0]["n_attempted"] == 50


# --- provenance the reader needs before the numbers -------------------------


def test_the_page_carries_the_licence_of_every_input():
    """One of the five inputs has a licence. A reader deciding whether to reuse
    any of this needs that before the scores, not in a file they never open."""
    data = report.build([_row()])
    sources = {entry["source"] for entry in data["licences"]}

    assert {"TN-Eval (code)", "TN-Eval-Data", "AnnoMI", "iCARE", "TheraFuse"} == sources
    licensed = [e for e in data["licences"] if e["licence"] == "Apache-2.0"]
    assert len(licensed) == 1, "only the TN-Eval code repository carries one"


def test_every_icare_section_is_defined_not_just_named():
    """A reader who has never seen the form cannot judge a score on it."""
    sections = report.protocol()["icare_sections"]
    assert len(sections) == 17
    assert all(len(s["description"]) > 30 for s in sections)
    assert [s["number"] for s in sections if s["temporal"]] == [5, 17]


def test_the_section_descriptions_are_ours_not_upstreams():
    """iCARE publishes no licence, so the page describes the fields in its own
    words and never reproduces their instruction text."""
    joined = " ".join(s["description"] for s in report.protocol()["icare_sections"])
    assert "helpful mental health assistant" not in joined
    assert "###Dialog###" not in joined


def test_a_scored_system_is_not_also_shown_as_unscored():
    """It reads as a missing measurement rather than as two version sets --
    which is exactly how a reader hit it: a row of dashes for a model that had
    already been judged."""
    data = report.build(
        [
            _row(system_id="gemma4"),  # coverage row, no judge
            _scored("gemma4", 0.57),  # the same model, judged
            _row(system_id="kimi-k3"),  # genuinely not judged yet
        ]
    )
    unscored = [t for t in data["tables"] if not t["scored"]]
    scored = [t for t in data["tables"] if t["scored"]]

    assert [r["label"] for r in unscored[0]["rows"]] == ["kimi-k3"]
    assert [r["label"] for r in scored[0]["rows"]] == ["gemma4"]


def test_a_table_left_with_no_rows_is_dropped_rather_than_drawn_empty():
    data = report.build([_row(system_id="gemma4"), _scored("gemma4", 0.57)])
    assert [t["scored"] for t in data["tables"]] == [True]


def test_the_coverage_row_still_exists_for_a_scored_system():
    """Only the page hides it. results/ is append-only and keeps both."""
    rows = [_row(system_id="gemma4"), _scored("gemma4", 0.57)]
    assert len(results.latest(rows)) == 2


def test_a_table_with_nothing_scored_is_not_drawn_as_a_scoreboard():
    """A grid of em-dashes under headings called COMPLETENESS and CONCISENESS
    reads as "the benchmark measured nothing". Three separate readers hit that.
    It is a queue and the page draws it as one."""
    page = report.render_page(report.build([_row(system_id="kimi-k3")]))

    assert "waiting for the judge" in page
    assert "renderQueue" in page, "the queue path exists"


def test_scored_tables_come_before_queues():
    """Printing the queue above the numbers is how a reader concludes the
    benchmark is empty when it is not."""
    data = report.build([_row(system_id="kimi-k3"), _scored("gemma4", 0.57)])
    assert [table["scored"] for table in data["tables"]] == [True, False]


def test_a_queue_still_reports_the_one_thing_that_is_measured():
    """How many notes each system produced that the protocol could read is a
    real measurement, and the only one a queue has."""
    data = report.build([_row(system_id="gpt-oss-120b", n_sessions_generated=42, n_failed=8)])
    row = data["tables"][0]["rows"][0]
    assert (row["n_generated"], row["n_attempted"], row["n_failed"]) == (42, 50, 8)
