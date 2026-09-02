"""Scoring the iCARE track: two automatic metrics, one judge, one flag.

The last missing scorer. The iCARE track has had generation, a track id and
page columns since phase 2, and nothing that produced a number.

**Three columns that are meant to disagree.** The source paper found that
clinical preference "did not always mirror automatic benchmarks" — a smaller
Mistral model was preferred by experts over the model that led on the automatic
scores. Reporting only one of them would delete that finding, so ROUGE-L and
BERTScore sit beside TRACE and the gap between them is published as a result.

**TRACE here has no human anchor.** The authors' TRACE annotations and their
blinded expert review are not in the public repository — checked, and recorded
in docs/datasets.md. The TN-Eval track can say how far its judge agrees with two
therapists; this one cannot say anything of the sort, and every view that
carries a TRACE number says so.

The two automatic metrics are computed here rather than imported so the offline
test suite can exercise them: ROUGE-L is a longest-common-subsequence, which is
a dozen lines, and BERTScore is imported lazily because it drags a model
download behind it and most runs do not want one.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from tnb import corpus
from tnb.config import REPO_ROOT
from tnb.datasets import ihope
from tnb.tasks import icare

#: Bumped whenever anything reaching the TRACE judge changes. Result rows carry
#: it and the leaderboard never mixes two versions.
JUDGE_PROMPT_VERSION = "icare-trace-v1"

#: What each reported measure is, on what scale, and what a reader must not
#: conclude from it. Same shape as `tneval.MEASURES`; `report.column_meta` reads
#: whichever belongs to the track.
MEASURES: dict[str, dict[str, str]] = {
    "rouge_l": {
        "label": "ROUGE-L",
        "scale": "0-1",
        "definition": (
            "Longest-common-subsequence overlap with the expert note, F-measure. "
            "Rewards using the same words in the same order."
        ),
        "caveat": (
            "Not the source paper's ROUGE-L and not comparable with their "
            "published table. Theirs compares the whole rendered note, which "
            "puts our own field labels and every Nil the expert wrote on both "
            "sides -- a note where the model wrote nothing at all scores 0.379 "
            "that way, above most real notes. This compares the field values of "
            "the sections the expert answered, where the same empty note scores "
            "0.000, and every model's figure fell by about a third. It also "
            "cannot tell a good paraphrase from a wrong answer, and the source "
            "paper found it disagrees with what clinicians preferred. It also "
            "falls as notes get longer; where this table has a Words column, the "
            "correlation between the two is printed under it."
        ),
    },
    "bertscore": {
        "label": "BERTScore",
        "scale": "0-1",
        "definition": "Embedding similarity to the expert note. Tolerates paraphrase.",
        "caveat": "A fluent note about the wrong session still scores well.",
    },
    "trace": {
        "label": "TRACE",
        "scale": "1-5",
        "definition": (
            "Trustworthiness, relevance, accuracy, comprehensiveness and expression, "
            "each rated 1-5 by a judge and averaged."
        ),
        "caveat": (
            "A re-implementation with no human anchor: the authors never published "
            "their ratings, so unlike the TN-Eval track this number is not "
            "calibrated against anybody."
        ),
    },
    "temporal_past": {
        "label": "Looks back",
        "scale": "0-1",
        "definition": (
            "Section 5 only -- what happened in the previous session. The fraction "
            "of the 34 sessions whose expert note answered it where the model did too."
        ),
        "caveat": (
            "Counts once in the order like every column, and moves it little: every "
            "model scores 0.97-1.00 here, so it separates nobody -- it is shown "
            "because its twin does."
        ),
    },
    "temporal_next": {
        "label": "Looks forward",
        "scale": "0-1",
        "definition": (
            "Section 17 only -- what happens at the next session. The fraction of "
            "the 11 sessions whose expert note answered it where the model did too."
        ),
        "caveat": (
            "This is where the source paper reports every model it tested failing, "
            "and ours do too: 0.00 to 0.55. Reported apart from its twin because "
            "averaging the two turned 1.00 and 0.09 into 0.78 and hid exactly this."
        ),
    },
}

#: Reported side by side, never merged. Naming one the ranking would publish a
#: claim the methodology declines to make -- see docs/methodology.md.
RANKING_MEASURE = None

#: Written into the row but not shown as a column.
INTERNAL_MEASURES: tuple[str, ...] = ()

#: Which measures a judge produces. Only these can be compared *between* judges:
#: ROUGE-L, BERTScore and the two temporal columns are computed from the note
#: and the expert note, so they are byte-identical under every judge and
#: reporting "the judges agree perfectly on ROUGE-L" would dress a tautology as
#: a finding. TRACE is the only thing a judge decides here.
JUDGE_MEASURES: tuple[str, ...] = ("trace",)

#: Which iHOPE section each time-bearing measure reads. Separate measures, never
#: averaged -- see `temporal_score` for the numbers that forced the split.
#:
#: Derived from `ihope.TEMPORAL_SECTIONS` rather than repeated, because that
#: module raises when the upstream form changes shape and this would otherwise
#: keep pointing at whatever section 5 and 17 became.
_LOOKS_BACK, _LOOKS_FORWARD = ihope.TEMPORAL_SECTIONS
TEMPORAL_MEASURES = {"temporal_past": _LOOKS_BACK, "temporal_next": _LOOKS_FORWARD}

#: The five TRACE dimensions, in the source paper's order.
TRACE_DIMENSIONS = (
    ("trustworthiness", "the note can be relied on and does not overstate what was said"),
    ("relevance", "the note keeps to what matters clinically about this session"),
    ("accuracy", "every statement in the note is supported by the transcript"),
    ("comprehensiveness", "the note covers what a clinician would need from this session"),
    ("expression", "the note is written clearly and in appropriate clinical language"),
)

#: Our own wording. The authors published no TRACE prompt -- only the dimension
#: names and their definitions in the paper's prose -- so unlike the TN-Eval
#: prompts, which are reproduced byte for byte, this one could not be copied.
#: That is one more reason the column is labelled as a re-implementation.
PROMPT_TRACE = """\
Below is a therapy session transcript and a clinical note written about it.

