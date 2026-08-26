"""Checking the judge against the two therapists who rated the same notes.

TN-Eval released, for each of 150 notes, the ratings of **two human
annotators** — per-criterion rubric judgements and 1-5 Likert scales, section by
section. Our judge answered the same questions. This compares them.

Two numbers matter and one of them is not about our judge at all:

- **judge vs human** is the thing being measured;
- **human vs human** is the ceiling it is measured against. A judge that agrees
  with a therapist as often as two therapists agree with each other has done as
  well as the task allows. TN-Eval measured Krippendorff's alpha of 0.52 on
  rubric completeness and **0.08** on Likert completeness between trained
  therapists — so a low Likert agreement is a property of the scale, not a
  verdict on the judge, and reporting it without the ceiling beside it would be
  misleading.

Whatever comes out goes in the README. A leaderboard whose referee has never
been checked against a person is a table of numbers, not a measurement.

The statistics are implemented here rather than imported: Cohen's kappa and
Spearman are a dozen lines each, and this way the check runs in the offline test
suite with no scientific stack behind it.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from tnb import judge as judge_module
from tnb.datasets.base import Session
from tnb.scoring import run as scoring
from tnb.scoring import tneval

#: TN-Eval released exactly two annotators per note.
ANNOTATORS = 2


def cohens_kappa(first: list[int], second: list[int]) -> float | None:
    """Agreement beyond chance. None when there is nothing to compute.

    Returns 1.0 for the degenerate case where both raters gave the same single
    label to everything: they agreed completely, and chance-correction is
    undefined rather than zero.
    """
    if not first or len(first) != len(second):
        return None

    # A rater who gave everything the same label made no distinctions, so there
    # is no agreement to chance-correct. `spearman` refuses this case and says
    # why -- "0.0 would look like a measured disagreement" -- and kappa produced
    # exactly that 0.0 instead: observed equals expected, so the formula returns
    # zero, which reads as "agrees no better than chance".
    #
    # Live in docs/calibration.json before this: the judge answered "no" to
    # assessment-goals on all 150 notes and was published at 0.000, as though it
    # had measured the criterion and disagreed. Krippendorff's alpha on the same
    # data gives -0.15; only kappa manufactured the zero. The both-constant case
    # below is different and stays -- two raters who agreed on everything did
    # agree.
    judge_varies = len(set(first)) > 1
    human_varies = len(set(second)) > 1
    if not (judge_varies and human_varies) and first != second:
        return None

    labels = sorted(set(first) | set(second))
    total = len(first)
    observed = sum(a == b for a, b in zip(first, second, strict=True)) / total

    expected = sum((first.count(label) / total) * (second.count(label) / total) for label in labels)
    if expected == 1.0:
        return 1.0 if observed == 1.0 else 0.0
    return (observed - expected) / (1 - expected)


def _ranks(values: list[float]) -> list[float]:
    """Average ranks, so ties do not distort the correlation."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(order):
        stop = index
        while stop + 1 < len(order) and values[order[stop + 1]] == values[order[index]]:
            stop += 1
        shared = (index + stop) / 2 + 1
        for position in range(index, stop + 1):
            ranks[order[position]] = shared
        index = stop + 1
    return ranks


def spearman(first: list[float], second: list[float]) -> float | None:
    """Rank correlation. None when a side has no variation to correlate."""
    if len(first) < 2 or len(first) != len(second):
        return None

    x, y = _ranks(list(first)), _ranks(list(second))
    mean_x, mean_y = sum(x) / len(x), sum(y) / len(y)
    covariance = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y, strict=True))
    spread_x = sum((a - mean_x) ** 2 for a in x) ** 0.5
    spread_y = sum((b - mean_y) ** 2 for b in y) ** 0.5
    if spread_x == 0 or spread_y == 0:
        return None
    return covariance / (spread_x * spread_y)


