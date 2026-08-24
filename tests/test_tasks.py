"""The prompts, checked against the sources they were copied from.

Every assertion here is about fidelity, not about taste. If a prompt drifts from
its published wording our numbers stop being comparable with the paper's, and
that failure is silent unless something like this catches it. No test reaches the
network; ``tnb prompts --verify`` is the online counterpart.
"""

from __future__ import annotations

import hashlib

import pytest

from tnb import tasks
from tnb.datasets.base import Session, Turn
from tnb.tasks import icare, soap

CONVERSATION = Session(
    id="42",
    source="tneval",
    turns=(
        Turn("therapist", "How was your week?"),
        Turn("client", "Rough."),
        Turn("client", "I drank again."),
    ),
)


# --- TN-Eval SOAP ----------------------------------------------------------


def test_soap_template_is_byte_identical_to_tn_evals():
    """The digest is of TN-Eval's published template, trailing spaces included.
    Reformatting the prompt to look tidier would change what is measured."""
    digest = hashlib.sha256(soap.PROMPT_TEMPLATE_SOAP.encode()).hexdigest()
    assert digest == soap.UPSTREAM_SHA256


def test_soap_prompt_is_assembled_the_way_tn_eval_assembles_it():
    """template + transcript + "\\n\\nSOAP Note:\\n", with their leading blank
    line and their lowercase speaker labels."""
    prompt = soap.build_prompt(CONVERSATION)
    assert prompt.startswith(soap.PROMPT_TEMPLATE_SOAP)
    assert prompt.endswith("\n\nSOAP Note:\n")
    assert "\n\n\ntherapist: How was your week?\nclient: Rough." in prompt


def test_soap_repair_attempts_accumulate_like_the_original_loop():
    """TN-Eval re-append the same sentence on each failed parse and keep the
    earlier copies. A single copy would be a different prompt."""
    assert soap.build_prompt(CONVERSATION, attempt=2).count(soap.REPAIR_SENTENCE) == 2


def test_soap_parses_a_note_out_of_surrounding_prose():
    """Models wrap the dictionary in explanations and code fences; TN-Eval slice
    from the first brace, so we do too."""
    answer = 'Sure!\n```json\n{"Subjective": "a", "Objective": "b", '
    answer += '"Assessment": "c", "Plan": "d"}\n```\nHope this helps.'
    assert soap.parse_note(answer) == {
        "subjective": "a",
        "objective": "b",
        "assessment": "c",
        "plan": "d",
    }


@pytest.mark.parametrize(
    "answer",
    [
        "I am sorry, I cannot help with that.",
        '{"Subjective": "a"}',
        '{"Subjective": "a", "Objective": "b", "Assessment": "c", "Plan": "d", "Extra": "e"}',
        "{not json at all}",
    ],
)
def test_soap_refuses_to_invent_a_note(answer):
    """A refusal, a truncated answer and a four-empty-sections note must stay
    distinguishable, or a model gets scored on something it never wrote."""
    assert soap.parse_note(answer) is None


# --- iCARE -----------------------------------------------------------------

INSTRUCTIONS = [f"Instruction {index}." for index in range(1, 18)]


def test_icare_builds_one_prompt_per_section():
    prompts = icare.build_prompts(CONVERSATION, INSTRUCTIONS)
    assert [p.number for p in prompts] == list(range(1, 18))
    assert [p.unit for p in prompts][:2] == ["section-01", "section-02"]


def test_icare_prompt_matches_the_baseline_wording():
    """Reproduced from iCARE's PromptGen, including the 'Nil' clause and the
    two ### markers."""
    first = icare.build_prompts(CONVERSATION, INSTRUCTIONS)[0]
    assert first.prompt == (
        "You're a helpful mental health assistant and follow the given instructions "
        "carefully. Instruction 1. If no information is available, write 'Nil' only. "
        "###Dialog###: #Therapist#: How was your week? #Patient#: Rough. I drank again. "
        "###Summary Response###: "
    )


def test_icare_merges_consecutive_turns_by_the_same_speaker():
    """Their diarised CSV splits one speech over many rows and the marker is
    written once. Repeating it per turn would be a different transcript."""
    assert icare.render_dialog(CONVERSATION).count(icare.PATIENT_MARKER) == 1


def test_icare_marks_the_two_sections_the_paper_says_everyone_fails():
    """Sections 5 and 17 get their own leaderboard column; they have to be
    identifiable from the generation record onwards."""
    temporal = [p.number for p in icare.build_prompts(CONVERSATION, INSTRUCTIONS) if p.is_temporal]
    assert temporal == [5, 17]


def test_icare_refuses_a_changed_number_of_sections():
    """If upstream adds a section, the temporal indices are wrong and the whole
    track needs rechecking. Fail loudly instead."""
    with pytest.raises(RuntimeError, match="17"):
        icare.build_prompts(CONVERSATION, INSTRUCTIONS[:16])


# --- registry --------------------------------------------------------------


def test_units_carry_the_prompt_version_the_cache_is_keyed_on():
    units = tasks.TASKS["soap"].build_units(CONVERSATION)
    assert len(units) == 1
    assert units[0].prompt_version == soap.PROMPT_VERSION
    assert units[0].unit == "note"


def test_resolve_rejects_an_unknown_task():
    with pytest.raises(RuntimeError, match="Unknown task"):
        tasks.resolve("soap,sopa")


def test_resolve_defaults_to_both_tracks():
    assert [task.name for task in tasks.resolve(None)] == ["soap", "icare"]


def test_the_seventeen_section_labels_stay_in_step_with_the_prompts():
    """The labels are for display; the prompts are fetched at run time. If
    upstream ever changes the count, the page would quietly show the old form."""
    assert len(icare.SECTION_TITLES) == 17
    assert icare.SECTION_TITLES[4] == "Past session information", "section 5 is temporal"
    assert icare.SECTION_TITLES[16] == "Next session details", "section 17 is temporal"


def test_the_labels_are_names_not_someone_elses_prompt():
    """iCARE publishes no licence, so this repository shows field names and
    never republishes their instruction text."""
    assert all(len(title) < 60 for title in icare.SECTION_TITLES)
    assert not any("helpful mental health assistant" in t for t in icare.SECTION_TITLES)
