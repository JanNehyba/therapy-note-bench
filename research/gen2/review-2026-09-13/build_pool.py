"""Build one deduplicated record pool from every executed search.

Deduplication is by DOI, then PMID, then a normalised title. The source query
or queries of every record are kept, so per-database counts stay reportable
after merging.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPORTS = Path("C:/Users/Nehyba/therapy-note-bench/local/gen2-review-2026-09-13/exports")
POOL = EXPORTS / "pool.json"

PUBMED_QUERIES = [
    "pubmed-direct",
    "pubmed-transfer",
    "pubmed-llm-docquality",
    "pubmed-requirements",
    "pubmed-client-access-supervision",
    "pubmed-note-quality-instruments",
]
ACL_QUERIES = ["acl-direct", "acl-transfer", "acl-clinical-doc"]


def norm_title(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", t.lower())


def norm_doi(raw: str | None) -> str | None:
    """Reduce a DOI field to the bare DOI.

    Some PubMed records carry a resolver URL with a query string in the doi
    ArticleId. One of them embedded a Google Scholar session token, which would
    have been committed as part of a record identifier. Query strings and
    fragments are not part of a DOI, so they are dropped here rather than
    stripped later.
    """
    if not raw:
        return None
    d = raw.strip().lower()
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", d)
    d = re.sub(r"^https?://doi:", "", d)
    d = re.split(r"[?#\s]", d, maxsplit=1)[0]
    return d.rstrip(".,;") or None


def parse_pubmed_xml(path: Path) -> list[dict]:
    """Parse concatenated PubmedArticleSet documents."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    chunks = re.findall(r"<PubmedArticleSet>.*?</PubmedArticleSet>", raw, re.S)
    out: list[dict] = []
    for chunk in chunks:
        try:
            root = ET.fromstring(chunk)
        except ET.ParseError:
            continue
        for art in root.iter("PubmedArticle"):
            pmid_el = art.find(".//PMID")
            pmid = pmid_el.text if pmid_el is not None else None
            title = "".join(art.find(".//ArticleTitle").itertext()) if art.find(".//ArticleTitle") is not None else ""
            abst = " ".join(
                "".join(a.itertext()) for a in art.findall(".//Abstract/AbstractText")
            ).strip()
            journal = art.find(".//Journal/Title")
            year = art.find(".//JournalIssue/PubDate/Year")
            medline_date = art.find(".//JournalIssue/PubDate/MedlineDate")
            doi = None
            for aid in art.findall(".//ArticleId"):
                if aid.get("IdType") == "doi":
                    doi = norm_doi(aid.text)
            ptypes = [p.text for p in art.findall(".//PublicationType") if p.text]
            out.append(
                {
                    "pmid": pmid,
                    "doi": doi,
                    "title": title,
                    "abstract": abst,
                    "venue": journal.text if journal is not None else "",
                    "year": (year.text if year is not None else (medline_date.text or "")[:4] if medline_date is not None else ""),
                    "pubtypes": ptypes,
                    "source_db": "PubMed",
                }
            )
    return out


def main() -> None:
    pool: dict[str, dict] = {}
    per_query: dict[str, int] = {}

    def add(rec: dict, qid: str) -> None:
        ident = (
            f"doi:{rec['doi']}"
            if rec.get("doi")
            else f"pmid:{rec['pmid']}"
            if rec.get("pmid")
            else f"ttl:{norm_title(rec['title'])}"
        )
        if ident in pool:
            pool[ident]["queries"].append(qid)
            if rec["source_db"] not in pool[ident]["source_dbs"]:
                pool[ident]["source_dbs"].append(rec["source_db"])
            if not pool[ident].get("abstract") and rec.get("abstract"):
                pool[ident]["abstract"] = rec["abstract"]
        else:
            r = dict(rec)
            r["id"] = ident
            r["queries"] = [qid]
            r["source_dbs"] = [rec["source_db"]]
            pool[ident] = r

    for qid in PUBMED_QUERIES:
        recs = parse_pubmed_xml(EXPORTS / f"{qid}.xml")
        per_query[qid] = len(recs)
        for r in recs:
            add(r, qid)

    for qid in ACL_QUERIES:
        recs = json.loads((EXPORTS / f"{qid}.json").read_text(encoding="utf-8"))
        per_query[qid] = len(recs)
        for r in recs:
            add(
                {
                    "pmid": None,
                    "doi": norm_doi(r.get("doi")),
                    "title": r.get("title", ""),
                    "abstract": r.get("abstract", ""),
                    "venue": r.get("booktitle", ""),
                    "year": r.get("year", ""),
                    "pubtypes": ["Conference/Workshop paper"],
                    "acl_key": r.get("_key"),
                    "url": r.get("url"),
                    "source_db": "ACL Anthology",
                },
                qid,
            )

    records = list(pool.values())
    POOL.write_text(json.dumps(records, indent=1, ensure_ascii=False), encoding="utf-8")
    summary = {
        "records_per_query_before_dedup": per_query,
        "sum_before_dedup": sum(per_query.values()),
        "unique_records_after_dedup": len(records),
        "duplicates_removed": sum(per_query.values()) - len(records),
        "dedup_rule": "DOI, else PMID, else normalised title (ASCII-folded, alphanumeric only)",
        "with_abstract": sum(1 for r in records if r.get("abstract")),
        "by_source_db": {
            db: sum(1 for r in records if db in r["source_dbs"])
            for db in ("PubMed", "ACL Anthology")
        },
        "pool_file": str(POOL),
        "pool_sha256": hashlib.sha256(POOL.read_bytes()).hexdigest(),
    }
    (ROOT / "pool-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
