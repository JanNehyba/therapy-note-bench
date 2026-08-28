"""Does a model's general capability predict the notes it writes?

The obvious question once a benchmark has a table of models, and one this
repository cannot answer from anything it measures: it records what a model
wrote and how the judges rated it, never how big the model is or when it came
out. So the comparison needs data from outside, and everything about how that
data is handled follows from its being from outside.

**It is matched by name, and the name is the weak link.** This repository's
first working rule exists because `command-a` returned `gemma4`'s output. A name
on e-INFRA is not evidence about which public model is behind it, so every row
is an assumption. Three models could not be matched at all -- Gemma 4 ships in
six sizes scoring 15 to 30, and the id names none of them -- and they are absent
rather than guessed. `local/model-external.json` records what was tried: the
endpoint's metadata, which returns one placeholder date for every model, and
asking the models directly, which produced no variant either.

**The external score moves too.** It is a property of the benchmark's version as
much as of the model, which is what `harness_version` says about this
repository's own measures. The version and the fetch date travel with every
figure.

**And it stays local.** Nothing here was measured here and none of it can be
verified from the endpoint the models ran on, so it is kept out of git and off
the published page until somebody decides otherwise.

Writes `local/czech-external.json` for `tools/czech_brief.py`.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from statistics import mean

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

from tnb import judge, results  # noqa: E402
from tnb.scoring import czech  # noqa: E402

DEFAULT_SOURCE = REPO / "local" / "model-external.json"
DEFAULT_TARGET = REPO / "local" / "czech-external.json"

#: Resamples for the permutation p-value. Sampled rather than enumerated:
#: fifteen models is 1.3 trillion orderings.
DRAWS = 200_000
SEED = 0

#: The quality attributes that vary. A column every model scores 5.00 on adds
#: nothing to a composite except a constant.
QUALITY = ("accurate", "thorough", "succinct")


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
    """Spearman with a sampled permutation p-value, or None if either is flat."""
    if len(a) < 4 or len(set(a)) == 1 or len(set(b)) == 1:
        return None
    ra, rb = _ranks(a), _ranks(b)
    observed = _rho(ra, rb)
    if observed is None:
        return None

    rng = random.Random(SEED)  # noqa: S311 -- a p-value, not a secret
    hits = 0
    for _ in range(DRAWS):
        shuffled = list(rb)
        rng.shuffle(shuffled)
        value = _rho(ra, shuffled)
        if value is not None and abs(value) >= abs(observed) - 1e-12:
            hits += 1
    return {"rho": round(observed, 4), "p": round(hits / DRAWS, 4), "n": len(a)}


def _tables(rows, track: str, judge_model: str) -> dict:
    return {
        row.system_id: row.metrics.headline
        for row in results.latest(rows)
        if row.track == track and row.is_scored and row.judge_model == judge_model
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args(argv)

    if not args.source.exists():
        print(f"{args.source} is not there.", file=sys.stderr)
        return 1
    external = json.loads(args.source.read_text(encoding="utf-8"))
    index = {k: v["index"] for k, v in external["models"].items() if v.get("index") is not None}
    released = {
        k: int(v["released"].replace("-", ""))
        for k, v in external["models"].items()
        if v.get("released")
    }

    published = results.load()
    local = results.load(results.LOCAL_ROWS_PATH)

    payload: dict = {
        "source": external["_source"],
        "fetched": external["_fetched"],
        "index_version": external["_index_version"],
        "unmatched": sorted(external.get("unmatched", {})),
        "judges": {},
    }

    measures = [
        ("english_completeness", published, results.TRACK_TNEVAL, ("completeness",)),
        ("english_quality", published, results.TRACK_PDSQI, QUALITY),
        ("czech_quality", local, results.TRACK_CZECH_TRANSLATED_PDSQI, QUALITY),
        ("czech_language", local, results.TRACK_CZECH_TRANSLATED, czech.CRITERION_KEYS),
    ]

    for judge_model in (judge.DEFAULT_MODEL, judge.SECOND_JUDGE):
        block = {}
        for name, rows, track, keys in measures:
            table = _tables(rows, track, judge_model)
            for label, outside in (("intelligence_index", index), ("release_date", released)):
                shared = sorted(set(outside) & set(table))
                pairs = [
                    (outside[m], mean([table[m][k] for k in keys if k in table[m]]))
                    for m in shared
                    if any(k in table[m] for k in keys)
                ]
                if len(pairs) < 4:
                    continue
                result = correlate([x for x, _ in pairs], [y for _, y in pairs])
                if result:
                    block.setdefault(name, {})[label] = result
        if block:
            payload["judges"][judge_model] = block

    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for judge_model, block in payload["judges"].items():
        print(f"\n### {judge_model}")
        for name, entries in block.items():
            for label, r in entries.items():
                star = " *" if r["p"] < 0.05 else ""
                print(
                    f"  {label:20} x {name:22} rho {r['rho']:+.2f}  "
                    f"p={r['p']:.4f}  n={r['n']}{star}"
                )
    print(f"\nwrote {args.target}")
    print(f"unmatched and therefore absent: {', '.join(payload['unmatched'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
