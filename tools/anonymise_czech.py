"""De-identify the Czech transcripts, from a table that is not in this file.

The Czech track reads ten real psychotherapy sessions with one client. They are
transcripts of speech, so names, districts, countries and the recording's own
identifier are spoken aloud in the middle of ordinary sentences. This script
removes them.

**The replacement table lives in `data/czech/anonymisation.json`, not here.** It
names real people and places, and this file is committed. What is here is only
the machinery, so the two can be read separately: the table is auditable by
anyone with the corpus, and the code is auditable by anyone without it.

Three decisions the table records and this docstring should not repeat, but
which govern what the script does:

*Replacements are substitutions, not redactions.* A placeholder like ``[NAME]``
would be safer to write and would ruin the measurement: this corpus feeds a
benchmark of Czech *language quality*, and a bracketed token is not Czech. Every
replacement is a real Czech word in the case the sentence needs, chosen by hand
after reading the sentence.

*The recording identifier is spoken in the first turn of every session.* Where
stripping it leaves a turn with nothing else in it, the turn goes. Five of the
ten sessions open that way, so five transcripts begin with the client.

*The output is named neutrally.* The originals are named after clinical record
numbers. `datasets/czech.py` derives a session id from the file's bytes rather
than its name, so the name matters little -- but a file called `163783.txt` is
one careless `cp` away from somewhere it should not be.

Run it as ``uv run python tools/anonymise_czech.py``. It refuses to overwrite an
existing anonymised corpus: re-running after the corpus has been generated from
would silently change every session id and orphan the cache.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "data" / "czech"
TARGET = SOURCE / "anonymised"
TABLE = SOURCE / "anonymisation.json"
MAPPING = TARGET / "mapping.json"

#: Turn prefixes, as `datasets/czech.py` reads them.
PREFIXES = ("T: ", "K: ")


def _load_table() -> dict:
    if not TABLE.exists():
        raise SystemExit(f"No replacement table at {TABLE}. It is not in this repository.")
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    return {
        "preamble": tuple(table["preamble"]["patterns"]),
        # Longest first, so a two-word name is not half-replaced by a one-word rule.
        "phrases": tuple(
            sorted(
                ((k, v) for k, v in table["phrases"].items() if not k.startswith("_")),
                key=lambda pair: -len(pair[0]),
            )
        ),
        "words": tuple((k, v) for k, v in table["words"].items() if not k.startswith("_")),
    }


def _strip_preamble(line: str, patterns: tuple[str, ...]) -> str | None:
    """The first turn without the spoken identifier, or None if nothing is left."""
    for prefix in PREFIXES:
        if not line.startswith(prefix):
            continue
        body = line[len(prefix) :]
        for pattern in patterns:
            if pattern in body:
                body = body.replace(pattern, "", 1).strip()
                return f"{prefix}{body}" if body else None
        return line
    return line


def _substitute(text: str, table: dict) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for phrase, replacement in table["phrases"]:
        text, n = re.subn(re.escape(phrase), replacement, text)
        if n:
            counts[phrase] = n
    for word, replacement in table["words"]:
        # Whole words only, and case-sensitively: the table's keys are the exact
        # forms the transcriber wrote, and a case-insensitive rule would catch
        # ordinary nouns that happen to share a stem.
        text, n = re.subn(rf"\b{re.escape(word)}\b", replacement, text)
        if n:
            counts[word] = n
    return text, counts


def anonymise(source: Path, target: Path, table: dict) -> tuple[str, dict[str, int], int]:
    lines = source.read_text(encoding="utf-8").splitlines()
    dropped = 0

    for index, line in enumerate(lines):
        if not line.strip():
            continue
        stripped = _strip_preamble(line, table["preamble"])
        if stripped is None:
            lines[index] = ""
            dropped = 1
        else:
            lines[index] = stripped
        break

    text = "\n".join(lines).strip() + "\n"
    text, counts = _substitute(text, table)
    # Collapse the blank line a dropped opening turn leaves behind.
    text = re.sub(r"\n{3,}", "\n\n", text).lstrip("\n")
    target.write_text(text, encoding="utf-8")
    return text, counts, dropped


def verify(texts: dict[str, str], table: dict) -> list[str]:
    """Whether anything the table was meant to remove is still there.

    Reports the file and the count. Never the surrounding text: this runs in a
    terminal and its output is the one place a de-identification script can
    undo itself.
    """
    problems: list[str] = []
    removed = [key for key, _ in table["phrases"]] + [key for key, _ in table["words"]]
    for name, text in texts.items():
        for key in removed:
            found = len(re.findall(rf"\b{re.escape(key)}\b", text))
            if found:
                problems.append(f"{name}: {found} occurrence(s) of a replaced token survived")
        for pattern in table["preamble"]:
            if pattern in text:
                problems.append(f"{name}: the recording identifier survived")
        if re.search(r"\d{4,}", text):
            problems.append(f"{name}: a run of four or more digits")
        if "@" in text:
            problems.append(f"{name}: an at-sign")
    return problems


def main() -> int:
    table = _load_table()
    sources = sorted(p for p in SOURCE.glob("*.txt") if p.is_file())
    if not sources:
        raise SystemExit(f"No transcripts at {SOURCE}.")

    TARGET.mkdir(parents=True, exist_ok=True)
    existing = sorted(TARGET.glob("*.txt"))
    if existing:
        print(f"{TARGET} already holds {len(existing)} transcript(s).")
        print("Refusing to rewrite them: every session id is a digest of these bytes,")
        print("so regenerating would orphan every note already generated. Delete them")
        print("by hand if that is really what you want.")
        return 1

    mapping: dict[str, str] = {}
    totals: dict[str, int] = {}
    texts: dict[str, str] = {}
    dropped_turns = 0

    for number, source in enumerate(sources, start=1):
        name = f"session-{number:02d}.txt"
        text, counts, dropped = anonymise(source, TARGET / name, table)
        mapping[name] = source.name
        texts[name] = text
        dropped_turns += dropped
        for key, n in counts.items():
            totals[key] = totals.get(key, 0) + n

    MAPPING.write_text(
        json.dumps(
            {"anonymised_to_original": mapping}, ensure_ascii=False, indent=2, sort_keys=True
        ),
        encoding="utf-8",
    )

    print(f"Wrote {len(mapping)} transcripts to {TARGET.relative_to(REPO)}/")
    print(f"  {sum(totals.values())} substitution(s) over {len(totals)} distinct token(s)")
    print(f"  {dropped_turns} opening turn(s) dropped, having held nothing but the identifier")

    problems = verify(texts, table)
    if problems:
        print("\nVERIFICATION FAILED:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print("  verification clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
