"""Does the task actually ask for the property the catalog says matters?

Every candidate carries a relevance level for each of the four note purposes, and
nineteen of them carry an operational rule. Nothing checked that the task given
to the model for a purpose puts the property in scope. Measuring a property the
task never asked for measures the gap between our rubric and our own prompt.

The investigator raised this on 2026-09-21, about K20: *"ok, ale jen nutne to mit
jasne a standardizovane napsane v promptu"*. That one reached the catalog's
applicability. The general case did not, and this file is the general case.

Scope, decided on 2026-10-19: the nineteen candidates that have an operational
rule, at the purposes where their relevance is `high`. Those are the pairs that
could reach a measurement.

That scope was wrong by itself and the first run showed why. A measurement names
the purposes it runs at, and it names them independently of the relevance levels:
M07 measures K11 at `continuity` and `audit`, and K11 is rated high at `client`
alone. So the high pairs are not the measured pairs, and auditing only the former
leaves what is actually being measured unexamined. The scope is the union of the
two, which adds four pairs and found the defect this file exists to find.

What this is not: the pairs are judged by the assistant, one at a time, against
the assembled instruction. That judgement is recorded, not hidden, and every
`covered` and `partial` row carries the fragment it rests on. The fragment is
**checked against the assembled instruction before the file is written**, so a
quote nobody can find is a failed build rather than a claim on a page -- the same
rule the review's own source quotes are held to. What cannot be checked
mechanically is whether a fragment really covers a property; that is the reading,
and it is why the rows are quoted rather than summarised.

The instruction is assembled by `therapy_note_eval.profiles.instructions`, which
is the string the model is given: the purpose, the priorities, the shared rules,
and the section and word-limit line. The audit reads the English; the Czech block
of each profile is a translation of the same fields, and the structural check
below holds the two to the same shape, which is not the same as holding them to
the same meaning.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from therapy_note_eval.profiles import DEFINITIONS
from therapy_note_eval.profiles import VERSION as PROFILES_VERSION
from therapy_note_eval.profiles import instructions
from therapy_note_eval.schema import PROFILES, NoteSpec

HERE = Path(__file__).resolve().parent
OUT = HERE / "prompt-coverage.json"
CATALOG_PATH = HERE / "catalog.json"
OPERATIONAL_PATH = HERE / "operational.json"

#: Where in the instruction a fragment comes from. Recorded because a property
#: named in the shared rules is in scope for every purpose, while one named in a
#: profile's own sections is in scope for that purpose alone.
PLACES = ("purpose", "sections", "priorities", "rules", "format")

COVERED, PARTIAL, GAP = "covered", "partial", "gap"

#: One row per (candidate, purposes) where the same fragment does the work.
#: `quote` is a verbatim fragment of the assembled instruction; `missing` says
#: what the instruction does not ask for, and is required unless the row is
#: `covered`.
AUDIT: tuple[tuple, ...] = (
    # --- fidelity to the source, carried by the shared rules -----------------
    ("K01", PROFILES, COVERED, "rules", "Use only the supplied sources.", None),
    (
        "K02",
        ("continuity", "supervision", "client"),
        COVERED,
        "rules",
        "Preserve speaker, time, negation and uncertainty.",
        None,
    ),
    (
        "K03",
        ("continuity", "audit"),
        COVERED,
        "rules",
        "Preserve speaker, time, negation and uncertainty.",
        None,
    ),
    (
        "K04",
        ("continuity", "supervision", "client"),
        COVERED,
        "rules",
        "Label clinical hypotheses and recommendations as such.",
        None,
    ),
    (
        "K09",
        ("continuity", "supervision"),
        COVERED,
        "rules",
        "Use only the supplied sources.",
        None,
    ),
    # --- what to cover, carried by each purpose's own priorities or sections --
    (
        "K05",
        ("continuity",),
        COVERED,
        "priorities",
        "Retain changes, meaningful context, interventions and client response",
        None,
    ),
    (
        "K05",
        ("supervision",),
        COVERED,
        "priorities",
        "Preserve the sequence and rationale where stated, the client's perspective, response",
        None,
    ),
    (
        "K05",
        ("audit",),
        COVERED,
        "sections",
        "Documented concerns and goals, Interventions and response",
        None,
    ),
    (
        "K06",
        ("audit",),
        COVERED,
        "sections",
        "Unavailable information",
        None,
    ),
    (
        "K06",
        ("supervision",),
        COVERED,
        "priorities",
        "uncertainty and unresolved questions",
        None,
    ),
    (
        "K06",
        ("continuity",),
        PARTIAL,
        "rules",
        "Preserve speaker, time, negation and uncertainty.",
        "Negation covers a thing said to be absent. The third distinction the construct "
        "makes, that nobody asked, is asked for only by the audit purpose.",
    ),
    (
        "K07",
        PROFILES,
        COVERED,
        "purpose",
        None,
        None,
    ),
    (
        "K08",
        ("continuity",),
        COVERED,
        "sections",
        "Risk and agreed next steps",
        None,
    ),
    ("K08", ("audit",), COVERED, "sections", "Assessment and risk", None),
    (
        "K08",
        ("supervision",),
        PARTIAL,
        "rules",
        "Silence about risk is not evidence of no risk.",
        "The shared rule forbids concluding there is no risk from silence, so risk is in "
        "scope, but the supervision purpose never asks for risk as content of its own.",
    ),
    (
        "K10",
        ("continuity",),
        COVERED,
        "sections",
        "Risk and agreed next steps",
        None,
    ),
    ("K10", ("client",), COVERED, "sections", "What was agreed next", None),
    ("K10", ("audit",), COVERED, "sections", "Progress and plan", None),
    # The shared rule carries economy at every purpose, including the two M07
    # runs at, which are not the one the catalog rates high.
    (
        "K11",
        ("client", "continuity", "audit"),
        COVERED,
        "rules",
        "it is a maximum, not a target. Never pad a note to reach it.",
        None,
    ),
    (
        "K12",
        ("continuity", "client", "audit"),
        COVERED,
        "format",
        "Sections:",
        None,
    ),
    (
        "K14",
        ("client",),
        COVERED,
        "priorities",
        "Use plain, non-stigmatizing language.",
        None,
    ),
    (
        "K14",
        ("supervision",),
        GAP,
        "priorities",
        None,
        "The supervision purpose says nothing about how the client is written about. Its "
        "one rule of this kind protects the therapist: do not infer their competence.",
    ),
    # These two are not high for K14 and are audited because M08 runs there. This
    # is the live defect: the measurement of this round is pointed at the two
    # purposes whose task never raises the subject.
    (
        "K14",
        ("continuity", "audit"),
        GAP,
        "priorities",
        None,
        "Neither purpose mentions stigma or how the client is written about, and M08 "
        "measures this construct at both of them in this round. The audit purpose's one "
        "rule of the kind is about fabrication, not about language toward the client.",
    ),
    (
        "K17",
        ("client",),
        COVERED,
        "priorities",
        "Avoid unnecessary third-party details",
        None,
    ),
    (
        "K30",
        ("client",),
        GAP,
        "priorities",
        None,
        "The purpose asks for plain language, which is not the same property: the construct "
        "is about reading as a clinician of that language would write, with no machine "
        "phrasing and no carried-over idiom. Nothing asks for that.",
    ),
    (
        "K32",
        ("supervision", "client"),
        GAP,
        "priorities",
        None,
        "No purpose mentions the client's cultural, linguistic or social context. The "
        "construct was adopted by the investigator on 2026-09-21 and the task it would be "
        "measured under has never asked for it.",
    ),
    (
        "K33",
        ("continuity", "client"),
        GAP,
        "priorities",
        None,
        "No purpose asks the note not to contradict itself. The construct was added by the "
        "investigator on 2026-09-21 and the task it would be measured under has never "
        "asked for it.",
    ),
    (
        "K34",
        ("continuity", "supervision"),
        GAP,
        "priorities",
        None,
        "Neither purpose asks for professional terminology or for using it correctly. The "
        "client purpose is the only one that mentions terms at all, and it asks for the "
        "opposite: avoid unexplained clinical labels.",
    ),
)


def flat(text: str) -> str:
    """Whitespace-insensitive, for finding a fragment in a wrapped instruction."""
    return re.sub(r"\s+", " ", text).strip()


def assembled() -> dict[str, str]:
    """The instruction each purpose is given, as the model receives it."""
    return {profile: instructions(NoteSpec(profile=profile, language="en")) for profile in PROFILES}


def with_rules(catalog: dict, operational: dict) -> set[str]:
    """Candidates that have an operational rule, in this round or written for a later one."""
    in_round = {k for m in operational["methods"] for k in m["construct_ids"]}
    in_round |= {x["construct_id"] for x in operational["measurements"]}
    written = {r["construct_id"] for r in operational["rules_written_not_in_this_round"]["items"]}
    return (in_round | written) & set(c["id"] for c in catalog["candidates"])


def measured_pairs(operational: dict) -> set[tuple[str, str]]:
    """Every (candidate, purpose) a measurement of this round actually runs at.

    Only `measurements` name their purposes; the three methods name constructs
    and leave the purpose to the task, so they contribute nothing here and the
    pairs they would run at are covered by the relevance half of the scope.
    """
    return {
        (x["construct_id"], purpose) for x in operational["measurements"] for purpose in x["profiles"]
    }


def pairs_to_audit(catalog: dict, operational: dict) -> set[tuple[str, str]]:
    """Every (candidate, purpose) that could reach a measurement, or already does.

    Derived rather than listed, so a new candidate with a rule, a relevance level
    raised to high, or a measurement pointed at another purpose makes the audit
    incomplete instead of making it silent.
    """
    rules = with_rules(catalog, operational)
    by_id = {c["id"]: c for c in catalog["candidates"]}
    high = {
        (code, purpose)
        for code in rules
        for purpose, level in by_id[code]["relevance"].items()
        if level == "high"
    }
    return high | {pair for pair in measured_pairs(operational) if pair[0] in rules}


def rows() -> list[dict]:
    out = []
    for code, purposes, status, place, quote, missing in AUDIT:
        for purpose in purposes:
            out.append(
                {
                    "candidate": code,
                    "purpose": purpose,
                    "status": status,
                    "where": place,
                    "quote": quote,
                    "missing": missing,
                }
            )
    return out


def problems(catalog: dict, operational: dict, texts: dict[str, str]) -> list[str]:
    """Everything that must hold before the file is written.

    The first two are the point: a fragment nobody can find in the instruction is
    a claim about a text that does not exist, and a pair the audit does not name
    is a measurement nobody checked.
    """
    out: list[str] = []
    audited = rows()
    seen = {(r["candidate"], r["purpose"]) for r in audited}
    if len(seen) != len(audited):
        out.append("a pair is audited twice")
    expected = set(pairs_to_audit(catalog, operational))
    for code, purpose in sorted(expected - seen):
        out.append(f"{code}/{purpose}: could be measured and is not audited")
    for code, purpose in sorted(seen - expected):
        out.append(f"{code}/{purpose}: audited but cannot be measured; relevance is not high")

    for row in audited:
        if row["where"] not in PLACES:
            out.append(f"{row['candidate']}/{row['purpose']}: {row['where']} is not a place")
        if row["status"] == GAP:
            if row["quote"]:
                out.append(f"{row['candidate']}/{row['purpose']}: a gap quotes the instruction")
            if not row["missing"]:
                out.append(f"{row['candidate']}/{row['purpose']}: a gap says nothing")
            continue
        if row["status"] == PARTIAL and not row["missing"]:
            out.append(f"{row['candidate']}/{row['purpose']}: partial says nothing")
        # K07 is the purpose mechanism itself: every profile declares a recipient
        # and a purpose, which is the property, so there is no fragment to quote.
        if row["where"] == "purpose" and row["quote"] is None:
            continue
        if not row["quote"]:
            out.append(f"{row['candidate']}/{row['purpose']}: {row['status']} with no fragment")
        elif flat(row["quote"]) not in flat(texts[row["purpose"]]):
            out.append(
                f"{row['candidate']}/{row['purpose']}: the fragment is not in the instruction"
            )
    return out


def shape_of_the_czech(out: list[str]) -> None:
    """The two language blocks of a profile must at least have the same shape.

    Whether a translated clause carries the same meaning is not checkable here,
    and the file says so rather than implying the audit covers both languages.
    """
    for profile in PROFILES:
        english, czech = DEFINITIONS[profile]["en"], DEFINITIONS[profile]["cs"]
        if set(english) != set(czech):
            out.append(f"{profile}: the two language blocks name different fields")
        if len(english["sections"]) != len(czech["sections"]):
            out.append(f"{profile}: the two language blocks have different section counts")


def measurements_against_relevance(catalog: dict, operational: dict) -> list[dict]:
    """Where each measurement of this round runs, against where the catalog says it matters.

    The two were chosen separately and nothing compared them. M07 runs K11 at
    neither of the purposes the catalog rates high for it, and M08 runs K14 at
    neither of its two. That is not the same defect as an unasked property, and
    it is the one a reader of the results would never see.
    """
    by_id = {c["id"]: c for c in catalog["candidates"]}
    coverage = {(r["candidate"], r["purpose"]): r["status"] for r in rows()}
    out = []
    for measurement in operational["measurements"]:
        code = measurement["construct_id"]
        runs_at = list(measurement["profiles"])
        relevance = by_id[code]["relevance"]
        out.append(
            {
                "measurement": measurement["id"],
                "candidate": code,
                "runs_at": runs_at,
                "relevance_where_it_runs": {purpose: relevance[purpose] for purpose in runs_at},
                "high_purposes_it_does_not_run_at": sorted(
                    purpose
                    for purpose, level in relevance.items()
                    if level == "high" and purpose not in runs_at
                ),
                "coverage_where_it_runs": {
                    purpose: coverage[(code, purpose)] for purpose in runs_at
                },
            }
        )
    return out


def build(catalog: dict, operational: dict) -> dict:
    texts = assembled()
    audited = rows()
    counts: dict[str, int] = {}
    for row in audited:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    against = measurements_against_relevance(catalog, operational)
    measured_gaps = sorted(
        f"{entry['candidate']}/{purpose}"
        for entry in against
        for purpose, status in entry["coverage_where_it_runs"].items()
        if status == GAP
    )
    return {
        "version": "prompt-coverage-v1",
        "marker": "AUTHORED-INSTRUMENT-TEXT",
        "built_by": "research/gen2/catalog/prompt_coverage.py",
        "profiles_version": PROFILES_VERSION,
        "what_this_is": (
            "For every candidate that has an operational rule, at every purpose where its "
            "relevance is high, whether the task given to the model for that purpose asks "
            "for the property. Each covered or partial row quotes the fragment of the "
            "assembled instruction it rests on, and the fragment is checked against that "
            "instruction before this file is written."
        ),
        "why_it_exists": (
            "Nothing bound the catalog's relevance levels to the prompt that is supposed to "
            "put a property in scope, so a property the task never asked for could be "
            "measured and reported as a failure of the model. The investigator raised the "
            "specific case on 2026-09-21 about K20 and it reached that candidate's "
            "applicability; the general case reached nothing until now."
        ),
        "what_it_does_not_establish": (
            "Whether a fragment truly covers a property is a reading, made by the assistant, "
            "one pair at a time, and recorded here rather than hidden. The audit is of the "
            "English instruction; the Czech block of each profile is a translation held to "
            "the same shape and not to the same meaning."
        ),
        "scope": (
            "The candidates with an operational rule, at their high purposes. A candidate "
            "with no rule cannot be measured yet, and a purpose that does not rate it high "
            "is not where it would be measured first."
        ),
        "counts": {
            "candidates_with_a_rule": len(with_rules(catalog, operational)),
            "pairs": len(audited),
            **{status: counts.get(status, 0) for status in (COVERED, PARTIAL, GAP)},
            "measured_at_a_purpose_whose_task_does_not_ask": len(measured_gaps),
        },
        "measured_at_a_purpose_whose_task_does_not_ask": measured_gaps,
        "what_has_to_happen_before_the_round_runs": (
            "A pair listed above is measured at a purpose whose task never raises the "
            "property, so a model would be marked down for not doing what it was not asked "
            "to do. One of three things has to happen to each, and which one is the "
            "investigator's decision: the purpose's instruction gains a clause, the "
            "measurement stops running at that purpose, or the result is published with the "
            "gap named beside it. Reporting the number without the gap is the one option "
            "this file exists to prevent."
        ),
        "measurements_against_relevance": against,
        "instruction_audited": texts,
        "rows": audited,
    }


def main() -> int:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    operational = json.loads(OPERATIONAL_PATH.read_text(encoding="utf-8"))
    found = problems(catalog, operational, assembled())
    shape_of_the_czech(found)
    if found:
        print("nothing was written:", file=sys.stderr)
        for line in found:
            print(f"  {line}", file=sys.stderr)
        return 2
    report = build(catalog, operational)
    OUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    counts = report["counts"]
    print(f"wrote {OUT.name}: {counts['pairs']} pairs over {counts['candidates_with_a_rule']}")
    print(f"  covered {counts[COVERED]}, partial {counts[PARTIAL]}, gap {counts[GAP]}")
    for row in report["rows"]:
        if row["status"] != COVERED:
            print(f"  {row['status']:8s} {row['candidate']}/{row['purpose']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
