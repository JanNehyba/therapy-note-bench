"""Prepare a reviewable sibling patch; never edit the sibling or invent a release commit."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import tomllib
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--revision", help="full commit hash containing core version 0.3.0")
    mode.add_argument("--development", action="store_true", help="local preview, not a release pin")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if not output.is_relative_to(repo / "local"):
        parser.error("Integration previews must remain under this checkout's local directory")
    if args.revision:
        if not re.fullmatch(r"[0-9a-f]{40}", args.revision):
            parser.error("Use a complete immutable commit hash")
        result = subprocess.run(
            ["git", "show", args.revision + ":packages/therapy-note-eval-core/pyproject.toml"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode or tomllib.loads(result.stdout)["project"]["version"] != "0.3.0":
            parser.error("That commit does not contain the reviewed core version")
        source = (
            '{ git = "https://github.com/JanNehyba/therapy-note-bench", '
            f'rev = "{args.revision}", subdirectory = "packages/therapy-note-eval-core" }}'
        )
    else:
        source = (
            "{ path = "
            + json.dumps(str(repo / "packages" / "therapy-note-eval-core"))
            + ", editable = true }"
        )
    target = args.target.resolve()
    originals = {
        name: (target / name).read_text(encoding="utf-8")
        for name in ("pyproject.toml", "src/tnb/cli.py", "README.md")
    }
    if "therapy-note-eval-core" in originals["pyproject.toml"]:
        parser.error("Sibling already contains an integration; review its changes explicitly")
    pyproject = originals["pyproject.toml"].replace(
        "[project.optional-dependencies]\n",
        '[project.optional-dependencies]\ngen2 = ["therapy-note-eval-core==0.3.0"]\n',
        1,
    )
    if "[tool.uv.sources]" in pyproject:
        parser.error("Merge the existing UV sources table manually")
    pyproject += "\n[tool.uv.sources]\ntherapy-note-eval-core = " + source + "\n"
    tomllib.loads(pyproject)
    declaration = "def main(argv: list[str] | None = None) -> int:\n"
    host_cli = (repo / "src" / "tnb" / "cli.py").read_text(encoding="utf-8")
    dispatch = host_cli.split(declaration, 1)[1].split("    load_dotenv", 1)[0]
    if (
        originals["src/tnb/cli.py"].count(declaration) != 1
        or "gen2_main" in originals["src/tnb/cli.py"]
    ):
        parser.error("Sibling CLI changed; inspect its entrypoint before integrating")
    replacements = {
        "pyproject.toml": pyproject,
        "src/tnb/cli.py": originals["src/tnb/cli.py"].replace(
            declaration, declaration + dispatch, 1
        ),
        "README.md": originals["README.md"] + "\n## Experimental Gen-2\n\n"
        "The optional shared evaluator uses the separate `therapy_note_eval` namespace. "
        "After installing the `gen2` extra, run `tnb gen2 --help`. Real-session "
        "notes, QA and evidence remain local or on approved e-INFRA. "
        "The new instrument requires a reviewed research registry; prototype criteria "
        "are reserved for synthetic demonstrations. "
        "Gen-1 results retain their original protocol.\n",
    }
    patches = []
    for name, replacement in replacements.items():
        path = output / "files" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(replacement, encoding="utf-8")
        patches.extend(
            difflib.unified_diff(
                originals[name].splitlines(True),
                replacement.splitlines(True),
                fromfile="a/" + name,
                tofile="b/" + name,
            )
        )
    (output / "integration.patch").write_text("".join(patches), encoding="utf-8")
    metadata = {
        "target": str(target),
        "core_revision": args.revision,
        "mode": "release_candidate" if args.revision else "development_preview",
        "original_sha256": {
            k: hashlib.sha256((target / k).read_bytes()).hexdigest() for k in originals
        },
        "lockfile_status": "Regenerate uv.lock in a staging checkout "
        "and test before applying; not complete.",
        "remote_availability": "Not verified; local commit existence "
        "does not imply it has been published.",
        "applied": False,
    }
    (output / "status.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps({"patch": str(output / "integration.patch"), **metadata}, indent=2))


if __name__ == "__main__":
    main()
