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
        # Not decoration. Every row the scorer writes carries the judge's
        # fingerprint, and a judged group that records none is no longer drawn
        # -- so a fixture without one models a row that can no longer be
        # produced. The tests that want that case pass `judge_settings=None`.
        "judge_settings": {"model": "claude-opus-5", "thinking_budget": 256},
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
    assert keys == ["rouge_l", "bertscore", "trace", "temporal_past", "temporal_next"]


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
    # Look for the row, not the word. The column legend below the table explains
    # that two *therapists* rated these notes, and a bare substring check reads
    # that sentence as the therapist baseline having leaked into the table.
    rows = [line for line in section.splitlines() if line.startswith("| `")]
    named = {line.split("`")[1] for line in rows}
    assert named == {"gemma4"}
    assert "full leaderboard" in section


def test_the_readme_prints_a_dash_rather_than_a_zero_for_a_missing_score():
    """A model with a measure missing has no score for it. Zero is a claim.

    This test used to pass an *unscored* row, which renders no table at all --
    just "waiting for the judge" -- so the cell it exists to guard never ran.
    The em-dash it asserted was the one in the heading. It needs a row that is
    scored on one measure and silent on another, which is the only shape that
    reaches the branch.
    """
    row = _scored("gemma4", 0.61)
    row.metrics.headline.pop("conciseness", None)
    section = report.render_readme_section(report.build([row]))

    line = next(line for line in section.splitlines() if line.startswith("| `gemma4`"))
    assert "0.610" in line, "the measure that exists is printed"
    assert "—" in line, "and the one that does not is a dash"
    assert "0.000" not in line


