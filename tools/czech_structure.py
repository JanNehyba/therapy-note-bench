"""What the notes look like, before anybody interprets them.

The repository can count words and nothing else about the shape of a note:
``czech_length.py`` measures length and ``czech.py`` strips headings so it can
tell an empty note from a written one. Nothing extracts a sub-heading, a list
marker, a quotation mark or a paragraph. This does.

**It is a screen, not a measurement, and the difference decides how to read it.**
Every feature here is a regular expression over the note, so every one of them
has a false-positive rate nobody has measured. A quotation mark is not a
quotation of the client; a capitalised line ending in a colon is not necessarily
a sub-heading. What the census can establish is the negative: a feature that does
not vary here cannot separate models however it is measured, so it is not worth
putting to a reader. What it cannot establish is that a feature that *does* vary
means anything.

**The variance split is the point of the file.** Every model wrote from every
session, so a feature's variance decomposes into a part that belongs to the model,
a part that belongs to the session and a residual. A feature whose variance sits
in the session orders transcripts rather than models -- which is exactly what the
briefing already says about several published criterion columns. Doing this
before any coder is asked is what stops a reader spending attention on note-level
noise.

The decomposition is the plain two-way one with no interaction term, on a grid
that is complete apart from the notes nobody wrote. It is reported as three
shares that sum to one, never as a significance test: eleven models over ten
sessions is not enough grid for that, and a share is honest about being a
description.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path

from tnb.scoring import czech_run, deepsy_run
from tnb.tasks import czech as czech_task
from tnb.tasks import deepsy as deepsy_task

REPO = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = REPO / "local" / "czech-structure.json"

#: Every track, with the loader and assembler that reach its notes. The same
#: shape as ``czech_variance.CRITERIA_TRACKS``, and for the same reason its
#: docstring gives: a track that loads the wrong sessions pairs a note with a
#: transcript that is not its own.
TRACKS: dict[str, dict] = {
    "czech-real": {"loader": czech_task.load_real, "task": czech_task.NAME_REAL},
    "czech-translated": {
        "loader": czech_task.load_translated,
        "task": czech_task.NAME_TRANSLATED,
    },
    "deepsy-real": {"loader": czech_task.load_real, "task": deepsy_task.NAME_REAL},
    "deepsy-translated": {
        "loader": czech_task.load_translated,
        "task": deepsy_task.NAME_TRANSLATED,
    },
}

#: A line that opens with a capitalised label and a colon. The commonest way a
#: model puts a heading inside a section it was not asked to structure.
LABEL_LINE = re.compile(r"(?m)^\s*([A-ZÁ-Ža-zá-ž][^:\n]{1,45}):\s")

#: Markdown emphasis used as a heading. Rare here -- the SOAP note comes back as
#: a JSON string rather than a document -- and counted so that "rare" is a
#: measured word.
BOLD = re.compile(r"\*\*[^*\n]{1,60}\*\*")
HASH_HEADING = re.compile(r"(?m)^\s*#{1,6}\s+\S")

#: List markers, dash and numeric.
BULLET = re.compile(r"(?m)^\s*[-*•–]\s+\S")
NUMBERED = re.compile(r"(?m)^\s*\d+[.)]\s+\S")

#: Quotation, by style. Kept apart because the style is itself a per-model
#: fingerprint, and because a straight double quote inside a JSON string has to
#: be escaped by the model and so is suppressed for a reason that is nothing to
#: do with how it writes.
QUOTE_STYLES = {
    "czech": re.compile(r"[„“]"),
    "straight_double": re.compile(r'"'),
    "single": re.compile(r"(?<!\w)'|'(?!\w)"),
    "guillemet": re.compile(r"[»«]"),
    "curly_double": re.compile(r"[”‘’]"),
}

#: Assertions about something a text transcript cannot carry. The real
#: transcripts contain no paralinguistic annotation at all -- zero bracketed
#: cues in ten files -- so a note that reports these is reporting something the
#: input did not contain. Whether that is a fault of the model or of a prompt
#: that asked for appearance and speech is exactly what this cannot say.
UNSUPPORTED_MODALITY = re.compile(
    r"tempo\s+řeči|plynul\w*\s+řeč|rychlost\s+řeči|tón\w*\s+hlasu|intonac|hlasitost"
    r"|oční\s+kontakt|kontakt\s+očima|mimik|gestikul|držení\s+těla|neverbáln"
    r"|psychomotor|vzhled|upraven\w+|oblečen|hygien",
    re.IGNORECASE,
)

#: Saying the information is not available, rather than inventing it.
DECLINED = re.compile(
    r"nelze\s+posoudit|nelze\s+hodnotit|není\s+k\s+dispozici|nebylo\s+možné\s+posoudit"
    r"|z\s+přepisu\s+nelze|nelze\s+z\s+přepisu|není\s+možné\s+posoudit|neuvedeno"
    r"|nepozorováno|z\s+textu\s+nevyplývá|údaje\s+chybí|chybí\s+údaje"
    r"|nejsou\s+k\s+dispozici|není\s+zaznamenáno|nebyl\w*\s+pozorován|není\s+popsán"
    r"|přepis\w*\s+neobsahuje|na\s+základě\s+přepisu\s+nelze",
    re.IGNORECASE,
)

#: A section shorter than this is treated as not written. The same twenty
#: characters ``czech.has_content`` uses for a whole note.
NEAR_EMPTY_CHARS = 20

#: Czech words carrying no topic, dropped before measuring how much one section
#: repeats another. Without this the overlap measures grammar.
STOPWORDS = frozenset(
    # fmt: off
    """a aby ale ani ano az bez bude budou by byl byla bylo byt ci co coz cz dalsi
    do ho i jak jako je jeho jej jeji jejich jen jeste ji jine jiz jsem jsi jsme
    jsou jste k kam kde kdo kdy kdyz ke kterou ktera ktere kteri ktery ku ma mate
    me mezi mi mit mne mnou muj muze na nad nam nas nasi ne nebo nebot nej nejsou
    neni nez nic nove novy o od podle pod pokud potom pouze prave pred pres pri
    pro proc proti protoze prvni s se si sice smi ta tak takze tam tato te tedy
    tento teto tim timto to tohle toho tohoto tom tomto tomuto tu tudiz tuto tvuj
    ty tyto u uz v vam vas vase ve vedle vice vsak vsechen vsechny vy vzdy z za
    zda zde ze zpet""".split()  # noqa: SIM905
    # fmt: on
)

WORD = re.compile(r"[0-9A-Za-zÀ-žÁ-ž]+")

STRIP_DIACRITICS = str.maketrans("áčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ", "acdeeinorstuuyzACDEEINORSTUUYZ")


def _tokens(text: str) -> set[str]:
    """Topic-bearing word stems, for measuring how much two sections share.

    Diacritics are folded and the first six characters kept, which is a crude
    stand-in for a Czech lemmatiser. It is crude in a direction that matters:
    it over-merges, so it reports *more* overlap than a real lemmatiser would.
    The number is therefore an upper bound on repetition, which is the safe
    direction for a screen whose job is to rule features out.
    """
    out = set()
    for word in WORD.findall(text.lower()):
        folded = word.translate(STRIP_DIACRITICS)
        if len(folded) >= 4 and folded not in STOPWORDS:
            out.add(folded[:6])
    return out


def _jaccard(left: set[str], right: set[str]) -> float | None:
    """Overlap of two token sets, or None when either side is empty.

    None rather than 0.0 or 1.0: two empty sections are not two sections that
    repeat each other perfectly, and one empty section is not a section that
    repeats nothing. Both readings would be a measurement of an absence.
    """
    if not left or not right:
        return None
    union = left | right
    return round(len(left & right) / len(union), 4) if union else None


def features(note: dict[str, str]) -> dict:
    """Every surface feature of one note.

    Counts and rates only. Nothing here is a judgement and nothing here is
    published without the sentence saying so.
    """
    sections = {key: (value or "").strip() for key, value in note.items()}
    body = "\n".join(sections.values())
    words = {key: len(value.split()) for key, value in sections.items()}
    total_words = sum(words.values())

    quotes = {style: len(pattern.findall(body)) for style, pattern in QUOTE_STYLES.items()}
    quote_total = sum(quotes.values())

    out = {
        "words": total_words,
        "sections": len(sections),
        "section_words": words,
        "near_empty_sections": sum(
            1 for value in sections.values() if len(value) < NEAR_EMPTY_CHARS
        ),
        "paragraphs": sum(
            len([part for part in value.split("\n") if part.strip()]) for value in sections.values()
        ),
        "sections_with_a_line_break": sum(1 for value in sections.values() if "\n" in value),
        "subheading_labels": sorted({match.strip() for match in LABEL_LINE.findall(body)}),
        "subheadings": len(LABEL_LINE.findall(body)),
        "bold": len(BOLD.findall(body)),
        "hash_headings": len(HASH_HEADING.findall(body)),
        "bullets": len(BULLET.findall(body)),
        "numbered": len(NUMBERED.findall(body)),
        "quotes": quotes,
        "quote_total": quote_total,
        "declined": len(DECLINED.findall(body)),
    }

    # Present/absent forms, which is what a yes/no column would ask.
    out["has_subheading"] = float(out["subheadings"] > 0)
    out["has_bullet"] = float(out["bullets"] + out["numbered"] > 0)
    out["has_quote"] = float(quote_total > 0)
    out["has_declined"] = float(out["declined"] > 0)

    # SOAP-only measures. A Deepsy note has eleven sections and no subjective or
    # assessment, so these are absent rather than zero -- the whole point.
    if {"subjective", "assessment", "objective"} <= set(sections):
        if total_words:
            out["subjective_share"] = round(words["subjective"] / total_words, 4)
            out["assessment_share"] = round(words["assessment"] / total_words, 4)
        subjective, assessment = (
            _tokens(sections["subjective"]),
            _tokens(sections["assessment"]),
        )
        out["subjective_assessment_overlap"] = _jaccard(subjective, assessment)
        out["subjective_objective_overlap"] = _jaccard(subjective, _tokens(sections["objective"]))
        objective = sections["objective"]
        out["unsupported_modality"] = len(UNSUPPORTED_MODALITY.findall(objective))
        out["has_unsupported_modality"] = float(out["unsupported_modality"] > 0)
        out["objective_words"] = words["objective"]
    return out


def variance_split(cells: dict[tuple[str, str], float]) -> dict | None:
    """Where a feature's variance sits: the model, the session, or neither.

    A plain additive two-way decomposition. Returns None rather than a number
    when the grid is too thin to carry one -- fewer than two models, fewer than
    two sessions, or no variation at all. A zero here would read as "nothing
    belongs to the model", which is a different claim from "this cannot be
    decomposed".
    """
    models = sorted({model for model, _ in cells})
    sessions = sorted({session for _, session in cells})
    if len(models) < 2 or len(sessions) < 2 or len(cells) < 4:
        return None

    grand = statistics.fmean(cells.values())
    by_model = {
        model: statistics.fmean([v for (m, _), v in cells.items() if m == model])
        for model in models
    }
    by_session = {
        session: statistics.fmean([v for (_, s), v in cells.items() if s == session])
        for session in sessions
    }
    model_var = statistics.pvariance(list(by_model.values()))
    session_var = statistics.pvariance(list(by_session.values()))
    residual_var = statistics.pvariance(
        [v - by_model[m] - by_session[s] + grand for (m, s), v in cells.items()]
    )
    total = model_var + session_var + residual_var
    if total <= 0:
        return None
    return {
        "model": round(model_var / total, 4),
        "session": round(session_var / total, 4),
        "residual": round(residual_var / total, 4),
        "cells": len(cells),
        "models": len(models),
        "sessions": len(sessions),
        "mean": round(grand, 4),
    }


#: The features the split is computed for. Only the numeric ones, and only the
#: ones a column could plausibly be built on.
SPLIT_FEATURES = (
    "words",
    "has_subheading",
    "subheadings",
    "has_bullet",
    "has_quote",
    "quote_total",
    "has_declined",
    "near_empty_sections",
    "subjective_share",
    "assessment_share",
    "subjective_assessment_overlap",
    "unsupported_modality",
    "has_unsupported_modality",
)


def _candidates(track: str) -> list:
    spec = TRACKS[track]
    sessions = spec["loader"]()
    if track.startswith("deepsy"):
        return list(deepsy_run.from_generations(sessions, task_name=spec["task"]))
    return list(czech_run.from_generations(sessions, task_name=spec["task"]))


def survey(track: str) -> dict:
    per_note = {}
    for candidate in _candidates(track):
        per_note[(candidate.system_id, candidate.session_id)] = features(candidate.note)

    models = sorted({model for model, _ in per_note})
    sessions = sorted({session for _, session in per_note})

    splits = {}
    for name in SPLIT_FEATURES:
        cells = {
            key: float(value[name])
            for key, value in per_note.items()
            if value.get(name) is not None
        }
        split = variance_split(cells)
        if split is not None:
            splits[name] = split

    by_model: dict[str, dict] = {}
    for model in models:
        rows = [value for (m, _), value in per_note.items() if m == model]
        entry: dict = {"notes": len(rows)}
        for name in SPLIT_FEATURES:
            values = [row[name] for row in rows if row.get(name) is not None]
            if values:
                entry[name] = round(statistics.fmean(values), 4)
                entry[f"{name}.notes"] = len(values)
        labels: set[str] = set()
        for row in rows:
            labels.update(row["subheading_labels"])
        entry["distinct_subheading_labels"] = len(labels)
        by_model[model] = entry

    return {
        "notes": len(per_note),
        "models": models,
        "sessions": sessions,
        "by_model": by_model,
        "variance": splits,
        "subheading_labels": sorted(
            {label for value in per_note.values() for label in value["subheading_labels"]}
        ),
    }


CAVEAT = (
    "Every feature here is a regular expression over the note text. A quotation "
    "mark is not a quotation of the client and a capitalised line ending in a "
    "colon is not necessarily a sub-heading, and no false-positive rate has been "
    "measured for any of them. Read a feature that does NOT vary as settled -- it "
    "cannot separate models however it is measured. Read a feature that does vary "
    "as a place to look, never as a finding."
)


def build() -> dict:
    return {
        "caveat": CAVEAT,
        "tracks": {track: survey(track) for track in TRACKS},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Surface features of the Czech notes.")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    payload = build()
    args.target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.target}")
    for track, survey_out in payload["tracks"].items():
        print(f"\n{track}: {survey_out['notes']} notes, {len(survey_out['models'])} models")
        print(f"  {'feature':32s} {'model':>6s} {'session':>8s} {'resid':>6s} {'mean':>8s}")
        for name, split in survey_out["variance"].items():
            print(
                f"  {name:32s} {split['model']:6.2f} {split['session']:8.2f} "
                f"{split['residual']:6.2f} {split['mean']:8.3f}"
            )


if __name__ == "__main__":
    main()
