"""The briefing's prose, checked against the payload it claims to be read from.

The briefing is the artefact that leaves this repository: it is printed to PDF
and sent to people who will never open the site. It used to open its last
section with "Every figure and every number in this document is generated from
two published files. Nothing was typed in" -- while carrying more than thirty
hand-typed numbers, four of which were wrong:

* the calibration table printed Krippendorff's alpha under the heading the
  README uses for Cohen's kappa and Spearman's rho, so the same judge beat the
  therapists' ceiling on the site and failed it in the PDF;
* an effect of 0.02 was called "a fiftieth" of a range the same section printed
  two paragraphs above as 0.22, understating the judge's vendor bias 4.5-fold;
* the judge-vs-judge interval was a superseded estimate, 2.5 times narrower than
  the one the payload beside it carries;
* and the paragraph asserting all of this told the reader not to check.

So each figure the prose states is recomputed here from the published payload.
The registry below is the list the briefing now promises: **a sentence this file
does not name is a sentence nobody is checking**, and that is said out loud
rather than left for a reader to discover.
"""

from __future__ import annotations

import html
import json
import re
import sys

import pytest

from tnb.config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tools"))

brief = pytest.importorskip("brief")
figures = pytest.importorskip("figures")

DOCS = REPO_ROOT / "docs"
TRACK = "tneval-soap"
RANKING = "completeness"


@pytest.fixture(scope="module")
def data():
    if not (DOCS / "leaderboard.json").exists():
        pytest.skip("no published payload in this checkout")
    return figures.Data.load()


@pytest.fixture(scope="module")
def prose(data) -> str:
    """The rendered briefing with its wrapping and its figures taken out.

    Wrapping, because every sentence here is written across three or four source
    lines and a reader sees one line. Figures, because an SVG is full of
    coordinates that would match a search for any number at all.
    """
    rendered = re.sub(r"<svg.*?</svg>", " ", brief.render(data), flags=re.S)
    return " ".join(rendered.split())


@pytest.fixture(scope="module")
def calibration() -> dict:
    path = DOCS / "calibration.json"
    if not path.exists():
        pytest.skip("no calibration payload in this checkout")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def calibration_row(data) -> dict[tuple[str, str], list[str]]:
    """The cells of each calibration row, keyed by the measure and its form.

    Read out of the table rather than searched for in the page. The first
    version of this test asked whether each number appeared anywhere in the
    document, and a mutation that dropped the kappa and rho columns entirely
    went unnoticed: the checklist's kappa and its alpha both print as 0.60, and
    the ceiling sentence under the table already says 0.13. Presence somewhere
    is not presence in the cell that claims to hold it.

    Keyed on the form as well as the name, because the rubric row and the likert
    row are both called "completeness" and only "checklist" against
    "1-5 rating" tells them apart.
    """
    rendered = brief.render(data)
    table = re.search(r"<table>(?:(?!</table>).)*?Alpha, judge.*?</table>", rendered, re.S)
    assert table, "the briefing draws no calibration table"

    rows = {}
    for row in re.findall(r"<tr>(.*?)</tr>", table.group(0), re.S):
        cells = [
            " ".join(html.unescape(re.sub(r"<[^>]+>", "", cell)).replace("–", "-").split())
            for cell in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        ]
        if cells:
            rows[(cells[0], cells[1])] = cells
    return rows


# --- the calibration table carries both statistics ----------------------------


def test_the_calibration_table_names_its_statistic(calibration_row, calibration):
    """Two pairs of numbers, and the name of the statistic, in every row.

    The table used to print the alpha pair alone under "Judge vs therapist" --
    the heading the README uses for the kappa/rho pair. Same words, different
    statistic, and on likert completeness the two disagree about whether the
    judge clears the human ceiling. Nothing in the document said the other pair
    existed, so the contradiction looked like an error in one of the two pages.
    """
    for entry in calibration["agreements"]:
        name = entry["name"].replace("_", " ").replace("rubric ", "").replace("likert ", "")
        form = "checklist" if entry["name"].startswith("rubric") else "1-5 rating"
        cells = calibration_row.get((name, form))
        assert cells, f"{entry['name']} has no row in the calibration table"

        assert cells[2] == entry["statistic"], f"{entry['name']} does not say what it measured"
        printed = cells[3:]
        expected = [f"{entry[f]:.2f}" for f in ("judge", "humans", "alpha", "alpha_humans")]
        assert printed == expected, f"{entry['name']} prints {printed}, payload says {expected}"


