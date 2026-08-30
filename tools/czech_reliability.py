"""How far the coders agreed, measured the way a shared unit allows.

**Not a flat kappa over raw code names.** Two coders doing open coding produce
codebooks in different label spaces, and a kappa over the labels comes out
pathologically low while meaning nothing -- QualReAI's own plan says so and
rejects it. What is comparable is a verdict on a *shared* unit against a *shared*
category, which is what the deductive pass produces, and that is what is measured
here.

Three numbers per category, and never one:

- **Boundary agreement**, over the binary question *did this coder mark this unit
  at all*. Label-space free, and the honest headline.
- **Per-category kappa**, over the four values, for each pair of coders.
- **Krippendorff's alpha** over all coders at once, because there are three of
  them and because ``unclear`` and ``not-applicable`` have to be values rather
  than missing data.

Raw agreement, prevalence and the unit count are printed beside every one of
them. Kappa collapses when a category is present in nearly every unit or nearly
none, and a reader shown only kappa would read that collapse as disagreement. The
number of units is there because the third decimal place of an agreement figure
over forty units is noise.

**A coder that did not answer leaves the denominator.** It is never counted as a
disagreement, which would punish a coder for a failed call, and never as
agreement, which would invent a measurement. How many went missing is reported
beside the figure that excluded them.

Nothing here says the coders were right. Agreement is evidence that a category is
stable and codeable. Whether it is a category worth having is a different question
and this file cannot reach it.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO / "local" / "czech-codes.jsonl"
DEFAULT_TARGET = REPO / "local" / "czech-reliability.json"

#: The four verdicts. A value outside this set was already normalised to None by
#: the coding harness and reaches here as an absence.
VALUES = ("present", "absent", "unclear", "not-applicable")


def cohen_kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Agreement between two coders, corrected for chance.

    None when there is nothing to correct against -- fewer than two units, or a
    chance agreement of exactly one, which happens when both coders used a single
    value throughout. Returning 0.0 there would say "no better than chance" about
    two coders who agreed on everything, which is the opposite of what happened.
    """
    if len(pairs) < 2:
        return None
    total = len(pairs)
    observed = sum(1 for left, right in pairs if left == right) / total
    left_counts = Counter(left for left, _ in pairs)
    right_counts = Counter(right for _, right in pairs)
    expected = sum(
        (left_counts[value] / total) * (right_counts[value] / total)
        for value in set(left_counts) | set(right_counts)
    )
    if math.isclose(expected, 1.0):
        return None
    return round((observed - expected) / (1 - expected), 4)


def krippendorff_alpha(units: list[list[str]]) -> float | None:
    """Nominal alpha over any number of coders, with missing values dropped.

    Alpha rather than a kappa because there are three coders and because a unit
    one coder did not answer still carries the two answers it has. The
    coincidence-matrix form is used directly rather than a library, so that the
    handling of a unit with fewer than two answers is visible: it contributes
    nothing, because a single answer cannot agree or disagree with anything.
    """
    usable = [[value for value in unit if value] for unit in units]
    usable = [unit for unit in usable if len(unit) >= 2]
    if not usable:
        return None

    coincidences: dict[tuple[str, str], float] = defaultdict(float)
    totals: Counter = Counter()
    grand = 0.0
    for unit in usable:
        count = len(unit)
        for index, left in enumerate(unit):
            for other, right in enumerate(unit):
                if index == other:
                    continue
                coincidences[(left, right)] += 1.0 / (count - 1)
        for value in unit:
            totals[value] += 1
            grand += 1

    if grand < 2:
        return None
    observed = sum(coincidences[(value, value)] for value in totals)
    expected = sum(totals[value] * (totals[value] - 1) for value in totals) / (grand - 1)
    if math.isclose(expected, grand):
        return None
    return round(1 - (grand - observed) / (grand - expected), 4)


#: Which corpus a row belongs to, read off the session id. See the twin of this
#: in ``czech_graduate``: the file holds every corpus the panel has read and a
#: row says which one only through its session id.
TRACK_PREFIX = {"czech-real": "cz-r-", "czech-translated": "cz-t-"}


