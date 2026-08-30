"""Every Czech sentence in the briefing's dictionary still answers an English one.

One direction of this was already guarded and the other was not. `czech_brief._t`
raises `Untranslated` rather than falling back, so an English sentence with no
Czech stops the build -- the document cannot go out half-translated. Nothing
watched the reverse: a chapter deleted from `czech_brief.py` leaves its Czech
behind in `czech_brief_cs.py`, and the dictionary slowly becomes a shadow copy of
a document that no longer exists. Rewriting this briefing deleted about a third
of it and stranded thirty-five entries, several of them carrying figures the run
they were written from no longer produces -- "the two judges agree on 79% of
notes", "the lowest of the seven" when there are six criteria. Nothing was wrong
with the document; it was wrong with the file a translator reads.

**Reachability, not execution.** What is checked is that every key is a sentence
the translating tools still contain, rather than that some build looked it up.
The difference matters because several entries here are branches this data does
not reach on purpose -- the box that would print if the two judges never
disagreed about a band, the paragraph that would print if one of the three views
turned out redundant -- and they are written and translated in advance so that
the day the data changes the document does not fall into English in the one
paragraph that changed. A test keyed on what one build asked for would delete
exactly those, and would also depend on `local/`, which is not in version
control and is absent from any fresh checkout.

What it does not catch, said rather than left to be discovered: a key whose
English is in one of these files as something other than a sentence -- a
dictionary key, a message printed to stderr -- passes. Those were swept by hand
once and would have to be swept by hand again.
"""

from __future__ import annotations

import ast
import re
import sys

from tnb import i18n
from tnb.config import REPO_ROOT

TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from czech_brief_cs import CS  # noqa: E402

#: Every tool whose sentences reach the briefing, and each is here for its own
#: reason. `czech_brief` writes the document. `czech_figures` draws the four
#: charts and puts their titles, axes and source lines through the same `_t`,
#: so a chart's axis label is as much this dictionary's business as a paragraph
#: is. `czech_join` writes its caveats into `local/czech-join.json` and the
#: document reads them back out and translates them there, so its prose is
#: never a literal in `czech_brief` and would otherwise read as dead.
TRANSLATING = ("czech_brief.py", "czech_figures.py", "czech_join.py")


def _sentences() -> set[str]:
    """Every string these tools contain, normalised the way `_t` normalises a key."""
    found: set[str] = set()
    for name in TRANSLATING:
        tree = ast.parse((TOOLS / name).read_text(encoding="utf-8"))
        found |= {
            i18n.norm(node.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
    return found


def test_every_czech_sentence_still_answers_an_english_one():
    """A key nothing asks for is Czech that will never be read, and worse than
    that: it is a translation of a claim the document has stopped making, kept
    where the next person to correct the Czech will read it as current."""
    orphans = sorted(key for key in CS if i18n.norm(key) not in _sentences())

    assert not orphans, (
        "Czech with no English left to answer, in "
        + ", ".join(f"tools/{name}" for name in TRANSLATING)
        + f" ({len(orphans)}). Delete each, or say which tool its English moved to:\n  "
        + "\n  ".join(repr(key[:90]) for key in orphans)
    )


def test_the_check_would_notice_a_dead_key():
    """The assertion above passes trivially if `_sentences` ever comes back with
    everything -- an over-broad file list, a parse that silently returns nothing.
    A sentence nobody has ever written must not be found in it."""
    invented = "a paragraph that was deleted from this briefing three commits ago"

    assert i18n.norm(invented) not in _sentences()


def test_every_tool_in_the_list_is_carrying_its_own_weight():
    """`TRANSLATING` is hand-kept and widening it is how the check above gets
    quietly disabled: name enough files and every orphan is forgiven by one of
    them. Each entry has to answer for itself -- some Czech in this dictionary
    must be answered by that file and by no other. Two of the files are here for
    a handful of sentences each, which is exactly the case where an entry could
    stop being load-bearing without anybody noticing."""
    for name in TRANSLATING:
        tree = ast.parse((TOOLS / name).read_text(encoding="utf-8"))
        mine = {
            i18n.norm(node.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        others: set[str] = set()
        for other in TRANSLATING:
            if other == name:
                continue
            elsewhere = ast.parse((TOOLS / other).read_text(encoding="utf-8"))
            others |= {
                i18n.norm(node.value)
                for node in ast.walk(elsewhere)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
            }
        answered = {i18n.norm(key) for key in CS} & mine - others

        assert answered, (
            f"tools/{name} is in TRANSLATING and no Czech entry needs it. Either its "
            "prose has moved, in which case take it out of the list, or the entries it "
            "answered have been deleted."
        )


# --- the third direction: English that never reaches `_t` at all --------------

#: Text between two HTML tags that is not prose a reader is being told something
#: in. `&mdash;` and `&nbsp;` are punctuation; SOAP and Deepsy are the names of
#: two note formats and are written the same way in Czech.
NOT_PROSE = ("&mdash;", "&nbsp;", "SOAP", "Deepsy")


def test_no_cell_of_the_briefing_is_written_straight_into_its_html():
    """English that never reaches `_t` cannot be caught by a missing key.

    Both checks above ask whether a sentence has a Czech twin. Neither can see a
    sentence that is never looked up: three cells of the sabotage-control table
    were written as `"<td>found it</td>"`, so the Czech document printed "found
    it" twelve times, and the two cells that appear only when a criterion fails
    would have told a Czech reader that in English on the day it happened.

    What is checked is the text between two tags in a literal, which is where a
    cell written by hand ends up. A phrase that is the same word in both
    languages is named in `NOT_PROSE` rather than passed over silently.
    """
    tree = ast.parse((TOOLS / "czech_brief.py").read_text(encoding="utf-8"))
    leaked = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        for between in re.findall(r">([^<>]+)<", node.value):
            plain = re.sub(r"\{[^}]*\}", "", between).strip()
            if re.search(r"[A-Za-z]{2}", plain) and plain not in NOT_PROSE:
                leaked.append(f"line {node.lineno}: {plain!r}")

    assert not leaked, (
        "tools/czech_brief.py writes English into its own HTML, where `_t` never "
        "sees it and the Czech build cannot stop:\n  " + "\n  ".join(leaked)
    )


def test_the_check_would_notice_a_hand_written_cell():
    """The assertion above is a regex over literals and would pass on a file it
    failed to read. A cell of the shape it is looking for is put in front of it
    here."""
    tree = ast.parse('CELL = "<td>found it</td>"')
    between = [
        text
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        for text in re.findall(r">([^<>]+)<", node.value)
    ]

    assert between == ["found it"]
