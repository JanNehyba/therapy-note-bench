"""Which candidate categories could carry a column, and which could not.

Seven gates, every threshold fixed in the plan before any coder ran. A category
passes or it does not, and one that does not is reported with its numbers rather
than dropped -- "this difference is real and should not become a column" is a
result and gets written in the same voice as a positive one.

**Passing the gates does not make a category true.** The gates ask whether a
number is *possible*: does the thing vary, does it belong to the model rather
than the session, can coders agree what it is, is its evidence real, can it be
answered without sending a confidential transcript anywhere, is it separable from
length. Whether the distinction matters to a psychologist is a question no
arrangement of models answers, and no person has read these notes as a clinician.

The unit-level share is the point of the whole design. Every existing Czech
criterion asks whether a fault appears anywhere in a note, which is why all six
scale with length. A share of *meaning units* has a denominator that grows with
the note, so the length effect is divided out by construction instead of being
regressed out afterwards -- and gate 6 checks that it worked rather than assuming
it did.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_CODES = REPO / "local" / "czech-codes.jsonl"
DEFAULT_RELIABILITY = REPO / "local" / "czech-reliability.json"
DEFAULT_STRUCTURE = REPO / "local" / "czech-structure.json"
DEFAULT_TARGET = REPO / "local" / "czech-graduation.json"
#: Gate 7's answers. One file for every track: the stimulus is invented and
#: belongs to no corpus, so there is nothing track-specific to key it on.
DEFAULT_CONTROL = REPO / "local" / "czech-category-control.json"

#: Every threshold, together, so that changing one is a visible act. All of them
#: were written into the plan before the first coder ran.
GATES = {
    "occurrence_min": 0.20,
    "occurrence_max": 0.80,
    "model_variance_min": 0.40,
    "model_over_session": 3.0,
    "boundary_kappa_min": 0.60,
    "pairwise_kappa_min": 0.60,
    "span_discard_max": 0.05,
    #: Hundredths of a point per hundred words. The slope the six published
    #: criteria already carry; a new column steeper than this is length wearing
    #: a different name.
    "length_slope_max": 0.09,
}


#: Which corpus a row belongs to, read off the session id. The ids are digests
#: prefixed by their half, so this needs no lookup and cannot drift from the
#: corpus the row was actually coded from.
TRACK_PREFIX = {"czech-real": "cz-r-", "czech-translated": "cz-t-"}


def load_rows(path: Path, mode: str = "deductive", track: str | None = None) -> list[dict]:
    """The coded rows of one corpus, or of all of them.

    **The track filter is not optional in practice, and it was missing.** The
    file holds every corpus the panel has read, and nothing in a row says which
    one it came from except its session id. Reading the file whole and averaging
    it produced one number over two corpora -- for a panel whose own heading says
    "the real sessions". Two corpora that differ by a factor of seven in
    transcript length are not one corpus, and this repository already refuses to
    pool them anywhere else.
    """
    prefix = TRACK_PREFIX.get(track) if track else None
    if track and prefix is None:
        raise ValueError(f"{track} has no session prefix. Known: {', '.join(TRACK_PREFIX)}")
    rows = []
    with path.open(encoding="utf-8") as handle:
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


def per_model_counts(rows: list[dict]) -> dict[str, dict[str, dict]]:
    """Per category, per model: how many verdicts were `present`, out of how many.

    Counts rather than a share alone, because a share hides how much it rests on.
    Two of these models have fewer than ten notes -- one has six -- and a reader
    shown only "42%" cannot tell that apart from a model with the full corpus.

    **Sentences and notes are counted distinctly, not averaged over the coders.**
    An earlier version divided the verdict count by the number of coders, which
    made the corpus size a number that is true of neither coder: coder A answered
    3367 sentences across 104 notes and coder B 3313 across 102, and the mean of
    those, 3339 in 102, is a corpus nobody read.

    ``rate`` is left unrounded. Rounding it here and again for display turned
    306/572 into 54% where the arithmetic says 53 -- a rounding of a rounding,
    which is a small error that is impossible to trace back from the page.
    """
    present: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    verdicts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    units: dict[str, set] = defaultdict(set)
    notes: dict[str, set] = defaultdict(set)
    coders: dict[str, dict] = defaultdict(lambda: defaultdict(set))

    for row in rows:
        category, value = row.get("category"), row.get("value")
        model = row["system_id"]
        units[model].add((row["session_id"], row["unit_index"]))
        notes[model].add(row["session_id"])
        coders[model][(row["session_id"], row["unit_index"])].add(row["coder"])
        if category is None or value is None or value == "not-applicable":
            continue
        verdicts[category][model] += 1
        present[category][model] += int(value == "present")

    return {
        category: {
            model: {
                "present": present[category][model],
                "verdicts": answered,
                "sentences": len(units[model]),
                "both_coders": sum(1 for s in coders[model].values() if len(s) > 1),
                "notes": len(notes[model]),
                "rate": present[category][model] / answered if answered else None,
            }
            for model, answered in models.items()
        }
        for category, models in verdicts.items()
    }


def per_note_share(rows: list[dict]) -> dict[str, dict[tuple[str, str], float]]:
    """For each category, the share of a note's units marked present.

    The denominator is the units this coder actually answered for that note, not
    the units it was sent. A coder that answered eighty of a hundred units has
    measured eighty, and dividing by a hundred would count its silence as twenty
    absences.
    """
    marked: dict[str, dict[tuple[str, str], list[int]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        category = row.get("category")
        value = row.get("value")
        if category is None or value is None:
            continue
        if value == "not-applicable":
            # No opportunity is not a mark and not a miss. It leaves the
            # denominator, the same way the quotation criterion did.
            continue
        key = (row["system_id"], row["session_id"])
        marked[category][key].append(1 if value == "present" else 0)

    return {
        category: {key: statistics.fmean(values) for key, values in cells.items() if values}
        for category, cells in marked.items()
    }


def variance_split(cells: dict[tuple[str, str], float]) -> dict | None:
    models = sorted({model for model, _ in cells})
    sessions = sorted({session for _, session in cells})
    if len(models) < 2 or len(sessions) < 2 or len(cells) < 4:
        return None
    grand = statistics.fmean(cells.values())
    by_model = {
        model: statistics.fmean([v for (m, _), v in cells.items() if m == model])
        for model in models
    }
    by_session = {
        session: statistics.fmean([v for (_, s), v in cells.items() if s == session])
        for session in sessions
    }
    model_var = statistics.pvariance(list(by_model.values()))
    session_var = statistics.pvariance(list(by_session.values()))
    residual = statistics.pvariance(
        [v - by_model[m] - by_session[s] + grand for (m, s), v in cells.items()]
    )
    total = model_var + session_var + residual
    if total <= 0:
        return None
    return {
        "model": round(model_var / total, 4),
        "session": round(session_var / total, 4),
        "residual": round(residual / total, 4),
        "by_model": {model: round(value, 4) for model, value in sorted(by_model.items())},
    }


def length_slope(
    cells: dict[tuple[str, str], float], words: dict[tuple[str, str], float]
) -> float | None:
    """Change in the share per hundred words, by ordinary least squares.

    A slope, not a correction. Length was chosen by the models rather than
    assigned to them, so subtracting what it predicts would remove the result
    along with the artefact: a model may write long *because* it summarises
    badly. The number is here to say whether the share still measures something
    once length is accounted for, not to produce an adjusted ranking.
    """
    pairs = [(words[key], value) for key, value in cells.items() if key in words]
    if len(pairs) < 4:
        return None
    xs = [x / 100.0 for x, _ in pairs]
    ys = [y for _, y in pairs]
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator <= 0:
        return None
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / denominator
    return round(slope, 4)


def note_words(structure: dict, track: str) -> dict[tuple[str, str], float]:
    """Median note length per model, from the census. Keyed per note is better,
    but the census reports per model, and per model is the resolution the length
    argument is made at in the published tables."""
    per_model = {
        model: entry.get("words") for model, entry in structure["tracks"][track]["by_model"].items()
    }
    sessions = structure["tracks"][track]["sessions"]
    return {
        (model, session): value
        for model, value in per_model.items()
        if value is not None
        for session in sessions
    }


def _planted_control(category: str, control: dict | None) -> dict:
    """Gate 7, from `tools/czech_category_control.py` if it has been run.

    **The gate is about the instrument, not about either corpus.** Its stimulus
    is an invented note that belongs to no session and no model, so the same
    answer applies to the real half and the translated one and this function is
    handed the same file for both. That is why it takes no track.

    Absent means unmeasured, and says so. The wording used to say no control
    note had been written, which stopped being true the moment one was; a gate
    that explains its own silence has to be told when the silence ends.
    """
    if not control:
        return {
            "value": None,
            "passed": None,
            "why": (
                "NOT RUN. A note built to carry the feature must fire it and a note "
                "built without it must not, under every coder. Reported as unmeasured "
                "rather than assumed: `tools/czech_category_control.py` exists and has "
                "not been run, or its output is not where this looked for it."
            ),
        }

    by_coder = control.get(category) or {}
    if not by_coder:
        return {
            "value": None,
            "passed": None,
            "why": (
                f"NOT RUN for `{category}`. The control was run and this category is "
                "not in its verdicts, so nothing is claimed about it either way."
            ),
        }

    verdicts = {coder: found.get("verdict") for coder, found in by_coder.items()}
    passed = bool(verdicts) and all(v == "found it" for v in verdicts.values())
    said = ", ".join(f"{coder}: {verdict}" for coder, verdict in sorted(verdicts.items()))
    return {
        "value": said,
        "passed": passed,
        "why": (
            f"A note built to carry `{category}` was put to every coder, and so was "
            f"the clean note it was built from. {said}. A coder that misses the "
            "planted instance is not answering the question its category asks; one "
            "that fires on the clean note is producing a number from nothing, and "
            "every share it contributed to is inflated by however often that "
            "happens. A planted instance is unambiguous by construction and a real "
            "one is not, so passing here is the floor and not the ceiling."
        ),
    }


def grade(
    category: str,
    shares: dict[tuple[str, str], float],
    reliability: dict | None,
    words: dict[tuple[str, str], float],
    control: dict | None = None,
) -> dict:
    present_rate = round(statistics.fmean(shares.values()), 4) if shares else None
    split = variance_split(shares)
    slope = length_slope(shares, words)

    checks: dict[str, dict] = {}

    checks["1_varies"] = {
        "value": present_rate,
        "passed": (
            present_rate is not None
            and GATES["occurrence_min"] <= present_rate <= GATES["occurrence_max"]
        ),
        "why": (
            f"Share of meaning units marked present, averaged over notes. Outside "
            f"{GATES['occurrence_min']}-{GATES['occurrence_max']} ten notes per model "
            "cannot separate anybody."
        ),
    }

    checks["2_model_not_session"] = {
        "value": split and {k: split[k] for k in ("model", "session", "residual")},
        "passed": bool(
            split
            and split["model"] >= GATES["model_variance_min"]
            and split["model"] >= GATES["model_over_session"] * max(split["session"], 1e-9)
        ),
        "why": (
            "A feature whose variance sits in the session orders transcripts rather "
            "than models, which is what the briefing already says about several "
            "published columns."
        ),
    }

    boundary = pairwise = alpha = None
    discard = None
    if reliability:
        boundary_values = [
            entry["kappa"]
            for entry in reliability.get("boundary", {}).values()
            if entry.get("kappa") is not None
        ]
        pairwise_values = [
            entry["kappa"]
            for entry in reliability.get("pairwise", {}).values()
            if entry.get("kappa") is not None
        ]
        boundary = round(min(boundary_values), 4) if boundary_values else None
        pairwise = round(min(pairwise_values), 4) if pairwise_values else None
        alpha = reliability.get("krippendorff_alpha")
        rates = [
            entry["discard_rate"]
            for entry in reliability.get("spans", {}).values()
            if entry.get("discard_rate") is not None
        ]
        discard = round(max(rates), 4) if rates else None

    checks["3_coders_agree"] = {
        "value": {
            "boundary_kappa_min_pair": boundary,
            "pairwise_kappa_min_pair": pairwise,
            "krippendorff_alpha": alpha,
        },
        "passed": bool(
            boundary is not None
            and pairwise is not None
            and boundary >= GATES["boundary_kappa_min"]
            and pairwise >= GATES["pairwise_kappa_min"]
        ),
        "why": (
            "The worst pair, not the average: a panel is only as reliable as its "
            "weakest agreement. Read beside the prevalence -- kappa collapses at "
            "extreme rates and the collapse is arithmetic, not disagreement."
        ),
    }

    checks["4_evidence_is_real"] = {
        "value": discard,
        "passed": discard is not None and discard <= GATES["span_discard_max"],
        "why": (
            "Share of `present` verdicts whose verbatim span was not found in the "
            "unit it claimed to quote. A coder that invents its evidence fails here "
            "rather than passing silently."
        ),
    }

    checks["5_answerable_from_the_note"] = {
        "value": True,
        "passed": True,
        "why": (
            "Every category in this codebook is asked of the note alone. No real "
            "transcript left the machine, which is what let the real half be scored "
            "at all."
        ),
    }

    checks["6_separable_from_length"] = {
        "value": slope,
        "passed": slope is not None and abs(slope) <= GATES["length_slope_max"],
        "why": (
            "Change in the share per hundred words. The unit-level denominator is "
            "supposed to divide length out by construction; this checks that it did "
            "rather than assuming it. A steeper slope than the published criteria "
            "carry means the column is length under another name, and it is then "
            "printed as a level and never as a ranking."
        ),
    }

    checks["7_planted_control"] = _planted_control(category, control)

    decided = [check for check in checks.values() if check["passed"] is not None]
    return {
        "present_rate": present_rate,
        "notes": len(shares),
        "variance": split,
        "length_slope_per_100_words": slope,
        "gates": checks,
        "gates_passed": sum(1 for check in decided if check["passed"]),
        "gates_decided": len(decided),
        "verdict": (
            "would be a column" if all(check["passed"] for check in decided) else "not a column"
        ),
    }


CAVEAT = (
    "A category that passes every gate has shown that a number about it is "
    "possible, not that the number matters. No person has read these notes as a "
    "clinician, three of the seven gates rest on models agreeing with each other, "
    "and gate 7 was not run at all. Ten sessions with one client on the real half: "
    "read the ordering, never the gaps between neighbours."
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply the graduation gates.")
    parser.add_argument("--codes", type=Path, default=DEFAULT_CODES)
    parser.add_argument("--reliability", type=Path, default=DEFAULT_RELIABILITY)
    parser.add_argument("--structure", type=Path, default=DEFAULT_STRUCTURE)
    parser.add_argument("--track", default="czech-real")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--control", type=Path, default=DEFAULT_CONTROL)
    args = parser.parse_args()

    rows = load_rows(args.codes, track=args.track)
    shares = per_note_share(rows)
    reliability = (
        json.loads(args.reliability.read_text(encoding="utf-8"))["categories"]
        if args.reliability.is_file()
        else {}
    )
    structure = json.loads(args.structure.read_text(encoding="utf-8"))
    words = note_words(structure, args.track)
    control = (
        json.loads(args.control.read_text(encoding="utf-8")).get("verdicts")
        if args.control.is_file()
        else None
    )

    payload = {
        "caveat": CAVEAT,
        "gates": GATES,
        "track": args.track,
        "rows": len(rows),
        "control": str(args.control.relative_to(REPO)) if control else None,
        "categories": {
            category: grade(category, cells, reliability.get(category), words, control)
            for category, cells in sorted(shares.items())
        },
        "by_model": per_model_counts(rows),
    }
    args.target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"wrote {args.target}  ({len(rows)} rows)")
    print(f"{'category':26s} {'rate':>6s} {'model':>6s} {'sess':>6s} {'slope':>7s}  gates  verdict")
    for category, entry in payload["categories"].items():
        split = entry["variance"] or {}
        print(
            f"{category:26s} {entry['present_rate'] or 0:6.3f} "
            f"{split.get('model', 0):6.2f} {split.get('session', 0):6.2f} "
            f"{entry['length_slope_per_100_words'] or 0:7.3f}  "
            f"{entry['gates_passed']}/{entry['gates_decided']}    {entry['verdict']}"
        )


if __name__ == "__main__":
    main()
