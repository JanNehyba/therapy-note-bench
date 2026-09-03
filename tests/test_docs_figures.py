"""Figures written into the prose documents, recomputed from the payload.

`docs/*.md` carries roughly 232 numbers and, before this file, not one of them
was compared with the data. The tests that did name a figure pinned it as a
literal string, so when a measure moved the document and its test went stale
together and the suite stayed green.

Seven of those numbers were wrong at once, and each was wrong in the direction
that flattered the sentence around it:

* "Most systems are beaten outright by nobody" -- eight of nineteen, a minority,
  in the sentence that explains why no winner is named;
* "the correlation is negative under both judges" -- negative under one
  (-0.025) and positive under the other (+0.053), three lines above a paragraph
  congratulating itself for having removed hand-copied numbers that were "wrong
  by more than the difference they were describing";
* "that document is 46% empty" -- 46% is the share *filled*, stated correctly by
  the same file 48 lines above, so the answer key was described as half as thin
  as it is;
* "a few tenths apart" -- the figure drawn from the same numbers says
  hundredths, and the figure is right: scores there are k/11, so the smallest
  gap that can exist is nine hundredths;
* "Seven of nine things ... are not measured" -- PDSQI-9 had been run and
  reaches eight, which the same section said forty-nine lines below;
* the self-preference intervals on the page explaining how they were repaired
  were the pre-repair ones, the judge-versus-judge interval among them 2.5 times
  too narrow;
* "Inference runs entirely inside e-INFRA" -- 38% of the published notes were
  written elsewhere, and both judges run outside it.

So each is recomputed here. As in `test_brief.py`, this file is a registry: **a
figure it does not name is a figure nobody is checking**, and the documents
carry many more than it names.
"""

from __future__ import annotations

import json
import re
import sys

import pytest

from tnb.config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tools"))

figures = pytest.importorskip("figures")

DOCS = REPO_ROOT / "docs"
TRACK = "tneval-soap"

#: The three columns the leaderboard's dominance claim is made over. Named here
#: rather than discovered, because "every measure" in that sentence means the
#: rubric's three and not the PDSQI columns, which are a different instrument.
RUBRIC = ("completeness", "conciseness", "faithfulness")

#: The eight PDSQI-9 attributes this benchmark scores. The ninth, "cited", is
#: dropped because a note written from one transcript has no source documents.
PDSQI = frozenset(
    {
        "accurate",
        "thorough",
        "succinct",
        "organized",
        "synthesized",
        "useful",
        "comprehensible",
        "stigmatizing",
    }
)

#: Small numbers as the documents spell them, so a count can be compared with a
#: sentence instead of with a second copy of itself.
WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "sixteen": 16,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "twenty-one": 21,
}


@pytest.fixture(scope="module")
def data():
    if not (DOCS / "leaderboard.json").exists():
        pytest.skip("no published payload in this checkout")
    return figures.Data.load()


@pytest.fixture(scope="module")
def payload() -> dict:
    path = DOCS / "leaderboard.json"
    if not path.exists():
        pytest.skip("no published payload in this checkout")
    return json.loads(path.read_text(encoding="utf-8"))


def read(name: str) -> str:
    """A document with its wrapping removed, because sentences run across lines."""
    path = DOCS / name
    if not path.exists():
        pytest.skip(f"{name} is not in this checkout")
    return " ".join(path.read_text(encoding="utf-8").split())


# --- limitations.md -----------------------------------------------------------


def test_the_dominance_count_is_the_count(data):
    """ "Eight of the nineteen are beaten outright by nobody."

    Dominance as this repository defines it: at least as good on every rubric
    measure under both judges, and strictly better on one.
    """
    scores = {
        (judge, measure): data.scores(TRACK, judge, measure)
        for judge in (figures.JUDGE_A, figures.JUDGE_B)
        for measure in RUBRIC
    }
    names = sorted(set.intersection(*(set(v) for v in scores.values())))

    def dominates(winner: str, loser: str) -> bool:
        strictly = False
        for table in scores.values():
            if table[winner] < table[loser]:
                return False
            strictly = strictly or table[winner] > table[loser]
        return strictly

    unbeaten = [n for n in names if not any(dominates(o, n) for o in names if o != n)]

    text = read("limitations.md")
    said = re.search(r"([\w-]+) of the ([\w-]+) are beaten outright by nobody", text)
    assert said, "limitations.md no longer states a dominance count"
    assert [WORDS[w.lower()] for w in said.groups()] == [len(unbeaten), len(names)], (
        f"the file says {said.group(0)!r}; the payload says {len(unbeaten)} of {len(names)}"
    )
    assert len(unbeaten) < len(names) / 2, "it is a minority, which is what the sentence says"
    assert "Most systems are beaten outright by nobody" not in text


