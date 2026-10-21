"""The audit must find a planted defect, not merely report zero.

An independent review of the self-audit on 2026-10-22 made one finding that
mattered more than the others: *"The gate enforces the checker's answer, not its
detection ability."* It proved it by replacing one pattern with a never-matching
one, which took the live count from one to zero; regenerating the saved report
then satisfied the only test that looked. Narrowing a check was indistinguishable
from repairing the data.

Every test here hands the checker an input with a defect in it and requires the
defect to come back. Each one is an input the review constructed and the checker
of that day passed:

    a governing version followed by a colon        operational.json said 2.3.0
    a Czech label that is only a quotation         the exemption stripped it away
    the adjective form of "measured"               the filter buttons used it
    a dated count beside a current one            the exemption covered the line
    a generation-2 row in the ledger              the claim and the totals both lied

And each has its opposite beside it: the historical sentence that must stay
spared, the sentence that explains the old label by quoting it, the repaired
label. A check that catches everything is as useless as one that catches
nothing, and both halves have to hold at once.

This file carries no Czech of its own. The Czech it needs is built from code
points, so that the file checking for Czech does not need an exception for it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GEN2 = REPO / "research" / "gen2"

#: Built rather than written, so this file holds no Czech. "MERI SE", "Jen
#: merene", "Jen nemerene", "NAVRZENO K MERENI" and the quotation marks.
E, R, I_, EE, ZZ = chr(0x11A), chr(0x158), chr(0xCD), chr(0x11B), chr(0x17D)
R_ = chr(0x159)
LOW_E, LOW_I = chr(0x11B), chr(0xED)
OPEN_Q, CLOSE_Q = chr(0x201E), chr(0x201C)
MERI_SE = f"M{E}{R}{I_} SE"
JEN_MERENE = f"Jen m{LOW_E}{R_}en{chr(0xE9)}"
JEN_NEMERENE = f"Jen nem{LOW_E}{R_}en{chr(0xE9)}"
NAVRZENO = f"NAVR{ZZ}ENO K M{E}{R}EN{I_}"


def _module(name: str):
    spec = importlib.util.spec_from_file_location(f"gen2_{name}", GEN2 / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"gen2_{name}"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def audit():
    return _module("audit")


@pytest.fixture(scope="module")
def state():
    return _module("state")


# --- C1, which is a registry because no pattern could do it ------------------


def test_a_registered_pool_count_is_checked_against_the_list(audit, monkeypatch):
    """A registered phrase whose number is wrong must come back as a finding.

    Four patterns were tried before this became a registry, and the last one
    failed because "38 candidates rest on at least one source property" is a
    correct statement about a part of the pool and reads exactly like a stale
    statement about its size.
    """
    monkeypatch.setattr(
        audit, "POOL_CLAIMS", (("research/gen2/catalog/catalog.json", "{n} candidates in a row"),)
    )
    found = audit.c1_pool([])
    assert len(found) == 1
    assert found[0]["holds"] == len(audit.load("research/gen2/catalog/catalog.json")["candidates"])


def test_the_registry_names_phrases_that_are_actually_published(audit):
    """An entry nobody publishes any more detects nothing and must be removed.

    This is the sensitivity test for a registry: it cannot be weakened by
    tightening a pattern, only by deleting an entry, so what has to be checked is
    that every entry still points at a sentence that exists.
    """
    assert audit.POOL_CLAIMS, "an empty registry detects no pool count at all"
    truth = len(audit.load("research/gen2/catalog/catalog.json")["candidates"])
    for name, template in audit.POOL_CLAIMS:
        assert template.format(n=truth) in audit.text_of(name), (
            f"{name} no longer publishes {template!r}; the entry detects nothing"
        )


def test_what_the_wide_net_catches_is_reported_and_not_counted(audit):
    """Kept so that tightening the registry cannot make anything invisible."""
    report = audit.run()
    assert report["counts"]["to_triage"] == len(report["to_triage"])
    assert report["to_triage_note"].strip()
    for row in report["to_triage"]:
        assert set(row) == {"path", "says", "line"}


# --- C2, the version presented as governing ----------------------------------


def test_a_governing_version_followed_by_a_colon_is_found(audit):
    """The case the narrowed lookahead rejected, and the defect it hid."""
    line = "Feasibility pilot under research protocol 2.3.0: the two public AnnoMI"
    assert audit.VERSION.search(line), "a colon introduces a governing scope"


@pytest.mark.parametrize(
    "line",
    [
        "repaired on 2026-09-15 by commit 4da6055. Protocol 2.1.0 lists the",
        "Arrived after protocol 2.7.0 froze the round's measured set at 16",
        "bounded by decision D6 in protocol 2.1.0.",
    ],
)
def test_a_historical_version_reference_is_not_a_finding(audit, line):
    """Thirteen true sentences about the past were reported as faults once."""
    assert not audit.VERSION.search(line)


# --- C6, the Czech word that asserted a measurement --------------------------


def test_a_label_that_is_only_a_quotation_is_found(audit):
    """The exemption stripped the whole label away and what was left matched nothing."""
    label = f"{OPEN_Q}{MERI_SE}{CLOSE_Q}"
    assert audit.MEASURES.search(audit.without_quotations(label))


def test_a_sentence_that_explains_the_old_label_is_not_a_finding(audit):
    """Why the exemption exists: the page says what the rows used to read."""
    explains = (
        f"Do 21. 10. 2026 st{chr(0xE1)}lo u tmav{chr(0xFD)}ch {R_}{chr(0xE1)}dk"
        f"{chr(0x16F)} {OPEN_Q}m{LOW_E}{R_}{LOW_I} se{CLOSE_Q}, anglicky jinak."
    )
    assert not audit.MEASURES.search(audit.without_quotations(explains))


def test_the_adjective_form_is_found(audit):
    """The filter buttons partitioned the criteria into measured and unmeasured."""
    assert audit.MEASURES.search(JEN_MERENE)


@pytest.mark.parametrize("spared", [NAVRZENO, JEN_NEMERENE])
def test_the_repaired_and_the_negated_forms_are_not_findings(audit, spared):
    """A pattern that reported the repair as the defect would be worse than none."""
    assert not audit.MEASURES.search(spared)


# --- the exemptions that are left, and the one that is not ------------------


def test_there_is_no_sentence_level_exemption(audit):
    """It existed for one sentence, acquired two loopholes, and is gone.

    It exempted a value whose sentence dated it, for the panel's registration
    saying the pool was 34 items on the day the rule was registered. The review
    found both of its holes: it covered the whole line, so a current claim beside
    a dated one went quiet too, and it was evaluated against a truncated copy of
    the line, so whether it fired depended on how long the surrounding field name
    was -- which is what made the committed zero go stale.

    It is unreachable now in any case: C1 is a registry, and its wide net stopped
    counting "items" as a word that means a candidate, so that sentence matches
    nothing. A dead exemption reads as a safeguard and is only a surface, so this
    asserts it stays gone.
    """
    assert not hasattr(audit, "dated_sentence")
    assert not hasattr(audit, "DATED_SENTENCES")
    assert "dated_sentence" not in (GEN2 / "audit.py").read_text(encoding="utf-8")


def test_a_record_level_exemption_says_which_record_and_why(audit):
    """What is left: a whole file, named, with a reason, and nothing wider."""
    assert audit.DATED_RECORDS
    for path, why in audit.DATED_RECORDS.items():
        assert (REPO / path).exists(), f"{path} is exempt and is not there"
        assert len(why.split()) >= 5, f"{path} is exempt for {why!r}"


# --- the state file ---------------------------------------------------------


def test_a_generation_two_row_flips_the_claim_and_stays_out_of_generation_one(state):
    """Handed one, the builder said measured and "no note has been written" at once."""
    planted = [
        {"track": "tneval-soap", "prompt_version": "tneval-soap-v1", "judge_model": "j1"},
        {"track": "gen2-continuity", "prompt_version": "gen2-profiles-v1", "judge_model": "j2"},
    ]
    report = state.generations(planted)
    two = report["generation_2"]
    assert two["measured"] is True and two["rows"] == 1
    assert "has rows in the result ledger" in two["what_that_means"]
    assert "no note has been written" not in two["what_that_means"].lower()

    one = report["generation_1"]
    assert one["rows"] == 1
    assert "gen2-continuity" not in one["tracks"]
    assert "gen2-profiles-v1" not in one["prompt_versions"]
    assert one["judges"] == ["j1"]


def test_with_no_generation_two_row_it_says_what_it_cannot_see(state):
    """The ledger's silence is evidence about the ledger, not about the notes."""
    report = state.generations(
        [{"track": "icare", "prompt_version": "icare-zeroshot-v1", "judge_model": "j"}]
    )
    two = report["generation_2"]
    assert two["measured"] is False
    assert "pipeline.py" in two["what_this_does_not_establish"]
    assert "gitignored" in two["what_this_does_not_establish"]
