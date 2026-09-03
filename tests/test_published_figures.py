"""Every figure a reader meets on a published page comes from a committed file.

`tests/test_published_numbers.py` holds the hand-written surface: the five
documents, the README, `NOTICE`. The two generated pages were left out of it,
with a comment saying they were held elsewhere. That comment used to name two
files. One of them was `tests/test_i18n.py`, which went with the Czech mirror
on 2026-09-03, and what remained checks that the pages *run* and that panels
*draw* -- not that the numbers on them are true.

So this is the ratchet's shape, pointed at the generated pages. It renders them
the way a reader gets them, reads every figure out of their prose, and requires
that some committed artefact holds a value that formats to it -- under the
page's own rounding rule, because a checker that rounds differently reports
faults that are its own. Anything else has to be listed below with what it is
and where it came from.

An audit of these pages on 2026-09-03 found no typed figure on either of them.
That is the state this file exists to keep: not to fix a fault, but to stop the
next one arriving unseen.
"""

import glob
import html
import json
import math
import re
import shutil
import subprocess
from dataclasses import dataclass

import pytest

from tnb.config import REPO_ROOT

DOCS = REPO_ROOT / "docs"
RUNNER = REPO_ROOT / "tests" / "support" / "run_page.js"

#: The pages a reader is given. `index.html` and `methods.html` draw themselves
#: from an inlined payload; `brief.html` is written whole by `tools/brief.py`
#: and has no script to run.
PAGES = ("index.html", "methods.html", "brief.html")


@dataclass(frozen=True)
class Accounted:
    """One figure on a page that no artefact holds, and the reason it may stand.

    `derived` -- the page computes it from figures it also publishes, so there
    is nothing to store and a stored copy could disagree with the arithmetic
    beside it. `quoted` -- somebody else's number, printed with whose it is.
    """

    page: str
    figure: str
    kind: str  # derived | quoted
    because: str


ACCOUNTED = (
    Accounted(
        page="methods.html",
        figure="0.077",
        kind="derived",
        because=(
            "the spread between the best and the worst per-system agreement, subtracted on "
            "the page from two figures the table immediately above it prints"
        ),
    ),
    Accounted(
        page="brief.html",
        figure="124",
        kind="derived",
        because="`figures.agreeing_pairs` counts the pairs; the count is not a stored value",
    ),
    Accounted(
        page="brief.html",
        figure="127",
        kind="derived",
        because="the denominator of the same count, from the same function",
    ),
    Accounted(
        page="brief.html",
        figure="2023",
        kind="quoted",
        because="the era the two source papers benchmarked. A date, not a measurement",
    ),
    Accounted(
        page="brief.html",
        figure="2024",
        kind="quoted",
        because="the same era, and the year of the two reference models the papers released",
    ),
)

#: TN-Eval's own figure for the agreement between its two therapists on
#: faithfulness, printed on both pages with their name beside it. It is not
#: interpolated from our calibration and must not be: the sentence says they
#: measured it. What is checked instead is that our recomputation has not
#: drifted away from it -- see the test at the foot of this file.
QUOTED_FAITHFULNESS_ALPHA = 0.18

NUMBER = re.compile(r"(?<![\w.])(−?-?\d+(?:[.,]\d+)?%?)(?![\w])")
BLOCK = re.compile(r"<(p|li|h1|h2|h3|h4|summary|dd|dt)\b[^>]*>(.*?)</\1>", re.S)


def _strip(text: str, *patterns: str) -> str:
    for pattern in patterns:
        text = re.sub(pattern, " ", text, flags=re.S)
    return text


