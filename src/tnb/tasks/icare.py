"""The iCARE task: 17 section prompts, one model call each, per session.

The wording is not ours. The 17 instructions are fetched at run time from the
iCARE repository (``instructions.json``, key ``doctors_prompts``, approved by
clinicians at AIIMS Delhi) and the sentences wrapped around them are copied from
iCARE's own ``Baselines.py``:

    "You're a helpful mental health assistant and follow the given instructions
    carefully. " + instruction + " If no information is available, write 'Nil'
    only. " + "###Dialog###: " + dialog + "###Summary Response###: "

Their closed-model baseline (``Baselines_ClosedModels.py``) sends exactly that
string as a single user message with no system prompt, which is what this
harness does too.

**Zero-shot only.** iCARE also report a one-shot setting that prepends a random
training session and its gold note. That variant needs the train split and a
reproducible sample, and it measures a different thing; if it is ever added it
becomes a second prompt version rather than a change to this one.
"""

from __future__ import annotations

from dataclasses import dataclass

from tnb.datasets import ihope
from tnb.datasets.base import Session

NAME = "icare"

#: Bumped whenever anything reaching the model changes. Result rows carry it and
#: the leaderboard never mixes two versions -- see docs/methodology.md.
PROMPT_VERSION = "icare-zeroshot-v1"

#: Verbatim from iCARE's ``PromptGen``. The trailing spaces are theirs.
PREFIX = "You're a helpful mental health assistant and follow the given instructions carefully. "
NIL_CLAUSE = " If no information is available, write 'Nil' only. "
DIALOG_MARKER = "###Dialog###: "
RESPONSE_MARKER = "###Summary Response###: "

#: iCARE's ``CSVtoStringDialog`` speaker markers. Not the same labels the
#: TheraFuse JSON uses, and not the same labels TN-Eval uses either.
THERAPIST_MARKER = "#Therapist#: "
PATIENT_MARKER = "#Patient#: "


@dataclass(frozen=True)
class SectionPrompt:
    """One of the 17 calls that make up a note for a session."""

    #: One-based, matching how the paper numbers its sections.
    number: int
    instruction: str
    prompt: str

    @property
    def unit(self) -> str:
        """Cache and record key for this call within its session."""
        return f"section-{self.number:02d}"

    @property
    def is_temporal(self) -> bool:
        """Sections 5 and 17, which the paper reports every model fails."""
        return self.number in ihope.TEMPORAL_SECTIONS


#: Short labels for the 17 sections, in order, for display only.
#:
#: The instructions themselves are fetched at run time and never vendored --
#: iCARE publishes no licence. These are descriptive names taken from the field
#: labels the expert notes use, so a reader can see what a note contains without
#: this repository republishing anybody's prompt. A test checks there are still
#: seventeen of them.
SECTION_TITLES = (
    "Patient particulars",
    "Clinical identifiers",
    "Referral information",
    "Therapist information",
    "Past session information",
    "Presenting complaints (symptoms)",
    "History",
    "Crisis markers",
    "Current mental status examination",
    "Psychotherapy type",
    "Psychotherapy technique",
    "Assessments",
    "Issues discussed in current session",
    "Reflections by the therapist",
    "Clinical diagnosis by reviewer",
    "Action plan",
    "Next session details",
)


def render_dialog(session: Session) -> str:
    """Render the transcript the way iCARE's ``CSVtoStringDialog`` does.

    One space after every utterance, and **consecutive turns by the same speaker
    are merged** under a single marker rather than repeating it. Their loop does
    this because the diarised CSV splits a single speech into many rows; we
    reproduce it so the string the model sees is theirs, not ours.

    One difference is unavoidable and worth stating: our transcripts come from
    TheraFuse's already-joined JSON, where a continuation inside one utterance is
    separated by ``; ``. iCARE joined those with a space. The turns and the words
    are the same; some inner punctuation is not.
    """
    parts: list[str] = []
    previous: str | None = None
    for turn in session.turns:
        if turn.speaker != previous:
            parts.append(THERAPIST_MARKER if turn.speaker == "therapist" else PATIENT_MARKER)
            previous = turn.speaker
        parts.append(f"{turn.text} ")
    return "".join(parts)


def build_prompts(session: Session, instructions: list[str]) -> list[SectionPrompt]:
    """The 17 exact strings sent to the model for one session."""
    if len(instructions) != ihope.SECTION_COUNT:
        raise RuntimeError(
            f"Expected {ihope.SECTION_COUNT} iCARE instructions, got {len(instructions)}."
        )

    dialog = render_dialog(session)
    tail = f"{DIALOG_MARKER}{dialog}{RESPONSE_MARKER}"
    return [
        SectionPrompt(
            number=index,
            instruction=instruction,
            prompt=f"{PREFIX}{instruction}{NIL_CLAUSE}{tail}",
        )
        for index, instruction in enumerate(instructions, start=1)
    ]


def load_instructions() -> list[str]:
    """The 17 section prompts, fetched from iCARE and used unmodified."""
    return ihope.load_instructions()


def load_sessions(limit: int | None = None) -> list[Session]:
    """The 40 held-out iHOPE sessions, minus the one with no gold note."""
    return ihope.load("test", limit=limit)
