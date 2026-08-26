"""Has this benchmark run out of room to measure anything?

The question worth asking of any benchmark, and the one this repository is best
placed to answer, because it holds every individual judgement rather than only
the averages. Three analyses, none of which needs an external capability score:

**Per criterion.** The 23 rubric items do not behave alike. Some every model
satisfies — nothing left to measure. Some *nobody* satisfies, the therapist
included, because a single counselling session does not contain the answer;
a zero there is a property of the corpus, not of the model. The rest is where
the benchmark still separates one model from another, and counting them is the
honest statement of how much measuring power is left.

**Confidence intervals.** Every model wrote a note for the same 50
conversations, so the bootstrap is *paired*: resample conversations, not models,
and the same resample scores everyone. That answers "can these two models be
told apart at all", which a ranking on its own never does. `docs/limitations.md`
has always said small gaps are noise; this is what turns that warning into a
number.

**The 2025 anchor.** TN-Eval released notes from Llama 3.1 70B and Mistral Large
V2, scored here by the same judge on the same rubric. A year of model progress
is therefore measurable directly, with no external index and no assumption about
which model is which.

Deterministic on purpose: the bootstrap is seeded, so a rebuilt page is
byte-identical and its diffs stay readable.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from tnb import judge
from tnb.scoring import tneval

#: Fixed so the published intervals do not move when nothing else did.
BOOTSTRAP_SEED = 20260824
BOOTSTRAP_SAMPLES = 2000

#: A criterion every model satisfies almost always has nothing left to measure.
SATURATED_AT = 0.90
#: A criterion nobody satisfies -- the human reference included -- is not a hard
#: question but an absent one: the transcript does not contain the answer.
FLOOR_AT = 0.10
#: How far apart the best and worst model must be for a criterion to be doing
#: any separating.
DISCRIMINATES_AT = 0.25


@dataclass(frozen=True)
class CriterionProfile:
    """One rubric item, and what it does to the field of models."""

    key: str
    text: str
    section: str
    by_system: dict[str, float]
    human: float | None

    @property
    def models(self) -> dict[str, float]:
        return {name: rate for name, rate in self.by_system.items() if name != "therapist"}

    @property
    def spread(self) -> float:
        rates = list(self.models.values())
        return max(rates) - min(rates) if rates else 0.0

    @property
    def verdict(self) -> str:
        rates = list(self.models.values())
        if not rates:
            return "unknown"
        if min(rates) >= SATURATED_AT:
            return "saturated"
        everyone = rates + ([self.human] if self.human is not None else [])
        if max(everyone) <= FLOOR_AT:
            return "unreachable"
        if self.spread >= DISCRIMINATES_AT:
            return "discriminating"
        return "mixed"


@dataclass(frozen=True)
class Interval:
    """A model's score with the range the evidence actually supports."""

    system: str
    mean: float
    low: float
    high: float
    #: Conversations in the shared set -- the same number for every system here,
    #: because that is what makes the comparison paired.
    sessions: int
    #: Conversations this system was actually scored on. Larger than `sessions`
    #: whenever some *other* system lost notes, which is why this mean and the
    #: leaderboard's differ: same measure, different denominator.
    own_sessions: int = 0
    #: The mean over this system's own conversations -- what the table shows.
    own_mean: float = 0.0


def label_for(provider: str, system_id: str, providers_by_system: dict) -> str:
    """How a system is named in this analysis.

    Bare id while it is unambiguous, qualified once two providers serve the same
    name. A model id is only unique inside one endpoint, and merging two
    providers' answers under one name is the mistake the rest of this repository
    is built to avoid.
    """
    return (
        system_id
        if len(providers_by_system.get(system_id, ())) < 2
        else f"{system_id} ({provider})"
    )


