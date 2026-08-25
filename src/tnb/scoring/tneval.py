"""TN-Eval's reference-free scoring protocol, reproduced from their code.

Five prompts and 23 rubric criteria, copied byte for byte from TN-Eval's
``src/run_metrics_reference_free.py`` and ``src/constant.py`` (Apache-2.0,
attributed in NOTICE). Their parsers are reproduced too, quirks included:
anything that is not "yes" counts as no, and an unparseable Likert rating
becomes 3. Both matter — a judge that fails to answer is scored as a "no" and
as a middling rating, and that is how their published numbers were produced.

What is *not* theirs is the aggregation into a single headline number, because
they never published one. See :func:`aggregate`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: Bumped whenever anything reaching the judge changes. Result rows carry it and
#: the leaderboard never mixes two versions -- see docs/methodology.md.
JUDGE_PROMPT_VERSION = "tneval-rubric-v1"

#: The four SOAP sections, in TN-Eval's order.
SOAP_SECTIONS = ("subjective", "objective", "assessment", "plan")

#: What each reported measure is, on what scale, and what a reader must know
#: before believing it.
#:
#: Two scales sit side by side in this protocol and nothing in the numbers says
#: which is which: a completeness of 0.65 and a faithfulness of 4.98 look like
#: the same kind of quantity and are not. Every view renders `scale` beside the
#: heading and `caveat` beside the table, so the answer travels with the number
#: instead of living in a footnote.
MEASURES: dict[str, dict[str, str]] = {
    "completeness": {
        "label": "Completeness",
        "scale": "0-1",
        "definition": (
            "Fraction of the section's rubric criteria the judge found present. "
            "0.65 means about two thirds of the required items are in the note."
        ),
        "caveat": "",
    },
    "conciseness": {
        "label": "Conciseness",
        "scale": "0-1",
        "definition": (
            "Fraction of the note's sentences that fit at least one rubric item. "
            "1.00 means nothing is off-topic; it does not mean the note is short."
        ),
        "caveat": "",
    },
    "faithfulness": {
        "label": "Faithfulness",
        "scale": "1-5",
        "definition": (
            "Whether the note contradicts the transcript, rated 1 to 5, where 5 is "
            "no inaccuracies. TN-Eval's protocol has no criterion-based version of "
            "this one, so it stays a Likert scale."
        ),
        "caveat": (
            "A different scale from the two columns beside it, and a weak one: "
            "TN-Eval measured Krippendorff's alpha of 0.18 between trained "
            "therapists on this rating. Read it as a flag for gross invention, "
            "not as a ranking."
        ),
    },
    "likert_completeness": {
        "label": "Completeness (Likert)",
        "scale": "1-5",
        "definition": ("The completeness question asked as a 1-5 rating instead of a checklist."),
        "caveat": "Kept only so the two forms can be compared; not displayed.",
    },
    "likert_conciseness": {
        "label": "Conciseness (Likert)",
        "scale": "1-5",
        "definition": "The 1-5 counterpart of conciseness.",
        "caveat": "Kept only so the two forms can be compared; not displayed.",
    },
}

#: The judge answers a unit named `likert_faithfulness`; the measure it produces
#: is named `faithfulness`. The unit name is part of the answer-cache path and
#: must not move -- this maps one to the other in the single place that stores a
#: score, so a measure can never be written under a name a view does not read.
MEASURE_OF_UNIT = {"likert_faithfulness": "faithfulness"}

#: Written into `by_section` but deliberately not on the leaderboard. Named so
#: that the test which pairs produced keys against displayed columns can tell
#: "internal on purpose" from "computed and silently dropped".
INTERNAL_MEASURES = ("likert_completeness", "likert_conciseness")

#: The measure this track is ranked by. Everything else on the row is context.
RANKING_MEASURE = "completeness"

#: Verbatim from TN-Eval's ``rubric_prompt_completeness``.
PROMPT_COMPLETENESS = """\
Below is a behavioral therapy progress note segment. The rubric item outlines one of the necessary components for the note. Verify if the rubric item presents in the progress note segment. 

## Note Segment
{note_segment}

## Rubric Item (an item that should present in the note segment)
{rubric_item}

Does the note segment contain the rubric item? Response in [Yes, No] with no other content:"""

#: Verbatim from TN-Eval's ``rubric_prompt_conciseness``.
PROMPT_CONCISENESS = """\
Below is a sentence from a behavioral therapy progress note. The rubrics outlines the necessary components for the note. Verify if the note sentence fit in one of the rubric items.

## Note Sentence
{note_sentence}

## Rubrics (a list of items that should present in the note segment)
{rubrics}