## Transcript
{conversation}

## Note
{note}

## Dimension
{dimension}: {description}

## Rating Codebook
1: The note fails this dimension throughout.
2: The note fails this dimension more often than not.
3: The note meets this dimension in part.
4: The note meets this dimension with minor lapses.
5: The note fully meets this dimension.

Using the 1 to 5 scale from the rating codebook, rate the note on this \
dimension. Output only the rating [1, 2, 3, 4, 5]:"""


@dataclass(frozen=True)
class TraceTask:
    """One question about one note, and where its answer is cached."""

    dimension: str
    prompt: str

    @property
    def unit(self) -> str:
        return f"trace.{self.dimension}"

    @property
    def kind(self) -> str:
        return "trace"

    @property
    def section(self) -> str:
        return "trace"

    @property
    def accepts(self) -> Callable[[str], bool]:
        """The test that decides whether a reply is an answer: a rating, as
        `score` requires (see `is_a_rating`), handed to the cache so that a
        stored reply which would not count there is re-asked rather than
        reused."""
        return is_a_rating


@dataclass
class Scores:
    """One note's scores, at the levels a result row carries."""

    headline: dict[str, float] = field(default_factory=dict)
    by_section: dict[str, dict[str, float]] = field(default_factory=dict)
    by_criterion: dict[str, float] = field(default_factory=dict)
    sections_used: dict[str, int] = field(default_factory=dict)
    incomplete: dict[str, list[str]] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        return not self.incomplete


def build_trace_tasks(note: str, conversation: str) -> list[TraceTask]:
    """The five questions asked about one note."""
    return [
        TraceTask(
            dimension=name,
            prompt=PROMPT_TRACE.format(
                conversation=conversation, note=note, dimension=name, description=description
            ),
        )
        for name, description in TRACE_DIMENSIONS
    ]


# --- splitting a note into its 17 fields --------------------------------------


def split_sections(note: str) -> dict[int, str]:
    """Map a note's own labels onto the 17 field numbers.

    Reuses `corpus._match_section`, which compares on letters only because the
    labels are hand-written and vary -- extra spaces, dropped parentheses -- and
    which refuses an ambiguous label rather than guessing. "Psychotherapy type"
    and "Psychotherapy technique" share a long prefix, and a loose match once
    credited one field with the other's answers.

    A field the note never labelled is absent from the result, which is not the
    same as a field it answered with "Nil". Both are unfilled; only one of them
    means the model ignored the question.
    """
    found: dict[int, str] = {}
    for part in (note or "").split(corpus.FIELD_SEPARATOR):
        label, separator, value = part.partition(":")
        if not separator:
            continue
        number = corpus._match_section(label)
        if number is None:
            continue
        found.setdefault(number, value.strip())
    return found


#: Whether a field says anything a clinician could use. Lives in `corpus` so the
#: gold notes and the generated ones are read by one rule -- `profile_ihope` used
#: to inline its own copy, and the two would have drifted the moment either moved.
is_filled = corpus.is_filled


def content_of(sections: dict[int, str], fields) -> str:
    """The values of these fields, without their labels and without the empty ones.

    What a text-overlap metric must be given, and what it was not. `render_note`
    builds a note out of 17 field titles with "Nil" wherever the model wrote
    nothing, and the expert note is built the same way -- so comparing the two
    strings compares our scaffolding with itself.

    Measured on the 40 gold notes: a note in which the model wrote **absolutely
    nothing** scored ROUGE-L 0.379 on average and 0.770 on one session, above
    what most real models score. The single published iCARE row was 0.303, below
    the score for writing nothing at all.

    Attributing that floor: dropping the titles takes it from 0.379 to 0.090,
    and dropping the "Nil" values as well takes it to exactly 0.000 on all 40.
    Both halves are needed.
    """
    return " ".join(
        sections[number]
        for number in sorted(fields)
        if number in sections and is_filled(sections[number])
    )


