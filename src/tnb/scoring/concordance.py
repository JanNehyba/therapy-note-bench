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

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

from tnb import judge
from tnb.results import Row
from tnb.scoring.calibration import spearman


def as_printed(value: float, decimals: int) -> str:
    """The number as the table shows it. The unit every claim here is made in.

    This replaced a fixed tolerance of 0.0005. That number was chosen for a
    three-decimal column, and it failed at both ends. Faithfulness prints two
    decimals, where half a digit is 0.005, so `glm-5` 4.96 and `gpt-5.6-sol`
    4.955 print the same and were ranked against each other -- fifteen such
    pairs across the tables. And raising it would not have fixed it: 0.9742 and
    0.9735 are 0.0007 apart, *above* any three-decimal tolerance, and both
    print 0.974.

    Printed equality is also transitive, which a tolerance is not. Three
    systems each a fifth of a digit from the next used to be one tie though the
    ends were further apart than the tolerance allowed.
    """
    return f"{value:.{decimals}f}"


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

    #: How many systems print the same value as each other, counted on the
    #: judge where the tie is worst. A measure has to tell the systems apart
    #: before an agreement about its ordering means anything.
    tied: int = 0

    @property
    def stable(self) -> int:
        return self.n_systems - self.moved

    @property
    def rankable(self) -> bool:
        """Whether this measure orders the systems at all.

        `organized` gives 5.00 to eighteen of nineteen systems under both
        judges. Spearman over that is +1.000 and the page said the judges
        "agree on the shape of the ranking" -- a claim decided by the single
        system that was not at the ceiling. It is the same defect the
        `judge_measures` filter above was written for, arriving by the other
        road: there the correlation was a tautology, here it is a coin.

        Half is the line. A measure on which most systems are indistinguishable
        cannot order them, whatever the remainder does.
        """
        return self.n_systems >= 2 and self.tied * 2 <= self.n_systems


@dataclass(frozen=True)
class Dominance:
    """One system that is better than another with no weighting required."""

    system: str
    beats: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Tension:
    """Two measures, and how much the ranking on one predicts the other."""

    first: str
    second: str
    #: One per judge, so a near-zero correlation cannot be blamed on one of them.
    rho_by_judge: dict[str, float | None]
    n_systems: int
    #: The worst tie either column carries, on the judge where it is worst.
    #: `MeasureAgreement` has had this since a measure that gives 5.00 to
    #: eighteen of nineteen systems was reported as the two judges agreeing
    #: perfectly about its ordering. The same defect lived on in this table for
    #: as long again: the panel printed "no agreement figure is given for
    #: organized (18 of 19 share one value)" and then, one table lower, printed
    #: `useful` against `organized` at rho 1.000. The guard was written once
    #: and applied to one of the two places that needed it.
    tied: int = 0

    @property
    def rankable(self) -> bool:
        """Whether both columns order the systems at all. Same line as above."""
        return self.n_systems >= 2 and self.tied * 2 <= self.n_systems

    @property
    def agrees(self) -> bool:
        """Whether the two columns move together, in either direction.

        Magnitude, not value. `trace` against `temporal_past` is -0.411 and
        -0.472: both judges find a moderate inverse relation, and the page's
        verdict column called it "not related" -- denying a relationship it had
        just measured, because the test read the sign as weakness.
        """
        found = [rho for rho in self.rho_by_judge.values() if rho is not None]
        if not found or not self.rankable:
            return False
        if not all(abs(rho) >= 0.5 for rho in found):
            return False
        # And in the same direction. A first draft asked only for magnitude and
        # swallowed the case this panel exists for: +1.000 under one judge and
        # -1.000 under the other is the two judges reading the same pair of
        # columns in opposite directions, which is maximal disagreement and was
        # about to be printed as "related".
        return all(rho > 0 for rho in found) or all(rho < 0 for rho in found)

    @property
    def inverse(self) -> bool:
        """Whether the relation they agree on runs the other way."""
        found = [rho for rho in self.rho_by_judge.values() if rho is not None]
        return bool(found) and all(rho <= -0.5 for rho in found)


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
    #: Every system the comparison was made over: both judges scored it, so its
    #: dominance count is a measurement. A system outside this list has no count
    #: at all, and the difference matters -- a system that beats nobody and a
    #: system nobody could compare must not print the same digit. Derivable from
    #: `undominated` and the `beats` lists, and published rather than derived
    #: because a reader of the page should not have to prove that identity, and
    #: because the day it stops holding the page would silently print zero for
    #: an absence.
    systems: list[str] = field(default_factory=list)
    #: How the measures relate to each other, which is a different question from
    #: how the judges relate to each other and just as necessary before reading
    #: the ranking column as "the best model".
    tensions: list[Tension] = field(default_factory=list)
    #: Which of `measures` a judge actually decides -- the ones the agreement
    #: figures above are computed over.
    judge_measures: tuple[str, ...] = ()
    #: The column the table is ordered by, if it has one. Named so the summary
    #: can report the tensions involving it rather than the numerically most
    #: extreme pair, which is often one nobody is reading as a ranking.
    ranking_measure: str | None = None

    @property
    def any_ranking_support(self) -> bool:
        return any(m.rho is not None for m in self.measures)