class Answers(defaultdict):
    """Judge answers keyed (system, session) -> {unit: answer}, from one instrument.

    A plain dict of the answers plus the two facts a caller needs in order to
    say what was analysed: which judge settings produced them, and what else
    was in the cache and left out.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        #: The `judge_fingerprint` every answer in here shares.
        self.chosen_fingerprint: dict | None = None
        #: Fingerprints found in the cache and not used, with how many answers
        #: each had. Non-empty during a re-scoring run, and the caller says so
        #: rather than silently reporting a subset.
        #:
        #: Per instance, not on the class: a mutable class attribute is shared
        #: by every `Answers` ever made, and two judges are loaded in one
        #: process by `tnb preference`.
        self.other_fingerprints: dict[str, int] = {}


def load_answers(root: Path | None = None, judge_model: str = judge.DEFAULT_MODEL) -> Answers:
    """Every judge answer, keyed (system, session) -> {question unit: answer}.

    Read from the answer cache rather than from the result rows, because the
    rows carry averages and these analyses need the individual judgements.

    The system key carries its provider whenever two providers serve the same
    model id: they may be two different builds, and averaging them together
    would report a model that does not exist.
    """
    # Scoped to one judge prompt version, not the whole judge directory. Two
    # versions of the rubric are two instruments, and the leaderboard's central
    # rule is that their numbers never mix -- an analysis that read both would
    # break it silently.
    base = (
        (root or judge.CACHE_DIR)
        / judge._slug_model(judge_model)
        / judge._slug_model(tneval.JUDGE_PROMPT_VERSION)
    )
    answers = Answers(dict)
    if not base.exists():
        return answers

    records = []
    by_fingerprint: dict[str, list[dict]] = defaultdict(list)
    for path in base.rglob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not record.get("ok"):
            continue
        by_fingerprint[json.dumps(record.get("judge_fingerprint"), sort_keys=True)].append(record)

    # One instrument at a time. The directory is scoped by judge model and
    # prompt version but not by the judge's *settings*, and a thinking budget
    # is a setting: raising it from 128 to 256 re-asks every question, so
    # mid-run the cache holds both and averaging across them would report a
    # number no single judge produced. The leaderboard's rule that two
    # fingerprints never share a table has to hold here too.
    #
    # The largest set wins, deterministically: during a re-scoring run that is
    # the complete old instrument rather than the half-finished new one, which
    # is the conservative choice. `dropped_fingerprints` says what was left
    # out so the caller can report it.
    if by_fingerprint:
        chosen = max(sorted(by_fingerprint), key=lambda key: len(by_fingerprint[key]))
        records = by_fingerprint[chosen]
        answers.chosen_fingerprint = json.loads(chosen) if chosen != "null" else None
        answers.other_fingerprints = {
            key: len(group) for key, group in sorted(by_fingerprint.items()) if key != chosen
        }

    providers_by_system: dict[str, set[str]] = defaultdict(set)
    for record in records:
        providers_by_system[record["system_id"]].add(record.get("provider", ""))

    for record in records:
        label = label_for(record.get("provider", ""), record["system_id"], providers_by_system)
        answers[(label, record["session_id"])][record["unit"]] = record["answer"]
    return answers


def per_criterion(answers: dict, include: list[str] | None = None) -> list[CriterionProfile]:
    """How often each system satisfied each of the 23 criteria.

    ``include`` is the same coverage filter the intervals use. Without it the
    panel excluded a half-scored system from its ranking and then let that
    system's handful of notes set the min, the max and therefore the verdict of
    every criterion bar beside it -- one panel saying two different things about
    who was measured.
    """
    hits: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    allowed = None if include is None else set(include)

    for (system, _session), units in answers.items():
        if allowed is not None and system not in allowed:
            continue
        for unit, answer in units.items():
            parts = unit.split(".")
            if len(parts) != 3 or parts[1] != "rubric_completeness":
                continue
            slot = hits[(system, parts[2])]
            slot[0] += tneval.parse_yes_no(answer)
            slot[1] += 1

    systems = sorted({system for system, _key in hits})
    profiles = []
    for key, text in tneval.CHECKBOX_MAPPING.items():
        by_system = {}
        for system in systems:
            got, total = hits[(system, key)]
            if total:
                by_system[system] = got / total
        if not by_system:
            continue
        profiles.append(
            CriterionProfile(
                key=key,
                text=text.split(":")[0].strip(),
                section=key.split("-")[0],
                by_system=by_system,
                human=by_system.get("therapist"),
            )
        )
    return profiles


def per_session_scores(answers: dict, measure: str = "completeness") -> dict[str, dict[str, float]]:
    """One score per (system, session), which is what the bootstrap resamples.

    Completeness by default, because it is the measure the leaderboard ranks on
    and the only one every cached answer set can support: the note text is not
    in the cache, so which conciseness questions *should* have been asked cannot
    be reconstructed here.
    """
    scores: dict[str, dict[str, float]] = defaultdict(dict)
    for (system, session), units in answers.items():
        aggregate = tneval.aggregate(units)
        # A measure computed from some of the four sections is not this note's
        # score for it. A judge that answered subjective and objective in full
        # and never reached assessment and plan produces a completeness of 1.0
        # over two sections with an empty `incomplete`, and it entered the
        # bootstrap as a measurement. Judge failures cluster on the notes that
        # are hard to read, so the bias from keeping them runs one way.
        #
        # `is_complete` is the wrong test here and would drop everything: it
        # also requires conciseness and faithfulness, and the note text is not
        # in the answer cache, so those cannot be reconstructed at all.
        # `usable_systems` then drops and names a system that loses too many,
        # which is the honest way for coverage to fall rather than for scores
        # to quietly sag.
        if not aggregate.rests_on_every_section(measure):
            continue
        value = aggregate.headline.get(measure)
        if value is not None:
            scores[system][session] = value
    return scores


#: A system covering less of the corpus than this, relative to the best-covered
#: one, is still being scored. Including it would drag the shared set down to its
#: handful of conversations and silently shrink everybody else's evidence.
MIN_COVERAGE = 0.8


def usable_systems(scores: dict[str, dict[str, float]]) -> tuple[list[str], list[str]]:
    """Split systems into those with enough coverage to compare, and the rest.

    Found the hard way: one model two conversations into its scoring run
    collapsed the shared set to two and voided the whole analysis. A partial
    system is now left out and named, rather than quietly taking everyone with
    it.
    """
    if not scores:
        return [], []
    best = max(len(sessions) for sessions in scores.values())
    usable, partial = [], []
    for system, sessions in sorted(scores.items()):
        (usable if len(sessions) >= best * MIN_COVERAGE else partial).append(system)
    return usable, partial


def paired_intervals(
    scores: dict[str, dict[str, float]],
    *,
    samples: int = BOOTSTRAP_SAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[list[Interval], dict[str, dict[str, float]]]:
    """Bootstrap over conversations, scoring every system on the same resample.

    Paired because every system wrote a note for the same conversations: a
    conversation that is hard for one is hard for all, and resampling them
    together removes that shared difficulty from the comparison instead of
    counting it as disagreement.

    Returns the intervals and, for every ordered pair, the fraction of resamples
    in which the first system scored above the second — which is the number that
    answers "can these two be told apart".
    """
    systems, _partial = usable_systems(scores)
    shared = (
        sorted(set.intersection(*(set(scores[system]) for system in systems))) if systems else []
    )
    if len(shared) < 2:
        return [], {}

    rng = random.Random(seed)
    draws: dict[str, list[float]] = {system: [] for system in systems}
    wins: dict[str, dict[str, int]] = {a: dict.fromkeys(systems, 0) for a in systems}

    for _ in range(samples):
        picked = [shared[rng.randrange(len(shared))] for _ in shared]
        means = {
            system: sum(scores[system][session] for session in picked) / len(picked)
            for system in systems
        }
        for system, value in means.items():
            draws[system].append(value)
        for first in systems:
            for second in systems:
                if means[first] > means[second]:
                    wins[first][second] += 1

    intervals = []
    for system in systems:
        ordered = sorted(draws[system])
        own = scores[system]
        intervals.append(
            Interval(
                system=system,
                mean=sum(scores[system][s] for s in shared) / len(shared),
                low=ordered[int(0.025 * samples)],
                high=ordered[int(0.975 * samples) - 1],
                sessions=len(shared),
                own_sessions=len(own),
                own_mean=sum(own.values()) / len(own) if own else 0.0,
            )
        )

    beats = {
        first: {second: wins[first][second] / samples for second in systems if second != first}
        for first in systems
    }
    return sorted(intervals, key=lambda i: -i.mean), beats


def indistinguishable(
    intervals: list[Interval], beats: dict[str, dict[str, float]], *, threshold: float = 0.95
) -> list[list[str]]:
    """Groups of systems the evidence cannot separate, best first.

    Two systems are told apart only when one beats the other in at least
    `threshold` of resamples. Anything less is a ranking the data does not
    support, however confidently the table prints it.

    These are groups, **not equivalence classes**, and cannot be: "cannot be
    separated" is not transitive. A may be inseparable from B, and B from C,
    while A is clearly above C. Systems are placed best-first into the first
    group whose members none of them beats, which keeps the reading "everything
    on this line is tied for this position" true, and leaves the boundary
    between adjacent lines a convention rather than a fact.
    """
    groups: list[list[str]] = []
    for interval in intervals:
        for group in groups:
            if all(beats[member].get(interval.system, 0) < threshold for member in group):
                group.append(interval.system)
                break
        else:
            groups.append([interval.system])
    return groups


def build(root: Path | None = None, judge_model: str = judge.DEFAULT_MODEL) -> dict | None:
    """The whole analysis, as the page consumes it."""
    answers = load_answers(root, judge_model)
    if not answers:
        return None

    scores = per_session_scores(answers)
    usable, partial = usable_systems(scores)
    criteria = per_criterion(answers, include=usable)
    intervals, beats = paired_intervals(scores)
    if not intervals:
        return None

    verdicts = defaultdict(list)
    for profile in criteria:
        verdicts[profile.verdict].append(profile.key)

    # Why the two Completeness figures on this page differ, computed rather than
    # asserted. The table averages each system over its own notes; this panel
    # averages every system over the conversations they all share, because a
    # paired bootstrap has no meaning otherwise. When some system lost notes the
    # shared set is smaller than the corpus, and the two means -- and sometimes
    # the two orderings -- come apart. Saying which systems cost how many
    # conversations turns an apparent contradiction into a stated fact.
    shared = intervals[0].sessions
    largest = max((i.own_sessions for i in intervals), default=shared)

    # Which systems constrain the intersection -- the ones scored on fewer
    # conversations than the fullest corpus. Naming these is the point; listing
    # the systems that lost nothing would be a list of everybody else.
    narrowed_by = {
        interval.system: largest - interval.own_sessions
        for interval in intervals
        if interval.own_sessions < largest
    }

    return {
        "judge_model": judge_model,
        # Which *settings* of that judge, and what else was in the cache. The
        # model name alone does not identify the instrument: the same judge at
        # two thinking budgets produces two, and until now a published panel
        # could not say which one it was.
        "judge_fingerprint": answers.chosen_fingerprint,
        "ignored_fingerprints": answers.other_fingerprints,
        "sessions": shared,
        #: The fullest per-system corpus, so the page can say "42 of 50".
        "corpus_sessions": largest,
        #: Systems scored on fewer conversations than the fullest corpus, and by
        #: how many. These are why the shared set is smaller than the corpus, and
        #: therefore why this panel's means differ from the leaderboard's. Empty
        #: when every system was scored on the same conversations.
        "narrowed_by": dict(sorted(narrowed_by.items(), key=lambda kv: -kv[1])),
        # Named rather than dropped: a reader must be able to tell "not measured
        # yet" from "measured and left out".
        "still_scoring": partial,
        "criteria": [
            {
                "key": profile.key,
                "text": profile.text,
                "section": profile.section,
                "verdict": profile.verdict,
                "spread": round(profile.spread, 3),
                "human": None if profile.human is None else round(profile.human, 3),
                "by_system": {k: round(v, 3) for k, v in sorted(profile.by_system.items())},
            }
            for profile in sorted(
                criteria, key=lambda p: -sum(p.models.values()) if p.models else 0
            )
        ],
        "verdict_counts": {name: len(keys) for name, keys in sorted(verdicts.items())},
        "intervals": [
            {
                "system": i.system,
                "mean": round(i.mean, 4),
                "own_mean": round(i.own_mean, 4),
                "own_sessions": i.own_sessions,
                "low": round(i.low, 4),
                "high": round(i.high, 4),
            }
            for i in intervals
        ],
        "indistinguishable": indistinguishable(intervals, beats),
        "bootstrap": {"samples": BOOTSTRAP_SAMPLES, "seed": BOOTSTRAP_SEED, "paired": True},
    }
