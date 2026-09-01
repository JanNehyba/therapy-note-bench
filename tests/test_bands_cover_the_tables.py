"""A model drawn in a banded table is a model the bands place.

Offline. Reads `local/czech-rows.jsonl` and `local/czech-variance.json` when
both exist and skips when either does not, so a fresh checkout is not a failure.

**This is the check that was missing when a model was added.** `glm-5.3` was
generated and scored on the Czech tracks on 2026-08-31. The bands had last been
computed on 2026-08-29. Nothing refused the mismatch: `_band_numbers` looks the
model up in the payload, finds nothing, and `_band_cell` draws an empty cell.
So the model appeared in six tables with a score and no band, and the only way
to notice was to count the names in the payload by hand.

An empty Band cell is not a smaller claim than a filled one -- it is the
document silently declining to say which gaps around that row a reader may
read, in a table whose whole purpose is to say exactly that. The rest of the
page tells the reader that a position is not a measurement and that bands are
how you tell the difference; a row without one invites the neighbour-to-
neighbour comparison every other row is protected from.

The rule this pins is one-directional on purpose. The bands may not be missing
a model the rows draw. The reverse -- a model in the bands that the rows no
longer carry -- is a different fault with a different cause (a withdrawn run),
and it is checked separately below so that one failure does not hide the other.
"""

from __future__ import annotations

import json

import pytest

from tnb import results

ROWS = results.LOCAL_ROWS_PATH
VARIANCE = ROWS.parent / "czech-variance.json"


def _payload() -> dict:
    if not ROWS.exists() or not VARIANCE.exists():
        pytest.skip("the local Czech record is not in this checkout")
    return json.loads(VARIANCE.read_text(encoding="utf-8"))


def _scored_by_track_and_judge() -> dict[tuple[str, str], set[str]]:
    """Which systems each (track, judge) actually draws a row for."""
    found: dict[tuple[str, str], set[str]] = {}
    for row in results.latest(results.load(ROWS)):
        if not row.is_scored or not row.judge_model:
            continue
        found.setdefault((row.track, row.judge_model), set()).add(row.system_id)
    return found


def _banded(payload: dict, track: str, judge: str) -> set[str] | None:
    grouped = (payload.get("bands") or {}).get(track, {}).get(judge)
    if not grouped:
        return None
    return {model for band in grouped["bands"] for model in band["models"]}


def test_every_drawn_model_has_a_band():
    """The failure this file exists for, stated as an assertion.

    Only tracks that ARE banded are checked. A track with no bands at all is a
    separate and visible decision -- the table simply has no Band column, which
    is what the two Deepsy PDSQI tables looked like before they were computed --
    and it is not what this test is about.
    """
    payload = _payload()
    scored = _scored_by_track_and_judge()

    missing: dict[str, list[str]] = {}
    for (track, judge), systems in sorted(scored.items()):
        placed = _banded(payload, track, judge)
        if placed is None:
            continue  # not a banded track; nothing is claimed about its rows
        absent = sorted(systems - placed)
        if absent:
            missing[f"{track} | {judge}"] = absent

    assert not missing, (
        "these models are drawn in a banded table with no band, so the document "
        "declines to say which gaps around them may be read -- recompute the "
        "bands for the named tracks with `tools/czech_variance.py --only "
        f"<track>`:\n{json.dumps(missing, indent=2)}"
    )


def test_no_band_names_a_model_the_rows_have_withdrawn():
    """The other direction, checked separately so it cannot mask the first.

    A band naming a system with no scored row is the residue of a run that was
    abandoned or cleaned out of the record afterwards. It is not harmless: the
    band boundaries were drawn against that system's score, so every other
    model's placement rests partly on a number the tables no longer carry.
    """
    payload = _payload()
    scored = _scored_by_track_and_judge()

    stale: dict[str, list[str]] = {}
    for track, judges in sorted((payload.get("bands") or {}).items()):
        for judge in sorted(judges):
            placed = _banded(payload, track, judge) or set()
            gone = sorted(placed - scored.get((track, judge), set()))
            if gone:
                stale[f"{track} | {judge}"] = gone

    assert not stale, (
        "these bands place a model the rows no longer score, so the boundaries "
        "were drawn against a number the tables do not carry:\n"
        f"{json.dumps(stale, indent=2)}"
    )


def test_the_check_actually_ran():
    """A test that skips silently on an empty record proves nothing.

    Both assertions above pass trivially when no track is banded, and that is
    exactly the state a broken payload would leave behind.
    """
    payload = _payload()
    banded = sum(len(judges) for judges in (payload.get("bands") or {}).values())
    assert banded >= 8, f"only {banded} (track, judge) band sets in the payload"
