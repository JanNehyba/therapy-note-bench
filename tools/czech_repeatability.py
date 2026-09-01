"""Ask the judge the same question twice, and measure how far the answer moves.

Every number this project publishes rests on an assumption nobody has tested:
that the judge, asked the same question about the same note at the same
settings, gives the same answer. The assumption is not obviously true -- both
judges are sampled models, and one of them is a reasoning model whose answer
depends on a thinking pass that is not pinned by a seed.

**The reason this exists is an accident.** 280 answers for `glm-5.3` were
destroyed by a cache collision and had to be asked again. Same judge, same
settings, same ten notes. Most columns came back within 0.20; `thorough` under
`gpt-5.6-terra` came back at 3.20 where it had been 4.30. That is one model on
one half, which is an observation and not a measurement -- so this makes the
measurement.

**Nothing existing is touched.** The repeat is written under a cache root of its
own, so the answers behind every published number stay exactly where they are.
That is not a precaution, it is the whole design: overwriting them would destroy
the very thing being compared against, which is how the accident happened in the
first place.

The sample is drawn by `sha256("<session>/<system>")`, the ordering
`tools/czech_rating_sheet.py` already uses -- one session per model, a different
one for each, fixed before any answer is seen and unreachable from any score.
One session per model rather than one model's ten notes, because the question is
about the instrument and not about a model, and because ten notes of one model
would confound repeatability with whatever is peculiar to that model's writing.

Prints ids, attribute names and numbers. Never a note, never a transcript.

    uv run python tools/czech_repeatability.py --dry-run
    uv run python tools/czech_repeatability.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from dotenv import load_dotenv  # noqa: E402

from tnb import judge, results  # noqa: E402
from tnb.scoring import czech_pdsqi, pdsqi_run  # noqa: E402
from tnb.tasks import czech as czech_task  # noqa: E402

DEFAULT_TARGET = REPO / "local" / "czech-repeatability.json"

#: Where the second asking lives. A root of its own, never the live one: the
#: comparison needs both answers, and `write_cached` would put the new one on
#: top of the old.
REPEAT_ROOT = judge.CACHE_DIR / "repeatability-1"

#: The two halves of the Czech PDSQI instrument. The real half is six attributes
#: and the translated half eight; the two that need a session are never asked of
#: the real one, and that is a question nobody put rather than an answer that
#: went missing.
HALVES = {
    "real": (results.TRACK_CZECH_REAL_PDSQI, czech_task.NAME_REAL, czech_task.load_real),
    "translated": (
        results.TRACK_CZECH_TRANSLATED_PDSQI,
        czech_task.NAME_TRANSLATED,
        czech_task.load_translated,
    ),
}

#: One instrument per judge, read off the published rows rather than assumed.
#: A repeat asked at a different budget would measure two instruments and call
#: the difference instability.
BUDGETS = {"gemini-3.1-pro-preview": 2048, "gpt-5.6-terra": 256}


def _rank(session_id: str, system_id: str) -> str:
    """The project's sampling order. No score can reach it."""
    return hashlib.sha256(f"{session_id}/{system_id}".encode()).hexdigest()


def _sample(task_name: str) -> list:
    """One note per model: the first session in that model's own hash order."""
    best: dict[str, tuple[str, object]] = {}
    loader = HALVES["real"][2] if task_name == czech_task.NAME_REAL else HALVES["translated"][2]
    for cand in czech_pdsqi.from_generations(loader(), task_name=task_name):
        key = _rank(cand.session_id, cand.system_id)
        if cand.system_id not in best or key < best[cand.system_id][0]:
            best[cand.system_id] = (key, cand)
    return [cand for _key, cand in (best[system] for system in sorted(best))]


def _scored_by_note(results_list) -> dict[tuple[str, str], dict[str, float]]:
    return {
        (note.candidate.system_id, note.candidate.session_id): dict(note.scored)
        for note in results_list
    }


