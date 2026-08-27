"""Every number that is produced is displayed, and every number says its scale.

These exist because of a bug nothing caught. `aggregate` stored a measure under
``likert_faithfulness`` while the headline and the table column called it
``faithfulness``. Python does not mind a key that never matches, the browser
renders it as an em dash, and the suite stayed green: a value was computed,
written to disk, and silently dropped between the scorer and the reader.

So these tests do not check a number. They check the joins — that the names a
scorer writes and the names a view reads are the same set, that nothing on the
page is a bare figure with no stated range, and that what the table says it is
ordered by is what it is actually ordered by.
"""

from __future__ import annotations

import re

import pytest

from tnb import report, results
from tnb.scoring import tneval


def _tneval_scores(note: dict, transcript: str) -> tneval.Scores:
    """Every question the protocol asks, answered, and scored the way a run does.

    The tasks are passed to `aggregate` as well as used to build the answers.
    Without them conciseness has no denominator -- the note text is what says
    how many sentence questions there should have been -- and the scorer now
    declines to publish a mean over however many happened to arrive.
    """
    tasks = tneval.build_tasks(note, transcript)
    answers = {task.unit: ("Yes" if task.kind.startswith("rubric") else "4") for task in tasks}
    return tneval.aggregate(answers, tasks)


NOTE = {
    "subjective": "The client reports drinking most evenings. She feels guilty about it.",
    "objective": "Cooperative and oriented. Speech normal.",
    "assessment": "Alcohol use at a risky level. Motivation is ambivalent.",
    "plan": "Agreed to cut down to three evenings. Review at the next session.",
}


def test_every_measure_a_scorer_produces_is_either_displayed_or_declared_internal():
    """The join that would have caught the original bug.

    A key written into ``by_section`` must be a column on the page or on the
    scorer's explicit internal list. A third possibility -- produced, stored, and
    read by nobody -- is the bug, and this is the assertion that names it.
    """
    scores = _tneval_scores(NOTE, "therapist: hello")
    produced = {key for values in scores.by_section.values() for key in values}
    produced |= set(scores.headline)

    displayed = {key for key, _ in report.COLUMNS[results.TRACK_TNEVAL]}
    accounted = displayed | set(tneval.INTERNAL_MEASURES)

    assert produced <= accounted, (
        f"produced but never read: {sorted(produced - accounted)} -- either put it on "
        f"the page or add it to tneval.INTERNAL_MEASURES so the omission is on purpose"
    )


def test_every_displayed_column_is_actually_produced():
    """The other direction: a column with no producer renders as a dash forever."""
    scores = _tneval_scores(NOTE, "therapist: hello")
    produced = set(scores.headline)
    displayed = {key for key, _ in report.COLUMNS[results.TRACK_TNEVAL]}

    assert displayed <= produced, f"columns nothing computes: {sorted(displayed - produced)}"


def test_faithfulness_is_named_the_same_in_the_headline_and_in_every_section():
    """The original defect, stated directly."""
    scores = _tneval_scores(NOTE, "therapist: hello")

    assert "faithfulness" in scores.headline
    for section, values in scores.by_section.items():
        assert "faithfulness" in values, f"{section} has no faithfulness under that name"
    assert not any("likert_faithfulness" in values for values in scores.by_section.values()), (
        "one number must not be stored under two names: results/ is append-only"
    )


@pytest.mark.parametrize("track", sorted(report.COLUMNS))
def test_every_column_states_its_range_and_what_it_counts(track):
    """No bare number. A reader seeing 0.65 beside 4.98 must be told why."""
    for key, _digits in report.COLUMNS[track]:
        meta = report.column_meta(track, key)
        assert meta["scale"], f"{track}.{key} has no scale"
        assert "-" in meta["scale"], f"{track}.{key} scale {meta['scale']!r} is not a range"
        assert len(meta["definition"]) > 40, f"{track}.{key} has no usable definition"


def test_a_column_with_no_documented_scale_fails_loudly():
    """The failure mode must be an error, not a blank that ships to the page."""
    with pytest.raises(KeyError, match="no entry in the measure table"):
        report.column_meta(results.TRACK_TNEVAL, "a_measure_nobody_documented")


