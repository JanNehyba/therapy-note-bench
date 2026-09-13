"""The completeness order under other weightings, and the artefact that publishes it.

The leaderboard averages four SOAP sections equally. `weighting` recomputes the
same notes item-weighted and under TN-Eval's own importance grading, and
publishes what each does to the order. These tests pin three things: that the
grading table covers exactly the rubric this repository scores, that the
arithmetic is the arithmetic, and that the macro column of the published
artefact is the leaderboard's completeness column -- position by position --
so the two files cannot describe different orders.
"""

from __future__ import annotations

import json

import pytest

from tnb.scoring import tneval, weighting

# --- the grading table --------------------------------------------------------


def test_importance_covers_exactly_the_scored_rubric():
    """One label per criterion this repository asks about, none for any other.

    The table is transcribed from the paper's appendix, which lists 27 items;
    this repository scores 23. A key here that the rubric does not score would
    be a weight on nothing, and a scored criterion missing here would be
    silently unweighted.
    """
    assert set(weighting.IMPORTANCE) == set(tneval.CHECKBOX_MAPPING)


def test_every_label_is_one_the_paper_uses():
    for key, level in weighting.IMPORTANCE.items():
        assert level is None or level in weighting.LEVELS, f"{key}: {level!r}"


def test_the_one_unlabelled_criterion_is_named_and_not_guessed():
    """The appendix carries no importance line for Identifying Triggers.

    That is the only such entry of the 27, checked against the paper on
    2026-09-13. The honest reading of a source that says nothing is to say
    nothing: the criterion is excluded from the importance-weighted figure and
    listed in the artefact as unlabelled, never given a level by assumption.
    """
    unlabelled = [key for key, level in weighting.IMPORTANCE.items() if level is None]
    assert unlabelled == ["assessment-triggers"]


def test_the_general_items_the_repository_does_not_score_are_declared():
    """Three appendix items, one of them Mandatory, are not asked of any note.

    The artefact must say so rather than let a reader assume the 23 are the
    paper's whole rubric.
    """
    levels = {item["level"] for item in weighting.NOT_IMPLEMENTED}
    assert "mandatory" in levels, "the safety item is Mandatory and is not scored here"
    assert len(weighting.NOT_IMPLEMENTED) == 3


# --- the arithmetic ------------------------------------------------------------


def _scores(by_criterion: dict[str, float], sections: int = 4, macro: float = 1.0) -> tneval.Scores:
    return tneval.Scores(
        headline={"completeness": macro},
        by_criterion=by_criterion,
        sections_used={"completeness": sections},
    )


def test_a_complete_note_reads_the_same_under_every_weighting():
    full = _scores({key: 1.0 for key in tneval.CHECKBOX_MAPPING})
    found = weighting.weighted(full)
    assert found["macro"] == 1.0
    assert found["item_weighted"] == 1.0
    assert found["importance_weighted"] == 1.0
    assert all(value == 1.0 for value in found["by_level"].values())


def test_item_weighting_counts_every_criterion_once():
    """Eight Mandatory criteria present and nothing else: 8 of 23, exactly."""
    only_mandatory = {
        key: (1.0 if level == "mandatory" else 0.0) for key, level in weighting.IMPORTANCE.items()
    }
    found = weighting.weighted(_scores(only_mandatory, macro=8 / 23))
    assert found["item_weighted"] == pytest.approx(8 / 23)
    assert found["by_level"]["mandatory"] == 1.0
    assert found["by_level"]["highly_recommended"] == 0.0


def test_importance_weighting_uses_the_declared_weights_and_skips_the_unlabelled():
    """The denominator is the 22 labelled criteria at their weights, not 23.

    Eight Mandatory at 1.0, one Mandatory-in-circumstances at 1.0, thirteen
    Highly recommended at the ratio. With only the Mandatory eight present the
    figure is 8 over that sum, and it moves with the ratio exactly as the
    weights say.
    """
    only_mandatory = {
        key: (1.0 if level == "mandatory" else 0.0) for key, level in weighting.IMPORTANCE.items()
    }
    scores = _scores(only_mandatory, macro=8 / 23)
    for ratio in weighting.RATIOS:
        found = weighting.weighted(scores, ratio)
        assert found["importance_weighted"] == pytest.approx(8 / (9 + 13 * ratio)), ratio


def test_a_partial_note_is_refused_not_weighted():
    """Two sections averaged print like four and are not the same measurement."""
    full = _scores({key: 1.0 for key in tneval.CHECKBOX_MAPPING}, sections=2)
    with pytest.raises(ValueError, match="every section"):
        weighting.weighted(full)


def test_a_complete_note_missing_a_criterion_is_refused():
    some = {key: 1.0 for key in list(tneval.CHECKBOX_MAPPING)[:20]}
    with pytest.raises(ValueError, match="lacks criteria"):
        weighting.weighted(_scores(some))


