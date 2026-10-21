"""Re-derive every audit finding from the files, so none of them rests on being asserted.

The audit of 2026-09-15 was a narrative. Narratives go stale: that one still names
protocol 2.1.0, a pool of 10,059 records and 29 candidates, and still says nothing
has been translated. It closed by prescribing its own replacement -- *"Do not
create a new free-standing plan at each iteration ... generate the current status
from artifacts. Counts belong in configuration or derived reports, not in several
manually maintained narratives"* -- and that is this file.

So nothing here is written down as a finding. Every finding is computed from the
files it is about, and prints the path, what that path says, the path that holds
the truth, and what it holds. A finding that stops being true disappears from the
output; a new one appears without anybody noticing it first. That is the whole
point, and it is why the assistant's own claims about this repository belong in a
checker rather than in a message: seven of them were wrong in two days, each one a
statement about the state of the project made without a place that states it.

Two limits, declared rather than hidden.

The first is that some counts are *historical and correct*. A record of the round
of 2026-09-13 that says "36 candidates" was true when it was written, and
rewriting it would falsify a record. Those paths are declared in `DATED_RECORDS`
and their findings are reported separately, as prose to annotate rather than
numbers to fix. The membership of that list is a judgement; it is in one place so
it can be argued with.

The second is that four classes of defect cannot be computed at all: two prose
sentences contradicting each other, the present tense used of something not yet
run, a claim buried in a field meant for something else, and a convention with no
source. Those were found by reading, they are listed in `FOUND_BY_READING` with
the evidence, and this file says so rather than implying its coverage is complete.

    uv run python research/gen2/audit.py          # print, exit 1 if anything live
    uv run python research/gen2/audit.py --write  # also write audit-findings.json
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
GEN2 = HERE
CATALOG = GEN2 / "catalog"

#: Paths whose counts describe a dated round and are correct as of that date.
#: Reported apart from the live ones: a record that is rewritten when the world
#: moves is no longer a record. Every entry says why it is here.
DATED_RECORDS = {
    "research/gen2/history": "an archived protocol names its own version and pool; that is what it is for",
    "research/gen2/review-2026-09-13/review-memo.md": "declares itself not rewritten when later work changes something",
    "research/gen2/review-2026-09-13/flow-recorded.json": "append-only; records what was recorded on 2026-09-15",
    "docs/audit-and-repair-plan-2026-09-15.md": "a log of one inspection; its counts describe that day",
    "research/gen2/prior-proposals.json": "a prior-exposure ledger dated before the search",
}

#: Sentences inside live files that state a past value and are correct as history.
#:
#: A count is not a defect when the sentence dates it. The registration of the
#: panel's rule says the pool was 34 items on the day it was registered, which is
#: the fact that makes the registration meaningful, and no pattern can tell it
#: from a stale claim. Each entry is a literal substring verified once by reading,
#: so the exemption is per sentence rather than per file and can be argued with.
#: Short enough to survive the 140 characters a finding keeps of its line: the
#: first version named the whole clause and the truncation cut it in half, so the
#: exemption never fired.
DATED_SENTENCES = ("The pool was 34 items",)

#: The classes no script can decide, with what was found by reading and where.
#: Here so that the output never implies the checker covers everything.
FOUND_BY_READING = {
    "two artefacts contradicting each other in prose": [
        "the same 33 investigator acts are mode 'human' in review-record.json and "
        "'seen_no_objection' in the registry build; both files now say so (2026-10-19)",
        "docs/audit-and-repair-plan-2026-09-15.md says nothing has been translated; "
        "translation/instrument.json and translations.json record a translator chosen "
        "and two conversations translated on 2026-09-21",
    ],
    "the present tense used of something not run": [
        "the Czech page prints MERI SE in bold capitals for the state whose English "
        "reads 'an AI proposal awaiting human selection' (checked mechanically below)",
        "prompt_coverage.py, written by the assistant on 2026-10-19, says 'what is "
        "actually being measured' and 'M08 measures this construct ... in this round'",
        "paper/methods.md writes 'of the 16 measured' two sentences after '16 are "
        "proposed for measurement'",
        "language-set-proposal.json holds six agreement figures under the field name "
        "'measured_already'; five of the six do not say that there was one rater",
    ],
    "a claim buried in a field meant for something else": [
        "fifteen of the investigator's objections sat in the reason field of a "
        "retention decision; lifted into decisions.json on 2026-10-19, nine answered "
        "by the catalog, five open, one partly",
    ],
    "a convention with no source": [
        "the panel's four-step relevance scale has no origin recorded in protocol.json, "
        "which is scrupulous about the threshold in the same block",
    ],
}


def load(path: str) -> dict:
    return json.loads((REPO / path).read_text(encoding="utf-8"))


def text_of(path: str) -> str:
    return (REPO / path).read_text(encoding="utf-8", errors="replace")


#: What the audit does not read, and why. Its own report quotes the stale
#: sentences it found, so scanning it reports every finding a second time as a
#: finding of its own: the count went from 42 to 67 the moment the report was
#: committed. A checker that reads its own output measures itself.
NOT_SCANNED = {
    "research/gen2/audit.py": "the checker",
    "research/gen2/audit-findings.json": "its report, which quotes what it found",
}


def claim_bearing() -> list[str]:
    """Tracked files that state something, by the scope decided on 2026-10-21."""
    out = subprocess.run(
        ["git", "ls-files", "-z"], capture_output=True, text=True, cwd=REPO
    ).stdout.split("\0")
    return [
        name
        for name in out
        if name
        and name not in NOT_SCANNED
        and Path(name).suffix in (".json", ".md", ".py", ".html")
        and (
            name.startswith(("research/", "paper/", "docs/"))
            or name in ("README.md", "CLAUDE.md", "NOTICE")
        )
    ]


def dated(path: str) -> str | None:
    """Whether a finding sits in a record of a dated round.

    The first version compared the whole locator, so `review-memo.md:13` did not
    match the declared path `review-memo.md` and six findings in dated records
    were reported as live. The checker needed checking too, which is the argument
    for it being a script rather than a paragraph.
    """
    bare = re.sub(r":\d+$", "", path).split(" ")[0]
    for prefix, why in DATED_RECORDS.items():
        if bare == prefix or bare.startswith(prefix + "/"):
            return why
    return None


def dated_sentence(note: str) -> str | None:
    """Whether the line a finding sits on dates the value it states."""
    for sentence in DATED_SENTENCES:
        if sentence in note:
            return f"the sentence dates the value: {sentence!r}"
    return None


def finding(check: str, path: str, says, holder: str, holds, note: str = "") -> dict:
    return {
        "check": check,
        "path": path,
        "says": says,
        "holder": holder,
        "holds": holds,
        "note": note,
        "dated_record": dated(path) or dated_sentence(note),
    }


# --- C1 the pool ------------------------------------------------------------

#: A pool size beside a word that means a criterion. Deliberately narrow to the
#: values the pool has actually held: a wider pattern reported TN-Eval's 23 rubric
#: criteria, 40 sources and 127 judge pairs as pool claims, 68 findings for 21 real
#: ones. A number that overstates a problem is the same defect as one that hides it.
POOL = re.compile(
    r"\b(3[1-6])\b[^.\n]{0,30}?(candidates?|vlastnost\w*|kandid\w*)"
    r"|(candidates?|vlastnost\w*|kandid\w*|pool)[^.\n]{0,22}?\b(3[1-6])\b",
    re.I,
)


def c1_pool(paths: list[str]) -> list[dict]:
    """Every file that states a pool size, against the list that holds it."""
    truth = len(load("research/gen2/catalog/catalog.json")["candidates"])
    out = []
    for path in paths:
        if path.endswith("audit.py"):
            continue
        for line_no, line in enumerate(text_of(path).splitlines(), 1):
            for match in POOL.finditer(line):
                stated = int(match.group(1) or match.group(4))
                if stated == truth:
                    continue
                out.append(
                    finding(
                        "C1 pool size",
                        f"{path}:{line_no}",
                        stated,
                        "research/gen2/catalog/catalog.json candidates",
                        truth,
                        re.sub(r"\s+", " ", line.strip())[:140],
                    )
                )
    return out


# --- C2 the protocol version ------------------------------------------------

#: A version asserted as the current one. Naming an old version is not a defect:
#: "repaired on 2026-09-15 by protocol 2.1.0" is a true sentence about the past,
#: and the first version of this check reported thirteen such sentences as faults.
#: Only a phrase that presents a version as the governing one is counted, which is
#: a reading somebody made once and not a pattern a machine can infer.
VERSION = re.compile(
    r"(?:[Rr]esearch protocol|under research protocol|[Pp]rotocol)"
    r"[ :]+(\d+\.\d+\.\d+)\b(?=[ ,]*(?:admits|freezes|amended|gen2|$))",
)


def c2_version(paths: list[str]) -> list[dict]:
    """Every file that names a protocol version, against the live protocol."""
    protocol = load("research/gen2/protocol.json")
    live = protocol["version"]
    archived = {p.stem.removeprefix("protocol-") for p in (GEN2 / "history").glob("protocol-*.json")}
    out = []
    for path in paths:
        if path.endswith("audit.py"):
            continue
        for line_no, line in enumerate(text_of(path).splitlines(), 1):
            for match in VERSION.finditer(line):
                stated = match.group(1)
                if stated == live or stated not in archived | {live}:
                    continue
                out.append(
                    finding(
                        "C2 protocol version",
                        f"{path}:{line_no}",
                        stated,
                        "research/gen2/protocol.json version",
                        live,
                        re.sub(r"\s+", " ", line.strip())[:140],
                    )
                )
    return out


# --- C3 the pilot entries ---------------------------------------------------


def c3_pilot() -> list[dict]:
    """The entry list against every file that states its length."""
    catalog = load("research/gen2/catalog/catalog.json")
    entries = catalog["pilot_proposal"]["entries"]
    truth = len(entries)
    ids = [e["id"] for e in entries]
    out = []

    note = catalog["pilot_proposal"]["count_note"]
    stated = re.search(r"There are (\d+) entries", note)
    if stated and int(stated.group(1)) != truth:
        out.append(
            finding(
                "C3 pilot entries",
                "research/gen2/catalog/catalog.json pilot_proposal.count_note",
                int(stated.group(1)),
                "research/gen2/catalog/catalog.json pilot_proposal.entries",
                truth,
                "the note counts the list it sits on",
            )
        )
    # An id the prose names and the list does not hold.
    for named in sorted(set(re.findall(r"\bP\d\d\b", note))):
        if named not in ids:
            out.append(
                finding(
                    "C3 pilot entries",
                    "research/gen2/catalog/catalog.json pilot_proposal.count_note",
                    named,
                    "research/gen2/catalog/catalog.json pilot_proposal.entries",
                    "absent",
                    f"{named} is described as an entry and is not one",
                )
            )
    protocol = load("research/gen2/protocol.json")
    # Not stating the count is the repair, not a defect: the protocol said 14
    # while the list held 13. What it must do instead is say where the count
    # lives, so a reader is sent to the list rather than left with nothing.
    where = protocol["selection"]["first_round_measurements"]["supported_at_amendment"]
    if "catalog_entries" in where and where["catalog_entries"] != truth:
        out.append(
            finding(
                "C3 pilot entries",
                "research/gen2/protocol.json selection...catalog_entries",
                where["catalog_entries"],
                "research/gen2/catalog/catalog.json pilot_proposal.entries",
                truth,
            )
        )
    return out


# --- C4 what has been executed ----------------------------------------------


def c4_executed() -> list[dict]:
    """What queries.json says about running, against the logs, in both directions.

    Until 2026-10-21 all fifteen said `not_run` and twelve were in a log with a
    date, a record count and the sha256 of an export. Repairing that could have
    left this check reporting nothing for ever, which is a check that has stopped
    working rather than a defect that has gone; so it now also catches a query
    that claims to have run and is in no log, and one that names a log it is not
    in.
    """
    rows = load("research/gen2/queries.json")["queries"]
    in_logs: dict[str, str] = {}
    for log in sorted((GEN2 / "review-2026-09-13").glob("search-log-*.json")):
        for entry in json.loads(log.read_text(encoding="utf-8")).get("searches", ()):
            if entry.get("query_id"):
                in_logs[entry["query_id"]] = f"research/gen2/review-2026-09-13/{log.name}"

    out = []
    for row in rows:
        ident, status = row.get("id"), row.get("status")
        where = in_logs.get(ident)
        if status == "not_run" and where:
            out.append(
                finding(
                    "C4 executed vs planned",
                    f"research/gen2/queries.json {ident}",
                    "not_run",
                    where,
                    "executed, with counts and an export checksum",
                )
            )
        elif status == "run" and not where:
            out.append(
                finding(
                    "C4 executed vs planned",
                    f"research/gen2/queries.json {ident}",
                    "run",
                    "the four search logs",
                    "no log holds this query",
                )
            )
        elif status == "run" and row.get("executed", {}).get("log") != where:
            out.append(
                finding(
                    "C4 executed vs planned",
                    f"research/gen2/queries.json {ident}",
                    row.get("executed", {}).get("log"),
                    "the four search logs",
                    where,
                    "the query names one log and the logs put it in another",
                )
            )
    return out


# --- C5 decisions that name what they change --------------------------------

DOTTED = re.compile(r"^[a-z_]+(\.[a-z_]+)*$")


def c5_affects() -> list[dict]:
    """Every machine-readable target a decision names, against the protocol."""
    protocol = load("research/gen2/protocol.json")

    def resolves(path: str) -> bool:
        node = protocol
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                return False
            node = node[part]
        return True

    out = []
    for decision in protocol["decision_ledger"]:
        for target in decision.get("affects", ()):
            if DOTTED.match(target) and not resolves(target):
                out.append(
                    finding(
                        "C5 decision target",
                        f"research/gen2/protocol.json {decision['id']}.affects",
                        target,
                        "research/gen2/protocol.json",
                        "no such path",
                    )
                )
    return out


# --- C6 the same state in two languages -------------------------------------

#: Czech that asserts a measurement happens or happened, and nothing weaker.
#:
#: The reflexive present `meri se` ("is measured") and the participle `zmereno`
#: ("was measured"), not the noun `mereni` ("measurement"): the repaired label
#: reads "NAVRZENO K MERENI", proposed for measurement, and a pattern that
#: matched the noun would report the repair as the defect. A negated form is not
#: a finding either -- "v tomhle kole se nemeri" is the sentence we want.
#: Both word orders, because Czech takes the reflexive on either side of the verb
#: and the page's colour legend used the one the first pattern missed: "tmave
#: radky se meri", the dark rows are measured.
MEASURES = re.compile(
    r"(?<!ne)m[eě][řr][íi]\s*se\b|\bse\s+m[eě][řr][íi]\b|(?<!ne)zm[eě][řr]en", re.I
)


#: Czech quotation marks. A text that explains a defect has to be able to quote
#: it: the page's introduction now says that the dark rows read "meri se" until
#: 2026-10-21, and that sentence is the repair, not the fault. Stripping what is
#: quoted is the same exemption the review's source quotes get.
QUOTED_CS = re.compile("„[^“]*“")


def without_quotations(text: str) -> str:
    return QUOTED_CS.sub(" ", text)


def c6_state_words() -> list[dict]:
    """A Czech state word that asserts measurement, against its English original.

    The one finding of the reading classes that can be computed, and the one the
    investigator meets daily: the Czech page's word for the state whose English
    says "an AI proposal awaiting human selection" is the present indicative of
    "to measure", set in capitals, on every proposed row.
    """
    czech = load("research/gen2/catalog/czech.json")
    catalog = load("research/gen2/catalog/catalog.json")
    rows = sum(1 for c in catalog["candidates"] if c["state"] == "proposed")
    out = []

    pairs = [
        ("page.states.measured", czech["page"]["states"]["measured"], "proposed"),
        ("vocabulary.state.proposed", czech.get("vocabulary", {}).get("state", {}).get("proposed"), "proposed"),
    ]
    for where, word, state in pairs:
        if word and MEASURES.search(without_quotations(word)):
            out.append(
                finding(
                    "C6 state word",
                    f"research/gen2/catalog/czech.json {where}",
                    word,
                    f"research/gen2/catalog/catalog.json candidate_states.{state}",
                    catalog["candidate_states"][state],
                    f"asserts measurement for {rows} rows; nothing has been measured",
                )
            )
    for key, label in czech["page"]["filters"].items():
        if MEASURES.search(without_quotations(label)):
            out.append(
                finding(
                    "C6 state word",
                    f"research/gen2/catalog/czech.json page.filters.{key}",
                    label,
                    "results/rows.jsonl",
                    "no generation-2 row exists",
                    "a filter that partitions the criteria into measured and unmeasured",
                )
            )
    for index, paragraph in enumerate(czech["page"]["intro"]):
        if MEASURES.search(without_quotations(paragraph)):
            out.append(
                finding(
                    "C6 state word",
                    f"research/gen2/catalog/czech.json page.intro[{index}]",
                    paragraph[:90],
                    "results/rows.jsonl",
                    "no generation-2 row exists",
                    "the page's own explanation of its colour coding",
                )
            )
    return out


# --- C7 has generation 2 run at all -----------------------------------------


def c7_execution_evidence() -> list[dict]:
    """The only execution evidence in the repository, and what it covers."""
    rows = [json.loads(line) for line in (REPO / "results/rows.jsonl").read_text().splitlines() if line]
    tracks = sorted({row.get("track") for row in rows})
    gen2 = [row for row in rows if row.get("prompt_version", "").startswith(("gen2", "profiles"))]
    if gen2:
        return []
    return [
        finding(
            "C7 execution evidence",
            "results/rows.jsonl",
            f"{len(rows)} rows, tracks {tracks}",
            "research/gen2/catalog/operational.json measurements",
            "M06, M07, M08 proposed",
            "generation 2 has generated no note and measured nothing; no tracked file "
            "states this in one place, which is the defect every other check above is "
            "a symptom of",
        )
    ]


CHECKS = (
    ("C1", c1_pool, True),
    ("C2", c2_version, True),
    ("C3", c3_pilot, False),
    ("C4", c4_executed, False),
    ("C5", c5_affects, False),
    ("C6", c6_state_words, False),
    ("C7", c7_execution_evidence, False),
)


def run() -> dict:
    paths = claim_bearing()
    found: list[dict] = []
    for _, check, needs_paths in CHECKS:
        found.extend(check(paths) if needs_paths else check())
    live = [f for f in found if not f["dated_record"]]
    historical = [f for f in found if f["dated_record"]]
    by_check: dict[str, int] = {}
    for item in live:
        by_check[item["check"]] = by_check.get(item["check"], 0) + 1
    return {
        "version": "audit-v1",
        "marker": "AUTHORED-INVESTIGATOR-TEXT",
        "what_this_is": (
            "Every finding re-derived from the files it is about. Nothing here is written "
            "down as a finding: a finding that stops being true disappears from this file, "
            "and a new one appears without anybody noticing it first."
        ),
        "what_it_cannot_do": (
            "Four classes cannot be computed: two prose sentences contradicting each other, "
            "the present tense used of something not run, a claim buried in a field meant "
            "for something else, and a convention with no source. They are listed under "
            "found_by_reading with their evidence, and reading is not exhaustive."
        ),
        "claim_bearing_files_scanned": len(paths),
        "not_scanned": NOT_SCANNED,
        "counts": {"live": len(live), "in_dated_records": len(historical), "by_check": by_check},
        "live": live,
        "in_dated_records": historical,
        "found_by_reading": FOUND_BY_READING,
        "dated_records": DATED_RECORDS,
    }


def main() -> int:
    report = run()
    if "--write" in sys.argv:
        out = HERE / "audit-findings.json"
        out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        print(f"wrote {out.relative_to(REPO).as_posix()}")
    counts = report["counts"]
    print(f"scanned {report['claim_bearing_files_scanned']} claim-bearing files")
    print(f"live findings: {counts['live']}   in dated records: {counts['in_dated_records']}")
    for check, number in sorted(counts["by_check"].items()):
        print(f"   {check}: {number}")
    print()
    for item in report["live"]:
        print(f"{item['check']}  {item['path']}")
        print(f"      says   {item['says']!r}")
        print(f"      holder {item['holder']} holds {item['holds']!r}")
        if item["note"]:
            print(f"      {item['note']}")
    return 1 if counts["live"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