@pytest.mark.parametrize("track", sorted(report.COLUMNS))
def test_the_table_is_ordered_by_the_measure_it_says_it_is_ordered_by(track):
    """One declaration, not three. The claim and the sort read the same constant."""
    declared = report.RANKING_MEASURES[track]
    if declared is None:
        return  # iCARE declines to rank; the sort falls back and claims nothing

    flagged = [key for key, _ in report.COLUMNS[track] if report.column_meta(track, key)["ranking"]]
    assert flagged == [declared]

    def row(system_id: str, value: float) -> results.Row:
        return results.Row(
            track=track,
            system_id=system_id,
            system_type="model",
            n_sessions_attempted=1,
            metrics=results.Metrics(headline={declared: value}),
        )

    better, worse = row("better", 0.9), row("worse", 0.1)
    ordered = sorted([worse, better], key=lambda row: report._sort_key(row, track))
    assert [row.system_id for row in ordered] == ["better", "worse"]


def test_the_icare_track_does_not_claim_a_ranking():
    """Its columns disagree on purpose; naming one the ranking would hide that."""
    assert report.RANKING_MEASURES[results.TRACK_ICARE] is None
    assert not any(
        report.column_meta(results.TRACK_ICARE, key)["ranking"]
        for key, _ in report.COLUMNS[results.TRACK_ICARE]
    )


def test_a_row_written_under_the_old_measure_name_is_repaired_on_read():
    """`results/` is append-only, so a rename has to happen on the way in.

    Without this the 41 rows already on disk keep the old key while the view
    looks up the new one, and the page prints a dash over a number in the file.
    """
    legacy = {
        "track": results.TRACK_TNEVAL,
        "system_id": "written-before-the-rename",
        "system_type": "model",
        "n_sessions_attempted": 1,
        "metrics": {
            "headline": {"likert_faithfulness": 4.5},
            "by_section": {"plan": {"completeness": 0.5, "likert_faithfulness": 5.0}},
        },
    }

    row = results.from_dict(legacy)

    assert row.metrics.headline == {"faithfulness": 4.5}
    assert row.metrics.by_section["plan"] == {"completeness": 0.5, "faithfulness": 5.0}


def test_a_row_written_after_the_rename_is_left_alone():
    """The repair must not overwrite a value a newer row already carries."""
    current = {
        "track": results.TRACK_TNEVAL,
        "system_id": "written-after",
        "system_type": "model",
        "n_sessions_attempted": 1,
        "metrics": {"by_section": {"plan": {"faithfulness": 4.0}}},
    }

    row = results.from_dict(current)

    assert row.metrics.by_section["plan"] == {"faithfulness": 4.0}


def test_conciseness_is_not_published_when_its_denominator_is_unknown():
    """How many sentence questions there should have been is a fact about the note.

    Without the note text there is no denominator, and the mean of whatever
    answers arrived is not conciseness: one "yes" of four sentences read as a
    perfect 1.00 with nothing marking it. Not knowing the denominator is not the
    same as the denominator being the numerator's length.
    """
    tasks = tneval.build_tasks(NOTE, "therapist: hello")
    answers = {task.unit: ("Yes" if task.kind.startswith("rubric") else "4") for task in tasks}

    with_note = tneval.aggregate(answers, tasks)
    without = tneval.aggregate(answers)

    assert with_note.headline["conciseness"] == 1.0
    assert "conciseness" not in without.headline
    assert without.headline["completeness"] == 1.0, "completeness needs no note text"


def test_every_column_a_table_draws_carries_a_caveat():
    """An empty `caveat` is a claim that the number needs no qualification.

    Three of them were empty, including `completeness` -- the column the
    TN-Eval table is *ordered by*. `docs/limitations.md` ends its section on
    that measure with "quote the number with that sentence attached, or do not
    quote it", and the sentence appeared nowhere near the number. ROUGE-L's
    said nothing about being a different measure from the source paper's, which
    three sections of prose are about.

    The column definitions are the only text most readers meet. This is not a
    style rule: a measure whose caveat is genuinely empty has to say so out
    loud, by being listed here.
    """
    #: Measures whose caveat may be empty, with the reason. Empty today.
    NEEDS_NO_CAVEAT: dict[str, str] = {}

    silent = []
    for track, columns in report.COLUMNS.items():
        table = report.MEASURE_TABLES[track]
        for key, _decimals in columns:
            if key in NEEDS_NO_CAVEAT:
                continue
            if not (table.get(key, {}).get("caveat") or "").strip():
                silent.append(f"{track}.{key}")

    assert not silent, f"drawn in a table with an empty caveat: {silent}"


