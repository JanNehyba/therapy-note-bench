"""Does a model's standing on the English leaderboard say anything about its Czech?

The question the whole track was built to answer. It is answered by joining two
tables on the models they share, and it has two answers depending on which
English number is asked.

**The clean comparison is the same instrument in two languages.** PDSQI-9 rates
the English SOAP notes on `pdsqi-soap` and the Czech notes on
`czech-translated-pdsqi`. Same attributes, same anchors, same judge -- only the
language of the note differs. If quality transfers, it shows here.

**The comparison a reader actually makes is the leaderboard's.** The English
page ranks by TN-Eval completeness, so "this model is third" means third on
completeness. Whether *that* predicts anything about Czech is a different
question with a different answer, and both belong in the report.

**Nine models, so the arithmetic has to be honest about it.** Spearman over nine
points is easy to over-read, and this repository has a standing rule against
reporting an impression as a result. Every correlation here carries an exact
permutation p-value -- all 362,880 relabellings, computed rather than
approximated -- and a column that is flat on either side is named as flat rather
than correlated. A rho over a column where every model scores 5.00 is a coin.

**And one confound that cannot be removed, only stated.** The English numbers
are over all 50 AnnoMI conversations; the Czech ones are over the 10 that were
translated. So this compares two *standings*, not two scores on one session set.
Recomputing the English side over the same ten would remove it and is not done
here.

Writes `local/czech-join.json` for `tools/czech_brief.py`.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from itertools import permutations
from math import factorial
from pathlib import Path
from statistics import mean

from tnb import judge, results
from tnb.scoring import pdsqi

REPO = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = REPO / "local" / "czech-join.json"

#: Above this many relabellings, sample instead of enumerating. Nine models is
#: 362,880 and takes a second; ten is 3.6 million and does not.
EXACT_LIMIT = 500_000
SAMPLES = 200_000

#: What the English page ranks by. Its correlation with the Czech columns is the
#: question a reader asks without meaning to, every time they read a position.
ENGLISH_RANKING = ("tneval-soap", "completeness")

#: The one thing wrong with this comparison that cannot be fixed here, only
#: said. It travels with every figure the tool produces.
CONFOUND = (
    "The English scores are over all 50 AnnoMI conversations and the Czech over the "
    "10 that were translated, so these are two standings rather than two scores on "
    "one set of sessions. Removing it means recomputing the English side over the "
    "same ten, which has not been done."
)

#: What a reader may take from nine points, and what they may not.
READING = (
    "Nine models. Read a column that says the same thing under both judges; treat "
    "one that does not as unmeasured rather than as weak evidence."
)


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def _rho(a: list[float], b: list[float]) -> float | None:
    ma, mb = mean(a), mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b, strict=True))
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    return num / den if den else None


def correlate(a: list[float], b: list[float]) -> dict | None:
    """Spearman with a permutation p-value, or None when either side is flat.

    Flat means one value for every model. `concordance.MeasureAgreement`
    already refuses to rank such a column and the reason is the same here: a
    correlation computed over it is decided by whichever model is not at the
    ceiling.
    """
    if len(a) < 3 or len(set(a)) == 1 or len(set(b)) == 1:
        return None

    ra, rb = _ranks(a), _ranks(b)
    observed = _rho(ra, rb)
    if observed is None:
        return None

    if factorial(len(a)) <= EXACT_LIMIT:
        trials = permutations(rb)
        total = factorial(len(a))
        exact = True
    else:
        shuffler = random.Random(0)  # noqa: S311 -- a p-value, not a secret

        def sampled():
            for _ in range(SAMPLES):
                order = list(rb)
                shuffler.shuffle(order)
                yield order

        trials = sampled()
        total = SAMPLES
        exact = False

    hits = 0
    for permuted in trials:
        value = _rho(ra, list(permuted))
        if value is not None and abs(value) >= abs(observed) - 1e-12:
            hits += 1

    return {
        "rho": round(observed, 4),
        "p": round(hits / total, 4),
        "n": len(a),
        "exact": exact,
    }


def _table(rows, track: str, judge_model: str) -> dict[str, dict[str, float]]:
    return {
        row.system_id: row.metrics.headline
        for row in results.latest(rows)
        if row.track == track and row.is_scored and row.judge_model == judge_model
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args(argv)

    published = results.load()
    local = results.load(results.LOCAL_ROWS_PATH)
    if not local:
        print("No local Czech rows yet.", file=sys.stderr)
        return 1

    payload: dict = {
        "question": (
            "Does a model's standing on the English leaderboard say anything about "
            "the Czech it writes?"
        ),
        "confound": CONFOUND,
        "reading": READING,
        "judges": {},
    }

    for judge_model in (judge.DEFAULT_MODEL, judge.SECOND_JUDGE):
        english_pdsqi = _table(published, results.TRACK_PDSQI, judge_model)
        english_rubric = _table(published, ENGLISH_RANKING[0], judge_model)
        czech_pdsqi = _table(local, results.TRACK_CZECH_TRANSLATED_PDSQI, judge_model)
        shared = sorted(set(english_pdsqi) & set(czech_pdsqi))
        if len(shared) < 3:
            continue

        same_instrument, flat = {}, []
        for key in pdsqi.ATTRIBUTE_KEYS:
            a = [english_pdsqi[s].get(key) for s in shared]
            b = [czech_pdsqi[s].get(key) for s in shared]
            if None in a or None in b:
                continue
            result = correlate(a, b)
            if result is None:
                flat.append(key)
            else:
                same_instrument[key] = result

        leaderboard = {}
        ranking = [english_rubric.get(s, {}).get(ENGLISH_RANKING[1]) for s in shared]
        if None not in ranking:
            for key in pdsqi.ATTRIBUTE_KEYS:
                b = [czech_pdsqi[s].get(key) for s in shared]
                if None in b:
                    continue
                result = correlate(ranking, b)
                if result is not None:
                    leaderboard[key] = result

        payload["judges"][judge_model] = {
            "systems": shared,
            "same_instrument": same_instrument,
            "flat": flat,
            "leaderboard_ranking": leaderboard,
            "ranking_measure": ENGLISH_RANKING[1],
        }

    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for judge_model, block in payload["judges"].items():
        print(f"\n### {judge_model} — {len(block['systems'])} models in both tables")
        print("PDSQI-9 in English against PDSQI-9 in Czech, attribute by attribute:")
        for key, r in block["same_instrument"].items():
            star = " *" if r["p"] < 0.05 else ""
            print(f"  {key:16} rho {r['rho']:+.2f}   p = {r['p']:.3f}{star}")
        if block["flat"]:
            print(f"  flat on one side, not correlated: {', '.join(block['flat'])}")
        print(f"English {block['ranking_measure']} against the Czech quality columns:")
        for key, r in block["leaderboard_ranking"].items():
            star = " *" if r["p"] < 0.05 else ""
            print(f"  {key:16} rho {r['rho']:+.2f}   p = {r['p']:.3f}{star}")

    print(f"\nwrote {args.target}")
    print("* p < 0.05 by exact permutation. Nine models is a small sample; read the")
    print("  columns that agree under both judges and treat the rest as unmeasured.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
