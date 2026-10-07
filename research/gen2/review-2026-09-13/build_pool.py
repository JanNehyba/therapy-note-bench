"""Build one deduplicated record pool from every executed search.

Deduplication is by DOI, then PMID, then a normalised title. The source query
or queries of every record are kept, so per-database counts stay reportable
after merging.

Three databases feed it: PubMed (XML, six queries), the ACL Anthology (BibTeX
parsed to JSON, three queries) and Scopus (CSV, three queries added on
2026-10-07 by amendment AM-7).
"""

from __future__ import annotations

import csv
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
SCOPUS_QUERIES = ["scopus-direct", "scopus-note-quality", "scopus-llm-docs"]

#: Scopus writes this in the abstract column when there is no abstract. Kept as
#: an empty abstract rather than as text, so a record without an abstract is not
#: scored by the prioritiser on the words of the placeholder.
NO_ABSTRACT = "[No abstract available]"


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
            title = (
                "".join(art.find(".//ArticleTitle").itertext())
                if art.find(".//ArticleTitle") is not None
                else ""
            )
            abst = " ".join(
                "".join(a.itertext()) for a in art.findall(".//Abstract/AbstractText")
            ).strip()
            journal = art.find(".//Journal/Title")
            year = art.find(".//JournalIssue/PubDate/Year")
            medline_date = art.find(".//JournalIssue/PubDate/MedlineDate")
            # The record's own DOI only: PubmedData/ArticleIdList, else the
            # article's ELocationID. Never `.//ArticleId`, which also walks the
            # cited-reference list and keyed a third of the PubMed pool by a
            # reference's DOI until 2026-09-15.
            doi = None
            for aid in art.findall("./PubmedData/ArticleIdList/ArticleId"):
                if aid.get("IdType") == "doi":
                    doi = norm_doi(aid.text)
                    break
            if doi is None:
                for el in art.findall("./MedlineCitation/Article/ELocationID"):
                    if el.get("EIdType") == "doi":
                        doi = norm_doi(el.text)
                        break
            ptypes = [p.text for p in art.findall(".//PublicationType") if p.text]
            out.append(
                {
                    "pmid": pmid,
                    "doi": doi,
                    "title": title,
                    "abstract": abst,
                    "venue": journal.text if journal is not None else "",
                    "year": (
                        year.text
                        if year is not None
                        else (medline_date.text or "")[:4]
                        if medline_date is not None
                        else ""
                    ),
                    "pubtypes": ptypes,
                    "source_db": "PubMed",
                }
            )
    return out


