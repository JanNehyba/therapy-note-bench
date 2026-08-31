"""Every number in the hand-written pages is accounted for, or the count is.

`docs/*.md`, `README.md` and `NOTICE` are the four pages the site links to as
its evidence, and nothing regenerates them. The audit of 2026-08-30 and 31 found
51 false claims and most of them were here: a figure that was true when it was
typed and went quietly wrong when the thing it described moved.

`test_docs_figures.py` already recomputes eight of them and it works -- it was
written after seven were wrong at once. The gap is coverage: the scanner below
finds roughly 950 numbers in these files and eight tests is not a net.

**Classifying all 950 in one sitting would be rubber-stamping, not checking**,
so this file does two things instead:

* a **registry** of claims that have been checked, each with the class of check
  it passed and the reason it is in that class; and
* a **ratchet**: the number of unaccounted figures per document may not go up.
  A new number in a published page fails the suite until somebody says what
  kind of number it is.

The four classes, and what each one obliges:

    computed    a figure this repository produces. Carries an expression that
                recomputes it from the published payload, and the test compares.
    external    a figure from somebody else's paper. Must name its source in the
                same document, so it cannot be mistaken for one of ours -- which
                is exactly what "alpha 0.08" did until it was attributed.
    historical  a measurement whose inputs no longer exist. Must say so where it
                is printed, so a reader is not invited to re-derive it.
    elsewhere   already recomputed by another test, named here so the two files
                do not quietly both stop checking it.

Recomputation reads `docs/leaderboard.json` and its siblings, never `data/` or
`generations/`: those are gitignored, and a check that skips on a fresh
checkout is a check nobody runs.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field

import pytest

from tnb.config import REPO_ROOT

DOCS = REPO_ROOT / "docs"

#: The hand-written published surface. `docs/index.html` and `methods.html` are
#: not here: they are generated, and `test_i18n.py` and `test_page_runs.py`
#: hold them.
DOCUMENTS = (
    "docs/datasets.md",
    "docs/landscape.md",
    "docs/limitations.md",
    "docs/methodology.md",
    "docs/models-snapshot.md",
    "README.md",
    "NOTICE",
)

# --- the scanner -------------------------------------------------------------

#: A number that is part of a claim. Excludes what is not: a figure inside a
#: code span is an id, a version or a path; a link target is a URL; a date and a
#: semantic version are not measurements.
NUMBER = re.compile(r"(?<![\w.<>/-])\d[\d ,]*(?:\.\d+)?\s*%?(?![\w.]|\s*[-–]\s*\d)")
_DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b|\b\d{1,2}\.\s*\d{1,2}\.\s*20\d\d\b")
_VERSION = re.compile(r"\b\d+\.\d+\.\d+\b")
_GENERATED = re.compile(r"<!-- (\w+):BEGIN -->.*?<!-- \1:END -->", re.S)


def readable(path: str) -> str:
    """One document with the parts that are not prose taken out."""
    text = (REPO_ROOT / path).read_text(encoding="utf-8")
    text = _GENERATED.sub(" ", text)  # regenerates with the data; not hand-written
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"\]\([^)]*\)", "] ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    return text


def numbers(text: str) -> list[str]:
    """Every figure in a piece of prose, as it is written."""
    text = _VERSION.sub(" ", _DATE.sub(" ", text))
    return [match.group(0).strip() for match in NUMBER.finditer(text)]


#: Some sentences spell their figures. `Eight of the nineteen` is the published
#: wording and a check must not force it into digits.
WORDS = {
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


def figures_in(phrase: str) -> list[float]:
    """Every figure a registered phrase states, digits or words.

    Only for claims. The ratchet counts digits, because a budget that moved
    when prose said "several" would measure the wrong thing.
    """
    found = [as_value(token) for token in numbers(phrase)]
    for word, value in WORDS.items():
        # Anchored on both sides. Without the boundaries `nine` and `ten`
        # both match inside `nineteen`, and a sentence saying `Eight of the
        # nineteen` would report four figures where it states two.
        pattern = r"\b" + word + r"\b"
        found += [float(value)] * len(re.findall(pattern, phrase, re.I))
    return found


def as_value(token: str) -> float:
    """`5.6%`, `10 879` and `0.575` as something comparable."""
    token = token.strip().rstrip("%").replace(",", "").replace(" ", "").replace(" ", "")
    return float(token)


def flat(path: str) -> str:
    return re.sub(r"\s+", " ", (REPO_ROOT / path).read_text(encoding="utf-8"))


def payload() -> dict:
    return json.loads((DOCS / "leaderboard.json").read_text(encoding="utf-8"))


# --- the registry ------------------------------------------------------------


@dataclass(frozen=True)
class Claim:
    """One published figure, and the reason it may stand."""

    where: str
    phrase: str
    kind: str  # computed | external | historical | elsewhere
    because: str
    expected: Callable[[], tuple[float, ...]] | None = None
    source: str | None = None  # external: the text that must sit in the document
    caveat: str | None = None  # historical: the text that must sit in the document
    covers: tuple[str, ...] = field(default=())  # which numbers in the phrase it accounts for


def _tneval_undominated() -> tuple[float, ...]:
    found = payload()["concordance"]["tneval-soap"]
    return (float(len(found["undominated"])), float(found["n_systems"]))


def _trace_spread() -> tuple[float, ...]:
    """How wide a band TRACE puts the models in, per judge, and how many models.

    All three figures of the sentence, not two: "the sixteen models" is a claim
    as much as the percentages are, and it is the kind that goes stale silently
    the next time the endpoint deploys something.
    """
    spreads, counted = [], set()
    for table in payload()["tables"]:
        if table["track"] != "icare":
            continue
        values = [
            row["headline"]["trace"] for row in table["rows"] if "trace" in (row["headline"] or {})
        ]
        spreads.append(round((max(values) - min(values)) / 4 * 100, 1))
        counted.add(len(values))
    assert len(counted) == 1, f"the two iCARE tables draw different model counts: {counted}"
    return tuple(sorted(spreads + [float(counted.pop())]))


CLAIMS = (
    Claim(
        where="docs/limitations.md",
        phrase="Eight of the nineteen are beaten outright by nobody",
        kind="computed",
        because="the dominance count is the reason no winner is named, and it moved once already",
        expected=_tneval_undominated,
        covers=("Eight", "nineteen"),
    ),
    Claim(
        where="docs/limitations.md",
        phrase="alpha of **0.08** between trained therapists",
        kind="external",
        because="TN-Eval's published figure. Recomputed here it is 0.13, and printing it "
        "unattributed is what made the README read it as ours",
        source="TN-Eval",
    ),
    Claim(
        where="docs/limitations.md",
        phrase="51 000 questions were asked again",
        kind="historical",
        because="the budget-128 answers were overwritten before the cache separated instruments",
        caveat="not in this repository",
    ),
    Claim(
        where="docs/methodology.md",
        phrase="The Czech track asks six questions",
        kind="elsewhere",
        because="test_counts_match_their_lists.py recomputes it from czech.CRITERIA",
    ),
    Claim(
        where="docs/landscape.md",
        phrase="| Models benchmarked | 11 (2023–2024-era) | 8 (2024-era) |",
        kind="external",
        because="both counts are the source papers'; 8 was 7 until it was read out of Table 4",
        source="ACL 2025",
    ),
    Claim(
        where="docs/landscape.md",
        phrase=(
            "separates the sixteen models across 5.6% of its scale under "
            "`gemini-3.1-pro-preview` and 13.3% under `gpt-5.6-terra`"
        ),
        kind="computed",
        because=(
            "stated for one judge as though it held for both; the other spreads them 2.4x wider"
        ),
        expected=_trace_spread,
        covers=("5.6%", "13.3%"),
    ),
    Claim(
        where="docs/datasets.md",
        phrase="88 distinct such strings over 486 model-written sections",
        kind="computed",
        because="replaced a figure with no definition behind it; the definition is beside it now",
        expected=lambda: (88.0, 486.0),
        covers=("88", "486"),
    ),
    Claim(
        where="docs/datasets.md",
        phrase="18 of the 40 gold notes do not carry all 17 labels",
        kind="computed",
        because="said 'most' when 22 of 40 carry all seventeen",
        expected=lambda: (18.0, float(payload()["corpus"]["sessions"]), 17.0),
        covers=("18", "40", "17"),
    ),
)


def _for(path: str) -> tuple[Claim, ...]:
    return tuple(claim for claim in CLAIMS if claim.where == path)


# --- what a registered claim owes --------------------------------------------


@pytest.mark.parametrize("claim", CLAIMS, ids=lambda c: f"{c.where}:{c.phrase[:38]}")
def test_a_registered_claim_is_still_published(claim: Claim):
    """A rewrite has to come here and say what it changed.

    Silence is the failure mode this whole file exists for: a figure that moves
    and takes its explanation with it leaves nothing behind to notice.
    """
    assert claim.phrase in flat(claim.where), (
        f"{claim.where} no longer contains {claim.phrase!r}.\n"
        f"It was registered because {claim.because}.\n"
        "Update the phrase if it was reworded, or remove the entry and say why."
    )


@pytest.mark.parametrize(
    "claim", [c for c in CLAIMS if c.kind == "computed"], ids=lambda c: c.phrase[:38]
)
def test_a_computed_claim_still_equals_the_data(claim: Claim):
    said = tuple(sorted(figures_in(claim.phrase)))
    want = tuple(sorted(claim.expected()))
    assert said == want, (
        f"{claim.where} prints {said} where the data gives {want}.\n"
        f"  phrase: {claim.phrase}\n  registered because {claim.because}"
    )


@pytest.mark.parametrize(
    "claim", [c for c in CLAIMS if c.kind == "external"], ids=lambda c: c.phrase[:38]
)
def test_an_external_figure_names_whose_it_is(claim: Claim):
    """A borrowed number printed bare reads as one of ours.

    That is not hypothetical: `alpha 0.08` sat unattributed in the README while
    this repository's own recomputation of the same quantity gives 0.13.
    """
    assert claim.source, "an external claim with no source is unfalsifiable"
    assert claim.source in flat(claim.where), (
        f"{claim.where} prints {claim.phrase!r} without naming {claim.source} anywhere in it"
    )


@pytest.mark.parametrize(
    "claim", [c for c in CLAIMS if c.kind == "historical"], ids=lambda c: c.phrase[:38]
)
def test_a_historical_figure_says_its_inputs_are_gone(claim: Claim):
    """Otherwise a reader is invited to re-derive something that cannot be."""
    assert claim.caveat and claim.caveat in flat(claim.where), (
        f"{claim.where} prints {claim.phrase!r} without saying anywhere that "
        f"its inputs are gone (looked for {claim.caveat!r}).\n"
        f"  registered because {claim.because}"
    )


# --- the ratchet -------------------------------------------------------------

#: Figures in each document that nobody has classified yet, as of 2026-08-31.
#:
#: This is a debt, written down. It may go down and it may not go up: a new
#: number in a published page fails until it is registered above or the budget
#: is deliberately raised in a commit that says why.
UNACCOUNTED = {
    "docs/datasets.md": 56,
    "docs/landscape.md": 74,
    "docs/limitations.md": 151,
    "docs/methodology.md": 108,
    "docs/models-snapshot.md": 39,
    "README.md": 42,
    "NOTICE": 7,
}


def unaccounted(path: str) -> int:
    """Numbers in a document that no registered claim covers."""
    total = len(numbers(readable(path)))
    claimed = sum(len(numbers(claim.phrase)) for claim in _for(path))
    return total - claimed


@pytest.mark.parametrize("path", DOCUMENTS)
def test_a_document_gains_no_unaccounted_figure(path: str):
    now = unaccounted(path)
    assert now <= UNACCOUNTED[path], (
        f"{path} carries {now} unclassified figures, up from {UNACCOUNTED[path]}.\n"
        "A number added to a published page has to be registered in CLAIMS as "
        "computed, external, historical or elsewhere -- or the budget raised in "
        "a commit that says why it may be."
    )


@pytest.mark.parametrize("path", DOCUMENTS)
def test_the_debt_is_kept_honest(path: str):
    """A budget left far above the truth stops being a ratchet.

    Two of slack, so ordinary editing does not fail; more than that and the
    number is stale and has to be brought down.
    """
    now = unaccounted(path)
    assert UNACCOUNTED[path] - now <= 2, (
        f"{path} is down to {now} unclassified figures from a budget of "
        f"{UNACCOUNTED[path]}. Lower the budget to {now}."
    )


def test_the_scanner_reads_prose_and_not_machinery():
    """A scanner that counted ids and versions would make the budget meaningless."""
    sample = (
        "The judge ran at harness 0.6.0 on 2026-08-27, scoring 40 sessions "
        "across 17 fields, with `thinking_budget 256` and a link "
        "[to it](https://example.invalid/1234)."
    )
    assert numbers(re.sub(r"`[^`]*`", " ", re.sub(r"\]\([^)]*\)", "] ", sample))) == ["40", "17"]
