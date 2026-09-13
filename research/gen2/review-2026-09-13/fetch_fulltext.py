"""Retrieve full texts for the records selected for deep extraction.

Retrieval is attempted through Europe PMC open access, then Unpaywall, then the
publisher. A record that cannot be retrieved is logged as not retrieved, which
is not an eligibility exclusion.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "therapy-note-bench-gen2-review/1.0 (mailto:jan.nehyba@gmail.com)"
ROOT = Path(__file__).resolve().parent
FT = Path("C:/Users/Nehyba/therapy-note-bench/local/gen2-review-2026-09-13/fulltext")
EXPORTS = Path("C:/Users/Nehyba/therapy-note-bench/local/gen2-review-2026-09-13/exports")

# (slug, doi or None, pmid or None, direct url or None)
TIER_A = [
    ("tn-eval", None, None, "https://aclanthology.org/2025.acl-industry.14.pdf"),
    ("icare-ihope", "10.1101/2025.06.25.25330252", None, None),
    ("pdsqi-9", "10.1093/jamia/ocaf068", "40323321", None),
    ("pdqi-9-prelim", "10.1197/jamia.M2404", "18436914", None),
    ("pdqi-9-validation", "10.4338/aci-2011-11-ra-0070", "22577483", None),
    # PMID corrected: 28197625 was a guess and belongs to an unrelated oncology
    # paper whose text Unpaywall returned. Found by reading the file, not by
    # trusting the retrieval. See fulltext-retrieval-log.json.
    ("pdqi-9-negative-ed", "10.4338/aci2017050080", "28956888", None),
    ("mentalclouds", "10.2196/57306", "39042893", None),
    ("questeval", None, None, "https://aclanthology.org/2021.emnlp-main.529.pdf"),
    ("qafacteval", None, None, "https://aclanthology.org/2022.naacl-main.187.pdf"),
    ("factscore", None, None, "https://aclanthology.org/2023.emnlp-main.741.pdf"),
    ("cosmin-content-validity", "10.1007/s11136-018-1829-0", None, None),
    ("boateng-scale-development", "10.3389/fpubh.2018.00149", None, None),
]


def get(url: str, timeout: int = 90) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def europepmc_fulltext(doi: str | None, pmid: str | None) -> tuple[bytes | None, str]:
    q = f'DOI:"{doi}"' if doi else f"EXT_ID:{pmid}"
    u = (
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
        + urllib.parse.urlencode({"query": q, "format": "json", "resultType": "core", "pageSize": 1})
    )
    raw = get(u, 60)
    if not raw:
        return None, "europepmc search failed"
    try:
        res = json.loads(raw)["resultList"]["result"]
    except Exception:
        return None, "europepmc parse failed"
    if not res:
        return None, "not indexed in europepmc"
    r = res[0]
    pmcid = r.get("pmcid")
    if pmcid and r.get("isOpenAccess") == "Y":
        body = get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML")
        if body and b"<article" in body[:4000]:
            return body, f"europepmc OA fullTextXML {pmcid}"
    for f in r.get("fullTextUrlList", {}).get("fullTextUrl", []):
        if f.get("availability") in ("Free", "Open access"):
            body = get(f["url"])
            if body and len(body) > 20000:
                return body, f"free full text at {f['site']}"
    return None, f"no open full text (pmcid={pmcid}, OA={r.get('isOpenAccess')})"


def unpaywall_pdf(doi: str) -> tuple[bytes | None, str]:
    raw = get(f"https://api.unpaywall.org/v2/{doi}?email=jan.nehyba@gmail.com", 60)
    if not raw:
        return None, "unpaywall failed"
    try:
        d = json.loads(raw)
    except Exception:
        return None, "unpaywall parse failed"
    for loc in d.get("oa_locations") or []:
        url = loc.get("url_for_pdf") or loc.get("url")
        if not url:
            continue
        body = get(url)
        if body and (body[:5] == b"%PDF-" or len(body) > 40000):
            return body, f"unpaywall {loc.get('host_type')} {url}"
    return None, f"unpaywall: is_oa={d.get('is_oa')}, no usable location"


def main() -> None:
    log = []
    for slug, doi, pmid, url in TIER_A:
        body, how, ext = None, "", "html"
        if url:
            body = get(url)
            how = f"direct url {url}"
            ext = "pdf" if url.endswith(".pdf") else "html"
        if body is None and (doi or pmid):
            body, how = europepmc_fulltext(doi, pmid)
            ext = "xml"
        if body is None and doi:
            body, how2 = unpaywall_pdf(doi)
            how = f"{how}; {how2}"
            ext = "pdf"
        rec = {"slug": slug, "doi": doi, "pmid": pmid, "route": how}
        if body:
            p = FT / f"{slug}.{ext}"
            p.write_bytes(body)
            rec.update(
                retrieved=True,
                file=str(p),
                bytes=len(body),
                sha256=hashlib.sha256(body).hexdigest(),
            )
            print(f"[OK ] {slug:28s} {len(body):>9,} bytes  via {how[:60]}")
        else:
            rec.update(retrieved=False, note="full text not retrieved; this is not an eligibility exclusion")
            print(f"[MISS] {slug:28s} {how[:80]}")
        log.append(rec)
        time.sleep(0.5)

    (ROOT / "fulltext-retrieval-log.json").write_text(
        json.dumps(
            {
                "version": "fulltext-log-v1",
                "principle": "A report not retrieved is recorded as not retrieved, never as content-ineligible.",
                "retrieved": sum(1 for r in log if r["retrieved"]),
                "not_retrieved": sum(1 for r in log if not r["retrieved"]),
                "records": log,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nretrieved {sum(1 for r in log if r['retrieved'])}/{len(log)}")


if __name__ == "__main__":
    main()
