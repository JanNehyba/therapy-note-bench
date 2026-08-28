"""Is the Czech right: seven yes/no questions, asked of the note alone.

This scorer answers one question and refuses the rest. It does not ask whether
the note is true, complete or clinically useful -- it has no transcript and no
reference note, so it could not. A fluent, correctly typeset, entirely invented
note passes everything here. Every measure carries that caveat, and PDSQI-9 on
the same notes is what asks the other question.

**Yes/no rather than a 1-5 scale, on this repository's own published numbers.**
An earlier version of this module rated six dimensions 1-5. The calibration
block says what that shape is worth here: two therapists agree at kappa 0.50 on
a criterion checklist and at rho 0.13 to 0.19 on 1-5 scales, and the judge
reaches alpha 0.60 against 0.03 to 0.11. It is why the leaderboard ranks on the
rubric and not on the Likert columns, and there was no reason to build a third
instrument out of the weaker half.

The measured consequence is on the page already. In the PDSQI-9 table all
sixteen models score exactly 5.00 on four of eight columns, and
`concordance.rankable` refuses an agreement figure for each -- a correlation of
+1.000 over a column of fives is not agreement, it is a coin. A proportion over
ten notes has eleven values and 0.3 against 0.9 is a difference a reader can
see.

**It fixes half the problem and it is worth being clear which half.** Where a
column is flat because the *judge* cannot see a difference, a concrete question
can recover it: one judge separates `comprehensible` where the other does not.
Where a column is flat because the *task* prescribes the answer, no wording
helps -- every model writes into the same four-part template, so nothing can
distinguish them on structure. So none of the seven criteria asks about
anything the prompt dictates. Diacritics, calques, terminology, register and
quotation marks are choices a model makes; the shape of the note is not, and it
is not asked about.

**No composite.** Seven proportions, no average. Weighting spelling against
terminology is a linguistic decision rather than a measurement, and the
correlation this track exists to look for is more useful per criterion anyway:
English completeness may predict terminology and say nothing about typography.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tnb.scoring import pdsqi
from tnb.tasks import czech as _task

#: Bumped whenever anything reaching the judge changes. Rows carry it and the
#: leaderboard never mixes two versions.
JUDGE_PROMPT_VERSION = "czech-criteria-v2"

#: The shared caveat. Repeated on every measure because a reader meets one
#: column at a time, and this is the limit that matters most about all of them.
_NO_CONTENT_CHECK = (
    "Asked of the note alone, with no transcript and no reference: it says nothing "
    "about whether the note is true or complete. An invented note in faultless Czech "
    "passes. Reported as the share of notes free of the fault, so higher is better."
)


@dataclass(frozen=True)
class Criterion:
    """One fault, asked about as a yes/no question.

    `guidance` carries an example and a counter-example, and both are in the
    prompt on purpose. Without them two criteria blur into each other and their
    columns then correlate because they are answering the same question:
    `sebepece` is a diacritic that went missing, not a word Czech does not have,
    and only a counter-example says which column it belongs in.
    """

    key: str
    label: str
    #: The question, in Czech. Answered yes when the fault is present.
    question: str
    #: What belongs in this criterion, and what belongs in a different one.
    guidance: str
    #: English, because this reaches the published page.
    definition: str
    #: Whether a note can lack the chance to make this mistake at all.
    gated: bool = False
    #: Whether the answer is read off the note instead of asked of a judge.
    #:
    #: Only `quotes`, and it was asked of a judge until it was checked against
    #: the characters in the note: `gemini-3.1-pro-preview` was right on 75 of
    #: 75 and `gpt-5.6-terra` on 65, with nine notes it reported straight marks
    #: in that have none. A judge that at best matches `in` and at worst
    #: contradicts it is spending money to add error.
    computed: bool = False


CRITERIA: tuple[Criterion, ...] = (
    Criterion(
        key="diacritics",
        label="Diacritics",
        question="Je v poznámce české slovo s chybějící nebo špatnou délkou či háčkem?",
        guidance=(
            "Patří sem například „sebepeče“ místo „sebepéče“. Nepatří sem slovo, které "
            "v češtině vůbec neexistuje, ani výraz přeložený z angličtiny — na ty se "
            "ptáme jinde."
        ),
        definition=(
            "Whether any Czech word in the note has a missing or wrong length mark or "
            "hachek. A word Czech does not have at all belongs to another criterion."
        ),
    ),
    Criterion(
        key="calque",
        label="Calques",
        question="Je v poznámce výraz utvořený doslovným překladem z angličtiny?",
        guidance=(
            "Patří sem například „pres“ tam, kde se česky řekne „tlak“. Nepatří sem "
            "anglické slovo ponechané v původní podobě — to je jiné kritérium."
        ),
        definition=(
            "Whether the note contains a phrase built by translating English word for "
            "word. An English word left as it was belongs to another criterion."
        ),
    ),
    Criterion(
        key="untranslated",
        label="Untranslated terms",
        question="Zůstal v poznámce anglický odborný termín nepřeložený?",
        guidance=(
            "Patří sem například „behavioral avoidance coping“ ponechané anglicky. "
            "Nepatří sem mezinárodní zkratka, která se v české dokumentaci běžně "
            "používá, jako CBT nebo PTSD."
        ),
        definition=(
            "Whether an English clinical term was left in English. International "
            "abbreviations that Czech documentation uses as they are do not count."
        ),
    ),
    Criterion(
        key="agreement",
        label="Agreement",
        question="Je v poznámce věta s chybnou shodou, špatným pádem nebo nedokončená?",
        guidance=(
            "Patří sem například „klientka uvedl“. Nepatří sem věta, která je "
            "stylisticky těžkopádná, ale gramaticky správná."
        ),
        definition=(
            "Whether any sentence has broken agreement, a wrong case, or is left "
            "unfinished. A clumsy but grammatical sentence does not count."
        ),
    ),
    Criterion(
        key="register",
        label="Register",
        question="Je v poznámce hovorový nebo citově zabarvený výraz tam, kam patří odborný?",
        guidance=(
            "Patří sem například „ségra“ tam, kde patří „sestra“. Nepatří sem citace "
            "klientovy vlastní řeči uvedená v uvozovkách."
        ),
        definition=(
            "Whether the note slips out of the register of clinical documentation into "
            "colloquial or emotive wording. A quotation of the client does not count."
        ),
    ),
    Criterion(
        key="quotes",
        label="Quotation marks",
        # The apostrophe is named because leaving it unnamed cost this project a
        # measurement. A native speaker rating twenty notes counted `'slovo'` as
        # a straight mark and the judge did not, and 45 of the 75 notes that
        # quote anything use exactly that -- so the two answered different
        # questions and their 0.55 agreement was the wording, not the Czech.
        question=("Jsou v poznámce rovné uvozovky \" nebo apostrofy ' místo českých „ a “?"),
        guidance=(
            "Ptáme se jen na tvar uvozovek, ne na to, co je v nich. Apostrof "
            "použitý místo uvozovky sem patří."
        ),
        definition=(
            "Whether the note uses a straight quotation mark or an apostrophe where "
            "Czech uses its own marks. Counted from the characters in the note rather "
            "than asked of a judge, and only of notes that quote anything at all."
        ),
        gated=True,
        computed=True,
    ),
    Criterion(
        key="nonword",
        label="Non-words",
        question="Je v poznámce slovo, které v češtině neexistuje?",
        guidance=(
            "Patří sem překlep nebo vymyšlený odborný termín. Nepatří sem vlastní "
            "jméno, ani slovo, které je jen špatně napsané s diakritikou, ani anglický "
            "termín ponechaný anglicky — na ty se ptáme jinde."
        ),
        definition=(
            "Whether the note contains a word Czech does not have. A proper noun, a "
            "diacritic slip and an English term left in English each belong elsewhere."
        ),
    ),
)

CRITERION_KEYS: tuple[str, ...] = tuple(c.key for c in CRITERIA)

#: Every quotation mark a note might use, straight or typographic. What decides
#: whether the `quotes` criterion had anything to judge.
#:
#: Determined here rather than by asking, because it is a fact about the string
#: and a judge call would spend money to be less certain about it.
QUOTE_CHARACTERS = "\"'„“”«»’"

#: The subset that is the fault. Everything else in `QUOTE_CHARACTERS` is a
#: typographic mark; these two are the typewriter ones Czech does not use.
#:
#: Measured on the real half: 348 apostrophe pairs stand where quotation marks
#: belong and exactly one apostrophe sits inside a word, so treating `'` as a
#: quotation mark mistakes almost nothing.
STRAIGHT_QUOTE_CHARACTERS = "\"'"

#: How many words the note ran to. Written into the row, not shown as a column.
#:
#: A longer note has more chances to misspell something, so "this model writes
#: bad Czech" and "this model writes long notes" are the first two explanations
#: of the same number. Recording it costs nothing and makes the objection
#: answerable instead of arguable.
INTERNAL_MEASURES: tuple[str, ...] = ("note_words",)

MEASURES: dict[str, dict[str, str]] = {
    criterion.key: {
        "label": criterion.label,
        "scale": "0-1",
        "definition": f"{criterion.definition} Reported as the share of notes free of it.",
        "caveat": _NO_CONTENT_CHECK,
    }
    for criterion in CRITERIA
}

#: Seven measures, no average. See the module docstring.
RANKING_MEASURE = None

#: The criteria a judge decides, which is every one except `quotes`. Comparing
#: two judges on a column computed from the characters in the note would report
#: perfect agreement and mean nothing -- the same tautology `icare` avoids by
#: keeping ROUGE-L out of this tuple.
#:
#: Disagreement matters more on this track than anywhere else, because it has no
#: human anchor and is the only control it has. Where a column turns out flat,
#: `concordance.rankable` declines to report a figure, which is the honest
#: answer rather than a missing one.
JUDGE_MEASURES: tuple[str, ...] = tuple(c.key for c in CRITERIA if not c.computed)

PROMPT = """\
Níže je klinická poznámka z psychoterapeutického sezení, napsaná česky.

