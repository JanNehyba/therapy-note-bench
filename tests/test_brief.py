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
    """
    preference = data.preference or {}
    effects = {entry["judge"]: entry for entry in preference.get("effects", [])}
    if not effects:
        pytest.skip("no preference payload in this checkout")

    shares = []
    for judge in (figures.JUDGE_A, figures.JUDGE_B):
        entry = effects.get(judge)
        scores = data.scores(TRACK, judge, RANKING)
        if not entry or not scores:
            continue
        width = max(scores.values()) - min(scores.values())
        shares.append(f"{entry['estimate'] / width:.0%}")

    assert f"these effects are {' and '.join(shares)} of the range" in prose
    assert "a fiftieth" not in prose


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
    """It said two. Data.load reads three, and the judges table a fourth."""
    for name in ("leaderboard.json", "saturation-*.json", "calibration.json"):
        assert name in prose
    assert "Four files rather than two" in prose
