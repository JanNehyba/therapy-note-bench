"""The PDSQI tracks share a rubric, so they may not share a cache path.

Offline. Every path here is computed; nothing is written and nothing is read
from the answer cache.

This is `test_judge_cache_collision.py` for the other instrument, and it exists
because the same collision happened a second time on the tracks that were added
later. `judge.cache_path` is keyed on judge, prompt version, provider, system,
session and unit. The Deepsy PDSQI track shares all six with the Czech SOAP
PDSQI track -- the same models, the same ten sessions, the same eight
attributes, the same `pdsqi9-note-cs-v1`. Only the note differs, and the note is
not in the key.

**The digest check makes a collision unreadable, not harmless, and here it was
worse than on the criteria side.** Since 2026-08-31 an answer lives under its
instrument's own directory, and `load_cached` falls back to the older
settings-free path only when the instrument path is EMPTY. So a Deepsy answer
written at the shared path does not sit beside the Czech answer it collides
with -- it hides it. One run left 2 684 intact Czech answers unreadable and
destroyed 280 more that had no older copy underneath.
"""

from __future__ import annotations

import ast

from tnb import judge, results
from tnb.config import REPO_ROOT
from tnb.scoring import czech_pdsqi, pdsqi
from tnb.tasks import czech as czech_task
from tnb.tasks import deepsy


def _path(root, unit="pdsqi.succinct"):
    return judge.cache_path(
        "gemini-3.1-pro-preview",
        czech_pdsqi.JUDGE_PROMPT_VERSION,
        "einfra",
        "kimi-k3",
        "cz-r-313e71f4",
        unit,
        fingerprint={"model": "gemini-3.1-pro-preview", "thinking_budget": 2048},
        root=root,
    )


def test_the_six_key_fields_really_are_shared():
    """The premise. Both tracks put the same instrument to the same models on
    the same sessions, so only the root can separate them."""
    assert deepsy.PROMPT_VERSION != czech_task.PROMPT_VERSION
    # One rubric, deliberately: the instrument does not change, only what it is
    # shown. Both tracks are scored under `czech_pdsqi.JUDGE_PROMPT_VERSION`.
    source = (REPO_ROOT / "src" / "tnb" / "cli.py").read_text(encoding="utf-8")
    assert "judge_prompt_version=czech_pdsqi.JUDGE_PROMPT_VERSION" in source


def test_one_root_collides():
    """The bug, as an assertion rather than a comment."""
    assert _path(None) == _path(None)


def test_deepsy_pdsqi_gets_a_root_of_its_own():
    separated = _path(judge.CACHE_DIR / deepsy.PROMPT_VERSION)
    assert separated != _path(None)
    assert deepsy.PROMPT_VERSION in separated.parts
    # And it stays distinct from where the Deepsy *criteria* answers live: same
    # root, different prompt version, so the two instruments do not collide
    # with each other once both are separated from the SOAP one.
    from tnb.scoring import czech as czech_criteria

    assert czech_pdsqi.JUDGE_PROMPT_VERSION != czech_criteria.JUDGE_PROMPT_VERSION


def test_a_shared_root_hides_rather_than_neighbours():
    """Why this collision cost answers where the criteria one only cost calls.

    `load_cached` reads the instrument path first and falls back to the
    pre-2026-08-31 path only when that file does not exist. So an answer written
    at the instrument path shadows an intact older answer underneath it, and the
    older one is never consulted again. This pins that ordering: the legacy path
    is the instrument path with one component removed, which is exactly what
    makes one capable of hiding the other.
    """
    instrument = _path(None)
    legacy = judge.legacy_path(instrument)
    assert legacy is not None
    assert legacy != instrument
    assert legacy.name == instrument.name
    assert len(legacy.parts) == len(instrument.parts) - 1


def test_the_czech_pdsqi_scorer_passes_a_root_that_depends_on_the_format():
    """A separate root nobody passes is a comment.

    The failure was not a missing argument -- `cache_root=_cache_root(args)` was
    there and looked right. It was a root that did not vary with `--format`, so
    both formats resolved to the same directory. Read the call.
    """
    source = (REPO_ROOT / "src" / "tnb" / "cli.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    checked = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "cmd_score_czech_pdsqi":
            continue
        for call in ast.walk(node):
            if not isinstance(call, ast.Call) or getattr(call.func, "attr", None) != "score_many":
                continue
            roots = [k for k in call.keywords if k.arg == "cache_root"]
            assert roots, "cmd_score_czech_pdsqi calls score_many with no cache_root"
            # The root must mention the format. A constant root is the bug.
            rendered = ast.dump(roots[0].value)
            assert "format" in rendered, "the PDSQI cache root does not depend on --format"
            assert "PROMPT_VERSION" in rendered
            checked = True
    assert checked, "cmd_score_czech_pdsqi no longer calls score_many"


def test_the_variance_tool_reads_each_pdsqi_corpus_with_its_own_root_and_renderer():
    """The other reader of that cache, and it knew about neither Deepsy track.

    `_pdsqi_cells` picked its loader with `task_name == czech_task.NAME_REAL`
    and took the translated corpus otherwise, and always rendered with the SOAP
    renderer. A Deepsy task name compares false against both, so it would have
    paired every Deepsy note with a translated AnnoMI transcript. The root and
    the renderer must travel together: `load_cached` checks the digest of the
    prompt the renderer produced, so the right root with the wrong renderer
    finds files and then rejects every one of them.
    """
    import sys

    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import czech_variance

    deepsy_root = judge.CACHE_DIR / deepsy.PROMPT_VERSION
    expected = {
        czech_task.NAME_REAL: (czech_task.render_note, None),
        czech_task.NAME_TRANSLATED: (czech_task.render_note, None),
        deepsy.NAME_REAL: (deepsy.render_note, deepsy_root),
        deepsy.NAME_TRANSLATED: (deepsy.render_note, deepsy_root),
    }
    assert set(czech_variance.PDSQI_CORPORA) == set(expected)
    for task_name, (render, root) in expected.items():
        _loader, got_render, got_root = czech_variance.PDSQI_CORPORA[task_name]
        assert got_render is render, task_name
        assert got_root == root, task_name


def test_every_pdsqi_track_is_banded_on_the_same_composite():
    """A SOAP-to-Deepsy difference read off two composites is a fact about the
    composites. The four PDSQI tracks must name the same attributes."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import czech_variance

    tracks = (
        results.TRACK_CZECH_REAL_PDSQI,
        results.TRACK_CZECH_TRANSLATED_PDSQI,
        results.TRACK_DEEPSY_REAL_PDSQI,
        results.TRACK_DEEPSY_TRANSLATED_PDSQI,
    )
    composites = {czech_variance.COMPOSITES[track] for track in tracks}
    assert len(composites) == 1, composites


def test_the_soap_renderer_over_a_deepsy_note_asks_the_pdsqi_judge_nothing():
    """The silent half of the same mistake, on this instrument.

    `czech_task.render_note` reads four SOAP keys a Deepsy note does not have,
    so it renders empty headings and the run reports `asked 0 cached 0` -- which
    reads exactly like a cache hit.
    """
    note = {key: "Text." for keys in deepsy.KEYS.values() for key in keys}

    assert pdsqi.build_tasks(deepsy.render_note(note), None)
    assert pdsqi.build_tasks(czech_task.render_note(note), None) == []
