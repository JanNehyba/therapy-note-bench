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
#:
#: Keyed on the **vendor**, not on the judge's own name. Keying it on the name
#: put two of the judges' own vendors in the comparison group: `gemma4` is
#: Google's, like the Gemini judge, and `gpt-oss-120b` is OpenAI's, like the
#: GPT judge. Both then pulled the estimate toward zero, and both published
#: results read "not detected" with an interval sitting near it -- so the
#: panel's conclusion could have been an artefact of its own control group.
FAMILY_PREFIXES = {
    "google": ("gemini", "gemma", "google/", "google_"),
    "openai": ("gpt-", "o1-", "o3-", "o4-", "openai/", "openai_"),
}


def family_of(system_id: str) -> str | None:
    """The vendor family of a system, or None when it belongs to neither judge.

    `None` is the answer that puts a system in the comparison group, so it is
    the answer that has to be earned. A vendor this table does not list reads
    as neutral, silently, and a silent mistake here moves the estimate rather
    than raising anything -- which is what `unfamilied` exists to surface.
    """
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

    #: And which they were, by name. A count cannot be checked; a list can.
    #: `gemma4` sat in this group for the Gemini judge and `gpt-oss-120b` for
    #: the GPT one, because the vendor table was keyed on the judges' own model
    #: names. Naming the group is how a reader sees that before quoting the
    #: number, and how a test sees it before a reader does.
    neutral: tuple[str, ...] = ()

    @property
    def detected(self) -> bool:
        """Whether the interval clears zero by more than a negligible amount.

        False is a real answer and is published as one: "not detected in this
        data" is not "absent", only that a run this size could not see it.
        """
        return self.low > NEGLIGIBLE or self.high < -NEGLIGIBLE


@dataclass(frozen=True)
class Spread:
    """How far apart two judges' self-preferences are, with an interval.

    The panel prints +0.018 and +0.027 side by side, and side by side is how
    they get compared: the larger number reads as the more partial judge. Two
    overlapping intervals do not license that, and the difference has an
    interval of its own, which is this.

    It is not the two effects subtracted and their intervals eyeballed. It is
    the difference taken inside every bootstrap draw, so the correlation
    between the two effects -- they share every conversation and the same
    neutral group -- is carried rather than thrown away. Subtracting
    independent intervals would give a wider one and would be wrong in a
    direction that flatters the conclusion.
    """

    judge_a: str
    judge_b: str
    #: `judge_b`'s effect minus `judge_a`'s, in the units of the measure.
    estimate: float
    low: float
    high: float

    @property
    def detected(self) -> bool:
        """Whether the two judges lean by detectably different amounts."""
        return self.low > NEGLIGIBLE or self.high < -NEGLIGIBLE


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


#: The same threshold saturation uses, and deliberately the same number: a
#: system covering less of the corpus than this, relative to the best-covered
#: one, is still being scored rather than done.
MIN_COVERAGE = 0.8

#: Below this the interval is not worth reporting. Two conversations produce a
#: bootstrap that resamples two numbers, and its interval says nothing.
MIN_SESSIONS = 10