def krippendorff_alpha(units: list[list[float]], *, ordinal: bool) -> float | None:
    """Krippendorff's alpha over units, each rated by two or more raters.

    Implemented because the comparison it feeds cannot be made with anything
    else. Cohen's kappa suits the rubric's yes/no calls and Spearman suits the
    1-5 scales, but they are different quantities: an inequality between a kappa
    and a rho says nothing about which instrument agrees better. TN-Eval reached
    their own finding with alpha on both, so reproducing the finding means using
    the statistic they used.

    ``ordinal`` picks the distance function: nominal treats every disagreement
    as total, which is right for a yes/no criterion, while ordinal weights a
    4-versus-5 as a smaller disagreement than a 1-versus-5, which is right for a
    Likert scale. Both are normalised the same way, which is what makes the two
    alphas comparable in the way the two raw statistics were not.

    Returns None when there is nothing to measure: fewer than two units, or a
    corpus where every rating is identical and expected disagreement is zero.
    """
    usable = [unit for unit in units if len(unit) >= 2]
    if len(usable) < 2:
        return None

    # Coincidence matrix: every ordered pair of ratings within a unit, weighted
    # by that unit's rater count so units with more raters do not dominate.
    coincidence: dict[tuple[float, float], float] = {}
    for unit in usable:
        weight = len(unit) - 1
        for i, first in enumerate(unit):
            for j, second in enumerate(unit):
                if i == j:
                    continue  # a rating is not paired with itself -- by position,
                    # not by value: two raters who agree are the case that matters
                key = (first, second)
                coincidence[key] = coincidence.get(key, 0.0) + 1.0 / weight

    values = sorted({value for unit in usable for value in unit})
    marginal = {
        value: sum(count for (a, _b), count in coincidence.items() if a == value)
        for value in values
    }
    total = sum(marginal.values())
    if total <= 1:
        return None

    if ordinal:
        # The ordinal distance runs over the marginals between the two values,
        # so the gap between adjacent categories reflects how populated they are.
        cumulative = {}
        running = 0.0
        for value in values:
            cumulative[value] = running + marginal[value] / 2
            running += marginal[value]

        def distance(first: float, second: float) -> float:
            return (cumulative[first] - cumulative[second]) ** 2
    else:

        def distance(first: float, second: float) -> float:
            return 0.0 if first == second else 1.0

    observed = sum(count * distance(a, b) for (a, b), count in coincidence.items()) / total
    expected = sum(
        marginal[a] * marginal[b] * distance(a, b) for a in values for b in values if a != b
    ) / (total * (total - 1))
    if expected == 0:
        return None
    return 1 - observed / expected


def exact_agreement(first: list[int], second: list[int]) -> float | None:
    if not first:
        return None
    return sum(a == b for a, b in zip(first, second, strict=True)) / len(first)


#: How far apart two agreement figures must be before the difference between
#: them is a finding. Two instruments within this of each other are reported as
#: inseparable rather than rounded into an ordering.
#:
#: This rule is why the leaderboard shares ranks between models it cannot
#: separate. It was applied to the rubric-against-Likert comparison inside one
#: judge and to nothing else -- so the panel that picks the judge ordered seven
#: candidates spanning 0.089 by differences as small as 0.0072, and the page
#: derived a sentence from the top of that ordering.
ALPHA_MARGIN = 0.05


@dataclass
class Paired:
    """Judgements of the same thing by the judge and by each human."""

    judge: list[float] = field(default_factory=list)
    humans: list[list[float]] = field(default_factory=lambda: [[] for _ in range(ANNOTATORS)])

    def add(self, judge_value: float, human_values: list[float]) -> None:
        self.judge.append(judge_value)
        for index, value in enumerate(human_values):
            self.humans[index].append(value)

    def __len__(self) -> int:
        return len(self.judge)


@dataclass
class Agreement:
    """One measure, scored three ways: judge vs each human, and human vs human."""

    name: str
    n: int
    judge_vs_human: list[float | None]
    human_vs_human: float | None
    statistic: str

    #: The same measure again under Krippendorff's alpha, which -- unlike kappa
    #: and Spearman -- is defined for both the binary rubric and the 1-5 scales.
    #: Reported beside the natural statistic, and it is the only one the
    #: rubric-versus-Likert comparison is allowed to use.
    alpha_judge_vs_human: list[float | None] = field(default_factory=list)
    alpha_human_vs_human: float | None = None
    alpha_level: str = ""

    @property
    def judge_mean(self) -> float | None:
        values = [value for value in self.judge_vs_human if value is not None]
        return sum(values) / len(values) if values else None

    @property
    def alpha_judge_mean(self) -> float | None:
        values = [value for value in self.alpha_judge_vs_human if value is not None]
        return sum(values) / len(values) if values else None

    @property
    def reaches_ceiling(self) -> bool | None:
        """Does the judge agree with a therapist as often as they agree with each other?"""
        if self.judge_mean is None or self.human_vs_human is None:
            return None
        return self.judge_mean >= self.human_vs_human