Does the note sentence fit in one of the rubric items? Response in [Yes, No] with no other content:"""

#: Verbatim from TN-Eval's ``rubric_prompt_likert_completeness``.
PROMPT_LIKERT_COMPLETENESS = """\
Below is a behavioral therapy conversation along with a corresponding progress note segment. The rubrics outline the necessary components for the note. Based on the conversation and rubrics, evaluate the completeness of the note segment.

## Conversation
{conversation}

## Note Segment
{note_segment}

## Rubrics (a list of items that should present in the note segment)
{rubrics}

## Rating Codebook
1: The note segment is missing most of the key information from the conversation.
2: The note segment includes some important details but is significantly incomplete.
3: The note segment contains a moderate amount of important information.
4: The note segment captures most of the key information from the conversation.
5: The note segment comprehensively captures all the key information.

Using the 1 to 5 scale from the rating codebook, rate the completeness of the note segment. Output only the rating [1, 2, 3, 4, 5]:"""

#: Verbatim from TN-Eval's ``rubric_prompt_likert_conciseness``.
PROMPT_LIKERT_CONCISENESS = """\
Below is a behavioral therapy conversation along with a corresponding progress note segment. The rubrics outline the necessary components for the note. Based on the conversation and rubrics, evaluate the conciseness of the note segment.

## Conversation
{conversation}

## Note Segment
{note_segment}

## Rubrics (a list of items that should present in the note segment)
{rubrics}

## Rating Codebook
1: The note segment includes substantial non-important information that detracts from the main points.
2: The note segment includes non-important information that needs to be reduced.
3: The note segment includes some non-important information but does not heavily detract from the main points.
4: The note segment includes minor non-critical information.
5: The note segment includes no non-important information, making it concise and focused.

In the scale of 1 to 5, rate the conciseness of the note segment following the rating codebook. Output only the rating [1, 2, 3, 4, 5]:"""

#: Verbatim from TN-Eval's ``rubric_prompt_likert_faithfulness``.
PROMPT_LIKERT_FAITHFULNESS = """\
Below is a behavioral therapy conversation along with a corresponding progress note segment. Verify the faithfulness of the note segment based on the conversation.

## Conversation
{conversation}

## Note Segment
{note_segment}

## Rating Codebook
1: The note segment contains significant inaccuracies or false information.
2: The note segment contains several inaccuracies or false information.
3: The note segment may contain some inaccuracies or false information.
4: The note segment contains minor non-critical inaccuracies or false information.
5: The note segment contains no inaccuracies or false information.