## Poznámka
{note}

## Otázka
{question}

{guidance}

Odpověz pouze slovem „ano“ nebo „ne“ a nic jiného:"""

#: Czech answers, normalised to what `pdsqi.parse_yes_no` reads.
_ANSWERS = {"ano": "yes", "ne": "no"}

#: The section headings `tasks.czech.render_note` writes, so that `_content`
#: can tell what the model wrote from what the renderer added. Imported rather
#: than repeated: two lists of four Czech words would drift.
_LABELS = frozenset(_task.SECTION_LABELS.values())


@dataclass(frozen=True)
class CriterionTask:
    """One criterion asked about one note, and where its answer is cached."""

    criterion: str
    prompt: str

    @property
    def unit(self) -> str:
        return f"czech.{self.criterion}"

    @property
    def kind(self) -> str:
        return "czech"

    @property
    def section(self) -> str:
        return "czech"


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


def parse_answer(answer: str) -> bool | None:
    """True when the fault is present, False when it is not, None otherwise.

    Delegates to `pdsqi.parse_yes_no` after translating the two Czech words,
    rather than writing a third yes/no parser. The question is Czech because the
    criteria are about Czech quotation marks, Czech diacritics and Czech
    clinical terms, so a judge answering in Czech is the expected case and an
    English answer is still read.

    None for anything else, never False. Reading "not yes" as "no" would declare
    every unanswered note free of the fault, which is the one failure a rubric
    of absences cannot afford.

    **The last line counts, and only the last line.** Measured on this corpus: a
    judge sometimes leaks its own deliberation into the answer and then answers
    anyway --

        '" - wait, no.\\n\\n    I will output "ne".\\nne'

    -- which is a rating, written where the prompt asked for it, preceded by
    text the prompt did not ask for. Taking the final line reads it; refusing
    would throw away an answer that is there. This is deliberately *not*
    `tneval.parse_likert`'s fallback, which scans the whole string for any digit
    and reads "4 (Patient says 2" as 2. Anywhere is a guess. The last line is
    where the answer was asked for.
    """
    text = (answer or "").strip()
    for candidate in (text, text.splitlines()[-1] if text else ""):
        normalised = candidate.strip().strip(".!?„“”\"'").lower()
        verdict = pdsqi.parse_yes_no(_ANSWERS.get(normalised, normalised))
        if verdict is not None:
            return verdict
    return None


def has_content(note: str) -> bool:
    """Whether there is a note here to judge at all.

    Every one of the seven criteria asks about the *absence* of a fault, and a
    note that says nothing has none of them: no misspelling, no calque, no slip
    of register. It would pass all seven. PDSQI-9 met the same shape and three
    of its eight attributes gave an empty note full marks against a therapist's
    4.20; here it would be seven of seven, because there is no companion measure
    of the kind that scores TN-Eval's empty note zero.

    So an empty note is not scored. It is not *dropped* either -- see
    `aggregate`. A model that wrote nothing must not have its worst note vanish.

    Judged on the values and not on the string, because the string is not empty:
    `tasks.czech.render_note` writes every section heading whether or not the
    section has anything under it, so a note with four blank sections still
    renders as four labels. Caught by a test rather than by reading, which is
    how `pdsqi.has_content` came by the same line.
    """
    return bool(_content(note).strip())


def _content(note: str) -> str:
    """What the model wrote, without the headings the renderer added.

    A line with no colon is content in its own right -- a model that ignored the
    template still wrote something, and counting it as a heading would report
    its note as empty.
    """
    parts = []
    for line in (note or "").splitlines():
        head, sep, tail = line.partition(":")
        parts.append(tail if sep and head.strip() in _LABELS else line)
    return "\n".join(parts)


def has_quotes(note: str) -> bool:
    """Whether the note quotes anything, and so could get the marks wrong.

    A note with no quotation marks cannot have the wrong ones. Counting it as
    clean would let a model score on `quotes` for never citing the client --
    the same vacuity as an empty note, smaller. Notes without the opportunity
    are left out of that column's denominator and counted beside it.
    """
    return any(character in note for character in QUOTE_CHARACTERS)


def has_straight_quotes(note: str) -> bool:
    """Whether the note uses a typewriter mark where Czech uses its own.

    The `quotes` criterion's answer, read off the string. It was a judge's
    answer until the two were compared: on the 75 notes that quote anything,
    `gemini-3.1-pro-preview` matched this function 75 times out of 75 and
    `gpt-5.6-terra` 65, reporting straight marks in nine notes that have none.
    Nothing is bought by asking.
    """
    return any(character in note for character in STRAIGHT_QUOTE_CHARACTERS)


def build_tasks(note: str) -> list[CriterionTask]:
    """The questions asked about one note -- one call each.

    Not one call returning seven answers. `judge.ANSWER_TOKENS` is inside the
    judge fingerprint and `judge.load_cached` rejects any answer whose
    fingerprint differs, so raising it to fit a longer reply would re-key and
    throw away every cached answer belonging to the other tracks.

    The prompt carries the note and nothing else. There is no transcript in it
    and no parameter one could arrive through, which is why the confidential
    Czech sessions never reach the judge's provider -- only the note a model
    wrote about them does.
    """
    if not has_content(note):
        return []

    return [
        CriterionTask(
            criterion=criterion.key,
            prompt=PROMPT.format(
                note=note, question=criterion.question, guidance=criterion.guidance
            ),
        )
        for criterion in CRITERIA
        if not criterion.computed and (not criterion.gated or has_quotes(note))
    ]


def note_words(note: str) -> int:
    """How long the note is, not counting the headings the renderer wrote."""
    return len(_content(note).split())


def aggregate(note: str, answers: dict[str, str]) -> Scores:
    """One note's seven answers, or a named account of what is missing.

    A criterion the judge did not answer is listed in `incomplete`, never scored
    as clean and never quietly dropped from a denominator. A criterion the note
    gave no chance to make -- quotation marks in a note that quotes nothing --
    is neither: it is simply absent, and `_mean_of_dicts` averages the notes
    that have a value.

    An empty note has no answers at all and is therefore partial. That is the
    honest treatment *here* and the opposite of TN-Eval's, where an empty note
    must stay in the mean because completeness legitimately scores it zero. A
    proportion of notes free of a diacritic error is a statement about notes
    that have some Czech in them; an empty note is not bad Czech, it is missing
    Czech, and `n_sessions_partial` and `note_words` are where it shows.
    """
    scores = Scores()
    missing: list[str] = []
    asked = {task.criterion for task in build_tasks(note)}
    content = has_content(note)

    for criterion in CRITERIA:
        if criterion.computed:
            # Read off the note, but under the same two rules as the rest: an
            # empty note is not rated at all, and a note with no quotation marks
            # is absent from this column rather than clean in it.
            if content and (not criterion.gated or has_quotes(note)):
                fault = has_straight_quotes(note)
                scores.headline[criterion.key] = 0.0 if fault else 1.0
                scores.by_criterion[criterion.key] = scores.headline[criterion.key]
            continue
        if criterion.key not in asked:
            continue
        present = parse_answer(answers.get(f"czech.{criterion.key}", ""))
        if present is None:
            missing.append(criterion.key)
            continue
        # The fault's absence, so that every column is better when higher.
        scores.headline[criterion.key] = 0.0 if present else 1.0
        scores.by_criterion[criterion.key] = scores.headline[criterion.key]

    if missing or not asked:
        scores.incomplete["czech"] = missing or list(CRITERION_KEYS)

    # Not a judge measure and not a column, so it is recorded whatever the judge
    # did or did not answer -- including for the empty note it explains.
    scores.headline["note_words"] = float(note_words(note))
    scores.sections_used["czech"] = len(asked) - len(missing)
    return scores
