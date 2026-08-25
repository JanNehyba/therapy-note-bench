"""Do the two judges agree about who is better, and where do they not?

The leaderboard's own rule is that rows scored by different judges never share
a table, so the page draws two tables and a reader is left to compare them by
eye. That comparison is the most important thing on the page and the hardest to
do by eye: measured over the first full pass, the two judges agreed on the
*shape* of the ranking -- Spearman 0.889 on completeness -- and still moved 13
of 19 models. The top and the bottom held; the middle did not.

So this computes three things a reader cannot get from two tables side by side.

**How much the ranking agrees, per measure.** One rho each, because they do not
agree equally: a measure the two judges rank the same way supports "9th versus
10th" and a measure they do not, does not.

**How far each system moved.** A rho near 1 with one system moving six places
means something different from one where everybody moved one place, and the
statistic alone cannot tell them apart.

**Who is unambiguously better than whom.** A system that beats another on every
measure under *both* judges is better without any weighting -- and weighting the
measures is a clinical decision, not a measurement. That gives an honest answer
to "which model writes the best notes" for the pairs where one exists, and an
honest "nobody has shown it" for the rest, which is most of them.

Nothing here weights the measures against each other or produces a combined
score. That is the point.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tnb import judge
from tnb.results import Row
from tnb.scoring.calibration import spearman

#: A gap below this is not a difference in the units the leaderboard prints.
#: Completeness is published to three decimals and faithfulness to two, so two
#: systems whose scores round to the same printed number must not be ranked
#: against each other by digits the reader cannot see.
TIES_WITHIN = 0.0005


@dataclass(frozen=True)
class MeasureAgreement:
    """How the two judges' orderings compare on one measure."""

    measure: str
    rho: float | None
    n_systems: int
    #: Systems whose position differs between the two tables.
    moved: int
    #: The system that moved furthest, with its two positions (1-based).
    furthest: tuple[str, int, int] | None = None

    @property
    def stable(self) -> int:
        return self.n_systems - self.moved


@dataclass(frozen=True)
class Dominance:
    """One system that is better than another with no weighting required."""

    system: str
    beats: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Comparison:
    """Everything two judges' tables say when read together."""

    judge_a: str
    judge_b: str
    measures: list[MeasureAgreement]
    dominance: list[Dominance]
    #: Systems no other system beats on every measure under both judges. Not a
    #: winners' list: it includes everything nobody has separated from the rest.
    undominated: list[str]
    n_systems: int

    @property
    def any_ranking_support(self) -> bool:
        return any(m.rho is not None for m in self.measures)


def _scores_by_judge(rows: list[Row], track: str) -> dict[str, dict[str, dict[str, float]]]:
    """{judge: {system: {measure: value}}} for the scored rows of one track."""
    out: dict[str, dict[str, dict[str, float]]] = {}
    for row in rows:
        if row.track != track or not row.is_scored or not row.judge_model:
            continue
        label = row.system_label or row.system_id
        out.setdefault(row.judge_model, {})[label] = dict(row.metrics.headline)
    return out


def _positions(scores: dict[str, dict[str, float]], measure: str) -> dict[str, int]:
    """1-based rank per system, best first, ties sharing the better position."""
    have = [(system, values[measure]) for system, values in scores.items() if measure in values]
    have.sort(key=lambda pair: (-pair[1], pair[0]))

    positions: dict[str, int] = {}
    for index, (system, value) in enumerate(have):
        if index and abs(value - have[index - 1][1]) <= TIES_WITHIN:
            positions[system] = positions[have[index - 1][0]]
        else:
            positions[system] = index + 1
    return positions


def _dominates(
    better: str, worse: str, by_judge: dict[str, dict[str, dict[str, float]]], measures: list[str]
) -> bool:
    """Whether `better` is at least as good on every measure under every judge.

    "At least as good" plus "strictly better somewhere", which is what makes the
    claim survive any weighting a reader might apply. A measure missing for
    either system under either judge makes the comparison unavailable rather
    than favourable: an absent number is not a low one.
    """
    strictly_better_somewhere = False
    for scores in by_judge.values():
        for measure in measures:
            first = scores.get(better, {}).get(measure)
            second = scores.get(worse, {}).get(measure)
            if first is None or second is None:
                return False
            if first < second - TIES_WITHIN:
                return False
            if first > second + TIES_WITHIN:
                strictly_better_somewhere = True
    return strictly_better_somewhere


