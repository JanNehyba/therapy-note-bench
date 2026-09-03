"""A count written into prose, checked against the list it is describing.

Six of the fifty-one false claims found on 2026-08-30 and 31 were this one
mistake: a sentence states how many things there are, a few lines above or
below the list itself, and the list grows.

    "one of the five inputs carries a licence"      six, and two carry one
    "two of them publish no licence at all"         three, and a fourth has a badge
    "Two of the four iCARE columns"                 five
    "scored on seven yes/no criteria"               six since 2026-08-28

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

from tnb import report, results
from tnb.config import REPO_ROOT

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
    #: The list the expectation reads, as (module, attribute). Named rather
    #: than inferred, because the guard below proves the dependency by growing
    #: that list and requiring the expected value to move. A check that names
    #: no list is a literal pinned against a literal, which is what this file
    #: exists to forbid, so it may not be omitted.
    reads: tuple[object, str] = ()


CHECKS = (
    Check(
        where="README.md",
        pattern=r"\*\*(\w+) of the (\w+) inputs carry a licence",
        expected=lambda: (carrying_a_licence(), len(report.LICENCES)),
        why="the table of sources is printed six lines below this sentence",
        reads=(report, "LICENCES"),
    ),
    Check(
        where="src/tnb/templates/methods.html",
        pattern=r"<strong>(\w+) of the (\w+) carry a licence; (\w+) publish none",
        expected=lambda: (carrying_a_licence(), len(report.LICENCES), publishing_none()),
        why="the same list, drawn as a table directly underneath",
        reads=(report, "LICENCES"),
    ),
    Check(
        where="src/tnb/templates/leaderboard.html",
        pattern=r"(\w+) of them publish no licence at all",
        expected=lambda: (publishing_none(),),
        why="the Sources line names every one of them in the same sentence",
        reads=(report, "LICENCES"),
    ),
    Check(
        where="src/tnb/templates/methods.html",
        pattern=r"(\w+) of the (\w+) iCARE columns measure",
        expected=lambda: (2, len(report.MEASURE_TABLES["icare"])),
        why="ROUGE-L and BERTScore of five; the other three are drawn beside them",
        reads=(report, "MEASURE_TABLES"),
    ),
    Check(
        where="src/tnb/templates/leaderboard.html",
        pattern=r"agree on all (\w+) of track, harness version",
        expected=lambda: (len(results.COMPARABILITY_KEYS),),
        why="the sentence then lists them, and the list is the comparability key itself",
        reads=(results, "COMPARABILITY_KEYS"),
    ),
    Check(
        where="src/tnb/templates/methods.html",
        pattern=r"agree on all (\w+) of track, harness version",
        expected=lambda: (len(results.COMPARABILITY_KEYS),),
        why="the same sentence, on the other page",
        reads=(results, "COMPARABILITY_KEYS"),
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


@pytest.mark.parametrize("check", CHECKS, ids=lambda c: f"{c.where}:{c.pattern[:34]}")
def test_the_expectation_moves_when_its_list_does(check: Check, monkeypatch):
    """A check whose expectation is a literal proves nothing, demonstrated.

    The first version of this test asked whether `expected.__code__.co_names`
    was non-empty, which is true of *any* lambda that mentions a global -- so
    replacing all eight expectations with `lambda: (int("2"), int("5"))`, a
    literal pinned against a literal, left it green. It also tolerated one
    check with a bare literal, on the theory that one is harmless.

    So the dependency is proved instead of inspected: the list the check names
    is grown by one entry and the expectation has to notice. Nothing is
    published from the mutated list -- `monkeypatch` puts it back.
    """
    module, attribute = check.reads
    before = check.expected()
    current = getattr(module, attribute)

    moved = False
    for grown in _grown(current):
        monkeypatch.setattr(module, attribute, grown)
        try:
            moved = check.expected() != before
        finally:
            monkeypatch.setattr(module, attribute, current)
        if moved:
            break

    assert moved, (
        f"{check.where}: no way of growing {attribute} moved the expected value "
        f"from {before}, so this check pins a literal against a literal and would "
        "stay green while the page went wrong. Compute it from the list."
    )


def _grown(current):
    """Every way of adding one entry that might move a count.

    More than one, because a count that filters does not move for every entry:
    `publishing_none()` counts the sources with no licence, so duplicating a
    licensed one leaves it where it was, and a single probe pronounced a working
    check dead. A count that reads the list at all moves for *some* entry, so
    the assertion is over the set rather than over one guess.
    """
    if isinstance(current, dict):
        for key, value in current.items():
            if isinstance(value, (list, tuple)):
                yield {**current, key: type(value)([*value, value[0]])}
            elif isinstance(value, dict) and value:
                # A table of tables: `MEASURE_TABLES["icare"]` is the five iCARE
                # columns, and only growing *that* moves a count of them.
                probe = next(iter(value))
                yield {**current, key: {**value, "__probe__": value[probe]}}
        if current:
            yield {**current, "__probe__": next(iter(current.values()))}
        return
    for element in current:
        yield type(current)([*current, element])