def test_a_measure_nobody_computed_does_not_sort_a_model_last():
    """The same mistake one level up: in the ordering rather than in the cell.

    Reading a missing completeness as 0.0 puts the model at the bottom of a
    ranking on evidence nobody has.
    """
    # Scored, but not on the measure the table ranks by. A row with *nothing*
    # measured is already `is_scored == False` and never reaches this branch,
    # so it cannot tell the two readings apart.
    unmeasured = _scored("a-not-measured", 0.0)
    unmeasured.metrics.headline.pop("completeness")
    unmeasured.metrics.headline["conciseness"] = 0.9
    # Two things make this discriminate, and it passed for the wrong reason
    # without each of them. A model genuinely measured at zero, because
    # completeness cannot go below 0.0 and a missing value read as 0.0 also
    # lands last. And names whose alphabetical order is the *opposite* of the
    # expected one, because ties break on system_id -- with friendlier names
    # the accident put them in the right order anyway.
    rows = [
        _scored("high", 0.7),
        unmeasured,
        _scored("z-measured-zero", 0.0, metrics=Metrics(headline={"completeness": 0.0})),
    ]

    labels = [row["label"] for row in report.build(rows)["tables"][0]["rows"]]

    assert labels == ["high", "z-measured-zero", "a-not-measured"]


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
    opens.

    This used to render one unscored TN-Eval row and assert that the strings
    "Krippendorff" and "no human anchor" appeared somewhere on the page. With
    no iCARE row there is no TRACE column, and the second string was matching
    the static footer -- so every measure caveat could have been deleted and
    this would have stayed green.

    Now both tracks are rendered and each caveat is read out of the measure
    table it belongs to, so rewording one does not silently satisfy the test
    and dropping one fails it.
    """
    rows = [
        _scored("gemma4", 0.6),
        _scored(
            "gemma4",
            0.6,
            track=results.TRACK_ICARE,
            prompt_version="icare-zeroshot-v1",
            metrics=Metrics(headline={"trace": 3.9}),
        ),
    ]
    page = report.render_page(report.build(rows))

    for track, columns in report.COLUMNS.items():
        table = report.MEASURE_TABLES[track]
        for key, _decimals in columns:
            caveat = (table[key].get("caveat") or "").strip()
            assert caveat, f"{track}.{key} is drawn with no caveat at all"
            # A distinctive fragment rather than the whole sentence, which the
            # renderer is free to wrap.
            fragment = caveat.split(".")[0][:40]
            assert fragment in page, f"{track}.{key}'s caveat is not on the page"

    # The two the docstring names, by the words a reader would look for.
    assert "Krippendorff" in page
    assert "no human anchor" in page


def test_rendering_twice_produces_the_same_bytes(tmp_path):
    """A report that churns on every run makes its own diffs unreadable and
    turns every workflow run into a commit.

    Two judges rather than one, so the panels that only exist when there are
    two -- the judge comparison, its bootstrap, its tie-breaking -- are in the
    output being compared. Everything feeding them has to be ordered rather
    than merely present. The README is compared too: it is a third artefact
    written by the same call and it was not checked here.
    """
    rows = _two_judges()
    readme = tmp_path / "README.md"
    readme.write_text(
        "<!-- LEADERBOARD:BEGIN -->"
        + chr(10)
        + "x"
        + chr(10)
        + "<!-- LEADERBOARD:END -->"
        + chr(10),
        encoding="utf-8",
    )
    docs = tmp_path / "docs"

    report.write(rows, docs_dir=docs, readme=readme)
    first = {p.name: p.read_bytes() for p in docs.iterdir()} | {"README": readme.read_bytes()}

    report.write(rows, docs_dir=docs, readme=readme)
    second = {p.name: p.read_bytes() for p in docs.iterdir()} | {"README": readme.read_bytes()}

    assert first == second


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


def test_report_reads_the_generation_cache_rather_than_trusting_a_memory(tmp_path, monkeypatch):
    """The page said iCARE was "3/3" for two days after 7 480 sections existed.

    Nothing was wrong with the data; the last `tnb results index` predated the
    generation run and nobody remembered to run it again. Reading the cache is
    cheap and cannot be stale by construction.
    """
    import argparse

    from tnb import cli, results

    calls = []
    monkeypatch.setattr(results, "index_generations", lambda **kw: calls.append(kw) or [])
    monkeypatch.setattr(results, "load", lambda *a, **kw: [])

    args = argparse.Namespace(no_index=False, run_id="")
    cli.cmd_report(args)

    assert calls, "report must re-read generations/ before rendering"
    assert calls[0]["run_id"].startswith("report-"), "the rows it appends are traceable"


def test_no_index_renders_exactly_what_results_already_holds(tmp_path, monkeypatch):
    """An escape hatch, so a published page can be reproduced from results/ alone."""
    import argparse

    from tnb import cli, results

    calls = []
    monkeypatch.setattr(results, "index_generations", lambda **kw: calls.append(kw) or [])
    monkeypatch.setattr(results, "load", lambda *a, **kw: [])

    cli.cmd_report(argparse.Namespace(no_index=True, run_id=""))

    assert not calls


# --- what a number is compared with -----------------------------------------


def test_every_track_says_what_it_scores_a_note_against():
    """Two readers in a row worked this out only by asking, so it is on the page.

    The two tracks put a human's note in opposite roles and every number means
    something different depending on which: on TN-Eval the therapist competes and
    is a row in the table, on iCARE the expert note is the answer key and never
    competes.
    """
    data = report.build([_scored("gemma4", 0.6), _row(track=results.TRACK_ICARE)])

    for table in data["tables"]:
        design = table["design"]
        assert design["scored_against"], table["track"]
        assert design["human_role"], table["track"]
        assert design["calibration"], table["track"]


def test_the_two_tracks_disagree_about_what_the_human_note_is_for():
    tneval = report.TRACK_DESIGN[results.TRACK_TNEVAL]
    icare = report.TRACK_DESIGN[results.TRACK_ICARE]

    assert tneval["human_role_short"] == "competitor"
    assert icare["human_role_short"] == "answer key"
    assert tneval["calibrated"] is True
    assert icare["calibrated"] is False, "the authors' expert ratings were never published"


def test_the_similarity_example_is_computed_from_the_text_beside_it():
    """A quoted score can drift from its example; a computed one cannot.

    0.111 is what the real pair scores in the corpus. An abridged model note
    shares proportionally more words and scores 0.238, which would have made the
    point look weaker than it is — so the strings are verbatim and the number is
    recomputed on every render.
    """
    example = report.similarity_example()

    assert example["rouge_l"] == pytest.approx(0.111, abs=0.001)
    assert "Butterflies in stomach" in example["generated"]
    assert "Tingling sensation in stomach" in example["expert"]


def test_the_worked_example_reaches_the_page():
    """Each on the page whose reader needs it.

    The design block says what a note here *is* and what a human's note is
    doing in the comparison, so it belongs on the row it qualifies. The worked
    similarity example is a demonstration of how one metric behaves, which is a
    question about the instrument.
    """
    data = report.build([_scored("gemma4", 0.6)])

    assert "designBlock" in report.render_page(data), "it qualifies the table"
    assert "similarity-example" in report.render_methods(data)


def test_an_older_harness_is_named_rather_than_drawn_beside_the_new_one():
    """Two harnesses are two definitions of the measures, not two models.

    ROUGE-L, the temporal measures and `is_filled` all changed meaning during
    the repairs. Drawing both versions puts a model's old ROUGE-L beside its
    new one with nothing saying which is which, and a reader cannot tell a
    changed model from a changed metric. `build`'s docstring has promised this
    split since it was written; the code drew every group.
    """
    old = _scored("gemma4", 0.61, harness_version="0.1.0", scored_at="2026-08-01T00:00:00Z")
    new = _scored("gemma4", 0.42, harness_version="0.2.0", scored_at="2026-08-26T00:00:00Z")

    data = report.build([old, new])

    assert len(data["tables"]) == 1
    assert data["tables"][0]["versions"]["harness_version"] == "0.2.0"
    assert [row["headline"]["completeness"] for row in data["tables"][0]["rows"]] == [0.42]

    assert len(data["superseded"]) == 1
    gone = data["superseded"][0]
    assert gone["harness_version"] == "0.1.0"
    assert gone["current_harness_version"] == "0.2.0"
    assert gone["rows"] == 1


def test_two_judges_at_the_same_harness_both_stay_drawn():
    """The split is per lane. Two judges are two instruments, not two versions,
    and comparing them is the whole reason there are two."""
    a = _scored("gemma4", 0.61, judge_model="gemini-3.1-pro-preview")
    b = _scored("gemma4", 0.55, judge_model="gpt-5.6-terra")

    data = report.build([a, b])

    assert len(data["tables"]) == 2
    assert data["superseded"] == []


def test_the_readme_says_why_a_number_it_used_to_show_is_gone():
    """A reader who remembers a different figure needs to know the measure moved.

    Otherwise the only available reading is that the model got worse.
    """
    old = _scored("gemma4", 0.61, harness_version="0.1.0")
    new = _scored("gemma4", 0.42, harness_version="0.2.0")

    section = report.render_readme_section(report.build([old, new]))

    assert "0.610" not in section, "the old number is not drawn"
    assert "no longer shown" in section
    assert "`0.1.0`" in section and "`0.2.0`" in section
    assert "results/rows.jsonl" in section, "and where it still is"


def test_the_page_says_it_too():
    """The README's reader and the page's reader need the same explanation.

    It is on the methods page rather than under the tables: a list of what was
    withdrawn is a statement about the instrument, and a reader choosing a
    model is not the reader who needs it.
    """
    old = _scored("gemma4", 0.61, harness_version="0.1.0")
    new = _scored("gemma4", 0.42, harness_version="0.2.0")

    data = report.build([old, new])
    methods = report.render_methods(data)

    assert "Withdrawn from the tables" in methods
    assert "renderSuperseded" in methods
    assert "renderSuperseded" not in report.render_page(data), "and not in both places"


def _two_judges() -> list[Row]:
    """One system each side of a disagreement, under both panel judges."""
    from tnb import judge

    rows = []
    for judge_model, scores in (
        (judge.DEFAULT_MODEL, {"x": 0.9, "y": 0.5, "z": 0.1}),
        (judge.SECOND_JUDGE, {"x": 0.5, "y": 0.1, "z": 0.9}),
    ):
        for system, value in scores.items():
            rows.append(
                _scored(
                    system,
                    value,
                    judge_model=judge_model,
                    metrics=Metrics(
                        headline={
                            "completeness": value,
                            "conciseness": value,
                            "faithfulness": value,
                        }
                    ),
                )
            )
    return rows


def test_the_readme_says_how_far_the_two_judges_agree(tmp_path):
    """The comparison a reader cannot do by eye, in the view that gets read.

    Two tables side by side do not say that the judges place most systems
    differently, and that is the fact deciding whether "ninth versus tenth" is
    a claim this benchmark can make.
    """

    rows = _two_judges()
    data = report.build(rows)
    data["concordance"] = report.concordance_payload(rows)

    section = report.render_readme_section(data)

    assert "Do the two judges agree?" in section
    assert "ninth" in section
    assert "beaten outright by nobody" in section


def test_a_withdrawn_coverage_group_is_not_described_as_scored_by_nobody():
    """Rows with no judge are generation coverage, written before any scoring.

    Both views said "scored by `None`" about them, which is ugly and untrue.
    """
    old = _row(harness_version="0.1.0")
    new = _row(harness_version="0.2.0")

    data = report.build([old, new])
    assert len(data["superseded"]) == 1

    section = report.render_readme_section(data)
    methods = report.render_methods(data)

    assert "None" not in section and "null" not in section
    assert "generation coverage" in section
    assert "generation coverage" in methods


def test_a_table_names_the_judges_settings_not_only_its_name():
    """The same judge at two thinking budgets is two instruments.

    Measured on this benchmark: raising Gemini's from 128 to 256 moved
    completeness by +0.017 on every system and changed the conciseness top
    three. A heading reading only "scored by gemini-3.1-pro-preview" would name
    both of them the same way.
    """
    row = _scored(
        "gemma4",
        0.61,
        judge_model="gemini-3.1-pro-preview",
        judge_settings={"model": "gemini-3.1-pro-preview", "thinking_budget": 256},
    )

    data = report.build([row])
    section = report.render_readme_section(data)
    page = report.render_page(data)

    assert data["tables"][0]["versions"]["judge_settings"]["thinking_budget"] == 256
    assert "thinking_budget 256" in section
    assert "judge_settings" in page
    # The model name is already the heading; repeating it inside the brackets
    # would be noise.
    assert "model gemini-3.1-pro-preview" not in section


def test_two_budgets_of_one_judge_are_two_tables():
    """The rule the comparability key exists for, at the level a reader sees."""
    at_128 = _scored("gemma4", 0.61, judge_settings={"thinking_budget": 128})
    at_256 = _scored("gemma4", 0.63, judge_settings={"thinking_budget": 256})

    tables = report.build([at_128, at_256])["tables"]

    assert len(tables) == 2
    assert {t["versions"]["judge_settings"]["thinking_budget"] for t in tables} == {128, 256}


def test_a_row_that_records_its_judge_settings_supersedes_one_that_does_not():
    """`judge_settings` was added mid-project and `results/` is append-only.

    Rows written before it exists record none, and drawing both sides of that
    commit put two identical Gemini tables next to each other. The described
    group wins the lane; the silent one is withdrawn rather than drawn -- it
    cannot be shown to have come from one instrument, which is a stronger
    reason than being the loser of a lane.
    """
    described = _scored("gemma4", 0.61, judge_settings={"thinking_budget": 256})
    silent = _scored("gemma4", 0.61, judge_settings=None)

    data = report.build([silent, described])

    assert len(data["tables"]) == 1
    assert data["tables"][0]["versions"]["judge_settings"] == {"thinking_budget": 256}
    assert data["superseded"][0]["reasons"] == ["settings"]


def test_two_real_settings_at_one_harness_are_still_two_tables():
    """The rule supersedes an *unrecorded* setting, not a different one."""
    at_128 = _scored("gemma4", 0.61, judge_settings={"thinking_budget": 128})
    at_256 = _scored("gemma4", 0.63, judge_settings={"thinking_budget": 256})

    assert len(report.build([at_128, at_256])["tables"]) == 2


def test_a_table_measured_by_an_older_harness_says_so():
    """A judge tried and not re-run keeps its table -- a different judge is a
    different table, which is this project's rule -- but its columns are
    defined by an older harness and may not mean what the newer tables' columns
    mean. `gemini-2.5-pro` is drawn at 0.1.0 beside two tables at 0.2.0.
    """
    old = _scored("gemma4", 0.61, judge_model="a-retired-judge", harness_version="0.1.0")
    new = _scored("gemma4", 0.63, judge_model="the-current-judge", harness_version="0.2.0")

    data = report.build([old, new])
    by_judge = {t["versions"]["judge_model"]: t for t in data["tables"]}

    assert by_judge["a-retired-judge"]["stale_harness"] is True
    assert by_judge["the-current-judge"]["stale_harness"] is False

    section = report.render_readme_section(data)
    assert "may not mean what the newer tables' columns mean" in section
    assert "older harness" in report.render_page(data)


def test_a_judged_table_that_cannot_say_how_the_judge_was_set_is_not_drawn():
    """Two rows that both record nothing are not thereby one instrument.

    The published `gemini-2.5-pro` table was fourteen rows from two: eleven
    e-INFRA systems answered at `thinking_budget` 128, and the therapist and
    TN-Eval's two reference models at 256 -- the very setting this repository
    elsewhere shows reorders a leaderboard. Both halves recorded `null`, so the
    comparability key could not tell them apart and ranked them against each
    other.
    """
    blended = [
        _scored("gemma4", 0.61, judge_settings=None),
        _scored("therapist", 0.34, judge_settings=None),
    ]

    data = report.build(blended)

    assert data["tables"] == []
    assert len(data["superseded"]) == 1
    assert data["superseded"][0]["reasons"] == ["settings"]
    # No harness superseded it, so no harness may be named as the cause.
    assert data["superseded"][0]["current_harness_version"] == ""

    said = report.render_readme_section(data) + report.render_page(data)
    assert "settings were not recorded" in said


def test_generation_coverage_has_no_settings_to_record_and_stays():
    """The rule reaches a ranking, not a count. Coverage rows have no judge, so
    demanding they describe one would erase the only thing on the page before
    anything is scored."""
    data = report.build([_row(), _row(system_id="glm-5")])

    assert len(data["tables"]) == 1
    assert data["superseded"] == []


def test_a_group_withdrawn_for_two_reasons_reports_both():
    """`at harness 0.2.0 ... redefined in 0.2.0` contradicted itself, and named
    the wrong cause: what actually beat that group was a group that could say
    what settings it used."""
    old = _scored("gemma4", 0.61, harness_version="0.1.0", judge_settings=None)
    new = _scored("gemma4", 0.42, harness_version="0.2.0", judge_settings={"thinking_budget": 256})

    data = report.build([old, new])

    assert len(data["tables"]) == 1
    gone = data["superseded"][0]
    assert gone["reasons"] == ["settings", "harness"]

    sentence = report._superseded_sentence(gone)
    assert "settings were not recorded" in sentence
    assert "redefined in `0.2.0`" in sentence
    assert "`0.1.0` are no longer shown" in sentence


def test_a_judge_grading_its_own_vendor_is_marked_in_the_row():
    """`docs/limitations.md` has promised this since the second judge was added.

    "Cells where a judge scored a model from its own family are marked in the
    table where they sit" -- and nothing marked them, in `renderTable` or in
    the row data it draws from. The effect is no longer hypothetical: with the
    comparison group corrected to the vendor that built each model,
    `gpt-5.6-terra` shows a detected self-preference of +0.027 completeness.
    """
    data = report.build(
        [
            _scored("gpt-oss-120b", 0.61, judge_model="gpt-5.6-terra"),
            _scored("gemma4", 0.60, judge_model="gpt-5.6-terra"),
            _scored("kimi-k3", 0.59, judge_model="gpt-5.6-terra"),
        ]
    )

    marked = {row["system_id"]: row["judges_own_family"] for row in data["tables"][0]["rows"]}

    assert marked["gpt-oss-120b"] == "openai", "OpenAI's model, graded by OpenAI's judge"
    assert marked["gemma4"] == "", "Google's model is not the GPT judge's own"
    assert marked["kimi-k3"] == ""

    page = report.render_page(data)
    assert "judges_own_family" in page, "and the page reads it"


def test_a_coverage_row_has_no_judge_to_share_a_vendor_with():
    """Nobody scored it, so the question does not arise."""
    data = report.build([_row(system_id="gpt-oss-120b")])

    assert data["tables"][0]["rows"][0]["judges_own_family"] == ""


def test_the_page_is_assembled_from_its_partials_and_carries_all_of_them():
    """`__STYLE__` and `__HELPERS__` are shared with `methods.html`.

    A marker left unreplaced ships the literal word to a reader; a partial
    dropped ships a page with no stylesheet, which still renders and looks
    merely ugly rather than broken. Both are cheap to check.
    """
    page = report.render_page(report.build([]))

    for marker in report.PARTIALS:
        assert marker not in page, f"{marker} was not replaced"

    assert "<style>" in page and "</style>" in page
    assert "const esc" in page and "function code(" in page


def test_a_partial_is_shared_rather_than_copied():
    """The point of the extraction. Two copies of a stylesheet drift the first
    time one of them is edited, and the drift is invisible until a reader on
    one page sees a rule the other page lost."""
    for name in report.PARTIALS.values():
        body = (report.TEMPLATE_DIR / name).read_text(encoding="utf-8")
        for template in report.TEMPLATE_DIR.glob("*.html"):
            if template.name.startswith("_"):
                continue
            assert body not in template.read_text(encoding="utf-8"), (
                f"{template.name} holds its own copy of {name}"
            )