def _scores_by_judge(rows: list[Row], track: str) -> dict[str, dict[str, dict[str, float]]]:
    """{judge: {system: {measure: value}}} for the scored rows of one track.

    Raises rather than overwriting when one system appears twice under one
    judge. That is not a hypothetical: `results/` holds every iCARE system at
    two harness versions, and a dictionary keyed on the system would keep
    whichever came last -- comparing one judge's new ROUGE-L with the other's
    old one and calling the difference a disagreement. Callers pass
    `report.current_rows`, which resolves it; anything that does not, fails
    here rather than quietly.
    """
    out: dict[str, dict[str, dict[str, float]]] = {}
    for row in rows:
        if row.track != track or not row.is_scored or not row.judge_model:
            continue
        label = row.system_label or row.system_id
        seen = out.setdefault(row.judge_model, {})
        if label in seen:
            raise ValueError(
                f"{label!r} appears twice for judge {row.judge_model!r} on {track!r}. "
                f"Pass rows through `report.current_rows` first: two harness versions "
                f"are two definitions of the same measure."
            )
        seen[label] = dict(row.metrics.headline)
    return out


def _largest_tie(
    scores: dict[str, dict[str, float]], measure: str, systems: list[str], decimals: int
) -> int:
    """How many systems print the same value as each other on this measure.

    Counted on the printed value, like `_positions` and for the same reason: a
    reader who cannot tell two numbers apart in the table cannot tell the two
    systems apart, whatever the stored floats do.
    """
    printed = Counter(
        as_printed(scores[s][measure], decimals) for s in systems if measure in scores.get(s, {})
    )
    return max(printed.values(), default=0)


def _positions(
    scores: dict[str, dict[str, float]], measure: str, systems: list[str], decimals: int
) -> dict[str, int]:
    """1-based rank per system, best first, ties sharing the better position.

    Over `systems` and nothing else, so both judges rank the same field. Ranking
    each judge's whole table would compare a position out of nineteen with a
    position out of sixteen and report the difference as movement -- and a
    judge part-way through a run has a smaller table, so the error would grow
    exactly when a reader is most likely to be watching.

    Two systems share a position when they print the same number. Every claim
    this panel makes is one a reader checks against the table, so the table's
    own precision is the unit it has to be made in.
    """
    have = [(s, scores[s][measure]) for s in systems if measure in scores.get(s, {})]
    have.sort(key=lambda pair: (-pair[1], pair[0]))

    positions: dict[str, int] = {}
    for index, (system, value) in enumerate(have):
        if index and as_printed(value, decimals) == as_printed(have[index - 1][1], decimals):
            positions[system] = positions[have[index - 1][0]]
        else:
            positions[system] = index + 1
    return positions


