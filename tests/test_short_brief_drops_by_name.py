"""The short brief drops named paragraphs, never numbered ones.

Offline. Builds nothing and asks nothing; reads the two modules.

**What went wrong.** `czech_short._findings` took `_conclusion`'s output, split
it on `<p>`, and removed indices `(3, 4, 5)`. That is only correct while the
list has a fixed length, and it does not have one: section 1c writes a second
paragraph only when there is a second thing to say, and a section was later
added above those indices. Both happened. The short document -- the copy most
likely to be forwarded -- began dropping the central negative finding about the
quality instrument instead of the two checking notes it was written to drop,
lost 846 words, and printed nothing.

The defect was the positional index, not the numbers in it. A name that no
longer matches drops nothing, which is the correct failure: a paragraph that
stopped being written removes itself here too, instead of shifting every
paragraph after it into somebody else's slot.
"""

from __future__ import annotations

import re
import sys

from tnb.config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tools"))

import czech_brief  # noqa: E402
import czech_short  # noqa: E402

SOURCE = (REPO_ROOT / "tools" / "czech_brief.py").read_text(encoding="utf-8")

#: Every name `_conclusion` can attach to a paragraph, read out of the source
#: rather than out of a run: a paragraph written only under conditions today's
#: data does not meet is still a paragraph whose name must be spelled the same
#: in both files.
EMITTED = set(re.findall(r'_say\(\s*"([^"]+)"', SOURCE))


def test_the_conclusion_names_every_paragraph_it_writes():
    assert EMITTED, "no named paragraphs found; has `_say` been renamed?"
    # Exactly one `said.append(` may survive -- the one inside `_say` itself.
    # Any other is a paragraph the short document can neither keep nor drop
    # deliberately, because it reaches the markup with no name on it.
    conclusion = SOURCE[SOURCE.index("def _conclusion(") :]
    conclusion = conclusion[: conclusion.index("\ndef ", 1)]
    appends = conclusion.count("said.append(")
    assert appends == 1, (
        f"{appends} raw `said.append(` calls in `_conclusion`; one is `_say` "
        "itself and every other is an unnamed paragraph"
    )


def test_the_names_are_unique():
    """Two paragraphs under one name means dropping one drops both."""
    names = re.findall(r'_say\(\s*"([^"]+)"', SOURCE)
    duplicated = {n for n in names if names.count(n) > 1}
    assert not duplicated, f"these names are used twice: {sorted(duplicated)}"


def test_dropping_is_by_name_and_not_by_position():
    assert all(isinstance(name, str) for name in czech_short._DROPPED), (
        "_DROPPED still holds positions; a positional index into a "
        "variable-length list is the defect this file exists for"
    )


def test_every_dropped_name_is_one_the_conclusion_can_write():
    """A misspelled name silently drops nothing and reads as a decision.

    Checked against what the source CAN emit, not against what today's data
    does: a paragraph that is conditional is still a real name.
    """
    unknown = [name for name in czech_short._DROPPED if name not in EMITTED]
    assert not unknown, (
        f"these names are dropped but never written, so they drop nothing: {unknown}. "
        f"Known names: {sorted(EMITTED)}"
    )


def test_the_findings_the_document_exists_for_are_not_droppable():
    """The regression, stated as a rule rather than as a number.

    Both quality paragraphs are the answer to "is the note any good", which is
    the question the short document is handed to answer. Whatever else changes,
    these two reach the forwarded copy.
    """
    for name in ("soap-quality", "deepsy-quality"):
        assert name in EMITTED, f"{name} is no longer written at all"
        assert name not in czech_short._DROPPED, f"{name} is being dropped from the short brief"


def test_the_short_brief_keeps_what_it_does_not_drop():
    """Round-trip on synthetic markup, so no judge and no payload is needed."""
    body = (
        "<h2>x</h2>"
        '<p data-part="soap-quality">keep me</p>'
        '<p data-part="how-thin">drop me</p>'
        '<p data-part="deepsy-quality">keep me too</p>'
    )
    kept = czech_short._trim_conclusion(body)
    assert "keep me" in kept and "keep me too" in kept
    assert "drop me" not in kept
    _ = czech_brief
