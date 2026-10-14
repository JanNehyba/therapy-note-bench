"""Search the ACL Anthology for the language-quality layer (AM-8).

The seven queries were recorded in `research/gen2/queries.json` and the reason
for the layer in `amendments.json` before this file existed, so that "recorded
before use" is checkable from the history.

Separate from `acl_search.py` on purpose. That script rewrites
`search-log-acl.json` for all of its queries, including `executed_utc`, so
re-running it to add a query would restamp the three searches of 2026-09-13 with
today's date and claim they ran now. The corpus parser is imported from it
rather than copied: it carries a fix for BibTeX continuation lines that had
corrupted 1886 identifiers, and a second copy would be a second thing to get
wrong.

Writes `search-log-acl-language.json` beside the first log, and one export per
query. The counts are deliberately not folded into `flow.json`: that diagram is
the identification of the 2026-09-13 round, and a round that could not have
found this literature should not appear to have searched for it.
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
QUERIES_PATH = ROOT.parent / "queries.json"
LAYER = "language"


def _acl_search():
    spec = importlib.util.spec_from_file_location("acl_search", ROOT / "acl_search.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("acl_search", module)
    spec.loader.exec_module(module)
    return module


#: The boolean of each recorded query, as conjunctive regex groups over title
#: and abstract. A record matches when it matches at least one alternative in
#: every group, which is the rule the other ACL searches used.
#:
#: These groups are the record of what was actually matched. The query string in
#: queries.json is the claim; this is the thing that ran, and where they could
#: drift the log keeps both side by side.
GROUPS = {
    "acl-quality-typology": [
        r"\b(translation|generat\w*|summari[sz]\w*|machine translation)\b",
        r"\b(error\w*|quality)\b",
        r"\b(typolog\w*|taxonom\w*|annotation scheme|framework|mqm"
        r"|multidimensional quality metrics)\b",
    ],
    "acl-fluency-adequacy": [
        r"\b(fluenc\w*|adequac\w*|grammaticalit\w*|acceptabilit\w*)\b",
        r"\b(evaluat\w*|annotat\w*|human judg\w*|rating\w*|rater\w*)\b",
    ],
    "acl-post-editing": [
        r"\b(post[- ]?editing|translationese)\b",
        r"\b(error\w*|taxonom\w*|effort|quality|annotat\w*)\b",
    ],
    "acl-small-language-quality": [
        r"\b(low[- ]resource\w*|under[- ]resourced|morphologically rich|slavic|czech)\b",
        r"\b(generat\w*|summari[sz]\w*|translat\w*)\b",
        r"\b(quality|error\w*|evaluat\w*|fluenc\w*)\b",
    ],
    "acl-orthography-and-morphology": [
        r"\b(diacritics?|orthograph\w*|spelling|grammatical error correction"
        r"|morphosyntactic|agreement error\w*)\b",
        r"\b(error\w*|correct\w*|restorat\w*|detect\w*|evaluat\w*)\b",
    ],
    "acl-borrowing-and-register": [
        r"\b(calque\w*|loan ?word\w*|anglicism\w*|borrowing\w*|code[- ]switch\w*"
        r"|untranslated|register|formality|colloquial\w*)\b",
        r"\b(detect\w*|classif\w*|annotat\w*|evaluat\w*|corpus|corpora)\b",
    ],
    "acl-nonword": [
        r"\b(non[- ]?words?|neologism\w*|out[- ]of[- ]vocabulary|malformed|nonsense words?)\b",
        r"\b(detect\w*|error\w*|generat\w*|evaluat\w*)\b",
    ],
}


def main() -> int:
    acl = _acl_search()
    recorded = {
        q["id"]: q
        for q in json.loads(QUERIES_PATH.read_text(encoding="utf-8"))["queries"]
        if q["layer"] == LAYER
    }
    missing = set(recorded) ^ set(GROUPS)
    if missing:
        # A query that ran without being recorded, or a recorded query that did
        # not run, are both the same failure: the log would not say what was
        # asked.
        print(f"recorded queries and implemented groups disagree: {sorted(missing)}")
        return 2

    started = datetime.now(UTC).isoformat()
    corpus_sha = hashlib.sha256(acl.CORPUS_GZ.read_bytes()).hexdigest()
    records = acl.parse_bib(acl.CORPUS)
    print(f"parsed {len(records)} records from the Anthology corpus")

    log = []
    seen: set[str] = set()
    for qid, groups in GROUPS.items():
        patterns = [re.compile(group, re.I) for group in groups]
        hits = [
            record
            for record in records
            if all(
                pattern.search(f"{record.get('title', '')} {record.get('abstract', '')}")
                for pattern in patterns
            )
        ]
        export = acl.EXPORTS / f"{qid}.json"
        export.write_text(json.dumps(hits, indent=1, ensure_ascii=False), encoding="utf-8")
        new = {h["_key"] for h in hits} - seen
        seen |= {h["_key"] for h in hits}
        log.append(
            {
                "query_id": qid,
                "database": "ACL Anthology",
                "platform": "complete Anthology BibTeX corpus, searched offline (AM-5, AM-8)",
                "layer": LAYER,
                "query_as_recorded": recorded[qid]["query"],
                "asks": recorded[qid]["asks"],
                "regex_groups_as_run": groups,
                "match_rule": "a record matches when title+abstract match at least one "
                "alternative in every group",
                "fields_searched": "title and abstract",
                "executed_utc": started,
                "search_date": started[:10],
                "filters_applied": "none",
                "corpus_file": "anthology+abstracts.bib.gz",
                "corpus_sha256": corpus_sha,
                "corpus_records": len(records),
                "total_records": len(hits),
                "records_new_to_this_layer": len(new),
                "records_downloaded": len(hits),
                "download_complete": True,
                "export_file": export.name,
                "export_sha256": hashlib.sha256(export.read_bytes()).hexdigest(),
            }
        )
        print(f"[{qid}] hits={len(hits)} new={len(new)}")

    out = ROOT / "search-log-acl-language.json"
    out.write_text(
        json.dumps(
            {
                "version": "search-log-v1",
                "layer": LAYER,
                "amendment": "AM-8",
                "database": "ACL Anthology",
                "platform": "offline corpus search",
                "corpus_url": "https://aclanthology.org/anthology+abstracts.bib.gz",
                "corpus_sha256": corpus_sha,
                "corpus_records": len(records),
                "corpus_snapshot": "the corpus downloaded on 2026-09-13 for AM-5, unchanged; "
                "work published between that date and this search is therefore not in it",
                "peer_review_of_search": "none",
                "language_restriction": "none applied at corpus level",
                "date_limits": "no lower limit",
                "declared_gaps": (
                    "The Anthology only. Scopus would add proceedings outside it and was not "
                    "searched for this layer; PubMed does not index this literature. Both are "
                    "named rather than left silent."
                ),
                "limitation": (
                    "Records whose abstract is absent from the corpus are searched on title "
                    "alone, which lowers recall for those entries."
                ),
                "records_matched_by_at_least_one_query": len(seen),
                "searches": log,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
        newline="\n",
    )
    print(f"\nwrote {out.name}: {len(seen)} distinct records across {len(GROUPS)} queries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
