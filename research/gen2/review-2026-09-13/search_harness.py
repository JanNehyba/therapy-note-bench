"""Execute and log the Gen-2 scoping searches.

Every search records the database, platform, exact query as run, execution
timestamp, filters, total count, the range actually downloaded and a SHA-256
checksum of the export. A partially downloaded result set is marked as partial
and never reported as a complete export.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
UA = "therapy-note-bench-gen2-review/1.0 (mailto:jan.nehyba@gmail.com)"
ROOT = Path(__file__).resolve().parent
EXPORTS = Path("C:/Users/Nehyba/therapy-note-bench/local/gen2-review-2026-09-13/exports")


def _get(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def esearch(term: str, retmax: int = 0) -> dict:
    url = f"{EUTILS}/esearch.fcgi?" + urllib.parse.urlencode(
        {"db": "pubmed", "retmode": "json", "retmax": retmax, "term": term}
    )
    return json.loads(_get(url))["esearchresult"]


def efetch(pmids: list[str]) -> list[str]:
    """Fetch full PubMed XML records in batches of 200."""
    out: list[str] = []
    for i in range(0, len(pmids), 200):
        batch = pmids[i : i + 200]
        url = f"{EUTILS}/efetch.fcgi?" + urllib.parse.urlencode(
            {"db": "pubmed", "retmode": "xml", "id": ",".join(batch)}
        )
        out.append(_get(url).decode("utf-8", "replace"))
        time.sleep(0.4)
    return out


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_pubmed(query_id: str, layer: str, term: str, log: list) -> dict:
    started = datetime.now(UTC).isoformat()
    head = esearch(term, retmax=0)
    total = int(head["count"])
    ids_res = esearch(term, retmax=min(total, 9999))
    ids = ids_res.get("idlist", [])
    EXPORTS.mkdir(parents=True, exist_ok=True)
    export = EXPORTS / f"{query_id}.xml"
    with export.open("w", encoding="utf-8") as fh:
        for chunk in efetch(ids):
            fh.write(chunk)
    rec = {
        "query_id": query_id,
        "database": "PubMed",
        "platform": "NCBI E-utilities (esearch/efetch)",
        "layer": layer,
        "query_as_run": term,
        "query_translation": head.get("querytranslation"),
        "phrases_ignored": head.get("warninglist", {}).get("phrasesignored", []),
        "phrases_not_found": head.get("errorlist", {}).get("phrasesnotfound", []),
        "executed_utc": started,
        "search_date": started[:10],
        "filters_applied": "none; no date, language, species or article-type limit",
        "total_records": total,
        "records_downloaded": len(ids),
        "download_complete": len(ids) == total,
        "export_file": str(export),
        "export_sha256": sha256_file(export),
        "export_bytes": export.stat().st_size,
    }
    log.append(rec)
    status = "complete" if rec["download_complete"] else "PARTIAL"
    print(f"[{query_id}] total={total} downloaded={len(ids)} ({status}) sha={rec['export_sha256'][:16]}")
    return rec


PUBMED_QUERIES = [
    (
        "pubmed-direct",
        "direct",
        '(psychotherap*[Title/Abstract] OR counsel*[Title/Abstract] OR "mental health"[Title/Abstract]) '
        'AND ("progress note*"[Title/Abstract] OR "session summar*"[Title/Abstract] '
        'OR "clinical documentation"[Title/Abstract] OR "therapy note*"[Title/Abstract])',
    ),
    (
        "pubmed-transfer",
        "transfer",
        '("clinical note*"[Title/Abstract] OR "medical summar*"[Title/Abstract] '
        'OR "clinical documentation"[Title/Abstract]) AND (quality[Title/Abstract] '
        'OR evaluat*[Title/Abstract] OR validat*[Title/Abstract] OR instrument*[Title/Abstract] '
        'OR rubric*[Title/Abstract])',
    ),
    (
        "pubmed-llm-docquality",
        "transfer",
        '("large language model*"[Title/Abstract] OR "LLM"[Title/Abstract] '
        'OR "generative AI"[Title/Abstract] OR "ambient AI"[Title/Abstract] '
        'OR "AI scribe*"[Title/Abstract] OR "automatic* generat*"[Title/Abstract]) '
        'AND ("clinical note*"[Title/Abstract] OR "progress note*"[Title/Abstract] '
        'OR "discharge summar*"[Title/Abstract] OR "clinical documentation"[Title/Abstract] '
        'OR "clinical summar*"[Title/Abstract] OR "documentation summar*"[Title/Abstract] '
        'OR "session summar*"[Title/Abstract]) '
        'AND (quality[Title/Abstract] OR evaluat*[Title/Abstract] OR validat*[Title/Abstract] '
        'OR accuracy[Title/Abstract] OR hallucinat*[Title/Abstract] OR rubric*[Title/Abstract] '
        'OR instrument*[Title/Abstract] OR error*[Title/Abstract])',
    ),
    (
        "pubmed-requirements",
        "requirements",
        '(psychotherap*[Title/Abstract] OR counsel*[Title/Abstract] '
        'OR "mental health"[Title/Abstract] OR psycholog*[Title/Abstract]) '
        'AND ("record keeping"[Title/Abstract] OR "record-keeping"[Title/Abstract] '
        'OR documentation[Title/Abstract] OR "clinical records"[Title/Abstract] '
        'OR "medical records"[Title/Abstract]) '
        'AND (guideline*[Title/Abstract] OR standard*[Title/Abstract] OR ethic*[Title/Abstract] '
        'OR audit[Title/Abstract] OR requirement*[Title/Abstract] OR legal[Title/Abstract] '
        'OR confidential*[Title/Abstract] OR privacy[Title/Abstract])',
    ),
    (
        "pubmed-client-access-supervision",
        "requirements",
        '("open notes"[Title/Abstract] OR "OpenNotes"[Title/Abstract] '
        'OR "patient access"[Title/Abstract] OR "client access"[Title/Abstract] '
        'OR "shared notes"[Title/Abstract] OR "reading their notes"[Title/Abstract] '
        'OR "clinical supervision"[Title/Abstract]) '
        'AND ("mental health"[Title/Abstract] OR psychotherap*[Title/Abstract] '
        'OR psychiatr*[Title/Abstract] OR counsel*[Title/Abstract]) '
        'AND (note*[Title/Abstract] OR documentation[Title/Abstract] '
        'OR record*[Title/Abstract] OR summar*[Title/Abstract])',
    ),
    (
        "pubmed-note-quality-instruments",
        "transfer",
        '("note quality"[Title/Abstract] OR "documentation quality"[Title/Abstract] '
        'OR "quality of documentation"[Title/Abstract] OR "quality of clinical notes"[Title/Abstract]) '
        'AND (instrument*[Title/Abstract] OR scale[Title/Abstract] OR rubric*[Title/Abstract] '
        'OR tool[Title/Abstract] OR measure*[Title/Abstract] OR valid*[Title/Abstract] '
        'OR reliab*[Title/Abstract] OR psychometric*[Title/Abstract])',
    ),
]


def main() -> None:
    log: list[dict] = []
    for qid, layer, term in PUBMED_QUERIES:
        run_pubmed(qid, layer, term, log)
        time.sleep(0.5)
    out = ROOT / "search-log-pubmed.json"
    payload = {
        "version": "search-log-v1",
        "database": "PubMed/MEDLINE",
        "platform": "NCBI E-utilities",
        "peer_review_of_search": "none; no information specialist reviewed these strategies",
        "search_filters_used": "none",
        "language_restriction": (
            "none applied at the database level; eligibility is limited to English or "
            "Czech full text and that restriction is declared"
        ),
        "date_limits": "no lower limit; upper limit is the execution date recorded per query",
        "deduplication": (
            "within-PubMed duplicates are impossible (PMID is unique); cross-query and "
            "cross-source deduplication is recorded separately"
        ),
        "searches": log,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