def comparable_pair(note: str, reference: str) -> tuple[str, str]:
    """The two strings a text-overlap metric should compare.

    Restricted to the fields the **expert** answered. A field they left blank
    has nothing to compare against, so whatever the model wrote there is neither
    rewarded nor punished -- the same rule the temporal measures use for their
    denominator.

    The trade-off, stated: a model that pads fields the expert left empty is not
    penalised for it here. iCARE has no conciseness measure to catch that, and
    the alternative is putting the padding back into both sides of a comparison
    it would only add noise to.
    """
    note_sections, gold_sections = split_sections(note), split_sections(reference)
    answered = [n for n in gold_sections if is_filled(gold_sections[n])]
    return content_of(note_sections, answered), content_of(gold_sections, answered)


# --- ROUGE-L ------------------------------------------------------------------

_WORD = re.compile(r"[a-z0-9']+")


def tokenise(text: str) -> list[str]:
    return _WORD.findall((text or "").lower())


def _lcs_length(first: list[str], second: list[str]) -> int:
    """Longest common subsequence, on one row of state rather than a matrix.

    A full note against a full note is a few thousand tokens each side, so the
    quadratic matrix is tens of megabytes per pair and there are 640 pairs. One
    row is the same answer in a few kilobytes.
    """
    if not first or not second:
        return 0
    previous = [0] * (len(second) + 1)
    for a in first:
        current = [0]
        for index, b in enumerate(second):
            current.append(
                previous[index] + 1 if a == b else max(current[index], previous[index + 1])
            )
        previous = current
    return previous[-1]


def rouge_l(candidate: str, reference: str) -> float:
    """LCS-based F-measure, the same statistic the source paper reports.

    F rather than recall: recall alone rewards a note that repeats the whole
    transcript, and at least one model in this benchmark does exactly that when
    it cannot decide what to leave out.
    """
    hypothesis, gold = tokenise(candidate), tokenise(reference)
    if not hypothesis or not gold:
        return 0.0
    common = _lcs_length(hypothesis, gold)
    if not common:
        return 0.0
    precision = common / len(hypothesis)
    recall = common / len(gold)
    return 2 * precision * recall / (precision + recall)


# --- BERTScore ----------------------------------------------------------------


#: Where computed BERTScores live, keyed by the pair they measure.
#:
#: The score is a property of (note, expert note) and nothing else -- not of the
#: judge, not of the run -- but it was recomputed from scratch every time,
#: loading roberta-large and spending about half an hour on 640 pairs before the
#: first judge question was asked. Three runs in one evening paid that three
#: times for identical numbers.
BERT_CACHE = REPO_ROOT / "scores" / "bertscore.json"


def _bert_key(candidate: str, reference: str) -> str:
    return hashlib.sha256(f"{candidate}\x00{reference}".encode()).hexdigest()


def bertscore(
    candidates: list[str], references: list[str], *, cache: Path | None = None
) -> list[float] | None:
    """Embedding similarity, F1, or None when the optional dependency is absent.

    None rather than zero, and never a substitute metric: a column of zeros
    would rank every model equally and look like a measurement. The extra is
    `scoring` in pyproject; without it the page shows the column as not computed
    and says why.

    Cached on the exact pair of strings, so a re-run scores only what changed
    and a model whose note was re-generated is recomputed because its key moved.
    The import is inside the function because it pulls a model download behind
    it, and it is skipped entirely when every pair is already known -- which is
    what makes a cached run start immediately.
    """
    if not candidates:
        return []

    path = cache or BERT_CACHE
    known: dict[str, float] = {}
    if path.exists():
        try:
            known = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            known = {}

    keys = [_bert_key(c, r) for c, r in zip(candidates, references, strict=True)]
    todo = [index for index, key in enumerate(keys) if key not in known]

    if todo:
        try:
            from bert_score import score as _score
        except ImportError:
            return None

        _precision, _recall, f1 = _score(
            [candidates[i] for i in todo], [references[i] for i in todo], lang="en", verbose=False
        )
        for index, value in zip(todo, f1, strict=True):
            known[keys[index]] = float(value)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(known, indent=0, sort_keys=True), encoding="utf-8")

    return [known[key] for key in keys]


# --- putting one note's numbers together --------------------------------------


def parse_likert(answer: str) -> int:
    """TN-Eval's parser, reused so both tracks read a rating the same way."""
    from tnb.scoring.tneval import parse_likert as _parse

    return _parse(answer)