In the scale of 1 to 5, rate the faithfulness of the note segment following the rating codebook. Output only the rating [1, 2, 3, 4, 5]:"""

#: sha256 of each prompt as published on 2026-08-24. An edit to the text
#: above -- even one space -- changes this and fails the offline test.
UPSTREAM_SHA256 = {
    "PROMPT_COMPLETENESS": "442078a5ce4341a54645d26091bf2f53bdfbc9874943459e303e68d900374188",
    "PROMPT_CONCISENESS": "1071609c3c9cf325d5dc981e44593dcaab8421197b05ff90ee2adecdc380b398",
    "PROMPT_LIKERT_COMPLETENESS": "97821d49da76e6958e988921996af718323356f269647cfe63fe7053a7be7895",
    "PROMPT_LIKERT_CONCISENESS": "f189b323ec9abbd238dca6be6d60e9c981a4ccc6f6f02de73a3dc704b7358884",
    "PROMPT_LIKERT_FAITHFULNESS": "074e526ae1da152bc9808b44b17de1e8b8385991c650d392d8d21ebe8404ff1b",
}

#: TN-Eval's ``CHECKBOX_MAPPING``: 23 completeness criteria, keyed
#: ``<section>-<slug>``. Six subjective, five objective, eight assessment,
#: four plan. The wording is what the judge is asked about, so it is copied
#: rather than paraphrased.
CHECKBOX_MAPPING = {
    "subjective-chief-complaint": (
        "Chief complaint: The reason why the client is seeking therapy or a description of symptoms."
    ),
    "subjective-symptoms": (
        "Symptoms: The client’s own description of their feelings, thoughts, and behaviors along with the severity."
    ),
    "subjective-history": (
        "History: Relevant background information, including any past medical, therapy, or behavioral issues."
    ),
    "subjective-goals": "Client's Goals: What the client hopes to achieve through therapy.",
    "subjective-homework": (
        "Homework from previous sessions: Reviewing homework from the previous sessions and note client’s compliance."
    ),
    "subjective-quotes": (
        "Quotes: Direct quotes from the client capturing their exact words and emotional tone."
    ),
    "objective-behavior": (
        "Client’s observed behavior: The therapist's observations of the client's behavior, mood, appearance, and affect during the session."
    ),
    "objective-mental-status": (
        "Mental Status: Observations regarding the client’s appearance, speech, thought processes, and orientation."
    ),
    "objective-assessment-tools": (
        "Assessment Tools: Results from any standardized assessments or scales used during the session."
    ),
    "objective-therapy-activities": (
        "Therapy Activities: Description of specific interventions or activities conducted during the session."
    ),
    "objective-interventions": (
        "Interventions: Applied interventions and treatment plans (MI, Cognitive Restructuring, DBT, etc.). Focus on describing active interventions provided rather than passive ones."
    ),
    "assessment-diagnosis": (
        "Diagnosis/Symptoms: Any formal diagnoses made based on DSM-5 criteria or other diagnostic tools."
    ),
    "assessment-triggers": "Identifying Triggers: Any triggers shown by the client.",
    "assessment-progress": (
        "Progress: Evaluation of the client's progress toward their therapeutic goals."
    ),
    "assessment-analysis": (
        "Analysis: The therapist's interpretation of how the client's subjective report and objective observations relate to their overall condition."
    ),
    "assessment-response": (
        "Response to interventions: The client's response to the provided interventions."
    ),
    "assessment-overall-progress": "Overall/high-level progress: Overall progress made by the client.",
    "assessment-goals": (
        "Treatment Goals: Specific, measurable, achievable, relevant, and time-bound (SMART) goals for the client. Adjustment to the treatment goals."
    ),
    "assessment-stages": (
        "Stages of change: Client's stage of change (Pre-contemplation, contemplation, action, maintenance, etc.)."
    ),
    "plan-interventions": (
        "Future Interventions: Planned therapeutic techniques or strategies to be used in future sessions."
    ),
    "plan-follow-up": (
        "Follow-Up: Scheduling of the next session and any referrals to other professionals if needed. Note the date for the next appointment if decided upon."
    ),
    "plan-adjustment": (
        "Adjustment of medication/intervention: Any adjustments made to medications or interventions."
    ),
    "plan-homework": (
        "Homework: Assignments or activities for the client to work on between the sessions."
    ),
}


#: TN-Eval split note text into sentences with ``nltk.sent_tokenize``. Pulling
#: in nltk and its punkt model for this is a network fetch at scoring time and a
#: multi-megabyte dependency, so the split is done here — on sentence-ending
#: punctuation followed by whitespace, with the common abbreviations that would
#: otherwise split mid-sentence held back. Conciseness is a *ratio* over
#: sentences, so a different split changes the denominator; the difference is
#: recorded in docs/limitations.md rather than hidden.
_ABBREVIATIONS = ("Dr", "Mr", "Mrs", "Ms", "e.g", "i.e", "vs", "etc", "St", "Prof")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    """Split a note segment into the sentences conciseness is scored over."""
    parts: list[str] = []
    for candidate in _SENTENCE_END.split(text.strip()):
        candidate = candidate.strip()
        if not candidate:
            continue
        previous = parts[-1] if parts else ""
        if previous and any(previous.endswith(f"{abbr}.") for abbr in _ABBREVIATIONS):
            parts[-1] = f"{previous} {candidate}"
        else:
            parts.append(candidate)
    return parts


def rubrics_for(section: str) -> list[str]:
    """The criteria that belong to one SOAP section, in TN-Eval's order."""
    return [value for key, value in CHECKBOX_MAPPING.items() if key.split("-")[0] == section]


def criteria_keys(section: str) -> list[str]:
    return [key for key in CHECKBOX_MAPPING if key.split("-")[0] == section]


def parse_yes_no(answer: str) -> int:
    """TN-Eval's parser. Anything that is not "yes" is a no, including silence.

    Reproduced rather than improved: a judge that refuses to answer is scored as
    a missing rubric item in their numbers too, and changing that would make
    ours incomparable.
    """
    return 1 if "yes" in (answer or "").lower() else 0


def parse_likert(answer: str) -> int:
    """TN-Eval's parser: an unparseable rating becomes 3, the middle of the scale."""
    text = (answer or "").strip()
    try:
        score = int(text)
    except ValueError:
        for candidate in range(1, 6):
            if str(candidate) in text:
                return candidate
        return 3
    return score if 1 <= score <= 5 else 3


@dataclass(frozen=True)
class JudgeTask:
    """One question for the judge about one note.

    ``unit`` is what the answer is cached under, so a scoring run that stops
    halfway resumes at the question it stopped on rather than at the note.
    """

    kind: str
    section: str
    prompt: str
    #: Rubric key for a completeness question, sentence index for conciseness.
    item: str = ""

    @property
    def unit(self) -> str:
        return f"{self.section}.{self.kind}{f'.{self.item}' if self.item else ''}"

    @property
    def is_likert(self) -> bool:
        return self.kind.startswith("likert")


