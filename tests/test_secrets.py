"""Nothing that identifies a private account may enter a tracked file.

This repository is public and its results page is served from it. The cloud
project, the service-account address and the API tokens live in ``.env`` and
``secrets/``, both ignored — but "ignored" is a property of one checkout, and a
value pasted into a docstring or a fixture is committed forever.

So it is a test rather than a promise. The forbidden values are read from the
environment, never written here: a test that contained the secret in order to
search for it would be the leak.

Two limits, stated rather than implied. This runs *after* ``git commit``, so it
is a backstop and not a gate — a secret it catches is already in the local
object database. And it reads the current worktree, so a value committed and
later deleted stays in history where this cannot see it.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tnb.config import REPO_ROOT, load_policy

#: Values that must never appear in a tracked file, beyond the provider tokens
#: that :func:`_sensitive_env` discovers from ``models.yaml``. The project id is
#: the one Jan asked about by name; the rest are credentials for services the
#: benchmark talks to that are not generation providers.
EXTRA_SENSITIVE_ENV = (
    "VERTEX_PROJECT",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
)

#: Shapes that are credentials whoever issued them. Caught even when the value
#: is not in this machine's environment, so a key pasted from elsewhere is found
#: too. `sk-proj-` needs no pattern of its own: `-` is inside the class below,
#: so the general `sk-` shape already covers it.
#:
#: The `sk-` pattern needed a second form. A provider does not always quote the
#: key back whole -- OpenAI's 401 body reads `sk-proj-Ab3d************xyz9`, and
#: `*` is outside the character class, so the match died after twelve
#: characters and the fragment sailed through. A redacted key is still a key:
#: it names the account, and the visible head and tail narrow it considerably.
KEY_SHAPES = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    # The redacted form: a `sk-` head, a run of mask characters, then a tail.
    re.compile(r"\bsk-[A-Za-z0-9_-]{2,}(?:[*.]{3,}|…+)[A-Za-z0-9_-]{2,}"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{30,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b\d{10,}-compute@developer\.gserviceaccount\.com"),
    re.compile(r"\"private_key_id\"\s*:"),
)

#: Too short or too common to search for without matching ordinary prose.
MIN_SECRET_LENGTH = 6


def _sensitive_env() -> tuple[str, ...]:
    """Every variable whose value is a secret, provider tokens included.

    ``models.yaml`` advertises adding a provider as a config change rather than
    a code change, so the token names cannot be a hand-kept list here: a new
    provider's key would be outside the scan the moment someone followed those
    instructions.
    """
    from_providers = {provider.token_env for provider in load_policy().providers}
    return tuple(sorted(from_providers | set(EXTRA_SENSITIVE_ENV)))


@pytest.fixture(scope="session")
def tracked_files() -> list[Path]:
    """Every file git would publish. Ignored files are not this test's business."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [REPO_ROOT / name for name in result.stdout.split("\0") if name]


def _readable_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None  # a binary fixture cannot carry a pasted token


def _secret_values() -> dict[str, str]:
    return {
        name: value
        for name in _sensitive_env()
        if (value := os.environ.get(name, "").strip()) and len(value) >= MIN_SECRET_LENGTH
    }


def find_secret_values(files: list[Path], secrets: dict[str, str]) -> list[str]:
    """Which of ``files`` contain any of ``secrets``, named by variable.

    A plain function rather than a test body, so the self-check below can run it
    against a planted file instead of monkeypatching a module by name — which is
    how the first version of this file quietly patched a second copy of itself
    and proved nothing.
    """
    offences = []
    for path in files:
        text = _readable_text(path)
        if text is None:
            continue
        for name, value in secrets.items():
            if value in text:
                offences.append(f"{path} contains ${name}")
    return offences


def find_key_shapes_in_text(text: str) -> list[str]:
    """Which credential shapes a string matches. The same net the file scan
    uses, exposed so a test can prove the net catches what it claims to."""
    return [p.pattern for p in KEY_SHAPES if p.search(text)]


