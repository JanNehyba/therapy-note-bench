"""What the dominance test costs when conversations share a video.

`edges` draws conversations, and the 50 AnnoMI conversations are transcripts of
43 videos, so a draw can take one conversation of a pair without the other and
count a dependency as independent evidence (audit A12). Pinned here on
constructed cases: an unclustered run is the run this repository already
published, byte for byte; a clustered run draws whole clusters; a claim that
rests on one video stops holding when that video is drawn whole; and the
comparison reports both numbers rather than replacing one with the other.
"""

from __future__ import annotations

import json

import pytest

from tnb.config import REPO_ROOT
from tnb.scoring import clusters, edges

COLUMNS = (("x", 3), ("y", 2))
JUDGES = ("judge-a", "judge-b")


def _sessions(values: list[float]) -> dict[str, float]:
    return {f"s{index:02d}": value for index, value in enumerate(values)}


def _per_session(spec) -> edges.PerSession:
    return {
        judge: {
            system: {column: _sessions(values) for column, values in columns.items()}
            for system, columns in spec.items()
        }
        for judge in JUDGES
    }


def _means(spec) -> dict:
    return {
        judge: {
            system: {column: sum(values) / len(values) for column, values in columns.items()}
            for system, columns in spec.items()
        }
        for judge in JUDGES
    }


def _examine(spec, samples=2000, **overrides):
    return edges.examine(
        "t", COLUMNS, _means(spec), _per_session(spec), samples=samples, **overrides
    )


# --- the draw ----------------------------------------------------------------


def test_without_a_map_every_conversation_is_its_own_cluster():
    common = ["a", "b", "c"]
    assert edges.draw_plan(common, None) == [[0], [1], [2]]


def test_a_map_draws_the_cluster_whole():
    common = ["a", "b", "c", "d"]
    plan = edges.draw_plan(common, {"a": "v1", "b": "v1", "c": "v2", "d": "v3"})
    assert plan == [[0, 1], [2], [3]]
    assert sorted(index for group in plan for index in group) == [0, 1, 2, 3]


def test_a_conversation_with_no_known_video_stands_alone():
    """The conservative reading: a dependency nobody established is not assumed."""
    plan = edges.draw_plan(["a", "b"], {"a": "v1"})
    assert sorted(plan) == [[0], [1]]


def test_the_unclustered_run_is_the_published_one_unchanged():
    """The sensitivity analysis must not move the artefact it is measured against."""
    spec = {
        "top": {"x": [0.9] * 20, "y": [4.0] * 20},
        "bottom": {"x": [0.2] * 20, "y": [2.0] * 20},
    }
    explicit = _examine(spec, clusters={f"s{i:02d}": f"s{i:02d}" for i in range(20)})
    implicit = _examine(spec)
    assert implicit["draws"] == "conversations" and explicit["draws"] == "clusters"
    for name in ("edges", "layers", "counts", "undominated"):
        assert implicit[name] == explicit[name], name
    assert implicit["edges"][0]["n_drawn"] == implicit["edges"][0]["n_shared"] == 20


# --- what clustering costs ----------------------------------------------------


def _one_video_carries_it():
    """A lead that exists only on conversations sharing one video.

    Ten conversations: the winner is ahead on four that come from one video and
    level on the rest. Drawing conversations, the four enter draws separately;
    drawing the video whole, they enter together or not at all, and the claim
    swings with a single draw.
    """
    ahead, level = [0.5] * 4, [0.0] * 6
    return {
        "top": {"x": [v + 0.5 for v in ahead + level], "y": [1.0] * 10},
        "bottom": {"x": [0.5] * 10, "y": [1.0] * 10},
    }


def test_a_claim_carried_by_one_video_stops_holding_when_the_video_is_drawn_whole():
    spec = _one_video_carries_it()
    shared = {f"s{i:02d}": ("v1" if i < 4 else f"v{i}") for i in range(10)}
    loose = _examine(spec)
    clustered = _examine(spec, clusters=shared)

    (edge,) = loose["edges"]
    (other,) = clustered["edges"]
    assert edge["n_shared"] == other["n_shared"] == 10
    assert edge["n_drawn"] == 10 and other["n_drawn"] == 7
    assert edge["p_holds"] > other["p_holds"], "drawing a dependency whole cannot add certainty"
    assert edge["holds"] and not other["holds"]


def test_the_comparison_names_every_claim_whose_verdict_changed():
    spec = _one_video_carries_it()
    shared = {f"s{i:02d}": ("v1" if i < 4 else f"v{i}") for i in range(10)}
    found = clusters.compare(_examine(spec), _examine(spec, clusters=shared))

    assert found["tested"] == 1
    assert found["verdict_changed"] == 1 and found["verdict_unchanged"] == 0
    (row,) = found["changed"]
    assert (row["winner"], row["loser"]) == ("top", "bottom")
    assert row["kept_by_conversations_only"] is True
    assert row["p_holds_conversations"] > row["p_holds_clusters"]
    assert row["n_drawn_clustered"] == 7
    assert found["holds"] == {"conversations": 1, "clusters": 0}
    assert found["undominated"]["conversations"] <= found["undominated"]["clusters"]


def test_a_lead_spread_over_many_videos_survives_either_draw():
    spec = {
        "top": {"x": [0.9] * 20, "y": [4.0] * 20},
        "bottom": {"x": [0.2] * 20, "y": [2.0] * 20},
    }
    pairs = {f"s{i:02d}": f"v{i // 2}" for i in range(20)}
    found = clusters.compare(_examine(spec), _examine(spec, clusters=pairs))
    assert found["verdict_changed"] == 0 and found["verdict_unchanged"] == 1
    assert found["holds"] == {"conversations": 1, "clusters": 1}


# --- what it refuses to do ----------------------------------------------------


def test_the_icare_track_is_not_clustered_on_a_guess():
    from tnb import results

    assert results.TRACK_ICARE not in clusters.CLUSTERED_TRACKS
    assert clusters.build_track(results.TRACK_ICARE) is None


@pytest.mark.parametrize("track", clusters.CLUSTERED_TRACKS)
def test_a_published_sensitivity_artefact_says_it_replaces_nothing(track):
    found = clusters.load(track)
    if found is None:
        pytest.skip("the clustered sensitivity has not been built in this checkout")
    assert "not a replacement" in found["reading"]
    assert found["clustering"]["by"] == "AnnoMI source video"
    assert found["clustering"]["clusters"] <= found["clustering"]["conversations"]
    published = json.loads((REPO_ROOT / "docs" / f"edges-{track}.json").read_text(encoding="utf-8"))
    assert published["draws"] == "conversations", "the published test still draws conversations"
    assert found["comparison"]["holds"]["conversations"] == sum(
        1 for edge in published["edges"] if edge["holds"]
    ), "the sensitivity run disagrees with the artefact it is measured against"
