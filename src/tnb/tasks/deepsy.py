"""The note format the Deepsy team actually writes, as a task.

Every other track here measures a format nobody in this project uses. TN-Eval's
SOAP is what the paper published, and the Czech track translates it so that the
English numbers mean something beside the Czech ones -- but a Czech clinical
psychologist does not write SOAP, and neither does the application these models
are meant to serve. This track asks the models for the sections that application
asks for, in its own words.

**Three of its eleven sections, and the three are not a preference.** What is
left after the ones that cannot be run is six, and these three are the three
with a SOAP counterpart:

===================  ========================================================
`data`               what the session contained -- SOAP's Subjective and
                     Objective together
`clinical_hypotheses`  what it might mean -- SOAP's Assessment
`plan`               what happens next -- SOAP's Plan
===================  ========================================================

That correspondence is the whole design. The same models write from the same
transcripts, and the only thing that changes is the shape they are asked for --
so a difference between this table and the Czech SOAP table is a fact about the
*format*, which nothing measured so far can separate from the model.

**What was left out, and why it was not a choice.** `dekurz` and the
questionnaire sections are out by decision. `episode_summary` has no transcript
in its template at all -- it works from the previous note. `progress` needs the
previous session's own progress section, and this benchmark scores single
sessions with no chain between them. `glossary` is not a section; it is a
fragment the application pastes into every system message. Of the six that read
only a transcript, `constructs` has no SOAP counterpart to compare against,
`risk_assessment` would be answered "no risk" on ten sessions with one client,
and `alliance` without its alliance data asks the model to infer something the
application supplies.

**No questionnaires.** The templates carry `{if_questionnaire_data}` blocks, and
`PromptLoader` removes them when there is no data, so the prompt stays exactly
what the application would send a client who has filled nothing in. Feeding
questionnaires would measure which sessions had them, not which model wrote
better.

`build_prompt` reproduces `PromptLoader::buildUserMessage` step for step,
including the order of substitutions -- the placeholders are replaced first and
the conditional blocks stripped afterwards, so a block whose variable was
emptied still disappears -- and the collapse of three or more newlines that the
removal leaves behind.
"""

from __future__ import annotations

import json
import re

from tnb.datasets.base import Session
from tnb.tasks import deepsy_prompts

#: Not a reproduction of anything upstream: `monitor-notes` has no version on
#: its prompts, so this names the day they were copied and which three.
PROMPT_VERSION = "deepsy-3section-v1"

NAME_REAL = "deepsy-real"
NAME_TRANSLATED = "deepsy-translated"

#: In the order the application generates them, which is also SOAP's order.
SECTIONS: tuple[str, ...] = ("data", "clinical_hypotheses", "plan")

#: The keys each section's prompt names in its own "Output format (JSON)" block.
#: A reply is parsed against these and against nothing else: a model that
#: invents a key has not answered the question that was asked.
KEYS: dict[str, tuple[str, ...]] = {
    "data": (
        "main_themes",
        "problems_symptoms",
        "therapy_goals",
        "client_resources",
        "important_persons",
    ),
    "clinical_hypotheses": ("hypotheses",),
    "plan": (
        "treatment_plan",
        "unresolved_problems",
        "between_session_tasks",
        "referrals",
        "crisis_planning",
    ),
}

#: What the application writes into `{length}`. Reproduced with its wording,
#: because a limit stated softly is a different instruction.
LENGTH_MACRO = (
    "STRIKTNÍ LIMIT DÉLKY: Celý výstup NESMÍ překročit {length} slov. "
    "Cílová délka je {length} slov pro celou sekci (všechny subsekce dohromady). "
    "Odpověď delší než {length} slov je NEVALIDNÍ. Piš stručně a výstižně."
)

#: The bullet-point branch of both format macros. Every one of these three
#: sections declares `bullet points`, so the narrative branch never runs here
#: and is not reproduced -- it belongs to `dekurz`, which this track does not
#: generate.
FORMAT_MACRO = "Formát výstupu: odrážky."
FORMAT_INSTRUCTION = (
    "Každá hodnota je řetězec v češtině. Piš ve formátu odrážek: "
    'každá položka na novém řádku s prefixem "- ".'
)

#: `{if_X}...{/if_X}`, kept when option X is non-empty. Nothing here supplies
#: any option, so every block goes -- but the mechanism is reproduced rather
#: than the outcome, so that supplying one later needs no second reading of the
#: PHP.
_CONDITIONAL = re.compile(r"\{if_(\w+)\}(.*?)\{/if_\1\}", re.S)
_BLANK_RUN = re.compile(r"\n{3,}")

THERAPIST = "Terapeut"
CLIENT = "Klient"

