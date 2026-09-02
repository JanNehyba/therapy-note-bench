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

Six more sentences joined it on 2026-09-03, and they are why the promise is
worth making. Two systems joined the payload and every hand-typed count in the
document stayed where it was: the lede said sixteen models where eighteen had
written notes; the front-page card sized the production gap at 0.00-0.55 where
the column now runs to 0.73; the looking-back sentence said "fourteen of
sixteen"; the TRACE paragraph quoted an agreement of +0.83 over 16 systems
where the payload own concordance says +0.77 over 18; and the drop-one sentence
quoted a GPT effect of +0.027 that contradicted the table two paragraphs above
it. Every test in this file passed throughout, because none of them named these
sentences. They are computed now, and each has a test below.
"""

from __future__ import annotations

import collections
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
    saturation files -- and `brief.py` opens more of its own:
    `calibration.json`, `corpus-profile.json`, and `repeatability.json` where
    the repeat run has published one.

    The count is taken from the list rather than asserted, because "Five files
    rather than two" was typed under a list of five and stayed five when the
    document began reading a sixth.
    """
    expected = [
        "leaderboard.json",
        f"saturation-{figures.JUDGE_A}.json",
        f"saturation-{figures.JUDGE_B}.json",
        "calibration.json",
        "corpus-profile.json",
    ]
    if (DOCS / "repeatability.json").exists():
        expected.append("repeatability.json")
    for name in expected:
        assert name in prose, f"{name} is not named in the section that says how to check"
    assert f"{brief.spelled(len(expected)).capitalize()} files rather than two" in prose


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


def test_every_artefact_the_document_links_is_a_file_the_site_publishes(prose):
    """A link in the "how to check" section that 404s is worse than no link.

    The section hands over six files it reads and three it does not -- the
    per-track dominance tests, which are where "beats outright" is decided
    rather than eyeballed. Every one of those paths is written by hand in the
    template, and a reader following a broken one has been told to check
    something they cannot open.
    """
    linked = {
        href
        for href in re.findall(r'href="([^"]+)"', prose)
        if not href.startswith("http") and href.endswith((".json", ".md"))
    }
    assert linked, "the document links no artefact at all"
    missing = sorted(href for href in linked if not (DOCS / href).exists())
    assert not missing, f"linked from the briefing and not published beside it: {missing}"


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


# --- the counts that grew when the payload did --------------------------------
#
# Every one of these was a word or a number typed beside the prose it belonged
# to, and every one of them was still there a week after the payload it
# described had changed underneath it.


def test_the_lede_counts_the_models_it_says_wrote_the_notes(prose, data):
    """ "Sixteen models wrote psychotherapy session notes." Eighteen did.

    The first sentence of the document, and the first sentence of the PDF that
    leaves this repository. It was written when sixteen was right and had no
    way of hearing that two more had been scored.
    """
    models = [row for row in data.rows(TRACK, figures.JUDGE_A) if row.get("system_type") == "model"]
    assert f"{brief.spelled(len(models)).capitalize()} models wrote" in prose


def test_the_production_gap_card_spans_the_column_it_names(prose, data):
    """The headline a reader takes from page one, against the column itself.

    It said 0.00-0.55 while the best system answered the looking-forward
    section in eight sessions of eleven, which is 0.73 -- a third of the
    published range missing from the number the card exists to give.
    """
    forward = [
        row["headline"]["temporal_next"]
        for row in data.rows("icare", figures.JUDGE_A)
        if row["headline"].get("temporal_next") is not None
    ]
    assert forward, "no looking-forward column in this payload"
    assert f"{min(forward):.2f}–{max(forward):.2f}" in prose


def test_both_temporal_denominators_come_from_the_corpus_profile(prose):
    """How often the experts themselves answered each of the two sections.

    Neither number is about a model: they are what the corpus contains, and
    every temporal figure on the page is a fraction of them.
    """
    back, forward = brief.temporal_fields(brief.corpus_profile())
    assert back and forward, "corpus-profile.json no longer marks the two temporal sections"
    assert f"all {brief.spelled(back)} sessions the experts answered" in prose
    assert f"the {brief.spelled(forward)} sessions where an expert did" in prose
    assert f"{brief.spelled(forward)} sessions where an expert did. Both columns" in prose