def _answers_for(
    session_id: str,
    system_id: str,
    judge_model: str,
    *,
    provider: str = "tneval",
    root: Path | None = None,
    seen: Counter | None = None,
) -> dict[str, str]:
    """Every cached judge answer for one note, keyed by question unit.

    `seen` counts the settings the answers were produced at. A candidate
    measured at one thinking budget and compared against a candidate measured
    at another is the mistake this whole panel exists to avoid making about
    models -- and the panel was making it about itself.
    """
    path = judge_module.cache_path(
        judge_model,
        tneval.JUDGE_PROMPT_VERSION,
        provider,
        system_id,
        session_id,
        "x",
        root=root,
    ).parent
    if not path.exists():
        return {}

    answers = {}
    for file in path.glob("*.json"):
        record = json.loads(file.read_text(encoding="utf-8"))
        if record.get("ok"):
            answers[record["unit"]] = record["answer"]
            if seen is not None:
                seen[json.dumps(record.get("judge_fingerprint"), sort_keys=True)] += 1
    return answers


def collect(
    sessions: list[Session], judge_model: str, *, root: Path | None = None
) -> dict[str, Paired]:
    """Pair every judgement the judge made with the humans' on the same item.

    Only the notes TN-Eval released carry human ratings, so this walks those
    three systems per conversation and nothing else.
    """
    pairs: dict[str, Paired] = defaultdict(Paired)
    per_criterion: dict[str, Paired] = defaultdict(Paired)
    seen: Counter = Counter()

    for session in sessions:
        blobs = {"therapist": session.meta.get("human_ratings") or {}}
        for key, (system_id, _label) in scoring.REFERENCE_MODELS.items():
            blobs[system_id] = (session.meta.get("model_notes") or {}).get(key, {})

        for system_id, blob in blobs.items():
            human = blob.get("metrics_human")
            if not isinstance(human, list) or len(human) != ANNOTATORS:
                continue
            answers = _answers_for(session.id, system_id, judge_model, root=root, seen=seen)
            if not answers:
                continue

            for section in tneval.SOAP_SECTIONS:
                per_annotator = [entry.get(section) or {} for entry in human]
                if not all(per_annotator):
                    continue

                for key in tneval.criteria_keys(section):
                    unit = f"{section}.rubric_completeness.{key}"
                    raw = [entry.get("rubric_completeness_raw") or {} for entry in per_annotator]
                    if unit not in answers or not all(key in entry for entry in raw):
                        continue
                    # A refusal paired against a therapist's real rating is not
                    # a disagreement, it is a missing observation. Counting it
                    # drags the judge's agreement down for something the judge
                    # did rather than something it got wrong.
                    if not tneval.is_an_answer(answers[unit]):
                        continue
                    value = float(tneval.parse_yes_no(answers[unit]))
                    humans = [float(entry[key]) for entry in raw]
                    pairs["rubric_completeness"].add(value, humans)
                    per_criterion[key].add(value, humans)

                for measure in ("likert_completeness", "likert_conciseness", "likert_faithfulness"):
                    unit = f"{section}.{measure}"
                    if unit not in answers or not all(measure in e for e in per_annotator):
                        continue
                    pairs[measure].add(
                        float(tneval.parse_likert(answers[unit])),
                        [float(entry[measure]) for entry in per_annotator],
                    )

    pairs["_per_criterion"] = per_criterion  # type: ignore[assignment]
    pairs["_settings"] = seen  # type: ignore[assignment]
    return pairs


def score_agreement(name: str, paired: Paired, *, binary: bool) -> Agreement:
    """Kappa or Spearman as the measure deserves, and alpha for both.

    The first is the statistic a reader expects for that kind of rating. The
    second exists so the rubric and the Likert scales can be put side by side at
    all: kappa and rho are not the same quantity, and an inequality between them
    is not a finding.
    """
    if binary:
        judge_vs = [
            cohens_kappa([int(v) for v in paired.judge], [int(v) for v in human])
            for human in paired.humans
        ]
        human_vs = cohens_kappa(
            [int(v) for v in paired.humans[0]], [int(v) for v in paired.humans[1]]
        )
        statistic = "Cohen's kappa"
    else:
        judge_vs = [spearman(paired.judge, human) for human in paired.humans]
        human_vs = spearman(paired.humans[0], paired.humans[1])
        statistic = "Spearman rho"

    ordinal = not binary
    alpha_judge = [
        krippendorff_alpha(
            [[j, h] for j, h in zip(paired.judge, human, strict=True)], ordinal=ordinal
        )
        for human in paired.humans
    ]
    alpha_human = krippendorff_alpha(
        [[a, b] for a, b in zip(paired.humans[0], paired.humans[1], strict=True)],
        ordinal=ordinal,
    )

    return Agreement(
        name=name,
        n=len(paired),
        judge_vs_human=judge_vs,
        human_vs_human=human_vs,
        statistic=statistic,
        alpha_judge_vs_human=alpha_judge,
        alpha_human_vs_human=alpha_human,
        alpha_level="ordinal" if ordinal else "nominal",
    )


