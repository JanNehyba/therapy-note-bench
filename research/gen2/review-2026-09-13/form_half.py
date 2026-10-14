"""The half of the error literature the consensus taxonomy threw away.

Huidrom and Belz merged fifteen schemes into one taxonomy and said what they
left out: "We removed those categories that relate to errors in the form, rather
than the content, of outputs." Every Czech language criterion is a form error,
so the search that found nothing for them had been looking in the half those
categories had been deliberately removed from.

This reads the other paper by the same authors, the survey the merge was built
on, which covers twenty-two papers and keeps both halves.

What it finds, and one correction it forces on this project's own account.

The field's two top branches have names and definitions, from MQM: accuracy for
content and fluency for form. The fluency branch is the missing half and it
names its own subtypes: spelling, punctuation, grammatical rules, inconsistent
style, unidiomatic style.

And `untranslated` is not in it. MQM puts an untranslated term under accuracy,
because the target does not correspond to the source. So the claim made on
2026-10-14 that all six Czech criteria are errors of form is wrong for one of
them, and the correction belongs in the record rather than in a quiet edit.

Every quote is checked against the extracted text before this file is written.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
SOURCE = REPO / "local" / "gen2-language-fulltext" / "huidrom-belz-2022-survey.txt"
OUT = ROOT / "form-half.json"

PAPER = {
    "key": "huidrom-belz-2022-survey",
    "title_in_the_document": "A Survey of Error Annotation Schemes for Human and Machine "
    "Generated Text",
    "title_in_the_anthology_record": "A Survey of Recent Error Annotation Schemes for "
    "Automatically Generated Text",
    "authors": "Rudali Huidrom and Anya Belz",
    "venue": "2nd Workshop on Natural Language Generation, Evaluation, and Metrics (GEM), "
    "2022, pages 383-398",
    "url": "https://aclanthology.org/2022.gem-1.33/",
    "note": "The bibliographic record and the document disagree on the title, which the "
    "retrieval check caught on 2026-10-14. The document's title is the one used here, and it "
    "is the more accurate of the two: this survey covers human-written text as well as "
    "generated text, which is what this benchmark compares a model against.",
}

FINDINGS = [
    {
        "id": "F1",
        "finding": "The field's two top branches have names and definitions, and the one this "
        "project needs is called fluency",
        "quote": "Fluency: Errors related to grammar and style. Examples include errors "
        "relating to spelling, punctuation, grammatical rules, inconsistent style, "
        "unidiomatic style etc.",
        "source_of_the_definition": "MQM, the Multidimensional Quality Metrics framework "
        "(Lommel et al., 2014), as the survey quotes it",
        "what_it_means_here": "This is the missing half, named, with its own subtypes. "
        "Spelling, punctuation, grammatical rules, inconsistent style and unidiomatic style "
        "cover five of the seven questions the Czech rating sheet asks. The catalog has no "
        "such branch and no criterion that says it is about form rather than content.",
    },
    {
        "id": "F2",
        "finding": "An untranslated term is an accuracy error, not a fluency one",
        "quote": "Accuracy: Errors where the target sentence does not correspond to the source "
        "text due to omission, distortion or addition to the text. Error types include "
        "mistranslation, overtranslation, under-translation, untranslated, omission, and "
        "addition.",
        "source_of_the_definition": "MQM, as the survey quotes it",
        "what_it_means_here": "A correction to what this project said on 2026-10-14. The claim "
        "was that all six Czech criteria are errors of form, and that this explains why the "
        "content literature could not support them. For `untranslated` that is wrong: MQM puts "
        "it under accuracy, because a term left in the source language means the target does "
        "not correspond to the source. The explanation still holds for the other five. It also "
        "makes sense of a finding from the same day that looked like luck: `untranslated` was "
        "the one of the six that already had a named category in the content literature, "
        "Russian Code-Switching, because it was never a form error to begin with.",
    },
    {
        "id": "F3",
        "finding": "A taxonomy whose top level is mostly form",
        "quote": "At the top level, the taxonomy is divided into five categories: orthography, "
        "lexis, grammar, semantic and discourse.",
        "source_of_the_definition": "Costa et al. (2015), a linguistically motivated taxonomy "
        "for English to European Portuguese machine translation, five levels and 25 leaf "
        "nodes, as the survey describes it",
        "what_it_means_here": "Three of these five are form: orthography, lexis and grammar. "
        "They line up with the Czech criteria one for one, which is the support that was "
        "missing. The fourth, semantic, is what the consensus taxonomy kept. The fifth, "
        "discourse, has no counterpart among the 39 candidates at all and is the clearest "
        "candidate for something this project does not measure.",
    },
    {
        "id": "F4",
        "finding": "The survey covers twenty-two papers; the merge used fifteen",
        "quote": "Our survey reviews the resulting 22 papers.",
        "source_of_the_definition": "the survey's own paper selection section",
        "what_it_means_here": "The consensus taxonomy of 2023 built on fifteen of these for "
        "content. The arithmetic says where the form categories went: they were collected "
        "from all of them and then dropped from the merged result. Seven papers of the "
        "twenty-two were not used for the merge at all, and nobody here has looked at which.",
    },
]

#: What a Czech criterion maps onto once the form half is visible. The keys are
#: the ones local/czech-anchor.json uses, so this file carries no Czech and the
#: rule that keeps the Czech behind one allow-list entry holds here too. The mapping
#: is the assistant's judgement and is recorded as one, next to the words it was
#: made from.
MAPPING = [
    {
        "czech_criterion": "diacritics",
        "lands_in": "orthography (Costa et al.), spelling (MQM fluency)",
        "note": "Orthography is the branch, and the Greek ELERRANT adds an accent category "
        "under it from scratch. Czech diacritics belong in the same place.",
    },
    {
        "czech_criterion": "nonword",
        "lands_in": "orthography / spelling",
        "note": "A misspelling and an invented word are both orthographic in these schemes. "
        "The Czech sheet separates them and the schemes do not, which is a difference worth "
        "keeping: an invented professional term is a different failure from a typo.",
    },
    {
        "czech_criterion": "agreement",
        "lands_in": "grammar (Costa et al.), grammatical rules (MQM fluency)",
        "note": "Straightforward. Agreement and case are grammar in every scheme that has a "
        "grammar branch.",
    },
    {
        "czech_criterion": "calque",
        "lands_in": "lexis (Costa et al.), unidiomatic style (MQM fluency)",
        "note": "The closest named thing in the field is `unidiomatic style`, which is what a "
        "calque is: a construction carried over from another language that native usage does "
        "not have. It is weaker than a category of its own and it is more than nothing, which "
        "is what the catalog had.",
    },
    {
        "czech_criterion": "register",
        "lands_in": "inconsistent style (MQM fluency)",
        "note": "`Inconsistent style` is about a text that does not hold one register. That is "
        "the criterion, named, in the framework the field uses.",
    },
    {
        "czech_criterion": "quotes",
        "lands_in": "punctuation (MQM fluency)",
        "note": "Punctuation is a named subtype of fluency. The question dropped out of this "
        "project's set on 2026-10-14 as a format check, and that is still the right place for "
        "it, but it is not outside the field's taxonomy as that decision implied.",
    },
    {
        "czech_criterion": "untranslated",
        "lands_in": "accuracy, not fluency",
        "note": "See F2. This one is a content error in MQM's terms, so it was never in the "
        "missing half.",
    },
]


def flat(text: str) -> str:
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    return re.sub(r"\s+", " ", text)


def main() -> int:
    if not SOURCE.is_file():
        print(f"the source text is not on this machine: {SOURCE.name}")
        return 2
    raw = SOURCE.read_bytes()
    body = flat(raw.decode("utf-8", errors="replace"))

    missing = [f["id"] for f in FINDINGS if flat(f["quote"]) not in body]
    if missing:
        print("these quotes are not in the source and were not written:")
        for name in missing:
            print(f"  {name}")
        return 2

    record = {
        "version": "form-half-v1",
        "date": datetime.now(UTC).date().isoformat(),
        "marker": "AUTHORED-INSTRUMENT-TEXT",
        "what_this_is": (
            "The reading of the form half of the error literature: the categories the "
            "consensus taxonomy of 2023 collected from fifteen schemes and then removed, "
            "because it treats content only. Every Czech language criterion is a form error, "
            "so this is where their support was."
        ),
        "why_it_was_missing": (
            "Not a gap in the literature and not a gap in the search. The merge this project "
            "read first says in its own words that it removed the form categories, and nobody "
            "here noticed until 2026-10-14."
        ),
        "paper": PAPER,
        "source_text_sha256": hashlib.sha256(raw).hexdigest(),
        "every_quote_was_found_in_that_text": True,
        "findings": FINDINGS,
        "what_the_czech_criteria_map_onto": MAPPING,
        "the_correction_this_forces": (
            "On 2026-10-14 this project said all six Czech criteria are errors of form. That "
            "is wrong for `untranslated`, which MQM places under accuracy. Five of the six "
            "are form errors and the explanation holds for them."
        ),
        "what_is_new_rather_than_support": (
            "Discourse. Costa et al. have it as one of five top categories and no candidate of "
            "the 39 asks about it. Whether a session note has a discourse-level property worth "
            "measuring is a question for the investigator, not something to adopt from a "
            "translation taxonomy without thinking."
        ),
        "nothing_is_in_the_catalog_yet": (
            "No candidate is created and no criterion is re-stated here. What this changes is "
            "that five of the six Czech criteria now have a named place in the field's "
            "framework rather than none."
        ),
        "still_unread": (
            "The twenty-two papers of the survey themselves. This reads the survey's account "
            "of them, which is one step removed from each scheme: a category named in a "
            "summary is weaker evidence than a category read in the paper that defines it."
        ),
    }
    OUT.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"{len(FINDINGS)} findings, every quote verified against {SOURCE.name}")
    for f in FINDINGS:
        print(f"  {f['id']}  {f['finding']}")
    print(f"\n{len(MAPPING)} Czech criteria placed; one of them is accuracy and not form")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
