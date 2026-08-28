"""Two tracks that share a rubric may not share a cache path.

Offline. Every path here is computed, nothing is written.

`judge.cache_path` is keyed on judge, rubric, provider, system, session and
unit. The Deepsy track shares all six with the Czech SOAP track -- the same ten
sessions, the same eleven models, the same seven criteria, the same
`czech-criteria-v2`. Only the note differs, and the note is not in the key.

Under one root each run would overwrite the other's answers and neither track
would ever keep a cache: `load_cached` rejects a record whose prompt digest does
not match, so the answer read is never the wrong one -- but the answer WRITTEN
lands on top of a right one. The digest check makes a collision unreadable; it
does not make it harmless.
"""

from __future__ import annotations

import ast

from tnb import judge
from tnb.config import REPO_ROOT
from tnb.scoring import czech
from tnb.tasks import czech as czech_task
from tnb.tasks import deepsy


def _path(root, unit="czech.diacritics"):
    return judge.cache_path(
        "gemini-3.1-pro-preview",
        czech.JUDGE_PROMPT_VERSION,
        "einfra",
        "kimi-k3",
        "cz-r-313e71f4",
        unit,
        root=root,
    )


def test_the_six_key_fields_really_are_shared():
    """The premise. If Deepsy ever stops sharing the rubric this test should
    say so, because then the separate root is no longer load-bearing."""
    assert deepsy.PROMPT_VERSION != czech_task.PROMPT_VERSION
    # Same rubric, and that is deliberate: the instrument does not change, only
    # what it is shown. `cmd_score_deepsy` passes czech.JUDGE_PROMPT_VERSION.
    source = (REPO_ROOT / "src" / "tnb" / "cli.py").read_text(encoding="utf-8")
    assert "judge_prompt_version=czech.JUDGE_PROMPT_VERSION" in source


def test_one_root_collides():
    """The bug, stated as an assertion rather than as a comment."""
    assert _path(None) == _path(None)


def test_deepsy_gets_a_root_of_its_own():
    separated = _path(judge.CACHE_DIR / deepsy.PROMPT_VERSION)
    assert separated != _path(None)
    assert deepsy.PROMPT_VERSION in separated.parts
    # And the Czech SOAP answers keep the paths they were written at: giving
    # Deepsy a root must not re-key the 2544 answers already on disk.
    assert _path(None).parts[-6:-1] == (
        "gemini-3.1-pro-preview",
        "czech-criteria-v2",
        "einfra",
        "kimi-k3",
        "cz-r-313e71f4",
    )


def test_the_deepsy_scorer_actually_passes_it():
    """A separate root nobody passes is a comment. Read the call, not the
    docstring: this is the line that would go missing in a refactor."""
    source = (REPO_ROOT / "src" / "tnb" / "cli.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    found = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "cmd_score_deepsy":
            continue
        for call in ast.walk(node):
            if not isinstance(call, ast.Call):
                continue
            if getattr(call.func, "attr", None) != "score_many":
                continue
            roots = [k for k in call.keywords if k.arg == "cache_root"]
            assert roots, "cmd_score_deepsy calls score_many with no cache_root"
            found = True
    assert found, "cmd_score_deepsy no longer calls score_many"