def test_the_ranking_column_says_what_it_cannot_see():
    """The caveat that has to travel furthest, because it travels with an order."""
    for track, measure in report.RANKING_MEASURES.items():
        if measure is None:
            continue
        caveat = report.MEASURE_TABLES[track][measure]["caveat"]
        assert "checklist" in caveat or "coverage" in caveat, (
            f"{track} is ordered by {measure} and its caveat does not say what "
            f"the ordering cannot see"
        )


def test_the_reference_models_beat_the_therapist_where_the_docs_say_they_do():
    """`docs/limitations.md` makes a claim about published rows, so it is
    checkable, so it is checked.

    An earlier version of that paragraph said the two 2025 models beat the
    therapist on all three measures. They do on completeness and conciseness
    under every judge; Llama 3.1 70B is *below* her on faithfulness under both
    panel judges. The paragraph now says so, and this holds it to that.
    """
    from tnb import report, results

    drawn = report.current_rows(results.latest(results.load()))
    tables: dict[str, dict[str, dict]] = {}
    for row in drawn:
        if row.track != results.TRACK_TNEVAL or not row.judge_model:
            continue
        tables.setdefault(row.judge_model, {})[row.system_label or row.system_id] = (
            row.metrics.headline
        )

    checked = 0
    for systems in tables.values():
        human = systems.get("therapist-written (TN-Eval)")
        if not human:
            continue  # a table without her makes no claim about her
        for name in ("mistral-large-v2 (TN-Eval, 2025)", "llama-3.1-70b (TN-Eval, 2025)"):
            model = systems.get(name)
            if not model:
                continue
            checked += 1
            for measure in ("completeness", "conciseness"):
                assert model[measure] > human[measure], (
                    f"{name} is not above the therapist on {measure}, which "
                    f"docs/limitations.md says it is under every judge"
                )

    assert checked >= 4, "the corpus must actually contain the rows this checks"


def test_the_empty_marker_set_was_pinned_open_and_the_count_was_wrong():
    """This test used to hold the hole open, and the reason it gave was measured
    and false.

    It said: `is_filled` reads "Nil" as empty and "Nil." as content, a real hole
    and not a live one, 0 of 524 expert fields and 0 of 10 879 model-written
    sections. Re-counted on 2026-08-27 over every `ok` iCARE generation on disk,
    the trailing stop fires **1 of 10 880** -- `gpt-5.6-luna`, session 81,
    section 2: eight sub-fields, every one "Nil", counted as content because the
    last one ended in a full stop.

    And the comma form, which nothing had counted at all, fires twice -- both in
    section 17, `deepseek-v4-flash-thinking`, which is its **entire**
    Looks-forward score: 2 of the 11 the expert answered, published as 0.1818
    where the answer is 0.0000.

    So the decision the old test pinned was taken on a number that was wrong.
    Both are closed now, with the `harness_version` bump and re-score the old
    docstring correctly said it would cost.
    """
    from tnb.corpus import is_filled

    assert is_filled("Nil") is False
    assert is_filled("Date: Nil; Place: Nil") is False
    assert is_filled("Nil.") is False, "closed 2026-08-27; it fired once"
    assert is_filled("Date: Nil, Place: Nil, Time: Nil") is False, "and the comma form twice"
    assert is_filled("Type: Nil; Mode: Individual") is True, "one sub-field is enough"


