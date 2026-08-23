"""TN-Eval's SOAP note task: one note per conversation, reference-free.

The prompt below is copied verbatim from TN-Eval's ``src/generate_soap_note.py``
(Apache-2.0, attributed in NOTICE), trailing spaces and all. Nothing about it is
improved: the point is to measure a model on their task, so that our numbers can
be read next to their published ones.

The assembly around it is theirs too — ``PROMPT_TEMPLATE_SOAP + transcript +
"\\n\\nSOAP Note:\\n"``, the ``{...}`` slice used to recover the note from whatever
the model wrapped it in, and the repair sentence re-appended after a parse
failure. See :func:`build_prompt` and :func:`parse_note`.
"""

from __future__ import annotations

import json

from tnb.datasets import tneval
from tnb.datasets.base import Session

NAME = "soap"

#: Bumped whenever anything reaching the model changes. Result rows carry it and
#: the leaderboard never mixes two versions -- see docs/methodology.md.
PROMPT_VERSION = "tneval-soap-v1"

#: Verbatim from TN-Eval. :func:`prompt_digest` and ``tnb prompts --verify``
#: check this copy against upstream rather than trusting that it was pasted
#: correctly.
PROMPT_TEMPLATE_SOAP = """
In emotional support conversations, two primary roles exist: the therapist (individual providing support) and the client (individual seeking support). Your task is to summarize an emotional support conversation into client progress notes. These notes are usually in the SOAP format. The SOAP is a standardized form of recording a client's progress. It stands for:

- Subjective: In this section, document the subjective reports from the client, their family members, and past medical records. Include how the client describes their feelings and current symptoms.
- Objective: This section is for recording objective observations made during the session. Note any factual, observable information, such as the client's appearance, behavior, mood, affect, and speech patterns. Avoid including any subjective statements or self-reported information from the client. 
- Assessment: In this section, integrate the subjective and objective information to provide a comprehensive analysis of the client's current condition. Summarize your clinical impressions and hypotheses regarding the client's issues. 
- Plan: Outline the next steps for the client's treatment. Include both short-term and long-term goals, specifying what will be addressed in the next session as well as overall treatment objectives. Be clear and specific about your expectations and the client’s goals for the duration of treatment.

Output Dictionary template: 
{
"Subjective": "...",
"Objective": "...",
"Assessment": "...",
"Plan": "..."
}
Generate notes for the provided conversation in the above Dictionary style template. 
"""

#: sha256 of the template as published on 2026-08-23. An edit to the text above
#: -- even one trailing space -- changes this and fails the offline test.
UPSTREAM_SHA256 = "e3807172c9bb7e582e112fb1b069eda40106a4c3d5f5d7b1a4d7f14af55ccc22"

#: TN-Eval appends this and retries when the answer does not parse as a note.
#: The prompt grows cumulatively across attempts, exactly as in their loop.
REPAIR_SENTENCE = (
    "\n\nGenerate notes for the provided conversation in the above Dictionary style template.\n"
)

#: TN-Eval's ``constant.SOAP_SECTIONS``. A note that does not carry these four
#: keys is a failed generation, not a differently shaped note.
SECTIONS = ("subjective", "objective", "assessment", "plan")

#: How many times TN-Eval re-asks before giving up on a conversation.
PARSE_ATTEMPTS = 5


def render_transcript(session: Session) -> str:
    """Render the conversation the way TN-Eval's generation script does.

    Their loop starts the transcript with a blank line and prefixes every
    utterance with a newline, which produces one leading empty line and no
    trailing newline. Reproduced rather than tidied: it is part of the prompt
    the published numbers were produced with.
    """
    lines = "".join(f"\n{turn.speaker}: {turn.text}" for turn in session.turns)
    return f"\n\n{lines}"


def build_prompt(session: Session, *, attempt: int = 0) -> str:
    """The exact string sent to the model.

    ``attempt`` reproduces TN-Eval's repair loop: after a note fails to parse
    they append :data:`REPAIR_SENTENCE` and ask again, keeping every earlier
    copy of it in the prompt.
    """
    prompt = PROMPT_TEMPLATE_SOAP + render_transcript(session) + "\n\nSOAP Note:\n"
    return prompt + REPAIR_SENTENCE * attempt


def parse_note(text: str) -> dict[str, str] | None:
    """Recover the note from the model's answer, or None if it is not there.

    TN-Eval slices from the first ``{`` to the first following ``}`` and parses
    that with ``strict=False`` -- models wrap the dictionary in prose, in code
    fences, or in an explanation. Returning None rather than an empty note keeps
    a refusal distinguishable from a note with four empty sections.
    """
    if "{" not in text:
        return None
    candidate = "{" + text.split("{")[1].split("}")[0] + "}"
    try:
        parsed = json.loads(candidate, strict=False)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None

    note = {str(key).lower(): value for key, value in parsed.items()}
    if set(note) != set(SECTIONS):
        return None
    return {section: str(note[section]) for section in SECTIONS}


def load_sessions(limit: int | None = None) -> list[Session]:
    """The 50 conversations TN-Eval released notes for."""
    return tneval.load(limit=limit)