def parse_scopus_csv(path: Path) -> list[dict]:
    """Read one Scopus CSV export.

    The DOI column is the record's own; Scopus does not put a cited reference
    there. The EID is carried through because it is the only identifier a
    Scopus record without a DOI has, and because it is what the export file is
    auditable by.
    """
    out: list[dict] = []
    with open(path, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            abstract = (row.get("Abstract") or "").strip()
            if abstract.startswith(NO_ABSTRACT):
                abstract = ""
            doctype = (row.get("Document Type") or "").strip()
            out.append(
                {
                    "pmid": None,
                    "doi": norm_doi(row.get("DOI")),
                    "title": (row.get("Title") or "").strip(),
                    "abstract": abstract,
                    "venue": (row.get("Source title") or "").strip(),
                    "year": (row.get("Year") or "").strip(),
                    "pubtypes": [doctype] if doctype else [],
                    "keywords": "; ".join(
                        k
                        for k in (
                            (row.get("Author Keywords") or "").strip(),
                            (row.get("Index Keywords") or "").strip(),
                        )
                        if k
                    ),
                    "eid": (row.get("EID") or "").strip() or None,
                    "url": (row.get("Link") or "").strip() or None,
                    "source_db": "Scopus",
                }
            )
    return out


def _duplicate_titles(records: list[dict]) -> dict:
    """Measure the duplicates the key order cannot catch.

    The key order is DOI, then PMID, then normalised title. Two records of the
    same work therefore stay apart whenever one database gives a DOI and the
    other does not, which is common between PubMed and Scopus. This counts the
    groups rather than merging them, because merging on title needs a guard
    against short and generic titles and would move every stratum drawn from
    the pool.
    """
    groups: dict[str, list[dict]] = {}
    for r in records:
        key = norm_title(r["title"])
        if key:
            groups.setdefault(key, []).append(r)
    repeated = {k: v for k, v in groups.items() if len(v) > 1}
    with_scopus = {
        k: v for k, v in repeated.items() if any("Scopus" in r["source_dbs"] for r in v)
    }
    return {
        "groups": len(repeated),
        "records_involved": sum(len(v) for v in repeated.values()),
        "groups_involving_scopus": len(with_scopus),
        "defect": (
            "these are the same work entered twice, not two works with one title, in every "
            "case inspected. The key order is DOI, then PMID, then normalised title, so a "
            "work that PubMed gives a DOI for and Scopus does not is keyed two different ways "
            "and never merged."
        ),
        "known_consequence": (
            "the unique record count above is an overcount by at most the difference between "
            "records_involved and groups, the duplicates are ranked twice by the prioritiser, "
            "and one work is in the priority stratum twice and was screened in twice, once in "
            "each round."
        ),
        "not_fixed_here": (
            "merging on normalised title needs a guard against short and generic titles, and "
            "it would move the strata, the samples drawn from them and the screening "
            "judgements made over those samples. It is a correction of its own."
        ),
    }


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
            # A merge must not lose the identifier the other database knew the
            # record by: a Scopus EID on a record first seen in PubMed is how
            # that record is found again in the export it came from.
            for field in ("eid", "pmid", "doi", "keywords", "url"):
                if not pool[ident].get(field) and rec.get(field):
                    pool[ident][field] = rec[field]
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

    for qid in SCOPUS_QUERIES:
        recs = parse_scopus_csv(EXPORTS / f"{qid}.csv")
        per_query[qid] = len(recs)
        for r in recs:
            add(r, qid)

    records = list(pool.values())
    POOL.write_bytes((json.dumps(records, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    summary = {
        "records_per_query_before_dedup": per_query,
        "sum_before_dedup": sum(per_query.values()),
        "unique_records_after_dedup": len(records),
        "duplicates_removed": sum(per_query.values()) - len(records),
        "dedup_rule": "DOI, else PMID, else normalised title (ASCII-folded, alphanumeric only)",
        "doi_rule": (
            "a PubMed record's DOI is read from PubmedData/ArticleIdList, else from the "
            "article's ELocationID; never from its reference list"
        ),
        "corrections": [
            {
                "date": "2026-09-15",
                "what": (
                    "Until this date the DOI was the last ArticleId of type doi anywhere in "
                    "the record, which includes the cited-reference list: 2719 PubMed records "
                    "were keyed by a reference's DOI and distinct records merged as duplicates "
                    "(10059 unique, 1303 removed before the correction)."
                ),
                "effect": "rebuilt with the record's own DOI; the counts in this file changed",
            },
            {
                "date": "2026-10-07",
                "what": (
                    "The three Scopus queries of amendment AM-7 were added to the pool. "
                    "Scopus had been a declared gap since 2026-09-13 because its API needs a "
                    "key; the investigator ran the queries in the institutional web interface."
                ),
                "effect": (
                    "the pool grew and the counts in this file changed; every record that "
                    "entered through Scopus alone is unscreened until a dated screening round "
                    "says otherwise"
                ),
            },
        ],
        "with_abstract": sum(1 for r in records if r.get("abstract")),
        "by_source_db": {
            db: sum(1 for r in records if db in r["source_dbs"])
            for db in ("PubMed", "ACL Anthology", "Scopus")
        },
        "in_more_than_one_database": sum(1 for r in records if len(r["source_dbs"]) > 1),
        "reached_only_through": {
            db: sum(1 for r in records if r["source_dbs"] == [db])
            for db in ("PubMed", "ACL Anthology", "Scopus")
        },
        "identifier_key_used": {
            kind: sum(1 for r in records if r["id"].startswith(f"{kind}:"))
            for kind in ("doi", "pmid", "ttl")
        },
        "title_key_risk": (
            "a record with no DOI and no PMID is keyed by its normalised title, which merges "
            "the same work across databases and fails to merge it when a subtitle differs. "
            "The count above is how many records that applies to."
        ),
        "same_normalised_title_on_several_records": _duplicate_titles(records),
        "pool_file": str(POOL),
        "pool_sha256": hashlib.sha256(POOL.read_bytes()).hexdigest(),
    }
    (ROOT / "pool-summary.json").write_bytes((json.dumps(summary, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
