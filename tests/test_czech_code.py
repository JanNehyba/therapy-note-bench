"""The coding harness, and the two gates that make its output checkable.

Nothing here calls a model. Every test is about what the harness does with an
answer once it has one, because that is where the two failures this study is most
exposed to would occur: a coder that writes a quotation instead of copying one,
and a coder whose silence gets read as "no".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import czech_code  # noqa: E402
import czech_units  # noqa: E402

NOTE = {
    "subjective": "Klientka popisuje přetížení prací. Uvádí chronickou únavu.",
    "objective": "Řeč je plynulá, bez známek zpomalení.",
    "assessment": "Stav odpovídá dlouhodobému přetížení.",
    "plan": "Zaměřit se na hranice v zaměstnání.",
}


def units():
    return czech_units.split_note(NOTE)


def test_a_span_that_is_in_the_unit_passes():
    assert czech_code.check_span("přetížení prací", "Klientka popisuje přetížení prací.")


def test_a_span_the_coder_wrote_rather_than_copied_is_caught():
    """The whole point of the gate.

    A paraphrase is the shape a fabricated quotation takes: plausible, on topic,
    and not in the text. Nothing fuzzier than an exact substring will catch it,
    which is why the match deliberately is not fuzzy.
    """
    assert not czech_code.check_span(
        "klientka je přetížená v práci", "Klientka popisuje přetížení prací."
    )


def test_whitespace_is_collapsed_before_the_comparison():
    """A line break inside a copied span is a formatting difference, not a lie."""
    assert czech_code.check_span("přetížení   prací", "Klientka popisuje přetížení\nprací.")


def test_an_empty_span_never_passes():
    assert not czech_code.check_span("", "Klientka popisuje přetížení prací.")


def test_a_discarded_span_is_counted_and_the_row_survives():
    """The row is kept with `span_valid` False rather than dropped silently.

    Dropping it would hide the discard from the rate that is supposed to expose
    it, which is the shape of every "an absence is never a measurement" bug this
    repository has met.
    """
    tally = czech_code.Tally()
    parsed = {
        "units": [
            {
                "unit_index": 0,
                "splittable": False,
                "codes": [
                    {"name": "popis přetížení", "span": "přetížení prací"},
                    {"name": "vymyšlený kód", "span": "tohle v textu není"},
                ],
            }
        ]
    }
    rows = czech_code.rows_from_open(parsed, units(), tally)
    assert len(rows) == 2
    assert tally.spans_checked == 2
    assert tally.spans_discarded == 1
    assert [row["span_valid"] for row in rows] == [True, False]


def test_unclear_is_kept_as_itself_and_never_folded_into_absent():
    """The oldest rule in this repository, at the level of one verdict."""
    tally = czech_code.Tally()
    codebook = {"unsupported": {"question": "Tvrdí celek něco nepozorovatelného?"}}
    parsed = {"units": [{"i": 0, "v": {"unsupported": "u"}}]}
    rows = czech_code.rows_from_deductive(parsed, units(), codebook, tally)
    assert rows[0]["value"] == "unclear"


def test_not_applicable_is_kept_as_itself_too():
    tally = czech_code.Tally()
    codebook = {"quotes": {"question": "Cituje celek klientku doslova?"}}
    parsed = {"units": [{"i": 0, "v": {"quotes": "n"}}]}
    rows = czech_code.rows_from_deductive(parsed, units(), codebook, tally)
    assert rows[0]["value"] == "not-applicable"


def test_a_category_the_coder_did_not_answer_is_none_not_absent():
    """Silence is recorded as silence.

    Reading "not answered" as "no fault here" is the failure that gave a model a
    perfect temporal score for writing nothing, and it is the same failure at a
    smaller scale.
    """
    tally = czech_code.Tally()
    codebook = {
        "asked": {"question": "První otázka?"},
        "never_answered": {"question": "Druhá otázka?"},
    }
    parsed = {"units": [{"i": 0, "v": {"asked": "a"}}]}
    rows = czech_code.rows_from_deductive(parsed, units(), codebook, tally)
    values = {row["category"]: row["value"] for row in rows}
    assert values["asked"] == "absent"
    assert values["never_answered"] is None


def test_a_value_outside_the_four_becomes_none():
    tally = czech_code.Tally()
    codebook = {"unsupported": {"question": "Otázka?"}}
    parsed = {"units": [{"i": 0, "v": {"unsupported": "maybe"}}]}
    rows = czech_code.rows_from_deductive(parsed, units(), codebook, tally)
    assert rows[0]["value"] is None


def test_a_present_verdict_without_a_usable_span_is_counted_as_a_discard():
    tally = czech_code.Tally()
    codebook = {"unsupported": {"question": "Otázka?"}}
    parsed = {"units": [{"i": 0, "v": {"unsupported": "p"}, "s": {"unsupported": "není tam"}}]}
    czech_code.rows_from_deductive(parsed, units(), codebook, tally)
    assert tally.spans_checked == 1
    assert tally.spans_discarded == 1


def test_only_a_present_verdict_spends_a_span_check():
    """An `absent` verdict has nothing to quote, so it is not a discard."""
    tally = czech_code.Tally()
    codebook = {"unsupported": {"question": "Otázka?"}}
    parsed = {"units": [{"i": 0, "v": {"unsupported": "a"}}]}
    czech_code.rows_from_deductive(parsed, units(), codebook, tally)
    assert tally.spans_checked == 0
    assert tally.spans_discarded == 0


def test_a_unit_the_coder_invented_is_ignored():
    """An index that was never sent cannot be an answer to anything."""
    tally = czech_code.Tally()
    parsed = {"units": [{"unit_index": 999, "codes": [{"name": "x", "span": "y"}]}]}
    assert czech_code.rows_from_open(parsed, units(), tally) == []
    assert tally.units_answered == 0


def test_an_answer_that_is_not_json_is_a_failure_not_an_empty_reading():
    assert czech_code.parse_json("Omlouvám se, ale nemohu odpovědět.") is None
    assert czech_code.parse_json("") is None


def test_json_is_recovered_from_a_code_fence():
    parsed = czech_code.parse_json('Tady je výsledek:\n```json\n{"units": []}\n```')
    assert parsed == {"units": []}


def test_the_coder_is_shown_no_model_name_and_no_score():
    """Blinding, asserted rather than trusted to the prompt builder."""
    rendered = czech_code.render_units(units())
    prompt = czech_code.build_prompt(units(), None)
    for leak in ("qwen", "glm-5", "deepseek", "kimi", "gemma", "cz-r-"):
        assert leak not in rendered.lower()
        assert leak not in prompt.lower()


def test_the_open_prompt_carries_no_codebook():
    """The inductive guarantee: a coder told what to look for finds it."""
    prompt = czech_code.build_prompt(units(), None)
    assert "KATEGORIE" not in prompt


def test_the_deductive_prompt_carries_exactly_the_codebook_it_was_given():
    """Codebook shown must equal codebook sent -- the audit invariant."""
    codebook = {"unsupported": {"question": "Tvrdí celek něco nepozorovatelného?"}}
    prompt = czech_code.build_prompt(units(), codebook)
    assert "unsupported" in prompt
    assert "Tvrdí celek něco nepozorovatelného?" in prompt
    assert "quotes" not in prompt


def test_a_cached_answer_to_a_different_question_is_not_reused(tmp_path):
    """The cache is keyed on what was asked, as the judge cache has been since
    re-scoring a regenerated note reused the judgement of the text it replaced."""
    path = tmp_path / "note.json"
    path.write_text(json.dumps({"prompt_sha256": "aaa", "answer": "{}"}), encoding="utf-8")
    assert czech_code.load_cached(path, "aaa") is not None
    assert czech_code.load_cached(path, "bbb") is None


def test_every_rejected_coder_is_named_with_its_reason():
    """A panel of two is a finding about the endpoint, not a design preference.

    Each candidate failed for its own measured reason and each is written down,
    so that a reader cannot mistake the size of the panel for a choice.
    """
    assert czech_code.MISSING_CODER["planned"] > czech_code.MISSING_CODER["actual"]
    assert czech_code.MISSING_CODER["actual"] == len(czech_code.PANEL)
    for model, reason in czech_code.REJECTED_CODERS.items():
        assert len(reason) > 40, model


def test_the_cost_of_a_two_coder_panel_is_stated():
    """With two coders there is no majority, so nothing can be adjudicated."""
    assert "no majority" in czech_code.MISSING_CODER["cost"]


def test_every_coder_names_the_systems_it_shares_a_vendor_with():
    for coder in czech_code.PANEL:
        assert coder.in_family, coder.model


def test_the_einfra_concurrency_stays_at_two():
    """Not a style choice: six concurrent requests drew 429 on a third of calls,
    and the key is one person's academic quota."""
    assert czech_code.EINFRA_CONCURRENCY == 2