def _first_asked(candidate, judge_model: str, fingerprint: dict, attribute: str) -> str | None:
    """The day the first answer to this question was written, or None.

    Recorded because two different things move an answer and they need telling
    apart. One is the judge: a sampled model asked twice may answer twice
    differently, and that is what this tool is for. The other is the endpoint:
    a model served under an unchanged id may not be the model that was served a
    week ago -- this repository has `command-a` returning `gemma4`'s output on
    record, and its own snapshot says the roster changed after the last probe.

    Those two produce the same difference and mean opposite things. If answers
    written days ago move and answers written today do not, the instability is
    not the judge's, and no amount of re-asking will settle it.

    The file's date, not a field: the answer records `scored_at`, but an answer
    recovered from the pre-2026-08-31 path was written before that field could
    be trusted to survive a move. The date the bytes were last written is the
    one thing that is true of every file here.
    """
    import time

    path = judge.cache_path(
        judge_model,
        czech_pdsqi.JUDGE_PROMPT_VERSION,
        candidate.provider,
        candidate.system_id,
        candidate.session_id,
        f"pdsqi.{attribute}",
        fingerprint=fingerprint,
    )
    if not path.exists():
        older = judge.legacy_path(path)
        if older is None or not older.exists():
            return None
        path = older
    return time.strftime("%Y-%m-%d", time.localtime(path.stat().st_mtime))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--half", choices=[*HALVES, "both"], default="both")
    parser.add_argument("--judge-model", action="append", help="default: both judges")
    parser.add_argument("--max-judge-usd", type=float, default=10.0)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    load_dotenv(REPO / ".env")
    halves = [args.half] if args.half != "both" else list(HALVES)
    judges = args.judge_model or list(BUDGETS)

    payload: dict = {"root": str(REPEAT_ROOT), "halves": {}}
    planned = 0

    for half in halves:
        track, task_name, _loader = HALVES[half]
        sample = _sample(task_name)
        attributes = czech_pdsqi.attribute_keys(task_name)
        planned += len(sample) * len(attributes) * len(judges)
        print(f"\n=== {half}: {len(sample)} note(s), {len(attributes)} attribute(s)")
        for cand in sample:
            print(f"    {cand.system_id:26s} {cand.session_id}")

        if args.dry_run:
            continue

        with_transcript = czech_pdsqi.transcripts_may_leave(task_name)
        for judge_model in judges:
            client = judge.Judge(
                judge.config_from_env(model=judge_model, thinking_budget=BUDGETS[judge_model])
            )
            spend = judge.Spend(limit_usd=args.max_judge_usd)

            # 1. What was answered the first time. Read only; the live cache is
            #    never written to by this tool.
            first = _scored_by_note(
                pdsqi_run.from_cache(
                    sample,
                    client,
                    with_transcript=with_transcript,
                    render=czech_task.render_note,
                    judge_prompt_version=czech_pdsqi.JUDGE_PROMPT_VERSION,
                )
            )

            # 2. Ask again, into a root of its own.
            print(f"\n  asking {judge_model} again ({half}) ...", flush=True)
            pdsqi_run.score_many(
                sample,
                client,
                spend,
                cache_root=REPEAT_ROOT,
                with_transcript=with_transcript,
                render=czech_task.render_note,
                judge_prompt_version=czech_pdsqi.JUDGE_PROMPT_VERSION,
            )
            second = _scored_by_note(
                pdsqi_run.from_cache(
                    sample,
                    client,
                    cache_root=REPEAT_ROOT,
                    with_transcript=with_transcript,
                    render=czech_task.render_note,
                    judge_prompt_version=czech_pdsqi.JUDGE_PROMPT_VERSION,
                )
            )

            # 3. Compare per note per attribute. A note answered once and not
            #    twice is dropped from the comparison and counted, never
            #    treated as agreement.
            fingerprint = client.config.fingerprint()
            by_note = {(c.system_id, c.session_id): c for c in sample}
            moves: dict[str, list[float]] = defaultdict(list)
            by_age: dict[str, list[float]] = defaultdict(list)
            unpaired = 0
            for key, before in first.items():
                after = second.get(key)
                if after is None:
                    unpaired += 1
                    continue
                for attribute, value in before.items():
                    if attribute not in after:
                        unpaired += 1
                        continue
                    move = after[attribute] - value
                    moves[attribute].append(move)
                    day = _first_asked(by_note[key], judge_model, fingerprint, attribute)
                    by_age[day or "unknown"].append(move)

            block = {}
            for attribute in sorted(moves):
                diffs = moves[attribute]
                same = sum(1 for d in diffs if abs(d) < 1e-9)
                block[attribute] = {
                    "n": len(diffs),
                    "identical": same,
                    "identical_share": round(same / len(diffs), 4) if diffs else None,
                    "median_abs": round(statistics.median(abs(d) for d in diffs), 4),
                    "max_abs": round(max(abs(d) for d in diffs), 4),
                    "mean_signed": round(statistics.fmean(diffs), 4),
                }
            # The same moves cut by when the first answer was written. Two
            # causes produce one difference: a judge that answers twice
            # differently, and an endpoint serving a different model under an
            # unchanged id. Only the dates tell them apart.
            ages = {
                day: {
                    "n": len(diffs),
                    "identical_share": round(
                        sum(1 for d in diffs if abs(d) < 1e-9) / len(diffs), 4
                    ),
                    "median_abs": round(statistics.median(abs(d) for d in diffs), 4),
                }
                for day, diffs in sorted(by_age.items())
                if diffs
            }
            payload["halves"].setdefault(track, {})[judge_model] = {
                "attributes": block,
                "by_first_answer_day": ages,
                "notes": len(first),
                "unpaired": unpaired,
                "budget": BUDGETS[judge_model],
                "usd": round(spend.usd(client.config.model), 4),
            }

            usd = spend.usd(client.config.model)
            print(f"\n  {track} | {judge_model}   ({len(first)} note(s), ${usd:.2f})")
            print(f"    {'attribute':16s} {'n':>4} {'same':>6} {'med|d|':>8} {'max|d|':>8}")
            for attribute, cells in block.items():
                print(
                    f"    {attribute:16s} {cells['n']:4d} "
                    f"{cells['identical_share']:6.0%} {cells['median_abs']:8.2f} "
                    f"{cells['max_abs']:8.2f}"
                )
            if ages:
                print(f"    {'first asked':16s} {'n':>4} {'same':>6} {'med|d|':>8}")
                for day, cells in ages.items():
                    print(
                        f"    {day:16s} {cells['n']:4d} "
                        f"{cells['identical_share']:6.0%} {cells['median_abs']:8.2f}"
                    )
            if unpaired:
                print(
                    f"    !! {unpaired} answer(s) present once and not twice -- "
                    "excluded, never counted as agreement"
                )

    if args.dry_run:
        print(f"\nDry run: {planned} judge question(s) would be asked. Nothing was sent.")
        print(f"They would be written under {REPEAT_ROOT}, never over the live answers.")
        return 0

    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nwrote {args.target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
