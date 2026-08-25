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
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env", override=False)