def find_key_shapes(files: list[Path]) -> list[str]:
    """Which of ``files`` contain something shaped like a credential."""
    here = Path(__file__).resolve()
    offences = []
    for path in files:
        if path.resolve() == here:
            continue  # the patterns themselves live here
        text = _readable_text(path)
        if text is None:
            continue
        for pattern in KEY_SHAPES:
            if pattern.search(text):
                offences.append(f"{path} matches /{pattern.pattern}/")
    return offences


def test_no_configured_secret_appears_in_a_tracked_file(tracked_files):
    """The direct check: is any value from .env sitting in something committed?"""
    secrets = _secret_values()
    if not secrets:
        pytest.skip("nothing sensitive configured in this environment")

    assert not find_secret_values(tracked_files, secrets)


def test_the_scan_reads_the_env_file_when_there_is_one():
    """The scan above is worthless if the values never reach the environment.

    ``.env`` is loaded by ``tests/conftest.py`` precisely so this works; before
    that it skipped on Jan's machine and in CI alike, which is every machine.
    """
    if not (REPO_ROOT / ".env").exists():
        pytest.skip("no .env in this checkout")

    assert _secret_values(), (
        ".env exists but no sensitive value reached os.environ, so the leak scan "
        "would have skipped on the one machine that has the secrets"
    )


def test_no_credential_shaped_string_appears_in_a_tracked_file(tracked_files):
    """The wider net: a key pasted from another machine is still a key.

    This one needs no environment at all, so it protects the repository even on
    a checkout that has never been configured.
    """
    assert not find_key_shapes(tracked_files)


def test_the_secret_files_are_not_tracked(tracked_files):
    """`.env` and `secrets/` must be ignored, not merely absent from the index."""
    tracked = {path.relative_to(REPO_ROOT).as_posix() for path in tracked_files}

    assert ".env" not in tracked
    assert not any(name.startswith("secrets/") for name in tracked)
    assert ".env.example" in tracked, "the example is tracked on purpose and holds no values"


def test_the_check_would_catch_a_leak(tmp_path):
    """A test that never fails proves nothing. Plant one and see it caught."""
    planted = tmp_path / "leaked.md"
    planted.write_text("the project is a-private-project-name", encoding="utf-8")

    found = find_secret_values([planted], {"VERTEX_PROJECT": "a-private-project-name"})

    assert found and "VERTEX_PROJECT" in found[0]


def test_the_shape_check_would_catch_a_pasted_key(tmp_path):
    """The same proof for the pattern net, which runs even with no .env."""
    planted = tmp_path / "pasted.py"
    planted.write_text('KEY = "sk-' + "x" * 40 + '"', encoding="utf-8")

    assert find_key_shapes([planted])


def test_a_provider_token_added_in_models_yaml_is_scanned():
    """The token list follows the config, so a new provider is covered for free."""
    assert "EINFRA_API_TOKEN" in _sensitive_env()
    assert set(EXTRA_SENSITIVE_ENV) <= set(_sensitive_env())


def test_the_test_module_is_importable_under_its_package_name():
    """Guards the trap this file fell into: two copies of one test module.

    ``conftest.py`` puts the repository root on the path. If that ever stops
    being true, a string-target monkeypatch anywhere in the suite starts
    patching a second module object and passing for the wrong reason.
    """
    import tests.test_secrets as by_package

    assert by_package is sys.modules[__name__]


def test_a_redacted_key_is_still_caught():
    """A provider does not always quote the key back whole.

    OpenAI's 401 body reads `sk-proj-Ab3d************xyz9`. `*` is outside the
    general pattern's character class, so the match died after twelve characters
    and the fragment sailed through the backstop. A redacted key still names the
    account, and its visible head and tail narrow it considerably.
    """
    for body in (
        "Incorrect API key provided: sk-proj-Ab3d************xyz9",
        "Incorrect API key provided: sk-proj-Ab3d...xyz9",
        "key sk-Ab3d…xyz9 was rejected",
    ):
        assert find_key_shapes_in_text(body), body


def test_ordinary_prose_is_not_mistaken_for_a_redacted_key():
    """The pattern needs a `sk-` head, so a sentence with dots is safe."""
    for body in (
        "the request failed... try again",
        "asked for sk-ip but got nothing",
        "HTTP500: backend error",
    ):
        assert not find_key_shapes_in_text(body), body