def test_the_looking_back_sentence_counts_the_models_that_answered_every_session(prose, data):
    """ "Fourteen of sixteen on all thirty-four sessions", when it was sixteen of eighteen.

    Two of the three numbers in one clause went stale together, and the clause
    is the evidence for the claim the section opens with -- that the
    looking-back field is the one models do reliably fill.
    """
    back = [
        row["headline"]["temporal_past"]
        for row in data.rows("icare", figures.JUDGE_A)
        if row["headline"].get("temporal_past") is not None
    ]
    assert back, "no looking-back column in this payload"
    complete = [value for value in back if value >= 1.0]
    assert f"{brief.spelled(len(complete))} of {brief.spelled(len(back))} on all" in prose


def test_the_looking_forward_sentence_is_the_best_system_counted(prose, data):
    """ "Just over half" described a system managing eight sessions of eleven."""
    _, asked = brief.temporal_fields(brief.corpus_profile())
    forward = [
        row["headline"]["temporal_next"]
        for row in data.rows("icare", figures.JUDGE_A)
        if row["headline"].get("temporal_next")
    ]
    assert forward and asked, "no looking-forward column in this payload"
    best = brief.spelled(round(max(forward) * asked))
    assert f"manages it in {best} of the {brief.spelled(asked)} sessions" in prose
    assert "just over half" not in prose, (
        "a fraction in words, which cannot go stale visibly: the column it "
        "described has moved twice"
    )


def test_the_trace_agreement_is_the_one_the_payload_computed(prose, data):
    """ "+0.83 and place 11 of 16 systems differently", against +0.77 over 18.

    The same two judges, the same measure, and a figure the payload has
    computed for every page since the concordance was added. The brief quoted
    its own, from a run two systems ago.
    """
    measure = next(
        (
            entry
            for entry in data.concordance.get("icare", {}).get("measures", [])
            if entry.get("measure") == "trace" and entry.get("rankable")
        ),
        None,
    )
    if not measure:
        pytest.skip("this payload gives no rankable TRACE agreement")
    assert (
        f"correlate at {measure['rho']:+.2f} and place "
        f"{measure['moved']} of {measure['n_systems']} systems differently" in prose
    )


def test_the_two_trace_ranges_are_stated_once_and_restated_from_the_same_numbers(prose, data):
    """ "6% against 13%" was typed under the two percentages it repeats.

    Correct when written and one payload from being wrong. The paragraph that
    tells a reader the two judges disagree about how much room is left is the
    one place the two numbers have to match.
    """
    shares = []
    for judge in (figures.JUDGE_A, figures.JUDGE_B):
        values = [
            row["headline"]["trace"]
            for row in data.rows("icare", judge)
            if row["headline"].get("trace") is not None
        ]
        if not values:
            pytest.skip("no TRACE column in this payload")
        shares.append(f"{(max(values) - min(values)) / 4:.0%}")
    assert f"{shares[0]} against {shares[1]}" in prose


def test_the_drop_one_sentence_is_the_published_leave_one_out(prose, data):
    """ "Takes the GPT one from +0.027 to +0.018", under a table printing +0.017.

    The one stale number in this document that contradicted another number on
    the same page. It was hand-computed in a terminal, and `docs/methodology.md`
    -- recomputed over the current payload and edited alone -- had said +0.011
    for a week. `docs/preference.json` carries the leave-one-out now.
    """
    effects = {entry["judge"]: entry for entry in (data.preference or {}).get("effects", [])}
    if not effects:
        pytest.skip("no preference payload in this checkout")

    seen = 0
    for judge in (figures.JUDGE_A, figures.JUDGE_B):
        entry = effects.get(judge)
        lean = (entry or {}).get("leans_on")
        if not entry or not lean:
            continue
        seen += 1
        assert f"<code>{lean['system']}</code>" in prose
        stated = (
            f"takes the {brief.family_word(entry['family'])} figure from "
            f"{brief.signed(entry['estimate'])} to {brief.signed(lean['estimate'])}"
        )
        assert stated in prose, f"the drop-one clause for {judge} is not the published one"
    assert seen, "the payload carries no leave-one-out for either judge"


# --- the judge asked the same question twice ----------------------------------


@pytest.fixture(scope="module")
def repeats() -> dict:
    found = brief.repeatability()
    if not found or not found.get("judges"):
        pytest.skip("no repeat run published in this checkout")
    return found


