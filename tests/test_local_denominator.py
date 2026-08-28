"""A model's denominator is the corpus, not the notes it managed to write.

Offline. The rows here are built in this file.

The three local scoring commands passed one dict as both `n_generated` and
`n_attempted`, so a model that wrote five notes of ten was recorded as five of
five -- full coverage -- and the model that wrote none produced no candidate,
therefore no row, therefore no trace at all. On the Deepsy track, where e-INFRA
returned HTTP 500 to a quarter of the calls, that would have printed a table of
models at 100% coverage with one model silently missing.
"""

from __future__ import annotations

import ast

from tnb.config import REPO_ROOT
from tnb.scoring import czech_run

LOCAL_COMMANDS = ("cmd_score_czech", "cmd_score_czech_pdsqi", "cmd_score_deepsy")


def test_to_rows_accepts_a_corpus_size_rather_than_a_per_model_count():
    """The contract the fix depends on: `n_attempted` may be one int for every
    model, because the corpus is the same size for all of them. Read from the
    source, since building a `SystemAggregate` by hand would pin the runner's
    internals rather than this contract."""
    import inspect

    source = inspect.getsource(czech_run.to_rows)
    assert "isinstance(n_attempted, dict)" in source, "the int branch is gone"
    assert "attempted = n_attempted or generated" in source


def test_no_local_command_passes_the_same_count_twice():
    """The defect, stated so it cannot come back. `n_attempted=coverage` beside
    `n_generated=coverage` is the bug: two names for one number."""
    tree = ast.parse((REPO_ROOT / "src" / "tnb" / "cli.py").read_text(encoding="utf-8"))
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name not in LOCAL_COMMANDS:
            continue
        for call in ast.walk(node):
            if not isinstance(call, ast.Call):
                continue
            named = {k.arg: k.value for k in call.keywords if k.arg}
            if "n_generated" not in named or "n_attempted" not in named:
                continue
            generated, attempted = named["n_generated"], named["n_attempted"]
            if (
                isinstance(generated, ast.Name)
                and isinstance(attempted, ast.Name)
                and generated.id == attempted.id
            ):
                offenders.append(f"{node.name}: n_attempted is the same name as n_generated")
    assert not offenders, offenders


def test_the_deepsy_scorer_names_the_models_that_would_vanish():
    """A model with no complete note gets no row. It cannot be given one -- there
    is no score to put in it -- so it must be said out loud where the person
    starting the run will read it. Silence there reads as "not run"."""
    source = (REPO_ROOT / "src" / "tnb" / "cli.py").read_text(encoding="utf-8")
    assert "_attempted_systems" in source
    assert "NO COMPLETE NOTE" in source

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "cmd_score_deepsy":
            body = ast.dump(node)
            assert "_attempted_systems" in body, "the warning is not in the Deepsy command"
            return
    raise AssertionError("cmd_score_deepsy not found")