#: Appended when a reply arrives and does not parse. Deepsy's own prompt already
#: says CRITICAL and names the keys, so this repeats the demand rather than
#: inventing a new instruction -- the application has no retry of its own, and a
#: harness that talked the model into a different answer would be measuring its
#: own persuasion.
REPAIR_SENTENCE = "\n\nOdpověz POUZE platným JSON objektem s uvedenými klíči.\n"

#: The Czech SOAP task's number, so a model that needs several attempts is not
#: given fewer here for a format that demands stricter output.
PARSE_ATTEMPTS = 5


def load_real(limit: int | None = None):
    """The de-identified real sessions. Never the originals -- see `datasets.czech`."""
    from tnb.tasks import czech

    return czech.load_real(limit)


def load_translated(limit: int | None = None):
    from tnb.tasks import czech

    return czech.load_translated(limit)


def with_repair(prompt: str, attempt: int) -> str:
    return prompt + REPAIR_SENTENCE * attempt


def render_transcript(session: Session) -> str:
    """The conversation as the prompt's `{transcript}`.

    The same rendering the Czech SOAP task uses. Two tracks that differ in the
    prompt must not also differ in how the session was written down, or the
    comparison measures both at once.
    """
    from tnb.tasks import czech

    return czech.render_transcript(session)


def build_prompt(session: Session, section: str, options: dict | None = None) -> str:
    """One section's user message, as `PromptLoader::buildUserMessage` builds it.

    The order is the PHP's and it matters: placeholders first, conditional
    blocks second. A `{questionnaire_data}` that has just been replaced with an
    empty string still sits inside `{if_questionnaire_data}`, and it is that
    second pass which removes the sentence around it.
    """
    if section not in SECTIONS:
        raise ValueError(f"{section!r} is not one of {SECTIONS}.")
    options = options or {}

    message = deepsy_prompts.template(section).replace("{transcript}", render_transcript(session))
    for placeholder, value in (
        ("{client_info}", options.get("client_info", "")),
        ("{modality_macro}", options.get("modality_macro", "")),
        (
            "{length}",
            LENGTH_MACRO.format(length=options.get("length", deepsy_prompts.default_length())),
        ),
        ("{format_macro}", FORMAT_MACRO),
        ("{format_instruction}", FORMAT_INSTRUCTION),
        ("{questionnaire_data}", options.get("questionnaire_data", "")),
        ("{alliance_data}", options.get("alliance_data", "")),
        ("{risk_data}", options.get("risk_data", "")),
        ("{previous_progress}", options.get("previous_progress", "")),
    ):
        message = message.replace(placeholder, value)

    message = _CONDITIONAL.sub(lambda m: m.group(2) if options.get(m.group(1)) else "", message)
    return _BLANK_RUN.sub("\n\n", message)


def default_length() -> int:
    """The word limit the Deepsy prompt sets, read from the application.

    Exposed here because `tools/czech_length.py` measures compliance against it
    and should not have to know where the prompts come from.
    """
    return deepsy_prompts.default_length()


def system_message(section: str) -> str:
    return deepsy_prompts.system(section)


def parse_note(text: str, section: str) -> dict[str, str] | None:
    """One section's JSON reply, or None when it is not one.

    Every key the prompt named or nothing. A reply missing a key is a reply to a
    different question, and letting it through would put a note scored on four
    fields beside one scored on five under the same heading -- the shape this
    repository keeps meeting.

    `None` is not an empty note. `scoring/czech.py` distinguishes the two and the
    distinction is the reason a model that refused does not score as a model
    that wrote nothing.
    """
    if not text or not text.strip():
        return None

    body = text.strip()
    # Models wrap JSON in a fence despite being told not to. Stripping one is
    # not leniency about the content: what is inside still has to parse and to
    # carry every key.
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", body, re.S)
    if fenced:
        body = fenced.group(1)

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    if set(parsed) != set(KEYS[section]):
        return None
    return {key: str(parsed[key]) for key in KEYS[section]}


def render_note(note: dict[str, str]) -> str:
    """The three sections as one text, for a judge that reads a whole note.

    Ordered by `SECTIONS` and then by each section's own key order, never by
    the dictionary's: a model's reply carries whatever order it wrote in, and
    anything asking about structure would then be scoring the order a parser
    happened to see.

    Every key appears even when empty, for the reason the Czech SOAP renderer
    gives: a model that answered nothing under a heading is shown as having
    answered nothing, not as having been asked less.
    """
    lines = []
    for section in SECTIONS:
        for key in KEYS[section]:
            value = (note.get(key) or "").strip()
            lines.append(f"{key}: {value}")
    return "\n\n".join(lines)