def compare_with_spread(
    by_judge: dict[str, dict[str, dict[str, float]]],
    *,
    judge_a: str,
    judge_b: str,
    samples: int = BOOTSTRAP_SAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[list[Effect], Spread | None]:
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
        return [], None

    # A system still being scored is dropped before the intersection below, the
    # same rule and threshold `saturation.usable_systems` applies and for the
    # identical reason: `shared` is an intersection, so one model two
    # conversations into its run collapses it to two and the whole comparison
    # rests on them. Saturation was given this guard after exactly that
    # happened; this module was written later and never got it.
    covered = {s: len(set(scores_a[s]) & set(scores_b[s])) for s in systems}
    best = max(covered.values())
    systems = [s for s in systems if covered[s] >= MIN_COVERAGE * best]
    if len(systems) < 2:
        return [], None

    # Only conversations every remaining system was scored on by both judges: a
    # difference taken over two different session sets is not a difference.
    shared = sorted(set.intersection(*(set(scores_a[s]) & set(scores_b[s]) for s in systems)))
    if len(shared) < MIN_SESSIONS:
        return [], None

    families: dict[str, tuple[str, list[str], float]] = {}
    for judge_model in (judge_a, judge_b):
        family = family_of_judge(judge_model)
        if family is None:
            continue
        own = [s for s in systems if family_of(s) == family]
        if not own:
            continue
        # A's effect is measured on d = A - B; B's is the same quantity with
        # the sign flipped, because d is antisymmetric in the two judges.
        families[judge_model] = (family, own, 1.0 if judge_model == judge_a else -1.0)

    # Systems neither judge wrote. Not "everyone else": including the other
    # judge's family makes the two effects inseparable -- see the module
    # docstring for the arithmetic.
    neutral = [s for s in systems if family_of(s) is None]
    if not families or not neutral:
        return [], None

    def difference(system: str, sessions: list[str]) -> float:
        """Mean of score_A - score_B for one system over these conversations."""
        return _mean([scores_a[system][x] - scores_b[system][x] for x in sessions])

    def observed(own: list[str], sign: float) -> float:
        """The point estimate, over the systems as they were actually scored.

        The interval below resamples the systems as well; this does not,
        because the point estimate is a statement about the systems that were
        scored and the interval is a statement about the vendor.
        """
        return sign * (
            _mean([difference(s, shared) for s in own])
            - _mean([difference(s, shared) for s in neutral])
        )

    # Conversations *and* systems. The claim this interval supports is "this
    # judge scores its own vendor's models higher", which generalises past the
    # three or four models the mean is over -- the page marks rows with it, and
    # a row is a vendor's model rather than one of these four. Resampling
    # conversations alone treats those four as the whole of OpenAI, and that is
    # what produced the one "detected" verdict this repository published:
    # widened properly it is [-0.0014, +0.0572] and includes zero.
    #
    # **One loop for both judges, and that is the point.** Each judge used to
    # get its own bootstrap from the same seed, which gave them the same
    # conversation draws and -- because the two `own` groups differ in size and
    # so consume different amounts of the stream -- different draws of the
    # neutral group they are both measured against. Their difference could not
    # be read off two runs like that at all. Here one draw picks the
    # conversations and the neutral group once and scores both judges on them,
    # so the effects are paired and their difference can be taken inside the
    # draw. The individual intervals move by Monte-Carlo noise only; what they
    # estimate is unchanged.
    rng = random.Random(seed)
    draws: dict[str, list[float]] = {name: [] for name in families}
    gap: list[float] = []
    for _ in range(samples):
        picked = [shared[rng.randrange(len(shared))] for _ in shared]
        neutral_sample = [neutral[rng.randrange(len(neutral))] for _ in neutral]
        base = _mean([difference(s, picked) for s in neutral_sample])
        drawn: dict[str, float] = {}
        for name, (_family, own, sign) in families.items():
            own_sample = [own[rng.randrange(len(own))] for _ in own]
            drawn[name] = sign * (_mean([difference(s, picked) for s in own_sample]) - base)
            draws[name].append(drawn[name])
        if len(drawn) == 2:
            gap.append(drawn[judge_b] - drawn[judge_a])

    effects = []
    for name, (family, own, sign) in families.items():
        ordered = sorted(draws[name])
        effects.append(
            Effect(
                judge=name,
                family=family,
                own=sign * _mean([difference(s, shared) for s in own]),
                others=sign * _mean([difference(s, shared) for s in neutral]),
                estimate=observed(own, sign),
                low=ordered[int(0.025 * samples)],
                high=ordered[int(0.975 * samples) - 1],
                n_own=len(own),
                n_others=len(neutral),
                n_neutral=len(neutral),
                neutral=tuple(neutral),
                n_sessions=len(shared),
            )
        )

    if not gap:
        return effects, None
    gap.sort()
    by_name = {effect.judge: effect for effect in effects}
    return effects, Spread(
        judge_a=judge_a,
        judge_b=judge_b,
        estimate=by_name[judge_b].estimate - by_name[judge_a].estimate,
        low=gap[int(0.025 * samples)],
        high=gap[int(0.975 * samples) - 1],
    )


def compare(
    by_judge: dict[str, dict[str, dict[str, float]]],
    *,
    judge_a: str,
    judge_b: str,
    samples: int = BOOTSTRAP_SAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> list[Effect]:
    """The effects alone, for callers with no use for their difference."""
    return compare_with_spread(
        by_judge, judge_a=judge_a, judge_b=judge_b, samples=samples, seed=seed
    )[0]


#: How each vendor is written in a sentence. The family key is a slug because
#: it is matched against model ids; a sentence is not.
FAMILY_NAMES = {"google": "Google", "openai": "OpenAI"}


def family_name(family: str) -> str:
    return FAMILY_NAMES.get(family, family)


def describe(effect: Effect, measure: str = "completeness") -> str:
    """One sentence a reader can act on, whichever way it came out."""
    if not effect.detected:
        # Which of the two it is, rather than both. "an interval that includes
        # zero, or is smaller than 0.005" was said of [+0.004, +0.032], which
        # does not include zero -- the reader had to work out which half
        # applied, from numbers printed to three places beside a threshold
        # given to one.
        why = (
            "an interval that includes zero"
            if effect.low <= 0 <= effect.high
            else f"an interval that clears zero by less than {NEGLIGIBLE:g}"
        )
        return (
            f"`{effect.judge}` shows no detectable preference for {family_name(effect.family)} "
            f"models: {effect.estimate:+.3f} {measure} "
            f"[{effect.low:+.3f} to {effect.high:+.3f}], {why}. Not detected is not the same "
            f"as absent — {effect.n_own} system(s) against {effect.n_neutral} neutral one(s) "
            f"over {effect.n_sessions} conversations is what this run could see."
        )
    direction = "higher" if effect.estimate > 0 else "lower"
    return (
        f"`{effect.judge}` scores {family_name(effect.family)} models "
        f"{abs(effect.estimate):.3f} {measure} {direction} than the other judge does, "
        f"relative to how the two differ on the {effect.n_neutral} systems neither of "
        f"them wrote [{effect.low:+.3f} to {effect.high:+.3f}]. Read its column for a "
        f"{family_name(effect.family)} model with that in mind."
    )


def describe_spread(spread: Spread, measure: str = "completeness") -> str:
    """One sentence about the two effects side by side, rather than each alone.

    The two numbers are printed in one table, and a reader compares what is
    printed together. Without this the comparison happens anyway, by eye, on
    two intervals that overlap.
    """
    if not spread.detected:
        return (
            f"The two leans are not distinguishable from each other: "
            f"`{spread.judge_b}` minus `{spread.judge_a}` is {spread.estimate:+.3f} "
            f"{measure} [{spread.low:+.3f} to {spread.high:+.3f}]. Neither judge is "
            f"the more partial one on this evidence, and the larger of the two "
            f"numbers above should not be read as though it were."
        )
    ahead, behind = (
        (spread.judge_b, spread.judge_a)
        if spread.estimate > 0
        else (spread.judge_a, spread.judge_b)
    )
    return (
        f"`{ahead}` leans toward its own vendor by {abs(spread.estimate):.3f} {measure} "
        f"more than `{behind}` does [{spread.low:+.3f} to {spread.high:+.3f}], so the "
        f"difference between the two numbers above is itself a finding."
    )
