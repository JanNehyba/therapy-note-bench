"""Collect the registry review decisions out of the untracked working copies.

Eight snapshots of the same review live under `local/gen2-review-v4` to `v11`,
which is gitignored. They hold 14 response files, and the decisions in them are
the only record that the sources, the evidence items, the Czech measurements and
the methods were ever put in front of a person: `research/gen2/decisions.json`
carries the constructs and nothing else.

A snapshot is not a revision of the one before it. Counts went 30, 29, 29, 31,
31, 33, and the earliest holds a `revise` that no later one does, so a decision
could be withdrawn as well as added. This writes every decision from every
snapshot rather than the newest set, keys each to the file and version it came
from, and counts what changed between them. The count is the finding: an
instrument whose review silently lost a judgement is not a reviewed instrument.

It is a rescue, not a registry. It picks no winner where snapshots disagree and
supersedes nothing: deciding which record is current is the registry's job, and
doing it here would turn a transcription into a judgement nobody made.

Run from the repository root; writes `research/gen2/review-record.json`.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SNAPSHOTS = REPO / "local"
OUT = Path(__file__).resolve().parent / "review-record.json"

SNAPSHOT_VERSION = re.compile(r"-v(\d+)$")

#: What a subject id names, for the summary. The prefixes are the registry's,
#: and `language:cs:` prefixes a subject that is itself one of these.
KINDS = ("source", "evidence", "construct", "measurement", "method", "scope")


def snapshot_of(path: Path) -> int:
    match = SNAPSHOT_VERSION.search(path.parent.parent.name)
    if match is None:
        raise ValueError(f"not a numbered snapshot directory: {path.parent.parent.name}")
    return int(match.group(1))


def kind_of(subject: str) -> str:
    rest = subject[len("language:cs:") :] if subject.startswith("language:cs:") else subject
    head = rest.split(":", 1)[0]
    return head if head in KINDS else "other"


def main() -> int:
    files = sorted(
        SNAPSHOTS.glob("gen2-review-v*/registry_review_responses/*.json"),
        key=lambda p: (snapshot_of(p), p.name),
    )
    if not files:
        print("no snapshots under local/gen2-review-v*; nothing to rescue", file=sys.stderr)
        return 2

    sources = []
    decisions = []
    for path in files:
        raw = path.read_bytes()
        snapshot = snapshot_of(path)
        body = json.loads(raw.decode("utf-8"))
        response = body.get("response") or {}
        rows = body.get("decisions") or []
        sources.append(
            {
                "path": path.relative_to(REPO).as_posix(),
                "snapshot": snapshot,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "study_id": body.get("study_id"),
                "sheet_id": body.get("sheet_id"),
                "imported_at": body.get("imported_at"),
                "rater_id": response.get("rater_id"),
                "role": response.get("role"),
                "instrument_author": response.get("instrument_author"),
                "delegated": bool(response.get("delegated")),
                "delegation_decision": response.get("delegation_decision"),
                "submitted_at": response.get("submitted_at"),
                "collected_with": response.get("collected_with"),
                "decisions": len(rows),
            }
        )
        for row in rows:
            decisions.append(
                {
                    "snapshot": snapshot,
                    "source": path.relative_to(REPO).as_posix(),
                    "subject": row.get("subject"),
                    "subject_digest": row.get("subject_digest"),
                    "decision": row.get("decision"),
                    "mode": row.get("mode"),
                    "reviewer": row.get("reviewer"),
                    "role": row.get("role"),
                    "decided_at": row.get("decided_at"),
                    "reason": row.get("reason"),
                    "response_id": row.get("response_id"),
                }
            )

    by_subject: dict[str, list[dict]] = defaultdict(list)
    for row in decisions:
        by_subject[row["subject"]].append(row)

    # A subject whose record is not identical in every snapshot that named it:
    # either the decision differs, or the subject itself was rewritten under it
    # and the digest moved. Every value it was given is listed, in snapshot
    # order, because which one is current is a question this file does not
    # answer.
    changed = []
    for subject, rows in sorted(by_subject.items()):
        values = {r["decision"] for r in rows}
        digests = {r["subject_digest"] for r in rows}
        if len(values) > 1 or len(digests) > 1:
            changed.append(
                {
                    "subject": subject,
                    "decisions": sorted(v for v in values if v is not None),
                    "subject_digests": len(digests),
                    "snapshots": sorted({r["snapshot"] for r in rows}),
                    "records": [
                        {
                            "snapshot": r["snapshot"],
                            "decision": r["decision"],
                            "mode": r["mode"],
                            "subject_digest": r["subject_digest"],
                            "reason": r["reason"],
                        }
                        for r in sorted(rows, key=lambda r: r["snapshot"])
                    ],
                }
            )

    # A subject a snapshot named and no later snapshot did. Being dropped from
    # the review is not the same as being decided differently, and neither count
    # stands in for the other.
    seen_in: dict[int, set[str]] = {s["snapshot"]: set() for s in sources}
    for row in decisions:
        seen_in[row["snapshot"]].add(row["subject"])
    versions = sorted(seen_in)
    dropped = []
    for index, version in enumerate(versions[:-1]):
        later: set[str] = set().union(*(seen_in[v] for v in versions[index + 1 :]))
        for subject in sorted(seen_in[version] - later):
            dropped.append({"subject": subject, "last_named_in": version})

    kinds: dict[str, int] = defaultdict(int)
    for subject in by_subject:
        kinds[kind_of(subject)] += 1
    modes: dict[str, int] = defaultdict(int)
    for rows in by_subject.values():
        modes[sorted(rows, key=lambda r: r["snapshot"])[-1]["mode"]] += 1

    record = {
        "version": "review-record-v1",
        "built_by": "research/gen2/build_review_record.py",
        "what_this_is": (
            "AUTHORED-INVESTIGATOR-TEXT. Every registry review decision found in the "
            "gitignored working copies local/gen2-review-v4 to v11, keyed to the file "
            "and the snapshot it came from. A rescue of a record, not a registry: it "
            "picks no winner where snapshots disagree and supersedes nothing in "
            "decisions.json. The reasons are in the language the reviewer wrote them "
            "in, because a reason translated is no longer what was said."
        ),
        "why_it_exists": (
            "decisions.json carries the 33 construct decisions and nothing else. The "
            "decisions about the sources, the evidence items, the Czech measurements, "
            "the methods and the scope existed only under local/, which git ignores, "
            "so deleting a stale view would have deleted them."
        ),
        "what_mode_human_means_here": (
            "The mode below is the one the review form captured, not what the instrument "
            "counts. The 33 construct subjects carry mode 'human', and the same 33 are "
            "imported into the instrument registry by build_instrument.py as "
            "'seen_no_objection', because on 2026-10-08 the investigator said he does not "
            "stand behind those lines as judgements. Both are true of the same acts. Until "
            "2026-10-19 neither file said so, so a reader of this record counted 33 human "
            "reviews of the instrument; the registry's reading is the one any claim of human "
            "verification rests on, and it supports none."
        ),
        "summary": {
            "snapshots": len(seen_in),
            "response_files": len(sources),
            "decision_records": len(decisions),
            "subjects": len(by_subject),
            "subjects_by_kind": dict(sorted(kinds.items())),
            "subjects_by_latest_mode": dict(sorted(modes.items())),
            "subjects_decided_differently_across_snapshots": len(changed),
            "subjects_a_later_snapshot_stopped_naming": len(dropped),
        },
        "sources": sources,
        "subjects_decided_differently_across_snapshots": changed,
        "subjects_a_later_snapshot_stopped_naming": dropped,
        "decisions": decisions,
    }
    OUT.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    summary = record["summary"]
    where = OUT.relative_to(REPO).as_posix() if OUT.is_relative_to(REPO) else OUT.name
    print(
        f"{where}: {summary['decision_records']} decisions, "
        f"{summary['subjects']} subjects, {summary['snapshots']} snapshots"
    )
    print(
        f"  decided differently across snapshots: "
        f"{summary['subjects_decided_differently_across_snapshots']}"
    )
    print(
        f"  a later snapshot stopped naming:      "
        f"{summary['subjects_a_later_snapshot_stopped_naming']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
