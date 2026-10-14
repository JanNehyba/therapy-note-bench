"""Map the field's consensus error taxonomy onto this catalog, and name the gaps.

The inductive passes answered their own question: 1941 papers in the Anthology
enumerate kinds of error, the seven deductive queries could reach 373 of them,
and 64 papers define a taxonomy in their title. Of those 64, this review's
queries could have found 29. The rest were invisible to a search written from
the properties somebody already had in mind, which is the bias the investigator
asked about on 2026-10-14, now a number rather than a worry.

Reading the taxonomies is the next step and it is human-paced. This file does
the first one, the consensus taxonomy of Huidrom and Belz (2023), because it is
not one group's scheme: it is the merge of fifteen schemes, and its top level is
where "virtually complete agreement" was found.

Every category is recorded with the paper's own words, and every quote is
checked against the extracted text before this file is written. A category is
then mapped onto a candidate of the catalog, or marked as covered by nothing.
That mapping is a judgement by the assistant, it is labelled as one, and it is
the step that most needs a reader: a new property is lost by being declared
already covered, and the only defence is that the claim is written down next to
the words it was made from.

The source is gitignored, as every corpus here is. The quotes are in this file
and the digest of the text they came from is beside them, so the check can be
repeated wherever the paper is available.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
SOURCE = REPO / "local" / "gen2-language-fulltext" / "huidrom-belz-2023-towards.txt"
OUT = ROOT / "consensus-taxonomy-mapping.json"

PAPER = {
    "key": "huidrom-belz-2023-towards",
    "title": "Towards a Consensus Taxonomy for Annotating Errors in Automatically Generated Text",
    "authors": "Rudali Huidrom and Anya Belz",
    "venue": "Recent Advances in Natural Language Processing (RANLP), 2023, pages 527-540",
    "url": "https://aclanthology.org/2023.ranlp-1.58/",
    "what_it_is": (
        "A merge of the content/meaning error categories of fifteen annotation schemes, not "
        "one group's taxonomy. Its highest level is where the authors report virtually "
        "complete agreement across those schemes."
    ),
}

#: Each entry: the category as the paper names it, the paper's own words, the
#: candidate of this catalog it is taken to correspond to, and why. `covered_by`
#: of None is the finding; the reason then says what would have to be added.
#:
#: The judgement is the assistant's. It is recorded here rather than applied
#: silently, because the way a review loses a property is by deciding it was
#: already there.
MAPPING = [
    {
        "category": "Omission",
        "quote": "Some content that is present in the input and should be rendered in the "
        "output is not present in the output.",
        "covered_by": ["K05"],
        "reason": "K05 is coverage of essential content weighted by importance, measured "
        "against an information bank built before the note is seen. Same phenomenon.",
    },
    {
        "category": "Addition",
        "quote": "Some content that is not present in the input and should not be rendered in "
        "the output is present in the output.",
        "covered_by": ["K01"],
        "reason": "K01 calls this invented: the source has nothing of the kind.",
    },
    {
        "category": "Duplication",
        "quote": "Some content is repeated verbatim in the output, but there is no "
        "corresponding repetition in the input.",
        "covered_by": ["K31"],
        "reason": "K31 is redundancy. The taxonomy is narrower -- repetition with no "
        "counterpart in the input -- and K31 as written does not require that comparison, "
        "which is a difference in the rule rather than in the property.",
    },
    {
        "category": "Substitution",
        "quote": "Some content in the output, that is intended to convey some content that is "
        "present in the input, does it wrongly.",
        "covered_by": ["K01"],
        "reason": "K01 calls this distorted: the source says something else.",
    },
    {
        "category": "Should Not Be Verbatim",
        "quote": "Some part of the input has been copied verbatim to the output, but should "
        "have been rendered differently.",
        "covered_by": None,
        "reason": "Nothing in the catalog asks whether the note copied where it should have "
        "summarised. K01 uses the word verbatim for TN-Eval's three-way typology and K14 for "
        "telling a quotation from the author's own judgement; neither is this. In a session "
        "note the case is concrete and clinical: the client's words reproduced where a "
        "professional formulation was required, which is also a privacy question because a "
        "verbatim sentence carries more detail than a rendering of it.",
    },
    {
        "category": "Should Be Verbatim",
        "quote": "Some part of the input should have been copied verbatim to the output, but "
        "has been rendered differently.",
        "covered_by": ["K01"],
        "reason": "The core already has a `quotation` error type for a quotation that is not "
        "what was said, and K01 covers the claim being distorted. Partly covered: what is "
        "missing is the rule for when a note is required to quote rather than render.",
    },
    {
        "category": "Lexical Error",
        "quote": "An error that can be fixed by replacing one lexical item in the output with "
        "another.",
        "covered_by": ["K34", "K30"],
        "reason": "K34 is professional terminology and K30 language naturalness. The "
        "taxonomy's category is wider than either and is the bundle K30 already is.",
    },
    {
        "category": "Error In Input",
        "quote": "An error that is caused by an error in the input.",
        "covered_by": None,
        "reason": "Nothing in the catalog and nothing in the eleven blind spots. It matters "
        "here more than in most settings: the Czech transcripts are speech recognition output, "
        "so an error can be inherited rather than made. A note that faithfully reproduces a "
        "mis-transcribed word is wrong about the session and right about its input, and every "
        "criterion that compares note with transcript would score it as correct. The synthetic "
        "controls already have a `transcription_error` variant, so the project has the case "
        "and not the criterion.",
    },
    {
        "category": "Reordering",
        "quote": "An error that can be fixed by reordering parts of the output.",
        "covered_by": ["K12"],
        "reason": "K12 is the arrangement of the text, whether content stands where the "
        "template puts it. Close enough to be the same property, differently cut.",
    },
    {
        "category": "NE Deviation",
        "quote": "Deviation in named entities.",
        "covered_by": None,
        "reason": "K01 would score a wrong name as distorted, but no criterion and no error "
        "type names the facet. K01's unit is an atomic claim with four facets -- actor, time, "
        "polarity, certainty -- and the core's error types are speaker, negation, time, "
        "certainty, intervention, causality, diagnosis, risk, plan, quotation, omission, "
        "privacy, language, instruction, other. A wrong name, a wrong institution or a wrong "
        "referrer lands in `other`, so the one error a reader of a clinical note would check "
        "first cannot be counted.",
    },
    {
        "category": "Pos/Neg Deviation",
        "quote": "Deviation in negation, polarity or positive/negative sentiment.",
        "covered_by": ["K01"],
        "reason": "Covered twice over: polarity is one of K01's four facets and `negation` is "
        "one of the core's error types.",
    },
    {
        "category": "Numerical Deviation",
        "quote": "Deviation in numerical content.",
        "covered_by": None,
        "reason": "The same gap as named entities and the more serious one clinically. A dose, "
        "a frequency, a duration, the number of missed sessions, a date: all of these are "
        "claims K01 would call distorted without recording that what moved was a number. "
        "Neither K01's facets nor the error types name quantity.",
    },
    {
        "category": "Severity (major/minor)",
        "quote": "Severity of the error: Major and Minor",
        "covered_by": ["method qa"],
        "reason": "The operational severity rule has four levels, none/minor/major/critical, "
        "and the core carries them as a type. Covered, and finer than the taxonomy.",
    },
    {
        "category": "Content Word(s) vs Function Word(s)",
        "quote": "Degree to which words in the error contribute to the content/meaning of the "
        "output",
        "covered_by": None,
        "reason": "Not covered and probably not wanted. It is a granularity dimension for "
        "annotating a span, not a property a reader of a note would ask about. Recorded so "
        "that the decision not to take it is visible.",
    },
    {
        "category": "Single Word vs Multiple Words",
        "quote": "Number of words involved in a given error",
        "covered_by": None,
        "reason": "As above: a dimension of the annotation, not of the note. Recorded and not "
        "proposed.",
    },
]

#: The paper's own framing of the division this project does not make explicitly.
STRUCTURAL = [
    {
        "observation": "content versus form",
        "quote": "Errors of content (as opposed to errors of form such as grammatical or "
        "lexical-choice errors)",
        "what_it_means_here": (
            "The taxonomy divides errors of content from errors of form and then treats only "
            "content. This catalog mixes them: K01 and K05 are content, K30 and K34 are form, "
            "and nothing says so. The six Czech criteria are all errors of form, which is why "
            "no amount of searching the content literature was going to support them."
        ),
    },
    {
        "observation": "orthogonal dimensions rather than more categories",
        "quote": "any of the primary error categories can additionally be annotated with "
        "them, i.e. they necessarily result in duplication in the taxonomy if included there",
        "what_it_means_here": (
            "Their test for a dimension is whether putting it in the hierarchy would duplicate "
            "it. By that test some of this catalog's 36 are dimensions and not criteria: "
            "severity, and the disclosure level of a sensitive detail, apply to many criteria "
            "at once. Worth checking before the panel rates 36 items as if they were one kind "
            "of thing."
        ),
    },
]


def flat(text: str) -> str:
    """Whitespace-insensitive and de-hyphenated, so a quote can be found in a PDF dump."""
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    return re.sub(r"\s+", " ", text)


def main() -> int:
    if not SOURCE.is_file():
        print(f"the source text is not on this machine: {SOURCE}")
        return 2
    raw = SOURCE.read_bytes()
    body = flat(raw.decode("utf-8", errors="replace"))

    unverifiable = []
    for entry in MAPPING + STRUCTURAL:
        if flat(entry["quote"]) not in body:
            unverifiable.append(entry.get("category") or entry["observation"])
    if unverifiable:
        # The rule the review has kept since the first round: a quote that
        # cannot be found in the file it is attributed to is not written down.
        print("these quotes are not in the source and were not written:")
        for name in unverifiable:
            print(f"  {name}")
        return 2

    covered = [m for m in MAPPING if m["covered_by"]]
    gaps = [m for m in MAPPING if not m["covered_by"]]
    proposed = [
        g
        for g in gaps
        if g["category"]
        not in ("Content Word(s) vs Function Word(s)", "Single Word vs Multiple Words")
    ]
    out = {
        "version": "consensus-taxonomy-mapping-v1",
        "date": datetime.now(UTC).date().isoformat(),
        "paper": PAPER,
        "source_text_sha256": hashlib.sha256(raw).hexdigest(),
        "every_quote_was_found_in_that_text": True,
        "what_this_is": (
            "The categories of the field's consensus error taxonomy, each with the paper's own "
            "words, mapped onto the candidates of this catalog. The mapping is the assistant's "
            "judgement and is labelled as one."
        ),
        "why_the_mapping_is_separate_from_the_extraction": (
            "A review loses a property by deciding it was already covered. The extraction "
            "scripts know nothing of the catalog, and the claim that a category is covered is "
            "written here next to the words it was made from, where it can be disagreed with."
        ),
        "counts": {
            "categories": len(MAPPING),
            "mapped_to_a_candidate": len(covered),
            "covered_by_nothing": len(gaps),
            "of_those_proposed_as_candidates": len(proposed),
            "of_those_recorded_and_not_proposed": len(gaps) - len(proposed),
        },
        "gaps_proposed_as_candidates": [g["category"] for g in proposed],
        "nothing_is_in_the_catalog_yet": (
            "No candidate is created here. Whether these enter the pool is the investigator's "
            "decision, and the pool may only grow until the panel's first table exists (D14)."
        ),
        "mapping": MAPPING,
        "structural_observations": STRUCTURAL,
        "what_is_still_unread": (
            "Sixteen of the seventeen fetched papers, and 47 of the 64 in the frame. This is "
            "the first taxonomy read, chosen because it merges fifteen schemes rather than "
            "proposing one."
        ),
    }
    OUT.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    counts = out["counts"]
    print(f"{counts['categories']} categories, every quote verified in the source")
    print(f"  mapped onto a candidate: {counts['mapped_to_a_candidate']}")
    print(f"  covered by nothing:      {counts['covered_by_nothing']}")
    print(f"  proposed as candidates:  {counts['of_those_proposed_as_candidates']}")
    for gap in proposed:
        print(f"    - {gap['category']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
