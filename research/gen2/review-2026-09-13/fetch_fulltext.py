"""Retrieve a report named in the ledger and record the attempt as an event.

Targets come from reports.json, one `--report <id>` at a time; there is no
roster in this file to re-run by accident. Retrieval is attempted through a
direct URL when the report has one, then Europe PMC open access, then
Unpaywall. Whatever happens is appended as a dated event to the report's
entry in report-map.json, the recorded half of the ledger, and reports.json
and flow.json are rebuilt from it, so the invariant that the tracked ledger
equals the builder's output holds after every run. The log of 2026-09-13 is
never written again.

A report that cannot be retrieved gets a not_retrieved event; that is a
retrieval outcome, not an eligibility exclusion, and it never reverts an
earlier success.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import build_flow  # noqa: E402
import build_reports  # noqa: E402

UA = "therapy-note-bench-gen2-review/1.0 (mailto:jan.nehyba@gmail.com)"
FULLTEXT = ROOT.parents[2] / "local" / "gen2-review-2026-09-13" / "fulltext"


def get(url: str, timeout: int = 90) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def europepmc_fulltext(doi: str | None, pmid: str | None) -> tuple[bytes | None, str]:
    q = f'DOI:"{doi}"' if doi else f"EXT_ID:{pmid}"
    u = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
        {"query": q, "format": "json", "resultType": "core", "pageSize": 1}
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


def attempt(report: dict) -> tuple[bytes | None, str, str, str]:
    """Try the open routes for one report: body, route text, route kind, extension."""
    ids = report["identifiers"]
    tried: list[str] = []
    if ids.get("url"):
        body = get(ids["url"])
        if body:
            return (
                body,
                f"direct url {ids['url']}",
                "direct_url",
                "pdf" if ids["url"].endswith(".pdf") else "html",
            )
        tried.append(f"direct url {ids['url']} (no body)")
    if ids.get("doi") or ids.get("pmid"):
        body, how = europepmc_fulltext(ids.get("doi"), ids.get("pmid"))
        if body:
            return body, how, "open_access_api", "xml"
        tried.append(how)
    if ids.get("doi"):
        body, how = unpaywall_pdf(ids["doi"])
        if body:
            return body, how, "open_access_api", "pdf"
        tried.append(how)
    return (
        None,
        "attempted: " + "; ".join(tried) if tried else "no identifier to retrieve by",
        "open_access_api",
        "",
    )


def _filename(report: dict, ext: str) -> str:
    if report.get("current_file"):
        return report["current_file"]["file"]
    stem = report.get("catalog_source") or re.sub(
        r"[^a-z0-9]+", "-", report["report_id"].lower()
    ).strip("-")
    return f"{stem}.{ext}"


def run(
    review_dir: Path,
    report_ids: list[str],
    *,
    fetch=attempt,
    today: str,
    fulltext_dir: Path,
) -> dict:
    """Attempt every named report; record each attempt in the map; rebuild ledger and flow."""
    inputs = {
        name: json.loads((review_dir / name).read_text(encoding="utf-8"))
        for name in build_reports.INPUTS
    }
    mapping = inputs["report-map.json"]
    current = build_reports.build(*(inputs[name] for name in build_reports.INPUTS), root=review_dir)
    by_id = {r["report_id"]: r for r in current["reports"]}
    entries = {e["report_id"]: e for e in mapping["reports"]}
    for report_id in report_ids:
        if report_id not in by_id:
            raise ValueError(f"unknown report {report_id}; add it to report-map.json first")
        body, route, route_kind, ext = fetch(by_id[report_id])
        event = {
            "date": today,
            "time": None,
            "date_source": "fetch run",
            "route": route,
            "route_kind": route_kind,
            "outcome": "retrieved" if body else "not_retrieved",
            "file": None,
            "bytes": None,
            "sha256": None,
            "checksum_source": None,
            "bytes_source": None,
            "note": None,
            "remaining_options": None,
            "logged_retroactively": None,
            "log_row": None,
            "superseded_by_correction": None,
        }
        if body:
            name = _filename(by_id[report_id], ext)
            fulltext_dir.mkdir(parents=True, exist_ok=True)
            (fulltext_dir / name).write_bytes(body)
            event.update(
                file=name,
                bytes=len(body),
                sha256=hashlib.sha256(body).hexdigest(),
                checksum_source="computed at download",
                bytes_source="measured at download",
            )
        entries[report_id]["events"].append(event)
    (review_dir / "report-map.json").write_bytes(
        (json.dumps(mapping, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    )
    inputs["report-map.json"] = mapping
    ledger = build_reports.build(*(inputs[name] for name in build_reports.INPUTS), root=review_dir)
    (review_dir / "reports.json").write_bytes(
        (json.dumps(ledger, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    )
    flow_inputs = [
        ledger
        if name == "reports.json"
        else json.loads((review_dir / name).read_text(encoding="utf-8"))
        for name in build_flow.INPUTS
    ]
    flow = build_flow.build(*flow_inputs, root=review_dir)
    (review_dir / "flow.json").write_bytes(
        (json.dumps(flow, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    )
    return ledger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--report", action="append", required=True, help="report id from reports.json"
    )
    parser.add_argument("--date", default=dt.date.today().isoformat())
    args = parser.parse_args(argv)
    ledger = run(ROOT, args.report, today=args.date, fulltext_dir=FULLTEXT)
    for report in ledger["reports"]:
        if report["report_id"] in args.report:
            last = report["retrieval_events"][-1]
            print(
                f"{report['report_id']}: {last['outcome']} via {last['route'][:70]} "
                f"-> {report['current_status']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