def _dominates(
    better: str,
    worse: str,
    by_judge: dict[str, dict[str, dict[str, float]]],
    decimals: dict[str, int],
) -> bool:
    """Whether `better` is at least as good on every measure under every judge.

    "At least as good" plus "strictly better somewhere", which is what makes the
    claim survive any weighting a reader might apply. A measure missing for
    either system under either judge makes the comparison unavailable rather
    than favourable: an absent number is not a low one.

    **Compared as stored, not as printed, and the difference is not academic.**
    It was printed until 2026-09-01, for the reason `_positions` still is: a
    reader checking a claim about the table sees the digits and nothing else.
    That reason does not survive contact with what rounding does *here*.
    Dominance asks for "at least as good on every column", so rounding a narrow
    **loss** into a tie removes an obstacle and lets the claim through --
    rounding manufactures dominance rather than withholding it, which is the
    one direction this repository may not err in. It fired once on the
    published rows: `gemini-3.1-pro-preview` beat `glm-5.2` outright on the
    strength of a 0.0029 faithfulness gap in `glm-5.2`'s favour that printed as
    4.97 against 4.97. And the verifiability the printed form was chosen for
    fails exactly there: a reader sees two equal figures, concludes a tie, and
    is told one beats the other.

    So the comparison is on the stored values, and two rows printing the same
    figure may still not tie. The page says so where the count is defined.
    Cost of the change, measured before it was made: one claim of the thirty on
    the rubric, none of the eleven on PDSQI-9, and `undominated` -- which the
    published "eight of the nineteen" comes from -- identical either way.

    `_positions` keeps the printed comparison, and should: a shared *place* in
    a ranking is a statement about the column as drawn, and two rows printing
    the same figure share it.
    """
    strictly_better_somewhere = False
    for scores in by_judge.values():
        for measure in decimals:
            first = scores.get(better, {}).get(measure)
            second = scores.get(worse, {}).get(measure)
            if first is None or second is None:
                return False
            if first < second:
                return False
            if first > second:
                strictly_better_somewhere = True
    return strictly_better_somewhere


