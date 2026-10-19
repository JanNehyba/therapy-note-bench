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
    assert len(czech["candidates"]) == 39


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
    assert coverage["candidates"] == 39
    assert coverage["by_field"]["name"] == coverage["by_field"]["statement"] == 39
    # K35 and K36 were added on 2026-10-07, after the last generator ran, so they
    # have no question and no unit. K37 to K39 were written on 2026-10-14 with
    # both, which is why they are not in these lists.
    assert coverage["missing_by_field"]["question"] == ["K35", "K36"]
    assert coverage["missing_by_field"]["unit"] == ["K35", "K36"]
    assert coverage["candidates_with_no_explanation_of_their_state"] == ["K34", "K35", "K36"]
    assert coverage["candidates_with_no_explanation_note"]


def test_every_resolved_conflict_says_what_it_rejected(czech):
    """Five names and twelve questions were worded differently in two places.

    The file keeps one and records the other with the generator it came from.
    A silent merge would leave nobody able to see that a choice was made.
    """
    conflicts = czech["conflicts_resolved"]
    assert conflicts
    for entry in conflicts:
        kept = czech["candidates"][entry["candidate"]][entry["field"]]
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
AUTHORED_FIELDS = {"plain", "example"}


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


def test_the_sheet_has_one_row_per_candidate(czech, codes):
    table = panel_sheet.rows(czech, codes)
    items = [row for row in table if row and re.fullmatch(r"K\d\d", row[0])]
    assert len(items) == len(codes) == 39
    assert {row[0] for row in items} == set(codes)
    for code, name, statement, *answers in items:
        assert name == czech["candidates"][code]["name"]
        assert statement == czech["candidates"][code]["statement"]
        assert answers == ["", "", ""], code


def test_the_sheet_is_blind(catalog, czech, codes):
    """A rater who can see the state or the citation ratifies instead of judging.

    The sheet carries a code, a name and a statement. Nothing in it says whether
    a criterion is measured, where it came from, or who proposed it: the panel is
    asked what matters for a session note, not whether this project was right.
    """
    table = panel_sheet.rows(czech, codes)
    text = "\n".join("\t".join(row) for row in table)
    for candidate in catalog["candidates"]:
        assert candidate["state"] not in text
        assert candidate["origin"] not in text
        assert candidate["family"] not in text
        assert candidate["label"] not in text
    for source in catalog["sources"]:
        assert source["key"] not in text


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


def test_every_rater_gets_the_same_sheet_in_its_own_file(tmp_path, monkeypatch):
    """One file per rater, identical content.

    A shared sheet makes the second answer a reaction to the first; three copies
    of the same questions make the three answers independent, which is the whole
    reason a content-validity panel has more than one member.
    """
    monkeypatch.setattr(panel_sheet, "OUT_DIR", tmp_path)
    assert panel_sheet.main() == 0
    written = sorted(p.name for p in tmp_path.glob("*.csv"))
    assert written == [
        "hodnoceni-kriterii-1.csv",
        "hodnoceni-kriterii-2.csv",
        "hodnoceni-kriterii-3.csv",
    ]
    contents = {(tmp_path / name).read_bytes() for name in written}
    assert len(contents) == 1
    recorded = json.loads((tmp_path / "poradi.json").read_text(encoding="utf-8"))
    assert recorded["seed"] == panel_sheet.SEED
    assert recorded["items"] == 39


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
    assert page.count("<tr class=") == len(codes) == 39
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
