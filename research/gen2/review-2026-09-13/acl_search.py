"""Search the complete ACL Anthology corpus offline.

The Anthology has no query API. Amendment AM-5 replaces the web search box with
a checksummed download of the complete Anthology BibTeX corpus, searched here
with recorded regular expressions. Title and abstract are the searched fields,
matching the Title/Abstract scope used on PubMed.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPORTS = Path("C:/Users/Nehyba/therapy-note-bench/local/gen2-review-2026-09-13/exports")
CORPUS = EXPORTS / "anthology-abstracts.bib"
CORPUS_GZ = EXPORTS / "anthology-abstracts.bib.gz"

FIELD = re.compile(r"^\s*(title|abstract|booktitle|year|url|doi|author)\s*=\s*[\"{](.*)", re.I)
# Any BibTeX field assignment, including the ones this parser does not collect.
# A continuation line that matches this closes the current field instead of being
# appended to it. Without this, `pages = "1--11",` landed inside the preceding
# `doi`, which corrupted 1886 of 10066 recorded identifiers and blocked
# deduplication for those records. Found 2026-09-13 while auditing the pool.
ANY_FIELD = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_-]*\s*=\s*[\"{]")


def _close(value: str) -> str:
    """Strip BibTeX's trailing terminator from a collected field value."""
    return re.sub(r"[}\"]\s*,?\s*$", "", value).strip()


def parse_bib(path: Path) -> list[dict]:
    """Parse the Anthology bib into records. Multi-line braced values are joined."""
    records: list[dict] = []
    cur: dict | None = None
    key = None
    buf: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("@"):
            if cur is not None:
                if key:
                    cur[key] = " ".join(buf).strip()
                records.append(cur)
            cur = {"_key": line.split("{", 1)[-1].rstrip(",").strip()}
            key, buf = None, []
            continue
        if cur is None:
            continue
        m = FIELD.match(line)
        if m:
            if key:
                cur[key] = " ".join(buf).strip()
            key = m.group(1).lower()
            buf = [m.group(2)]
        elif ANY_FIELD.match(line):
            # A field this parser does not collect. Close the current one.
            if key:
                cur[key] = " ".join(buf).strip()
            key, buf = None, []
        elif key:
            buf.append(line.strip())
    if cur is not None:
        if key:
            cur[key] = " ".join(buf).strip()
        records.append(cur)
    for r in records:
        for k in ("title", "abstract", "booktitle", "doi", "url", "year"):
            if k in r:
                r[k] = _close(r[k]).replace("{", "").replace("}", "").strip()
    return records


# Each query is (id, layer, description, required regex groups).
# A record matches when it matches at least one alternative in EVERY group.
QUERIES = [
    (
        "acl-direct",
        "direct",
        'Planned acl-direct: ("therapy" OR "psychotherapy" OR "counseling" OR "counselling") '
        'AND ("note" OR "summary" OR "summarization" OR "summarisation")',
        [
            r"\b(therapy|psychotherap\w*|counsel\w*|therapeutic)\b",
            r"\b(notes?|summar\w*)\b",
        ],
    ),
    (
        "acl-transfer",
        "transfer",
        'Planned acl-transfer: ("summarization" OR "summarisation") AND ("evaluation" OR '
        '"faithfulness" OR "factuality" OR "attribution" OR "question answering" OR "multilingual")',
        [
            r"\b(summari[sz]\w*)\b",
            r"\b(evaluat\w*|faithful\w*|factual\w*|attribution|question answering|multilingual)\b",
        ],
    ),
    (
        "acl-clinical-doc",
        "transfer",
        "Amendment AM-5 companion: clinical or mental-health documentation in NLP venues",
        [
            r"\b(clinical|medical|psychiatr\w*|mental health|patient)\b",
            r"\b(notes?|documentation|discharge summar\w*|summar\w*)\b",
            r"\b(evaluat\w*|quality|faithful\w*|factual\w*|hallucinat\w*|error\w*)\b",
        ],
    ),
]


def main() -> None:
    started = datetime.now(UTC).isoformat()
    corpus_sha = hashlib.sha256(CORPUS_GZ.read_bytes()).hexdigest()
    records = parse_bib(CORPUS)
    print(f"parsed {len(records)} records from the Anthology corpus")

    log = []
    for qid, layer, desc, groups in QUERIES:
        pats = [re.compile(g, re.I) for g in groups]
        hits = []
        for r in records:
            hay = f"{r.get('title', '')} {r.get('abstract', '')}"
            if all(p.search(hay) for p in pats):
                hits.append(r)
        export = EXPORTS / f"{qid}.json"
        export.write_text(json.dumps(hits, indent=1, ensure_ascii=False), encoding="utf-8")
        rec = {
            "query_id": qid,
            "database": "ACL Anthology",
            "platform": "complete Anthology BibTeX corpus, searched offline (amendment AM-5)",
            "layer": layer,
            "description": desc,
            "regex_groups_as_run": groups,
            "match_rule": "a record matches when title+abstract match at least one alternative in every group",
            "fields_searched": "title and abstract",
            "executed_utc": started,
            "search_date": started[:10],
            "filters_applied": "none",
            "corpus_file": "anthology+abstracts.bib.gz",
            "corpus_sha256": corpus_sha,
            "corpus_records": len(records),
            "total_records": len(hits),
            "records_downloaded": len(hits),
            "download_complete": True,
            "export_file": str(export),
            "export_sha256": hashlib.sha256(export.read_bytes()).hexdigest(),
        }
        log.append(rec)
        print(f"[{qid}] hits={len(hits)}")

    out = ROOT / "search-log-acl.json"
    out.write_text(
        json.dumps(
            {
                "version": "search-log-v1",
                "database": "ACL Anthology",
                "platform": "offline corpus search, amendment AM-5",
                "corpus_url": "https://aclanthology.org/anthology+abstracts.bib.gz",
                "corpus_sha256": corpus_sha,
                "corpus_records": len(records),
                "peer_review_of_search": "none",
                "language_restriction": "none applied at corpus level",
                "date_limits": "no lower limit; corpus snapshot downloaded on the recorded date",
                "limitation": (
                    "Records whose abstract is absent from the Anthology corpus are searched on "
                    "title alone, which lowers recall for those entries."
                ),
                "searches": log,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
