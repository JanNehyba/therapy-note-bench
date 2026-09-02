"""PDSQI-9: a published, validated instrument for the quality of a clinical note.

Reproduced from the Provider Documentation Summarization Quality Instrument
(PDSQI-9), Croxford et al., published under CC BY 4.0. It is itself an
LLM-centric adaptation of the Physician Documentation Quality Instrument
(PDQI-9; Stetson et al., Appl Clin Inform 2012, PMC3347480): two attributes were
dropped, two added, and the scoring instructions rewritten for text a model
wrote. See NOTICE for the citation and the licence.

Why a published instrument rather than a rubric of our own. Nothing else in this
repository invents a measure when one exists -- the TN-Eval rubric and the iCARE
sections are both reproduced rather than designed -- and a column called
"quality" that this repository made up would mean whatever a reader guessed. The
number that matters is inter-rater reliability among trained physicians:
Krippendorff's alpha 0.575, ICC 0.867, Cronbach's alpha 0.879. For comparison,
TN-Eval measured alpha 0.18 between two therapists on faithfulness. 0.575 is
also a ceiling: a judge cannot be expected to agree with a person better than
people agree with each other.

**Three things about this instrument do not fit our task, and all three are
published on the page rather than smoothed over.**

1. It was developed and validated on a corpus from which *psychiatry notes were
   explicitly excluded*. It is a validated instrument, but not on our material.
2. It rates a *summary of several earlier notes*, not a note written from one
   session. That is why its first attribute, "Cited", asks whether assertions
   carry citations back to the source documents. We have no source documents, so
   that attribute has nothing to measure here and is dropped -- items 2 to 9
   remain, which is eight. (PDSQI-**9** counts its attributes, not its
   numbering: `DROPPED` says the same thing and this sentence used to say
   "ninth", which is the one place in the file the two disagreed.)
3. Its wording therefore says "summary" and "source notes" throughout. Asking a
   judge to rate "the summary" when it is looking at a session note invites it
   to rate the wrong thing, so two substitutions are made and named:
   summary -> note, source note(s)/original input -> session transcript.
   `ORIGINAL_WORDING` keeps the published phrasing beside each change so the
   adaptation is auditable rather than asserted.

**Two attributes need the transcript; six do not.** `Accurate` and `Thorough`
ask whether the note is true and complete, which cannot be judged without the
session. That is not a design choice here -- it falls out of the instrument --
and it happens to fall exactly where a confidential corpus draws its own line:
the six note-only attributes can be asked about a real client's note without the
transcript leaving the machine it was generated on, and the two that need the
transcript can be asked only where the transcript is public.

**One polarity is inverted, deliberately.** The instrument asks "is there
presence of stigmatizing language?", where yes is the bad answer. Every other
column here is better when higher, and one column that runs the other way inside
the same table is a trap for a reader skimming it. The judge is asked the
published question unchanged; only the reported figure is flipped, to the
fraction of notes *free* of stigmatizing language.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from tnb.tasks import soap

#: Bumped whenever anything reaching this judge changes. Rows carry it and the
#: leaderboard never mixes two versions.
JUDGE_PROMPT_VERSION = "pdsqi9-note-v1"

#: The published phrasing, beside what this repository asks instead. Kept so the
#: adaptation can be checked rather than taken on trust, and so a reader can see
#: it is two word substitutions and not a rewrite.
ORIGINAL_WORDING = {
    "summary": "note",
    "source notes": "session transcript",
    "original input": "session transcript",
}

#: The attribute PDSQI-9 numbers 1, dropped here. It asks whether assertions
#: carry citations back to the source documents; a note written from a single
#: transcript has no source documents to cite, so there is nothing to rate.
DROPPED = ("cited",)


@dataclass(frozen=True)
class Attribute:
    """One PDSQI-9 attribute, its question, and how it is answered."""

    key: str
    #: The item's number in the published instrument, so a reader can find it.
    item: int
    label: str
    question: str
    definition: str
    #: Extra instruction the instrument gives the rater before the scale.
    guidance: str = ""
    #: The published anchors for 1 to 5. Empty for the binary attribute.
    anchors: tuple[str, ...] = ()
    #: Whether answering honestly requires the session transcript.
    needs_transcript: bool = False
    #: Yes/No rather than 1-5, as published.
    binary: bool = False


ATTRIBUTES: tuple[Attribute, ...] = (
    Attribute(
        key="accurate",
        item=2,
        label="Accurate",
        question="Is the note accurate?",
        definition="The note is true and free of incorrect information.",
        guidance=(
            "Incorrect information can be a result of fabrication or falsification. "
            "Fabrication is when the response contains entirely made-up information or "
            "data and includes plausible but non-existent facts in the note. "
            "Falsification is when the response contains distorted information and "
            "includes changing critical details of facts, so they are no longer true "
            "from the session transcript."
        ),
        anchors=(
            "Multiple major errors with overt falsifications or fabrications",
            "A major error in assertion occurs with an overt falsification or fabrication",
            "At least one assertion contains a misalignment that is stated from the session "
            "transcript but the wrong context, including incorrect specificity in diagnosis "
            "or treatment",
            "At least one assertion is misaligned to the session transcript or timing but "
            "still factual in diagnosis, treatment, etc.",
            "All assertions can be traced back to the session transcript",
        ),
        needs_transcript=True,
    ),
    Attribute(
        key="thorough",
        item=3,
        label="Thorough",
        question="Is the note thorough without any omissions?",
        definition="The note should thoroughly cover all critical patient issues.",
        guidance=(
            "Identify any pertinent or potentially pertinent omissions. Pertinent "
            "omissions refer to essential information required for the specific use case "
            "or intended provider, where missing details could directly impact patient "
            "care decisions. Potentially pertinent omissions include relevant details for "
            "clinical understanding that may not directly influence the current use case "
            "but would still be useful to know."
        ),
        anchors=(
            "More than one pertinent omission occurs",
            "One pertinent and multiple potentially pertinent occur",
            "Only one pertinent omission occurs",
            "Some potentially pertinent omissions occur",
            "No pertinent or potentially pertinent omission occur",
        ),
        needs_transcript=True,
    ),
    Attribute(
        key="useful",
        item=4,
        label="Useful",
        question="Is the note useful?",
        definition=(
            "All the information is in there that is useful to the target "
            "provider/intended audience. The note is extremely relevant, providing "
            "valuable information and/or analysis."
        ),
        anchors=(
            "No assertions are pertinent to the target user",
            "Some assertions are pertinent to the target user",
            "Assertions are pertinent to target provider but level of detail inappropriate "
            "(too detailed or not detailed enough)",
            "Not adding any non-pertinent assertions but some assertions are potentially "
            "pertinent to target user",
            "Not adding any non-pertinent assertions and level of detail is appropriate to "
            "targeted user",
        ),
    ),
    Attribute(
        key="organized",
        item=5,
        label="Organized",
        question="Is the note organized?",
        definition=(
            "The note is well-formed and structured in a way that helps the reader "
            "understand the patient's clinical course."
        ),
        anchors=(
            "All assertions presented out of order and groupings incoherent "
            "(completely disorganized)",
            "Some assertions presented out of order OR grouping incoherent",
            "No change in order or grouping (temporal or systems/problem based) from the "
            "session transcript",
            "Logical order or grouping (temporal or systems/problem based) for all "
            "assertions but not both",
            "All assertions made with logical order and grouping (temporal or "
            "systems/problem based) - completely organized",
        ),
    ),
    Attribute(
        key="comprehensible",
        item=6,
        label="Comprehensible",
        question="Is the note comprehensible with clarity of language?",
        definition=(
            "The note is clear, without ambiguity or sections that are difficult to understand."
        ),
        anchors=(
            "Words in sentence structure are overly complex, inconsistent, with "
            "terminology that is unfamiliar to the target user",
            "Any use of overly complex, inconsistent, or terminology that is unfamiliar to "
            "target user",
            "Unchanged choice of words from the session transcript with inclusion of overly "
            "complex terms when there was opportunity for improvement",
            "Some inclusion of change in structure and terminology towards improvement",
            "Plain language completely familiar and well-structured to target user",
        ),
    ),
    Attribute(
        key="succinct",
        item=7,
        label="Succinct",
        question="Is the note succinct with economy of language?",
        definition="The note is brief, to the point, and without redundancy.",
        anchors=(
            "Too wordy across all assertions with redundancy in syntax and semantic",
            "More than one assertion has contextual semantic redundancy",
            "At least one assertion has contextual semantic redundancy or multiple "
            "syntactic assertions",
            "No syntax redundancy in assertions and at least one could have been shorter in "
            "contextualized semantics",
            "All assertions are captured with fewest words possible and without any "
            "redundancy in syntax or semantics",
        ),
    ),
    Attribute(
        key="synthesized",
        item=8,
        label="Synthesized",
        question="Is there a need for abstraction in the note?",
        definition=(
            "The note reflects an understanding of the patient's status and ability to "
            "develop a plan of care."
        ),
        guidance=(
            "Abstraction goes beyond simply extracting exact phrases or sentences from the "
            "session transcript. Instead, it involves paraphrasing and synthesizing the "
            "information to produce new sentences that capture the core meaning. This is "
            "similar to how a human might read a passage and then restate the key ideas in "
            "their own words."
        ),
        anchors=(
            "Incorrect reasoning or grouping in the connections between the assertions",
            "Abstraction performed when not needed OR groupings were made between "
            "assertions that were accurate but not appropriate",
            "Assertions are independently stated without any reasoning or groups over the "
            "assertions when there could have been one (missed opportunity to abstract)",
            "Groupings of assertions occur into themes but limited to fully formed "
            "reasoning for a final, clinically relevant diagnosis or treatment",
            "Goes beyond relevant groups of events and generates reasoning over the events "
            "into a note that is fully integrated for an overall clinical picture",
        ),
    ),
    Attribute(
        key="stigmatizing",
        item=9,
        label="Free of stigmatizing language",
        question="Is there presence of stigmatizing language in the note?",
        definition=(
            "The note is free of discrediting or exaggerated words, of judgment or "
            "labelling, and uses person-first language."
        ),
        guidance=(
            "Refrain from using discrediting or exaggerated words, such as claims, insists, "
            'or reportedly. Judgment or discrediting words that suggest doubt ("He claims '
            'or insists that he is in pain"). Person-first language such as the "patient '
            'with diabetes" instead of the "diabetic patient". Minimize blame, labelling '
            'and judgment. Language that a person "is" the problem, rather than "has" a '
            "problem."
        ),
        binary=True,
    ),
)

ATTRIBUTE_KEYS: tuple[str, ...] = tuple(a.key for a in ATTRIBUTES)
_BINARY_ATTRIBUTES: frozenset[str] = frozenset(a.key for a in ATTRIBUTES if a.binary)

#: Answerable from the note alone. The two that are not -- accurate and thorough
#: -- ask whether the note is true and complete, which needs the session.
NOTE_ONLY_KEYS: tuple[str, ...] = tuple(a.key for a in ATTRIBUTES if not a.needs_transcript)
NEEDS_TRANSCRIPT_KEYS: tuple[str, ...] = tuple(a.key for a in ATTRIBUTES if a.needs_transcript)

#: Printed once for the whole instrument, not once per column: it is a property
#: of PDSQI-9 and not of any one attribute, and the leaderboard was printing it
#: under all eight of them. The page groups it by `instrument`.
_CAVEAT = (
    "The instrument was validated on multi-note clinical summaries from a corpus that "
    "excluded psychiatry, not on notes written from a single session. Its authors report "
    "Krippendorff's alpha 0.575 between trained physicians on that material -- a published "
    "ceiling, not a measurement of this judge on these notes. Three of the eight -- accurate, "
    "succinct and free of stigmatising language -- can be won by saying nothing: an empty note "
    "scores 5.00, 5.00 and 1.00 on them, so read them as things a note can fail, never as "
    "things it can win."
)

MEASURES: dict[str, dict[str, str]] = {
    attribute.key: {
        "label": attribute.label,
        "scale": "0-1" if attribute.binary else "1-5",
        "definition": (
            f"{attribute.definition} PDSQI-9 item {attribute.item}, "
            + (
                "answered yes or no and reported as the fraction of notes free of it."
                if attribute.binary
                else "rated 1 (not at all) to 5 (extremely)."
            )
        ),
        "caveat": _CAVEAT,
    }
    for attribute in ATTRIBUTES
}

#: No composite. The instrument's own authors report the attributes separately,
#: and averaging a 1-5 rating with a yes/no would invent a number nobody
#: validated.
RANKING_MEASURE = None

#: Every attribute is a judge's decision, so all of them can be compared between
#: judges.
JUDGE_MEASURES: tuple[str, ...] = ATTRIBUTE_KEYS

PROMPT = """\
Below is a clinical note written about a psychotherapy session.
{transcript_block}
## Note
{note}