def test_the_same_verdict_written_twice_is_stored_once(tmp_path):
    """The repair for a bug that reached a published number.

    The output used to be opened in append mode. A partial rebuild followed by a
    full run left a quarter of the file duplicated, and the sentence counts in
    the briefing were inflated by exactly that much. The rates survived -- a
    duplicate doubles a numerator and its denominator together -- so nothing
    looked wrong until the counts were read.
    """
    target = tmp_path / "codes.jsonl"
    rows = [
        {
            "coder": "A",
            "system_id": "m",
            "session_id": "s",
            "unit_index": 0,
            "category": "restatement",
            "value": "present",
        }
    ]
    assert czech_code._write_rows(target, rows) == (1, 0)
    written, replaced = czech_code._write_rows(target, rows)
    assert (written, replaced) == (1, 1)
    assert len(target.read_text(encoding="utf-8").strip().split("\n")) == 1


def test_a_rerun_overwrites_its_own_verdict_rather_than_keeping_both(tmp_path):
    """An older answer to the same question is not a second measurement."""
    target = tmp_path / "codes.jsonl"
    key = {
        "coder": "A",
        "system_id": "m",
        "session_id": "s",
        "unit_index": 0,
        "category": "restatement",
    }
    czech_code._write_rows(target, [{**key, "value": "absent"}])
    czech_code._write_rows(target, [{**key, "value": "present"}])
    stored = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
    assert len(stored) == 1
    assert stored[0]["value"] == "present"


def test_two_different_verdicts_are_two_rows(tmp_path):
    """Different coder, different unit or different category is a different key."""
    target = tmp_path / "codes.jsonl"
    base = {"system_id": "m", "session_id": "s", "unit_index": 0, "category": "restatement"}
    written, replaced = czech_code._write_rows(
        target,
        [
            {**base, "coder": "A", "value": "present"},
            {**base, "coder": "B", "value": "absent"},
            {**base, "coder": "A", "unit_index": 1, "value": "absent"},
            {**base, "coder": "A", "category": "client_quotation", "value": "absent"},
        ],
    )
    assert (written, replaced) == (4, 0)
