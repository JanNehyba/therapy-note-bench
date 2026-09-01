"""A cell holding one value per judge may not break between them.

Offline. Checks the joiner directly, and the built document when it is present.

**The failure this pins was invisible on screen and only appeared in print.**
`czech_crosscheck` reported a figure on the page and missing from the Czech PDF.
Nothing was missing. The PDF text layer held

    10 4.32 / -- / -3.72
    4.50 / 5.00 / 4.30 5.00 / 4.70 3.30

which is several table cells each WRAPPED onto two lines, with Chrome emitting
every cell's first line across the row before any cell's second line. `4.32 /`
is one cell's first line and `3.72` its second; the `--` between them belongs to
the next column. A checker looking for `3.72` finds `-3.72` and calls it absent.

So the defect is that `4.32 / 3.72` was allowed to break in the middle. That
pair is ONE measurement read under two judges, not two words, and breaking it
was wrong typographically before it was wrong mechanically. It showed on the
Czech side first because Czech column headings are longer and leave the columns
narrower -- the same reason recorded in the print stylesheet, which had already
lost two columns off the right edge of the Czech print once.

A non-breaking space rather than `white-space: nowrap`: nowrap makes a cell that
cannot fit overflow the table instead of wrapping, which is that older failure
exactly. This keeps the pair together and still lets a cell wrap around it.
"""

from __future__ import annotations

import re
import sys

import pytest

from tnb.config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tools"))

import czech_brief  # noqa: E402

BUILT = (
    REPO_ROOT / "local" / "czech-brief.html",
    REPO_ROOT / "local" / "czech-brief-cs.html",
    REPO_ROOT / "local" / "czech-short.html",
    REPO_ROOT / "local" / "czech-short-cs.html",
)

#: Two figures with an ordinary space either side of the slash: the shape that
#: is allowed to wrap. `\s` would also match the non-breaking space this fix
#: introduces, so the space is spelled literally.
BREAKABLE = re.compile(r"\d+\.\d+ / (?:\d+\.\d+|--)")


def test_the_joiner_is_not_breakable():
    joined = czech_brief._pair(["4.32", "3.72"])
    assert "4.32" in joined and "3.72" in joined
    assert not BREAKABLE.search(joined), f"{joined!r} may wrap between the judges"
    assert "&nbsp;" in joined or " " in joined


def test_the_joiner_still_reads_as_a_pair():
    """Non-breaking, and still a slash: the checker unescapes before it looks
    and then finds figures with `\\d+\\.\\d+`, so the separator never enters a
    comparison -- but a reader still has to see two values, not one number."""
    assert czech_brief._pair(["1.00", "0.90"]).count("/") == 1
    assert czech_brief._pair(["--", "--"]).count("/") == 1


@pytest.mark.parametrize("path", BUILT, ids=lambda p: p.name)
def test_no_built_table_cell_can_break_between_judges(path):
    """The whole point is what reaches the page, not what the helper returns.

    Four places built this pair and only one of them was the helper; the others
    were literal `" / ".join(...)` calls in the score cell, the index cell and
    the notes-scored cell. A test on the helper alone would have passed while
    three quarters of every table stayed breakable.
    """
    if not path.exists():
        pytest.skip(f"{path.name} has not been built in this checkout")
    html = path.read_text(encoding="utf-8")
    offenders = [
        cell
        for cell in re.findall(r"<td[^>]*>([^<]*)</td>", html)
        if BREAKABLE.search(cell)
    ]
    assert not offenders, (
        f"{len(offenders)} cell(s) may wrap between the two judges' values, "
        f"which is what put a figure out of reach of the print check: {offenders[:5]}"
    )
