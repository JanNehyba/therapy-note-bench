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
        "caveat": (
            "Counts coverage of a checklist, not judgement. A therapist writes "
            "what matters for the next session and leaves out what does not; "
            "the rubric sees what is present and cannot see why anything was "
            "left out -- which is why every model here scores above the "
            "therapist on it. This is the column the table is ordered by, so "
            "the caveat travels with the ranking: quote the number with this "
            "sentence attached, or do not quote it."
        ),
    },
    "conciseness": {
        "label": "Conciseness",
        "scale": "0-1",
        "definition": (
            "Fraction of the note's sentences that fit at least one rubric item. "
            "1.00 means nothing is off-topic; it does not mean the note is short."
        ),
        "caveat": (
            "Not a length measure, despite the name: a note twice as long scores "
            "the same if every added sentence is on topic. It is also the measure "
            "most moved by the judge's own settings -- raising the thinking "
            "budget from 128 to 256 tokens shifted all nineteen systems and "
            "reordered sixteen of them."
        ),
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

#: Every measure on this track is the judge's. Declared rather than assumed, so
#: the two tracks answer the same question in the same place -- see
#: `icare.JUDGE_MEASURES`, where only one of five is.
JUDGE_MEASURES = ("completeness", "conciseness", "faithfulness")

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
#: A sentence ends at `.!?` followed by whitespace.
#:
#: **A list marker is not a sentence end, and used to be treated as one.** `1. `
#: ends in a full stop followed by a space, so "Plan: 1. Continue weekly
#: sessions. 2. Practise breathing." was cut into four pieces, one of them the
#: string "2." -- and every piece became a question put to the judge: does this
#: sentence serve a rubric criterion? A numeral cannot, so it was a certain No
#: in the numerator and a certain +1 in the denominator. Measured before the
#: fix: the numerals were 65% of `qwen3.5-122b`'s conciseness failures, 62% of
#: `google_gemini-3.7-flash`'s, 56% of `gpt-oss-120b`'s, and 0% for the five
#: models that write prose. The column was partly measuring markdown.
#:
#: **Those three shares cannot be recomputed today, and the reason is worth
#: knowing.** They were measured against the cache as it stood before the
#: repair. Applying the repair re-asked the conciseness questions on every note
#: whose sentence list changed -- 215 of `qwen3.5-122b`'s 1 225 conciseness
#: answers were overwritten -- so the answers the shares were computed from are
#: gone, and pairing today's answers with the old split re-creates exactly the
#: mis-pairing this repair exists to prevent. The measurement that justified the
#: change was destroyed by the change. They stand as a recorded observation,
#: not as a reproducible figure, and are marked as such wherever they appear.
#:
#: What *is* checkable is the effect, and it is in `results/`: conciseness rose
#: +0.090 for `qwen3.5-122b`, +0.075 for `gpt-oss-120b` and +0.059 for
#: `google_gemini-3.7-flash` under `gemini-3.1-pro-preview`, by nearly the same
#: amounts under `gpt-5.6-terra`, and by 0.000 for the five that write prose
#: under both.
#:
#: A piece ending in a standalone one- or two-digit numeral and a full stop is
#: joined to the piece after it, which is the same repair `_ABBREVIATIONS`
#: already makes for "Dr." and lands the marker where a reader would put it.
#: Two digits at most, so a sentence ending in a year -- "relapsed in 2019. She
#: has been sober since" -- still ends there.
#:
#: **Why this took two attempts.** A conciseness answer is cached under the
#: sentence's *index*, `subjective.rubric_conciseness.s02`, so changing what
#: counts as a sentence re-numbers them and pairs every cached answer with a
#: different sentence. 173 of the 942 notes change their sentence list under the
#: fix, and 672 bare numerals stop being questions. Applied on 2026-08-27 and reverted the same hour, because the published
#: conciseness moved for exactly the models with numbered lists and *downward* --
#: the re-pairing, not the fix. `judge.load_cached` could not catch it: it
#: compares a cached answer's prompt digest against the question about to be
#: asked, and neither published judge's answers carried one. They all carry one
#: now, so the re-paired answers are rejected and re-asked instead of returned.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

#: A standalone list marker at the end of a piece: "2." or "Plan: 1." but not
#: "in 2019." and not "v1.2." -- the numeral has to be the whole token.
_LIST_MARKER = re.compile(r"(?:^|\s)\d{1,2}\.$")


def split_sentences(text: str) -> list[str]:
    """Split a note segment into the sentences conciseness is scored over."""
    parts: list[str] = []
    for candidate in _SENTENCE_END.split(text.strip()):
        candidate = candidate.strip()
        if not candidate:
            continue
        previous = parts[-1] if parts else ""
        joins = previous and (
            any(previous.endswith(f"{abbr}.") for abbr in _ABBREVIATIONS)
            or _LIST_MARKER.search(previous) is not None
        )
        if joins:
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
    ours incomparable. Use `is_an_answer` to tell a refusal from a "No" before
    handing it here.
    """
    return 1 if "yes" in (answer or "").lower() else 0


def is_an_answer(answer: str) -> bool:
    """Whether a yes/no question actually got a yes or a no.

    `parse_yes_no` cannot say: it returns 0 both for a judge that said "No" and
    for one that said nothing usable, and their numbers depend on that. This
    separates the two without touching the parser.

    Not hypothetical. 242 of gemini-3.1-pro-preview's cached rubric answers are
    fragments of its own reasoning -- "Evaluate against Rubric Item:**",
    "producingproducing..." -- each scored as a criterion the note failed to
    satisfy. A judge that was cut off mid-thought is not evidence about the note.
    """
    text = (answer or "").lower()
    return "yes" in text or "no" in text


#: A rating, and nothing but a rating. Any digit 1-5 with only punctuation or a
#: bracket around it -- "4", "[4]", "4." -- which is what the prompt asks for.
_RATING = re.compile(r"^\W*([1-5])\W*$")


def is_a_rating(answer: str) -> bool:
    """Whether a 1-5 question actually got a 1-5.

    `parse_likert` always returns a number, so nothing downstream can tell a
    real rating from its fallback. This can.
    """
    return _RATING.match((answer or "").strip()) is not None


def parse_likert(answer: str) -> int:
    """TN-Eval's parser: an unparseable rating becomes 3, the middle of the scale.

    Reproduced with one bug removed rather than two kept. Their fallback scans
    for digits **1 to 5 in ascending order** and returns the first one present
    *anywhere* in the text, so a rating with any other number after it is read
    as that other number:

        "4 (Patient says 2"  ->  2

    That is on disk right now, in `qwen3.5-122b`'s TRACE accuracy for session
    146: the judge answered 4 and was recorded as 2. Scanning ascending is not a
    convention worth reproducing -- it is not even self-consistent, since it
    would read "5 out of 5" as 5 only by luck of ordering. The leading digit is
    taken instead, which is what the prompt asks the judge to emit and what the
    parser reads on every well-formed answer anyway.

    The middle-of-the-scale 3 for a genuinely unparseable answer *is* kept: it
    is their arithmetic and our numbers are compared with theirs. `is_a_rating`
    is how a caller tells that fabricated 3 from a real one.
    """
    text = (answer or "").strip()
    try:
        score = int(text)
    except ValueError:
        # The first digit in *reading* order, which is the rating the judge
        # gave. Their scan went 1,2,3,4,5 and returned whichever appeared
        # anywhere, so "4 (Patient says 2" read as 2. Reading order keeps
        # "Rating: 2" working and fixes that.
        first = re.search(r"[1-5]", text)
        return int(first.group()) if first else 3
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

    #: How many of the four SOAP sections each headline figure averaged. A
    #: three-section mean and a four-section mean print identically and are not
    #: the same measurement, so the count travels with the number.
    sections_used: dict[str, int] = field(default_factory=dict)
    #: Sections left out because the judge did not answer everything the
    #: protocol asks. Named, never silently folded into a smaller denominator.
    incomplete: dict[str, list[str]] = field(default_factory=dict)
    #: Measures the protocol asks for that produced no value at all.
    missing: tuple[str, ...] = ()

    @property
    def is_complete(self) -> bool:
        """Every headline figure exists and rests on all four sections.

        The `missing` half is not redundant. A note whose conciseness answers
        never arrived has no conciseness key at all, so a check that only walked
        `sections_used` found nothing wrong and called the note complete. It
        then joined its system's headline average contributing completeness
        alone -- which quietly shrinks the denominator for the two measures it
        did not have, and the shrinking is not random, because judge failures
        cluster on the notes that are hard to read.
        """
        return (
            not self.incomplete
            and not self.missing
            and all(count == len(SOAP_SECTIONS) for count in self.sections_used.values())
        )

    def rests_on_every_section(self, measure: str) -> bool:
        """Whether one measure was computed from all four SOAP sections.

        Weaker than `is_complete`, and needed where that is too strong. An
        analysis reading only the answer cache cannot reconstruct conciseness
        at all -- the note text is not there, so which sentence questions
        *should* have been asked is unknowable -- and asking it for
        `is_complete` would drop every session it has.

        What it can and must check is that the measure it *does* read is whole.
        A note whose judge answered subjective and objective in full and never
        reached assessment and plan comes back with completeness 1.0 over two
        sections and an empty `incomplete`: nothing in the object says it is
        half a measurement.
        """
        return self.sections_used.get(measure) == len(SOAP_SECTIONS)


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

    **Nothing here invents a measurement, and nothing divides by the answers
    that came back.** Completeness uses the
    protocol's criterion count as its denominator and a section with any
    unanswered criterion is omitted and named in ``incomplete``; the headline
    records in ``sections_used`` how many sections it averaged. Both exist
    because the alternative is silent: a partially-judged note scores like a
    fully-judged one, and judge failures are not random -- they cluster on the
    notes that are hard to read.
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
    incomplete: dict[str, list[str]] = {}

    for section in SOAP_SECTIONS:
        section_scores: dict[str, float] = {}

        # The denominator is the protocol's criterion count, never the number of
        # answers that came back. A judge call that failed is not a criterion the
        # note satisfied and it is not one it missed -- it is unknown, and
        # dividing by the survivors turns "two of six answered, both yes" into a
        # perfect score. Judge failures correlate with hard notes, so that bias
        # runs one way. Same policy as conciseness below: absent, not zero.
        expected = list(criteria_keys(section))
        answered = []
        missing = []
        for key in expected:
            unit = f"{section}.rubric_completeness.{key}"
            # `is_an_answer`, not merely `unit in answers`. `parse_yes_no`
            # returns 0 for "No" and 0 for a fragment of the judge's own
            # reasoning, so without this a judge that ran out of room was
            # scored as the model missing a criterion. Measured across the
            # cache: 43 of 39 696 rubric answers are fragments like
            # "Evaluate against Rubric Item:**", spread over 18 systems and 42
            # notes -- three of them the therapist's, a reference row.
            #
            # The parser itself is untouched. Reproducing TN-Eval's arithmetic
            # means running it on their answers; running it on our
            # infrastructure's failures was never part of their protocol.
            if unit in answers and is_an_answer(answers[unit]):
                value = parse_yes_no(answers[unit])
                by_criterion[key] = float(value)
                answered.append(value)
            else:
                missing.append(key)
        if not missing and expected:
            section_scores["completeness"] = sum(answered) / len(expected)
        elif answered:
            incomplete[section] = missing

        # Same rule as completeness above: a fragment is not a "no". A refused
        # sentence question shrinks the count below `expected_sentences`, so the
        # section is named in `incomplete` rather than averaged over survivors.
        sentences = [
            parse_yes_no(answer)
            for unit, answer in answers.items()
            if unit.startswith(f"{section}.rubric_conciseness.") and is_an_answer(answer)
        ]
        expected_sentences = None if expected_conciseness is None else expected_conciseness[section]
        # `expected_sentences is None` means the note text was not available, so
        # how many sentence questions *should* have been asked is unknowable.
        # That used to publish the mean of whatever arrived: one "yes" of four
        # sentences read as a conciseness of 1.00 with nothing marking it. Not
        # knowing the denominator is not the same as the denominator being the
        # numerator's length, so nothing is published. Live scoring always
        # passes `tasks` and is unaffected; the analyses that do not pass them
        # ask for completeness.
        if sentences and len(sentences) == expected_sentences:
            section_scores["conciseness"] = sum(sentences) / len(sentences)
        elif sentences:
            # The half of the denominator fix that completeness got and this did
            # not. Dividing by the sentences that came back turns "one of four
            # answered, and it was a yes" into a perfect 1.00 -- the exact
            # arithmetic the comment above forbids for completeness.
            #
            # It is also the likeliest loss: `build_tasks` emits conciseness
            # sentences last in each section, so any run that stops early --
            # a budget ceiling, Ctrl-C -- truncates conciseness first.
            incomplete.setdefault(section, [])
            incomplete[section].append(
                f"conciseness: {len(sentences)} of {expected_sentences} sentences"
            )
        elif expected_conciseness is not None and expected_conciseness[section] == 0:
            # TN-Eval's own zero, and only where it applies: the section really
            # had no sentences in it. Reaching this without `tasks` used to score
            # 0.0 as well -- so a note whose conciseness answers never arrived
            # was published as a model that wrote nothing but padding. A zero is
            # a measurement and absence is not one, so absence is now left out
            # and named below.
            section_scores["conciseness"] = 0.0

        # The third place this rule is needed, and the last one to get it.
        # `parse_likert` returns 3 for anything it cannot read, because that is
        # TN-Eval's arithmetic and our numbers are compared with theirs -- but
        # theirs was applied to answers from their protocol, not to our
        # infrastructure's failures. A judge that ran out of room mid-sentence
        # was published as a considered 3, and `faithfulness` is a headline
        # column, so it went straight onto the page.
        #
        # One answer in the cache is such a fragment: `'t like lectures about
        # it", "I` -- a piece of the transcript the judge was quoting -- in
        # `gemini-3.1-pro-preview`, 1 of 11 304 Likert answers. Small, and it is
        # a measurement nobody made. Named in `incomplete` like an unanswered
        # criterion rather than averaged in.
        # **A section with nothing in it is not rated, and this is the reason.**
        # These three ask whether the text is faithful, complete and concise --
        # questions about the *absence of a fault*. A section that says nothing
        # has nothing unfaithful in it, so it collects full marks for being
        # empty. Measured against `gemini-3.1-pro-preview`: an empty SOAP note
        # scores 5.00 on faithfulness, above the therapist's 4.65 and above
        # every model but one, while completeness and conciseness correctly
        # score 0.000.
        #
        # The note is **not** dropped and the section is **not** named in
        # `incomplete`, which would be the worse mistake: a partial note is left
        # out of the mean, so a model that wrote nothing would have its bad note
        # vanish rather than count. The emptiness is already measured -- by
        # completeness, at zero, and by TN-Eval's own conciseness rule, also at
        # zero. What is withheld is only the rating of text that does not exist.
        #
        # Nothing published today changes: none of the 942 notes has an empty
        # section, and across the real ones a shorter section does not score
        # higher (rho +0.07 and -0.01 on the two judges). This is a guard
        # against a model that starts writing thinly, not a repair of a number.
        has_text = expected_conciseness is None or expected_conciseness[section] > 0
        for kind in ("likert_completeness", "likert_conciseness", "likert_faithfulness"):
            unit = f"{section}.{kind}"
            if unit not in answers or not has_text:
                continue
            if is_a_rating(answers[unit]):
                section_scores[MEASURE_OF_UNIT.get(kind, kind)] = float(parse_likert(answers[unit]))
            else:
                incomplete.setdefault(section, [])
                incomplete[section].append(f"{kind}: answered, but not with a rating")

        if section_scores:
            by_section[section] = section_scores

    headline = {}
    sections_used = {}
    missing = []
    for measure in ("completeness", "conciseness", "faithfulness"):
        values = [scores[measure] for scores in by_section.values() if measure in scores]
        if values:
            headline[measure] = sum(values) / len(values)
            # A mean over three sections and a mean over four print the same and
            # are not the same. The count is stored so a view can say which.
            sections_used[measure] = len(values)
        else:
            missing.append(measure)

    return Scores(
        headline=headline,
        by_section=by_section,
        by_criterion=by_criterion,
        sections_used=sections_used,
        incomplete=incomplete,
        missing=tuple(missing),
    )