def _rendered(page: str, workspace) -> str:
    """What the page's own script writes into the document.

    Every node it touched, not a list of panel names: a list goes stale the
    first time somebody adds a section, and going stale unnoticed is the
    failure this file exists to prevent.
    """
    source = (DOCS / page).read_text(encoding="utf-8")
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", source, re.S)
    if not scripts:
        return ""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the published pages cannot be executed here")
    # Into the test's own directory, never into the checkout. A scratch file
    # written beside the sources is one more thing another process can trip
    # over, and this suite has been run beside a second writer more than once.
    script = workspace / f"{page}.audit.js"
    script.write_text("\n".join(scripts), encoding="utf-8")
    finished = subprocess.run(
        [node, str(RUNNER), str(script), "--all"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    assert finished.returncode == 0 and "THREW" not in (finished.stdout or ""), (
        f"{page} does not run: {(finished.stdout or '') + (finished.stderr or '')}"
    )
    return finished.stdout or ""


def _prose(page: str, workspace) -> list[str]:
    """The sentences on one page: what the file says plus what its script says.

    Both halves, because either alone misses a fault the other would catch. The
    authored prose in the file never reaches the script's node map -- the
    quoted alpha in the methods footer lives there -- and the script's output is
    not in the file at all.
    """
    source = (DOCS / page).read_text(encoding="utf-8")
    static = _strip(source, r"<script.*?</script>", r"<style.*?</style>", r"<!--.*?-->")
    both = _strip(static + _rendered(page, workspace), r"<svg.*?</svg>", r"<table.*?</table>")
    blocks = []
    for match in BLOCK.finditer(both):
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", match.group(2)))).strip()
        if text:
            blocks.append(text)
    return blocks


def _pool() -> set[float]:
    """Every value the committed artefacts hold, however deep."""
    values: set[float] = set()

    def walk(value):
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            values.add(float(value))
        elif isinstance(value, dict):
            for held in value.values():
                walk(held)
        elif isinstance(value, list):
            for held in value:
                walk(held)
        elif isinstance(value, str):
            for found in re.finditer(r"-?\d+(?:\.\d+)?", value):
                values.add(float(found.group(0)))

    for path in sorted(glob.glob(str(DOCS / "*.json"))):
        with open(path, encoding="utf-8") as handle:
            walk(json.load(handle))
    return values


def page_format(value: float, digits: int) -> str:
    """The pages' own rounding, reimplemented rather than imported.

    `fmt` in `_helpers.html` rounds half away from zero on the decimal the
    payload publishes, having dropped the binary noise first, because
    `toFixed` rounds the binary approximation and printed a last digit that was
    not the rounding of the number a reader is told to check against. A checker
    using Python's `round` -- which goes to even -- reported three faults on
    2026-09-03 that were all its own.
    """
    scale = 10**digits
    magnitude = math.floor(float(f"{abs(value) * scale:.15g}") + 0.5) / scale
    return f"{-magnitude if value < 0 else magnitude:.{digits}f}"


def backed(token: str, pool: set[float]) -> bool:
    """Whether any published value formats to exactly this figure."""
    plain = token.replace("−", "-").replace(",", "").rstrip("%")
    try:
        wanted = float(plain)
    except ValueError:
        return True
    digits = len(plain.split(".")[1]) if "." in plain else 0
    target = f"{wanted:.{digits}f}"
    return any(
        page_format(value, digits) == target or page_format(value * 100, digits) == target
        for value in pool
    )


@pytest.fixture(scope="module")
def pool() -> set[float]:
    if not list(DOCS.glob("*.json")):
        pytest.skip("no artefacts in this checkout")
    return _pool()


@pytest.mark.parametrize("page", PAGES)
def test_every_figure_on_a_published_page_comes_from_a_committed_file(page, pool, tmp_path):
    """The one that would have caught a typed number arriving.

    Prose only. A table cell is drawn from the payload's own columns and rows
    by construction, and the tests that hold those are elsewhere; a sentence is
    where a figure gets typed, and where nothing was watching.
    """
    if not (DOCS / page).exists():
        pytest.skip(f"docs/{page} is not built in this checkout")

    allowed = {found.figure for found in ACCOUNTED if found.page == page}
    unaccounted = []
    for block in _prose(page, tmp_path):
        for token in NUMBER.findall(block):
            if token in allowed or backed(token, pool):
                continue
            unaccounted.append((token, block[:140]))

    assert not unaccounted, (
        f"docs/{page} states {len(unaccounted)} figure(s) no committed artefact holds. "
        "Either the page computes it -- in which case add it to ACCOUNTED as `derived`, "
        "saying which published figures it is computed from -- or it is somebody else's "
        "number and belongs there as `quoted` with whose it is. A figure typed into a "
        "sentence is the one thing this file exists to stop:\n  "
        + "\n  ".join(f"{token}  in: {where}" for token, where in unaccounted)
    )


def test_every_exception_is_still_needed(pool, tmp_path):
    """An allowance that has stopped being needed is a claim nobody rechecks.

    The ratchet keeps its debt honest the same way. A figure that has since
    become a stored value should be dropped from the list, not left standing as
    a permanent exemption for a number that no longer needs one.
    """
    stale = []
    for found in ACCOUNTED:
        if not (DOCS / found.page).exists():
            continue
        blocks = _prose(found.page, tmp_path)
        on_page = any(found.figure in NUMBER.findall(block) for block in blocks)
        if not on_page:
            stale.append(f"{found.page}: {found.figure} is allowed and is not on the page")
        elif backed(found.figure, pool):
            stale.append(f"{found.page}: {found.figure} is allowed and an artefact now holds it")
    assert not stale, "\n  ".join(["exceptions that have outlived their reason:"] + stale)


def test_every_exception_says_what_kind_it_is():
    """Two kinds and no third invented in passing, as the ratchet has it."""
    for found in ACCOUNTED:
        assert found.kind in {"derived", "quoted"}, f"{found.figure}: unknown kind {found.kind}"
        assert found.because, f"{found.figure} is allowed with no reason given"
        assert found.page in PAGES, f"{found.figure} is allowed on a page nobody publishes"


def test_our_own_figure_has_not_drifted_from_the_one_we_quote():
    """The pages say TN-Eval measured an alpha of 0.18 between two therapists.

    That figure is theirs and is printed with their name on it, so it is not
    interpolated from our calibration -- doing that would put our number in a
    sentence that credits them, and today the two agree closely enough that
    nobody would notice.

    What can be checked is the other half of the claim, which the leaderboard
    makes in as many words: that recomputing it from their released annotations
    gives the same. When that stops being true the sentence has to change, and
    this is what says so.
    """
    path = DOCS / "calibration.json"
    if not path.exists():
        pytest.skip("no calibration in this checkout")
    calibration = json.loads(path.read_text(encoding="utf-8"))
    ours = next(
        (
            found["alpha_humans"]
            for found in calibration.get("agreements", [])
            if found["name"] == "likert_faithfulness"
        ),
        None,
    )
    assert ours is not None, "the calibration no longer reports the therapists' faithfulness alpha"
    assert page_format(ours, 2) == f"{QUOTED_FAITHFULNESS_ALPHA:.2f}", (
        f"our recomputation gives {ours:.4f}, which prints as {page_format(ours, 2)}, "
        f"where the pages quote TN-Eval's {QUOTED_FAITHFULNESS_ALPHA:.2f} and say the two "
        "agree. One of the two sentences is now wrong"
    )