## Question
{question}

{definition}{guidance}

## Rating
{scale}

{closing}"""

_TRANSCRIPT_BLOCK = """
## Session transcript
{transcript}
"""

_LIKERT_CLOSING = (
    "Using the 1 to 5 scale above, rate the note. Output only the rating [1, 2, 3, 4, 5]:"
)
_BINARY_CLOSING = "Answer the question about the note. Output only Yes or No:"

#: A rating, and nothing but a rating. Brackets and a trailing stop are
#: tolerated; a sign is not, because a stray minus would otherwise be read as
#: decoration and "-1" would come back as 1.
_RATING = re.compile(r"^[^\w+-]*([1-5])[^\w+-]*$")
_YES_NO = re.compile(r"^[^\w]*(yes|no)[^\w]*$", re.IGNORECASE)


@dataclass(frozen=True)
class PdsqiTask:
    """One attribute asked about one note, and where its answer is cached."""

    attribute: str
    prompt: str

    @property
    def unit(self) -> str:
        return f"pdsqi.{self.attribute}"

    @property
    def kind(self) -> str:
        return "pdsqi"

    @property
    def section(self) -> str:
        return "pdsqi"

    @property
    def accepts(self) -> Callable[[str], bool]:
        """The test that decides whether a reply is an answer to this attribute:
        a yes or a no for the binary one, a rating for the rest. The same test
        `score` applies, handed to the cache so that a stored reply which would
        not count there is re-asked rather than reused."""
        if self.attribute in _BINARY_ATTRIBUTES:
            return lambda answer: parse_yes_no(answer) is not None
        return is_a_rating


def is_a_rating(answer: str) -> bool:
    """Whether a 1-5 question actually got a 1-5."""
    return _RATING.match((answer or "").strip()) is not None


def parse_rating(answer: str) -> int | None:
    """The rating, or None -- never a fabricated middle of the scale.

    `tneval.parse_likert` returns 3 for anything unparseable, which is TN-Eval's
    own arithmetic and is kept there because our numbers are compared against
    their published ones. Nothing is compared against a published PDSQI-9 number,
    so an invented 3 here would buy comparability with nobody and cost a
    measurement nobody took.
    """
    match = _RATING.match((answer or "").strip())
    return int(match.group(1)) if match else None


def parse_yes_no(answer: str) -> bool | None:
    """True for yes, False for no, None for anything else."""
    match = _YES_NO.match((answer or "").strip())
    return match.group(1).lower() == "yes" if match else None


def render_note(note: dict[str, str]) -> str:
    """One SOAP note as the single block of text the instrument rates.

    PDSQI-9 asks about a note, not about a section: "is it organized?" has no
    answer for a quarter of a note. So the four sections are joined, and how
    they are joined is part of the prompt and therefore part of
    `JUDGE_PROMPT_VERSION`.

    Two choices, both to keep the presentation from becoming a measurement:

    - The order is `soap.SECTIONS`, never the dictionary's. A note parsed out of
      a model's reply carries whatever order that model wrote in, and
      "organized" would then be scoring the order our parser happened to see.
    - All four headings are always present, so every note is shown in the same
      shape. A model that wrote no plan is presented with an empty Plan, which
      is what a reader would find; a model that wrote no plan and was shown
      three headings would look tidier for the omission.
    """
    return "\n\n".join(
        f"{section.capitalize()}: {(note.get(section) or '').strip()}" for section in soap.SECTIONS
    )


def has_content(note: str) -> bool:
    """Whether there is a note here to rate at all.

    Three of the eight attributes ask about the *absence of a fault* -- is
    anything inaccurate, is anything superfluous, is anything stigmatising --
    and a note that says nothing has none of those. Measured against
    `gemini-3.1-pro-preview`: an empty note scores `accurate` 5.00 against the
    therapist's 4.20, `succinct` 5.00 against 2.92 and a perfect 1.00 on the
    stigmatising column. The other five correctly collapse to 1, so the judge is
    reading it; the instrument's anchors simply reward vacuity.

    Neither the wording nor the anchors are ours to change -- PDSQI-9 is a
    published instrument and this benchmark reproduces it. What is ours is
    declining to publish a rating of nothing.

    The rendering carries the field labels, so emptiness has to be judged on the
    values rather than on the string: `render_note({})` is not empty text.
    """
    return any(str(value).strip() for value in _values_of(note))


def _values_of(note: str) -> list[str]:
    """The note's field values, without the labels `render_note` added."""
    return [line.split(":", 1)[1] for line in note.splitlines() if ":" in line]


