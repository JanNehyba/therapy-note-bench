"""Test-suite setup.

Two jobs, both about making tests see the same world the program does.

``.env`` is loaded because the secrets scan checks that no configured value has
reached a tracked file, and it can only do that if it knows the values. Nothing
else in the package loads ``.env`` outside :func:`tnb.cli.main`, so without this
the scan skipped on the one machine where the secrets actually exist.

``tests`` is put on the import path so a test module can refer to itself by a
stable name. Without it pytest imports this directory's files as top-level
modules while ``monkeypatch.setattr("tests.x.y", ...)`` silently builds a second
copy of the module and patches that one instead.

Two more jobs, both about tests leaving nothing behind. The Gen-2 workspace
fixtures create their private directory under ``local/`` -- the store refuses
any other root -- and remove it when the test ends; an audit on 2026-09-15
found over two and a half thousand of them left by earlier runs. And the
corpus profile is staged: ``corpus.load_or_build`` writes the published
``docs/corpus-profile.json`` when the corpora are present, so every test sees a
copy of it under its own temporary directory and the published file stays as
it was committed.
"""

from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env", override=False)


@pytest.fixture
def workspace():
    """A private Gen-2 workspace under local/, removed when the test ends.

    Python 3.13's Windows mode=700 changes the ACL in this runner, so the
    directory is created with mode 777 and inherits the workspace ACL instead.
    """
    path = REPO_ROOT / "local" / ("gen2-test-" + uuid.uuid4().hex)
    path.mkdir(parents=True, mode=0o777)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def store(workspace):
    from therapy_note_eval.storage import Store

    return Store(workspace)


@pytest.fixture(autouse=True)
def _staged_corpus_profile(monkeypatch, tmp_path_factory):
    from tnb import corpus

    # Its own directory, not the test's tmp_path: a test that globs every JSON
    # file under its tmp_path must not find the profile among its own records.
    staged = tmp_path_factory.mktemp("corpus-profile") / "corpus-profile.json"
    if corpus.PROFILE_PATH.exists():
        staged.write_bytes(corpus.PROFILE_PATH.read_bytes())
    monkeypatch.setattr(corpus, "PROFILE_PATH", staged)
