"""The Gen-2 candidate catalog: one versioned record, two generated views.

The audit of 2026-09-15 found the review's criteria map in three unconnected
places: a Czech working catalog on one machine, a runtime registry with other
names, and prose that quoted both. `research/gen2/catalog/catalog.json` is now
the one record; `docs/gen2-catalog.html` and `draft-registry.json` are derived
from it. Pinned here: the catalog validates and points at the review's ledger,
the page and the draft equal a fresh rendering and conversion, the draft loads
in the core and is refused as a pilot instrument, no record claims a human
decision, every pilot entry and method is accounted for in the diagnostics,
and nothing in any of the files is Czech text, a local path or a secret.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest
from therapy_note_eval.registry import load_registry
from therapy_note_eval.schema import PROFILES, ValidationError, digest

REPO = Path(__file__).resolve().parents[1]
CATALOG = REPO / "research" / "gen2" / "catalog"
REVIEW = REPO / "research" / "gen2" / "review-2026-09-13"
PAGE = REPO / "docs" / "gen2-catalog.html"


def _module(name: str):
    spec = importlib.util.spec_from_file_location(name, CATALOG / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


catalog_mod = _module("catalog")
render_catalog = _module("render_catalog")
convert_to_registry = _module("convert_to_registry")


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def catalog() -> dict:
    return catalog_mod.load()


@pytest.fixture(scope="module")
def reports() -> dict:
    return _json(REVIEW / "reports.json")


@pytest.fixture(scope="module")
def protocol() -> dict:
    return _json(REPO / "research" / "gen2" / "protocol.json")


@pytest.fixture(scope="module")
def proposals() -> dict:
    return _json(REPO / "research" / "gen2" / "prior-proposals.json")


@pytest.fixture(scope="module")
def draft() -> dict:
    return _json(CATALOG / "draft-registry.json")


@pytest.fixture(scope="module")
def diagnostics() -> dict:
    return _json(CATALOG / "conversion-diagnostics.json")


# --- the record -------------------------------------------------------------


def test_the_catalog_validates_against_the_ledger(catalog, reports):
    assert catalog_mod.problems(catalog, reports) == []


def test_the_catalog_holds_what_the_review_proposed(catalog):
    """The counts the documentation states, held to the record."""
    # 29 from the round of 2026-09-13, two returned or split on 2026-09-16, and
    # two adopted on 2026-09-21 from properties the sources defined and the
    # catalog had not covered.
    assert len(catalog["candidates"]) == 34
    assert len(catalog["methods"]) == 17
    # 19 read in the round of 2026-09-13, and 6 more read on 2026-09-20 after
    # the investigator supplied them; 7 are still known from abstracts only.
    assert len(catalog["sources"]) == 25
    assert len(catalog["abstract_sources"]) == 7
    assert len(catalog["pilot_proposal"]["entries"]) == 14
    assert len(catalog["comparison"]) == 37
    assert catalog_mod.ids(catalog, "candidates") == [f"K{n:02d}" for n in range(1, 35)]
    assert catalog_mod.ids(catalog, "methods") == [f"ME{n:02d}" for n in range(1, 18)]


def test_every_candidate_carries_a_state_and_a_reason(catalog):
    """Audit A07: "irrelevant", "not yet operationalized" and "awaiting raters"
    are different reasons and were all being spelled as absence from the pilot."""
    states = {c["id"]: c["state"] for c in catalog["candidates"]}
    assert set(states.values()) <= set(catalog["candidate_states"])
    measured = {
        found
        for p in catalog["pilot_proposal"]["entries"]
        for found in catalog_mod.ID.findall(p["measures"])
        if found in states
    }
    assert {k for k, v in states.items() if v == "proposed"} == measured
    assert states["K30"] == states["K31"] == "not_yet_operationalized"
    assert states["K32"] == states["K33"] == "not_yet_operationalized"
    assert states["K15"] == "lacking_evidence"
    # K13 still waits for a reader the pilot has not got. K24 and K25 waited for
    # one too until decision D8 of 2026-09-16 put their purposes out of scope,
    # which is a different reason and has to read as one.
    assert states["K13"] == "awaiting_raters"
    assert states["K24"] == states["K25"] == "out_of_scope"
    assert states["K26"] == states["K27"] == "not_measured"
    assert states["K20"] == states["K22"] == "out_of_scope"
    assert "measurement_failed" not in states.values()
    for c in catalog["candidates"]:
        assert c["state_note"], c["id"]


def test_the_state_of_a_candidate_must_match_the_pilot_proposal(catalog):
    doctored = json.loads(json.dumps(catalog))
    by = {c["id"]: c for c in doctored["candidates"]}
    by["K30"]["state"] = "proposed"
    assert any("does not match the pilot proposal" in p for p in catalog_mod.problems(doctored))


def test_the_reopened_candidates_say_what_reopened_them(catalog):
    """A07 reopened two decisions, and the record has to show the reversal
    rather than quietly reading as though the drop never happened."""
    by = {c["id"]: c for c in catalog["candidates"]}
    assert "A07" in by["K30"]["origin_note"] and "A07" in by["K31"]["origin_note"]
    assert by["K30"]["origin"] == by["K31"]["origin"] == "prior_local"
    assert {e["source"] for e in by["K30"]["evidence"]} == {"S8", "S2"}
    assert "S4" in {e["source"] for e in by["K31"]["evidence"]}
    # By its reason, not by being the newest entry: revisions accumulate, and
    # pinning "the last one" would fail the next time anything else is revised.
    reopening = [r for r in catalog["revisions"] if "A07" in r["reason"]]
    assert len(reopening) == 1 and reopening[0]["date"] == "2026-09-16"


def test_the_round_serves_two_purposes_and_says_which_it_does_not(catalog):
    """Decision D8 of 2026-09-16. A purpose left out keeps its candidates and
    its evidence; what changes is what the round measures and claims."""
    scope = catalog["purposes_in_scope"]
    assert scope["served"] == ["continuity", "audit"]
    assert scope["out_of_scope"] == ["supervision", "client"]
    assert scope["protocol_decision"].startswith("D8")
    assert set(scope["served"]) | set(scope["out_of_scope"]) == set(catalog["purposes"])

    by = {c["id"]: c for c in catalog["candidates"]}
    for key in ("K24", "K25"):
        assert by[key]["state"] == "out_of_scope"
        assert "D8" in by[key]["state_note"]
        assert by[key]["evidence"], "a purpose left out keeps its evidence"
        assert set(by[key]["relevance"]) == set(catalog["purposes"])

    coverage = next(r for r in catalog["pilot_proposal"]["applied_criteria"] if r["id"] == "C3")
    assert "the round serves" in coverage["criterion"]
    assert "D8" in coverage["detail"]


def test_the_acceptability_criterion_asks_about_use_not_about_a_payer(catalog):
    """The investigator marked K23 `revise` on 2026-09-16: "accept the note into
    practice" read as a question about an insurer. The six parameters it rests
    on are about using the system, and the wording now says so."""
    k23 = next(c for c in catalog["candidates"] if c["id"] == "K23")
    assert "not about billing or any payer" in k23["definition"]
    for parameter in ("affective attitude", "burden", "ethicality", "opportunity costs"):
        assert parameter in k23["definition"]
    assert "never summed with" in k23["measurement"]
    assert "2026-09-16" in k23["state_note"]


def test_the_catalog_names_its_method_and_the_gap_that_method_leaves(catalog):
    """An earlier draft leaned on best-fit framework synthesis, which begins from a
    published framework; this began from the project's own prototype. The record
    names what was done instead, quotes the source for it, and says plainly that
    the content-validity judgement that method requires has not happened."""
    method = catalog["method"]
    assert "item generation" in method["named"] and "content validity" in method["named"]
    assert "withdrawn" in method["why_not_framework_synthesis"]
    generation = method["item_generation"]
    assert generation["source"] == "S12" and generation["quote"]
    assert generation["deductive_here"] and generation["inductive_here"]
    validity = method["content_validity"]
    assert validity["source"] == "S12"
    assert "independent of those who developed the item pool" in validity["quote"]
    assert validity["where_we_stand"].startswith("Not met")
    for key in ("S11", "S12"):
        assert key in catalog_mod.source_ids(catalog), "the method rests on sources it holds"


def test_the_framework_is_reported_from_the_sources_upwards(catalog, props):
    """The investigator asked whether a purely source-first derivation would reach
    the same framework. It nearly does, and the record says both halves of that:
    how far the convergence goes, and that the extraction was not blind."""
    derivation = catalog["method"]["derivation"]
    assert "source-first" in derivation["reported_from"]
    assert "comparison" in derivation["prior_map_role"]
    assert "not a blind replication" in derivation["caveat"]
    anchored = {
        key
        for source in props["sources"]
        for prop in source["properties"]
        for key in prop["maps_to"]
    }
    ids = {c["id"] for c in catalog["candidates"]}
    assert len(anchored & ids) == 34 - 1
    assert ids - anchored == {"K06"}, "the one candidate no source defines is named"
    assert [row["id"] for row in props["candidates_without_source_property"]] == ["K06"]
    assert "K06" in derivation["convergence"]
    assert "not a blind replication" in props["blindness"]


def test_nothing_is_measured_on_its_origin_alone(catalog):
    """The item pool mixes what the search found with what the project already had,
    which is how an item pool is built. What keeps that honest is that support, not
    origin, decides what may be measured, and the validator says so."""
    full_text = {s["id"] for s in catalog["sources"]}
    proposed = [c for c in catalog["candidates"] if c["state"] == "proposed"]
    assert len(proposed) == 17
    for candidate in proposed:
        assert any(e["source"] in full_text for e in candidate["evidence"]), candidate["id"]
    assert {c["origin"] for c in proposed} > {"literature"}, "the pool is mixed by design"

    doctored = json.loads(json.dumps(catalog))
    victim = next(c for c in doctored["candidates"] if c["id"] == "K05")
    abstract_only = doctored["abstract_sources"][0]["id"]
    victim["evidence"] = [{**e, "source": abstract_only} for e in victim["evidence"]]
    assert any(
        "without a source read in full" in problem for problem in catalog_mod.problems(doctored)
    )


def test_the_czech_legal_criterion_states_the_population_it_binds(catalog):
    """The investigator decided on 2026-09-16 not to obtain a legal review and
    to narrow the scope instead, so nothing here may read as a legal verdict.

    The decree binds records kept by a provider of health services. A therapist
    outside health services keeps no medical documentation, a client summary is
    not medical documentation, and no note structure is prescribed at all.
    """
    k19 = next(c for c in catalog["candidates"] if c["id"] == "K19")
    p09 = next(p for p in catalog["pilot_proposal"]["entries"] if p["id"] == "P09")
    for field in (k19["definition"], k19["applicability"]):
        assert "health services" in field
    assert "no SOAP, DAP or BIRP form is mandatory" in k19["applicability"]
    assert "never as a statement about legal compliance" in k19["validation"]
    assert "no lawyer has checked it" in k19["validation"]
    assert "never mixed into a quality score" in p09["risk"]
    assert "no legal review will be obtained" in p09["human_input"]
    narrowing = [r for r in catalog["revisions"] if "legal criterion" in r["reason"]]
    assert len(narrowing) == 1 and narrowing[0]["date"] == "2026-09-16"


def test_every_source_is_a_report_the_ledger_sought(catalog, reports):
    """What the catalog claims to have read, against what the ledger recorded.

    The two halves say different things and must not be conflated. A catalog
    source marked `full_text` claims the text was read, and the ledger has to
    show it was retrieved. An abstract-only source claims nothing beyond the
    abstract, whether or not the file has since arrived: six of them were
    downloaded on 2026-09-16 and are recorded as retrieved, and the catalog
    still rests on their abstracts because nobody has read them.
    """
    by_id = {r["report_id"]: r for r in reports["reports"]}
    for s in catalog["sources"]:
        report = by_id[s["ledger_report_id"]]
        assert report["catalog_source"] == s["id"]
        if s["verification"] == "full_text":
            assert report["current_status"] == "retrieved", s["id"]
            assert report["reading"]["basis"] == "full_text", s["id"]
        else:
            assert report["current_status"] != "retrieved", s["id"]
    for s in catalog["abstract_sources"]:
        report = by_id[s["ledger_report_id"]]
        assert report["catalog_source"] == s["id"]
        assert report["reading"]["basis"] == "abstract", s["id"]


def test_every_pilot_entry_carries_a_record_kind_and_the_count_is_recorded_not_capped(catalog):
    kinds = {p["id"]: p["record_kind"] for p in catalog["pilot_proposal"]["entries"]}
    assert kinds["P12"] == "study_condition"
    assert kinds["P09"] == "requirements_check"
    assert kinds["P10"] == kinds["P11"] == "human_use_outcome"
    assert kinds["P13"] == "corpus_level_proxy"
    assert kinds["P14"] == "derived_ratio"
    assert sum(1 for k in kinds.values() if k == "executable_measure") == 8
    note = catalog["pilot_proposal"]["count_note"]
    assert "record-not-cap" in note and "not a result of the review" in note


def test_the_problem_finder_refuses_a_human_decision_field(catalog):
    doctored = json.loads(json.dumps(catalog))
    doctored["candidates"][0]["reviewed_by"] = "somebody"
    assert any("human decision" in p for p in catalog_mod.problems(doctored))
    doctored = json.loads(json.dumps(catalog))
    doctored["status"] = "Accepted."
    assert any("no human acceptance" in p for p in catalog_mod.problems(doctored))


def test_the_problem_finder_refuses_a_dangling_reference(catalog):
    doctored = json.loads(json.dumps(catalog))
    doctored["methods"][0]["measures"].append("K99")
    assert any("unknown candidate" in p for p in catalog_mod.problems(doctored))
    doctored = json.loads(json.dumps(catalog))
    doctored["candidates"][3]["evidence"][0]["source"] = "S99"
    assert any("unknown source" in p for p in catalog_mod.problems(doctored))


def test_the_comparison_accounts_for_every_earlier_criterion(catalog):
    olds = [row["old"] for row in catalog["comparison"] if row["old"]]
    assert [o[:3] for o in olds] == [f"c{n:02d}" for n in range(1, 27)]
    added = {row["new"] for row in catalog["comparison"] if row["action"] == "add"}
    kept = {row["new"] for row in catalog["comparison"] if row["new"]}
    assert kept | added <= set(catalog_mod.ids(catalog, "candidates"))
    # c16 was the one dropped row until audit A07 reopened it; the row now
    # points at K30 and keeps the history of both decisions in its reason.
    assert not [row for row in catalog["comparison"] if row["action"] == "drop"]
    naturalness = next(row for row in catalog["comparison"] if row["old"].startswith("c16 "))
    assert naturalness["new"] == "K30" and "A07" in naturalness["reason"]
    assert "Dropped on 2026-09-13" in naturalness["reason"]


# --- the page ---------------------------------------------------------------


def test_the_published_page_equals_a_fresh_rendering(catalog):
    assert PAGE.read_bytes().decode("utf-8") == render_catalog.render(catalog)


def test_the_page_draws_every_entry_and_names_its_status(catalog):
    page = PAGE.read_text(encoding="utf-8")
    for section in ("candidates", "methods"):
        for item in catalog[section]:
            assert f'id="{item["id"]}"' in page
    for p in catalog["pilot_proposal"]["entries"]:
        assert p["label"] in page or render_catalog.esc(p["label"]) in page
    assert "No human acceptance decision exists" in page
    assert 'href="index.html"' in page


# --- the draft registry -----------------------------------------------------


@pytest.fixture(scope="module")
def operational() -> dict:
    return _json(CATALOG / "operational.json")


def test_the_draft_equals_a_fresh_conversion(
    catalog, protocol, proposals, operational, draft, diagnostics
):
    registry, notes = convert_to_registry.convert(catalog, protocol, proposals, operational)
    assert registry == draft
    assert notes == diagnostics


def test_the_draft_loads_and_is_refused_as_a_pilot_instrument(draft, protocol):
    """The draft carries the proposed rules and no decision: it is refused as a
    pilot instrument at the first human decision it lacks, the scope."""
    registry = load_registry(draft)
    assert registry.protocol_revision == digest(protocol)
    assert registry.reviews == ()
    assert (
        [m.id for m in registry.method_specs] == list(registry.methods) == ["qa", "claims", "items"]
    )
    assert [x.id for x in registry.measurements] == ["M06", "M07", "M08"]
    assert all(x.status == "development" for x in registry.measurements)
    with pytest.raises(ValidationError, match="human decision: scope"):
        load_registry(draft, pilot=True)


def test_the_operational_rules_are_bilingual_and_name_only_registry_records(operational, draft):
    """Every method rule and every item exists in Czech with the same outcome
    keys, names constructs and evidence the draft holds, and covers exactly the
    eight executable pilot entries; the six other entries say why they are not
    here. The Czech is instrument wording and carries the marker that lets a
    tracked file hold Czech at all."""
    constructs = {c["id"] for c in draft["constructs"]}
    evidence = {e["id"] for e in draft["evidence"]}
    covered = []
    for m in operational["methods"]:
        assert set(m["construct_ids"]) <= constructs and set(m["evidence_ids"]) <= evidence
        assert set(m["cs"]["outcomes"]) == set(m["outcomes"])
        assert set(m["cs"]["severity_rules"]) == set(m["severity_rules"])
        covered += m["pilot_entries"]
    assert sorted(covered) == [f"P0{i}" for i in range(1, 9)]
    assert {e["entry"] for e in operational["not_operationalised_here"]} == {
        f"P{i:02d}" for i in range(9, 15)
    }
    for x in operational["measurements"]:
        assert x["construct_id"] in constructs and set(x["sources"]) <= evidence
        assert set(x["cs"]["anchors"]) == set(x["labels"])
    assert operational["marker"] == "AUTHORED-INSTRUMENT-TEXT"
    for variant in (m["cs"] for m in operational["methods"]):
        assert variant["definition"] and variant["applicability"]


def test_no_draft_record_claims_a_human_decision(draft, diagnostics):
    for c in draft["constructs"]:
        assert c["status"] == "candidate" and c["reviewed_by"] is None
        assert c["decision_reason"] == "Awaiting human review"
        assert set(c["relevance"]) == set(PROFILES)
    for e in draft["evidence"]:
        assert e["human_checked_by"] is None
    assert draft["methods_reviewed_by"] is None
    assert diagnostics["pilot_check"]["result"] == "refused"


def test_every_source_evidence_line_and_candidate_maps(catalog, draft, diagnostics):
    assert {s["id"] for s in draft["sources"]} == catalog_mod.source_ids(catalog)
    assert [c["id"] for c in draft["constructs"]] == catalog_mod.ids(catalog, "candidates")
    lines = sum(len(c["evidence"]) for c in catalog["candidates"])
    assert len(draft["evidence"]) == lines
    assert diagnostics["mapped"] == {"sources": 32, "evidence": lines, "constructs": 34}
    for s in draft["sources"]:
        assert s["locator"].startswith("ledger:")


def test_every_unmapped_entry_has_a_diagnostic(catalog, diagnostics):
    assert [p["id"] for p in diagnostics["pilot_entries"]] == catalog_mod.ids(catalog, "pilot")
    assert all(p["why_not_a_measurement"] for p in diagnostics["pilot_entries"])
    assert [m["id"] for m in diagnostics["methods"]] == catalog_mod.ids(catalog, "methods")
    assert {
        m["id"]: m["implementation"] for m in diagnostics["methods"] if m["implementation"]
    } == {
        "ME01": "qa",
        "ME02": "claims",
        "ME03": "items",
        "ME08": "citations",
    }
    assert [c["id"] for c in diagnostics["constructs"]] == catalog_mod.ids(catalog, "candidates")
    assert "never becomes a registry status" in diagnostics["state_rule"]
    for c in diagnostics["constructs"]:
        assert c["catalog_state"] in {"proposed"} | set(catalog_mod.load()["candidate_states"])
        assert c["origin_reference"].startswith(("proposal:", "catalog:"))
        if c["origin_reference"].startswith("catalog:"):
            assert "placeholder" in c["note"]
    assert diagnostics["not_mapped"]["pilot_entries_without_operational_rules"] == 6
    assert diagnostics["operational"]["measurements"] == ["M06", "M07", "M08"]


def test_a_verbatim_proposal_name_is_the_only_way_to_a_recorded_origin(proposals):
    ids = {p["id"] for p in proposals["proposals"]}
    named = {
        "id": "K18",
        "origin": "expert_proposal",
        "origin_note": "A colleague's proposal (prior-source-links).",
    }
    assert convert_to_registry.origin_reference(named, ids)[0] == "proposal:prior-source-links"
    vague = {"id": "K20", "origin": "prior_local", "origin_note": "Exists in the prototype."}
    reference, note = convert_to_registry.origin_reference(vague, ids)
    assert reference == "catalog:K20" and "placeholder" in note
    two = {"id": "K01", "origin": "prior_local", "origin_note": "prior-qa and prior-reverse-claims"}
    assert convert_to_registry.origin_reference(two, ids)[0] == "catalog:K01"


def test_the_draft_is_something_the_workflow_can_actually_put_to_a_person(store, draft):
    """Loading is not enough: the point of the conversion is the review step.

    `registry-sheet` is the command that turns a draft into the questions a
    human answers, and a draft that loads but produces no sheet would have
    moved the wall one step further back without saying so. Every source,
    evidence line and construct has to arrive as its own subject, because a
    sheet that bundles them would take one decision for many.
    """
    from therapy_note_eval import development, research

    protocol = _json(REPO / "research" / "gen2" / "protocol.json")
    proposals = _json(REPO / "research" / "gen2" / "prior-proposals.json")
    queries = {"queries": [{"id": "q1", "database": "PubMed", "query": "toy query"}]}
    active = research.initialize(store, protocol, queries, proposals)

    sheet = development.registry_sheet(store, active, draft)
    subjects = {item["id"] for item in sheet["items"]}

    assert {"source:" + s["id"] for s in draft["sources"]} <= subjects
    assert {"evidence:" + e["id"] for e in draft["evidence"]} <= subjects
    assert {"construct:" + c["id"] for c in draft["constructs"]} <= subjects
    assert "scope" in subjects
    assert len(subjects) == len(sheet["items"]), "a subject appears twice on the sheet"
    assert sheet["stage"] == "registry_review" and sheet["mode"] == "independent"
    # The sheet asks; it never answers. Nothing on it may arrive pre-decided.
    assert not any(item.get("decision") or item.get("human_votes") for item in sheet["items"])
    assert all(item["require_reason"] for item in sheet["items"])


# --- the source-first table ---------------------------------------------------


@pytest.fixture(scope="module")
def props() -> dict:
    return catalog_mod.load_properties()


def test_the_source_first_table_agrees_with_the_catalog(catalog, props):
    assert catalog_mod.property_problems(catalog, props) == []


def test_the_table_is_extracted_source_first_and_mapped_second(catalog, props):
    """The round of 2026-09-13 collected evidence for candidates already on the
    table; this table goes the other way and has to be able to say what the
    sources define that the catalog does not cover."""
    counts = props["counts"]
    assert counts["properties"] == sum(len(s["properties"]) for s in props["sources"])
    assert counts["properties_mapped"] + counts["properties_unmapped"] == counts["properties"]
    read = {s["id"] for s in props["sources"] if s["read"] == "full_text"}
    assert read == {s["id"] for s in catalog["sources"] if s["verification"] == "full_text"}
    for s in props["sources"]:
        if s["read"] == "full_text" and s["defines_note_quality"]:
            for p in s["properties"]:
                assert p["quote"] and p["location"], p["pid"]
    # The methodological sources define no property of a note and say so.
    for sid in ("S11", "S12", "S15", "S16", "S17"):
        entry = next(s for s in props["sources"] if s["id"] == sid)
        assert not entry["defines_note_quality"] and entry["properties"] == []


def test_every_literature_candidate_rests_on_a_source_property(catalog, props):
    covered = props["coverage"]
    for c in catalog["candidates"]:
        if c["origin"] == "literature":
            assert covered[c["id"]], f"{c['id']} claims a literature origin with nothing behind it"
    without = {row["id"] for row in props["candidates_without_source_property"]}
    assert without == {"K06"}
    assert next(c for c in catalog["candidates"] if c["id"] == "K06")["origin"] == (
        "empirical_observation"
    )


def test_a_property_no_candidate_covered_was_opened_and_then_decided(catalog, props):
    """Two properties the sources define fit no candidate on 2026-09-20. They
    were recorded as open with a proposed disposition, and on 2026-09-21 the
    investigator decided both, one against the proposal. The record keeps the
    history: the open rows stay, carry the decision, and now map to K32 and
    K33; nothing in the table is unmapped without an explanation."""
    open_rows = {row["pid"]: row for row in catalog["open_source_properties"]}
    assert set(open_rows) == {"S1-p13", "S4-p09", "S_abs_tednq-p02a", "S_abs_tednq-p02b"}
    assert "adopted as K32" in open_rows["S1-p13"]["disposition"]
    assert "adopted as K33" in open_rows["S4-p09"]["disposition"]
    by_pid = {p["pid"]: p for s in props["sources"] for p in s["properties"]}
    assert by_pid["S1-p13"]["maps_to"] == ["K32"]
    assert by_pid["S4-p09"]["maps_to"] == ["K33"]
    unmapped = {row["pid"] for row in props["unmapped_properties"]}
    assert not (unmapped & set(open_rows))
    by_id = {c["id"]: c for c in catalog["candidates"]}
    assert by_id["K32"]["origin"] == by_id["K33"]["origin"] == "literature"
    assert "2026-09-21" in by_id["K32"]["origin_note"]
    # The two rows opened on 2026-10-05 are a part of a bundled property and are
    # not decided yet: they carry a proposal and name the row they came out of.
    for pid in ("S_abs_tednq-p02a", "S_abs_tednq-p02b"):
        assert open_rows[pid]["part_of"] == "S_abs_tednq-p02"
        assert open_rows[pid]["proposal"] and "disposition" not in open_rows[pid]
    decided = next(r for r in catalog["revisions"] if "open source properties" in r["reason"])
    assert "against" in decided["changes"][0]


def test_the_page_carries_the_source_first_table(catalog, props):
    page = PAGE.read_text(encoding="utf-8")
    assert 'id="source-properties"' in page
    for s in props["sources"]:
        assert f'id="props-{s["id"]}"' in page
    assert "Open properties: found in a source, covered by no candidate" in page


# --- public safety ----------------------------------------------------------

DIACRITIC = re.compile(
    "[" + "\u011b\u0161\u010d\u0159\u017e\u00fd\u00e1\u00ed\u00e9\u00fa\u016f\u0148\u0165\u010f"
    "\u011a\u0160\u010c\u0158\u017d\u00dd\u00c1\u00cd\u00c9\u00da\u016e\u0147\u0164\u010e]"
)


@pytest.mark.parametrize(
    "path",
    [
        CATALOG / "catalog.json",
        CATALOG / "source-properties.json",
        CATALOG / "draft-registry.json",
        CATALOG / "conversion-diagnostics.json",
        CATALOG / "catalog.py",
        CATALOG / "render_catalog.py",
        CATALOG / "convert_to_registry.py",
        PAGE,
    ],
)
def test_the_catalog_files_are_public_safe(path):
    text = path.read_text(encoding="utf-8")
    if path.name != "draft-registry.json":
        assert not DIACRITIC.search(text), f"{path.name} carries Czech text"
    assert "C:\\" not in text and "/Users/" not in text and "local/" not in text
    assert not re.search(r"(?i)(api[_-]?key|token)\s*[:=]\s*\S{8,}", text)
    assert b"\r\n" not in path.read_bytes()


def _czech_strings(value) -> set[str]:
    if isinstance(value, str):
        return {value} if DIACRITIC.search(value) else set()
    if isinstance(value, dict):
        return set().union(*(_czech_strings(v) for v in value.values())) if value else set()
    if isinstance(value, list):
        return set().union(*(_czech_strings(v) for v in value)) if value else set()
    return set()


def test_the_draft_carries_no_czech_but_the_authored_operational_wording(operational, draft):
    """The draft registry is the one derived file that holds Czech, because the
    raters' rules have to exist in Czech before the freeze. Every Czech string
    in it must be one that `operational.json`, the authored and marked file,
    put there; a transcript fragment could not get in through the converter
    without appearing here as an unexplained string."""
    authored = _czech_strings([m["cs"] for m in operational["methods"]]) | _czech_strings(
        [x["cs"] for x in operational["measurements"]]
    )
    assert authored, "the operational wording exists in Czech"
    assert _czech_strings(draft) == authored
