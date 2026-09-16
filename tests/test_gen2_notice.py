"""The Gen-2 notice on the leaderboard: a link to something that exists.

The index page says that a second generation is in preparation and links to
its candidate catalog. Nothing visible goes on `index.html` without a committed
artefact and a test binding it, so this holds the notice to three things: the
catalog page it links to is published beside it, the two repository files it
names are tracked, and the notice claims no number and no result.
"""

from __future__ import annotations

import re
from pathlib import Path

from tnb import report

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = report.TEMPLATE_DIR / "leaderboard.html"
INDEX = REPO / "docs" / "index.html"


def _notice(text: str) -> str:
    match = re.search(r'<p class="methods-link" id="gen2-notice">.*?</p>', text, re.S)
    assert match, "the Gen-2 notice is not on the page"
    return match.group(0)


def _links(notice: str) -> list[str]:
    return re.findall(r'href="([^"]+)"', notice)


def test_the_notice_links_to_the_catalog_page_and_to_tracked_files():
    notice = _notice(TEMPLATE.read_text(encoding="utf-8"))
    links = _links(notice)
    assert links[0] == "gen2-catalog.html"
    assert (REPO / "docs" / "gen2-catalog.html").is_file(), "the notice links to no page"
    prefix = "https://github.com/JanNehyba/therapy-note-bench/blob/main/"
    for link in links[1:]:
        assert link.startswith(prefix)
        assert (REPO / link.removeprefix(prefix)).is_file(), f"{link} names a missing file"
    assert {link.removeprefix(prefix) for link in links[1:]} == {
        "docs/gen2.md",
        "research/gen2/protocol.json",
    }


def test_the_notice_says_what_gen2_is_not():
    notice = _notice(TEMPLATE.read_text(encoding="utf-8"))
    flat = re.sub(r"<[^>]+>", "", notice)
    assert "in preparation" in flat
    assert "no human acceptance" in flat
    assert "nothing from it is scored" in flat
    # A figure typed into the template would be a claim nothing checks.
    assert not re.search(r"(?<![\w-])\d", re.sub(r"Gen-2|Generation 2", "", flat))


def test_the_published_page_carries_the_same_notice():
    """`tnb report` copies the template; a page rebuilt from an older template
    would announce nothing, and one hand-edited would announce something else."""
    if not INDEX.is_file():
        return
    assert _notice(INDEX.read_text(encoding="utf-8")) == _notice(
        TEMPLATE.read_text(encoding="utf-8")
    )
