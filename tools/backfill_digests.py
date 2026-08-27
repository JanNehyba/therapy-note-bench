"""Record, for every cached judge answer, the digest of the question it answered.

An answer is filed under what it was *about* — judge, prompt version, provider,
system, session, unit. That names the slot and not the text: a re-generated note
or a changed definition of what counts as a sentence puts different text in the
same slot, and `judge.load_cached` hands back the old answer with nothing to
notice. `write_cached` records `prompt_sha256` so the check has something to
compare against, and answers written before that carry none — `load_cached`
treats them as unknown rather than wrong, because rejecting them would re-ask
169 036 questions.

This closes it without re-asking anything. It rebuilds each note's questions
exactly as the scorer does, and writes the digest of the prompt that matches
each cached unit.

**Why that is sound, and it is not obvious.** Recording today's prompt as the
question a cached answer replied to is only true if the note has not changed
since. Measured on 2026-08-27 across every cached answer with a note on disk:
124 420 answers whose note is older than the answer, and **zero** whose note is
newer. The remaining 49 784 belong to the therapist and the two 2025 reference
systems, whose notes come from the checksummed corpus rather than from
`generations/` and cannot drift without the checksum saying so.

**A unit with no matching question is not given a digest.** It is counted and
left alone: an answer whose slot the current code would never ask for is exactly
the mismatch this guard exists to catch, and inventing a digest for it would
paper over the one case that matters.

Run it once per judge:

    python tools/backfill_digests.py --judge-model gemini-3.1-pro-preview
    python tools/backfill_digests.py --dry-run          # count, write nothing
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from tnb import judge  # noqa: E402
from tnb.scoring import run as scoring  # noqa: E402
from tnb.scoring import tneval  # noqa: E402


def prompts_for(candidate) -> dict[str, str]:
    """{unit: prompt} for one note, built the way the scorer builds them."""
    return {
        task.unit: task.prompt
        for task in tneval.build_tasks(candidate.note, candidate.conversation)
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge-model", default=judge.DEFAULT_MODEL)
    parser.add_argument("--dry-run", action="store_true", help="count, write nothing")
    args = parser.parse_args()

    sessions = scoring.load_sessions(None)
    candidates = list(scoring.from_generations(sessions)) + list(scoring.from_reference(sessions))
    print(f"{len(candidates)} note(s) to rebuild questions for.")

    counts: Counter[str] = Counter()
    for index, candidate in enumerate(candidates, start=1):
        prompts = prompts_for(candidate)
        for unit, prompt in prompts.items():
            path = judge.cache_path(
                args.judge_model,
                tneval.JUDGE_PROMPT_VERSION,
                candidate.provider,
                candidate.system_id,
                candidate.session_id,
                unit,
            )
            if not path.exists():
                counts["never asked"] += 1
                continue
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                counts["unreadable"] += 1
                continue
            if record.get("prompt_sha256"):
                counts["already recorded"] += 1
                continue
            counts["digest written"] += 1
            if not args.dry_run:
                record["prompt_sha256"] = judge.prompt_digest(prompt)
                path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

        # Answers on disk whose unit the current code would not ask for. The
        # mismatch this guard exists to catch, so it is named and left alone.
        directory = judge.cache_path(
            args.judge_model,
            tneval.JUDGE_PROMPT_VERSION,
            candidate.provider,
            candidate.system_id,
            candidate.session_id,
            "x",
        ).parent
        if directory.exists():
            for path in directory.glob("*.json"):
                if path.stem not in prompts:
                    counts["orphaned unit (left alone)"] += 1

        if index % 200 == 0:
            print(f"  {index}/{len(candidates)} {dict(counts)}", flush=True)

    print()
    for name, count in counts.most_common():
        print(f"  {name:30s} {count}")
    if args.dry_run:
        print("\nDry run: nothing was written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
