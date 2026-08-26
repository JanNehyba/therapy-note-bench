"""The Czech tracks' rubric: is the Czech right, judged from the note alone.

This scorer answers one question and refuses the rest. It does not ask whether
the note is true, complete, or clinically useful -- it has no transcript and no
reference note, so it could not. A fluent, correctly typeset, entirely invented
note scores well here. Every measure carries that caveat.

That narrowness is what makes the track cheap. The two English tracks are
expensive because they need a gold note or a 23-item rubric written by
clinicians; no Czech gold notes exist and nobody is going to write fifty. A
language rubric needs neither.

**Two prompt languages, and the choice is an instrument.** The note is Czech;
the question about it can be asked in Czech or in English, and which one detects
more real errors is not knowable from an armchair. Both are written here and
each has its own `judge_prompt_version`, which is part of `COMPARABILITY_KEYS`
-- so the two can never share a leaderboard table, and a run always records
which was used. `docs/methodology.md` records how the choice was decided.

**No composite.** Eight columns, no average. Weighting spelling against
terminology is a linguistic decision, not a measurement, and the correlation
this track exists to look for is more useful per dimension anyway: English
completeness may predict terminology and say nothing about typography.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: One per prompt language. Bumped whenever anything reaching the judge changes.
#: Result rows carry it and the leaderboard never mixes two versions.
JUDGE_PROMPT_VERSIONS = {
    "cs": "czech-quality-cs-v1",
    "en": "czech-quality-en-v1",
}

LANGUAGES = tuple(JUDGE_PROMPT_VERSIONS)

#: What a run uses unless told otherwise. Settled by the planted-error control
#: rather than by preference -- see `docs/methodology.md`.
DEFAULT_LANGUAGE = "cs"

#: The shared caveat. Repeated on every measure because a reader meets one
#: column at a time, and this is the limit that matters most about all of them.
_NO_CONTENT_CHECK = (
    "Judged from the note alone, with no transcript and no reference: this says "
    "nothing about whether the note is true or complete. An invented note in "
    "faultless Czech scores 10."
)

#: The eight dimensions, in the order they are asked and shown.
#:
#: `key` reaches the page and is English. The Czech and English wordings are
#: both here because the prompt language is part of the instrument. The example
#: in each description is a real error found by hand in the first round of Czech
#: notes, which is what keeps a dimension about something concrete rather than
#: about a feeling.
DIMENSIONS: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "spelling",
        "Pravopis a diakritika",
        "všechna slova jsou napsaná správně, včetně délek a háčků "
        "(například „sebepéče“, ne „sebepeče“)",
        "Spelling and diacritics",
        "every word is spelled correctly, including length marks and hacheks "
        "(for example „sebepéče“, not „sebepeče“)",
    ),
    (
        "grammar",
        "Gramatika a stavba vět",
        "pády, rody, čísla a časy se shodují a věty jsou dokončené",
        "Grammar and sentence structure",
        "cases, genders, numbers and tenses agree, and sentences are finished",
    ),
    (
        "lexis",
        "Volba slov",
        "slova a spojení jsou česká, ne doslovně přeložená z angličtiny "
        "(například „tlak“, ne „pres“)",
        "Word choice",
        "words and phrases are Czech rather than calqued from English "
        "(for example „tlak“, not „pres“)",
    ),
    (
        "terminology",
        "Odborná terminologie",
        "tam, kde má čeština zavedený odborný termín, poznámka ho používá a "
        "nenechává anglický originál (například „vyhýbavé zvládání“, ne "
        "„behavioral avoidance coping“)",
        "Clinical terminology",
        "where Czech has an established clinical term the note uses it rather than "
        "leaving the English (for example „vyhýbavé zvládání“, not "
        "„behavioral avoidance coping“)",
    ),
    (
        "register",
        "Rejstřík a stylová jednotnost",
        "poznámka drží rejstřík zdravotnické dokumentace a nesklouzává do hovorové "
        "řeči (například „sestra“, ne „ségra“)",
        "Register and stylistic consistency",
        "the note holds the register of clinical documentation and does not slip into "
        "colloquial speech (for example „sestra“, not „ségra“)",
    ),
    (
        "readability",
        "Čtivost",
        "poznámka se čte plynule a není zahlcená podstatnými jmény slovesnými ani "
        "neúnosně dlouhými souvětími",
        "Readability",
        "the note reads smoothly and is not choked with verbal nouns or unworkably long sentences",
    ),
    (
        "typography",
        "Typografie",
        "české uvozovky, pomlčky, mezery, zkratky a zápis čísel a dat odpovídají české normě",
        "Typography",
        "Czech quotation marks, dashes, spacing, abbreviations and the way numbers "
        "and dates are written follow Czech convention",
    ),
    (
        "consistency",
        "Vnitřní konzistence",
        "poznámka si neodporuje a tutéž věc i téhož člověka nazývá v celém textu stejně",
        "Internal consistency",
        "the note does not contradict itself and calls the same thing, and the same "
        "person, by the same name throughout",
    ),
)

DIMENSION_KEYS: tuple[str, ...] = tuple(key for key, *_ in DIMENSIONS)

#: How many words the note ran to. Written into the row, not shown as a column.
#:
#: A longer note has more chances to misspell something, so "this model writes
#: bad Czech" and "this model writes long notes" are the first two explanations
#: of the same number. Recording it costs nothing and makes the objection
#: answerable instead of arguable.
INTERNAL_MEASURES: tuple[str, ...] = ("note_words",)

MEASURES: dict[str, dict[str, str]] = {
    key: {
        "label": label_en,
        "scale": "0-10",
        "definition": (
            f"{description_en[0].upper()}{description_en[1:]}. "
            "Rated 0-10 by a judge reading only the note."
        ),
        "caveat": _NO_CONTENT_CHECK,
    }
    for key, _name_cs, _description_cs, label_en, description_en in DIMENSIONS
}

#: Eight measures, no average. See the module docstring.
RANKING_MEASURE = None

#: Every column here is a judge's decision -- unlike iCARE, where four of five
#: are computed from the note and the reference and so are byte-identical under
#: any judge. The two-judge agreement panel is therefore meaningful on all
#: eight, which matters more here than anywhere else: this track has no human
#: anchor at all, and where the judges disagree is the only control it has.
JUDGE_MEASURES: tuple[str, ...] = DIMENSION_KEYS

_SCALE_CS = """\
10: v této vlastnosti bez jediné chyby
8-9: jedna nebo dvě drobnosti, které čtenáře nezdrží
6-7: několik chyb, text je ale pořád dobře čitelný
4-5: chyby jsou časté a při čtení ruší
2-3: chyby jsou skoro v každé větě a kazí dojem z dokumentace
0-1: vlastnost v poznámce prakticky chybí"""

_SCALE_EN = """\
10: no error of this kind at all
8-9: one or two small things that do not slow a reader down
6-7: several errors, but the text still reads well
4-5: errors are frequent and get in the way
2-3: errors in almost every sentence, and the documentation suffers for it
0-1: the note effectively lacks this property"""

PROMPT_CS = f"""\
Níže je klinická poznámka z psychoterapeutického sezení, napsaná česky.