@dataclass
class Report:
    judge_model: str
    judge_prompt_version: str
    notes: int
    agreements: list[Agreement]
    per_criterion: list[tuple[str, float | None, float | None]] = field(default_factory=list)

    #: The judge settings these answers were produced at, so two candidates
    #: measured differently are not silently compared. `None` for a report read
    #: from a file written before this was recorded.
    judge_settings: dict | None = None
    #: Present only when one candidate's own cache held more than one setting.
    other_settings: dict[str, int] = field(default_factory=dict)

    #: How far apart the two alphas must be before the comparison is called.
    #: The shared rule, kept here under its old name so nothing that reads it
    #: through the class has to change.
    ALPHA_MARGIN = ALPHA_MARGIN

    @property
    def rubric_beats_likert(self) -> bool | None:
        """TN-Eval's central finding. Does our judge reproduce it?

        They measured far better human agreement on criterion checklists than on
        1-5 scales, using Krippendorff's alpha on both. If the judge shows the
        same pattern, the instrument behaves like the one they validated.

        Read from `alpha_judge_mean`, never from `judge_mean`: the latter is a
        kappa on one side and a Spearman rho on the other, and an inequality
        between two different statistics is not evidence of anything. That
        comparison is what this property used to make, and the sentence it
        produced was the repository's stated reason for ranking on the rubric.

        None when the two are within `ALPHA_MARGIN`, which is an answer -- "these
        cannot be separated" -- rather than a missing one.
        """
        rubric = next((a for a in self.agreements if a.name == "rubric_completeness"), None)
        likert = next((a for a in self.agreements if a.name == "likert_completeness"), None)
        if not rubric or not likert:
            return None
        first, second = rubric.alpha_judge_mean, likert.alpha_judge_mean
        if first is None or second is None or abs(first - second) < self.ALPHA_MARGIN:
            return None
        return first > second


def separations(judges: list[dict], measure: str, margin: float = ALPHA_MARGIN) -> dict:
    """Which candidate judges this measurement can actually tell apart.

    Takes the serialised rows -- the same list that goes into `docs/judges.json`
    and reaches the page -- rather than the `Report` objects behind them, so
    what this describes and what the reader sees cannot come apart.

    Seven candidates spanning 0.089 with consecutive gaps as small as 0.0072 is
    an ordering the data does not support, and the page was deriving a sentence
    from the top of it. The leaderboard has shared ranks for exactly this
    reason; the panel that picks the judge did not.

    Bands are deliberately *not* formed by chaining "within the margin" down
    the list. That relation is not transitive -- every consecutive gap here is
    under the margin while the ends are 0.089 apart -- so chaining would put all
    seven in one band and say nothing. What is reported instead is the set of
    pairs the margin does separate, which is a claim a reader can check against
    the two numbers beside it.

    `above_ceiling` gets the same treatment. Every candidate agrees with a
    therapist at least as often as the two therapists agree with each other,
    but only the ones clear of that ceiling *by the margin* are distinguishable
    from it, and the difference between those two sentences is most of what a
    calibration is for.
    """

    def number(value) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    found: list[tuple[str, float]] = []
    ceiling = None
    for row in judges:
        agreement = next((a for a in row.get("agreements", []) if a.get("name") == measure), None)
        if agreement is None:
            continue
        alpha = number(agreement.get("alpha"))
        if alpha is None:
            continue
        ceiling = number(agreement.get("alpha_humans")) or ceiling
        found.append((row["judge_model"], alpha))
    found.sort(key=lambda pair: (-pair[1], pair[0]))

    return {
        "measure": measure,
        "margin": margin,
        "ceiling": ceiling,
        "ranked": [{"judge": name, "alpha": alpha} for name, alpha in found],
        "separated": [
            {"better": better, "worse": worse, "by": round(first - second, 4)}
            for index, (better, first) in enumerate(found)
            for worse, second in found[index + 1 :]
            if first - second > margin
        ],
        "above_ceiling": (
            [name for name, alpha in found if alpha - ceiling > margin]
            if ceiling is not None
            else []
        ),
        "all_at_or_above_ceiling": (
            bool(found) and all(alpha >= ceiling for _, alpha in found)
            if ceiling is not None
            else False
        ),
    }


