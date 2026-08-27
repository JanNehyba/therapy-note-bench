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
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from tnb import judge, results
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
    #: The mean over this system's own conversations. **Not the table's figure**,
    #: which this comment claimed until 2026-08-27 and which is wrong for 10 of
    #: the 19 rows under the first judge, by up to 0.0070.
    #:
    #: The two admit a note on different tests. The leaderboard averages the
    #: notes `Scores.is_complete` accepts, which needs all four sections of
    #: *every* measure -- completeness, conciseness and faithfulness. This
    #: analysis reads only the answer cache, where the note text is not, so it
    #: cannot know which conciseness questions should have been asked and admits
    #: a note on `rests_on_every_section("completeness")` instead. That is a
    #: weaker test, so it keeps more notes: 49 against the table's 48 for
    #: `kimi-k3`, and a different mean over them.
    #:
    #: `None` when there is nothing to average, never 0.0: a zero there reads as
    #: a score rather than as an absence.
    own_mean: float | None = None


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
            # A fragment of the judge's own reasoning is not a "no". Without
            # this it counted in the denominator as a criterion the model
            # failed, and every criterion bar and every verdict on the page
            # rests on these two counters.
            if not tneval.is_an_answer(answer):
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
                own_mean=sum(own.values()) / len(own) if own else None,
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


def interval_json(interval: Interval) -> dict:
    """One system's interval, as the page consumes it.

    A function rather than four lines inside `build` so it can be called: the
    only way to reach it otherwise is to run the whole analysis off disk, which
    is why the `own_mean` absence went untested until it was found by reading.
    """
    return {
        "system": interval.system,
        "mean": round(interval.mean, 4),
        # `None` travels as null. The page guards on it and prints nothing;
        # rounding an absence here would throw, and returning 0.0 instead --
        # which is what this did -- prints "the table shows 0.000" about a
        # system nobody measured.
        "own_mean": None if interval.own_mean is None else round(interval.own_mean, 4),
        "own_sessions": interval.own_sessions,
        "low": round(interval.low, 4),
        "high": round(interval.high, 4),
    }


def note_words(cache_dir: Path | None = None) -> dict[str, dict[str, int]]:
    """{system: {session: words}} for the SOAP notes, from the generation cache.

    Read here rather than from the leaderboard because the length question is
    asked per note, and the row carries only a median.
    """
    from tnb import generation

    cache_dir = cache_dir or generation.CACHE_DIR
    found: dict[str, dict[str, int]] = defaultdict(dict)
    if not cache_dir.exists():
        return found
    for path in cache_dir.rglob("*.json"):
        parts = path.relative_to(cache_dir).parts
        if len(parts) != 6 or parts[1] != "soap":
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        note = record.get("note")
        if not record.get("ok") or not isinstance(note, dict):
            continue
        words = len(" ".join(str(value) for value in note.values()).split())
        if words:
            found[parts[3]][parts[4]] = words
    return found


def _sign_test(positive: int, total: int) -> float:
    """Two-sided probability of this many or more one-way results by chance.

    Written out rather than imported: this module is in the offline test suite
    and carries no scientific stack.
    """
    if not total:
        return 1.0
    extreme = max(positive, total - positive)
    tail = sum(math.comb(total, k) for k in range(extreme, total + 1))
    return min(1.0, 2 * tail / (2**total))


def length_effect(
    scores: dict[str, dict[str, float]], words: dict[str, dict[str, int]]
) -> dict | None:
    """Does completeness rise with how much the model wrote?

    Completeness counts coverage, so a longer note covers more even under a
    perfect judge. That is a property of the measure and no judge-versus-human
    check can see it.

    Two questions, and only the second is about the note:

    - **Within a system**, across its own conversations. Positive in all sixteen
      under both judges — but it cannot separate the note from the transcript,
      because a longer session yields both a longer note and more rubric
      material.
    - **Within a conversation**, across the systems. The transcript is held
      fixed, so it can explain nothing. Here the two judges part company, and
      that difference is not recorded anywhere else.

    Reported as the length itself on the leaderboard and as this on the methods
    page: the correlation depends on which judge is asked, and a coefficient in
    a table would be read as a grade.
    """
    from tnb.scoring.calibration import spearman

    within_system = []
    for system in sorted(set(scores) & set(words) | {s for s in scores if s in words}):
        per, length = scores.get(system) or {}, words.get(system) or {}
        shared = sorted(set(per) & set(length))
        if len(shared) < 25:
            continue
        rho = spearman([float(length[x]) for x in shared], [per[x] for x in shared])
        if rho is not None:
            within_system.append({"system": system, "rho": round(rho, 4), "n": len(shared)})

    by_session: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for system, per in scores.items():
        length = words.get(system) or {}
        for session, value in per.items():
            if session in length:
                by_session[session].append((length[session], value))
    within_conversation = []
    for _session, pairs in sorted(by_session.items()):
        if len(pairs) < 12:
            continue
        rho = spearman([float(w) for w, _ in pairs], [c for _, c in pairs])
        if rho is not None:
            within_conversation.append(rho)

    if not within_system or not within_conversation:
        return None

    ordered = sorted(within_conversation)
    positive = sum(1 for rho in within_conversation if rho > 0)
    return {
        "within_system": sorted(within_system, key=lambda row: -row["rho"]),
        "within_conversation": {
            "median": round(ordered[len(ordered) // 2], 4),
            "positive": positive,
            "n": len(within_conversation),
            # Not rounded to a few places: a real p of 3.7e-11 becomes 0.0 at six,
            # and "p = 0" is a claim nobody made.
            "sign_test_p": float(f"{_sign_test(positive, len(within_conversation)):.3g}"),
        },
    }


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
        # Which track these groups belong to. This module reads
        # `rubric_completeness` units out of the TN-Eval cache and knows nothing
        # about any other corpus, but it never said so, and `report._groups_for`
        # matched an analysis to a table on the judge alone -- so both iCARE
        # tables were drawn with a Rank column whose bands come from 50 AnnoMI
        # conversations scored on a 23-item checklist the iCARE track does not
        # have.
        "track": results.TRACK_TNEVAL,
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
        "intervals": [interval_json(i) for i in intervals],
        #: For every ordered pair, the fraction of resamples in which the first
        #: scored above the second. This is the bootstrap's own answer to "can
        #: these two be told apart", it was computed here and thrown away, and
        #: the figure that needed it read `indistinguishable` instead -- a
        #: greedy grouping whose own docstring says it is not an equivalence
        #: class, so two systems in different bands need not be separated at all.
        "beats": {
            first: {second: round(value, 4) for second, value in sorted(row.items())}
            for first, row in sorted(beats.items())
        },
        "indistinguishable": indistinguishable(intervals, beats),
        #: Whether completeness rises with how much the model wrote. `None` when
        #: the generation cache is not on this machine.
        "length_effect": length_effect(scores, note_words()),
        "bootstrap": {"samples": BOOTSTRAP_SAMPLES, "seed": BOOTSTRAP_SEED, "paired": True},
    }
