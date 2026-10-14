"""Which criteria may order the models, and which only describe them.

The distinction is the catalog's own and it was invisible. What decides a
criterion's correct answer already implies whether a higher score means a better
note, and one of the view generators said so in a sentence beside each basis:
for a criterion decided by the transcript, a deviation is an error and the
direction of quality is given; for an indicator, it must not be read as
more-is-better and is not a leaderboard column. The harvest of 2026-10-14 kept
the labels of that vocabulary and dropped those sentences, so the table named a
basis without saying what followed from it.

Four roles, derived from what decides the answer and from whether the criterion
is measured. Nothing here judges a particular criterion: the rule is applied, and
a role changes only when a basis or a state does.

- `orders`: the direction of quality is given by the source, the template or the
  note itself, so a higher score is a better note and the criterion may be a
  column of the published order.
- `orders_with_two_raters`: the quality *is* the expert's verdict, so it may
  order models only where two raters agree. One rater gives a reading.
- `describes_only`: an indicator, or a figure derived from other measures. It
  characterises a model and must never be read as more-is-better. Information
  density is the example: a denser note is not a better note.
- `not_measured_yet`: no rule, so no role.

The labels and the sentences are Czech and live in `czech.json`, where all the
wording does; every script in this directory carries none, which is what keeps
the Czech behind one allow-list entry and one test.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOG_PATH = HERE / "catalog.json"
CZECH_PATH = HERE / "czech.json"

ROLES = ("orders", "orders_with_two_raters", "describes_only", "not_measured_yet")


def role_of(candidate: dict) -> str:
    if candidate["state"] != "proposed":
        return "not_measured_yet"
    if candidate["decided_by"] in ("indicator", "derived"):
        return "describes_only"
    if candidate["decided_by"] == "rater":
        return "orders_with_two_raters"
    return "orders"


def needs_bank(candidate: dict) -> bool:
    """Whether the criterion cannot be measured without the information bank."""
    return "bank" in str(candidate.get("inputs", "")).lower()


def main() -> int:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    czech = json.loads(CZECH_PATH.read_text(encoding="utf-8"))

    missing = [key for key in ("ranking_role_labels", "basis_means") if key not in czech]
    if missing:
        print(f"czech.json has no wording for {missing}; nothing was written")
        return 2

    counts: dict[str, int] = dict.fromkeys(ROLES, 0)
    for candidate in catalog["candidates"]:
        role = role_of(candidate)
        counts[role] += 1
        entry = czech["candidates"][candidate["id"]]
        entry["ranking_role"] = role
        entry["needs_bank"] = needs_bank(candidate)

    czech["ranking_role_rule"] = (
        "Derived from what decides the correct answer and from whether the criterion is "
        "measured. An indicator or a derived figure never orders models; an expert verdict "
        "orders them only where two raters agree; the rest order them where the direction of "
        "quality is given. No role is set by hand, so one changes only when a basis or a "
        "state does."
    )
    czech["ranking_role_counts"] = counts
    czech["basis_means_note"] = (
        "What follows from the basis, restored on 2026-10-14. The harvest kept the label of "
        "each basis and dropped the sentence beside it, so the table named a basis without "
        "saying what followed from it."
    )
    czech["bank_is_not_a_criterion"] = (
        "The information bank is not a criterion and is not in the list. It is the answer "
        "key: the facts of one session, written down before anyone reads a note, each with "
        "how much it matters. The criteria that cannot be measured without it are marked by "
        "`needs_bank`."
    )
    CZECH_PATH.write_text(
        json.dumps(czech, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    labels = czech["ranking_role_labels"]
    for role in ROLES:
        print(f"  {counts[role]:3}  {role:24} {labels[role]}")
    print(f"  {sum(1 for c in catalog['candidates'] if needs_bank(c)):3}  need the bank")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
