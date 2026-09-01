"""What the endpoint serves today, against what the tables are built from.

Asks the endpoint for its catalogue -- one call, no generation, no judge -- and
compares it with the systems the local rows draw. Reports both directions.

**Why this exists.** `glm-5.3-flash` wrote Czech notes on 2026-08-28 and was
withdrawn from e-INFRA some time after. Nothing said so. It was found on
2026-09-01 by trying to generate with it and reading an HTTP 400 whose body said
`Invalid model name passed in model=glm-5.3-flash` -- three days late, after a
run that could never have succeeded. A withdrawal is not a failure to retry; it
is a question that can no longer be put, and the only honest response is to say
so beside the tables rather than leave an empty cell that reads as a result.

The other direction matters as much and is quieter. A model that ARRIVES is
missing from every table until somebody notices, and its absence looks exactly
like a model that did badly. `glm-5.3` sat unmeasured on the Czech tracks for
days for that reason.

**Neither direction is fixed by this tool, and that is deliberate.** An arrival
needs generation and scoring, which costs the endpoint's quota; a withdrawal
cannot be fixed at all. This says what is true and what each case costs, and
leaves the spending to a person.

Exit code is 1 when the roster and the tables disagree, so a rebuild can be
gated on it.

    uv run python tools/czech_roster.py
    uv run python tools/czech_roster.py --provider einfra
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from dotenv import load_dotenv  # noqa: E402

from tnb import results  # noqa: E402
from tnb.config import load_policy  # noqa: E402
from tnb.providers import openai_compatible as oc  # noqa: E402

ROWS = results.LOCAL_ROWS_PATH

#: The tracks this tool speaks for. The Czech branch is the one whose corpus may
#: only be sent to e-INFRA, so it is the one whose roster moves under it; the
#: published English tracks run against three providers and are not compared
#: here rather than compared badly.
CZECH_TRACKS = (
    results.TRACK_CZECH_REAL,
    results.TRACK_CZECH_TRANSLATED,
    results.TRACK_DEEPSY_REAL,
    results.TRACK_DEEPSY_TRANSLATED,
    results.TRACK_CZECH_REAL_PDSQI,
    results.TRACK_CZECH_TRANSLATED_PDSQI,
    results.TRACK_DEEPSY_REAL_PDSQI,
    results.TRACK_DEEPSY_TRANSLATED_PDSQI,
)


def _drawn() -> dict[str, set[str]]:
    """{system_id: the tracks that draw a scored row for it}."""
    found: dict[str, set[str]] = defaultdict(set)
    if not ROWS.exists():
        return found
    for row in results.latest(results.load(ROWS)):
        if row.is_scored and row.track in CZECH_TRACKS:
            found[row.system_id].add(row.track)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--provider", default="einfra")
    args = parser.parse_args(argv)

    load_dotenv(REPO / ".env")
    provider = load_policy().get(args.provider)

    try:
        # `included` only. `discover` returns everything the endpoint reports
        # and marks why each was dropped, so the raw set holds `whisper`,
        # embedding models and unversioned aliases -- none of which can write a
        # therapy note. Comparing against the raw set reported twenty
        # "arrivals" that will never be measured and buried the one that
        # mattered.
        deployed = {model.id for model in oc.discover(provider) if model.included}
    except Exception as error:  # noqa: BLE001 -- the reason belongs on the page
        # A catalogue that cannot be read is not an empty catalogue. Saying
        # "every model was withdrawn" because the network failed is exactly the
        # absence-as-measurement this repository refuses everywhere else.
        print(f"could not read {args.provider}'s catalogue: {type(error).__name__}: {error}")
        print("Nothing is claimed about the roster. This is not a clean result.")
        return 2

    drawn = _drawn()
    if not drawn:
        print(f"{ROWS} holds no scored Czech rows; nothing to compare.")
        return 0

    print(f"{args.provider} serves {len(deployed)} benchmarkable model(s) right now.")
    print(f"the local tables draw {len(drawn)} system(s) across {len(CZECH_TRACKS)} track(s).\n")

    withdrawn = sorted(set(drawn) - deployed)
    arrived = sorted(deployed - set(drawn))

    print("=== withdrawn: in the tables, not on the endpoint")
    if not withdrawn:
        print("  (none)")
    for system in withdrawn:
        tracks = sorted(drawn[system])
        print(f"  {system}")
        print(f"      drawn in {len(tracks)} of {len(CZECH_TRACKS)} track(s): {', '.join(tracks)}")
        absent = [t for t in CZECH_TRACKS if t not in drawn[system]]
        if absent:
            print(f"      absent from: {', '.join(absent)}")
            print("      those cannot be filled: the model is gone. Name the gap, do not retry it.")
        else:
            print("      complete. Its numbers stand; it will simply never gain another.")

    print("\n=== arrived: on the endpoint, not in the tables")
    if not arrived:
        print("  (none)")
    for system in arrived:
        print(f"  {system}")
        print(
            f"      fix: uv run tnb generate --models {system} --tasks czech-real,czech-translated"
        )
        print("           then the score-* commands, then tools/czech_variance.py --only <track>")

    print("\n=== ragged: served, drawn, but not everywhere")
    ragged = {
        system: sorted(set(CZECH_TRACKS) - tracks)
        for system, tracks in sorted(drawn.items())
        if system in deployed and set(CZECH_TRACKS) - tracks
    }
    if not ragged:
        print("  (none)")
    for system, missing in ragged.items():
        print(f"  {system}: missing from {len(missing)} track(s): {', '.join(missing)}")
    if ragged:
        print(
            "\n  A claim of the form 'in the top band of ALL N tables' is an intersection,\n"
            "  so a system drawn in fewer tables drops out of it silently. That reads as\n"
            "  'not among the best' when it means 'was not asked'."
        )

    problems = len(withdrawn) + len(arrived) + len(ragged)
    print(f"\n{problems} disagreement(s) between the roster and the tables.")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
