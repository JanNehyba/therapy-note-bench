"""Print ``docs/brief.html`` to ``docs/therapy-note-bench.pdf``.

Chrome in headless mode, because it is the one renderer on this machine that
understands the figures. They are SVG with their own ``<style>`` block and a
``prefers-color-scheme`` query; a converter that rasterises or flattens them
loses the type, and one that ignores the stylesheet loses the colour.

WeasyPrint is installed and cannot start -- it needs GTK libraries that are not
here -- and pandoc would go through LaTeX, which means re-authoring the layout
in a second language. Neither is worth it for a document whose source is
already HTML and CSS.

This is the only step in the repository that needs something outside Python, so
it says exactly what it could not find rather than failing with a stack trace,
and `tools/brief.py` writes a page that is readable on its own if you never run
this at all.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
SOURCE = DOCS / "brief.html"
TARGET = DOCS / "therapy-note-bench.pdf"

#: Where Chrome tends to be. `shutil.which` first; these are the fallback,
#: because on Windows it is usually not on PATH.
CANDIDATES = (
    "chrome",
    "chromium",
    "google-chrome",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


def find_browser() -> str | None:
    for candidate in CANDIDATES:
        found = shutil.which(candidate) or (candidate if Path(candidate).exists() else None)
        if found:
            return found
    return None


def main(argv: list[str] | None = None) -> int:
    # `--source` and `--target` exist because the Czech track needs the same
    # step for a document that is not published: it prints `local/` to `local/`,
    # where nothing is committed. Defaults unchanged, so `make pdf` is untouched.
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=SOURCE, help="the HTML to print")
    parser.add_argument("--target", type=Path, default=TARGET, help="where the PDF goes")
    args = parser.parse_args(argv)
    # Resolved, because `as_uri()` refuses a relative path and the obvious way
    # to call this from a script is `--source local/x.html`.
    source, target = args.source.resolve(), args.target.resolve()

    if not source.exists():
        print(f"{source} is not there. Run `make brief` first.", file=sys.stderr)
        return 1

    browser = find_browser()
    if browser is None:
        print(
            "No Chrome or Edge found, so there is no PDF this time.\n"
            f"  {SOURCE.relative_to(REPO)} is the same document and opens in any browser;\n"
            "  its own print dialogue produces the same pages.",
            file=sys.stderr,
        )
        return 1

    # What the file was before, so that "Chrome wrote it" can be checked rather
    # than assumed. Existence is not the check: a PDF open in a viewer is locked
    # on Windows, Chrome cannot replace it, and a tool that only asks whether
    # the path exists then reports the *previous* document as this run's output.
    # That happened, to a document that had already been handed over.
    before = target.stat().st_mtime_ns if target.exists() else None

    # `--headless=new` rather than the old mode: the old one silently ignores
    # `print-color-adjust`, and every figure comes out white.
    finished = subprocess.run(
        [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--virtual-time-budget=4000",
            f"--print-to-pdf={target}",
            source.as_uri(),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        # Chrome writes a profile somewhere whatever you ask it to do.
        env={**os.environ, "HOME": os.environ.get("TEMP", str(REPO))},
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        print(finished.stdout + finished.stderr, file=sys.stderr)
        print("Chrome ran and wrote no file.", file=sys.stderr)
        return 1

    if before is not None and target.stat().st_mtime_ns == before:
        print(finished.stdout + finished.stderr, file=sys.stderr)
        print(
            f"Chrome ran and did not replace {target.name}; what is there is the "
            "previous document.\n"
            "  The usual cause is that the PDF is open in a viewer, which locks it "
            "on Windows.\n"
            "  Close it and run this again.",
            file=sys.stderr,
        )
        return 1

    size = target.stat().st_size
    print(f"wrote {target}  {size:>9,} bytes  (via {Path(browser).name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
