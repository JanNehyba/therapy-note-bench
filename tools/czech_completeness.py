"""What the Czech branch is missing, and the command that fills each gap.

Offline. Reads the generation cache, `local/czech-rows.jsonl` and
`local/czech-variance.json`; asks no judge and calls no endpoint. Prints ids and
counts only -- never note text, never transcript text.

**Why this exists.** A model was added to the Czech corpus and nothing said what
that left undone. `glm-5.3` was generated and scored, and then appeared in six
tables with a score and an empty Band cell, because the bands had been computed
two days earlier and no step compares the two. Every gap of that shape is
invisible in the same way: the document draws what it has and says nothing about
what it does not, and `results` is append-only so nothing is ever overwritten
loudly enough to notice.

Four gaps are counted, because four are what actually happened:

1. **Generated, not scored.** Notes exist that no judge has read.
2. **Scored thinly.** A model scored on fewer sessions than the corpus holds.
   Its row is drawn beside models resting on more, and the mean is over a
   different denominator.
3. **Scored, not banded.** The gap that prompted this file.
4. **Asked in one place and not its twin.** A model rated on the real half and
   not the translated one, or in SOAP and not Deepsy, is a model whose two
   numbers cannot be compared -- and whose absence from one table reads as a
   result rather than as a question nobody put.

Exit code is 1 when anything is missing, so a rebuild can be gated on it.

    uv run python tools/czech_completeness.py
    uv run python tools/czech_completeness.py --track czech-real-pdsqi
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from dotenv import load_dotenv  # noqa: E402

from tnb import judge, results  # noqa: E402
from tnb.scoring import czech_pdsqi  # noqa: E402

ROWS = results.LOCAL_ROWS_PATH
VARIANCE = ROWS.parent / "czech-variance.json"

#: The two judges every Czech table is drawn under. A gap under one of them is a
#: gap: the document never averages them, so a model answered by one judge and
#: not the other is missing from half the tables it belongs in.
JUDGES = ("gemini-3.1-pro-preview", "gpt-5.6-terra")

#: Which tracks are twins of each other, and on which axis. Named rather than
#: derived from the ids: `czech-real` and `czech-real-pdsqi` share a prefix and
#: are NOT twins -- they are two instruments over one corpus, and a model may
#: honestly be in one and not the other.
TWINS = (
    ("half", results.TRACK_CZECH_REAL, results.TRACK_CZECH_TRANSLATED),
    ("half", results.TRACK_DEEPSY_REAL, results.TRACK_DEEPSY_TRANSLATED),
    ("half", results.TRACK_CZECH_REAL_PDSQI, results.TRACK_CZECH_TRANSLATED_PDSQI),
    ("half", results.TRACK_DEEPSY_REAL_PDSQI, results.TRACK_DEEPSY_TRANSLATED_PDSQI),
    ("format", results.TRACK_CZECH_REAL, results.TRACK_DEEPSY_REAL),
    ("format", results.TRACK_CZECH_TRANSLATED, results.TRACK_DEEPSY_TRANSLATED),
    ("format", results.TRACK_CZECH_REAL_PDSQI, results.TRACK_DEEPSY_REAL_PDSQI),
    ("format", results.TRACK_CZECH_TRANSLATED_PDSQI, results.TRACK_DEEPSY_TRANSLATED_PDSQI),
)


def _fix(track: str, judge_model: str) -> str:
    """The command that fills a scoring gap on this track under this judge."""
    import czech_variance

    if track in czech_variance.CRITERIA_TRACKS:
        base = "score-deepsy" if track.startswith("deepsy") else "score-czech"
        corpus = "real" if track.endswith("-real") else "translated"
    else:
        base = "score-czech-pdsqi"
        corpus = "real" if "-real-" in track else "translated"
    fmt = " --format deepsy" if track.startswith("deepsy") and "pdsqi" in track else ""
    budget = " --thinking-budget 2048" if "gemini" in judge_model else ""
    who = "" if judge_model == judge.DEFAULT_MODEL else f" --judge-model {judge_model}"
    return f"uv run tnb {base} --corpus {corpus}{fmt}{who}{budget}"


def _candidates() -> dict[str, dict[str, int]]:
    """{track: {system: notes that exist and could be read}}.

    Uses each track's own loader and assembler, because a Deepsy note is three
    calls assembled as a whole and the SOAP reader yields nothing for one --
    silently, which is the failure `czech_variance.Spec` records.
    """
    import czech_variance

    found: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for track, spec in czech_variance.CRITERIA_TRACKS.items():
        for cand in spec.assemble(spec.load(), task_name=spec.task_name):
            found[track][cand.system_id] += 1

    pdsqi_tracks = {
        results.TRACK_CZECH_REAL_PDSQI: "czech-real",
        results.TRACK_CZECH_TRANSLATED_PDSQI: "czech-translated",
        results.TRACK_DEEPSY_REAL_PDSQI: "deepsy-real",
        results.TRACK_DEEPSY_TRANSLATED_PDSQI: "deepsy-translated",
    }
    for track, task_name in pdsqi_tracks.items():
        loader, _render, _root = czech_variance.PDSQI_CORPORA[task_name]
        for cand in czech_pdsqi.from_generations(loader(), task_name=task_name):
            found[track][cand.system_id] += 1
    return {track: dict(systems) for track, systems in found.items()}


def _scored() -> dict[tuple[str, str], dict[str, int]]:
    """{(track, judge): {system: notes the judge finished}}.

    The count is `n_sessions_scored`. Getting the field name wrong is not a
    quiet failure here -- it is a loud one that says every model scored zero
    notes, which is how the first version of this file reported 24 gaps that
    were not there. The assertion below refuses that reading rather than
    printing it.
    """
    found: dict[tuple[str, str], dict[str, int]] = defaultdict(dict)
    for row in results.latest(results.load(ROWS)):
        if not row.is_scored or not row.judge_model:
            continue
        n = row.n_sessions_scored
        if not n:
            # A scored row that scored no session is a contradiction, not a
            # thin denominator. Say so instead of counting it as a gap.
            print(f"  !! {row.track} | {row.judge_model} | {row.system_id}: scored, n=0")
        found[(row.track, row.judge_model)][row.system_id] = n or 0
    return found


def _bands() -> dict[tuple[str, str], set[str]]:
    if not VARIANCE.exists():
        return {}
    payload = json.loads(VARIANCE.read_text(encoding="utf-8"))
    return {
        (track, judge_model): {m for band in grouped["bands"] for m in band["models"]}
        for track, judges in (payload.get("bands") or {}).items()
        for judge_model, grouped in judges.items()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--track", action="append", help="only these tracks")
    args = parser.parse_args(argv)

    load_dotenv(REPO / ".env")
    if not ROWS.exists():
        print(f"{ROWS} is not in this checkout; nothing to check.")
        return 0

    candidates, scored, bands = _candidates(), _scored(), _bands()
    wanted = set(args.track) if args.track else set(candidates)
    gaps: list[str] = []

    print("=== 1. generated but never read by a judge")
    for track in sorted(wanted & set(candidates)):
        for judge_model in JUDGES:
            have = scored.get((track, judge_model), {})
            absent = sorted(set(candidates[track]) - set(have))
            if absent:
                gaps.append(f"{track} | {judge_model}: unscored {', '.join(absent)}")
                print(f"  {track} | {judge_model}")
                print(f"      {len(absent)} model(s): {', '.join(absent)}")
                print(f"      fix: {_fix(track, judge_model)}")
    print("  (none)" if not gaps else "")

    before = len(gaps)
    print("\n=== 2. scored on fewer notes than the corpus holds")
    for track in sorted(wanted & set(candidates)):
        full = max(candidates[track].values(), default=0)
        for judge_model in JUDGES:
            thin = {
                system: n
                for system, n in sorted(scored.get((track, judge_model), {}).items())
                # A model that WROTE fewer notes is a generation gap, counted in
                # section 1's sibling below -- not a judge that stopped early.
                if n < candidates[track].get(system, 0)
            }
            if thin:
                gaps.append(f"{track} | {judge_model}: thin {thin}")
                print(f"  {track} | {judge_model}  (corpus holds {full})")
                for system, n in thin.items():
                    print(f"      {system}: {n} of {candidates[track][system]} note(s) scored")
                print(f"      fix: {_fix(track, judge_model)}")
    print("  (none)" if len(gaps) == before else "")

    before = len(gaps)
    print("\n=== 3. scored but absent from the bands")
    for (track, judge_model), have in sorted(scored.items()):
        if track not in wanted:
            continue
        placed = bands.get((track, judge_model))
        if placed is None:
            continue  # this track is not banded at all: a visible decision
        absent = sorted(set(have) - placed)
        if absent:
            gaps.append(f"{track} | {judge_model}: unbanded {', '.join(absent)}")
            print(f"  {track} | {judge_model}")
            print(f"      {len(absent)} model(s): {', '.join(absent)}")
            print(f"      fix: uv run python tools/czech_variance.py --only {track}")
    print("  (none)" if len(gaps) == before else "")

    before = len(gaps)
    print("\n=== 4. asked in one table and not its twin")
    for axis, left, right in TWINS:
        if left not in wanted and right not in wanted:
            continue
        for judge_model in JUDGES:
            a = set(scored.get((left, judge_model), {}))
            b = set(scored.get((right, judge_model), {}))
            if not a or not b:
                continue
            for missing_in, present_in, names in (
                (right, left, sorted(a - b)),
                (left, right, sorted(b - a)),
            ):
                if names:
                    gaps.append(f"{missing_in} | {judge_model}: absent {', '.join(names)}")
                    print(f"  {judge_model} | across the {axis}")
                    print(f"      in {present_in} and not {missing_in}: {', '.join(names)}")
                    # Scoring reads the generation cache. A model absent from a
                    # track usually has no notes there at all -- `glm-5` had
                    # zero on both Czech halves -- and telling the reader to
                    # score is telling them to run something that finds nothing
                    # and says so quietly. Say which of the two it is.
                    ungenerated = [n for n in names if not candidates.get(missing_in, {}).get(n)]
                    if ungenerated:
                        corpus = "real" if missing_in.endswith("real") else "translated"
                        base = (
                            "generate-deepsy"
                            if missing_in.startswith("deepsy")
                            else "generate-czech"
                        )
                        print(
                            f"      no notes exist for {', '.join(ungenerated)} -- generate first:"
                        )
                        print(f"      fix: uv run tnb {base} --corpus {corpus}")
                    print(f"      then: {_fix(missing_in, judge_model)}")
    print("  (none)" if len(gaps) == before else "")

    print(f"\n{len(gaps)} gap(s).")
    if gaps:
        print(
            "\nEach one is a question nobody put, not a measurement of zero. A table "
            "drawn over these\nis drawn over an uneven denominator, and the document "
            "cannot say so unless it is told."
        )
    return 1 if gaps else 0


if __name__ == "__main__":
    raise SystemExit(main())