def test_the_repeat_panel_quotes_the_published_counts(prose, repeats):
    """Every number in the panel, against `docs/repeatability.json`.

    The section exists because agreement with a therapist is only half of
    whether an instrument is any good, and the other half had no number
    anywhere on this page while every table on the site is a mean of answers
    taken once.
    """
    for judge in repeats["judges"]:
        asked, same = judge["questions"], judge["same"]
        assert f"<code>{judge['judge_model']}</code>" in prose
        assert f'<td class="num">{asked}</td>' in prose, (
            f"{judge['judge_model']} does not print how many questions were re-asked"
        )
        assert f"{same} ({brief.pct(same, asked)})" in prose
        assert f"{brief.pct(asked - same, asked)}" in prose


def test_the_repeat_panel_names_the_instrument_that_repeated_worst(prose, repeats):
    """An aggregate stays healthy long after its parts have died -- the same
    lesson the saturation section states, applied to the judge itself. One of
    these judges repeats itself on 90% of the rubric and 76% of TRACE.
    """
    for judge in repeats["judges"]:
        tracks = [track for track in judge.get("tracks", []) if track["questions"]]
        if not tracks:
            continue
        worst = min(tracks, key=lambda track: track["same"] / track["questions"])
        assert f"{brief.pct(worst['same'], worst['questions'])}" in prose


def test_the_repeat_panel_says_how_narrow_its_evidence_is(prose, repeats):
    """Five notes, one system. Published at that size with the size in the
    sentence, which is the condition on publishing it at all.
    """
    assert f"{brief.spelled(repeats['notes'])} notes per instrument" in prose
    for system in repeats.get("systems", []):
        assert f"<code>{system}</code>" in prose, (
            "the panel does not name the system whose notes were re-judged, so a "
            "reader cannot see how narrow the probe is"
        )
    assert "does not sample the field" in prose


def test_the_repeat_panel_does_not_promise_a_column_moves_by_its_rate(prose, repeats):
    """The inference the number invites, and which nothing here supports.

    A mean over dozens of answers cancels most of what the individual answers
    do. How much is left was not measured, and a section that let a reader
    carry 12% into a table would be worse than no section.
    """
    assert "It does not say a column moves by that much" in prose


def test_the_claim_about_the_less_repeatable_judge_matches_the_calibration(
    prose, repeats, calibration
):
    """Made only when the two orderings actually agree.

    Today the judge that agrees with the therapists less is also the judge that
    agrees with itself less. That is one re-calibration from being backwards,
    so the sentence is built from the comparison rather than typed.
    """
    rates = {
        judge["judge_model"]: judge["same"] / judge["questions"]
        for judge in repeats["judges"]
        if judge["questions"]
    }
    published = json.loads((DOCS / "judges.json").read_text(encoding="utf-8"))["judges"]
    anchored = {}
    for entry in published:
        if entry["judge_model"] not in rates:
            continue
        found = [a for a in entry["agreements"] if a["name"] == "rubric_completeness"]
        if found:
            anchored[entry["judge_model"]] = found[0]["judge"]

    claim = (
        "the one that agrees with the therapists less is also the one that agrees with itself less"
    )
    if len(anchored) == 2 and min(rates, key=rates.get) == min(anchored, key=anchored.get):
        assert claim in prose
    else:
        assert claim not in prose, (
            "the two orderings no longer agree, so the sentence claiming they do is backwards"
        )


# --- the second instrument, counted the way the first one is ------------------


@pytest.fixture(scope="module")
def pdsqi(data) -> dict[str, dict]:
    """The largest tie in every PDSQI column, per judge, recomputed here.

    Counted from the drawn rows rather than through `brief.flat_columns`: a
    test that builds its expectation with the code it checks agrees with it by
    construction, which this file has been caught doing once already.
    """
    if ("pdsqi-soap", figures.JUDGE_A) not in data.tables:
        pytest.skip("no PDSQI table in this payload")

    found = {}
    for judge in (figures.JUDGE_A, figures.JUDGE_B):
        rows = data.rows("pdsqi-soap", judge)
        columns = {}
        for measure in sorted(rows[0].get("headline", {})):
            values = [
                row["headline"][measure] for row in rows if row["headline"].get(measure) is not None
            ]
            if not values:
                continue
            top = collections.Counter(values).most_common(1)[0]
            columns[measure] = {"value": top[0], "tie": top[1], "scored": len(values)}
        found[judge] = columns
    return found


