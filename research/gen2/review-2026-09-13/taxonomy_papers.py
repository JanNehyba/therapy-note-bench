"""The papers that define a taxonomy of text-quality errors, selected by title.

The abstract-level inductive pass found its own ceiling and reported it: an
abstract says it has a taxonomy far more often than it prints one, so mining
abstracts for property names returns the handful of terms that happen to appear
in prose and misses the scheme that lives in a table. Two attempts to widen the
abstract patterns made it worse rather than better, because "error taxonomy" is
ubiquitous in current NLP and pulled in agent, SQL and retrieval papers whose
errors are not properties of a text.

The title is the precise field. A paper that defines a taxonomy of errors almost
always says so in its title, and a title is short enough that a structural
pattern over it does not drown.

Still no category list. The pattern asks whether the title says "taxonomy",
"typology", "error types" or "quality dimensions" and names no type and no
dimension, so a paper is selected for having a scheme and not for the scheme
containing something this project already measures.

`meta` marks the papers whose subject is other people's schemes -- a survey, a
consensus taxonomy, a standard taxonomy of quality criteria. Those are the ones
worth reading first for the question this was asked for, because each one
aggregates taxonomies this review would otherwise have to find separately.

Writes `taxonomy-papers.json`: the frame for the full-text step, with the count
of how many of them the seven deductive queries could have reached.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "taxonomy-papers.json"
LAYER_LOG = ROOT / "search-log-acl-language.json"

#: The title says the paper carries a scheme. Names no category.
TITLE_SCHEME = re.compile(
    r"\b(taxonom\w+|typolog\w+|error types?|error categor\w+|error scheme"
    r"|quality dimensions?|annotation of errors?|error annotation)\b",
    re.I,
)
#: The scheme is about something being wrong or about quality, rather than about
#: linguistic structure. Without this the selection fills with Universal
#: Dependencies, FrameNet and multiword-expression schemes, which are taxonomies
#: of language and not of error.
TITLE_QUALITY = re.compile(
    r"\b(error\w*|quality|failure\w*|hallucinat\w*|mistake\w*|fidelity|faithful\w*"
    r"|adequacy|fluency)\b",
    re.I,
)
#: A paper whose subject is other people's schemes. Read these first: each one
#: is a list of lists.
META = re.compile(
    r"\b(survey|consensus|standard taxonomy|mapping out|landscape|comparing approaches"
    r"|integrated taxonomy|quality criteria)\b",
    re.I,
)
#: A language other than English named in the title. The second generation exists
#: for a small language, so a scheme built for an inflected or low-resource one is
#: worth more here than its citation count says.
NAMED_LANGUAGE = re.compile(
    r"\b(arabic|chinese|japanese|korean|greek|turkish|russian|portuguese|vietnamese"
    r"|bangla|bengali|czech|slovak|polish|german|french|spanish|italian|icelandic"
    r"|hindi|indic|multilingual|cross-?lingual|non-?native|learner)\b",
    re.I,
)


def _acl():
    spec = importlib.util.spec_from_file_location("acl_search", ROOT / "acl_search.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("acl_search", module)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    acl = _acl()
    records = acl.parse_bib(acl.CORPUS)
    corpus_sha = hashlib.sha256(acl.CORPUS_GZ.read_bytes()).hexdigest()

    layer_keys: set[str] = set()
    if LAYER_LOG.is_file():
        log = json.loads(LAYER_LOG.read_text(encoding="utf-8"))
        for search in log["searches"]:
            hits = json.loads((acl.EXPORTS / search["export_file"]).read_text(encoding="utf-8"))
            layer_keys |= {h["_key"] for h in hits}

    papers = []
    for record in records:
        title = record.get("title", "") or ""
        if not (TITLE_SCHEME.search(title) and TITLE_QUALITY.search(title)):
            continue
        papers.append(
            {
                "key": record["_key"],
                "year": record.get("year"),
                "title": title,
                "venue": record.get("booktitle"),
                "url": record.get("url"),
                "doi": record.get("doi"),
                "meta": bool(META.search(title)),
                "names_a_language": bool(NAMED_LANGUAGE.search(title)),
                "reachable_by_the_seven_queries": record["_key"] in layer_keys,
                "abstract_present": bool(record.get("abstract")),
            }
        )
    papers.sort(key=lambda p: (not p["meta"], -(int(p["year"] or 0))))

    reachable = sum(p["reachable_by_the_seven_queries"] for p in papers)
    out = {
        "version": "taxonomy-papers-v1",
        "date": datetime.now(UTC).date().isoformat(),
        "what_this_is": (
            "The papers in the ACL Anthology whose title says they define a taxonomy or "
            "typology of errors, error types or quality dimensions. The frame for reading "
            "full texts, selected structurally: the pattern names no category, so a paper is "
            "here for having a scheme and not for the scheme matching ours."
        ),
        "why_the_title_and_not_the_abstract": (
            "The abstract pass reported its own ceiling. An abstract says it has a taxonomy "
            "far more often than it prints one, and widening its patterns filled the result "
            "with agent, SQL and retrieval papers whose errors are not properties of a text. "
            "A title is short, and a paper that defines a scheme says so there."
        ),
        "corpus": {
            "file": "anthology+abstracts.bib.gz",
            "sha256": corpus_sha,
            "records": len(records),
            "snapshot": "downloaded 2026-09-13 for AM-5",
        },
        "selection": {
            "title_says_it_has_a_scheme": TITLE_SCHEME.pattern,
            "and_the_scheme_is_about_error_or_quality": TITLE_QUALITY.pattern,
            "why_the_second_pattern": (
                "without it the selection fills with Universal Dependencies, FrameNet and "
                "multiword-expression schemes, which are taxonomies of language and not of "
                "error"
            ),
            "meta_marks_a_paper_about_other_schemes": META.pattern,
            "named_language_is_a_reading_priority_not_a_filter": NAMED_LANGUAGE.pattern,
        },
        "counts": {
            "papers": len(papers),
            "meta": sum(p["meta"] for p in papers),
            "naming_a_language": sum(p["names_a_language"] for p in papers),
            "reachable_by_the_seven_queries": reachable,
            "unreachable_by_the_seven_queries": len(papers) - reachable,
        },
        "what_the_reachability_count_measures": (
            "How much of this frame the deductive half of the layer could have found. It is a "
            "number for the bias in this review's own pipeline, not a property of the "
            "literature."
        ),
        "not_a_screening_decision": (
            "Nothing is included or excluded. These are papers to read, and a taxonomy is "
            "support for a criterion only once someone has read it and quoted it."
        ),
        "papers": papers,
    }
    OUT.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    counts = out["counts"]
    print(f"{counts['papers']} taxonomy papers; {counts['meta']} are about other schemes")
    print(f"  naming a language other than English: {counts['naming_a_language']}")
    print(f"  the seven queries could reach: {counts['reachable_by_the_seven_queries']}")
    print(f"\nwrote {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
