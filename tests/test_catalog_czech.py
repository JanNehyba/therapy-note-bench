"""The Czech text of the candidate catalog.

The audit of 2026-09-15 found the criteria map in three unconnected places, one
of them a Czech working catalog on a single machine, and fixed it by making
`catalog.json` the one record. On 2026-10-13 the Czech text turned out to have
drifted back into the same shape: no tracked file held a Czech name for a single
criterion, nine view generators in a session-scoped temp directory held them
instead, and five views claimed five different numbers of criteria.

`czech.json` puts that text back under the catalog. It translates and groups;
it adds no candidate and removes none, which is the difference between a
translation and a second catalog.

The panel rating sheet is generated from it, and that is why the Czech had to be
rescued rather than rewritten: the sheet shows items in a shuffled order drawn
from a seed recorded before the first answer, so a sheet nobody can rebuild is a
sheet whose answers nobody can check.

Pinned here: it validates, it names exactly the catalog's codes, the statement
and the question are kept apart, partial coverage is counted rather than
guessed, the file carries no path, no secret and no CRLF, and the sheet is
blind, stable and refused outright when the data behind it has drifted.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CATALOG_DIR = REPO / "research" / "gen2" / "catalog"
CZECH_PATH = CATALOG_DIR / "czech.json"


def _module(name: str):
    spec = importlib.util.spec_from_file_location(name, CATALOG_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


catalog_mod = _module("catalog")
panel_sheet = _module("panel_sheet")
render_cs = _module("render_catalog_cs")


@pytest.fixture(scope="module")
def catalog() -> dict:
    return catalog_mod.load()


@pytest.fixture(scope="module")
def czech() -> dict:
    return catalog_mod.load_czech()


def test_the_czech_text_validates(catalog, czech):
    assert catalog_mod.czech_problems(catalog, czech) == []


def test_it_names_exactly_the_catalog_codes(catalog, czech):
    """A Czech view may not be a second list of criteria.

    This is the 2026-09-15 finding, which cost five views claiming 36, 34, 33,
    17 and 16 criteria. The count lives in one file and the Czech text is held
    to it.
    """
    assert set(czech["candidates"]) == set(catalog_mod.ids(catalog, "candidates"))
    assert len(czech["candidates"]) == 48


def test_a_candidate_cannot_reach_a_sheet_without_a_name_and_a_statement(czech):
    for code, entry in czech["candidates"].items():
        assert entry["name"].strip(), code
        assert entry["statement"].strip(), code


def test_the_statement_and_the_question_are_not_the_same_field(czech):
    """What a panel marks is not what a reader is asked.

    The harvest first treated these as one field with 34 disagreements. They
    came from different generators for different sheets: a panel sheet states a
    proposition to agree or disagree with, a table asks. Merging them would have
    left the panel rating interrogatives, so the split is pinned by the shape of
    the text itself.
    """
    statements = [e["statement"] for e in czech["candidates"].values()]
    questions = [e["question"] for e in czech["candidates"].values() if "question" in e]
    assert len(statements) == len(czech["candidates"])
    assert not [s for s in statements if s.rstrip().endswith("?")]
    assert sum(1 for q in questions if q.rstrip().endswith("?")) >= len(questions) - 1
    assert czech["statement_and_question_are_not_variants"]


def test_partial_coverage_is_counted_and_the_gaps_are_named(catalog, czech):
    """A field no generator filled is a gap with a list, not a blank.

    K35 and K36 were added on 2026-10-07, after the last generator ran, so they
    have no question and no unit. K34, K35 and K36 have nothing that says how
    they are measured or why they are not. Writing those sentences now would
    invent a reason for a decision this file was not present for, so the
    coverage block lists them.
    """
    coverage = czech["coverage"]
    assert coverage["candidates"] == 48
    assert coverage["by_field"]["name"] == coverage["by_field"]["statement"] == 48
    # K35 and K36 were added on 2026-10-07, after the last generator ran, so they
    # have no question and no unit. K37 to K39 were written on 2026-10-14 with
    # both, which is why they are not in these lists.
    assert coverage["missing_by_field"]["question"] == ["K35", "K36"]
    # The language layer of 2026-10-23 carries a question and no unit: every one
    # of the nine is judged over one note, which the catalog records, and the
    # Czech word for it was not written for them.
    assert coverage["missing_by_field"]["unit"] == ["K35", "K36"] + [f"K4{n}" for n in range(9)]
    assert coverage["candidates_with_no_explanation_of_their_state"] == ["K34", "K35", "K36"]
    assert coverage["candidates_with_no_explanation_note"]


def test_every_resolved_conflict_says_what_it_rejected(czech):
    """Five names and twelve questions were worded differently in two places.

    The file keeps one and records the other with the generator it came from.
    A silent merge would leave nobody able to see that a choice was made.

    A resolution can also be overtaken. K31's name was settled between two
    generators and then changed on 2026-10-22 for a different reason: it named
    the defect where the sheet asks about a property. The record keeps what was
    resolved on the day and says it no longer holds, which rewriting `kept`
    would have erased -- and it may say so only where the entry records the
    rewording, so it cannot quietly excuse a drift.
    """
    conflicts = czech["conflicts_resolved"]
    assert conflicts
    for entry in conflicts:
        candidate = czech["candidates"][entry["candidate"]]
        kept = candidate[entry["field"]]
        if entry.get("superseded_on"):
            assert candidate["reworded_on"] == entry["superseded_on"], entry["candidate"]
            assert candidate["previous_wording"][entry["field"]] == entry["kept"]["text"]
            assert len(entry["superseded_why"].split()) >= 10
        else:
            assert entry["kept"]["text"] == kept
        assert entry["kept"]["from"]
        assert entry["rejected"]
        for rejected in entry["rejected"]:
            assert rejected["from"] and rejected["text"]
            assert rejected["text"] != kept
    fields = {entry["field"] for entry in conflicts}
    assert fields <= set(czech["precedence"]["by_field"])


#: Fields computed from catalog.json rather than written or harvested, so they
#: carry no provenance: the catalog is their provenance and they change when it
#: does. `ranking_role` says whether a criterion may order models and
#: `needs_bank` whether it needs the information bank, and both are derived by
#: research/gen2/catalog/ranking_role.py from what decides the criterion's answer.
DERIVED_FIELDS = {"ranking_role", "needs_bank"}

#: Fields that record what happened to an entry rather than what it says, so
#: they carry no generator either. K18's Czech question was reworded on
#: 2026-10-14 because it could not be told apart from K01's, and the entry keeps
#: the date, the reason and the previous wording beside the new one: a criterion
#: whose question changed silently is a criterion nobody can audit.
HISTORY_FIELDS = {"reworded_on", "why_reworded", "previous_wording"}

#: Fields written for this file rather than harvested from a generator, so their
#: provenance is a date and not a filename. `plain` is the one sentence that says
#: what a criterion is, written on 2026-10-15 because the catalog had a formal
#: definition for every candidate and no sentence a reader could start from;
#: `example` is its negative example from catalog.json, translated. Both are
#: still required to say when they were written: text that appears on a page
#: with no record of where it came from is how a working note becomes a claim.
AUTHORED_FIELDS = {"plain", "example", "example_positive"}


def test_every_field_says_which_generator_it_came_from(czech):
    known = set(czech["precedence"]["by_field"])
    for code, entry in czech["candidates"].items():
        provenance = entry["from"]
        expected = set(entry) - {"from"} - DERIVED_FIELDS - HISTORY_FIELDS
        assert set(provenance) == expected, code
        for field, filename in provenance.items():
            if field in AUTHORED_FIELDS:
                assert "2026-" in filename, (code, field, filename)
                continue
            assert field in known, (code, field)
            if filename == czech["authored_here"]:
                # Written for this file rather than harvested from a generator.
                # The three criteria accepted on 2026-10-14 postdate every
                # generator, so there was nothing to harvest.
                assert code in czech["authored_here_candidates"], (code, field)
                continue
            assert filename in czech["precedence"]["by_field"][field], (code, field)


def test_a_grouping_is_not_a_translation_and_says_so(catalog, czech):
    """The groupings are claims about the criteria and cover fewer of them.

    One maps a candidate onto a prior commercial taxonomy and the other is this
    project's grouping of the measured ones. Both predate K35 and K36. The gap
    is named rather than filled, and the note has to say which kind of thing
    these are, or a later reader takes a claim for a label.
    """
    codes = set(catalog_mod.ids(catalog, "candidates"))
    for name, groups in czech["groupings"].items():
        placed = [code for members in groups.values() for code in members]
        assert set(placed) <= codes, name
        assert len(placed) == len(set(placed)), name
        assert len(placed) < len(codes), name
    assert "not" in czech["groupings_note"]


def test_the_file_is_public_safe():
    text = CZECH_PATH.read_text(encoding="utf-8")
    assert "C:\\" not in text and "/Users/" not in text and "local/" not in text
    assert not re.search(r"(?i)(api[_-]?key|token)\s*[:=]\s*\S{8,}", text)
    assert b"\r\n" not in CZECH_PATH.read_bytes()


def test_it_declares_what_it_is(czech):
    """The allow-list in tests/test_no_clinical_content.py opens a door for
    Czech in a tracked file; the marker is what stops something else walking
    through it."""
    assert czech["marker"] == "AUTHORED-INSTRUMENT-TEXT"
    assert czech["version"] == "catalog-czech-v1"
    assert czech["what_this_is"] and czech["why_it_exists"] and czech["harvested_from"]


# --- the panel sheet that is generated from it -----------------------------


@pytest.fixture(scope="module")
def codes(catalog) -> list[str]:
    return catalog_mod.ids(catalog, "candidates")


def test_the_sheet_has_one_row_per_candidate(catalog, czech, codes):
    table = panel_sheet.rows(czech, codes, catalog)
    items = [row for row in table if row and re.fullmatch(r"K\d\d", row[0])]
    assert len(items) == len(codes) == 48
    assert {row[0] for row in items} == set(codes)
    units = czech["vocabulary"]["unit_of_analysis"]
    # The column names the unit of the property, which for one candidate is not
    # the unit its measurement is computed over; the test above holds that
    # override to its reason.
    overrides = czech["panel_sheet"]["judged_over_overrides"]
    judged = {
        c["id"]: units[overrides.get(c["id"], {}).get("unit", c["unit_of_analysis"])]
        for c in catalog["candidates"]
    }
    for code, name, statement, example, over, *answers in items:
        assert name == czech["candidates"][code]["name"]
        assert statement == czech["candidates"][code]["statement"]
        # One example, and the failing one. A pair of them -- this way, not
        # that way -- was two cells of reading for every criterion and the
        # investigator cut it. The positive half of a criterion written as the
        # absence of a fault reads as an ordinary sentence anyway: "the client
        # did not come to three sessions" says nothing about stigmatising
        # language.
        entry = czech["candidates"][code]
        assert example == entry["example"], code
        # What the property is judged over. The sheet did not say until
        # 2026-10-21, and three of the thirty-nine are not about one note at
        # all, so for those three the rater was answering about a single note,
        # which is a question nobody had asked.
        assert over == judged[code], code
        # Two cells to fill: the relevance answer and an optional note. The
        # harm question was a third until 2026-10-22, when it moved under the
        # table: thirty-nine cells of which thirty-eight stay empty is a lot of
        # attention for a question most rows have no answer to.
        assert answers == ["", ""], code
    assert len({judged[code] for code in codes}) == 3, "all three units reach the sheet"


def test_no_text_on_the_sheet_states_how_many_criteria_it_holds(catalog, czech, codes):
    """The one artefact of this project that goes to people outside it.

    An instruction read "Nize je 36 vlastnosti" while the sheet listed 39: true
    on 2026-10-07, false from 2026-10-14 when three criteria arrived, and held
    by nothing. It was repaired by filling the count from the list it counts,
    and on 2026-10-22 the sentence went altogether with the rest of the
    preamble. A count that no text states cannot go stale, so what is checked
    now is that none does: the rows are the only statement of how many there
    are.
    """
    table = panel_sheet.rows(czech, list(codes), catalog)
    # The sheet carries blank separator rows, so a row may be empty.
    items = [row for row in table if row and row[0] in set(codes)]
    assert len(items) == len(codes)

    everything = [
        cell
        for rows in (table, panel_sheet.legend(czech, list(codes)))
        for row in rows
        for cell in row
        if cell
    ]
    for line in everything:
        for near in range(len(codes) - 6, len(codes) + 7):
            # Not inside a criterion code: K42 to K48 are names, not counts.
            found = re.search(rf"(?<!K){near}", line)
            assert not found, f"a count of criteria is typed into {line[:60]!r}"


def test_the_sheet_is_blind(catalog, czech, codes):
    """A rater who can see the state or the citation ratifies instead of judging.

    The sheet carries a code, a name and a statement. Nothing in it says whether
    a criterion is measured, where it came from, or who proposed it: the panel is
    asked what matters for a session note, not whether this project was right.
    """
    table = panel_sheet.rows(czech, codes, catalog)
    text = "\n".join("\t".join(row) for row in table)
    for candidate in catalog["candidates"]:
        assert candidate["state"] not in text
        assert candidate["origin"] not in text
        assert candidate["family"] not in text
        assert candidate["label"] not in text
    for source in catalog["sources"]:
        assert source["key"] not in text


def test_every_step_of_the_scale_reaches_the_sheet_with_what_it_means(catalog, czech, codes):
    """Four words with no definition measure agreement on vocabulary.

    The sheet carried "nepodstatne / malo podstatne / podstatne / velmi
    podstatne" and nowhere a sentence saying what any of them meant, so three
    people would have been scored for agreeing on four adjectives. Each step now
    carries an anchor, the anchors live in the data beside the labels, and the
    sheet builds them from there rather than spelling them out twice.
    """
    scale = czech["vocabulary"]["relevance_scale"]
    assert len(scale) == 4
    # The anchors moved off the rating tab on 2026-10-22 with the rest of the
    # preamble: twenty-nine rows stood between a therapist and the first
    # criterion, and most of them were written for somebody else. They are on
    # the Legend tab, which is what a rater reads while answering.
    text = "\n".join("\t".join(row) for row in panel_sheet.legend(czech, codes))
    for step in scale:
        assert step["label"] in text, step["label"]
        assert len(step["anchor"].split()) >= 8, step["label"]
        assert step["anchor"] in text, step["label"]
    # The cut is the top two of the four, asserted by position so that this
    # file needs no Czech of its own and no exception from the checker that
    # looks for it.
    essential = [step["label"] for step in scale if step["counts_as_essential"]]
    assert essential == [step["label"] for step in scale[-2:]]
    assert all(label in text for label in essential), "the cut is named on the legend"


def test_the_harm_question_is_asked_once_with_an_example(catalog, czech, codes):
    """A rule with teeth needs an input, and the input is one box with a worked case.

    Any criterion the answer identifies stays unmeasured this round whatever its
    relevance, so the question cannot simply disappear. It was a column of
    thirty-nine cells until 2026-10-22, thirty-eight of which would have stayed
    empty, and the investigator refused both that and the invented example that
    explained it: a model graded on non-stigmatising language does not stop
    recording risk, because recording risk is not stigmatising language.

    What replaces it is one box under the table and the case this project
    documented itself: a one-sentence note scores 1.00 on economy, so grading
    economy alone rewards writing almost nothing.

    On the same day the question lost its harm clause and its instruction to
    write the criterion's code, at the investigator's word (D26). Asking for the
    code again is a change to the rule that reads the answer, not a wording
    choice, so this test holds the sheet to not asking.
    """
    sheet = czech["panel_sheet"]
    table = panel_sheet.rows(czech, codes, catalog)
    header = sheet["header"]
    assert len(header) == 7, "code, name, statement, example, unit, answer, note"

    under = [row[0] for row in table[table.index(list(header)) + len(codes) + 1 :] if row]
    asked = "\n".join(under)
    # Three open questions under the table, not one: what the list is missing,
    # which two criteria are the same thing, and how a good mark could be had
    # without the note deserving it.
    assert sum("?" in line for line in under) >= 4

    # The worked example is the criterion this project documented the trap on:
    # a one-sentence note scores 1.00 on economy.
    assert czech["candidates"]["K11"]["name"] in asked
    # A question under the table does ask for a criterion's code, and since
    # 2026-10-22 it is the duplicates one rather than the harm one: the harm
    # instruction was cut and the protocol's harm flag weakened to match, so
    # that rule reads prose and claims no machine-readable input.
    assert header[0].lower() in asked.lower()
    # Which is why the cut has to stay recorded. The guard below proves the
    # sentence is off the sheet; this proves the guard still has it to look for,
    # because deleting the record would make the guard pass over an empty set.
    retired = [
        record
        for record in sheet["superseded_instructions"]
        if header[0].lower() in record["text"].lower()
    ]
    assert retired, "nothing records an instruction that asked for the code"

    # The column's header and its legend block are gone, recorded with the
    # date, and may not come back onto a built sheet.
    everything = "\n".join(
        cell for rows in (table, panel_sheet.legend(czech, codes)) for row in rows for cell in row
    )
    gone = [r for r in sheet["superseded_instructions"] if r["until"] == "2026-10-22"]
    assert gone
    for record in gone:
        assert record["text"] not in everything


def test_the_column_says_what_the_property_is_about_not_what_measures_it(catalog, czech, codes):
    """K28 told a rater its property was about a model across clients.

    Whether a note says anything specific about this client is a property of
    that one note. Only detecting genericness needs a system's whole output,
    because it is found by comparing a model's notes with each other, and
    `catalog.unit_of_analysis` records that measurement unit. The column is for
    the rater, so it names the property's unit; where the two differ the
    override says which candidate, which unit and why, and nothing else moves.
    """
    sheet = czech["panel_sheet"]
    overrides = sheet["judged_over_overrides"]
    units = czech["vocabulary"]["unit_of_analysis"]
    by_id = {c["id"]: c for c in catalog["candidates"]}
    assert overrides
    for code, override in overrides.items():
        assert code in by_id
        assert override["unit"] in units
        # An override that agrees with the catalog is not an override; it is a
        # way to make the column stop tracking anything.
        assert override["unit"] != by_id[code]["unit_of_analysis"], code
        assert len(override["why"].split()) >= 15, code

    table = panel_sheet.rows(czech, codes, catalog)
    shown = {row[0]: row[4] for row in table if row and row[0] in set(codes)}
    for code, candidate in by_id.items():
        expected = overrides.get(code, {}).get("unit", candidate["unit_of_analysis"])
        assert shown[code] == units[expected], code


def test_the_note_type_is_said_once_and_on_the_legend(catalog, czech, codes):
    """A sheet that asks about "a session note" asks about two different things.

    A progress note is part of the record: the care team and the payer read it
    and the client has a right of access. A therapeutic note is the clinician's
    own analysis, kept apart from the record, and the American rule excludes
    diagnosis, plan, symptoms, prognosis and progress from it by name. The same
    property can be essential in one and pointless in the other, which is what
    the panel is being asked.

    Each tab used to open with a heading saying which note it meant. The tab is
    already named for that note, so the heading said it twice on one screen and
    the investigator cut it: the table is the first row of the tab, and one
    sentence for each note type is on the legend.
    """
    sheet = czech["panel_sheet"]
    purposes = sheet["purposes"]
    assert list(purposes) == ["progress_note", "therapeutic_note"]
    said = [cell for row in panel_sheet.legend(czech, codes) for cell in row if cell]
    for name, entry in purposes.items():
        table = panel_sheet.rows(czech, codes, catalog, name)
        assert table[0][0] == sheet["header"][0], "the table is the first row of the tab"
        assert "head" not in entry, name
        # One sentence, on the legend, exactly once -- and nowhere on the tab,
        # whose own name already says which note it asks about.
        assert len(entry["legend_line"].split()) >= 8, name
        assert said.count(entry["legend_line"]) == 1, name
        assert entry["legend_line"] not in "\n".join("\t".join(row) for row in table), name
    # One of the two is the purpose the code already has; the other is not yet
    # built, and the mapping is recorded rather than assumed.
    assert purposes["progress_note"]["maps_to_code"] == "continuity"
    assert purposes["therapeutic_note"]["maps_to_code"] is None


def test_the_sheet_carries_no_superseded_sentence(catalog, czech, codes):
    """It told three raters a rule the protocol no longer held, and nothing caught it.

    The instruction said an item two of three call relevant stays as contested.
    That was the rule recorded on 2026-10-07; D19 replaced it on 2026-10-21,
    before any answer existed, because two of three agree by chance with
    probability 0.50 when a four-point scale is cut above its midpoint. The
    sentence was changed by hand in one place, and the only thing that would
    have found a copy left behind was somebody reading the sheet.

    So the replaced sentences are kept rather than deleted, as a reworded Czech
    criterion keeps its previous wording, and none of them may reach a sheet.
    """
    superseded = czech["panel_sheet"]["superseded_instructions"]
    assert superseded, "nothing is recorded, so nothing is guarded"
    # The legend counts too. It did not until 2026-10-22, and a heading that
    # left the legend and came back an hour later sat there recorded as gone:
    # a false record of a removal, which is worse than no record at all.
    text = "\n".join(
        "\t".join(row)
        for rows in (panel_sheet.rows(czech, codes, catalog), panel_sheet.legend(czech, codes))
        for row in rows
    )
    for record in superseded:
        assert record["text"] and record["until"] and len(record["why"].split()) >= 8
        assert record["text"] not in text, record["why"]


def test_the_sheets_rule_is_the_protocols_rule(czech):
    """The rater is told what happens to the answer, so the two must agree.

    Checked on the protocol's side in English, because that is where the rule
    lives: unanimity retains, a dissent publishes and does not measure. The
    sheet's own sentence is Czech and is guarded by the test above, which holds
    it to not being the superseded one.

    The panel went from three raters to four on 2026-10-22, which made the rule
    stricter without changing its kind: all of them, whoever they are.
    """
    protocol = json.loads((REPO / "research/gen2/protocol.json").read_text(encoding="utf-8"))
    rule = protocol["content_validity"]["retention_rule"]
    raters = protocol["content_validity"]["panel"]["raters"]
    assert raters == 4
    assert "retained for measurement" in rule[f"{raters}_of_{raters}"]
    # One short of unanimity is two outcomes, not one: the last rater either is
    # against the item or merely does not think it essential, and a yes/no
    # answer cannot tell those apart. Neither is measured.
    assert "not measured" in rule[f"{raters - 1}_of_{raters}_nobody_against"]
    assert "not measured" in rule[f"{raters - 1}_of_{raters}_one_against"]
    # The tiers of the three-rater panel are gone, not left beside the new ones.
    assert not [key for key in rule if "_of_3" in key]
    assert "coin flip" in rule["modified_kappa"]
    assert rule["amended_before_any_answer"] is True
    chance = rule["chance_levels_under_a_uniform_rater"]
    assert chance[f"{raters}_of_{raters}"] == 0.0625
    assert chance[f"at_least_{raters - 1}_of_{raters}"] == 0.3125
    # The figure the panel of three would have had, kept so that a reader can
    # see that adding a rater halved the chance level rather than loosening it.
    assert chance["3_of_3_for_comparison"] == 0.125
    # The null is stated wherever the figures are, because nobody answers
    # uniformly and a chance level read as a behaviour is worse than none.
    assert "uniformly" in rule["chance_levels_under_a_uniform_rater"]["null"]
    # A blank is neither a zero nor a smaller denominator: the rule has to say
    # what it does with it, and what it does is leave the item unmeasured.
    assert "not computed" in rule["missing_answer"]
    assert "invent" in rule["missing_answer"]
    assert "not measured" in rule["missing_answer"]
    # Cohen's kappa is defined for two raters and the rule named it for three.
    assert "Krippendorff" in rule["agreement"] and "pairwise" in rule["agreement"]


def test_what_the_protocol_quotes_is_in_the_file_that_read_it():
    """The protocol said for weeks that neither primary source had been retrieved.

    Both were read on 2026-10-22 and the protocol now rests four claims on them:
    that four points with the cut above the midpoint is Lynn's, that three
    raters is a floor she names rather than only fewer than typical, that her
    Table 2 requires all three of three, and that the sheet's third question is
    her recommendation. A claim quoted from a paper nobody can check is worse
    than no claim, so every quotation lives in one artefact with its page, and
    this holds the protocol to it.

    What is deliberately asserted here too is the gap: the figure that would
    settle where this project's own labels come from was not read, and the
    artefact has to keep saying so.
    """
    artefact = json.loads((REPO / "research/gen2/panel-scale-sources.json").read_text("utf-8"))
    protocol = json.loads((REPO / "research/gen2/protocol.json").read_text(encoding="utf-8"))
    cv = protocol["content_validity"]

    sources = {s["id"]: s for s in artefact["sources"]}
    assert set(sources) == {"lynn-1986", "davis-1992"}
    quoted = []
    for source in sources.values():
        assert source["doi"] and source["route"] and source["read_on"] == "2026-10-22"
        # Read by the assistant in a browser. Nobody has checked a quote against
        # the paper, and the artefact may not imply otherwise.
        assert source["verified_by_a_person"] is False
        assert len(source["not_read"].split()) >= 5, source["id"]
        for quote in source["quotes"]:
            assert quote["page"] and len(quote["what_it_settles"].split()) >= 8
            quoted.append(quote["quote"])
    everything = " ".join(quoted)

    # Each fragment the protocol puts in quotation marks has to be one of them.
    for fragment in (
        "a minimum of three experts should be used",
        "not only statistically unjustifiable",
        "does not include the ambivalent middle rating",
        "the total number of items ranked 3 or 4 by both reviewers",
        "80% or better agreement among reviewers",
        "relevant but needs minor alteration",
        "should identify any area(s) that have been omitted",
    ):
        assert fragment in everything, fragment

    where = "research/gen2/panel-scale-sources.json"
    assert where in cv["retention_rule"]["supported_by"]
    assert where in cv["procedure"]["what_the_source_recommends"]
    relevance = next(q for q in cv["questions"] if q["id"] == "relevance")
    assert where in relevance["scale_source"]
    # The labels are not traced, and the protocol says so rather than implying
    # that reading the sources settled it.
    assert "not Lynn's" in relevance["scale_source"]
    assert "unsettled" in relevance["scale_source"]
    # Lawshe is still unretrieved and still gives nothing.
    assert "Lawshe" in relevance["scale_source"] and "unretrieved" in relevance["scale_source"]


def test_the_order_is_the_recorded_seed_and_does_not_move(codes):
    """The order is part of the method, so it is pinned, not re-drawn.

    Two panels shown different orders are not comparable, and the seed was
    recorded on 2026-10-07 before any answer existed.
    """
    assert panel_sheet.SEED == 20261007
    assert panel_sheet.order(codes) == panel_sheet.order(codes)
    assert panel_sheet.order(codes) != sorted(codes)
    assert sorted(panel_sheet.order(codes)) == sorted(codes)
    assert panel_sheet.order(codes, seed=1) != panel_sheet.order(codes)


def test_every_rater_gets_their_own_file_for_each_purpose(tmp_path, monkeypatch):
    """One file per rater and note type, and no name from this machine in it.

    A shared sheet makes the second answer a reaction to the first, which is the
    whole reason a content-validity panel has more than one member. The same
    argument splits the two note types onto separate tabs: a second answer made
    beside the first is an answer about the first.

    The raters are read from a gitignored file so that no name enters this
    repository, which is public. Redirecting the output directory must redirect
    that lookup too, or this test depends on one machine and prints four
    people's names while it runs -- so what it builds here is the numbered
    fallback.
    """
    monkeypatch.setattr(panel_sheet, "OUT_DIR", tmp_path)
    assert panel_sheet.main() == 0
    written = sorted(p.name for p in tmp_path.glob("*.csv"))
    assert written == [
        "hodnoceni-1-1-progress_note.csv",
        "hodnoceni-1-2-therapeutic_note.csv",
        "hodnoceni-1-legenda.csv",
        "hodnoceni-2-1-progress_note.csv",
        "hodnoceni-2-2-therapeutic_note.csv",
        "hodnoceni-2-legenda.csv",
    ]
    # Same purpose, same questions: two raters get identical files.
    for purpose in ("progress_note", "therapeutic_note"):
        same = {
            (tmp_path / name).read_bytes() for name in written if name.endswith(purpose + ".csv")
        }
        assert len(same) == 1, purpose
    # The two rating tabs hold the same questions and are now byte for byte the
    # same file: the tab's own name is what says which note it asks about, so
    # nothing inside it differs. The legend is the same for everyone too.
    rating = [name for name in written if not name.endswith("legenda.csv")]
    assert len({(tmp_path / name).read_bytes() for name in rating}) == 1
    assert len({(tmp_path / n).read_bytes() for n in written if n not in rating}) == 1

    recorded = json.loads((tmp_path / "poradi.json").read_text(encoding="utf-8"))
    assert recorded["seed"] == panel_sheet.SEED
    assert recorded["items"] == 48
    assert recorded["purposes"] == ["progress_note", "therapeutic_note"]


def test_the_sheet_refuses_to_build_from_drifted_data(tmp_path, monkeypatch):
    """The failure that this whole step exists to prevent.

    A sheet generated from a file that no longer matches the catalog asks the
    panel about an instrument that does not exist. It exits non-zero and writes
    nothing rather than producing a plausible CSV.
    """
    monkeypatch.setattr(panel_sheet, "OUT_DIR", tmp_path)
    module = panel_sheet._catalog_module()
    drifted = json.loads(CZECH_PATH.read_text(encoding="utf-8"))
    del drifted["candidates"]["K01"]
    monkeypatch.setattr(module, "load_czech", lambda *a, **k: drifted)
    monkeypatch.setattr(panel_sheet, "_catalog_module", lambda: module)
    assert panel_sheet.main() == 2
    assert not list(tmp_path.glob("*.csv"))


@pytest.mark.parametrize("script", ["panel_sheet.py", "render_catalog_cs.py"])
def test_the_generators_carry_no_czech_of_their_own(script):
    """The wording lives in the data, so these scripts stay public-safe.

    Every other script in the catalog directory is held to the same rule, and it
    is what lets the Czech sit behind one allow-list entry instead of several.
    """
    text = (CATALOG_DIR / script).read_text(encoding="utf-8")
    assert not DIACRITIC.search(text)
    assert "C:\\" not in text and "/Users/" not in text


# --- the one Czech table ---------------------------------------------------


@pytest.fixture(scope="module")
def operational() -> dict:
    return json.loads((CATALOG_DIR / "operational.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def page(catalog, czech, operational) -> str:
    return render_cs.render(catalog, czech, operational, "1. 1. 2026 00:00", "0" * 64)


def test_the_table_has_one_row_per_candidate(page, codes):
    assert page.count("<tr class=") == len(codes) == 48
    for code in codes:
        assert f"<td class=id>{code}</td>" in page


def test_the_plain_tier_has_two_columns_and_covers_everything_the_page_shows(page, czech, codes):
    """The table a reader meets first: a name, and what the thing is.

    The investigator asked for this after reading the nine-column table and
    being unable to tell what any of the criteria were, which is the defect it
    exists to fix: a third column would be the start of the same drift. It
    covers the candidates and the first-generation questions both, because the
    page shows both and the question "what is this" applies to each.
    """
    labels = czech["page"]["plain"]
    assert len(labels["columns"]) == 2
    questions = czech["first_generation_questions"]
    assert page.count("<tr data-code=") == len(codes) + len(questions)
    headers = "".join(f"<th>{column}</th>" for column in labels["columns"])
    assert page.count(headers) == 2, "both plain tables carry the same two columns"
    for code in [*codes, *(q["id"] for q in questions)]:
        assert f"<tr data-code='{code}'>" in page


def test_every_plain_row_shows_an_example(page, czech, codes):
    """A sentence saying what a criterion is, and a case of it going wrong.

    Without the example the sentence stays abstract, which is what the formal
    definitions already were. `example` is required of every candidate for this
    reason, so a row with none is a validation failure rather than a blank cell.
    """
    shown = page.count(f"<b>{czech['page']['plain']['example_label']}</b>")
    assert shown == len(codes) + len(czech["first_generation_questions"])
    for entry in czech["candidates"].values():
        assert entry["example"] in page


def test_the_plain_tier_comes_first_and_leads_into_the_detailed_table(page, czech, codes):
    """Order is the point, not decoration.

    The detailed table was the whole page and the explanation was nowhere, so a
    plain tier printed below it would answer the question after the reader had
    already given up. Each plain row also links to its own row in the detailed
    table, so the two tiers are one page rather than two lists.
    """
    labels = czech["page"]["plain"]
    assert page.index(labels["heading"]) < page.index(labels["detail_heading"])
    assert page.index(labels["detail_heading"]) < page.index("<td class=id>")
    for code in codes:
        assert f"<a href='#{code}'>{code}</a>" in page, f"{code} has no link to its row"
        assert f"id='{code}'" in page, f"{code} is linked to a row that is not there"
    # The first-generation questions are not in the detailed table, so a link
    # from them would point at nothing.
    for question in czech["first_generation_questions"]:
        assert f"<a href='#{question['id']}'>" not in page


def test_the_source_column_is_a_link_to_the_study(page, catalog):
    """The column said who found it and gave no way to go and read it.

    It held a short citation as plain text, so a reader who wanted the study had
    to search for it by author and year. The citation is now the link. The two
    sources that resolve nowhere stay text, because a dead link on a page about
    provenance is worse than no link, and one of them backs three criteria here.
    """
    sources = {s["id"]: s for s in catalog["sources"] + catalog["abstract_sources"]}
    linked = unlinkable = 0
    for candidate in catalog["candidates"]:
        for evidence in candidate["evidence"]:
            source = sources[evidence["source"]]
            url = catalog_mod.ledger_url(source["ledger_report_id"])
            if url:
                assert f'<a href="{url}">' in page, f"{source['id']} is named without its study"
                linked += 1
            else:
                unlinkable += 1
                assert f'href="{source["ledger_report_id"]}"' not in page
    assert linked and unlinkable, "both branches have to be exercised by the real data"
    # Escaping is the trap: the cell used to be wrapped in `esc`, which would
    # print the anchor as visible markup instead of drawing it.
    assert "&lt;a href=" not in page


def _state_audit():
    """The audit's own test for Czech that asserts a measurement, not a copy of it."""
    spec = importlib.util.spec_from_file_location(
        "gen2_state_audit", REPO / "research" / "gen2" / "audit.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["gen2_state_audit"] = module
    spec.loader.exec_module(module)
    return module


def test_no_czech_the_page_shows_says_a_criterion_is_being_measured(page, czech, catalog):
    """The defect the investigator met every day, and it was made in translation.

    The page printed MERI SE, bold and in capitals, on every row whose catalog
    state is `proposed`, whose English reads "an AI proposal awaiting human
    selection". Generation 2 has measured nothing, so the Czech reader was told
    the opposite of the truth by the page's most prominent string while the
    English reader was told the truth. Two more strings said it again: the legend
    of the page's own colour coding and the filter buttons.

    The check is the audit's, loaded rather than reimplemented, so the two cannot
    drift apart. A quotation is exempt: the introduction now says what the rows
    used to read, and that sentence is the repair.
    """
    audit = _state_audit()
    shown = [
        *czech["page"]["states"].values(),
        *czech["page"]["filters"].values(),
        *czech["page"]["intro"],
        *czech["vocabulary"]["state"].values(),
    ]
    for string in shown:
        assert not audit.MEASURES.search(audit.without_quotations(string)), (
            f"{string[:70]!r} tells the reader a criterion is measured; nothing is"
        )

    proposed = sum(1 for c in catalog["candidates"] if c["state"] == "proposed")
    assert page.count(czech["page"]["states"]["measured"]) >= proposed
    # And the one thing Czech never said at all: that the round has not run.
    # Written as escapes, like the diacritic class in test_no_clinical_content.py,
    # so that the file checking Czech does not have to be allow-listed for it.
    not_measured = "nezm" + chr(0x11B) + chr(0x159) + "ilo"
    assert not_measured in " ".join(czech["page"]["intro"])


def test_no_count_on_the_page_is_typed_anywhere(page, catalog, czech):
    """The defect that produced five different numbers.

    Each old view had its total written into a button by hand, so every one of
    them was right on the day it ran. The filter labels here are counted from
    the catalog, and the test fails if a number stops matching it rather than
    when somebody notices.
    """
    total = len(catalog["candidates"])
    measured = sum(1 for c in catalog["candidates"] if c["state"] == "proposed")
    labels = czech["page"]["filters"]
    assert f"{labels['all']} ({total})" in page
    assert f"{labels['on']} ({measured})" in page
    assert f"{labels['off']} ({total - measured})" in page
    for number in (16, 17, 33, 34):
        if number not in (total, measured, total - measured):
            assert f"({number})" not in page


def test_a_stale_copy_says_so_instead_of_being_recounted(catalog, czech, operational):
    """The header carries the digest of the catalog the page was made from.

    The old views could only be checked by counting their rows against the
    catalog, which is how one of them sat six days old and sixteen criteria
    short. A digest that does not match the file is visible at a glance.
    """
    rendered = render_cs.render(catalog, czech, operational, "1. 1. 2026 00:00", "abc123def456" * 5)
    assert "abc123def456" in rendered
    assert czech["page"]["stale"] in rendered


def test_the_digest_is_of_the_catalog_file_as_it_is_on_disk(tmp_path, monkeypatch):
    import hashlib

    monkeypatch.setattr(render_cs, "OUT", tmp_path / "kriteria-cesky.html")
    assert render_cs.main() == 0
    expected = hashlib.sha256(render_cs.CATALOG_PATH.read_bytes()).hexdigest()[:12]
    assert expected in (tmp_path / "kriteria-cesky.html").read_text(encoding="utf-8")


def test_a_candidate_with_no_czech_question_says_so_rather_than_showing_a_blank(page, czech):
    """K35 and K36 were added after the last generator ran.

    An empty cell reads as "nothing to ask here", which is a claim. The gap is
    labelled instead, and the label is in the data so it can be read.
    """
    missing = czech["coverage"]["missing_by_field"]["question"]
    assert missing == ["K35", "K36"]
    assert page.count(czech["page"]["no_question"]) == len(missing)


def test_the_table_refuses_to_render_from_drifted_data(tmp_path, monkeypatch):
    monkeypatch.setattr(render_cs, "OUT", tmp_path / "kriteria-cesky.html")
    module = render_cs._catalog_module()
    drifted = json.loads(CZECH_PATH.read_text(encoding="utf-8"))
    drifted["candidates"]["K01"]["statement"] = ""
    monkeypatch.setattr(module, "load_czech", lambda *a, **k: drifted)
    monkeypatch.setattr(render_cs, "_catalog_module", lambda: module)
    assert render_cs.main() == 2
    assert not (tmp_path / "kriteria-cesky.html").exists()


DIACRITIC = re.compile(
    "[" + "\u011b\u0161\u010d\u0159\u017e\u00fd\u00e1\u00ed\u00e9\u00fa\u016f\u0148\u0165\u010f"
    "\u011a\u0160\u010c\u0158\u017d\u00dd\u00c1\u00cd\u00c9\u00da\u016e\u0147\u0164\u010e]"
)


def test_the_validator_names_every_drift_instead_of_raising(catalog, czech):
    """A diagnosis, not a traceback.

    The first version of the check crashed with a KeyError on a candidate that
    czech.json did not name, which is the first drift anyone would hit. A
    validator that raises on the failure it exists to describe tells the person
    running it nothing, so each shape is asserted to come back as a line.
    """

    def drift(change) -> list[str]:
        copy = json.loads(json.dumps(czech))
        change(copy)
        found = catalog_mod.czech_problems(catalog, copy)
        assert found, "a drifted file validated"
        return found

    def unknown_candidate(copy):
        copy["candidates"]["K99"] = {"name": "x", "statement": "y", "from": {}}

    def missing_candidate(copy):
        del copy["candidates"]["K01"]

    def emptied_statement(copy):
        copy["candidates"]["K01"]["statement"] = "  "

    def miscounted(copy):
        copy["coverage"]["by_field"]["name"] = 35

    def grouping_names_a_stranger(copy):
        copy["groupings"]["our_groups"]["Pravdivost"] = ["K98"]

    def conflict_keeps_other_text(copy):
        copy["conflicts_resolved"][0]["kept"]["text"] = "something else"

    assert any("not a candidate" in line for line in drift(unknown_candidate))
    assert any("no Czech text" in line for line in drift(missing_candidate))
    assert any("required and empty" in line for line in drift(emptied_statement))
    assert any("by_field" in line for line in drift(miscounted))
    assert any("is not a candidate" in line for line in drift(grouping_names_a_stranger))
    assert any("kept text" in line for line in drift(conflict_keeps_other_text))


def test_every_criterion_says_in_one_sentence_what_it_is(czech, codes):
    """The thing the investigator asked for on 2026-10-15, and the reason it was missing.

    The catalog had a formal definition for every candidate, a unit, and a
    sentence on what goes wrong. It had no sentence a person who does not know
    the criteria could start from, so every column added to the table was one
    more thing to decode. `plain` is that sentence and `example` is what going
    wrong looks like, and both exist for all of them or the list has a hole
    exactly where somebody would stop reading.
    """
    for code in codes:
        entry = czech["candidates"][code]
        assert entry["plain"].strip(), code
        assert entry["example"].strip(), code
        # A plain sentence is short. The formal definition is one click away and
        # copying it here would meet the request only in appearance.
        assert len(entry["plain"]) < 160, (code, len(entry["plain"]))
        assert entry["plain"] != entry.get("definition"), code

    sheet = czech["first_generation_questions"]
    assert len(sheet) == 7
    for question in sheet:
        assert question["name"] and question["plain"] and question["example"]
