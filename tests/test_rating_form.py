"""The sheet a person rates on has to be the instrument the judge was given.

Offline. Nothing here reaches a corpus or a judge; the anchors are read from
`tnb.scoring.pdsqi` and the Czech from `tools/czech_pdsqi_form`.

**Why this file exists.** The agreement figure between the judge and one native
speaker is the only human anchor this track has. It measures nothing at all if
the two were answering different questions -- and they were. The Czech anchors
started as a paraphrase: `useful` lost that PDSQI-9 counts individual
ASSERTIONS rather than the note as a whole, `organized` dropped the
parenthetical that defines what may count as a grouping, and `synthesized` was
not a translation at all. Its anchor 1 said there was no reasoning where the
published instrument says the reasoning is WRONG.

Jan found it by reading one anchor and finding it unusable. Nothing else would
have: the numbers would have come out, the panel would have drawn, and the
figure would have been published as agreement.

A count cannot catch a rewrite, so the strong guard is not here -- it is that
the form now prints the English beside every Czech anchor, and the test below
holds it to that. A rater who can see both can see a drift; a test cannot.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from tnb.scoring import pdsqi  # noqa: E402

import czech_pdsqi_form as form  # noqa: E402  (isort: skip)

PUBLISHED = {a.key: a for a in pdsqi.ATTRIBUTES}


def test_every_attribute_asked_is_one_the_instrument_defines():
    """A question the form invents has no English to be checked against."""
    unknown = [key for key in form.ASKED if key not in PUBLISHED]
    assert not unknown, f"asked about attributes PDSQI-9 does not define: {unknown}"
    assert set(form.CS) == set(form.ASKED), "the Czech table and the asked set disagree"


@pytest.mark.parametrize("key", sorted(form.ASKED))
def test_the_czech_has_one_anchor_per_published_anchor(key):
    """Five published anchors, five Czech ones, in the published order.

    Weak on purpose about CONTENT -- no test can see that a translation drifted.
    It does catch the two things that are checkable: an anchor dropped, and an
    anchor added that the instrument does not have.
    """
    english = PUBLISHED[key].anchors
    czech = form.CS[key][2]
    assert english, f"{key} has no published anchors to translate"
    assert len(czech) == len(english), (
        f"{key}: {len(czech)} Czech anchors against {len(english)} published ones"
    )
    for n, text in enumerate(czech, start=1):
        assert text.strip(), f"{key} anchor {n} is empty"


@pytest.mark.parametrize("key", sorted(form.ASKED))
def test_a_rater_can_read_the_english_the_judge_was_given(key):
    """The real guard, and the reason the drift is now findable by eye.

    The form used to show the English QUESTION and DEFINITION and stop there,
    so the five anchors -- which are what a rating is actually chosen from --
    existed only in Czech on that page. A rater had no way to notice that the
    Czech had wandered off the instrument.
    """
    page = form.build(notes=1, corpus="real")
    for anchor in PUBLISHED[key].anchors:
        assert anchor in page or _escaped(anchor) in page, (
            f"{key}: the published anchor is nowhere on the sheet -- {anchor!r}"
        )


def _escaped(text: str) -> str:
    import html

    return html.escape(text)


def test_the_sheet_says_the_czech_is_a_translation():
    """A rater who sees only Czech has no reason to think there is an original.

    The wording of PDSQI-9 is not ours to improve -- `pdsqi` says so and the
    licence is why -- so where it reads badly the honest move is to show what it
    is, not to write something clearer and call it the same instrument.
    """
    page = form.build(notes=1, corpus="real")
    assert "anglick" in page, "the sheet never mentions the English original"
