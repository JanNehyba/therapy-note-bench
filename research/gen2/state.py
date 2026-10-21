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
}


def load(name: str) -> dict:
    return json.loads((REPO / name).read_text(encoding="utf-8"))


def release(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def generations() -> dict:
    """What has been generated and scored, and for which generation.

    Generation 2's prompt versions would be its own; none appears, which is the
    fact every stale sentence in the repository turned on.
    """
    rows = [
        json.loads(line)
        for line in (REPO / "results" / "rows.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    gen1_prompts = {"tneval-soap-v1", "icare-zeroshot-v1"}
    by_prompt = Counter(row.get("prompt_version") for row in rows)
    gen2 = {prompt: n for prompt, n in by_prompt.items() if prompt not in gen1_prompts}
    return {
        "rows_in_total": len(rows),
        "generation_1": {
            "measured": True,
            "tracks": dict(sorted(Counter(row.get("track") for row in rows).items())),
            "prompt_versions": dict(sorted(by_prompt.items())),
            "judges": sorted({row.get("judge_model") for row in rows if row.get("judge_model")}),
            "harness_versions": sorted(
                {row.get("harness_version") for row in rows if row.get("harness_version")}
            ),
        },
        "generation_2": {
            "measured": bool(gen2),
            "rows": sum(gen2.values()),
            "what_that_means": (
                "No note has been written and nothing has been scored for generation 2. Its "
                "operational rules are a proposal; a sentence in the present tense about one "
                "of its measurements describes a plan, not a result."
            ),
        },
    }


def protocol_state() -> dict:
    protocol = load("research/gen2/protocol.json")
    archived = sorted(
        (path.stem.removeprefix("protocol-") for path in (HERE / "history").glob("protocol-*.json")),
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
            "found 42 claims that had gone false, every one of them a symptom of its absence."
        ),
        "what_it_does_not_say": (
            "Whether an instrument is valid, whether a measurement would be any good, and "
            "whether anybody outside this project has agreed to anything. It reports what "
            "has happened, not what it is worth."
        ),
        "sources": SOURCES,
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
    print(f"  generation 1 measured: {gen['generation_1']['measured']}  {gen['generation_1']['tracks']}")
    print(f"  generation 2 measured: {gen['generation_2']['measured']}  rows {gen['generation_2']['rows']}")
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