def compare(
    rows: list[Row],
    track: str,
    measures: list[str],
    *,
    judge_a: str = judge.DEFAULT_MODEL,
    judge_b: str = judge.SECOND_JUDGE,
) -> Comparison | None:
    """Read the panel's two judges' tables together, or None if either is absent.

    Named rather than "whichever two are present". `results/` also holds rows
    from judges that were tried and not chosen -- `gemini-2.5-pro` scored a full
    pass during calibration -- and picking a pair out of three by whatever order
    they came back in would be a choice made silently. The panel is declared in
    `tnb.judge`; this reports on the panel.
    """
    by_judge = _scores_by_judge(rows, track)
    if judge_a not in by_judge or judge_b not in by_judge:
        return None
    by_judge = {judge_a: by_judge[judge_a], judge_b: by_judge[judge_b]}

    shared = sorted(set(by_judge[judge_a]) & set(by_judge[judge_b]))
    if len(shared) < 2:
        return None

    agreements = []
    for measure in measures:
        first = [by_judge[judge_a][s].get(measure) for s in shared]
        second = [by_judge[judge_b][s].get(measure) for s in shared]
        pairs = [
            (a, b) for a, b in zip(first, second, strict=True) if a is not None and b is not None
        ]
        if len(pairs) < 2:
            continue

        rank_a = _positions(by_judge[judge_a], measure)
        rank_b = _positions(by_judge[judge_b], measure)
        both = [s for s in shared if s in rank_a and s in rank_b]
        moves = {s: abs(rank_a[s] - rank_b[s]) for s in both}
        furthest = max(moves, key=lambda s: (moves[s], s)) if moves else None

        agreements.append(
            MeasureAgreement(
                measure=measure,
                rho=spearman([a for a, _ in pairs], [b for _, b in pairs]),
                n_systems=len(both),
                moved=sum(1 for distance in moves.values() if distance),
                furthest=(
                    (furthest, rank_a[furthest], rank_b[furthest])
                    if furthest and moves[furthest]
                    else None
                ),
            )
        )

    dominance = []
    dominated = set()
    for better in shared:
        beats = [w for w in shared if w != better and _dominates(better, w, by_judge, measures)]
        dominated.update(beats)
        if beats:
            dominance.append(Dominance(system=better, beats=sorted(beats)))

    return Comparison(
        judge_a=judge_a,
        judge_b=judge_b,
        measures=agreements,
        dominance=sorted(dominance, key=lambda d: (-len(d.beats), d.system)),
        undominated=sorted(set(shared) - dominated),
        n_systems=len(shared),
    )


def describe(comparison: Comparison) -> str:
    """One paragraph a reader can act on, whichever way the numbers came out."""
    parts = []
    ranked = [m for m in comparison.measures if m.rho is not None]
    if ranked:
        # Named per measure rather than as one worst-case number: they do not
        # agree equally, and "17 of 19 moved" attached to the ranking measure
        # would be a different and false claim.
        best = max(ranked, key=lambda m: m.rho)
        worst = min(ranked, key=lambda m: m.rho)
        parts.append(
            f"`{comparison.judge_a}` and `{comparison.judge_b}` agree on the shape of the "
            f"ranking on {best.measure} ({best.rho:+.3f}) and place {best.moved} of "
            f"{best.n_systems} systems differently on it anyway. They agree least on "
            f"{worst.measure} ({worst.rho:+.3f}, {worst.moved} of {worst.n_systems} moved). "
            f"The tables can say who is near the top and who is near the bottom. "
            f"They cannot say who is ninth and who is tenth."
        )

    if comparison.dominance:
        leader = comparison.dominance[0]
        parts.append(
            f"{len(comparison.dominance)} system(s) beat at least one other on every measure "
            f"under both judges, which needs no weighting to be true: `{leader.system}` beats "
            f"{len(leader.beats)}."
        )
    parts.append(
        f"{len(comparison.undominated)} of {comparison.n_systems} systems are beaten outright "
        f"by nobody. That is a result too, and it is the reason this page does not name a "
        f"single winner."
    )
    return " ".join(parts)


def to_json(comparison: Comparison | None) -> dict | None:
    """The shape the page reads."""
    if comparison is None:
        return None
    return {
        "judge_a": comparison.judge_a,
        "judge_b": comparison.judge_b,
        "n_systems": comparison.n_systems,
        "summary": describe(comparison),
        "measures": [
            {
                "measure": m.measure,
                "rho": None if m.rho is None else round(m.rho, 4),
                "n_systems": m.n_systems,
                "moved": m.moved,
                "stable": m.stable,
                "furthest": (
                    None
                    if m.furthest is None
                    else {"system": m.furthest[0], "rank_a": m.furthest[1], "rank_b": m.furthest[2]}
                ),
            }
            for m in comparison.measures
        ],
        "dominance": [{"system": d.system, "beats": d.beats} for d in comparison.dominance],
        "undominated": comparison.undominated,
    }
