"""Two tracks that share a rubric may not share a cache path.

Offline. Every path here is computed, nothing is written.

`judge.cache_path` is keyed on judge, rubric, provider, system, session and
unit. The Deepsy track shares all six with the Czech SOAP track -- the same ten
sessions, overlapping models, the same six criteria, the same
`czech-criteria-v2`. Only the note differs, and the note is not in the key.

Under one root each run would overwrite the other's answers and neither track
would ever keep a cache: `load_cached` rejects a record whose prompt digest does
not match, so the answer read is never the wrong one -- but the answer WRITTEN
lands on top of a right one. The digest check makes a collision unreadable; it
does not make it harmless.
"""

from __future__ import annotations

import ast

from tnb import judge, results
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


def test_the_variance_tool_reads_the_deepsy_root_with_the_deepsy_renderer():
    """The other reader of that cache, and it used to read neither.

    `tools/czech_variance.py` asks the same six-field question `cmd_score_deepsy`
    answers, so it needs the same root and the same renderer. It had both
    hardcoded to the SOAP track, and the two must move together: `load_cached`
    checks the digest of the prompt the renderer produced, so the right root with
    the wrong renderer finds files it then rejects.
    """
    import sys

    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import czech_variance

    for track in (results.TRACK_DEEPSY_REAL, results.TRACK_DEEPSY_TRANSLATED):
        spec = czech_variance.CRITERIA_TRACKS[track]
        assert spec.cache_root == judge.CACHE_DIR / deepsy.PROMPT_VERSION
        assert spec.render is deepsy.render_note
        # And the corpus is carried rather than derived from the track name.
        # `_cells` used to pick its loader with `task_name == "czech-real"`, so
        # `"deepsy-real"` compared false and would have loaded the TRANSLATED
        # sessions -- every note paired with the wrong transcript.
        assert spec.task_name == track

    for track in (results.TRACK_CZECH_REAL, results.TRACK_CZECH_TRANSLATED):
        spec = czech_variance.CRITERIA_TRACKS[track]
        assert spec.cache_root is None
        assert spec.render is czech_task.render_note


def test_the_soap_renderer_over_a_deepsy_note_asks_the_judge_nothing():
    """Why the wrong renderer failed silently instead of loudly.

    This is the regression that kept the Deepsy panels out of the document with
    nothing printed. `czech_task.render_note` reads `subjective`/`objective`/
    `assessment`/`plan`; a Deepsy note has none of those keys, so it renders four
    empty headings, `czech.has_content` strips them, and `build_tasks` returns
    an empty list. Zero tasks means zero cells, and the caller's `if not cells`
    skipped the track without a word -- indistinguishable from a judge that was
    never asked.
    """
    note = {key: "Text." for keys in deepsy.KEYS.values() for key in keys}

    assert czech.build_tasks(deepsy.render_note(note)), "the Deepsy renderer asks questions"
    assert czech.build_tasks(czech_task.render_note(note)) == []