def load(source: Path, mode: str, track: str | None = None) -> list[dict]:
    """The coded rows of one corpus, or of all of them.

    An agreement figure pooled over two corpora is not an agreement figure about
    either. Where the coders agree more about one half than the other, pooling
    hides exactly the thing worth knowing.
    """
    prefix = TRACK_PREFIX.get(track) if track else None
    if track and prefix is None:
        raise ValueError(f"{track} has no session prefix. Known: {', '.join(TRACK_PREFIX)}")
    rows = []
    with source.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("mode") != mode:
                continue
            if prefix and not str(row.get("session_id", "")).startswith(prefix):
                continue
            rows.append(row)
    return rows


def measure(rows: list[dict]) -> dict:
    """One entry per category, plus the panel-wide boundary figure."""
    coders = sorted({row["coder"] for row in rows})
    by_category: dict[str, dict[tuple, dict[str, str]]] = defaultdict(lambda: defaultdict(dict))
    spans: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))

    for row in rows:
        key = (row["system_id"], row["session_id"], row["unit_index"])
        category = row.get("category")
        if category is None:
            continue
        if row.get("value") is not None:
            by_category[category][key][row["coder"]] = row["value"]
        if row.get("value") == "present":
            spans[category][row["coder"]].append(bool(row.get("span_valid")))

    out: dict[str, dict] = {}
    for category, cells in sorted(by_category.items()):
        units = sorted(cells)
        prevalence = Counter(value for cell in cells.values() for value in cell.values())
        answered = sum(prevalence.values())
        expected = len(units) * len(coders)

        pairwise = {}
        boundary = {}
        for left, right in combinations(coders, 2):
            both = [
                (cells[unit][left], cells[unit][right])
                for unit in units
                if left in cells[unit] and right in cells[unit]
            ]
            name = f"{left}-{right}"
            pairwise[name] = {
                "units": len(both),
                "raw_agreement": (
                    round(sum(1 for a, b in both if a == b) / len(both), 4) if both else None
                ),
                "kappa": cohen_kappa(both),
            }
            marked = [
                ("present" if a == "present" else "not", "present" if b == "present" else "not")
                for a, b in both
            ]
            boundary[name] = {
                "units": len(marked),
                "raw_agreement": (
                    round(sum(1 for a, b in marked if a == b) / len(marked), 4) if marked else None
                ),
                "kappa": cohen_kappa(marked),
            }

        alpha = krippendorff_alpha(
            [[cells[unit].get(coder, "") for coder in coders] for unit in units]
        )
        span_stats = {
            coder: {
                "present": len(flags),
                "discarded": sum(1 for flag in flags if not flag),
                "discard_rate": (
                    round(sum(1 for flag in flags if not flag) / len(flags), 4) if flags else None
                ),
            }
            for coder, flags in sorted(spans[category].items())
        }

        out[category] = {
            "units": len(units),
            "coders": coders,
            "verdicts_expected": expected,
            "verdicts_answered": answered,
            "verdicts_missing": expected - answered,
            "prevalence": {value: prevalence.get(value, 0) for value in VALUES},
            "present_rate": (
                round(prevalence.get("present", 0) / answered, 4) if answered else None
            ),
            "pairwise": pairwise,
            "boundary": boundary,
            "krippendorff_alpha": alpha,
            "spans": span_stats,
        }
    return out


CAVEAT = (
    "Agreement between coders is evidence that a category is stable and codeable. "
    "It is no evidence at all that the category matters, and no human has read "
    "these notes as a clinician. Read a kappa beside its prevalence: a category "
    "present in nearly every unit, or nearly none, produces a low kappa from a "
    "high agreement and the collapse is arithmetic rather than disagreement."
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Agreement across the coder panel.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--mode", default="deductive")
    parser.add_argument("--track", default="czech-real")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    rows = load(args.source, args.mode, track=args.track)
    payload = {"caveat": CAVEAT, "mode": args.mode, "rows": len(rows), "categories": measure(rows)}
    args.target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.target}  ({len(rows)} rows)")
    for category, entry in payload["categories"].items():
        alpha = entry["krippendorff_alpha"]
        print(
            f"  {category:34s} units {entry['units']:5d}  present "
            f"{entry['present_rate']}  alpha {alpha}  missing {entry['verdicts_missing']}"
        )


if __name__ == "__main__":
    main()
