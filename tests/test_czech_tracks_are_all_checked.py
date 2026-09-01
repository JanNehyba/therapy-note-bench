"""Every Czech-branch track is covered by the checks that guard the branch.

Offline. No network, no judge, no rows required.

**Why.** Every failure this branch has had in the last week is the same shape: a
track or a model was added, and something that should have looked at it did not
know it existed. The Deepsy PDSQI tracks drew without bands because the variance
tool had never heard of them. `glm-5.3` sat in six tables with an empty Band
cell because the payload predated it. `glm-5.3-flash` was withdrawn from the
endpoint and nothing said so for three days.

Each of those got a check. A check with a hand-written list of tracks is the
next instance of the same bug, so the lists are asserted against
`results.LOCAL_TRACKS` rather than trusted.
"""

from __future__ import annotations

import sys

from tnb import results
from tnb.config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tools"))

import czech_completeness  # noqa: E402
import czech_roster  # noqa: E402
import czech_variance  # noqa: E402

#: The eight tracks the Czech branch draws. Read from `results` so that adding a
#: ninth fails this file rather than passing quietly through every tool.
CZECH = tuple(
    track
    for track in results.LOCAL_TRACKS
    if track.startswith(("czech-", "deepsy-"))
)


def test_the_branch_really_has_eight_tracks():
    """A premise worth failing on. If it changes, every list below must be
    re-read by a person rather than adjusted to match."""
    assert len(CZECH) == 8, f"the Czech branch now has {len(CZECH)} tracks: {CZECH}"


def test_the_roster_check_speaks_for_every_track():
    missing = sorted(set(CZECH) - set(czech_roster.CZECH_TRACKS))
    assert not missing, (
        "these tracks are drawn but the roster check does not count a model "
        f"missing from them: {missing}"
    )


def test_the_completeness_check_knows_every_track_pairing():
    """Both halves and both formats of every instrument are twinned.

    A track with no twin is a track whose model list is never compared with
    anything, so a model asked in one place and not the other goes unreported --
    which is how `glm-5` sat in the Deepsy tables and in no Czech one.
    """
    twinned = {track for _axis, left, right in czech_completeness.TWINS for track in (left, right)}
    missing = sorted(set(CZECH) - twinned)
    assert not missing, f"these tracks are in no twin pair: {missing}"


def test_every_banded_track_has_a_composite():
    """`czech_variance.bands` needs one number per model, and `COMPOSITES` says
    which columns make it. A track without an entry raises at run time, in the
    middle of a long offline read, rather than here."""
    missing = sorted(set(CZECH) - set(czech_variance.COMPOSITES))
    assert not missing, f"these tracks have no banding composite: {missing}"


def test_every_pdsqi_track_has_a_corpus_entry():
    """The loader, the renderer and the cache root travel together, and a
    missing entry is the wrong-corpus failure this file's siblings record."""
    pdsqi = [track for track in CZECH if track.endswith("-pdsqi")]
    assert len(pdsqi) == 4, pdsqi
    # `PDSQI_CORPORA` is keyed on the task name, which is the track without the
    # instrument suffix: the Deepsy PDSQI track reads the Deepsy notes.
    for track in pdsqi:
        task_name = track.removesuffix("-pdsqi")
        assert task_name in czech_variance.PDSQI_CORPORA, (
            f"{track} reads notes from {task_name!r}, which has no corpus entry"
        )