def is_a_rating(answer: str) -> bool:
    """Whether a TRACE answer is a rating at all.

    On the TN-Eval track a judge that will not answer is scored 3 because their
    published numbers were produced that way and ours are compared with them.
    **No such argument applies here.** The TRACE prompt is this repository's own
    wording -- the authors published the five dimension names and their prose
    definitions, never a prompt -- so a fabricated middle-of-the-scale 3 buys
    comparability with nothing and costs a measurement nobody took.

    Two are on disk: `glm-5` session 6 answered "and performance anxiety,
    physical symptoms," and was recorded as a 3.
    """
    from tnb.scoring.tneval import is_a_rating as _is_a_rating

    return _is_a_rating(answer)


def temporal_score(
    note_sections: dict[int, str], gold_sections: dict[int, str], section: int
) -> float | None:
    """One time-bearing field, scored only where the expert answered it.

    A model cannot be marked down for leaving blank what the expert also left
    blank, so the denominator is whether the expert filled *this* field. None
    when they did not -- there is nothing to measure, and 0.0 would be a claim.

    **One field at a time, and never averaged.** The two are not one measure:
    measured across all 16 models, looking back scores 0.97-1.00 and looking
    forward scores 0.00-0.55. Because the expert notes fill section 5 in 34 of
    40 sessions and section 17 in only 11, a blended average is weighted three
    to one toward the easy one and turned 1.00 and 0.09 into 0.78.

    That blend hid the finding this track exists to reproduce -- that models
    fail on the forward-looking field -- which is the second thing concealing
    it, after `is_filled` counting a written-out refusal as an answer.
    """
    if not is_filled(gold_sections.get(section, "")):
        return None
    return float(is_filled(note_sections.get(section, "")))


def aggregate(
    note: str,
    reference: str,
    trace_answers: dict[str, str] | None = None,
    *,
    bert: float | None = None,
) -> Scores:
    """One note's row-level scores.

    TRACE is the mean of whichever of the five dimensions came back, and a note
    missing any of them is named in ``incomplete`` rather than averaged over a
    smaller denominator -- the same rule the TN-Eval scorer follows, and for the
    same reason: judge failures cluster on the notes that are hard to read, so
    the bias from dividing by the survivors runs one way.
    """
    trace_answers = trace_answers or {}
    headline: dict[str, float] = {}
    by_criterion: dict[str, float] = {}
    incomplete: dict[str, list[str]] = {}
    sections_used: dict[str, int] = {}

    # Field values only, over the fields the expert answered -- see
    # `comparable_pair`. Comparing the rendered strings compared our own labels.
    candidate_content, gold_content = comparable_pair(note, reference)
    headline["rouge_l"] = rouge_l(candidate_content, gold_content)
    if bert is not None:
        headline["bertscore"] = bert

    ratings = []
    missing = []
    for name, _description in TRACE_DIMENSIONS:
        unit = f"trace.{name}"
        # An answer that is not a rating is a dimension nobody rated, not a 3.
        # See `is_a_rating`: this track has no paper to stay comparable with.
        if unit in trace_answers and is_a_rating(trace_answers[unit]):
            value = float(parse_likert(trace_answers[unit]))
            by_criterion[name] = value
            ratings.append(value)
        else:
            missing.append(name)
    if ratings and not missing:
        headline["trace"] = sum(ratings) / len(ratings)
        sections_used["trace"] = len(ratings)
    elif missing:
        # Every branch, including none-of-five. `elif ratings` skipped that case
        # entirely, so a note the judge never rated came back `is_complete` and
        # joined its system's headline contributing nothing to TRACE -- the same
        # hole the TN-Eval scorer closed with `missing` and this one never got.
        incomplete["trace"] = missing

    note_sections, gold_sections = split_sections(note), split_sections(reference)
    for measure, section in TEMPORAL_MEASURES.items():
        value = temporal_score(note_sections, gold_sections, section)
        if value is not None:
            headline[measure] = value

    return Scores(
        headline=headline,
        by_section={"trace": dict(by_criterion)} if by_criterion else {},
        by_criterion=by_criterion,
        sections_used=sections_used,
        incomplete=incomplete,
    )


def render_note(sections: dict[str, str]) -> str:
    """Join generated sections into the one string the metrics compare.

    The generator writes 17 units; the expert note is one string with 17
    labelled fields. Rendering ours the same way is what makes the comparison a
    comparison rather than a shape mismatch.
    """
    parts = []
    for number, title in enumerate(icare.SECTION_TITLES, start=1):
        value = (sections.get(f"section-{number:02d}") or "").strip()
        parts.append(f"{title} : {value or 'Nil'}")
    return f" {corpus.FIELD_SEPARATOR} ".join(parts)
