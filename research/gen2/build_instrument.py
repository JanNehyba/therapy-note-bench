"""Build the reviewed instrument in a local workspace and freeze it.

The catalog, the operational rules and the investigator's decisions are tracked
files; the study store is not, because it holds full texts. This script is the
step between them, and it exists because the core refuses to freeze an
instrument whose construct origins are not backed by records in the study:

* a literature origin needs an extraction bound to a screened report, and the
  extraction import checks every quoted passage verbatim against the supplied
  full text. That machine check is what stands where the investigator declined
  to verify the evidence by hand (decision D9): it establishes that the passage
  is in the source, and nothing at all about its interpretation.
* an expert or empirical origin needs a recorded input naming where the idea
  came from before the search.

The review of 2026-09-13 ran outside the core and fed it neither, so every
construct carried a placeholder reference and the freeze was refused. Here the
three reports the pilot's literature constructs rest on enter the study with
their route from the review ledger, their inclusion recorded in the delegated
mode of decision D11, and their passages checked against the retrieved files.

Nothing here decides anything. Every decision it replays is in
`decisions.json`: the investigator's own on the constructs, and the two
delegations, D9 for the sources and evidence lines and D10 for the operational
rules. Run it after any change to the catalog or the operational rules:

    uv run python research/gen2/build_instrument.py --workspace local/gen2-instrument
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CATALOG = HERE / "catalog"
REVIEW = HERE / "review-2026-09-13"
FULLTEXT = REPO / "local" / "gen2-review-2026-09-13" / "fulltext"

#: The report each literature-origin construct came from is the source of its
#: first evidence line, which is the one its origin note names. Every report the
#: pilot's evidence cites enters the study, because the core identifies a
#: registry source by the bibliographic record it screened.

#: What a prior or empirical origin has to say for itself. The content is the
#: catalog's origin note; this adds the attribution and the rationale the core
#: asks for, in the words of the project rather than of the literature.
LOCAL_ORIGINS = {
    "K01": (
        "proposal",
        "Gen-1 prototype of this project",
        "Existed as Factual agreement before the search; the review added support, "
        "which never changes an origin.",
    ),
    "K03": (
        "proposal",
        "Gen-1 prototype of this project",
        "A local criterion about time and change of state; PDSQI-9 later supplied a "
        "cautionary argument against a separate temporal column.",
    ),
    "K04": (
        "proposal",
        "Gen-1 prototype of this project",
        "A local refinement about hypotheses and agreements; TN-Eval's Assessment "
        "section later supported it.",
    ),
    "K06": (
        "observation",
        "Repeated finding in this project's code reviews",
        "Models wrote a denial of information nobody asked for and scored full marks "
        "for it; iCARE later supplied a counterexample.",
    ),
    "K07": (
        "proposal",
        "Gen-1 prototype of this project",
        "Existed as Relevance for the recipient; PDSQI later tied relevance to the use case.",
    ),
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalise(text: str) -> str:
    """One line, no hyphenation across a line break.

    A two-column PDF comes out of any extractor with its lines interleaved and
    its words split; the quotes are in the document and not in that text. This
    is the repair the quote check runs against, and the request records the
    digest of exactly what it checked.
    """
    return re.sub(r"\s+", " ", text.replace("-\n", "").replace("­", "")).strip()


def source_text(path: Path) -> str:
    """The retrieved file as text, decided by what is in it rather than by its name.

    Two reports were saved with an `.xml` name by the route that fetched them
    and hold PDF bytes; reading those as text would put a quote check against
    a binary stream, which would fail for the wrong reason.
    """
    raw = path.read_bytes()
    if raw[:4] == b"%PDF":
        done = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, check=False)
        if done.returncode != 0:
            raise SystemExit(f"pdftotext failed on {path.name}: {done.stderr.decode()[:200]}")
        return normalise(done.stdout.decode("utf-8", errors="replace"))
    text = raw.decode("utf-8", errors="replace")
    if text.lstrip()[:200].lstrip().startswith(("<?xml", "<article", "<!DOCTYPE")):
        text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return normalise(text)


def retrieved_file(reports: dict, source_id: str) -> Path:
    report = next(r for r in reports["reports"] if r.get("catalog_source") == source_id)
    names = [e["file"] for e in report["retrieval_events"] if e["outcome"] == "retrieved"]
    if not names:
        raise SystemExit(f"{source_id}: the ledger records no retrieved file")
    return FULLTEXT / names[-1]


def records_csv(catalog: dict, ids: tuple[str, ...]) -> str:
    """The three reports as the bibliographic records the core screens."""
    by = {s["id"]: s for s in catalog["sources"]}
    out = io.StringIO()
    writer = csv.DictWriter(
        out,
        fieldnames=[
            "title",
            "year",
            "doi",
            "abstract",
            "url",
            "language",
            "authors",
            "journal",
            "publication_type",
        ],
        lineterminator="\n",
    )
    writer.writeheader()
    for key in ids:
        source = by[key]
        locator = source["ledger_report_id"]
        writer.writerow(
            {
                "title": source["citation"],
                "year": re.search(r"(19|20)\d{2}", source["citation"]).group(0),
                "doi": locator.removeprefix("doi:") if locator.startswith("doi:") else "",
                "abstract": "",
                "url": "",
                "language": source.get("language", "en"),
                "authors": source["citation"].split(".")[0],
                "journal": source.get("venue", ""),
                "publication_type": source["type"],
            }
        )
    return out.getvalue()


def build(workspace: Path) -> dict:
    from therapy_note_eval import development, research, research_review
    from therapy_note_eval.registry import load_registry
    from therapy_note_eval.schema import digest
    from therapy_note_eval.storage import Store

    protocol = load(HERE / "protocol.json")
    catalog = load(CATALOG / "catalog.json")
    operational = load(CATALOG / "operational.json")
    draft = load(CATALOG / "draft-registry.json")
    decisions = load(HERE / "decisions.json")
    reports = load(REVIEW / "reports.json")

    store = Store(workspace)
    active = research.initialize(
        store, protocol, load(HERE / "queries.json"), load(HERE / "prior-proposals.json")
    )

    # 1. Where the ideas that did not come from the search came from.
    by_candidate = {c["id"]: c for c in catalog["candidates"]}
    references: dict[str, str] = {}
    for key, (kind, attribution, rationale) in LOCAL_ORIGINS.items():
        recorded = development.record_input(
            store,
            active,
            {
                "kind": kind,
                "id": f"origin-{key.lower()}",
                "content": by_candidate[key]["origin_note"],
                "attribution": attribution,
                "rationale": rationale,
            },
        )
        references[key] = recorded["reference"]

    # 2. The reports the pilot's evidence cites, screened by delegation.
    pilot_constructs = sorted(
        {k for m in operational["methods"] for k in m["construct_ids"]}
        | {x["construct_id"] for x in operational["measurements"]}
    )
    pilot_sources = tuple(
        sorted(
            {e["source"] for k in pilot_constructs for e in by_candidate[k]["evidence"]},
            key=lambda s: int(s.removeprefix("S")),
        )
    )
    content = records_csv(catalog, pilot_sources)
    research.import_records(
        store,
        active,
        content,
        "csv",
        {
            "status": "completed",
            "database": "review ledger of 2026-09-13",
            "platform": "research/gen2/review-2026-09-13/reports.json",
            "query": "the reports the pilot's literature constructs rest on",
            "executed_at": "2026-09-13",
            "query_id": "ledger",
            "supplementary_route": "known_before_search and citation routes, recorded report by "
            "report in the review ledger; these are not a database result",
        },
    )
    known = {r["doi"]: r["id"] for r in research.records_for(store, active) if r["doi"]}
    by_source = {s["id"]: s for s in catalog["sources"]}
    record_ids = {
        key: known[by_source[key]["ledger_report_id"].removeprefix("doi:")] for key in pilot_sources
    }
    delegation = next(d for d in protocol["decision_ledger"] if d["id"] == "D11")
    for stage in ("title_abstract", "full_text"):
        research.screen(
            store,
            active,
            [
                {
                    "record_id": record_ids[key],
                    "stage": stage,
                    "decision": "include",
                    "mode": "delegated",
                    "delegation_decision": delegation["id"],
                    "reviewer": decisions["rater_id"],
                    "decided_at": delegation["date"],
                    "reason": f"{key} is read, retrieved and cited by the catalog; included on "
                    "the assistant's reading by the investigator's delegation "
                    f"{delegation['id']} of {delegation['date']}, not screened by a person",
                }
                for key in pilot_sources
            ],
        )

    # 3. Every quoted passage, checked against the retrieved file.
    extractions: dict[str, str] = {}
    digests: dict[str, str] = {}
    for key in pilot_sources:
        text = source_text(retrieved_file(reports, key))
        request = research.extraction_prompt(store, active, record_ids[key], text)
        digests[key] = request["full_text_digest"]
        entries = []
        for candidate in (by_candidate[k] for k in pilot_constructs):
            for line in candidate["evidence"]:
                if line["source"] != key:
                    continue
                entries.append(
                    {
                        "source_location": line["location"],
                        "exact_quote": normalise(line["quote"]),
                        "construct_name": candidate["label"],
                        "definition": candidate["definition"],
                        "supports": line["supports"],
                        "our_adaptation": line["our_adaptation"],
                    }
                )
        out = research_review.import_extraction(store, active, digest(request), entries)
        extractions[key] = out["extraction_id"]

    # 4. The registry the pilot freezes: the draft, with its origins resolved.
    registry = json.loads(json.dumps(draft))
    for construct in registry["constructs"]:
        key = construct["id"]
        if key not in pilot_constructs:
            continue
        if construct["origin"] == "literature":
            source = by_candidate[key]["evidence"][0]["source"]
            construct["origin_reference"] = "extraction:" + extractions[source]
        else:
            construct["origin_reference"] = references[key]
        construct["status"] = "pilot"
        construct["reviewed_by"] = decisions["rater_id"]
        construct["decision_reason"] = (
            "named by the operational rules of this round; the construct is the "
            "investigator's own decision and its selection is delegation D10"
        )
    for item in registry["measurements"]:
        item["status"] = "pilot_reviewed"
    # The core names a registry source by the record it screened, so the catalog's
    # own identifier moves into the locator beside the ledger's.
    for source in registry["sources"]:
        if source["id"] in record_ids:
            source["locator"] = f"{source['locator']} catalog:{source['id']}"
            source["id"] = record_ids[source["id"]]
    for line in registry["evidence"]:
        if line["source_id"] in record_ids:
            line["source_artifact_digest"] = digests[line["source_id"]]
            line["source_id"] = record_ids[line["source_id"]]
    registry["methods_reviewed_by"] = f"{decisions['rater_id']} (delegation D10)"

    # The instrument is what this round measures. The catalog stays the record of
    # every candidate, and carrying the other twenty-one into the snapshot would
    # mean claiming an origin record for constructs nobody operationalised.
    registry["constructs"] = [c for c in registry["constructs"] if c["id"] in pilot_constructs]
    used_evidence = {e for c in registry["constructs"] for e in c["evidence_ids"]}
    used_evidence |= {e for m in registry["method_specs"] for e in m["evidence_ids"]}
    used_evidence |= {e for x in registry["measurements"] for e in x["sources"]}
    registry["evidence"] = [e for e in registry["evidence"] if e["id"] in used_evidence]
    used_sources = {e["source_id"] for e in registry["evidence"]}
    registry["sources"] = [s for s in registry["sources"] if s["id"] in used_sources]
    registry["method_evidence"] = {
        k: [e for e in v if e in used_evidence] for k, v in registry["method_evidence"].items()
    }

    # 5. The decisions, replayed against that registry.
    delegated_kinds = {
        kind: d["decision"] for d in decisions["delegations"] for kind in d["subjects"]
    }
    by_subject = {d["subject"]: d for d in decisions["decisions"]}
    subjects = load_registry(registry).subjects()
    batches: dict[str | None, list] = {None: [], "D9": [], "D10": []}
    for subject in subjects:
        kind = subject.split(":")[0]
        if subject in by_subject:
            recorded = by_subject[subject]
            batches[None].append(
                {"id": subject, "value": recorded["decision"], "reason": recorded["reason"]}
            )
        elif kind in delegated_kinds:
            which = delegated_kinds[kind]
            rule = next(d for d in decisions["delegations"] if d["decision"] == which)
            batches[which].append(
                {
                    "id": subject,
                    "value": "accept",
                    "reason": f"accepted on the assistant's work by the investigator's "
                    f"delegation {which} of {rule['date']}; {rule['means']}",
                }
            )
        else:
            raise SystemExit(f"no decision and no delegation covers {subject}")

    current = registry
    for which, answers in batches.items():
        if not answers:
            continue
        sheet = development.registry_sheet(store, active, current)
        response = {
            "version": "annotations-v3",
            "sheet_id": sheet["id"],
            "rater_id": decisions["rater_id"],
            "role": decisions["role"],
            "mode": "independent",
            "instrument_author": decisions["instrument_author"],
            "answers": answers,
            "submitted_at": (
                "2026-09-21T09:44:00.000Z"
                if which is None
                else next(d for d in decisions["delegations"] if d["decision"] == which)["date"]
            ),
            "missing_information": "",
            "review_seconds": None,
            "factual_edits": None,
            "style_edits": None,
            "information_found_seconds": None,
        }
        if which is not None:
            response["delegated"] = True
            response["delegation_decision"] = which
        else:
            # The investigator opened each construct on 2026-09-21, wrote a line
            # and accepted it. On 2026-10-08 he said he does not stand behind
            # those lines as judgements, and the reasons bear him out. Importing
            # them as a review would make every later claim of human
            # verification rest on them.
            response["seen_no_objection"] = True
        imported = development.import_registry_review(store, active, sheet, response)
        current = store.get("registry_drafts", imported["registry_revision"])

    frozen = development.freeze_instrument(store, active, current)
    snapshot = store.get("instrument_snapshots", frozen["snapshot_id"])
    return {
        "study_id": active["id"],
        "snapshot_id": frozen["snapshot_id"],
        "registry_revision": frozen["registry_revision"],
        "registry": frozen["registry"],
        "pilot_constructs": pilot_constructs,
        "evidence_lines": len(registry["evidence"]),
        "sources": sorted(pilot_sources),
        "measurements": [x["id"] for x in registry["measurements"]],
        "methods": registry["methods"],
        "seen_without_objection": len(batches[None]),
        "delegated_decisions": {k: len(v) for k, v in batches.items() if k},
        "delegated_reviews": len(snapshot["delegated_reviews"]),
        "quotes_checked": sum(
            1
            for key in pilot_sources
            for value in [store.get("research_extractions", extractions[key])]
            for _ in value["entries"]
        ),
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workspace", type=Path, default=REPO / "local" / "gen2-instrument")
    args = parser.parse_args(argv)
    if REPO / "local" not in args.workspace.resolve().parents:
        raise SystemExit("The study store holds full texts and belongs under local/")
    sys.path.insert(0, str(REPO / "packages" / "therapy-note-eval-core" / "src"))
    result = build(args.workspace)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