def calibrate(sessions: list[Session], judge_model: str, *, root: Path | None = None) -> Report:
    pairs = collect(sessions, judge_model, root=root)
    per_criterion = pairs.pop("_per_criterion", {})  # type: ignore[arg-type]
    settings = pairs.pop("_settings", Counter())  # type: ignore[arg-type]

    agreements = []
    for name in (
        "rubric_completeness",
        "likert_completeness",
        "likert_conciseness",
        "likert_faithfulness",
    ):
        paired = pairs.get(name)
        if paired and len(paired):
            agreements.append(score_agreement(name, paired, binary=name.startswith("rubric")))

    detail = []
    for key, paired in sorted(per_criterion.items()):
        if not len(paired):
            continue
        agreement = score_agreement(key, paired, binary=True)
        detail.append((key, agreement.judge_mean, agreement.human_vs_human))

    rubric = pairs.get("rubric_completeness")
    notes = len(rubric) // 23 if rubric else 0
    return Report(
        judge_model=judge_model,
        judge_prompt_version=tneval.JUDGE_PROMPT_VERSION,
        # What this candidate was measured at. Comparing a judge at one thinking
        # budget with a judge at another is exactly the confusion the panel is
        # meant to resolve, and it was making it about its own rows.
        judge_settings=(json.loads(settings.most_common(1)[0][0]) if settings else None),
        other_settings={key: count for key, count in sorted(settings.items())}
        if len(settings) > 1
        else {},
        notes=notes,
        agreements=agreements,
        per_criterion=detail,
    )


def render_markdown(report: Report) -> str:
    """The README block. Written the same way whether the news is good or bad."""
    if not report.agreements:
        return (
            "*Not yet measured.* Before any leaderboard number is published, the judge is "
            "scored against the two human annotators TN-Eval released, and the agreement "
            "figures appear here — including if they are bad."
        )

    lines = [
        f"Judge **`{report.judge_model}`** (prompts `{report.judge_prompt_version}`) against the "
        f"two therapists TN-Eval had rate the same notes.",
        "",
        "| Measure | Statistic | Judge vs therapist | Therapist vs therapist | "
        "Alpha, judge | Alpha, therapists | n |",
        "|---|---|---|---|---|---|---|",
    ]

    def cell(value: float | None) -> str:
        return "—" if value is None else f"{value:.2f}"

    for agreement in report.agreements:
        lines.append(
            f"| {agreement.name.replace('_', ' ')} | {agreement.statistic} | "
            f"{cell(agreement.judge_mean)} | {cell(agreement.human_vs_human)} | "
            f"{cell(agreement.alpha_judge_mean)} | {cell(agreement.alpha_human_vs_human)} | "
            f"{agreement.n} |"
        )

    lines += [
        "",
        "**The therapist-vs-therapist columns are the ceiling, not a target to beat.** Two "
        "trained therapists disagree with each other about these notes; a judge that agrees "
        "with a therapist as often as the other therapist does has done as well as the task "
        "allows.",
        "",
        "**Why two statistics.** Cohen's kappa suits a yes/no criterion and Spearman suits a "
        "1–5 scale, so each measure is reported under the one a reader expects. But those two "
        "are different quantities and an inequality between them means nothing, so the "
        "rubric-versus-Likert comparison below is made on **Krippendorff's alpha**, which is "
        "defined for both — nominal for the rubric, ordinal for the scales — and is the "
        "statistic TN-Eval used to reach the finding in the first place.",
    ]

    rubric = next((a for a in report.agreements if a.name == "rubric_completeness"), None)
    likert = next((a for a in report.agreements if a.name == "likert_completeness"), None)
    figures = (
        f" (alpha {rubric.alpha_judge_mean:.2f} against {likert.alpha_judge_mean:.2f})"
        if rubric is not None
        and likert is not None
        and rubric.alpha_judge_mean is not None
        and likert.alpha_judge_mean is not None
        else ""
    )

    if report.rubric_beats_likert is True:
        lines.append(
            f"\nThe judge reproduces TN-Eval's central finding: criterion checklists agree far "
            f"better than 1–5 scales{figures}. That is why the leaderboard ranks on the rubric "
            f"and reports the Likert columns with a caveat."
        )
    elif report.rubric_beats_likert is False:
        lines.append(
            f"\n**The judge does not reproduce TN-Eval's finding** that criterion checklists "
            f"agree better than 1–5 scales{figures}. That is unexpected and is reported rather "
            f"than explained away; see docs/limitations.md."
        )
    else:
        lines.append(
            f"\n**The two instruments cannot be separated here**{figures}, so this run neither "
            f"reproduces nor contradicts TN-Eval's finding that criterion checklists agree "
            f"better than 1–5 scales. Reported as undecided rather than rounded into a verdict."
        )
    return "\n".join(lines)
