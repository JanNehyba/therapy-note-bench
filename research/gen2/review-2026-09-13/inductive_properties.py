"""Extract text-quality properties from the corpus bottom-up, with no category list.

Everything this review has done so far is deductive. The queries were written
from properties somebody already had in mind, the ordering signals score a
record for naming one of them -- the `six` signal is worth 5 points for naming
one of the Czech scorer's criteria -- and the per-criterion breakdown counts how
many papers mention what we already measure. All of that can confirm a criterion
and none of it can find one nobody here has thought of.

So this reads the papers' own vocabulary instead.

How the bias is kept out, which is the whole point:

1. **The selection is structural, not topical.** The pattern that finds a paper
   says "this abstract enumerates kinds of error or quality" and names no kind.
   A paper is picked because it has a list, not because the list contains
   something we were looking for.

2. **It runs over the whole corpus**, all 131040 records, not the 6868 the seven
   queries returned and certainly not the 609 above the cut. Both of those were
   selected by patterns written from our categories, so extracting from them
   would rediscover them.

3. **The extraction patterns contain no property name.** The two that do the
   work take whatever word stands before "error" and whatever word follows
   "errors of", so the corpus supplies the vocabulary.

4. **Mapping happens afterwards and elsewhere.** This script does not know the
   36 candidates exist. It writes the ranked vocabulary and stops; comparing it
   with the catalog is a separate step whose judgements are recorded as
   judgements.

What it cannot do. An abstract names a taxonomy more often than it lists it, so
a scheme whose categories live in a table is counted once by its name and not by
its contents. Recall is therefore low and the result is a floor, not a census.
The stoplist is a bias and is declared: it removes function and framing words,
never a candidate property.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "inductive-properties.json"
LAYER_LOG = ROOT / "search-log-acl-language.json"

#: An abstract that enumerates kinds of error or quality. Structural only: every
#: alternative is a word about having a list, never a word about what is in it.
ENUMERATES = re.compile(
    r"\b(error (?:types?|categor\w+|class\w+|taxonom\w+|typolog\w+)"
    r"|taxonom\w+ of errors?|typolog\w+ of errors?"
    r"|(?:quality|error) (?:dimension|aspect)s?"
    r"|annotation (?:scheme|guidelines?|taxonom\w+)"
    r"|(?:we|they) (?:annotate|label|categori[sz]e|classify)[^.]{0,40}\berrors?\b"
    r"|fine[- ]grained errors?|error analysis)\b",
    re.I,
)

#: The extraction. P1 and P2 are the content-free ones: they take whatever the
#: corpus puts next to the word "error". P3 reads an explicit enumeration, and
#: only inside a sentence that is already about errors or quality.
MODIFIER = re.compile(r"\b([a-z][a-z-]{2,24})[- ]+errors?\b", re.I)
OF_ERRORS = re.compile(r"\berrors?\s+(?:of|in|related to)\s+([a-z][a-z-]{2,24})\b", re.I)
ENUMERATION = re.compile(
    r"(?:error|quality|issue)[a-z]*\s*(?:types?|categor\w+|dimensions?|aspects?)?"
    r"[^.]{0,30}?(?::|such as|including|namely|consisting of)\s*([^.;]{5,200})",
    re.I,
)
ITEM = re.compile(r"^[a-z][a-z -]{2,30}$")

#: Function and framing words. This list is a bias and it is declared. Each word
#: here is about the shape of a sentence or the apparatus of a study, not about a
#: property a text can have, so removing it cannot remove a candidate.
STOP = {
    "the",
    "these",
    "those",
    "this",
    "that",
    "such",
    "other",
    "others",
    "another",
    "all",
    "any",
    "some",
    "many",
    "most",
    "more",
    "less",
    "few",
    "several",
    "various",
    "different",
    "common",
    "frequent",
    "rare",
    "typical",
    "specific",
    "general",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "our",
    "their",
    "its",
    "his",
    "her",
    "your",
    "my",
    "human",
    "machine",
    "model",
    "models",
    "system",
    "systems",
    "neural",
    "automatic",
    "manual",
    "annotated",
    "annotation",
    "annotator",
    "annotators",
    "corpus",
    "corpora",
    "dataset",
    "datasets",
    "data",
    "test",
    "training",
    "train",
    "evaluation",
    "evaluate",
    "type",
    "types",
    "category",
    "categories",
    "class",
    "classes",
    "kind",
    "kinds",
    "taxonomy",
    "typology",
    "scheme",
    "schemes",
    "analysis",
    "study",
    "paper",
    "work",
    "result",
    "results",
    "number",
    "rate",
    "rates",
    "score",
    "scores",
    "metric",
    "metrics",
    "baseline",
    "state",
    "art",
    "task",
    "tasks",
    "approach",
    "method",
    "methods",
    "framework",
    "performance",
    "accuracy of",
    "set",
    "sets",
    "example",
    "examples",
    "case",
    "cases",
    "instance",
    "instances",
    "which",
    "where",
    "when",
    "with",
    "without",
    "than",
    "then",
    "also",
    "both",
    "each",
    "every",
    "same",
    "new",
    "novel",
    "first",
    "second",
    "third",
    "final",
    "total",
    "overall",
    "detected",
    "detection",
    "detect",
    "identified",
    "found",
    "made",
    "made by",
    "produced",
    "produced by",
    "generated",
    "generated by",
    "output",
    "outputs",
    "source",
    "target",
    "reference",
    "references",
    "sentence",
    "sentences",
    "word",
    "words",
    "text",
    "texts",
    "token",
    "tokens",
    "language",
    "languages",
    "translation",
    "translations",
    "summary",
    "summaries",
    "note",
    "notes",
    "percent",
    "percentage",
    "half",
    "one",
    "no",
    "non",
    "not",
    "only",
    "even",
    "high",
    "low",
    "large",
    "small",
    "major",
    "minor",
    "severe",
    "critical",
    "true",
    "false",
    "positive",
    "negative",
    "gold",
    "silver",
    "best",
    "worst",
}

#: A term that is a property only in a context this review does not care about:
#: the apparatus of a shared task, a measurement artefact, a kind of mistake a
#: pipeline makes rather than a text has. Kept separate from STOP so that the
#: judgement is visible and reversible.
NOT_A_TEXT_PROPERTY = {
    "annotation",
    "label",
    "labeling",
    "labelling",
    "prediction",
    "classification",
    "segmentation",
    "alignment",
    "parsing",
    "tagging",
    "recognition",
    "transcription",
    "ocr",
    "asr",
    "speech",
    "measurement",
    "estimation",
    "standard",
    "random",
    "systematic",
    "residual",
    "squared",
    "absolute",
    "relative",
    "mean",
    "margin",
}


def _acl():
    spec = importlib.util.spec_from_file_location("acl_search", ROOT / "acl_search.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("acl_search", module)
    spec.loader.exec_module(module)
    return module


def normalise(term: str) -> str | None:
    term = re.sub(r"\s+", " ", term.strip().lower().strip("-"))
    term = re.sub(r"^(?:a|an|the|of|in|and|or|to|for)\s+", "", term)
    term = re.sub(r"\s+(?:a|an|the|of|in|and|or|to|for)$", "", term)
    if term.endswith("s") and not term.endswith(("ss", "us", "is")):
        term = term[:-1]
    if not ITEM.match(term) or term in STOP or len(term) < 3:
        return None
    if all(part in STOP for part in term.split()):
        return None
    return term


def extract(text: str) -> set[str]:
    """Every property name this abstract puts next to the idea of an error."""
    found: set[str] = set()
    for match in MODIFIER.finditer(text):
        term = normalise(match.group(1))
        if term:
            found.add(term)
    for match in OF_ERRORS.finditer(text):
        term = normalise(match.group(1))
        if term:
            found.add(term)
    for match in ENUMERATION.finditer(text):
        for part in re.split(r",| and | or |/|;", match.group(1)):
            term = normalise(part)
            if term and len(term.split()) <= 3:
                found.add(term)
    return found


def main() -> int:
    acl = _acl()
    records = acl.parse_bib(acl.CORPUS)
    corpus_sha = hashlib.sha256(acl.CORPUS_GZ.read_bytes()).hexdigest()

    # Which records the seven deductive queries had returned. Used only to
    # report whether a property was reachable that way, never to filter.
    layer_keys: set[str] = set()
    if LAYER_LOG.is_file():
        log = json.loads(LAYER_LOG.read_text(encoding="utf-8"))
        for search in log["searches"]:
            hits = json.loads((acl.EXPORTS / search["export_file"]).read_text(encoding="utf-8"))
            layer_keys |= {h["_key"] for h in hits}

    documents = 0
    in_layer = 0
    frequency: Counter[str] = Counter()
    inside: Counter[str] = Counter()
    examples: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        text = f"{record.get('title', '')} {record.get('abstract', '')}"
        if not ENUMERATES.search(text):
            continue
        documents += 1
        reachable = record["_key"] in layer_keys
        in_layer += reachable
        for term in extract(text):
            frequency[term] += 1
            if reachable:
                inside[term] += 1
            if len(examples[term]) < 3:
                examples[term].append(
                    {
                        "year": record.get("year"),
                        "title": record.get("title"),
                        "url": record.get("url"),
                        "reachable_by_the_seven_queries": reachable,
                    }
                )

    terms = []
    for term, count in frequency.most_common():
        if count < 3:
            continue
        terms.append(
            {
                "term": term,
                "documents": count,
                "documents_reachable_by_the_seven_queries": inside[term],
                "found_only_outside_those_queries": inside[term] == 0,
                "probably_not_a_property_of_a_text": term in NOT_A_TEXT_PROPERTY,
                "examples": examples[term],
            }
        )

    record = {
        "version": "inductive-properties-v1",
        "date": datetime.now(UTC).date().isoformat(),
        "what_this_is": (
            "Text-quality property names taken from the corpus bottom-up. The papers were "
            "selected because their abstracts enumerate kinds of error, by a pattern that "
            "names no kind; the property names were then taken from whatever those abstracts "
            "put next to the word error. No category list was supplied, and this file does "
            "not know what the catalog contains."
        ),
        "why_it_exists": (
            "Every other step of this review is deductive. The queries were written from "
            "properties somebody already had in mind, the ordering gives 5 points for naming "
            "one of the Czech scorer's six, and the per-criterion breakdown counts mentions of "
            "what we already measure. None of that can find a property nobody here thought of, "
            "which is what the investigator asked for on 2026-10-14."
        ),
        "corpus": {
            "file": "anthology+abstracts.bib.gz",
            "sha256": corpus_sha,
            "records": len(records),
            "snapshot": "downloaded 2026-09-13 for AM-5",
        },
        "selection": {
            "rule": "the abstract or title enumerates kinds of error or quality",
            "pattern": ENUMERATES.pattern,
            "contains_no_property_name": True,
            "documents_selected": documents,
            "of_those_reachable_by_the_seven_deductive_queries": in_layer,
        },
        "extraction": {
            "modifier_before_error": MODIFIER.pattern,
            "after_errors_of": OF_ERRORS.pattern,
            "explicit_enumeration": ENUMERATION.pattern,
            "minimum_documents_to_report": 3,
            "stoplist_size": len(STOP),
            "stoplist_is_a_declared_bias": (
                "every word in it is about the shape of a sentence or the apparatus of a "
                "study, never a property a text can have, so removing it cannot remove a "
                "candidate"
            ),
            "not_a_text_property_is_a_judgement": (
                "a separate, smaller list of terms this review takes to be about a pipeline "
                "or a measurement rather than a text. The terms are kept and flagged rather "
                "than dropped, so the judgement can be reversed by whoever disagrees."
            ),
        },
        "limitations": (
            "An abstract names a taxonomy far more often than it lists one, so a scheme whose "
            "categories live in a table contributes its name and not its contents. Recall is "
            "low and this is a floor, not a census. Nothing here is read: a term is a place to "
            "look, not a property with a definition."
        ),
        "what_this_does_not_do": (
            "It maps nothing onto the catalog. Which of these the 36 candidates already cover "
            "is a judgement, made in a separate step and recorded there, because a mapping "
            "done here would hide the step where a new property could be talked away."
        ),
        "terms": terms,
    }
    OUT.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"corpus {len(records)} records, {documents} enumerate kinds of error")
    print(f"  of those, reachable by the seven queries: {in_layer}")
    print(f"  property names reported (>=3 documents): {len(terms)}")
    outside = [t for t in terms if t["found_only_outside_those_queries"]]
    print(f"  found only outside the seven queries: {len(outside)}")
    print(f"\nwrote {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
