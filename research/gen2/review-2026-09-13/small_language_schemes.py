"""What schemes built for languages other than English say, read one by one.

The deductive half of this layer searched for the six properties the Czech
scorer already measures and counted how many papers mention them. That can
confirm; it cannot find. The inductive half selected papers structurally -- the
title says it defines a taxonomy of errors, by a pattern that names no error --
and the selection turned out to be mostly invisible to the deductive queries:
of 1941 papers in the Anthology that enumerate kinds of error, they could reach
373, and of the 64 that define a taxonomy in their title, 29.

Twenty-one of those 64 name a language other than English in the title. This
reads four of them, chosen because each is built for a language that inflects or
is short of resources, which is the situation the second generation exists for.

Every quote is checked against the extracted text of the paper before this file
is written, as the consensus-taxonomy mapping is. What each category means for
this catalog is the assistant's judgement, labelled as one.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
TEXTS = REPO / "local" / "gen2-language-fulltext"
OUT = ROOT / "small-language-schemes.json"

PAPERS = {
    "elerrant": {
        "file": "korre-etal-2021-elerrant.txt",
        "title": "ELERRANT: Automatic Grammatical Error Type Classification for Greek",
        "authors": "Katerina Korre, Marita Chatzipanagiotou and John Pavlopoulos",
        "venue": "Recent Advances in Natural Language Processing (RANLP), 2021",
        "url": "https://aclanthology.org/2021.ranlp-1.81/",
        "language": "Greek",
        "why_read": "A language-specific extension of an English scheme for a language that "
        "inflects and carries diacritics. The same shape the second generation needs.",
    },
    "multilingual": {
        "file": "qiu-etal-2025-multilingual.txt",
        "title": "Multilingual Grammatical Error Annotation: Combining Language-Agnostic "
        "Framework with Language-Specific Flexibility",
        "authors": "Mengyang Qiu, Tran Minh Nguyen, Zihao Huang, Zelong Li, Yang Gu, "
        "Qingyu Gao, Siliang Liu and Jungyeul Park",
        "venue": "Workshop on Innovative Use of NLP for Building Educational Applications "
        "(BEA), 2025",
        "url": "https://aclanthology.org/2025.bea-1.15/",
        "language": "English, German, Czech, Korean, Chinese",
        "why_read": "It covers Czech, and its structure is a language-agnostic base with "
        "language-specific extensions, which is exactly the problem this benchmark has.",
    },
    "repa": {
        "file": "pugachev-etal-2025-repa.txt",
        "title": "REPA: Russian Error Types Annotation for Evaluating Text Generation and "
        "Judgment Capabilities",
        "authors": "Alexander Pugachev et al.",
        "venue": "Workshop on Balto-Slavic Natural Language Processing (BSNLP), 2025",
        "url": "https://aclanthology.org/2025.bsnlp-1.16/",
        "language": "Russian",
        "why_read": "Ten error types that humans annotated on generated text in an inflected "
        "Slavic language, and a measurement of how a judge does in it rather than in English.",
    },
    "talktag": {
        "file": "venturini-etal-2026-talktag.txt",
        "title": "TalkTag: Fine-Grained Morphosyntactic Error Annotation for Transcribed Speech",
        "authors": "Venturini et al.",
        "venue": "Linguistic Annotation Workshop (LAW), 2026",
        "url": "https://aclanthology.org/2026.law-main.20/",
        "language": "low-resource, children's narrative data",
        "why_read": "Clinical morphosyntactic annotation of transcribed speech: the setting "
        "of the Czech track, where the transcript is speech recognition output.",
    },
}

#: Each category as the paper names it, in the paper's own words, with what it
#: means for this catalog. `bears_on` names one of the six Czech criteria the
#: catalog could not support, or is None where the category is new to us.
CATEGORIES = [
    {
        "paper": "elerrant",
        "category": "ACC - Accentuation",
        "quote": "ACC Accentuation Accentuation addition or removal.",
        "bears_on": "diacritics",
        "what_it_means_here": "The first published support for the Czech scorer's diacritics "
        "criterion, and it arrives in the shape that matters: not as prose about how accents "
        "are hard, but as one error type of fourteen in a working classifier for a language "
        "that has them. Greek is not Czech, and an accent in Greek marks stress where a Czech "
        "diacritic can change the word, so the rule transfers and its severity does not.",
    },
    {
        "paper": "elerrant",
        "category": "VERB:SVA - Subject Verb Agreement",
        "quote": "VERB:SVA Subject Verb Agreement The subject and the verb to be in person "
        "agreement.",
        "bears_on": "agreement",
        "what_it_means_here": "Agreement as its own error type rather than a corner of "
        "grammar. The Czech scorer bundles agreement, case and an unfinished sentence into one "
        "criterion; this paper separates them, which is the direction to take rather than a "
        "disagreement.",
    },
    {
        "paper": "elerrant",
        "category": "WO - Word Order",
        "quote": "WO Words Order Error in words order.",
        "bears_on": None,
        "what_it_means_here": "Nobody on this project proposed word order, and it is a "
        "category in both schemes built for an inflected language. In Czech word order carries "
        "emphasis and given/new structure rather than grammatical role, so a note can be "
        "grammatical and still say the wrong thing by its order. None of the candidates "
        "asks about it.",
    },
    {
        "paper": "elerrant",
        "category": "UNK - an error that can be detected but not corrected",
        "quote": "UNK Unknown error type An error that can be detected but not corrected.",
        "bears_on": None,
        "what_it_means_here": "A category for being able to see that something is wrong "
        "without being able to say what the right version is. This project has the same "
        "instinct written as a rule -- an absence is never a measurement -- and no category "
        "that implements it for a language error. Worth having, because the alternative is a "
        "rater silently choosing between a wrong label and no label.",
    },
    {
        "paper": "multilingual",
        "category": "the language-agnostic base: Missing, Replacement, Unnecessary, crossed "
        "with part of speech",
        "quote": "Our approach combines a language-agnostic foundation with structured "
        "language-specific extensions, enabling both consistency and flexibility across "
        "languages.",
        "bears_on": None,
        "what_it_means_here": "The structural answer to the question the second generation "
        "asks. An error is missing, replaced or unnecessary, crossed with the part of speech "
        "it touches; that much holds in any language, and what each language adds sits on top "
        "and is declared. This is the shape the Czech criteria should have had from the start, "
        "instead of six flat properties with no relation to the English ones.",
    },
    {
        "paper": "multilingual",
        "category": "Czech word order annotated with the part of speech involved",
        "quote": "For Czech, the example highlights differences in word order (WO) annotation: "
        "our method distinguishes between auxiliary and main verbs by incorporating POS "
        "information, whereas prior work generally treated such cases as generic WO errors.",
        "bears_on": None,
        "what_it_means_here": "Czech is one of the five languages the framework was actually "
        "applied to, against a published Czech error corpus. So there is a Czech reference "
        "point for this, which is more than the catalog had for any of the six.",
    },
    {
        "paper": "repa",
        "category": "Code-Switching",
        "quote": "Code -Switching: The chatbot 's response contains unexpected switching "
        "between languages.",
        "bears_on": "untranslated",
        "what_it_means_here": "Support for the untranslated-term criterion, from a Slavic "
        "language, as one of ten error types that human annotators actually labelled. The "
        "paper's definition is wider than ours -- any unexpected switch, not only a technical "
        "term left in English -- which is an argument for widening ours rather than for "
        "keeping it narrow.",
    },
    {
        "paper": "repa",
        "category": "Fluency, defined by whether comprehension is hindered",
        "quote": "Fluency: The response contains critical grammatical errors that may hinder "
        "text comprehension.",
        "bears_on": "agreement",
        "what_it_means_here": "The useful part is the threshold. Not every grammatical slip "
        "counts, only one that may stop a reader understanding. The catalog's language "
        "criterion has no such threshold, so it treats a missing comma and an unreadable "
        "sentence as the same kind of finding.",
    },
    {
        "paper": "repa",
        "category": "Sudden Interruption",
        "quote": "Sudden Interruption: The chatbot 's response was abruptly cut off.",
        "bears_on": None,
        "what_it_means_here": "This project treats a cut-off answer as a harness failure: "
        "finish_reason decides whether a row is usable, and a truncated note never reaches "
        "scoring. REPA treats it as a property of the text that a human rates. Both can be "
        "right, and which one this benchmark wants is a decision nobody has made.",
    },
    {
        "paper": "repa",
        "category": "a judge does worse in Russian than in English",
        "quote": "Our findings reveal a notable gap between LLM judge performance in Russian "
        "and English.",
        "bears_on": None,
        "what_it_means_here": "Not a criterion, a warning. This benchmark judges Czech notes "
        "with judges whose calibration was measured on English, and the one paper that "
        "measured the same thing for a Slavic language found the judge worse there. The "
        "calibration against the two human annotators has to be repeated in Czech, not "
        "carried over.",
    },
    {
        "paper": "talktag",
        "category": "flagging the cases automated tagging cannot decide",
        "quote": "effectively identifying instances where linguistic ambiguity makes automated "
        "tagging genuinely complex",
        "bears_on": None,
        "what_it_means_here": "The same idea as the Greek UNK category, and from a clinical "
        "setting with transcribed speech, which is this track's setting exactly. A tool that "
        "says which cases it could not decide is the tool this project's own rule asks for.",
    },
]


def flat(text: str) -> str:
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    return re.sub(r"\s+", " ", text)


def main() -> int:
    bodies = {}
    digests = {}
    for key, paper in PAPERS.items():
        path = TEXTS / paper["file"]
        if not path.is_file():
            print(f"the source text is not on this machine: {path.name}")
            return 2
        raw = path.read_bytes()
        bodies[key] = flat(raw.decode("utf-8", errors="replace"))
        digests[key] = hashlib.sha256(raw).hexdigest()

    missing = [c["category"] for c in CATEGORIES if flat(c["quote"]) not in bodies[c["paper"]]]
    if missing:
        print("these quotes are not in the source and were not written:")
        for name in missing:
            print(f"  {name}")
        return 2

    supported = sorted({c["bears_on"] for c in CATEGORIES if c["bears_on"]})
    new = [c for c in CATEGORIES if not c["bears_on"]]
    out = {
        "version": "small-language-schemes-v1",
        "date": datetime.now(UTC).date().isoformat(),
        "what_this_is": (
            "Error categories from four schemes built for languages other than English, read "
            "one by one, each with the paper's own words. The inductive half of the language "
            "layer: the papers were selected because their title says they define a taxonomy, "
            "by a pattern that names no category."
        ),
        "why_it_exists": (
            "The deductive half searched for the six properties the Czech scorer already "
            "measures. It could confirm them and could not find anything else. These four "
            "papers were chosen for being built for a language that inflects or is short of "
            "resources, which is the situation the second generation exists for."
        ),
        "papers": {k: {**v, "source_text_sha256": digests[k]} for k, v in PAPERS.items()},
        "every_quote_was_found_in_its_paper": True,
        "counts": {
            "categories": len(CATEGORIES),
            "bearing_on_one_of_the_six_czech_criteria": len(CATEGORIES) - len(new),
            "new_to_this_project": len(new),
            "czech_criteria_that_now_have_a_named_category_behind_them": supported,
        },
        "what_this_changes_for_the_six": (
            "Three of the six now have a named category in a published scheme rather than a "
            "count of papers that mention the word: diacritics has Greek ACC, agreement has "
            "Greek VERB:SVA and the Czech application of the multilingual framework, and the "
            "untranslated term has Russian Code-Switching. Calque, register and non-word do "
            "not, from these four papers."
        ),
        "what_nobody_here_had_thought_of": [
            c["category"] for c in new if c["bears_on"] is None
        ],
        "the_judgement_is_the_assistants": (
            "What each category means for this catalog is written next to the words it was "
            "read from, and nothing is added to the catalog here."
        ),
        "still_unread": (
            "Thirteen of the seventeen fetched papers and 47 of the 64 in the frame. Seventeen "
            "of the 21 that name a language in the title are unread."
        ),
        "categories": CATEGORIES,
    }
    OUT.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    counts = out["counts"]
    print(f"{counts['categories']} categories from {len(PAPERS)} papers, every quote verified")
    print(f"  bearing on one of the six: {counts['bearing_on_one_of_the_six_czech_criteria']}")
    print(f"  new to this project:       {counts['new_to_this_project']}")
    print(f"  of the six, now supported: {', '.join(supported)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
