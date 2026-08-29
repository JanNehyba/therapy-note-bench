"""A judge appears at one setting in the local record, or the tables mix two.

Offline. The check runs over `local/czech-rows.jsonl` when it exists and is
skipped when it does not, so a fresh checkout is not a failure.

**Why this is a test and not a habit.** An abandoned run left rows behind three
times in one morning, and each time the leftovers were found by reading the
file rather than by anything refusing them. Twice the first clean missed some,
because the two judges record the ceiling differently -- Vertex writes
`thinking_budget + answer_tokens` and OpenAI writes a pinned constant -- so
filtering on the number one of them used left the other's rows in place.

Two settings for one judge is two instruments. `results.COMPARABILITY_KEYS`
keeps them out of one table, so nothing is *drawn* wrong; what goes wrong is
quieter. Every payload under `local/` is computed from the rows -- the bands,
the variance, the human anchor -- and those tools group by track and judge
without looking at the settings. A leftover row is then averaged into a figure
beside a table it does not belong to.
"""

from __future__ import annotations

import collections
import json

import pytest

from tnb import results

ROWS = results.LOCAL_ROWS_PATH


def _settings_by_judge() -> dict[str, set[str]]:
    if not ROWS.exists():
        pytest.skip(f"{ROWS} is not in this checkout")
    found: dict[str, set[str]] = collections.defaultdict(set)
    for line in ROWS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        judge = row.get("judge_model")
        if not judge:
            continue
        found[judge].add(json.dumps(row.get("judge_settings") or {}, sort_keys=True))
    return found


def test_each_judge_appears_at_one_setting():
    """Not "the tables are right" -- they are, the comparability key sees to
    that. This is about the payloads, which group by judge and never look."""
    offenders = {
        judge: sorted(settings)
        for judge, settings in _settings_by_judge().items()
        if len(settings) > 1
    }
    assert not offenders, (
        "a judge appears at more than one setting, so a payload computed per "
        f"judge averages two instruments together: {json.dumps(offenders, indent=2)}"
    )


def test_every_row_records_how_its_judge_was_set():
    """A group that names a judge and records no settings is withdrawn rather
    than drawn -- so a row without them is not a table, it is a table that
    silently is not there."""
    if not ROWS.exists():
        pytest.skip(f"{ROWS} is not in this checkout")
    missing = []
    for line in ROWS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("judge_model") and not row.get("judge_settings"):
            missing.append(f"{row.get('track')}/{row.get('system_id')}")
    assert not missing, f"rows naming a judge but not how it was set: {sorted(set(missing))[:8]}"
