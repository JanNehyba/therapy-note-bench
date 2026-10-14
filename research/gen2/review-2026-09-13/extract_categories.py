"""Take the category names out of the taxonomy papers, with no seed list.

This is the step the abstract passes could not do. A taxonomy lives in a table
or a numbered list in the body, an abstract names it, and mining abstracts
returned the handful of property words that happen to appear in prose. The
seventeen papers are on disk, so the categories are read out of them.

Still inductive, and the same three rules keep it so:

1. **No seed.** Nothing here lists a category, a criterion or one of the Czech
   scorer's six. The patterns look for the shape of a category name in the
   neighbourhood of a word about taxonomies, and take whatever is there.
2. **Document frequency across independent papers is the signal.** A name one
   paper invented is a lead; a name eight unrelated papers use is the field
   agreeing on a property, which is the thing worth comparing a catalog
   against.
3. **No mapping.** This writes the names and stops. Which of them the 36
   candidates already cover is a judgement, and it is made and recorded
   separately so that a new property cannot be talked away inside a script.

The extraction has to survive pdftotext. A two-column PDF hyphenates across
line breaks, so "Con-\\ntent Omission" has to be rejoined before anything else,
or the commonest category in the corpus is invisible.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
TEXTS = REPO / "local" / "gen2-language-fulltext"
LOG = ROOT / "taxonomy-fulltext-log.json"
OUT = ROOT / "category-names.json"

#: The shape a taxonomy entry is printed in: a label, a colon or dash, then a
#: definition beginning in lower case. A table of error types and a numbered
#: list of them are both set this way, and an ordinary sentence is not.
#:
#: The first version of this script looked for Title Case near a word about
#: taxonomies and returned `this`, `there`, `while`, `canada` and `vancouver`.
#: Capitalisation cannot tell a category name from the first word of a sentence,
#: so shape replaced it.
DEFINED = re.compile(
    r"(?:(?<=[;\u2022\u2013\u2014])|(?<=\d\.)|(?<=\d\))|^)\s*"
    r"([A-Za-z][A-Za-z/&' -]{3,44}?)\s*[:\u2013\u2014]\s+"
    r"(?=[a-z])([^.;:]{18,220})",
    re.M,
)

#: An item in an explicit enumeration, for the schemes that print their leaves
#: without a definition beside them.
ENUMERATED = re.compile(
    r"(?:(?:\(|\[)?\d{1,2}(?:\)|\.|\])|\u2022|\u2013|\u2014)\s+"
    r"([A-Za-z][A-Za-z -]{3,38}?)(?=[,;.:]|\s+\()"
)

#: Where the body of a paper is. The header carries affiliations, which gave
#: `dublin` and `ireland`, and the reference list gave `zhang`, `bryant` and
#: `long papers`.
HEADER_END = re.compile(r"\bAbstract\b", re.I)
REFERENCES = re.compile(r"^\s*(?:References|Bibliography)\s*$", re.I | re.M)

#: Words that look like a category and are the apparatus of a paper. Declared as
#: a bias; each one is about a document or a study, never about a property a
#: text can have.
STOP = {
    "table", "figure", "section", "appendix", "abstract", "introduction", "conclusion",
    "related work", "future work", "discussion", "results", "method", "methods",
    "methodology", "experiment", "experiments", "dataset", "datasets", "data",
    "annotation", "annotator", "annotators", "guidelines", "corpus", "corpora",
    "university", "research", "centre", "center", "association", "computational",
    "linguistics", "proceedings", "workshop", "conference", "volume", "pages",
    "appendix a", "appendix b", "the following", "as follows", "for example",
    "in this paper", "this paper", "our work", "this work", "the paper",
    "natural language", "natural language processing", "language model",
    "language models", "large language", "machine translation", "error analysis",
    "error annotation", "error type", "error types", "error taxonomy",
    "quality criteria", "quality criterion", "taxonomy", "typology", "scheme",
    "english", "german", "french", "spanish", "russian", "chinese", "japanese",
    "korean", "greek", "turkish", "arabic", "czech", "icelandic", "portuguese",
    "human", "machine", "system", "systems", "model", "models", "output",
    "outputs", "input", "text", "texts", "sentence", "sentences", "word", "words",
    "token", "tokens", "reference", "references", "source", "target", "gold",
    "test", "train", "training", "validation", "evaluation", "evaluations",
    "metric", "metrics", "score", "scores", "rating", "ratings", "agreement",
    "kappa", "accuracy", "precision", "recall", "f-score", "baseline",
    "state of", "art", "related", "prior", "previous", "current", "recent",
    "first", "second", "third", "fourth", "one", "two", "three", "four", "five",
    "all", "both", "each", "every", "other", "others", "such", "these", "those",
    "however", "therefore", "moreover", "furthermore", "finally", "thus",
    "we define", "we annotate", "we propose", "we use", "we distinguish",
}


def clean(raw: str) -> str:
    """Rejoin what a two-column PDF broke, then normalise the whitespace.

    Without the first substitution "Con-\\ntent Omission" never matches, and
    content omission is the category the field agrees on most.
    """
    text = raw.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = re.sub(r"\s*\n\s*", " ", text)
    return re.sub(r"\s{2,}", " ", text)


def normalise(name: str) -> str | None:
    term = re.sub(r"\s+", " ", name.strip().lower()).strip(" -/")
    term = re.sub(r"^(?:the|a|an|of|in|and|or|to)\s+", "", term)
    term = re.sub(r"\s+(?:the|a|an|of|in|and|or|to)$", "", term)
    if term in STOP or len(term) < 4 or len(term.split()) > 4:
        return None
    if any(part in STOP for part in (term,)) or term.isdigit():
        return None
    return term


def body_of(raw: str) -> str:
    """The paper without its header or its reference list, cut before cleaning.

    The cut has to happen while the line breaks are still there. An earlier
    version cleaned first, which collapsed every newline, so a pattern for a
    "References" heading on its own line could not match and the bibliography
    stayed in. The result was led by `springer`, `ieee` and the names of
    fourteen authors, because a bibliography entry has the same shape as a label
    with a definition after it.
    """
    start = HEADER_END.search(raw)
    body = raw[start.end() :] if start else raw
    end = REFERENCES.search(body)
    return body[: end.start()] if end else body


def names_in(text: str) -> dict[str, str]:
    """Each label that is printed with a definition beside it, and the definition.

    The definition is kept because a name without one cannot support anything:
    `register` means one thing in linguistics and another in a machine, and only
    the sentence next to it says which.
    """
    found: dict[str, str] = {}
    body = clean(body_of(text))
    for match in DEFINED.finditer(body):
        term = normalise(match.group(1))
        definition = re.sub(r"\s+", " ", match.group(2)).strip()
        if term and len(definition.split()) >= 4 and not definition.startswith("("):
            found.setdefault(term, definition)
    for match in ENUMERATED.finditer(body):
        term = normalise(match.group(1))
        if term:
            found.setdefault(term, "")
    return found


def main() -> int:
    log = json.loads(LOG.read_text(encoding="utf-8"))
    papers = [p for p in log["papers"] if p["retrieved"]]
    frequency: Counter[str] = Counter()
    sources: dict[str, list[str]] = defaultdict(list)
    definitions: dict[str, dict] = {}
    per_paper = []
    for paper in papers:
        path = TEXTS / f"{paper['key'].replace('/', '_')}.txt"
        if not path.is_file():
            print(f"missing text: {path.name}")
            continue
        found = names_in(path.read_text(encoding="utf-8", errors="replace"))
        for term, definition in found.items():
            frequency[term] += 1
            sources[term].append(paper["key"])
            if definition and term not in definitions:
                definitions[term] = {"definition": definition, "from": paper["key"]}
        per_paper.append(
            {"key": paper["key"], "year": paper["year"], "names_found": len(found)}
        )

    terms = [
        {
            "name": term,
            "papers": count,
            "in": sorted(sources[term]),
            **(definitions.get(term) or {}),
        }
        for term, count in frequency.most_common()
        if count >= 2
    ]

    out = {
        "version": "category-names-v1",
        "date": datetime.now(UTC).date().isoformat(),
        "what_this_is": (
            "Category names taken out of the full texts of the taxonomy papers, with no seed "
            "list. The patterns describe what a category name looks like and where in a paper "
            "one stands; they name no category, no criterion and none of the Czech scorer's "
            "six."
        ),
        "why_full_texts": (
            "A taxonomy lives in a table or a numbered list in the body. Two passes over "
            "abstracts returned the few property words that happen to appear in prose, and "
            "said so: that was a measurement of where taxonomies are printed, not of what is "
            "in them."
        ),
        "the_signal_is_document_frequency": (
            "A name one paper invented is a lead. A name several unrelated papers use is the "
            "field agreeing that a text has that property, which is what a catalog can be "
            "held against. Only names appearing in two or more papers are reported."
        ),
        "no_mapping_here": (
            "Which of these the 36 candidates already cover is a judgement, made and recorded "
            "in a separate step. A mapping done inside this script would let a new property be "
            "talked away where nobody could see it."
        ),
        "extraction": {
            "a_label_printed_with_a_definition": DEFINED.pattern,
            "an_enumerated_item": ENUMERATED.pattern,
            "why_not_capitalisation": (
                "the first version looked for Title Case near a word about taxonomies and "
                "returned `this`, `there`, `while`, `canada` and `vancouver`. Capitalisation "
                "cannot tell a category name from the first word of a sentence, so the shape "
                "of a printed taxonomy entry replaced it: a label, a colon, a definition."
            ),
            "header_and_references_are_cut": (
                "affiliations gave `dublin` and `ireland`, the bibliography gave `zhang` and "
                "`long papers`"
            ),
            "dehyphenation": (
                "a two-column PDF breaks words across lines, so 'Con-\\ntent Omission' is "
                "rejoined before anything else; without it the field's most agreed category is "
                "invisible"
            ),
            "stoplist_size": len(STOP),
            "stoplist_is_a_declared_bias": (
                "every entry is about a document or a study, never a property a text can have"
            ),
            "minimum_papers_to_report": 2,
        },
        "limitations": (
            "A table pdftotext scrambles contributes nothing, so this under-reports. A name is "
            "not a definition: what each category means still has to be read, and the quote "
            "recorded, before it can support a criterion."
        ),
        "outcome": (
            "This did not work, and the reason is worth keeping. It returns almost nothing, "
            "because a taxonomy is printed as a table or a figure and pdftotext turns both "
            "into a bare sequence of words with no label-colon-definition shape left in them. "
            "The result is a measurement of how taxonomies are typeset, not of what is in "
            "them. Three successive versions of the patterns made it worse rather than better: "
            "capitalisation could not tell a category name from the first word of a sentence, "
            "and loosening the anchors let the bibliography back in. The categories were read "
            "out of the papers by hand instead, with every quote machine-checked against the "
            "text file it is attributed to, which is what map_consensus_taxonomy.py records. "
            "Kept rather than deleted because the next person to think of mining these PDFs "
            "should see that it was tried and what it cost."
        ),
        "papers_read": per_paper,
        "names": terms,
    }
    OUT.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"{len(papers)} papers, {len(terms)} names in two or more of them")
    print(f"digest {hashlib.sha256(OUT.read_bytes()).hexdigest()[:12]}")
    for term in terms[:40]:
        print(f"  {term['papers']:2}  {term['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
