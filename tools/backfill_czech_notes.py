"""Parse the note out of Czech generation records written before there was a parser.

`generation._record` parses a SOAP answer into its four sections at write time,
so a note that never parsed is visible in the cache rather than surfacing as a
zero at scoring. The Czech tasks were generating for half an hour before that
branch knew about them, so their records carry the model's answer and no `note`.

The answer is in the record, so nothing has to be re-asked. This reads each one,
parses it with the Czech reader, and writes the result back -- including the
`ok: false` and the reason for an answer that does not parse, which is what
makes a failed note countable instead of invisible.

Idempotent: a record that already has a `note` key is left alone.
"""

from __future__ import annotations

import json
import sys

from tnb.generation import CACHE_DIR
from tnb.tasks import czech

TASKS = (czech.NAME_REAL, czech.NAME_TRANSLATED)


def main() -> int:
    touched = failed = already = 0
    for provider in sorted(p for p in CACHE_DIR.iterdir() if p.is_dir()):
        for name in TASKS:
            root = provider / name / czech.PROMPT_VERSION
            if not root.exists():
                continue
            for path in sorted(root.rglob("note.json")):
                record = json.loads(path.read_text(encoding="utf-8"))
                if "note" in record:
                    already += 1
                    continue
                record["note"] = czech.parse_note(record.get("text") or "")
                if record["note"] is None:
                    record["ok"] = False
                    record["error"] = record.get("error") or (
                        "answer did not contain a SOAP dictionary"
                    )
                    failed += 1
                path.write_text(
                    json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
                touched += 1

    print(f"{touched} record(s) parsed, {already} already had a note.")
    print(f"  {failed} answer(s) did not parse and are now marked as failures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
