"""Fetch the full texts of the taxonomy papers and record what came back.

The abstract passes could not answer the question they were asked. A taxonomy
lives in a table, an abstract names it, and no pattern over abstracts recovers
the categories. So the papers are read.

Seventeen of the sixty-four, chosen for two reasons that are recorded per paper
rather than left to the reader to infer. The six `meta` papers are about other
people's schemes, so each is a list of lists and worth more than any single
taxonomy. The rest either build a scheme for an inflected or small language,
which is what the second generation exists for, or name the quality dimensions
of generated text, which is this project's object.

The Anthology is open access and serves its PDFs without a key, which is why
this works at all: of the three upstream corpora two publish no licence and the
big publishers answer 403. Nothing clinical is sent anywhere; the requests carry
a paper id and nothing else.

Writes into a gitignored directory and records what was retrieved, with a digest
per file and the length of the extracted text, so a landing page saved as an
article is visible. Three files were once recorded as retrieved that were
landing pages of 438, 580 and 401 words, and length alone did not distinguish an
article from a page about one, so the check here is that the text contains the
paper's own title.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
FRAME = ROOT / "taxonomy-papers.json"
OUT_DIR = REPO / "local" / "gen2-language-fulltext"
LOG = ROOT / "taxonomy-fulltext-log.json"

#: The read set, by the substring of the title that identifies it in the frame,
#: with why it is in the set. Written out rather than computed so that the
#: choice is a recorded judgement and not an emergent property of a filter.
READ_SET = {
    "Mapping Out the NLP Evaluation Landscape": "meta: a standard taxonomy of quality criteria",
    "QCET": "meta: an interactive taxonomy of quality criteria",
    "Consensus Taxonomy for Annotating Errors": "meta: a consensus taxonomy across schemes",
    "Survey of Recent Error Annotation Schemes": "meta: a survey of error annotation schemes",
    "Integrated taxonomy of errors in chat": "meta: an integrated taxonomy across dialogue work",
    "Taxonomy and Study of Critical Errors": "which errors are critical rather than merely wrong",
    "REPA: Russian Error Types": "error types for an inflected Slavic language",
    "TalkTag": "morphosyntactic error annotation for transcribed speech, this project's setting",
    "Multilingual Grammatical Error Annotation": "a language-agnostic frame plus language-specific "
    "parts, which is the shape the second generation needs",
    "ELERRANT": "a language-specific extension of an English scheme, the same shape",
    "Beyond Error Categories": "argues against error categories, so it is the objection",
    "Text Quality Dimensions in Summarization": "quality dimensions of summaries",
    "Perceptual Quality Dimensions": "which quality dimensions a reader actually perceives",
    "ERRANT: Assessing": "the reference automatic error-type classifier",
    "MISMATCH": "fine-grained mismatch error types for generated text",
    "HAllucination Detection": "a hallucination taxonomy",
    "Quality Dimensions and Annotated Datasets": "quality dimensions with datasets behind them",
}

USER_AGENT = "therapy-note-bench research review (contact: jan.nehyba@gmail.com)"
PAUSE_SECONDS = 2.0


def pdf_url(landing: str) -> str:
    return landing.rstrip("/") + ".pdf"


def fetch(url: str, target: Path) -> tuple[bool, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        return False, f"{type(error).__name__}: {error}"
    if not body.startswith(b"%PDF"):
        return False, f"not a PDF ({len(body)} bytes)"
    target.write_bytes(body)
    return True, "ok"


def to_text(pdf: Path) -> tuple[str, str]:
    """Extract text. `-raw` recovers the reading order that two-column layouts break."""
    out = pdf.with_suffix(".txt")
    for mode in (["-raw"], ["-layout"], []):
        result = subprocess.run(  # noqa: S603
            ["pdftotext", *mode, str(pdf), str(out)],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0 and out.is_file() and out.stat().st_size > 2000:
            return out.read_text(encoding="utf-8", errors="replace"), " ".join(mode) or "default"
    return "", "failed"


def main() -> int:
    frame = json.loads(FRAME.read_text(encoding="utf-8"))
    chosen = []
    for needle, why in READ_SET.items():
        matches = [p for p in frame["papers"] if needle.lower() in p["title"].lower()]
        if not matches:
            print(f"not in the frame: {needle}")
            return 2
        chosen.append({**matches[0], "why_in_the_read_set": why})

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for paper in chosen:
        name = paper["key"].replace("/", "_")
        pdf = OUT_DIR / f"{name}.pdf"
        if pdf.is_file():
            ok, note = True, "already on disk"
        else:
            ok, note = fetch(pdf_url(paper["url"]), pdf)
            time.sleep(PAUSE_SECONDS)
        text, mode = to_text(pdf) if ok else ("", "not fetched")
        # A landing page saved as an article is the failure this check exists
        # for: it is short, but so is a short paper, so the test is that the
        # text carries the paper's own title.
        head = " ".join(paper["title"].split()[:4]).lower()
        looks_like_the_paper = head in " ".join(text.split()).lower()
        rows.append(
            {
                "key": paper["key"],
                "year": paper["year"],
                "title": paper["title"],
                "url": paper["url"],
                "why_in_the_read_set": paper["why_in_the_read_set"],
                "meta": paper["meta"],
                "retrieved": ok,
                "note": note,
                "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest() if ok else None,
                "characters_extracted": len(text),
                "pdftotext_mode": mode,
                "text_contains_its_own_title": looks_like_the_paper,
            }
        )
        flag = "ok " if ok and looks_like_the_paper else "CHECK"
        print(f"  {flag} {paper['year']} {len(text):7} chars  {paper['title'][:58]}")

    retrieved = [r for r in rows if r["retrieved"] and r["text_contains_its_own_title"]]
    LOG.write_text(
        json.dumps(
            {
                "version": "taxonomy-fulltext-log-v1",
                "date": datetime.now(UTC).date().isoformat(),
                "frame": FRAME.name,
                "frame_papers": frame["counts"]["papers"],
                "read_set": len(chosen),
                "why_a_read_set_and_not_all_64": (
                    "The six meta papers are each a list of other people's schemes, and the "
                    "rest were chosen for building a scheme for an inflected or small language "
                    "or for naming the quality dimensions of generated text. The other 47 are "
                    "in the frame and unread, which is a stated gap and not a claim that they "
                    "hold nothing."
                ),
                "source": "aclanthology.org, open access, no key",
                "nothing_clinical_was_sent": (
                    "each request carries a paper identifier and the contact address in the "
                    "user agent, and nothing else"
                ),
                "retrieved": len(retrieved),
                "not_retrieved": len(rows) - len(retrieved),
                "verification": (
                    "a file counts as retrieved when it is a PDF whose extracted text contains "
                    "the opening of its own title. Three files in an earlier round were "
                    "recorded as retrieved and were landing pages; length alone did not "
                    "distinguish an article from a page about one."
                ),
                "papers": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\nretrieved {len(retrieved)} of {len(rows)}; wrote {LOG.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
