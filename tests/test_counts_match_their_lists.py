"""A count written into prose, checked against the list it is describing.

Six of the fifty-one false claims found on 2026-08-30 and 31 were this one
mistake: a sentence states how many things there are, a few lines above or
below the list itself, and the list grows.

    "one of the five inputs carries a licence"      six, and two carry one
    "two of them publish no licence at all"         three, and a fourth has a badge
    "Two of the four iCARE columns"                 five
    "The Czech track asks seven questions"          six since 2026-08-28

Each was true when written. Nothing tied it to the thing it counts, so each
went quietly wrong the day that thing changed, and the same repository printed
the right number four hundred lines away in a sentence built from the data.

The shape of the fix: a count in prose is either interpolated from the list --
which several already are, and those never broke -- or it is registered here
with the expression that recomputes it. A phrase that stops matching fails
loudly, which is the point: a rewrite has to come and say what the new count is
rather than leaving a stale one behind.

Numbers are written as words in some of these sentences and as digits in
others, and both spellings are the published wording. `as_number` reads either
so a check does not force a rewrite into digits.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

import pytest

from tnb import report
from tnb.config import REPO_ROOT
from tnb.scoring import czech as czech_scorer

WORDS = {
    "no": 0,
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}


def as_number(token: str) -> int:
    """`8`, `eight` and `Eight` are the same count differently spelled."""
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    if token in WORDS:
        return WORDS[token]
    raise AssertionError(f"{token!r} is neither a digit nor a number word")


def carrying_a_licence() -> int:
    """A source with terms, as against one publishing none or showing a badge."""
    return sum(
        1
        for source in report.LICENCES
        if "none published" not in source["licence"] and "badge" not in source["licence"]
    )


def publishing_none() -> int:
    return sum(1 for source in report.LICENCES if "none published" in source["licence"])


@dataclass(frozen=True)
class Check:
    """One published sentence, and what its numbers must equal."""

    where: str
    pattern: str
    expected: Callable[[], tuple[int, ...]]
    why: str


CHECKS = (
    Check(
        where="README.md",
        pattern=r"\*\*(\w+) of the (\w+) inputs carry a licence",
        expected=lambda: (carrying_a_licence(), len(report.LICENCES)),
        why="the table of sources is printed six lines below this sentence",
    ),
    Check(
        where="src/tnb/templates/methods.html",
        pattern=r"<strong>(\w+) of the (\w+) carry a licence; (\w+) publish none",
        expected=lambda: (carrying_a_licence(), len(report.LICENCES), publishing_none()),
        why="the same list, drawn as a table directly underneath",
    ),
    Check(
        where="src/tnb/templates/leaderboard.html",
        pattern=r"(\w+) of them publish no licence at all",
        expected=lambda: (publishing_none(),),
        why="the Sources line names every one of them in the same sentence",
    ),
    Check(
        where="src/tnb/templates/methods.html",
        pattern=r"(\w+) of the (\w+) iCARE columns measure",
        expected=lambda: (2, len(report.MEASURE_TABLES["icare"])),
        why="ROUGE-L and BERTScore of five; the other three are drawn beside them",
    ),
    Check(
        where="docs/methodology.md",
        pattern=r"The Czech track asks (\w+) questions about a note",
        expected=lambda: (len(czech_scorer.CRITERIA),),
        why="said seven for three days after the seventh criterion was deleted",
    ),
    Check(
        where="docs/methodology.md",
        pattern=r"None of the (\w+) criteria therefore asks",
        expected=lambda: (len(czech_scorer.CRITERIA),),
        why="the same count, in the same document, restated",
    ),
    Check(
        where="docs/methodology.md",
        pattern=r"All (\w+) ask about the absence of a fault",
        expected=lambda: (len(czech_scorer.CRITERIA),),
        why="and again",
    ),
    Check(
        where="docs/limitations.md",
        pattern=r"scored on (\w+) yes/no criteria",
        expected=lambda: (len(czech_scorer.CRITERIA),),
        why="the same instrument described on the page that bounds what it claims",
    ),
)


def _flat(path: str) -> str:
    """Markdown and HTML both wrap, so a sentence spans lines in the file."""
    return re.sub(r"\s+", " ", (REPO_ROOT / path).read_text(encoding="utf-8"))


@pytest.mark.parametrize("check", CHECKS, ids=lambda c: f"{c.where}:{c.pattern[:34]}")
def test_the_count_matches_the_list(check: Check):
    found = re.search(check.pattern, _flat(check.where))
    assert found, (
        f"{check.where} no longer contains a sentence matching {check.pattern!r}.\n"
        f"It was registered here because {check.why}. If the sentence was "
        "rewritten, update the pattern; if the claim was dropped, remove the "
        "check and say so."
    )
    said = tuple(as_number(group) for group in found.groups())
    assert said == check.expected(), (
        f"{check.where} says {said} where the data says {check.expected()}.\n"
        f"  sentence: {found.group(0)}\n  registered because {check.why}"
    )


def test_every_check_is_about_a_number_that_can_move():
    """A check whose expectation is a literal proves nothing.

    Half of these would have passed while the page was wrong if the expected
    value had been typed in beside the sentence instead of computed.
    """
    computed = [c for c in CHECKS if c.expected.__code__.co_names]
    assert len(computed) >= len(CHECKS) - 1, (
        "checks with no call in their expectation are pinning a literal against "
        "a literal: " + ", ".join(c.where for c in CHECKS if c not in computed)
    )
