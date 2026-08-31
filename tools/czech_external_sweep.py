"""Does the answer depend on the three models the index cannot name?

`tools/czech_external.py` correlates a published capability index against what
this project measured, and leaves three models out because the index has no
unambiguous value for them: Gemma 4 ships in six variants scoring 15 to 30 and
the endpoint's id names no size, Qwen3.5 spans 0.8B to 397B where `int4` names
the quantisation rather than the model, and Artificial Analysis has no separate
page for a thinking variant at all. Assigning any one number would be a guess
spanning a factor of two, which is why they are absent rather than guessed.

Absent is right and it leaves a question open: the Czech comparisons then rest
on eight models against English's fifteen, and `czech_quality` reaches +0.69
under one judge at p = 0.064 -- a figure close enough to the line that the
missing three could plausibly decide it.

**So sweep instead of guess.** Every unknown is given its whole plausible range
rather than one value, the correlation is recomputed for each assignment, and
the question becomes: is there ANY assignment under which the index predicts
Czech, and does the conclusion hold across all of them. That is answerable
without knowing which variant e-INFRA served, and it costs no call: the notes
were scored long ago and this is arithmetic over the payloads.

A sweep cannot say what the true value is. It says whether the true value
matters, which is the only thing the gap was ever blocking.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from itertools import product
from pathlib import Path
from statistics import mean

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import czech_external as ext  # noqa: E402

from tnb import judge, results  # noqa: E402
from tnb.scoring import czech  # noqa: E402

DEFAULT_TARGET = REPO / "local" / "czech-external-sweep.json"

#: What each unmatched id could plausibly be, straight out of the reasons
#: `local/model-external.json` records for leaving it out. The endpoints are
#: included, so a sweep spans the whole stated interval rather than its inside.
RANGES: dict[str, tuple[float, ...]] = {
    # Six variants, 15 to 30.
    "gemma4": (15, 20, 25, 30),
    # 0.8B to 397B, 20 to 45.
    "qwen3.5-int4": (20, 28, 36, 45),
    # The 52 on the `deepseek-v4-flash` page is stated for "Reasoning, Max
    # Effort", so it may belong to this id instead. Swept around it, because
    # both ids cannot hold it and which one does is exactly the ambiguity.
    "deepseek-v4-flash-thinking": (45, 52, 60),
}

#: Fewer than the 200 000 `czech_external` uses. That figure is for a published
#: number and this is a screen over 48 assignments; the assignments that come
#: near the line are then re-run at full depth.
SCREEN_DRAWS = 20_000
CONFIRM_DRAWS = 200_000

MEASURES = {
    "czech_quality": (results.TRACK_CZECH_TRANSLATED_PDSQI, ext.QUALITY),
    "czech_language": (results.TRACK_CZECH_TRANSLATED, tuple(czech.CRITERION_KEYS)),
}


def _p(here: list[float], outside: list[float], draws: int) -> dict:
    """Spearman with a sampled permutation p-value, the way the tool does it."""
    ra, rb = ext._ranks(outside), ext._ranks(here)
    observed = ext._rho(ra, rb)
    if observed is None:
        return {"rho": None, "p": None, "n": len(here)}
    rng = random.Random(ext.SEED)  # noqa: S311 -- a p-value, not a secret
    hits = 0
    for _ in range(draws):
        shuffled = list(rb)
        rng.shuffle(shuffled)
        value = ext._rho(ra, shuffled)
        if value is not None and abs(value) >= abs(observed) - 1e-12:
            hits += 1
    return {"rho": round(observed, 4), "p": round(hits / draws, 4), "n": len(here)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--draws", type=int, default=SCREEN_DRAWS)
    args = parser.parse_args(argv)

    external = json.loads((REPO / "local" / "model-external.json").read_text(encoding="utf-8"))
    known = {k: v["index"] for k, v in external["models"].items() if v.get("index") is not None}
    rows = results.load(results.LOCAL_ROWS_PATH)

    judges = (judge.DEFAULT_MODEL, judge.SECOND_JUDGE)
    scores: dict[tuple[str, str], dict[str, float]] = {}
    for name, (track, keys) in MEASURES.items():
        for judge_model in judges:
            table = ext._tables(rows, track, judge_model)
            scores[(name, judge_model)] = {
                model: mean(values)
                for model, cells in table.items()
                if (values := [cells[k] for k in keys if cells.get(k) is not None])
            }

    combos = list(product(*(RANGES[name] for name in RANGES)))
    print(f"{len(combos)} assignments; unknown: {', '.join(RANGES)}\n")

    results_by_measure: dict[str, list[dict]] = {}
    for name in MEASURES:
        found = []
        for combo in combos:
            guessed = dict(zip(RANGES, combo, strict=True))
            outside = {**known, **guessed}
            per_judge = {}
            for judge_model in judges:
                here = scores[(name, judge_model)]
                shared = sorted(set(outside) & set(here))
                per_judge[judge_model] = _p(
                    [here[m] for m in shared], [outside[m] for m in shared], args.draws
                )
            found.append(
                {
                    "assignment": guessed,
                    "judges": per_judge,
                    "both_significant": all(
                        (v["p"] is not None and v["p"] < 0.05) for v in per_judge.values()
                    ),
                }
            )
        results_by_measure[name] = found

        n = found[0]["judges"][judges[0]]["n"]
        wins = sum(1 for f in found if f["both_significant"])
        print(f"=== {name}  (n = {n}, was 8)")
        for judge_model in judges:
            rhos = [f["judges"][judge_model]["rho"] for f in found]
            ps = [f["judges"][judge_model]["p"] for f in found]
            print(
                f"    {judge_model:26s} rho {min(rhos):+.2f} to {max(rhos):+.2f}"
                f"   p {min(ps):.3f} to {max(ps):.3f}"
                f"   significant in {sum(1 for p in ps if p < 0.05)}/{len(ps)}"
            )
        print(f"    -> significant under BOTH judges in {wins} of {len(found)}\n")

    payload = {
        "what_this_is": __doc__.strip().split("\n\n")[0],
        "not_a_score": (
            "A sensitivity analysis over values the index does not state. No figure here "
            "is a measurement of any model's capability, and none may be published as one."
        ),
        "ranges": {k: list(v) for k, v in RANGES.items()},
        "why_unmatched": external.get("unmatched"),
        "draws": args.draws,
        "measures": results_by_measure,
    }
    args.target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