def _flat(columns: dict[str, dict]) -> dict[str, dict]:
    """The columns where more than half the systems print one number.

    The same line `tnb.scoring.concordance.MeasureAgreement.rankable` draws:
    below it, a measure cannot order the systems whatever the remainder does.
    """
    return {name: entry for name, entry in columns.items() if entry["tie"] * 2 > entry["scored"]}


def test_the_flat_pdsqi_columns_are_named_and_counted_from_the_payload(prose, pdsqi):
    """Four of PDSQI-9's eight columns give one number to twenty of twenty-one
    systems. The document introduced this instrument as the wider one -- "and it
    is run over the same notes here, reaching eight" -- and never said how many
    of the eight tell any two systems apart.
    """
    worst = max(pdsqi, key=lambda judge: len(_flat(pdsqi[judge])))
    flat = _flat(pdsqi[worst])
    if not flat:
        pytest.skip("no flat PDSQI column under either judge")

    columns = len(pdsqi[worst])
    assert (
        f"{brief.spelled(len(flat)).capitalize()} of the second instrument&rsquo;s "
        f"{brief.spelled(columns)} columns separate nobody" in " ".join(prose.split())
    )
    assert f"the answer under <code>{worst}</code> is {brief.spelled(columns - len(flat))}" in prose
    for name in flat:
        assert f"<em>{name}</em>" in prose, f"{name} is flat and the document does not name it"


def test_the_size_of_the_tie_is_the_published_one(prose, pdsqi):
    """ "One number to 20 of the 21 systems" -- both halves from the table."""
    worst = max(pdsqi, key=lambda judge: len(_flat(pdsqi[judge])))
    flat = _flat(pdsqi[worst])
    if not flat:
        pytest.skip("no flat PDSQI column under either judge")
    widest = max(flat.values(), key=lambda entry: (entry["tie"], entry["scored"]))
    assert f"one number to {widest['tie']} of the {widest['scored']} systems" in prose


def test_the_shared_value_is_stated_where_the_columns_share_one(prose, pdsqi):
    """All four at 5.00, which is the top of the scale and the whole point.

    A column at the ceiling is a thing a note can fail, not a way to choose
    between notes -- the same trap the front page states for `accurate` and
    `succinct` on an empty note.
    """
    worst = max(pdsqi, key=lambda judge: len(_flat(pdsqi[judge])))
    flat = _flat(pdsqi[worst])
    values = {entry["value"] for entry in flat.values()}
    if len(values) != 1:
        pytest.skip("the flat columns no longer share one value")
    assert f"at {values.pop():.2f}, the top of the scale" in prose


def test_the_other_judge_is_compared_rather_than_assumed(prose, pdsqi):
    """Three of the four are flat under one judge only.

    Which makes the count a fact about the pair, and a sentence that said "the
    instrument is saturated" would be wrong about the second judge's table.
    """
    worst = max(pdsqi, key=lambda judge: len(_flat(pdsqi[judge])))
    other = next(judge for judge in pdsqi if judge != worst)
    both = sorted(set(_flat(pdsqi[worst])) & set(_flat(pdsqi[other])))
    if not _flat(pdsqi[worst]):
        pytest.skip("no flat PDSQI column under either judge")

    if both:
        assert f"Under <code>{other}</code> {brief.spelled(len(both))} of them" in prose
        for name in both:
            assert f"<em>{name}</em>" in prose
    else:
        assert f"Under <code>{other}</code> none of them is flat" in prose


def test_the_self_preference_card_is_the_rounded_pair(prose, data):
    """ "+0.02" on the front page, from two effects that could move apart.

    They are +0.018 and +0.017 today and round to one number, which is why the
    card could be typed and stay right. This repository has published a
    "detected" verdict on this panel and withdrawn it; the card should not be
    the last thing left saying the old number.
    """
    effects = (data.preference or {}).get("effects", [])
    if not effects:
        pytest.skip("no preference payload in this checkout")
    expected = "/".join(sorted({f"{entry['estimate']:+.2f}" for entry in effects}))
    assert f'<div class="figure">{expected}<small>each judge' in prose


def test_the_calibration_corpus_is_counted_once(prose, calibration):
    """ "TN-Eval released 150 notes" and "measured across 150 of those notes"
    are the same number, and one of them was typed.
    """
    assert f"TN-Eval released {calibration['notes']} notes" in " ".join(prose.split())
    assert f"across {calibration['notes']} of those notes" in prose
