"""A page credits, describes and names only what it drew -- and all of it.

Offline. Every check builds a payload from fixture rows and reads it; nothing
here renders or runs a browser.

**The failure these come from.** For a long time there was one page and it drew
every track, so `build` attached the whole registry to it and was right by
accident. A second page was added and inherited all of it: it credited
TN-Eval's two human annotators and profiled the iHOPE corpus while drawing
neither; it headed its expandable rows "Rubric criteria" over what is actually
a denominator; it printed iCARE's reason for not being ranked under tables
unranked for other reasons; and it named `rows.jsonl` as the record it came
from when it came from another file.

That page has left this repository and these checks stay, because what they
guard is `build` attaching a registry to a payload without asking whether the
payload drew it -- which is a property of `build`, not of that page.

None of those is a wrong number. Each is a sentence that reads as a claim about
provenance, and provenance is the one thing a reader cannot check for
themselves.
"""

from __future__ import annotations

import pytest

from tnb import report, results
from tnb.results import Row


def _row(track: str, **overrides) -> Row:
    base = {
        "track": track,
        "system_id": "gemma4",
        "system_type": "model",
        "provider": "einfra",
        "prompt_version": "p-v1",
        "n_sessions_attempted": 10,
        "n_sessions_generated": 10,
    }
    return Row(**{**base, **overrides})


UNRANKED = [track for track, measure in report.RANKING_MEASURES.items() if measure is None]


def test_every_unranked_track_says_why_in_its_own_words():
    """Two tracks carry no ranking column for two different reasons, and the
    page printed iCARE's under both: "the source paper found they disagree" is
    true of iCARE and is not a statement anybody has made about PDSQI-9.

    The reasons were written as comments beside `RANKING_MEASURES` and never
    reached a reader."""
    assert UNRANKED, "nothing is unranked, so this test is watching nothing"
    missing = [track for track in UNRANKED if track not in report.NOT_RANKED_REASONS]
    assert not missing, f"unranked tracks falling back to iCARE's reason: {missing}"

    icare = report.NOT_RANKED_REASONS[results.TRACK_ICARE]
    borrowed = [
        track
        for track in UNRANKED
        if track != results.TRACK_ICARE and report.NOT_RANKED_REASONS[track] == icare
    ]
    assert not borrowed, f"tracks printing iCARE's reason as their own: {borrowed}"


@pytest.mark.parametrize("track", sorted(report.RANKING_MEASURES))
def test_a_tables_reason_reaches_the_payload(track):
    """The map is only half of it: the renderer reads `not_ranked_reason` off
    the table, so a table without one draws nothing where the sentence goes.

    And a table that *is* ranked must carry none. This asked every table for one
    and `.get(track, <iCARE's>)` obliged, so both SOAP tables published "this
    track is deliberately not ranked: its columns measure different things and
    the source paper found they disagree" in `docs/leaderboard.json`, about a
    table ordered by completeness, under the iCARE paper's reasoning. The page
    guards on `ranking_measure` and never drew it; the JSON is published too and
    has no guard.
    """
    data = report.build([_row(track)])
    for table in data["tables"]:
        if report.RANKING_MEASURES.get(table["track"]) is None:
            assert table.get("not_ranked_reason"), f"{table['track']} carries no reason"
        else:
            assert "not_ranked_reason" not in table, (
                f"{table['track']} is ranked and carries a reason for not being ranked: "
                f"{table.get('not_ranked_reason')!r}"
            )
        assert table.get("detail_label"), f"{table['track']} carries no detail heading"


def test_a_page_credits_what_it_used_and_nothing_else():
    """Both directions. A source listed reads as a source used, and a source
    used and not listed is a licence problem, so neither is allowed to drift."""
    for track in results.PUBLISHED_TRACKS:
        data = report.build([_row(track)])
        got = {entry["source"] for entry in data["licences"]}
        want = {source for source, tracks in report.LICENCE_TRACKS.items() if track in tracks}
        assert got == want, f"{track}: credits {sorted(got)}, uses {sorted(want)}"


def test_a_withdrawn_track_keeps_its_sources():
    """A superseded group is still a track named on the page -- "this was
    published and is not any more" -- and the reader who reads that name still
    needs to know what it was measured with. Scoping to the drawn tables alone
    dropped PDSQI-9 from the published page while PDSQI-9 was still named on it.
    """
    data = report.build([_row(results.TRACK_TNEVAL)])
    drawn_only = {entry["source"] for entry in data["licences"]}

    withdrawn = dict(data)
    assert "superseded" in withdrawn
    # The same page, with a PDSQI group named as withdrawn rather than drawn.
    with_pdsqi = report.build(
        [
            _row(results.TRACK_TNEVAL),
            _row(results.TRACK_PDSQI, harness_version="0.0.1"),
            _row(results.TRACK_PDSQI, harness_version="0.9.9"),
        ]
    )
    named = {entry["track"] for entry in with_pdsqi["superseded"]} | {
        table["track"] for table in with_pdsqi["tables"]
    }
    assert results.TRACK_PDSQI in named, "the fixture did not produce a PDSQI group"
    assert "PDSQI-9" in {entry["source"] for entry in with_pdsqi["licences"]}
    assert "PDSQI-9" not in drawn_only, "the fixture proves nothing if it was there anyway"


def test_a_page_names_the_record_it_was_built_from():
    """A page built from one file and naming another. Of every line on a page,
    the one saying where the numbers came from is the one a reader has no way to
    check, so it is passed in rather than assumed.

    The second record this was written for has left the repository. The
    parameter has not, and neither has the default it overrides, so the check is
    made against a name that is not the published one.
    """
    assert report.build([_row(results.TRACK_TNEVAL)])["generated_from"] == results.ROWS_PATH.name
    elsewhere = report.build([_row(results.TRACK_TNEVAL)], source="somewhere-else.jsonl")
    assert elsewhere["generated_from"] == "somewhere-else.jsonl"
    assert elsewhere["generated_from"] != results.ROWS_PATH.name