def test_the_docs_name_what_is_not_measured():
    """Seven of PDSQI-9's nine attributes are not measured here, and until
    2026-08-26 nothing said so or named the instrument.

    `docs/landscape.md` is the survey of what exists in this field; a validated
    instrument for exactly this task was missing from it.
    """
    from tnb.config import REPO_ROOT

    # Whitespace-normalised: Markdown wraps, so a phrase that spans a line
    # break is absent from the raw text and present on the page.
    def flat(path):
        return re.sub(r"\s+", " ", (REPO_ROOT / "docs" / path).read_text(encoding="utf-8"))

    landscape = flat("landscape.md")
    limitations = flat("limitations.md")

    assert "PDSQI-9" in landscape and "PDSQI-9" in limitations
    for attribute in ("organized", "synthesized", "useful", "comprehensible", "stigmatizing"):
        assert attribute in limitations.lower(), f"{attribute} is not accounted for"

    # What adopting it does and does not buy, which is the part a reader skips.
    assert "did not compare LLM raters against human ones" in landscape
    assert "no human agreement figure at all" in landscape, "TRACE's position, stated"
    assert "0.575" in landscape, "and PDSQI-9's, which is not the same position"


def test_the_criteria_the_corpus_cannot_answer_are_named_with_the_sensitivity():
    """Two of 23 rubric criteria are on the floor for everyone, and the
    denominator is 23 regardless.

    The published claim is that excluding them deflates the number and not the
    ranking. Both halves are in the docs, so both are checked here.
    """
    from tnb.config import REPO_ROOT

    limitations = (REPO_ROOT / "docs" / "limitations.md").read_text(encoding="utf-8")

    assert "Two of the twenty-three criteria are on the floor" in limitations
    assert "+0.996" in limitations, "the sensitivity figure is the point of the section"
    assert "0.550 → 0.598" in limitations, "and so is what it does to the number"
    # The correction is not neutral between the parties, and the section that
    # this one replaces did not say so. That sentence is the finding.
    assert "not neutral between the parties" in limitations


def test_the_exclusion_is_not_read_off_the_party_being_measured():
    """The excluded criteria are `saturation`'s verdict, not the therapist's rate.

    The rule this replaced picked the criteria the therapist herself writes in at
    most 10% of her notes -- which decides the model-versus-therapist comparison
    with the therapist's own behaviour, and does not survive changing the judge:
    recomputed on the second judge's answers it keeps a different five, one of
    them `objective-mental-status`, and moves a system seven places.

    So the set is held to what the code already computes and both judges agree
    on. `unreachable` requires every system to be at or below the floor, the
    therapist counting as one system among nineteen rather than as the authority.
    """
    import json

    from tnb.config import REPO_ROOT
    from tnb.scoring import saturation

    docs = REPO_ROOT / "docs"
    published = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(docs.glob("saturation-*.json"))
    ]
    live = [
        d for d in published if d.get("judge_model") in ("gemini-3.1-pro-preview", "gpt-5.6-terra")
    ]
    assert len(live) == 2, "both live judges publish a saturation analysis"

    floors = [{c["key"] for c in d["criteria"] if c["verdict"] == "unreachable"} for d in live]
    agreed = set.intersection(*floors)
    assert agreed == {"assessment-goals", "subjective-homework"}

    # Not the same as "what the therapist rarely writes": under at least one
    # judge the two rules disagree, which is why one of them is in the docs.
    for d in live:
        therapist_rule = {
            c["key"] for c in d["criteria"] if (c["human"] or 0.0) <= saturation.FLOOR_AT
        }
        assert therapist_rule != agreed, (
            f"{d['judge_model']}: the therapist rule and the floor rule are not "
            "interchangeable, and the docs must not present them as if they were"
        )

    limitations = (docs / "limitations.md").read_text(encoding="utf-8")
    assert "`saturation`'s `unreachable`" in limitations, "the docs name the rule"
    assert "at most 10% of her notes" in limitations, "and name what it replaced"