def test_the_two_judges_disagree_about_the_sign_of_that_correlation(data):
    """The clause that called the correlation negative under both."""
    signs = {}
    for judge in (figures.JUDGE_A, figures.JUDGE_B):
        rho = figures._rho(TRACK, "completeness", "conciseness", data, judge)
        if rho is None:
            pytest.skip("the correlation is not computable in this checkout")
        signs[judge] = rho

    text = read("limitations.md")
    disagree = len({r > 0 for r in signs.values()}) == 2
    assert disagree, f"the judges now agree on the sign: {signs}"
    assert "the correlation is near zero and the two judges do not even agree on its sign" in text
    assert "the correlation is negative under both judges" not in text


def test_the_answer_key_is_described_as_filled_and_empty_consistently():
    """46% filled and 46% empty were both in this file, 48 lines apart.

    Recomputing the share is not possible offline -- `data/ihope_test.json` is
    fetched at run time into a gitignored directory -- so what is checked is
    that the two halves of the same fraction still add to a hundred. That is
    the defect that happened, and it is the half that can be checked here.
    """
    text = read("limitations.md")
    filled = {int(m) for m in re.findall(r"(\d{1,3})% of the form is filled in", text)}
    empty = {int(m) for m in re.findall(r"that document is (\d{1,3})% empty", text)}
    assert filled, "the file no longer states a fill rate"
    assert empty, "the file no longer states an empty share"
    for f in filled:
        for e in empty:
            assert f + e == 100, f"{f}% filled and {e}% empty cannot both be true"


def test_the_forward_temporal_gap_is_named_in_the_unit_it_can_move_in():
    """One session out of eleven is nine hundredths, so tenths is the wrong unit.

    The same sentence is drawn under the figure, where it says hundredths. Two
    copies of one sentence disagreeing by an order of magnitude is the reason
    this is pinned rather than fixed and left.
    """
    text = read("limitations.md")
    sessions = re.search(r"answered \"what happens at the next session\" in (\d+) of 40", text)
    assert sessions, "the file no longer says how many sessions the column rests on"

    step = 1 / int(sessions.group(1))
    assert f"a score of {step:.2f} there is one session" in text
    assert step < 0.1, "a step this size is hundredths, not tenths"
    assert "a few hundredths apart is not evidence" in text
    assert "a few tenths apart is not evidence" not in text


def test_the_rubric_measures_two_and_pdsqi_measures_eight(payload):
    """The section that said seven of nine are unmeasured after PDSQI-9 ran."""
    columns = set()
    for table in payload["tables"]:
        if table["track"] != TRACK or not table["scored"]:
            continue
        for row in table["rows"]:
            columns |= {k for k, v in row["headline"].items() if v is not None}
    measured = columns & PDSQI
    if not measured:
        pytest.skip("no PDSQI columns in this payload")
    assert len(measured) == 8, f"PDSQI reaches {len(measured)} attributes, not eight"

    text = read("limitations.md")
    assert "The ranking rubric measures two of the nine things" in text
    assert "reaches eight" in text
    assert "Seven of nine things" not in text
    assert "**This benchmark measures two of them.**" not in text


# --- methodology.md -----------------------------------------------------------
def test_the_two_temporal_ranges_in_the_prose_are_the_columns_they_describe(payload):
    """ "0.00-0.55" outlived the column by two systems, in three places at once.

    The briefing's front-page card, this sentence, and the `temporal_next`
    caveat inside `docs/leaderboard.json` -- which the README and both site
    pages reprint -- all froze the sixteen-model range. `glm-5.3` answers the
    looking-forward section in eight sessions of eleven, so the top is 0.73.

    The caveat computes its range now. This sentence is prose and cannot, so it
    is checked here. The figure regex in `test_published_numbers.py` cannot see
    either range -- it refuses a number followed by a dash and a digit -- so
    neither pair was ever in that file's budget, and registering them there
    would have credited four figures nothing counts.
    """
    rows = next(
        table["rows"]
        for table in payload["tables"]
        if table["track"] == "icare" and table["scored"]
    )
    text = read("methodology.md")
    for measure, name in (("temporal_past", "Looking back"), ("temporal_next", "looking forward")):
        values = [
            row["headline"][measure] for row in rows if row["headline"].get(measure) is not None
        ]
        assert values, f"no {measure} column in this payload"
        stated = f"({min(values):.2f}-{max(values):.2f}"
        assert stated in text, (
            f"the {name} sentence does not carry the range its column covers, {stated})"
        )


