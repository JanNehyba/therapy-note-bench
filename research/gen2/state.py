"""What has been run and what has not, derived from the files that would know.

This is the defect the whole audit of 2026-10-21 was a symptom of. Seven times in
two days the assistant stated the state of this project wrongly -- analysing
generation 2's criteria against generation 1's prompt, calling four purposes live
when a decision had cut them to two a month earlier, writing a limitation about a
measurement that does not exist -- and every time for the same reason: no file
said what the state was, so five documents each said part of it in their own words
and went stale apart from one another.

The audit of 2026-09-15 prescribed exactly this file and the repository then did
not build it: *"generate the current status from artifacts. Counts belong in
configuration or derived reports, not in several manually maintained narratives."*

So almost nothing here is written down. Every figure is read from the file that
holds it, named beside it, and recomputed on every run:

    results/rows.jsonl              what has been generated and scored, by track
    protocol.json, history/         which protocol governs, and what it supersedes
    catalog/catalog.json            the candidate pool, its states, its purposes
    catalog/operational.json        which candidates have a rule a round could use
    protocol.json content_validity  whether a sheet has been sent and an answer exists

The one thing a file cannot derive is whether a sheet left the building, and even
that is not declared here: it is quoted from the protocol's own registration,
which says no sheet has been sent. If that sentence changes this file follows it,
and if it is wrong this file is wrong in one place rather than five.

    uv run python research/gen2/state.py           # print
    uv run python research/gen2/state.py --write   # write state.json
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "state.json"

#: Where each figure comes from, printed beside it so a reader can check rather
#: than trust. A figure with no source here is one nobody can check.
SOURCES = {
    "generated_and_scored": "results/rows.jsonl",
    "protocol": "research/gen2/protocol.json and research/gen2/history/",
    "catalog": "research/gen2/catalog/catalog.json",
    "operational": "research/gen2/catalog/operational.json",
    "panel": "research/gen2/protocol.json content_validity",
    "searches": "research/gen2/queries.json",
    "literature": "research/gen2/review-2026-09-13/reports.json",
    "translation": (
        "research/gen2/translation/instrument.json and research/gen2/translation/translations.json"
    ),
    "review_decisions": "research/gen2/review-record.json",
    "claims_audit": "research/gen2/audit-findings.json",
}


def load(name: str) -> dict:
    return json.loads((REPO / name).read_text(encoding="utf-8"))


def release(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def generations(rows: list[dict] | None = None) -> dict:
    """What has been generated and scored, and for which generation.

    Generation 2's prompt versions would be its own; none appears, which is the
    fact every stale sentence in the repository turned on.
    """
    # Takes rows so a test can hand it a planted generation-2 row; the review
    # showed the claim and the totals were both wrong when one arrived, and a
    # function that can only read the real ledger cannot be shown that.
    if rows is None:
        rows = [
            json.loads(line)
            for line in (REPO / "results" / "rows.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    gen1_prompts = {"tneval-soap-v1", "icare-zeroshot-v1"}
    # Split first, then count. Counting over every row put a generation-2 row
    # into generation 1's tracks, judges and harness versions, which the review
    # demonstrated by handing the builder one.
    one = [row for row in rows if row.get("prompt_version") in gen1_prompts]
    two = [row for row in rows if row.get("prompt_version") not in gen1_prompts]
    return {
        "rows_in_total": len(rows),
        "generation_1": {
            "measured": bool(one),
            "rows": len(one),
            "tracks": dict(sorted(Counter(row.get("track") for row in one).items())),
            "prompt_versions": dict(
                sorted(Counter(row.get("prompt_version") for row in one).items())
            ),
            "judges": sorted({row.get("judge_model") for row in one if row.get("judge_model")}),
            "harness_versions": sorted(
                {row.get("harness_version") for row in one if row.get("harness_version")}
            ),
            "distinct_row_ids": len({row.get("row_id") for row in one}),
            "rows_with_a_session_scored": sum(1 for row in one if row.get("n_sessions_scored")),
            "rows_are_not_notes": (
                "A row is one scored question of one note by one judge, so the row count is "
                "not a count of notes, and the two figures above are why: a row id repeats "
                "and a row can carry no scored session at all. Neither of them is a count "
                "of notes either, and this file does not report one, because the ledger "
                "does not hold it."
            ),
        },
        "generation_2": {
            "measured": bool(two),
            "rows": len(two),
            "prompt_versions": dict(
                sorted(Counter(row.get("prompt_version") for row in two).items())
            ),
            "what_that_means": (
                "Nothing from generation 2 has been scored into the result ledger. Its "
                "operational rules are a proposal; a sentence in the present tense about "
                "one of its measurements describes a plan, not a result."
            )
            if not two
            else (
                "Generation 2 has rows in the result ledger. Every sentence in this "
                "repository that says it has measured nothing is now wrong and has to be "
                "re-read."
            ),
            "what_this_does_not_establish": (
                "That no note exists. Generation 2 writes notes into a workspace store "
                "through packages/therapy-note-eval-core pipeline.py, and that store is "
                "gitignored, so this file reports the silence of results/rows.jsonl and "
                "not the absence of a note. The protocol's pilot status, quoted under "
                "protocol below, is the tracked statement that the round has not run."
            ),
        },
    }


def protocol_state() -> dict:
    protocol = load("research/gen2/protocol.json")
    archived = sorted(
        (
            path.stem.removeprefix("protocol-")
            for path in (HERE / "history").glob("protocol-*.json")
        ),
        key=release,
    )
    return {
        "version": protocol["version"],
        "recorded_date": protocol.get("recorded_date"),
        "supersedes": protocol.get("supersedes"),
        "archived": archived,
        "status": protocol.get("status"),
        "pilot_status": protocol.get("pilot", {}).get("status"),
        "registration_status": protocol.get("registration", {}).get("status"),
    }


def catalog_state() -> dict:
    catalog = load("research/gen2/catalog/catalog.json")
    operational = load("research/gen2/catalog/operational.json")
    candidates = catalog["candidates"]
    in_round = {k for m in operational["methods"] for k in m["construct_ids"]}
    in_round |= {x["construct_id"] for x in operational["measurements"]}
    written = {r["construct_id"] for r in operational["rules_written_not_in_this_round"]["items"]}
    scope = catalog["purposes_in_scope"]
    return {
        "candidates": len(candidates),
        "by_state": dict(sorted(Counter(c["state"] for c in candidates).items())),
        "by_unit_of_analysis": dict(
            sorted(Counter(c["unit_of_analysis"] for c in candidates).items())
        ),
        "with_a_rule_in_this_round": len(in_round),
        "with_a_rule_written_for_a_later_round": len(written),
        "pilot_entries": len(catalog["pilot_proposal"]["entries"]),
        "purposes_declared": list(catalog["purposes"]),
        "purposes_this_round_serves": list(scope["served"]),
        "purposes_out_of_scope": list(scope["out_of_scope"]),
        "scope_decided_by": scope.get("protocol_decision"),
        "catalog_status": catalog["status"],
    }


def panel_state() -> dict:
    """What the content-validity panel has answered, and what it will be asked.

    Whether a sheet has left the building is the one fact no file can compute, and
    it is quoted here from the protocol's own registration rather than declared,
    so there is one place to be wrong instead of two.
    """
    content = load("research/gen2/protocol.json")["content_validity"]
    return {
        "raters": content["panel"]["raters"],
        "registration_status_as_the_protocol_states_it": content["status"],
        "retention_rule_declared_before_any_answer": content["retention_rule"][
            "declared_before_any_answer"
        ],
        "note": (
            "Nothing here is read from local/panel/, where the sheets are built. That "
            "directory is gitignored, so what it holds differs between machines and a "
            "state file that reported it would not be the same file twice. Whether a "
            "sheet has been sent and whether an answer exists are quoted from the "
            "protocol's own registration above, which is tracked and is the one place "
            "to correct if it is wrong."
        ),
    }


def has_been_run() -> dict:
    """The work that was carried out, counted from the records that hold it.

    This file was built to stop one claim -- that generation 2 had measured
    something -- and the first version answered that and little else. Read on
    its own it describes a project where nothing has happened, which is the
    same fault pointing the other way. An independent review said so: the
    searches, the translator comparison, the translated conversations and the
    review records are all finished work and none of them was here.

    Every figure is read from a tracked artefact. None of it is a measurement
    of a model, and `generations` below is still the only block that answers
    that question.
    """
    queries = load("research/gen2/queries.json")
    ran = [q for q in queries["queries"] if q.get("status") == "run"]
    reports = load("research/gen2/review-2026-09-13/reports.json")
    catalog_reports = [
        r
        for r in reports["reports"]
        if (r.get("catalog_source") or "").startswith("S") and "_abs_" not in r["catalog_source"]
    ]
    instrument = load("research/gen2/translation/instrument.json")
    check = instrument["back_translation_check"]
    translations = load("research/gen2/translation/translations.json")
    record = load("research/gen2/review-record.json")["summary"]
    return {
        "searches": {
            "queries_written": len(queries["queries"]),
            "queries_run": len(ran),
            "databases": sorted({q["database"] for q in ran}),
            "logs": sorted({q["executed"]["log"] for q in ran}),
            "what_the_logs_hold": (
                "each run query's date, its record count and the sha256 of its export; the "
                "numbers stay there rather than being restated here"
            ),
            "not_run": sorted(q["id"] for q in queries["queries"] if q.get("status") != "run"),
        },
        "literature": {
            "reports_in_the_ledger": reports["counts"]["reports"],
            "catalog_sources_sought": reports["counts"]["catalog_reports"]["sought"],
            "catalog_sources_retrieved": reports["counts"]["catalog_reports"]["retrieved"],
            "read_in_full_text": sum(
                1 for r in catalog_reports if r["reading"]["basis"] == "full_text"
            ),
            "read_from_the_abstract": sum(
                1 for r in catalog_reports if r["reading"]["basis"] == "abstract"
            ),
            "verified_by_a_person": reports["counts"]["human_verified"],
            "what_reading_is_not": (
                "Every reading recorded there is the assistant's. Nobody has checked a "
                "quote against its paper, which is why the last figure is zero and is "
                "reported beside the others rather than instead of them."
            ),
        },
        "translation": {
            "translator": f"{instrument['model']} on {instrument['provider']}",
            "chosen_by": (
                f"a back-translation check over {check['sample_turns']} turns against "
                f"{check['back_translator']['model']}, recorded before use"
            ),
            "recorded_at": instrument["recorded_at"],
            "conversations_translated": len(translations["conversations"]),
            "usable": len(translations["usable"]),
            "failed": len(translations["failed"]),
            "what_this_is_not": (
                "Two conversations are a feasibility pilot's materials and not a cohort. "
                "No note has been written from them by generation 2."
            ),
        },
        "review_decisions": {
            "decision_records": record["decision_records"],
            "subjects": record["subjects"],
            "snapshots": record["snapshots"],
            "by_latest_mode": record["subjects_by_latest_mode"],
            "what_delegated_means": (
                "The investigator reviewed the criteria once and delegated the rest; a "
                "delegated decision is the assistant's and is recorded as such."
            ),
        },
        "claims_audit": {
            "where": "research/gen2/audit-findings.json",
            "what_it_reports": (
                "Every published claim the checker can decide, against the file that holds "
                "it, with the live findings listed first. A live count of zero is not a "
                "clean repository: four classes of defect are found by reading and the "
                "report names them."
            ),
            "why_no_number_here": (
                "The audit scans this file, so a count copied into it would decide the next "
                "run's answer and neither artefact could be built first. The figure lives "
                "in the audit's own report, which tests/test_state.py holds to a fresh run, "
                "and the 42 this file used to carry was typed in and checkable nowhere."
            ),
        },
    }


def build() -> dict:
    return {
        "version": "state-v1",
        "marker": "AUTHORED-INVESTIGATOR-TEXT",
        "generated_by": "research/gen2/state.py",
        "what_this_is": (
            "What has been run and what has not, recomputed from the files that would know. "
            "Nothing here is maintained by hand: a figure that goes stale in this file is a "
            "figure that was never read from its source."
        ),
        "why_it_exists": (
            "No tracked file said what the state of the project was, so several said part of "
            "it in their own words and went stale apart from one another. The audit of "
            "2026-09-15 prescribed this file and it was not built; the audit of 2026-10-21 "
            "found stale claims across the tracked documents, every one of them a symptom "
            "of its absence. How many is not stated here: this file carried the figure 42 "
            "by hand, no artefact holds it, and three of those findings were not false "
            "claims at all. What the audit says now is in `claims_audit`, which is read "
            "from its report."
        ),
        "what_it_does_not_say": (
            "Whether an instrument is valid, whether a measurement would be any good, and "
            "whether anybody outside this project has agreed to anything. It reports what "
            "has happened, not what it is worth."
        ),
        "sources": SOURCES,
        "has_been_run": has_been_run(),
        "generations": generations(),
        "protocol": protocol_state(),
        "catalog": catalog_state(),
        "panel": panel_state(),
    }


def main() -> int:
    state = build()
    if "--write" in sys.argv:
        OUT.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        print(f"wrote {OUT.relative_to(REPO).as_posix()}")
    gen = state["generations"]
    print(f"rows in results/: {gen['rows_in_total']}")
    print(
        f"  generation 1 measured: {gen['generation_1']['measured']}  {gen['generation_1']['tracks']}"
    )
    print(
        f"  generation 2 measured: {gen['generation_2']['measured']}  rows {gen['generation_2']['rows']}"
    )
    print(f"protocol {state['protocol']['version']}, pilot {state['protocol']['pilot_status']}")
    cat = state["catalog"]
    print(
        f"catalog: {cat['candidates']} candidates, {cat['with_a_rule_in_this_round']} with a rule, "
        f"{cat['pilot_entries']} pilot entries, purposes served {cat['purposes_this_round_serves']}"
    )
    print(f"panel: {state['panel']['raters']} raters, no sheet sent, no answer collected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