## Poznámka
{{note}}

## Hodnocená vlastnost
{{name}}: {{description}}

## Stupnice
{_SCALE_CS}

Ohodnoť poznámku jen v této jedné vlastnosti. Nehodnoť, jestli je obsah poznámky \
správný nebo úplný -- transkript sezení k dispozici nemáš a posuzuje se pouze \
čeština. Napiš pouze číslo od 0 do 10 a nic jiného:"""

PROMPT_EN = f"""\
Below is a clinical note from a psychotherapy session, written in Czech.

## Note
{{note}}

## Property being rated
{{name}}: {{description}}

## Scale
{_SCALE_EN}

Rate the note on this one property only. Do not judge whether the note's content \
is correct or complete -- you do not have the session transcript, and only the \
Czech is being assessed. Output only a number from 0 to 10 and nothing else:"""

#: A rating, and nothing but a rating. 0 and 10 are both real answers here, so
#: the pattern spans the whole scale rather than TN-Eval's 1-5.
#:
#: Brackets, quotes, asterisks and a trailing full stop are tolerated because a
#: judge writes "[7]" or "7." often enough. A sign is not: `\W` would have
#: swallowed the minus in "-1" and returned 1, which is the same trick that
#: makes `tneval.parse_likert` read "10/10" as one.
_RATING = re.compile(r"^[^\w+-]*(10|[0-9])[^\w+-]*$")