def compare(
    rows: list[Row],
    track: str,
    measures: Sequence[tuple[str, int]],
    *,
    judge_a: str = judge.DEFAULT_MODEL,
    judge_b: str = judge.SECOND_JUDGE,
    judge_measures: tuple[str, ...] | None = None,
    ranking_measure: str | None = None,
) -> Comparison | None:
    """Read the panel's two judges' tables together, or None if either is absent.

    Named rather than "whichever two are present". `results/` also holds rows
    from judges that were tried and not chosen -- `gemini-2.5-pro` scored a full
    pass during calibration -- and picking a pair out of three by whatever order
    they came back in would be a choice made silently. The panel is declared in
    `tnb.judge`; this reports on the panel.
    """
    #: Each measure with the number of decimals the table prints it to. Passed
    #: in rather than looked up: `report.COLUMNS` owns the precision, and a
    #: second copy of it here would be a second thing to keep in step.
    places = dict(measures)
    measures = [name for name, _ in measures]

    by_judge = _scores_by_judge(rows, track)
    if judge_a not in by_judge or judge_b not in by_judge:
        return None
    by_judge = {judge_a: by_judge[judge_a], judge_b: by_judge[judge_b]}

    shared = sorted(set(by_judge[judge_a]) & set(by_judge[judge_b]))
    if len(shared) < 2:
        return None

    # Rank agreement is asked only of measures a judge decides. On the iCARE
    # track ROUGE-L, BERTScore and the two temporal columns come from the note
    # and the expert note alone, so they are identical under every judge:
    # reporting a correlation of 1.000 there would dress a tautology as a
    # finding. The tensions and the dominance below use every measure, because
    # those are questions about the columns and the models rather than about
    # the judges.
    compared = [m for m in measures if judge_measures is None or m in judge_measures]

    agreements = []
    for measure in compared:
        first = [by_judge[judge_a][s].get(measure) for s in shared]
        second = [by_judge[judge_b][s].get(measure) for s in shared]
        pairs = [
            (a, b) for a, b in zip(first, second, strict=True) if a is not None and b is not None
        ]
        if len(pairs) < 2:
            continue

        rank_a = _positions(by_judge[judge_a], measure, shared, places[measure])
        rank_b = _positions(by_judge[judge_b], measure, shared, places[measure])
        tied = max(
            _largest_tie(by_judge[judge_a], measure, shared, places[measure]),
            _largest_tie(by_judge[judge_b], measure, shared, places[measure]),
        )
        both = [s for s in shared if s in rank_a and s in rank_b]
        moves = {s: abs(rank_a[s] - rank_b[s]) for s in both}
        furthest = max(moves, key=lambda s: (moves[s], s)) if moves else None

        agreements.append(
            MeasureAgreement(
                measure=measure,
                rho=spearman([a for a, _ in pairs], [b for _, b in pairs]),
                n_systems=len(both),
                moved=sum(1 for distance in moves.values() if distance),
                tied=tied,
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
        beats = [w for w in shared if w != better and _dominates(better, w, by_judge, places)]
        dominated.update(beats)
        if beats:
            dominance.append(Dominance(system=better, beats=sorted(beats)))

    tensions = []
    for index, first in enumerate(measures):
        for second in measures[index + 1 :]:
            rho_by_judge: dict[str, float | None] = {}
            counted = 0
            for judge_model, scores in by_judge.items():
                pairs = [
                    (scores[s][first], scores[s][second])
                    for s in shared
                    if first in scores.get(s, {}) and second in scores.get(s, {})
                ]
                counted = max(counted, len(pairs))
                rho_by_judge[judge_model] = (
                    spearman([a for a, _ in pairs], [b for _, b in pairs])
                    if len(pairs) >= 2
                    else None
                )
            # The tie is a property of the columns, so it is read from the
            # judge where it is worst, exactly as `MeasureAgreement` reads it.
            tied = max(
                (
                    _largest_tie(scores, measure, shared, places[measure])
                    for scores in by_judge.values()
                    for measure in (first, second)
                ),
                default=0,
            )
            if any(rho is not None for rho in rho_by_judge.values()):
                tensions.append(
                    Tension(
                        first=first,
                        second=second,
                        rho_by_judge=rho_by_judge,
                        n_systems=counted,
                        tied=tied,
                    )
                )

    return Comparison(
        judge_a=judge_a,
        judge_b=judge_b,
        tensions=tensions,
        judge_measures=tuple(compared),
        ranking_measure=ranking_measure,
        measures=agreements,
        dominance=sorted(dominance, key=lambda d: (-len(d.beats), d.system)),
        undominated=sorted(set(shared) - dominated),
        n_systems=len(shared),
        systems=list(shared),
    )


def describe(comparison: Comparison) -> str:
    """One paragraph a reader can act on, whichever way the numbers came out."""
    parts = []
    # A measure that gives most systems the same number cannot order them, and
    # a correlation between two such orderings is decided by the handful that
    # differ. `organized` was published as "+1.000, agree on the shape of the
    # ranking" off eighteen of nineteen systems sitting on 5.00.
    unrankable = [m for m in comparison.measures if m.rho is not None and not m.rankable]
    ranked = [m for m in comparison.measures if m.rho is not None and m.rankable]
    if ranked:
        # Named per measure rather than as one worst-case number: they do not
        # agree equally, and "17 of 19 moved" attached to the ranking measure
        # would be a different and false claim.
        best = max(ranked, key=lambda m: m.rho)
        worst = min(ranked, key=lambda m: m.rho)
        parts.append(
            f"`{comparison.judge_a}` and `{comparison.judge_b}` agree on the shape of the "
            f"ranking on {best.measure} ({best.rho:+.3f}) and place {best.moved} of "
            f"{best.n_systems} systems differently on it anyway."
        )
        # Only when there is a second measure to be worst. With one -- the iCARE
        # track, where TRACE is the only thing a judge decides -- naming the same
        # measure twice reads as two findings and is one.
        if worst is not best:
            parts.append(
                f"They agree least on {worst.measure} ({worst.rho:+.3f}, {worst.moved} "
                f"of {worst.n_systems} moved)."
            )
        parts.append(
            "The tables can say who is near the top and who is near the bottom. "
            "They cannot say who is ninth and who is tenth."
        )

    if unrankable:
        named = ", ".join(
            f"{m.measure} ({m.tied} of {m.n_systems} share one value)"
            for m in sorted(unrankable, key=lambda m: m.measure)
        )
        one = len(unrankable) == 1
        parts.append(
            f"No agreement figure is given for {named}: most systems print the same "
            f"number there, so there {'is no ordering' if one else 'are no orderings'} "
            f"for the two judges to agree about, and a correlation over "
            f"{'it' if one else 'them'} would be decided by the few that differ."
        )

    if comparison.dominance:
        # Every system at the top, not the first one after an alphabetical
        # tie-break. Until 2026-09-01 this printed "`gpt-5.6-sol` beats 6" on
        # the iCARE track while `qwen3.8-27b` also beat 6 -- a page whose whole
        # argument is that no single winner can be named, naming one, and
        # picking it by the letter it starts with. Nothing revealed it: the
        # sentence is true of the system it names, and the one it leaves out
        # leaves no trace.
        most = len(comparison.dominance[0].beats)
        leaders = [d.system for d in comparison.dominance if len(d.beats) == most]
        named = ", ".join(f"`{system}`" for system in leaders)
        parts.append(
            f"Systems beating at least one other on every measure under both judges, which "
            f"needs no weighting to be true: {len(comparison.dominance)}. "
            + (
                f"{named} beats {most}."
                if len(leaders) == 1
                else f"The most any of them beats is {most}, and {len(leaders)} do: {named}."
            )
        )
    parts.append(
        f"{len(comparison.undominated)} of {comparison.n_systems} systems are beaten outright "
        f"by nobody."
    )

    # The reason there is no single winner, stated as the measurement rather
    # than as a policy. Reported for the column the table is *ordered by*,
    # because that is the one a reader is most likely to mistake for "quality".
    if comparison.ranking_measure:
        # Both the pairs that say nothing and the pairs that say the opposite.
        # A strongly inverse pair used to land in the first list and be
        # described as "says little", which is the sign read as weakness; with
        # that fixed it would have fallen out of the summary altogether, and a
        # trade-off between the ordering column and another is the finding this
        # whole panel exists to report -- a model that answers every question
        # satisfies more criteria and invents more.
        against = [
            t
            for t in comparison.tensions
            if comparison.ranking_measure in (t.first, t.second)
            and t.rankable
            and (not t.agrees or t.inverse)
        ]
        for tension in against:
            other = tension.second if tension.first == comparison.ranking_measure else tension.first
            readings = ", ".join(
                f"`{judge_model}` {'--' if rho is None else format(rho, '+.2f')}"
                for judge_model, rho in sorted(tension.rho_by_judge.items())
            )
            # Whether the judges even agree that the two columns disagree is
            # itself a finding, and picking the judge that tells the better
            # story would be the thing this repository exists not to do.
            found = [rho for rho in tension.rho_by_judge.values() if rho is not None]
            split = len(found) > 1 and max(found) - min(found) >= 0.4
            if tension.inverse:
                parts.append(
                    f"Ordering by {comparison.ranking_measure} orders {other} in reverse "
                    f"({readings}): the two are a trade-off, and collapsing them into one "
                    "number means deciding which of them matters."
                )
                continue
            parts.append(
                f"Ordering by {comparison.ranking_measure} says "
                f"{'little' if not split else 'different things to the two judges'} about "
                f"{other} ({readings})."
                + (
                    " The two judges disagree about whether those columns are related at "
                    "all, so neither reading is this benchmark's answer."
                    if split
                    else ""
                )
            )
    return " ".join(parts)


def to_json(comparison: Comparison | None) -> dict | None:
    """The shape the page reads."""
    if comparison is None:
        return None
    return {
        "judge_a": comparison.judge_a,
        "judge_b": comparison.judge_b,
        "ranking_measure": comparison.ranking_measure,
        "judge_measures": list(comparison.judge_measures),
        "n_systems": comparison.n_systems,
        "summary": describe(comparison),
        "measures": [
            {
                "measure": m.measure,
                "rho": None if m.rho is None else round(m.rho, 4),
                "n_systems": m.n_systems,
                "moved": m.moved,
                "stable": m.stable,
                "tied": m.tied,
                "rankable": m.rankable,
                "furthest": (
                    None
                    if m.furthest is None
                    else {"system": m.furthest[0], "rank_a": m.furthest[1], "rank_b": m.furthest[2]}
                ),
            }
            for m in comparison.measures
        ],
        "tensions": [
            {
                "first": t.first,
                "second": t.second,
                "n_systems": t.n_systems,
                "agrees": t.agrees,
                "inverse": t.inverse,
                "rankable": t.rankable,
                "tied": t.tied,
                "rho_by_judge": {
                    judge_model: None if rho is None else round(rho, 4)
                    for judge_model, rho in sorted(t.rho_by_judge.items())
                },
            }
            for t in comparison.tensions
        ],
        "dominance": [{"system": d.system, "beats": d.beats} for d in comparison.dominance],
        "undominated": comparison.undominated,
        "systems": comparison.systems,
    }
