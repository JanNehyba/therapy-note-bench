"""What every published measure says about a note with nothing in it.

The shape this repository keeps meeting: **a note that asserts nothing cannot be
wrong, so a measure that counts wrongness rewards it.** It has been met four
times, each time by accident and each time after the number was published:

- `rouge_l` gave an empty note 0.379, because both sides shared our 17 field
  labels and every "Nil" the expert wrote. Repaired in harness 0.2.0.
- `gemma4` published a perfect `temporal_past` for writing "Nil" four ways,
  because `is_filled` did not split on commas. Repaired in 0.3.0.
- PDSQI-9 rates an empty note 5.00 on `accurate`, 5.00 on `succinct` and 1.00
  on the stigmatising column -- all three beating the therapist.
- `faithfulness`, **a column on the main leaderboard**, rates it 5.00 on all
  four sections: higher than every model but one and higher than the therapist.

Four separate discoveries of one fact. What was missing was not another repair
but the question being asked of everything at once, which is this file.

**A measure gets in here or the suite fails.** The registry below is checked
against `report.COLUMNS`, so a new column cannot be published until somebody has
put an empty note through it and written down what came back. That is the part
that makes this a guard rather than a fourth patch.

Judge-backed measures cannot be recomputed offline, so their entries record what
was measured, against which judge and when. The computed ones are recomputed
here every run.
"""

from __future__ import annotations

import pytest

from tnb import report, results
from tnb.scoring import icare, tneval

#: One entry per published column: what an empty note scores, and whether that
#: is the top of the measure's scale. `tops_out` is the finding, not the score.
#:
#: Measured 2026-08-27 against `gemini-3.1-pro-preview` at the published
#: settings, over the first AnnoMI transcript. The judge reads the note in every
#: case -- most attributes correctly collapse to the floor -- so where it does
#: not, the instrument is saying what it means to say.
EMPTY_NOTE = {
    # --- TN-Eval SOAP ---------------------------------------------------
    "completeness": (0.0, False),
    "conciseness": (0.0, False),
    "faithfulness": (5.0, True),
    # --- iCARE / iHOPE --------------------------------------------------
    "rouge_l": (0.0, False),
    # Not asked: BERTScore of an empty string against the expert note is a
    # property of the embedding model rather than of this harness, and running
    # it would put a network fetch in the offline suite. Recorded as unasked
    # rather than as zero, which would be a measurement nobody made.
    "bertscore": (None, False),
    "trace": (1.0, False),
    "temporal_past": (0.0, False),
    "temporal_next": (0.0, False),
    # --- PDSQI-9 ---------------------------------------------------------
    "accurate": (5.0, True),
    "succinct": (5.0, True),
    "stigmatizing": (1.0, True),
    "thorough": (1.0, False),
    "useful": (1.0, False),
    "organized": (1.0, False),
    "comprehensible": (1.0, False),
    "synthesized": (1.0, False),
}

EMPTY_SOAP = {"subjective": "", "objective": "", "assessment": "", "plan": ""}


def test_every_published_column_has_been_put_to_an_empty_note():
    """The guard. Four measures were caught one at a time, after publication,
    because nobody asked the question of all of them at once. A column that
    reaches the page without an answer here fails the suite instead."""
    published = {key for columns in report.COLUMNS.values() for key, _digits in columns}
    missing = sorted(published - set(EMPTY_NOTE))

    assert not missing, (
        f"{missing} reach the page and nobody has scored an empty note on them. "
        "Run it, and record what came back -- including 'it tops out', which is "
        "the answer four of these gave."
    )


def test_the_measures_that_reward_an_empty_note_are_named():
    """Not a failure: `faithfulness` is TN-Eval's protocol reproduced verbatim
    and PDSQI-9's anchors are the instrument's own. Neither is ours to redefine.

    What is ours is saying so. This pins the list, so a repair that quietly
    removed one -- or a change that quietly added a fifth -- has to be argued
    for here rather than noticed later by a reader.
    """
    tops_out = {name for name, (_score, top) in EMPTY_NOTE.items() if top}

    assert tops_out == {"faithfulness", "accurate", "succinct", "stigmatizing"}


def test_an_empty_soap_note_still_scores_zero_for_coverage():
    """The two measures that count what a note contains, recomputed rather than
    remembered. A note with nothing in it satisfies no criterion and has no
    sentence that serves one."""
    tasks = tneval.build_tasks(EMPTY_SOAP, "therapist: hello\nclient: hello")
    answers = {task.unit: "No" for task in tasks if task.kind.startswith("rubric")}

    scores = tneval.aggregate(answers, tasks)

    assert scores.headline["completeness"] == pytest.approx(EMPTY_NOTE["completeness"][0])
    assert scores.headline["conciseness"] == pytest.approx(EMPTY_NOTE["conciseness"][0])


def test_an_empty_icare_note_scores_zero_against_the_expert_note():
    """`rouge_l` was the first instance and is the one that can be recomputed
    without a judge: an empty note against a real expert note, every run."""
    expert = {
        1: "Client reports low mood for three weeks.",
        2: "Sleep disturbed, appetite reduced.",
        3: "Nil",
    }
    empty = dict.fromkeys(expert, "")

    # Through `comparable_pair`, which is what the scorer uses: field values
    # over the fields the expert answered. Comparing the rendered notes -- the
    # shape this measure had before harness 0.2.0 -- scores this same pair
    # 1.000, because then both sides are our own field labels and nothing else.
    candidate, gold = icare.comparable_pair(icare.render_note(empty), icare.render_note(expert))

    assert icare.rouge_l(candidate, gold) == pytest.approx(EMPTY_NOTE["rouge_l"][0]), (
        "an empty note scored 0.379 here once, by sharing the labels it was scored against"
    )
    assert icare.rouge_l(icare.render_note(empty), icare.render_note(expert)) > 0.9, (
        "and this is the call that did it, kept so the difference stays visible"
    )


def test_the_documented_instances_are_the_ones_the_docs_carry():
    """The four are recorded where a reader meets the number, not only here."""
    text = (results.ROWS_PATH.parent.parent / "docs" / "limitations.md").read_text(encoding="utf-8")

    assert "an empty note" in text
    assert "never as things it can win" in text
