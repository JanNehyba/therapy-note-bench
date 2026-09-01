"""A file the site serves is written whole or not at all.

Its own file rather than a corner of another, because what it guards is not
a measure or a page: it is the act of publishing, and every artefact under
`docs/` goes through it.
"""

from __future__ import annotations

import pytest


def test_a_published_file_is_never_left_half_written(tmp_path):
    """`docs/corpus-profile.json` was found as 3 696 bytes of NUL on 2026-09-01.

    `Path.write_text` truncates and then fills, so anything that stops the write
    between the two leaves a file of the right length and no content -- and that
    one is linked from the briefing for a reader to open. Written beside the
    target and renamed now, so a failed run leaves the old file exactly as it
    was.

    Provoked with a lone surrogate, which cannot be encoded as UTF-8: the
    staging file is created and the write dies inside it, which is the shape of
    the accident. Built with `chr(0xD800)` rather than written as an escape,
    because a surrogate in this source is one more file that cannot be saved --
    which is how the first draft of this test destroyed itself.
    """
    from tnb.config import write_published

    target = tmp_path / "published.json"
    write_published(target, '{"a": 1}\n')
    assert target.read_text(encoding="utf-8") == '{"a": 1}\n'

    with pytest.raises(UnicodeEncodeError):
        write_published(target, '{"a": "' + chr(0xD800) + '"}')

    assert target.read_text(encoding="utf-8") == '{"a": 1}\n', (
        "a failed write replaced the published file with a partial one"
    )
    assert not list(tmp_path.glob("*.writing")), "the staging file was left behind"


def test_a_shared_top_is_named_as_a_shared_top():
    """The summary named one system out of a tie, chosen by the alphabet.

    `describe` took `dominance[0]`, and `dominance` is sorted by count and then
    by name. On the iCARE track that published "`gpt-5.6-sol` beats 6" while
    `qwen3.8-27b` also beat 6 -- on a page whose argument is that no single
    winner can be named. Nothing could reveal it: the sentence is true of the
    system it names and the one it omits leaves no trace.
    """
    from tnb.scoring.concordance import Comparison, Dominance, describe

    def summary(counts):
        return describe(
            Comparison(
                judge_a="judge-a",
                judge_b="judge-b",
                measures=[],
                dominance=[Dominance(system=s, beats=["x"] * n) for s, n in counts],
                undominated=["z"],
                n_systems=9,
                systems=["z"],
            )
        )

    alone = summary([("alpha", 3), ("beta", 1)])
    assert "`alpha` beats 3." in alone, alone

    shared = summary([("alpha", 3), ("beta", 3), ("gamma", 1)])
    assert "`beta`" in shared, "the second system at the top is not named"
    assert "and 2 do" in shared, shared
    assert "`alpha` beats 3." not in shared, "a tie is still being reported as one winner"
