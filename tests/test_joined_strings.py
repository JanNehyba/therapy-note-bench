"""A string split across two lines must not lose the space between them.

Python joins adjacent string literals silently, so

    "Released to benefit research community, with a citation "
    "requested. Fetched"
    "at run time."

publishes `Fetchedat run time.` and nothing complains. Two of these were live
on the public licence table for weeks -- `neverredistributed` and `Fetchedat` --
and they were found by a reader, not by the suite. The failure is invisible in
the source, because the two halves look correct one above the other, and
invisible to `ruff`, which has no opinion about what a concatenation means.

The rule, and why it has the shape it has:

    Flag a join where the left part ends with a letter, the right part begins
    with a letter, and the left part contains a space.

The last clause is what keeps it quiet. Prose wrapped mid-word is always a
mistake; an identifier, a URL or a long token split across lines is not, and
those have no spaces in the part before the break. Checked against every
Python file in the repository: with the two known faults repaired it fires
nowhere, and re-introducing either one is caught.

`tokenize`, not `ast`: the parser folds implicit concatenation into one
constant, so by the time there is a tree the join is gone.
"""

from __future__ import annotations

import ast
import io
import tokenize
from pathlib import Path

import pytest

from tnb.config import REPO_ROOT

#: Where a joined word is a published sentence rather than a variable name.
SEARCHED = ("src", "tests", "tools")

#: Constants whose contents are quoted from somewhere else, where a wrap inside
#: a word is correct and adding the space would corrupt the quotation.
#:
#: By the name the constant is assigned to, not by file: allow-listing
#: `report.py` would blind the licence table, which is where both of the faults
#: this test exists for actually shipped. One entry, one reason.
QUOTED_VERBATIM = {
    "SIMILARITY_EXAMPLE": (
        "an iHOPE note section and one model's answer, reproduced exactly; the "
        "line breaks are ours and the words are theirs"
    ),
}


def _owners(source: str) -> dict[int, str]:
    """Which module-level constant each line belongs to, if any."""
    lines: dict[int, str] = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Assign):
            continue
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if not names:
            continue
        for line in range(node.lineno, (node.end_lineno or node.lineno) + 1):
            lines[line] = names[0]
    return lines


def _literal(token: tokenize.TokenInfo) -> str | None:
    """The text a STRING token stands for, or None if it is not a plain one."""
    try:
        value = ast.literal_eval(token.string)
    except (ValueError, SyntaxError):
        return None
    return value if isinstance(value, str) else None


def joins_without_a_space(source: str) -> list[tuple[int, str, str]]:
    """Every implicit concatenation that glues two words together."""
    try:
        owner = _owners(source)
    except SyntaxError:
        owner = {}
    found = []
    previous: tokenize.TokenInfo | None = None
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT):
            continue
        if token.type == tokenize.STRING:
            if previous is not None:
                left, right = _literal(previous), _literal(token)
                if (
                    left
                    and right
                    and left[-1].isalpha()
                    and right[0].isalpha()
                    and " " in left
                    and owner.get(token.start[0]) not in QUOTED_VERBATIM
                ):
                    found.append((token.start[0], left[-24:], right[:24]))
            previous = token
        else:
            previous = None
    return found


def _files() -> list[Path]:
    return [
        path
        for directory in SEARCHED
        for path in sorted((REPO_ROOT / directory).rglob("*.py"))
        if "__pycache__" not in path.parts
    ]


def test_no_published_string_glues_two_words_together():
    """The two that shipped were `never` + `redistributed` and `Fetched` + `at`."""
    faults = []
    for path in _files():
        source = path.read_text(encoding="utf-8")
        for line, left, right in joins_without_a_space(source):
            faults.append(f"{path.relative_to(REPO_ROOT).as_posix()}:{line} ...{left}|{right}...")
    assert not faults, "a string was joined without its space:\n  " + "\n  ".join(faults)


def test_the_check_would_catch_the_two_that_shipped():
    """Pinned with the real text, so a rule relaxed into uselessness is caught.

    Without this, a future edit could narrow the rule until it fires on nothing
    and the test above would still be green.
    """
    shipped = (
        'x = ("The Apache licence is on the code repository, not this one. Fetched at run "\n'
        '     "time, never"\n'
        '     "redistributed.")\n'
    )
    assert joins_without_a_space(shipped), "the `neverredistributed` fault is no longer caught"

    also = "\n".join(
        (
            'y = ("Released to benefit research community, with a citation "',
            '     "requested. Fetched"',
            '     "at run time.")',
            "",
        )
    )
    assert joins_without_a_space(also), "the `Fetchedat` fault is no longer caught"


@pytest.mark.parametrize(
    "source",
    (
        # A space on either side of the break is the normal case.
        'x = ("a sentence that wraps "\n"onto the next line")\n',
        'x = ("a sentence that wraps"\n" onto the next line")\n',
        # A long token with no space before the break: a URL, an id, a digest.
        'x = ("https://example.invalid/some/very/long/"\n"path/that/continues")\n',
        # Punctuation at the seam is not two words.
        'x = ("ends with a full stop."\n"Starts a new one")\n',
    ),
)
def test_legitimate_wraps_are_not_flagged(source):
    """A rule that fires on ordinary wrapping would be turned off within a week."""
    assert not joins_without_a_space(source)