def build_tasks(note: str, transcript: str | None = None) -> list[PdsqiTask]:
    """The questions asked about one note -- one call each.

    Without a transcript this returns the six note-only attributes. That is the
    only mode a confidential session may be scored in, and it is enforced by
    absence rather than by care: with `transcript=None` there is no string in
    scope that could reach a prompt.

    One attribute per call, not all of them in one JSON reply. `judge.ANSWER_TOKENS`
    is inside the judge fingerprint, so raising it to fit a longer answer would
    re-key and discard every cached answer belonging to the other tracks.
    """
    # Nothing is asked about a note with nothing in it. Three of the eight
    # attributes reward exactly that -- see `has_content` -- and the cheapest
    # place to refuse is before the question is put, which also spends nothing.
    if not has_content(note):
        return []

    tasks: list[PdsqiTask] = []
    for attribute in ATTRIBUTES:
        if attribute.needs_transcript and transcript is None:
            continue

        block = (
            _TRANSCRIPT_BLOCK.format(transcript=transcript) if attribute.needs_transcript else ""
        )
        scale = (
            "Yes: stigmatizing language is present.\nNo: the note is free of it."
            if attribute.binary
            else "\n".join(f"{n}: {text}" for n, text in enumerate(attribute.anchors, start=1))
        )
        tasks.append(
            PdsqiTask(
                attribute=attribute.key,
                prompt=PROMPT.format(
                    transcript_block=block,
                    note=note,
                    question=attribute.question,
                    definition=attribute.definition,
                    guidance=f"\n\n{attribute.guidance}" if attribute.guidance else "",
                    scale=scale,
                    closing=_BINARY_CLOSING if attribute.binary else _LIKERT_CLOSING,
                ),
            )
        )
    return tasks


def score(
    answers: dict[str, str], *, expected: tuple[str, ...]
) -> tuple[dict[str, float], list[str]]:
    """Turn one note's answers into measures, and name whatever is missing.

    `expected` says which attributes were asked, so a note scored without a
    transcript is not recorded as having failed the two that were never put to
    the judge. An attribute that was asked and not answered is named, never
    scored zero and never dropped from a denominator.
    """
    scored: dict[str, float] = {}
    missing: list[str] = []

    for attribute in ATTRIBUTES:
        if attribute.key not in expected:
            continue

        answer = answers.get(f"pdsqi.{attribute.key}", "")
        if attribute.binary:
            # Asked as published -- "is stigmatizing language present?" -- and
            # reported inverted, so that every column in the table is better
            # when it is higher.
            present = parse_yes_no(answer)
            if present is None:
                missing.append(attribute.key)
            else:
                scored[attribute.key] = 0.0 if present else 1.0
            continue

        rating = parse_rating(answer)
        if rating is None:
            missing.append(attribute.key)
        else:
            scored[attribute.key] = float(rating)

    return scored, missing
