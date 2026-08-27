"""The same SOAP task as TN-Eval's, asked in Czech.

**This is a translation, and it is the one prompt in this repository that is not
reproduced verbatim.** Everywhere else the rule is to measure a model on its
authors' task, so `soap.PROMPT_TEMPLATE_SOAP` is copied trailing spaces and all
and `tnb prompts --verify` checks the copy against upstream. There is no
upstream Czech, so this cannot be that, and pretending otherwise would be worse
than saying so: it carries its own `PROMPT_VERSION`, it is labelled a
translation wherever it is published, and `tasks/fidelity.py` is deliberately
not extended to it, because there is nothing to verify it against.

Why translate theirs rather than write one. The question this track exists to
answer is whether a model's standing on the English leaderboard says anything
about the Czech it writes. That only means something if the task is the same
task -- same four sections, same instructions, same shape of answer -- with the
language as the one thing that differs. A prompt of our own would have made the
comparison meaningless in a way no caveat could repair.

**SOAP rather than a Czech form, and not for convenience.** Czech clinical
documentation has no published note format to reproduce. The word "dekurz" does
not appear once in the decree that governs medical records (444/2024 Sb., read
in full; the older 98/2012 Sb. was repealed on 1 January 2025), so there is
nothing there to copy either. What the decree does require, in section 3(1), is
a record of the patient's own account of their state and a targeted objective
finding, working conclusions and a diagnosis, and a recommendation for further
treatment. Those are S, O, A and P; the decree asks for them without naming
them that way.

**The section keys are Czech.** They are the one part of the note a reader sees
as a heading, and English headings would put English words into a note that is
then scored by `scoring/czech.py`, whose `untranslated` criterion asks whether
an English term was left in English. The note would fail a criterion for
obeying its own prompt. Internally the sections keep their English keys, so the
code is shared with `soap.py` and the two tracks stay comparable.
"""

from __future__ import annotations

import json

from tnb.datasets import czech as corpus
from tnb.datasets.base import Session

#: One task per corpus, because `results.TRACK_BY_TASK` maps a generation
#: directory to a track and a single task could not tell the two halves apart.
NAME_REAL = "czech-real"
NAME_TRANSLATED = "czech-translated"

#: Bumped whenever anything reaching the model changes. Result rows carry it and
#: the leaderboard never mixes two versions.
PROMPT_VERSION = "czech-soap-v1"

#: The internal keys, shared with `soap.SECTIONS` so the two tracks line up.
SECTIONS = ("subjective", "objective", "assessment", "plan")

#: What the model is asked to write, and what a reader sees as a heading.
SECTION_LABELS = {
    "subjective": "Subjektivně",
    "objective": "Objektivně",
    "assessment": "Hodnocení",
    "plan": "Plán",
}

_BY_LABEL = {label.lower(): key for key, label in SECTION_LABELS.items()}

#: Speaker labels. The corpus writes `T:` and `K:`; the prompt spells them out,
#: because a model that has to infer what `K` stands for is being measured on
#: something this benchmark is not asking about.
THERAPIST = "Terapeut"
CLIENT = "Klient"

PROMPT_TEMPLATE = """
V podpůrném rozhovoru vystupují dvě role: terapeut (ten, kdo podporu poskytuje) a klient (ten, kdo ji vyhledává). Tvým úkolem je shrnout podpůrný rozhovor do záznamu o průběhu klientovy práce. Takový záznam se obvykle píše ve formátu SOAP. SOAP je ustálený způsob zápisu, jak klientova práce postupuje. Znamená:

- Subjektivně: Sem zapiš, co uvádí sám klient, jeho blízcí a dřívější zdravotnická dokumentace. Uveď, jak klient popisuje své prožívání a současné obtíže.
- Objektivně: Sem patří objektivní pozorování ze sezení. Zaznamenej faktické, pozorovatelné údaje: klientův vzhled, chování, náladu, afekt a řeč. Nezapisuj sem nic, co klient sám o sobě sdělil, ani vlastní úsudky.
- Hodnocení: Zde spoj subjektivní a objektivní údaje a podej ucelený rozbor klientova současného stavu. Shrň své klinické dojmy a hypotézy o klientových obtížích.
- Plán: Popiš další kroky v klientově léčbě. Uveď krátkodobé i dlouhodobé cíle a upřesni, co se bude řešit na příštím sezení i jaké jsou cíle léčby celkově. Buď konkrétní v tom, co očekáváš ty a jaké jsou klientovy cíle po dobu léčby.

Šablona výstupního slovníku:
{
"Subjektivně": "...",
"Objektivně": "...",
"Hodnocení": "...",
"Plán": "..."
}
Napiš záznam k uvedenému rozhovoru ve výše uvedené šabloně slovníku. Piš česky.
"""

#: Appended and re-asked when an answer arrives that does not parse as a note,
#: mirroring TN-Eval's repair loop rather than inventing one.
REPAIR_SENTENCE = (
    "\n\nNapiš záznam k uvedenému rozhovoru ve výše uvedené šabloně slovníku. Piš česky.\n"
)

#: As many times as TN-Eval re-asks before giving up on a conversation.
PARSE_ATTEMPTS = 5


def render_transcript(session: Session) -> str:
    """The conversation as the prompt carries it.

    TN-Eval's own rendering, with their leading blank lines kept: one fewer
    difference between the two tracks is one fewer thing a result could be about.
    """
    labels = {"therapist": THERAPIST, "client": CLIENT}
    lines = "".join(f"\n{labels[turn.speaker]}: {turn.text}" for turn in session.turns)
    return f"\n\n{lines}"


def build_prompt(session: Session, *, attempt: int = 0) -> str:
    """The exact string sent to the model."""
    prompt = PROMPT_TEMPLATE + render_transcript(session) + "\n\nZáznam SOAP:\n"
    return prompt + REPAIR_SENTENCE * attempt


def parse_note(text: str) -> dict[str, str] | None:
    """Recover the note from the answer, or None if it is not there.

    The same slice TN-Eval uses -- from the first brace to the next -- because
    models wrap the dictionary in prose, in code fences or in an apology.
    Returning None rather than four empty strings keeps a refusal
    distinguishable from a note whose sections are blank, which
    `scoring/czech.py` treats differently and deliberately.
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

    note = {
        _BY_LABEL.get(str(key).strip().lower(), str(key).lower()): value
        for key, value in parsed.items()
    }
    if set(note) != set(SECTIONS):
        return None
    return {section: str(note[section]) for section in SECTIONS}


def render_note(note: dict[str, str]) -> str:
    """The four sections as one string, for a judge that reads the whole note.

    Every section appears even when empty, and the labels are Czech. An empty
    section is a fact about the note -- `scoring/czech.py` refuses to rate a
    note with nothing in it at all -- and hiding the heading would make a model
    that wrote no plan look tidier for the omission.
    """
    return "\n\n".join(
        f"{SECTION_LABELS[section]}: {(note.get(section) or '').strip()}" for section in SECTIONS
    )


def load_real(limit: int | None = None) -> list[Session]:
    return corpus.load_real(limit=limit)


def load_translated(limit: int | None = None) -> list[Session]:
    return corpus.load_translated(limit=limit)