def test_rank_changes_names_who_moved_and_by_how_much():
    systems = {
        "a": {"macro": 0.9, "item_weighted": 0.5},
        "b": {"macro": 0.8, "item_weighted": 0.7},
        "c": {"macro": 0.7, "item_weighted": 0.6},
    }
    found = weighting.rank_changes(systems, lambda row: row["item_weighted"])
    assert found["order"] == ["b", "c", "a"]
    assert found["moved"] == 3 and found["of"] == 3
    by_system = {c["system"]: c for c in found["changes"]}
    assert by_system["a"] == {"system": "a", "macro_place": 1, "place": 3, "by": 2}
    assert by_system["b"]["by"] == -1


# --- the published artefact -------------------------------------------------------


def _published(judge_model: str) -> dict | None:
    return weighting.load(judge_model)


def _leaderboard_table(judge_model: str) -> dict | None:
    from tnb import report

    if not report.DATA_PATH.exists():
        return None
    payload = json.loads(report.DATA_PATH.read_text(encoding="utf-8"))
    for table in payload["tables"]:
        versions = table.get("versions") or {}
        if table["track"] == "tneval-soap" and versions.get("judge_model") == judge_model:
            return table
    return None


def _bare(label: str) -> str:
    """`saturation.label_for` qualifies a system with its provider only when two
    providers serve the same id; the leaderboard keys on the bare id."""
    return label.split(" (", 1)[0]


@pytest.mark.parametrize("judge_model", ["gemini-3.1-pro-preview", "gpt-5.6-terra"])
def test_the_macro_column_is_the_leaderboard_column(judge_model: str):
    """The artefact's macro figures are the leaderboard's, note for note.

    Recomputed from the answer cache and compared to the published rows, not
    trusted. If this holds, the other two columns rest on exactly the notes the
    leaderboard's own figure rests on, which is the whole point of computing
    them here rather than from the rows' averages. Absent is allowed -- the
    artefact is not drawn without it -- and wrong is not.
    """
    found = _published(judge_model)
    if found is None:
        pytest.skip(f"no weighting artefact for {judge_model} in this checkout")
    table = _leaderboard_table(judge_model)
    if table is None:
        pytest.skip("no published leaderboard table for this judge in this checkout")

    rows = {row["system_id"]: row for row in table["rows"]}
    # Every system the artefact scored must be a row the table draws. A label
    # the table does not know is a drift between the cache and the rows, and
    # skipping it would let this test shrink to whatever still joins. Checked
    # 2026-09-13: 21 systems in the cache, 21 rows, no id served by two
    # providers -- so the join is total and the test demands it stays so.
    for label, own in found["systems"].items():
        assert _bare(label) in rows, f"{label}: in the artefact and not on the table"
        row = rows[_bare(label)]
        # The table prints round(sum/len, 4); the artefact keeps the exact mean.
        # A mean can sit on a rounding tie -- qwen3.5-int4 is 0.53575 under the
        # first judge -- and the float sum then tips one way by an ulp while the
        # exact mean rounds the other, 5e-5 apart plus epsilon. The tolerance
        # cannot hide a real difference: one criterion on one note moves a
        # fifty-note mean by at least 6e-4.
        assert own["macro"] == pytest.approx(row["headline"]["completeness"], abs=5e-5 + 1e-9), (
            label
        )
        assert own["notes_used"] == row["n_complete"], f"{label}: note counts differ"

    ours = [_bare(s) for s in found["macro_order"]]
    theirs = sorted(
        (s for s in rows if s in set(ours)),
        key=lambda s: (-rows[s]["headline"]["completeness"], s),
    )
    assert ours == theirs, "the macro order in docs/weighting differs from docs/leaderboard"
    # And the artefact ranks exactly the systems the table draws. It applies no
    # coverage rule of its own: the table shows gpt-oss-120b on its 42 notes
    # with the count beside it, and so does this.
    assert set(rows) == set(ours), (
        f"rows on the table the artefact did not score: {sorted(set(rows) - set(ours))}"
    )


def test_the_artefact_names_its_instrument_and_its_gaps():
    published = [
        found
        for judge_model in ("gemini-3.1-pro-preview", "gpt-5.6-terra")
        if (found := _published(judge_model)) is not None
    ]
    if not published:
        pytest.skip("no weighting artefact in this checkout")
    assert len(published) == 2, "both live judges publish a weighting analysis"
    for found in published:
        assert found["judge_settings"], "the settings the answers were produced at"
        assert found["unlabelled"] == ["assessment-triggers"]
        assert len(found["not_implemented"]) == 3
        assert set(found["rank_changes"]) == {
            "item_weighted",
            *(f"importance_weighted_{r}" for r in weighting.RATIOS),
        }
        for change in found["rank_changes"].values():
            assert change["of"] == len(found["systems"])