def test_the_self_preference_intervals_are_the_published_ones(data):
    """The page explaining the repair carried the pre-repair numbers."""
    preference = data.preference or {}
    if not preference.get("effects"):
        pytest.skip("no preference payload in this checkout")

    text = read("methodology.md")
    for entry in preference["effects"]:
        stated = (
            f"`{entry['judge']}` {entry['estimate']:+.3f} "
            f"[{entry['low']:+.3f}, {entry['high']:+.3f}]".replace("-", "−")
        )
        # The backtick and the sign survive the minus swap; the judge name does
        # not contain a hyphen-minus by accident -- it contains several, so the
        # name is put back afterwards.
        name = entry["judge"].replace("-", chr(8722))
        stated = stated.replace(f"`{name}`", f"`{entry['judge']}`")
        assert stated in text, f"methodology.md does not carry {stated}"

    difference = preference.get("difference")
    if difference:
        pair = (
            f"{difference['estimate']:+.3f} "
            f"[{difference['low']:+.3f}, {difference['high']:+.3f}]".replace("-", "−")
        )
        assert pair in text, f"methodology.md does not carry {pair}"


def test_the_cost_control_section_describes_the_order_the_code_walks():
    """It claimed a per-session prefix cache the code does not build.

    Kept as a test because the wrong version was the flattering one: it
    described a saving as already made, which is what stops it being made.
    """
    text = read("methodology.md")
    assert "not what the code does today" in text
    assert "Scoring is grouped **by session, not by model**" not in text
    assert "The Batch API is used" not in text, "no Batch API exists in this repository"


# --- models-snapshot.md -------------------------------------------------------


def test_the_provider_split_is_the_published_one(payload):
    """ "Inference runs entirely inside e-INFRA" -- 38% of it does not."""
    counted, seen = {}, set()
    for table in payload["tables"]:
        if not table["scored"]:
            continue
        for row in table["rows"]:
            # One set of notes per (system, generation prompt), however many
            # instruments rated it: PDSQI-9 rates the SOAP track's notes and
            # its table must not count them a second time.
            key = (row["system_id"], table["versions"]["prompt_version"])
            if key in seen:
                continue
            seen.add(key)
            counted[row["provider"]] = counted.get(row["provider"], 0) + (row["n_generated"] or 0)

    total = sum(counted.values())
    if not total:
        pytest.skip("no generation counts in this payload")
    outside = sum(n for provider, n in counted.items() if provider != "einfra")

    text = read("models-snapshot.md")
    assert "Inference runs entirely inside e-INFRA CZ infrastructure." not in text
    assert f"{outside / total:.0%} of the published notes were written" in text
    for provider in ("openai", "vertex"):
        share = counted.get(provider, 0) / total
        assert f"{share:.0%}" in text, f"the {provider} share {share:.0%} is not stated"


# --- README ------------------------------------------------------------------


def test_the_status_line_counts_the_models_and_the_sessions(payload):
    """ "**18 models** have written notes on 50 AnnoMI conversations and on 40
    iHOPE sessions" -- the sentence a reader meets first, and the exact shape
    that went stale in the briefing's lede when two systems joined.

    Nothing held it there. `test_published_numbers.py` counts figures in the
    README but does not ask what any of them mean.
    """
    text = read("../README.md")
    models, sessions = set(), {}
    for table in payload["tables"]:
        if not table["scored"]:
            continue
        models |= {r["system_id"] for r in table["rows"] if r.get("system_type") == "model"}
        sessions[table["track"]] = max(
            (r.get("n_attempted") or 0 for r in table["rows"]), default=0
        )
    assert models, "no scored models in this payload"
    assert f"**{len(models)} models** have written notes" in text
    for track, corpus in (("tneval-soap", "AnnoMI conversations"), ("icare", "iHOPE sessions")):
        if track in sessions:
            assert f"{sessions[track]} {corpus}" in text, (
                f"the status line does not say how many {corpus} the {track} track covers"
            )


def test_the_readme_marks_the_rows_a_judge_scored_from_its_own_vendor(payload):
    """`docs/limitations.md`: "Cells where a judge scored a model from its own
    family are marked in the table where they sit."

    The page drew the mark and the README table did not, so the surface most
    people read first -- and the one that travels into other documents --
    showed a judge's own vendor's rows with nothing on them.
    """
    from tnb import judge

    text = read("../README.md")
    marked = 0
    for table in payload["tables"]:
        # The tables the README actually prints: one per track, the default
        # judge's. A row in the other judge's table carries its own mark and
        # the model's name appears in this table too, so asking the question of
        # every table asks it of a row the README never drew.
        if not table["scored"] or table["versions"]["judge_model"] != judge.DEFAULT_MODEL:
            continue
        for row in table["rows"]:
            own = row.get("judges_own_family")
            if not own:
                continue
            marked += 1
            assert f"`{row['label']}` *(judge's own {own})*" in text, (
                f"{row['label']} is scored by its own vendor's judge and the README "
                "table does not say so"
            )
    if not marked:
        pytest.skip("no judge scored a model from its own family in this payload")