def test_the_ceiling_sentence_reads_the_ceiling_from_the_payload(prose, calibration):
    """The sentence naming what two therapists manage on the 1-5 scales."""
    likert = [e for e in calibration["agreements"] if e["name"].startswith("likert")]
    stated = ", ".join(f"{e['alpha_humans']:.2f}" for e in likert[:-1])
    assert f"{stated} and {likert[-1]['alpha_humans']:.2f} by alpha" in prose

    checklist = next(e for e in calibration["agreements"] if e["name"].startswith("rubric"))
    reached = (
        f"On the 23-item checklist they reach {checklist['alpha_humans']:.2f}, "
        f"and the judge reaches {checklist['alpha']:.2f}."
    )
    assert reached in prose


def test_the_two_statistics_are_compared_in_the_direction_the_data_points(prose, calibration):
    """The sentence claims the judge clears one ceiling and not the other."""
    entry = next(e for e in calibration["agreements"] if e["name"] == "likert_completeness")
    by_rho = "above" if entry["judge"] > entry["humans"] else "below"
    by_alpha = "above" if entry["alpha"] > entry["alpha_humans"] else "below"
    assert by_rho != by_alpha, "the finding this sentence reports has gone away"
    assert f"{by_rho} the therapists on one and {by_alpha} them on the other" in prose


# --- the range, and the share of it an effect takes ---------------------------


def test_the_range_sentence_counts_the_systems_it_describes(prose, data):
    """Both halves of "19 systems are packed into a range of 0.22"."""
    scores = data.scores(TRACK, figures.JUDGE_A, RANKING)
    width = max(scores.values()) - min(scores.values())
    assert f"{len(scores)} systems are packed into a range of {width:.2f}" in prose


def test_the_bias_is_stated_as_the_share_of_the_range_it_actually_is(prose, data):
    """The sentence that called 0.02 "a fiftieth" of a range of 0.22.

    An eleventh. The error made the effect the section exists to report look 4.5
    times smaller than the section's own table shows, and the next clause --
    "enough to move a system several places" -- contradicted it.

    **And then it was wrong a second time, in the same direction, for a second
    reason** -- and this test blessed it, because it built its expectation the
    same way the code did. The denominator was every drawn row, which runs down
    to the therapist-written note and the two dated reference models; the
    sentence says "the range the current models occupy". Over the sixteen models
    the effects are 18% and 26%, not 8% and 11%. So the width here is computed
    from the population the *sentence* names, and a test that agrees with the
    code by construction is not a test.
    """
    preference = data.preference or {}
    effects = {entry["judge"]: entry for entry in preference.get("effects", [])}
    if not effects:
        pytest.skip("no preference payload in this checkout")

    shares = []
    for judge in (figures.JUDGE_A, figures.JUDGE_B):
        entry = effects.get(judge)
        models = [
            row["headline"][RANKING]
            for row in data.rows(TRACK, judge)
            if row.get("system_type") == "model" and row["headline"].get(RANKING) is not None
        ]
        if not entry or not models:
            continue
        width = max(models) - min(models)
        shares.append(f"{entry['estimate'] / width:.0%}")

    assert f"these effects are {' and '.join(shares)} of the range" in prose
    assert "a fiftieth" not in prose


def test_the_share_is_not_taken_over_a_range_that_includes_the_therapist(prose, data):
    """The wider denominator halves the number, so it must not be the one used.

    Pinned separately from the test above because the two are one edit apart: if
    somebody restores `data.scores`, which returns every drawn row, the shares
    become 8% and 11% again and only this assertion says so.
    """
    everyone = data.scores(TRACK, figures.JUDGE_A, RANKING)
    models = [
        row["headline"][RANKING]
        for row in data.rows(TRACK, figures.JUDGE_A)
        if row.get("system_type") == "model" and row["headline"].get(RANKING) is not None
    ]
    if not everyone or not models:
        pytest.skip("no scored table in this checkout")

    assert max(everyone.values()) - min(everyone.values()) > max(models) - min(models), (
        "the two populations no longer differ, so this test proves nothing; "
        "check whether the therapist row is still drawn"
    )
    effects = {e["judge"]: e for e in (data.preference or {}).get("effects", [])}
    entry = effects.get(figures.JUDGE_A)
    if not entry:
        pytest.skip("no preference payload in this checkout")
    wide = entry["estimate"] / (max(everyone.values()) - min(everyone.values()))
    assert f"these effects are {wide:.0%} and" not in prose, (
        "the share is divided by a range that includes the therapist-written note "
        "and the two dated reference models, which halves the effect the section "
        "exists to report"
    )