def build_tasks(note: dict[str, str], conversation: str) -> list[JudgeTask]:
    """Every judge call one note needs, in TN-Eval's order.

    Roughly 60 per note: 23 completeness (one per criterion), one per sentence
    for conciseness, and three Likert ratings per section.
    """
    tasks: list[JudgeTask] = []

    for section in SOAP_SECTIONS:
        segment = note.get(section, "") or ""
        rubrics = "\n".join(rubrics_for(section))

        for prompt, kind in (
            (PROMPT_LIKERT_COMPLETENESS, "likert_completeness"),
            (PROMPT_LIKERT_CONCISENESS, "likert_conciseness"),
            (PROMPT_LIKERT_FAITHFULNESS, "likert_faithfulness"),
        ):
            filled = (
                prompt.replace("{conversation}", conversation)
                .replace("{note_segment}", segment)
                .replace("{rubrics}", rubrics)
            )
            tasks.append(JudgeTask(kind=kind, section=section, prompt=filled))

        for key in criteria_keys(section):
            tasks.append(
                JudgeTask(
                    kind="rubric_completeness",
                    section=section,
                    item=key,
                    prompt=PROMPT_COMPLETENESS.replace("{note_segment}", segment).replace(
                        "{rubric_item}", CHECKBOX_MAPPING[key]
                    ),
                )
            )

        for index, sentence in enumerate(split_sentences(segment)):
            tasks.append(
                JudgeTask(
                    kind="rubric_conciseness",
                    section=section,
                    item=f"s{index:02d}",
                    prompt=PROMPT_CONCISENESS.replace("{note_sentence}", sentence).replace(
                        "{rubrics}", rubrics
                    ),
                )
            )

    return tasks


@dataclass
class Scores:
    """One note's scores, at the three levels a result row carries."""

    headline: dict[str, float] = field(default_factory=dict)
    by_section: dict[str, dict[str, float]] = field(default_factory=dict)
    by_criterion: dict[str, float] = field(default_factory=dict)


def aggregate(answers: dict[str, str], tasks: list[JudgeTask] | None = None) -> Scores:
    """Turn raw judge answers into scores, keyed by :attr:`JudgeTask.unit`.

    Per section, TN-Eval's own arithmetic: completeness is the fraction of that
    section's criteria the judge found, conciseness the fraction of its
    sentences that fit any criterion, and a section with no sentences scores 0
    for conciseness — their code does exactly that rather than skipping it.

    **The headline is ours, not theirs.** They publish per-section numbers and
    no overall figure, so this averages the four sections equally. An eight-item
    section is not twice as important as a four-item one, and `by_criterion` is
    kept so anyone who disagrees can recompute item-weighted instead.

    Pass ``tasks`` when the questions that *should* have been answered are known.
    Without it a section whose conciseness answers are simply missing scores a
    measured-looking 0.0, indistinguishable from a section where the judge
    rejected every sentence. TN-Eval's zero is for a section with no sentences
    in it; absence is not that, and is left out instead.
    """
    expected_conciseness = None
    if tasks is not None:
        expected_conciseness = {
            section: sum(
                1 for task in tasks if task.section == section and task.kind == "rubric_conciseness"
            )
            for section in SOAP_SECTIONS
        }
    by_section: dict[str, dict[str, float]] = {}
    by_criterion: dict[str, float] = {}

    for section in SOAP_SECTIONS:
        section_scores: dict[str, float] = {}

        completeness = []
        for key in criteria_keys(section):
            unit = f"{section}.rubric_completeness.{key}"
            if unit in answers:
                value = parse_yes_no(answers[unit])
                by_criterion[key] = float(value)
                completeness.append(value)
        if completeness:
            section_scores["completeness"] = sum(completeness) / len(completeness)

        sentences = [
            parse_yes_no(answer)
            for unit, answer in answers.items()
            if unit.startswith(f"{section}.rubric_conciseness.")
        ]
        if sentences:
            section_scores["conciseness"] = sum(sentences) / len(sentences)
        elif expected_conciseness is None or expected_conciseness[section] == 0:
            # TN-Eval's own zero: the section had no sentences to judge.
            section_scores["conciseness"] = 0.0

        for kind in ("likert_completeness", "likert_conciseness", "likert_faithfulness"):
            unit = f"{section}.{kind}"
            if unit in answers:
                section_scores[MEASURE_OF_UNIT.get(kind, kind)] = float(parse_likert(answers[unit]))

        if section_scores:
            by_section[section] = section_scores

    headline = {}
    for measure in ("completeness", "conciseness", "faithfulness"):
        values = [scores[measure] for scores in by_section.values() if measure in scores]
        if values:
            headline[measure] = sum(values) / len(values)

    return Scores(headline=headline, by_section=by_section, by_criterion=by_criterion)