def judge_prompt_version(language: str = DEFAULT_LANGUAGE) -> str:
    """The version string a run records, which says which prompt was used."""
    if language not in JUDGE_PROMPT_VERSIONS:
        raise ValueError(f"unknown prompt language {language!r}; expected one of {LANGUAGES}")
    return JUDGE_PROMPT_VERSIONS[language]


def is_a_rating(answer: str) -> bool:
    """Whether a 0-10 question actually got a 0-10."""
    return _RATING.match((answer or "").strip()) is not None


def parse_rating(answer: str) -> int | None:
    """The rating, or None. Never a fabricated middle of the scale.

    `tneval.parse_likert` returns 3 for anything it cannot read, because that is
    TN-Eval's own arithmetic and our numbers are compared against their published
    ones. No such argument applies here: this rubric is this repository's own and
    is compared against nothing, so an invented rating would buy comparability
    with nobody and cost a measurement nobody took.

    Delegating to that parser would have been wrong in two different ways, both
    checked against it rather than assumed:

        parse_likert("10")          ->  3   # int() succeeds, 10 is outside 1-5
        parse_likert("0")           ->  3
        parse_likert("7")           ->  3
        parse_likert("Rating: 10")  ->  1   # int() fails, the digit scan
        parse_likert("10/10")       ->  1   # finds the leading 1
        parse_likert("10.")         ->  1

    So a bare rating outside 1-5 becomes a fabricated middle of the scale, and a
    rating of ten with anything at all around it becomes a one -- the top of this
    scale recorded as the bottom. Neither says anything, and neither is visible
    afterwards.
    """
    match = _RATING.match((answer or "").strip())
    return int(match.group(1)) if match else None


@dataclass(frozen=True)
class RubricTask:
    """One dimension asked about one note, and where its answer is cached."""

    dimension: str
    prompt: str

    @property
    def unit(self) -> str:
        return f"quality.{self.dimension}"

    @property
    def kind(self) -> str:
        return "quality"

    @property
    def section(self) -> str:
        return "quality"


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


def build_tasks(note: str, language: str = DEFAULT_LANGUAGE) -> list[RubricTask]:
    """The eight questions asked about one note -- one call each.

    Not one call returning eight ratings, which would be cheaper and is wrong.
    `judge.ANSWER_TOKENS` and `judge.OPENAI_OUTPUT_CEILING` are inside the judge
    fingerprint, and `judge.load_cached` rejects any answer whose fingerprint
    differs. Raising either to fit eight ratings into one JSON reply would re-key
    and throw away every cached answer belonging to the other two tracks.

    The prompt carries the note and nothing else. There is no transcript in it,
    which is why the confidential Czech sessions never reach the judge's
    provider -- only the note a model wrote about them does.
    """
    if language not in LANGUAGES:
        raise ValueError(f"unknown prompt language {language!r}; expected one of {LANGUAGES}")
    template = PROMPT_CS if language == "cs" else PROMPT_EN

    return [
        RubricTask(
            dimension=key,
            prompt=template.format(
                note=note,
                name=name_cs if language == "cs" else name_en,
                description=description_cs if language == "cs" else description_en,
            ),
        )
        for key, name_cs, description_cs, name_en, description_en in DIMENSIONS
    ]


def note_words(note: str) -> int:
    return len((note or "").split())


def aggregate(note: str, answers: dict[str, str]) -> Scores:
    """One note's eight ratings, or a named account of what is missing.

    A dimension the judge did not rate is listed in `incomplete`, never scored
    zero and never quietly dropped from a denominator. All eight or the note is
    partial, and `SystemAggregate` keeps a partial note out of every headline:
    eight columns computed over different numbers of notes, with nothing on the
    page saying so, would be worse than eight columns over fewer notes.
    """
    scores = Scores()
    missing: list[str] = []

    for key in DIMENSION_KEYS:
        rating = parse_rating(answers.get(f"quality.{key}", ""))
        if rating is None:
            missing.append(key)
            continue
        scores.headline[key] = float(rating)
        scores.by_criterion[key] = float(rating)

    if missing:
        scores.incomplete["quality"] = missing

    # Not a judge measure and not a column, so it is recorded whatever the judge
    # did or did not answer.
    scores.headline["note_words"] = float(note_words(note))
    scores.sections_used["quality"] = len(DIMENSION_KEYS) - len(missing)
    return scores
