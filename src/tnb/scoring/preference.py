"""Does a judge score its own family higher than a neutral one would?

Two of the models on this leaderboard are also the two judging it —
`gemini-3.1-pro-preview` and `gpt-5.6-terra` both write notes here. A model
asked to grade text tends to grade its own output higher than a neutral rater
would, and that would inflate exactly the two systems a reader is most curious
about.

The obvious fix, each judge scoring only the other family, was rejected: it puts
two instruments with two calibrations in one column and leaves every system with
a single score and nothing to check it against. Instead both judges score
everything, and the difference between their tables **measures** the effect
rather than leaving it as a caveat.

For a system *s*, let ``d(s) = score_A(s) - score_B(s)``. If neither judge
favours anybody, ``d`` is the same for every system up to noise: it is just the
constant gap between two instruments of different strictness. Self-preference
shows up as ``d`` being systematically larger for A's own family than for
everyone else, which is a difference of differences:

    effect(A) = mean over A's family of d  -  mean over the *neutral* systems of d

That subtraction is what removes the strictness gap, so what is left is the
part attributable to whose notes are being graded.

**Neutral, not "everyone else".** With two judges there is only one difference
`d`, and it is antisymmetric, so the two effects are not independently
identified if each is measured against everything that is not its own family:
A's comparison group would then contain B's family, and B favouring its own
would show up as A favouring its own. Written out, with A favouring Gemini by
*x* and B favouring GPT by *y*, that estimator returns `x + y/2` for A. Taking
the comparison group to be the systems **neither judge wrote** returns *x*, and
the two effects can be read separately. It also means the panel needs at least
one neutral system to say anything at all, which it refuses to do otherwise.

The interval comes from a
paired bootstrap over **conversations**, not over systems: a hard conversation
is hard for every system, and resampling conversations together keeps that where
it belongs.

A number here is not proof of a mechanism. It says the two judges disagree about
one family more than about the others, which is what a reader needs before
believing either table.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

BOOTSTRAP_SAMPLES = 2000
#: Fixed, so the published interval is reproducible from the same rows.
BOOTSTRAP_SEED = 20260825

#: An effect smaller than this is reported as none. Completeness is a 0-1
#: fraction and the leaderboard already tells readers that small differences
#: between adjacent models are noise; half a point of it is well inside that.
#:
#: It also stops floating-point residue being published as a finding, which is
#: not hypothetical: two judges that agreed exactly produced an interval of
#: [-4.2e-17, -4.2e-17], which excludes zero and would have read as a detected
#: bias 15 orders of magnitude below anything measurable.
NEGLIGIBLE = 0.005

#: Which vendor a system belongs to, for "its own family". Matched on the model
#: id because that is what a row carries; the provider is not enough, since
#: e-INFRA serves models from half a dozen labs.
FAMILY_PREFIXES = {
    "gemini": ("gemini", "google/gemini", "google_gemini"),
    "gpt-5.6": ("gpt-5.6",),
}


def family_of(system_id: str) -> str | None:
    """The vendor family of a system, or None when it belongs to neither judge."""
    name = system_id.lower()
    for family, prefixes in FAMILY_PREFIXES.items():
        if any(name.startswith(prefix) for prefix in prefixes):
            return family
    return None


def family_of_judge(judge_model: str) -> str | None:
    return family_of(judge_model)


@dataclass(frozen=True)
class Effect:
    """One judge's self-preference, in the units of the measure."""

    judge: str
    family: str
    #: Mean difference for the judge's own family, and for everyone else.
    own: float
    others: float
    estimate: float
    low: float
    high: float
    n_own: int
    n_others: int
    n_sessions: int

    #: Systems neither judge's family wrote, which is what the effect is
    #: measured against.
    n_neutral: int = 0

    @property
    def detected(self) -> bool:
        """Whether the interval clears zero by more than a negligible amount.

        False is a real answer and is published as one: "not detected in this
        data" is not "absent", only that a run this size could not see it.
        """
        return self.low > NEGLIGIBLE or self.high < -NEGLIGIBLE


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def compare(
    by_judge: dict[str, dict[str, dict[str, float]]],
    *,
    judge_a: str,
    judge_b: str,
    samples: int = BOOTSTRAP_SAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> list[Effect]:
    """Estimate each judge's self-preference from two judges' per-session scores.

    ``by_judge`` is ``{judge_model: {system_id: {session_id: score}}}`` — the
    individual judgements, not the averages, because the bootstrap resamples
    conversations.

    Returns one `Effect` per judge that has a family among the systems, and an
    empty list when neither does — which is the honest output for a panel of
    judges that wrote none of the notes.
    """
    scores_a = by_judge.get(judge_a) or {}
    scores_b = by_judge.get(judge_b) or {}

    systems = sorted(set(scores_a) & set(scores_b))
    if len(systems) < 2:
        return []

    # Only conversations every system was scored on by both judges: a difference
    # taken over two different session sets is not a difference.
    shared = sorted(set.intersection(*(set(scores_a[s]) & set(scores_b[s]) for s in systems)))
    if len(shared) < 2:
        return []

    effects = []
    for judge_model in (judge_a, judge_b):
        family = family_of_judge(judge_model)
        if family is None:
            continue
        own = [s for s in systems if family_of(s) == family]
        # Systems neither judge wrote. Not "everyone else": including the other
        # judge's family makes the two effects inseparable -- see the module
        # docstring for the arithmetic.
        neutral = [s for s in systems if family_of(s) is None]
        if not own or not neutral:
            continue

        def difference(system: str, sessions: list[str]) -> float:
            """Mean of score_A - score_B for one system over these conversations."""
            return _mean([scores_a[system][x] - scores_b[system][x] for x in sessions])

        def estimate(sessions: list[str], own=own, neutral=neutral) -> float:
            return _mean([difference(s, sessions) for s in own]) - _mean(
                [difference(s, sessions) for s in neutral]
            )

        # A's effect is measured on d = A - B; B's is the same quantity with the
        # sign flipped, because d is antisymmetric in the two judges.
        sign = 1.0 if judge_model == judge_a else -1.0
        point = sign * estimate(shared)

        rng = random.Random(seed)
        draws = []
        for _ in range(samples):
            picked = [shared[rng.randrange(len(shared))] for _ in shared]
            draws.append(sign * estimate(picked))
        draws.sort()

        effects.append(
            Effect(
                judge=judge_model,
                family=family,
                own=sign * _mean([difference(s, shared) for s in own]),
                others=sign * _mean([difference(s, shared) for s in neutral]),
                estimate=point,
                low=draws[int(0.025 * samples)],
                high=draws[int(0.975 * samples) - 1],
                n_own=len(own),
                n_others=len(neutral),
                n_neutral=len(neutral),
                n_sessions=len(shared),
            )
        )
    return effects


def describe(effect: Effect, measure: str = "completeness") -> str:
    """One sentence a reader can act on, whichever way it came out."""
    if not effect.detected:
        return (
            f"`{effect.judge}` shows no detectable preference for its own family: "
            f"{effect.estimate:+.3f} {measure} "
            f"[{effect.low:+.3f} to {effect.high:+.3f}], an interval that includes "
            f"zero, or is smaller than {NEGLIGIBLE:g}. Not detected is not the same as "
            f"absent — {effect.n_own} system(s) against {effect.n_neutral} neutral one(s) "
            f"over {effect.n_sessions} conversations is what this run could see."
        )
    direction = "higher" if effect.estimate > 0 else "lower"
    return (
        f"`{effect.judge}` scores its own family {abs(effect.estimate):.3f} {measure} "
        f"{direction} than the other judge does, relative to how the two differ on "
        f"the {effect.n_neutral} systems neither of them wrote "
        f"[{effect.low:+.3f} to {effect.high:+.3f}]. Read its column "
        f"for a {effect.family} model with that in mind."
    )