def test_a_composite_nil_answer_is_empty_however_it_is_punctuated():
    """ "Nothing to report" spelled out one sub-question at a time is still
    nothing to report, whichever separator the model chose.

    `deepseek-v4-flash-thinking` wrote the comma form into *what happens next*
    in two sessions, and those two were its entire Looks-forward score: 2 of the
    11 the expert answered, published as 0.1818 where the answer is 0.0000. The
    trailing full stop is the other half, documented as a hole that fired
    nowhere and firing once.
    """
    from tnb.corpus import is_filled

    for empty in (
        "Nil",
        "Nil.",
        "Date: Nil\nPlace: Nil\nTime: Nil",
        "Date: Nil; Place: Nil; Time: Nil",
        "Date: Nil, Place: Nil, Time: Nil, Bring anyone: Nil",
        "Date: Nil, Place: Nil, Time: Nil, Bring anyone: Nil.",
    ):
        assert not is_filled(empty), f"{empty!r} says nothing"

    # And prose that happens to contain a comma is still content.
    for filled in ("Anxiety, low mood", "Type: Nil; Mode: Individual", "He reports poor sleep"):
        assert is_filled(filled), f"{filled!r} says something"


def test_a_numbered_list_is_not_cut_into_bare_numerals():
    """A list marker is not a sentence, and was scored as one.

    `1. ` ends in a full stop followed by a space, so a numbered plan was cut
    into pieces that were bare numerals -- and every piece became a question put
    to the judge: does this sentence serve a rubric criterion? A numeral cannot,
    so it was a certain No in the numerator and a certain +1 in the denominator.
    The numerals were 65% of `qwen3.5-122b`'s conciseness failures, 62% of
    `google_gemini-3.7-flash`'s and 56% of `gpt-oss-120b`'s, against 0% for the
    five models that write prose.

    **This took two attempts, and the first one is the reason for the digest.**
    A conciseness answer is cached under the sentence's *index*,
    `subjective.rubric_conciseness.s02`, so changing what counts as a sentence
    re-numbers them and pairs every cached answer with a different sentence. 173
    of the 942 notes change their sentence list, and 672 bare numerals stop
    being questions. Applied on 2026-08-27 and
    reverted the same hour, because the published conciseness moved for exactly
    the models with numbered lists and *downward*: the re-pairing, not the fix.
    `judge.load_cached` compares a cached answer's prompt digest against the
    question about to be asked and would have caught it, except that neither
    published judge's answers carried a digest. They all do now.

    Two digits at most, so a sentence that ends in a year still ends there.
    """
    from tnb.scoring.tneval import split_sentences

    assert split_sentences("Plan: 1. Continue weekly sessions. 2. Practise breathing.") == [
        "Plan: 1. Continue weekly sessions.",
        "2. Practise breathing.",
    ]
    assert split_sentences("1. First. 2. Second. 3. Third.") == [
        "1. First.",
        "2. Second.",
        "3. Third.",
    ]
    assert split_sentences("He was calm. She agreed.") == ["He was calm.", "She agreed."]
    assert split_sentences("She relapsed in 2019. She has been sober since.") == [
        "She relapsed in 2019.",
        "She has been sober since.",
    ], "a four-digit year is not a list marker"
    assert split_sentences("Seen by Dr. Novak. Client was calm.") == [
        "Seen by Dr. Novak.",
        "Client was calm.",
    ], "the abbreviation repair still works beside the new one"


def test_the_docs_say_that_nothing_verifies_the_icare_answer_key():
    """ "The form does not fit the material" and "nothing checks the answer key"
    are different claims. The second bounds what ROUGE-L and BERTScore can mean:
    a model is scored by distance from one unreviewed document.

    `data/ihope_test.json` holds one `summary` per session and no second
    version, so human disagreement is not measurable here at all — against
    TN-Eval, where two annotators rated every note and the disagreement is
    published.
    """
    import json

    from tnb.config import REPO_ROOT

    limitations = (REPO_ROOT / "docs" / "limitations.md").read_text(encoding="utf-8")
    assert "Nothing verifies the answer key" in limitations
    assert "not measurable" in limitations

    corpus = REPO_ROOT / "data" / "ihope_test.json"
    if not corpus.exists():
        pytest.skip("the corpus is fetched at run time and is not on this machine")
    sessions = json.loads(corpus.read_text(encoding="utf-8"))
    assert len({s["id"] for s in sessions}) == len(sessions), (
        "one record per session; a second expert note would show up as a repeated id "
        "and would make the claim in the docs false"
    )
