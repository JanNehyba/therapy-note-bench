"""The short document is the long one with passages removed, never retyped.

Its whole justification is that no figure in it was written by hand: it calls
`czech_brief`'s own functions over the same payloads, so a number can only
change in both documents at once. That property is easy to lose -- one
convenient `f"{value:.2f}"` in this file and the two drift silently, because
nothing else compares them.

These tests are offline and read the source rather than building the page. A
build needs the whole corpus; the property is about the code.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import czech_brief_cs  # noqa: E402
import czech_short  # noqa: E402

from tnb import i18n  # noqa: E402

SHORT = Path(__file__).resolve().parent.parent / "tools" / "czech_short.py"


def _tree() -> ast.Module:
    return ast.parse(SHORT.read_text(encoding="utf-8"))


def test_every_sentence_it_adds_has_a_czech_one() -> None:
    """The failure is total: `_t` raises and the Czech document does not build.

    Same guarantee `tests/test_czech_brief_translations.py` gives the long
    document, for the strings this one adds.
    """
    known = set(czech_brief_cs.CS) | set(i18n.CS)
    missing = []
    for node in _tree().body:
        target = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
        elif isinstance(node, ast.AnnAssign):
            target = node.target
        if not isinstance(target, ast.Name) or node.value is None:
            continue
        try:
            value = ast.literal_eval(node.value)
        except Exception:
            continue
        for text in _prose(value):
            if text not in known:
                missing.append(text)
    assert not missing, "no Czech for:\n  " + "\n  ".join(t[:100] for t in missing)


def _prose(value: object) -> set[str]:
    if isinstance(value, str):
        return {value} if " " in value.strip() else set()
    if isinstance(value, dict):
        return {s for item in value.items() for s in _prose(item)}
    if isinstance(value, (tuple, list, set, frozenset)):
        return {s for item in value for s in _prose(item)}
    return set()


def test_it_formats_no_figure_of_its_own() -> None:
    """No number in this file may be turned into text here.

    A `:.2f`, a `round(`, or a percent built from a division is the shape of a
    figure being authored rather than borrowed, and the moment one exists the
    two documents can disagree. Formatting belongs in `czech_brief`, which both
    read.
    """
    source = SHORT.read_text(encoding="utf-8")
    for banned in (":.1f", ":.2f", ":.0%", ":.1%", "round(", "Decimal("):
        assert banned not in source, (
            f"{banned} in tools/czech_short.py: a figure formatted here can differ "
            "from the same figure in the long document. Call czech_brief for it."
        )


def test_the_tables_come_from_the_long_document() -> None:
    """It draws tables by calling `_merged_table`, not by building rows."""
    source = SHORT.read_text(encoding="utf-8")
    assert "brief._merged_table(" in source
    assert "<td" not in source, "a cell written here is a cell that can disagree"


def test_the_dropped_paragraphs_are_named_and_in_range() -> None:
    """Dropping by index is brittle, so the indices are checked against reality.

    If the summary loses a paragraph, an index that used to point at a checking
    aside starts pointing at a finding, and the short document quietly stops
    saying something the long one says.
    """
    assert czech_short._DROPPED, "nothing dropped means the split is not doing anything"
    assert max(czech_short._DROPPED) < 11, (
        "an index past the end of the summary drops nothing and hides that it dropped nothing"
    )
    assert 0 not in czech_short._DROPPED, "index 0 is the heading, removed by its own line"


def test_it_refuses_before_it_writes() -> None:
    """The clinical-content check runs on the rows, and before the file exists.

    The long document's `main` refuses in the same order and for the same
    reason: a file written and then found to be wrong has already been written.
    """
    source = SHORT.read_text(encoding="utf-8")
    refuse = source.index("check_no_clinical_text")
    write = source.index("target.write_text")
    assert refuse < write, "the guard runs after the file is written"