def test_the_judge_versus_judge_interval_is_the_published_one(prose, data):
    """The interval that was 2.5 times narrower than the payload's.

    It is the sentence that tells a reader neither judge is the more partial
    one; a narrower interval makes that claim sound better established than it
    is, which is the direction that matters.
    """
    difference = (data.preference or {}).get("difference")
    if not difference:
        pytest.skip("no judge-versus-judge estimate in this checkout")

    stated = (
        f"{brief.signed(difference['estimate'])} "
        f"[{brief.signed(difference['low'])}, {brief.signed(difference['high'])}]"
    )
    assert stated in prose


# --- and the claim the document makes about itself ----------------------------


def test_the_document_does_not_tell_the_reader_not_to_check(prose):
    """The sentence that made every number above it unauditable by assertion.

    Kept as a test rather than only as a fix, because the sentence is the kind a
    writer reaches for: flattering, short, and false in a way that only reading
    the file would show.
    """
    assert "Nothing was typed in" not in prose
    assert "The prose around them is written by hand." in prose


def test_the_document_counts_the_files_it_reads(prose):
    """It said two, then four. `Data.load` reads three -- the payload and the two
    saturation files -- and `brief.py` opens two more of its own,
    `calibration.json` and `corpus-profile.json`. Five.
    """
    for name in (
        "leaderboard.json",
        f"saturation-{figures.JUDGE_A}.json",
        f"saturation-{figures.JUDGE_B}.json",
        "calibration.json",
        "corpus-profile.json",
    ):
        assert name in prose, f"{name} is not named in the section that says how to check"
    assert "Five files rather than two" in prose


def test_every_file_the_document_names_is_one_a_reader_can_open(prose):
    """A section headed "how to check" that names a file without linking it.

    Six published files were named as code spans and none but the leaderboard
    was a link: the two saturation files, `calibration.json`,
    `corpus-profile.json`, `judges.json` and `models-snapshot.md`. The
    instruction to check was given without the means.
    """
    named = set(re.findall(r"docs/([a-z0-9.\-]+\.(?:json|md))", prose))
    named |= set(re.findall(r"<code>([a-z0-9.\-]+\.(?:json|md))</code>", prose))
    linked = set(re.findall(r'href="([^"]+)"', prose))
    missing = sorted(name for name in named if name not in linked)
    assert not missing, (
        "named in the document and not linked from it, so a reader cannot open "
        f"what they are told to check: {missing}"
    )


def test_the_document_never_calls_completeness_a_fraction_of_23(prose):
    """The headline figure's own subtitle said it, 68 lines under the prose that denies it.

    Completeness is the equal-weighted mean of four section fractions over
    sections holding 6, 5, 8 and 4 criteria. The two readings differ by more
    than the gap between adjacent rows in the chart the caption sat on, so a
    reader who did the arithmetic the caption invited got a different table.
    Checked against the rendered document, figures included, because the
    sentence was inside an inlined SVG and no test of `brief.py` could see it.
    """
    for wrong in ("fraction of 23", "fraction of all 23 criteria", "half of them"):
        assert wrong not in prose, (
            f"{wrong!r} is back. Completeness is the equal-weighted mean of the "
            "four section fractions; see docs/methodology.md."
        )


def test_trace_is_labelled_a_re_implementation_wherever_it_appears(prose):
    """`landscape.md` states the practice as a fact, and this page broke it.

    "Our TRACE implementation is therefore a re-implementation with no human
    anchor, and is labelled as such everywhere it appears." The brief carried
    only the second half, and then asserted the labelling rule in a sentence the
    page itself falsified.
    """
    if "TRACE" not in prose:
        pytest.skip("this document does not draw TRACE")
    assert "re-implementation" in prose, (
        "TRACE is named without the word `re-implementation`, on a page that "
        "claims the label is applied wherever it appears"
    )


def test_the_document_says_when_its_numbers_were_scored(prose, data):
    """Undated, the PDF printed from it drifted three days without saying so."""
    assert f"scored {data.scored}" in prose, (
        f"the page does not carry its scoring date ({data.scored}), so a reader "
        "holding the page and the PDF cannot tell which is newer"
    )
