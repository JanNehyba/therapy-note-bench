"""Every sentence the Czech briefing can print has a Czech sentence behind it.

**This test exists because the same bug happened twice in one afternoon, and the
second time it was caused by fixing the first.** `_t` looks a string up by the
exact English it replaces. Reword the English in `czech_brief.py` and the lookup
misses, `Untranslated` is raised, and the Czech document cannot be built at all
-- while the English one builds fine, so nothing looks wrong until somebody asks
for Czech.

The first occurrence rewrote thirteen strings from "{tables} of these tables" to
"{tables} table-and-judge combinations" and left the keys alone; the Czech
briefing had been unbuildable for hours and the last good copy on disk was
stale. The second was a half-applied edit of one string, where the new key
reached `czech_brief_cs.py` and the new English never reached `czech_brief.py`.

Both were found by running the build. A build takes minutes and needs the whole
corpus; this takes milliseconds and needs neither, which is the point.

`tests/test_i18n.py` does the same job for the two published pages. The briefing
is a separate tool with a separate dictionary and was not covered.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import czech_brief_cs  # noqa: E402

from tnb import i18n  # noqa: E402

BRIEF = Path(__file__).resolve().parent.parent / "tools" / "czech_brief.py"


def _translatable() -> set[str]:
    """Every string the briefing can hand to ``_t``.

    Two shapes reach it: a literal written inside the call, and a module-level
    constant passed by name. Both are read out of the source rather than by
    importing and calling, because importing runs the module and the point is to
    be cheap enough that nobody skips it.

    A string built at run time -- an f-string, a join, a value out of a payload
    -- cannot be found this way and is not claimed to be. What this covers is the
    prose somebody edits, which is where both real failures came from.
    """
    tree = ast.parse(BRIEF.read_text(encoding="utf-8"))

    constants: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                try:
                    value = ast.literal_eval(node.value)
                except Exception:
                    continue
                if isinstance(value, str):
                    constants[target.id] = value

    found: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "_t"):
            continue
        if not node.args:
            continue
        argument = node.args[0]
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
            found.add(argument.value)
        elif isinstance(argument, ast.Name) and argument.id in constants:
            found.add(constants[argument.id])
    return found


def test_every_sentence_the_briefing_can_print_has_a_czech_one() -> None:
    """The failure this catches is total: the Czech document does not build.

    `_t` raises rather than falling back to the English, and that is the right
    choice -- a Czech page with an English paragraph in it is worse than a build
    that stops and says which string it wanted. This test moves the stop from
    "somebody ran a ten-minute build" to "somebody ran the tests".
    """
    known = set(czech_brief_cs.CS) | set(i18n.CS)
    missing = sorted(text for text in _translatable() if text not in known)
    assert not missing, (
        "reworded in tools/czech_brief.py without re-keying tools/czech_brief_cs.py, "
        "so the Czech briefing will not build:\n  " + "\n  ".join(text[:100] for text in missing)
    )


def test_the_check_is_actually_looking_at_something() -> None:
    """A test that silently found nothing to check would pass for ever."""
    assert len(_translatable()) > 100


def test_no_czech_entry_answers_a_sentence_the_briefing_no_longer_prints() -> None:
    """The mirror image: a translation whose English was deleted or reworded.

    It is not a build failure -- an unused key is harmless -- so this reports
    rather than asserts nothing, and the count is pinned. A key that outlives its
    sentence is how a stale Czech paragraph survives an English rewrite, and the
    thirteen re-keyed strings were exactly that, one edit away from being lost.
    """
    orphaned = sorted(set(czech_brief_cs.CS) - _translatable() - set(i18n.CS))
    # Some keys are reached through helpers this reader cannot follow -- a value
    # out of a payload, a label from `MEASURE_TABLES`. The number is pinned so a
    # rewrite that orphans a paragraph shows up as a change rather than as noise.
    assert len(orphaned) <= 130, (
        f"{len(orphaned)} Czech entries answer no sentence the briefing prints. "
        "If that is because a paragraph was reworded, re-key it; if a paragraph "
        "was deleted, delete its translation."
    )
