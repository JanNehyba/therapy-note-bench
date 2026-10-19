"""Whether the task asks for the property the catalog says matters.

Nineteen candidates carry an operational rule and every candidate carries a
relevance level per note purpose, and nothing bound the two to the instruction
the model is actually given. A property the task never raises can still be
measured, and the model is then marked down for not doing what nobody asked.

Pinned here: the artefact equals a fresh build, every pair that could be measured
is audited, a fragment nobody can find in the instruction fails the build rather
than reaching the file, and the one live case -- a measurement of this round
running at two purposes whose task never raises its subject -- is named and
cannot grow without this test changing.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CATALOG_DIR = REPO / "research" / "gen2" / "catalog"
ARTEFACT = CATALOG_DIR / "prompt-coverage.json"


def _module(name: str):
    spec = importlib.util.spec_from_file_location(name, CATALOG_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


coverage = _module("prompt_coverage")


@pytest.fixture(scope="module")
def catalog() -> dict:
    return json.loads((CATALOG_DIR / "catalog.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def operational() -> dict:
    return json.loads((CATALOG_DIR / "operational.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(ARTEFACT.read_text(encoding="utf-8"))


def test_the_artefact_equals_a_fresh_build(catalog, operational, report):
    assert report == coverage.build(catalog, operational), (
        "prompt-coverage.json is stale -- run research/gen2/catalog/prompt_coverage.py"
    )


def test_nothing_that_could_be_measured_is_left_unaudited(catalog, operational):
    """The scope is derived, so the audit cannot quietly stop covering something.

    A new candidate with a rule, a relevance level raised to high, or a
    measurement pointed at another purpose all make this fail. The first run
    showed why it has to be derived: the measurements name their purposes
    independently of the relevance levels, so the high pairs were not the
    measured pairs and four of the latter were unexamined.
    """
    found = coverage.problems(catalog, operational, coverage.assembled())
    coverage.shape_of_the_czech(found)
    assert found == []


def test_a_fragment_that_is_not_in_the_instruction_fails_the_build(
    catalog, operational, monkeypatch, tmp_path
):
    """The rule the review's own source quotes are held to, applied to our own prompt.

    A covered row rests on a fragment of the instruction. If the fragment is not
    there, the row is a claim about a text that does not exist, so the build has
    to refuse rather than write it and let a reader check the quote by hand.
    """
    doctored = (
        ("K01", coverage.PROFILES, coverage.COVERED, "rules", "Consult the oracle.", None),
    ) + coverage.AUDIT[1:]
    monkeypatch.setattr(coverage, "AUDIT", doctored)
    found = coverage.problems(catalog, operational, coverage.assembled())
    assert any("the fragment is not in the instruction" in line for line in found)

    monkeypatch.setattr(coverage, "OUT", tmp_path / "prompt-coverage.json")
    assert coverage.main() == 2
    assert not list(tmp_path.iterdir()), "a refused build wrote a file anyway"


def test_a_gap_says_what_is_missing_and_quotes_nothing(catalog, operational, monkeypatch):
    """A gap that quoted the instruction would be a covered row wearing the wrong word."""
    doctored = (
        ("K01", coverage.PROFILES, coverage.GAP, "rules", "Use only the supplied sources.", "x"),
    ) + coverage.AUDIT[1:]
    monkeypatch.setattr(coverage, "AUDIT", doctored)
    found = coverage.problems(catalog, operational, coverage.assembled())
    assert any("a gap quotes the instruction" in line for line in found)

    silent = (("K01", coverage.PROFILES, coverage.GAP, "rules", None, None),) + coverage.AUDIT[1:]
    monkeypatch.setattr(coverage, "AUDIT", silent)
    found = coverage.problems(catalog, operational, coverage.assembled())
    assert any("a gap says nothing" in line for line in found)


def test_the_live_defect_is_named_and_cannot_grow_in_silence(report):
    """One measurement of this round runs where its task never raises the subject.

    M08 measures non-stigmatising language at the continuity and audit purposes.
    Neither instruction mentions stigma or how the client is written about, so a
    score from it would be a model marked down for an instruction it never got.
    The list is pinned: another such pair needs an edit here, which is the point.
    """
    assert report["measured_at_a_purpose_whose_task_does_not_ask"] == [
        "K14/audit",
        "K14/continuity",
    ]
    assert report["counts"]["measured_at_a_purpose_whose_task_does_not_ask"] == 2
    says = report["what_has_to_happen_before_the_round_runs"]
    for option in ("gains a clause", "stops running", "gap named beside it"):
        assert option in says


def test_each_measurement_is_compared_with_where_the_catalog_says_it_matters(
    report, operational, catalog
):
    """The purposes a measurement runs at were chosen apart from the relevance levels.

    Two of the three run at no purpose the catalog rates high for their
    construct: M07 measures economy at continuity and audit when only the client
    purpose rates it high, and M08 measures non-stigmatising language at the two
    purposes that rate it medium while the two that rate it high go unmeasured.
    Nothing compared the two choices before this.
    """
    against = {entry["measurement"]: entry for entry in report["measurements_against_relevance"]}
    assert set(against) == {x["id"] for x in operational["measurements"]}
    by_id = {c["id"]: c for c in catalog["candidates"]}
    for entry in against.values():
        relevance = by_id[entry["candidate"]]["relevance"]
        assert entry["relevance_where_it_runs"] == {
            purpose: relevance[purpose] for purpose in entry["runs_at"]
        }
        for purpose in entry["high_purposes_it_does_not_run_at"]:
            assert relevance[purpose] == "high"
            assert purpose not in entry["runs_at"]
    assert against["M07"]["high_purposes_it_does_not_run_at"] == ["client"]
    assert against["M08"]["high_purposes_it_does_not_run_at"] == ["client", "supervision"]


def test_the_artefact_says_what_it_does_not_establish(report):
    """The readings are the assistant's, and the file may not imply otherwise."""
    said = report["what_it_does_not_establish"]
    assert "reading" in said and "assistant" in said
    assert "same shape and not to the same meaning" in said
    assert report["marker"] == "AUTHORED-INSTRUMENT-TEXT"
    assert report["profiles_version"]
