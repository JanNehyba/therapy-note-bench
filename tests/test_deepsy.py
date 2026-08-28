"""The Deepsy task: the prompts it reproduces and the replies it accepts.

Offline throughout. One test reads the Deepsy repository when it is beside this
one and skips when it is not, which is the only way a reproduction can be
checked rather than asserted.
"""

from __future__ import annotations

import json

import pytest

from tnb import results
from tnb.datasets.base import Session, Turn
from tnb.tasks import deepsy, deepsy_prompts

UPSTREAM = deepsy_prompts.__file__ and (
    __import__("pathlib").Path(__file__).resolve().parent.parent.parent
    / "monitor-notes"
    / "app"
    / "Config"
    / "TherapyNote"
    / "prompts"
)

SESSION = Session(
    id="cz-t-0000abcd",
    source="czech-translated",
    turns=(Turn("client", "dobrý den"), Turn("therapist", "vítejte")),
)


# --- the reproduction -------------------------------------------------------


@pytest.mark.skipif(
    not (UPSTREAM and UPSTREAM.exists()),
    reason="the Deepsy repository is not beside this one",
)
def test_the_prompts_are_the_ones_upstream_holds():
    """A prompt is reproduced word for word or it is a different prompt.

    Checked against the source rather than trusted, because these were copied
    by a script and a script can be re-run against a file that has since moved
    on. `tasks/fidelity.py` does the same for TN-Eval and iCARE; the difference
    is that this upstream is a directory on the same machine, so the check is
    exact instead of being a recorded digest.
    """
    yaml = pytest.importorskip("yaml")

    for section in deepsy.SECTIONS:
        loaded = yaml.safe_load((UPSTREAM / f"{section}.yaml").read_text(encoding="utf-8"))
        upstream = loaded[section]
        assert deepsy_prompts.SYSTEM[section] == upstream["system_message"], section
        assert deepsy_prompts.TEMPLATE[section] == upstream["user_message_template"], section


@pytest.mark.skipif(
    not (UPSTREAM and UPSTREAM.exists()),
    reason="the Deepsy repository is not beside this one",
)
def test_the_settings_are_the_ones_the_application_would_use():
    """`PromptLoader` takes the settings from the first section file and uses
    them for all of them. All three of these declare the same, so there is no
    ambiguity to inherit -- but `dekurz` declares 200 words and narrative
    paragraphs, so the claim is worth checking rather than assuming."""
    yaml = pytest.importorskip("yaml")

    for section in deepsy.SECTIONS:
        settings = yaml.safe_load((UPSTREAM / f"{section}.yaml").read_text(encoding="utf-8"))[
            "settings"
        ]
        assert settings["default_length"] == deepsy_prompts.DEFAULT_LENGTH, section
        assert settings["default_format"] == deepsy_prompts.DEFAULT_FORMAT, section


# --- building one -----------------------------------------------------------


def test_nothing_is_left_unfilled():
    """A placeholder that survives into the prompt is a placeholder the model
    reads as text."""
    for section in deepsy.SECTIONS:
        prompt = deepsy.build_prompt(SESSION, section)
        assert "{" not in prompt.replace('{\n  "', "{").split("Output format (JSON):")[0], section


def test_the_questionnaire_blocks_go_when_there_is_no_questionnaire():
    """The application removes them for a client who has filled nothing in, so
    the prompt this sends is the prompt that client would get. Feeding
    questionnaires would measure which sessions had them."""
    prompt = deepsy.build_prompt(SESSION, "data")

    assert "{if_questionnaire_data}" not in prompt
    assert "Zahrň kvantitativní data z dotazníků" not in prompt
    # ...and the sentence around them is gone, not merely emptied.
    assert "Vyplnění dotazníků není zdroj" not in prompt


def test_a_block_stays_when_its_data_is_supplied():
    """The mechanism is reproduced rather than its outcome: supplying one later
    must not need a second reading of the PHP."""
    prompt = deepsy.build_prompt(SESSION, "data", {"questionnaire_data": "PHQ-9: 14"})

    assert "PHQ-9: 14" in prompt
    assert "Zahrň kvantitativní data z dotazníků" in prompt


def test_the_transcript_is_rendered_the_way_the_czech_soap_task_renders_it():
    """Two tracks that differ in the prompt must not also differ in how the
    session was written down, or a difference between them is about both."""
    prompt = deepsy.build_prompt(SESSION, "data")
    assert "Klient: dobrý den" in prompt
    assert "Terapeut: vítejte" in prompt


def test_removing_a_block_leaves_no_run_of_blank_lines():
    """`PromptLoader` collapses three or more, and a prompt that differs only in
    whitespace is still a different prompt."""
    for section in deepsy.SECTIONS:
        assert "\n\n\n" not in deepsy.build_prompt(SESSION, section), section


def test_an_unknown_section_raises():
    with pytest.raises(ValueError, match="not one of"):
        deepsy.build_prompt(SESSION, "dekurz")


# --- reading one back -------------------------------------------------------


def test_every_key_the_prompt_named_or_nothing():
    """A reply missing a key answered a different question. Letting it through
    would put a note scored on four fields beside one scored on five under the
    same heading."""
    full = json.dumps({key: "x" for key in deepsy.KEYS["plan"]})
    assert deepsy.parse_note(full, "plan") is not None

    short = json.dumps({key: "x" for key in deepsy.KEYS["plan"][:-1]})
    assert deepsy.parse_note(short, "plan") is None

    extra = json.dumps({**{key: "x" for key in deepsy.KEYS["plan"]}, "invented": "x"})
    assert deepsy.parse_note(extra, "plan") is None


def test_a_fenced_reply_is_read_but_still_has_to_parse():
    """Models fence JSON despite being told not to. Stripping the fence is not
    leniency about what is inside it."""
    good = deepsy.parse_note('```json\n{"hypotheses": "- a"}\n```', "clinical_hypotheses")
    assert good == {"hypotheses": "- a"}

    assert deepsy.parse_note("```json\nnot json\n```", "clinical_hypotheses") is None


def test_a_refusal_is_none_and_not_an_empty_note():
    """`scoring/czech.py` treats the two differently and must keep being able
    to: a model that refused is not a model that wrote nothing."""
    for refusal in ("", "   ", "Promiňte, to neumím."):
        assert deepsy.parse_note(refusal, "data") is None


def test_the_rendering_is_ordered_by_the_prompt_and_not_by_the_reply():
    """A model's reply carries whatever order it wrote in. Anything asking
    about structure would then be scoring the order a parser happened to see."""
    backwards = {key: f"v-{key}" for key in reversed(deepsy.KEYS["plan"])}
    rendered = deepsy.render_note(backwards)
    positions = [rendered.index(f"{key}:") for key in deepsy.KEYS["plan"]]
    assert positions == sorted(positions)


def test_an_empty_field_is_shown_and_not_hidden():
    """A model that answered nothing under a heading is shown as having
    answered nothing, not as having been asked less."""
    rendered = deepsy.render_note({"hypotheses": ""})
    assert "hypotheses:" in rendered


# --- where the rows go ------------------------------------------------------


def test_both_tracks_are_local():
    for track in (results.TRACK_DEEPSY_REAL, results.TRACK_DEEPSY_TRANSLATED):
        assert track in results.LOCAL_TRACKS
        assert track not in results.PUBLISHED_TRACKS


def test_the_three_sections_are_the_three_with_a_soap_counterpart():
    """`data` is Subjective and Objective, `clinical_hypotheses` is Assessment,
    `plan` is Plan. That correspondence is what makes the comparison a
    comparison of formats rather than of tasks."""
    assert deepsy.SECTIONS == ("data", "clinical_hypotheses", "plan")
    assert "dekurz" not in deepsy.SECTIONS
    assert "questionnaire_summary" not in deepsy.SECTIONS


# --- the parse must run at generation time, or the repair never fires --------


def test_generation_parses_a_deepsy_section_and_marks_a_bad_one_failed():
    """The parse belongs in generation, not in scoring. Without it a reply that
    is not JSON is stored as `ok: true` with no note, the repair suffix never
    fires, and `PARSE_ATTEMPTS` is dead code -- which is how this shipped for
    thirteen calls before it was caught."""
    from tnb import generation

    job = generation.Job(
        provider="einfra",
        model_id="m",
        task=deepsy.NAME_REAL,
        prompt_version=deepsy.PROMPT_VERSION,
        session_id="cz-r-0000abcd",
        unit="clinical_hypotheses",
        prompt="...",
    )

    provider = _provider()

    good = generation._record(job, provider, _completion('{"hypotheses": "- a"}'), "now", "...")
    assert good["note"] == {"hypotheses": "- a"}
    assert good["ok"] is True

    bad = generation._record(job, provider, _completion("tady je vase poznamka:"), "now", "...")
    assert bad["note"] is None
    assert bad["ok"] is False
    assert "clinical_hypotheses" in bad["error"]


def _provider():
    from tnb.config import GenerationPolicy, Provider

    return Provider(
        name="einfra",
        base_url="https://example.invalid/v1",
        token_env="EINFRA_API_TOKEN",
        generation=GenerationPolicy(temperature=0.0, max_tokens=4096, concurrency=2),
    )


def _completion(text: str):
    from tnb.providers.openai_compatible import Completion

    return Completion(model="m", text=text, ok=True, finish_reason="stop")


# --- assembling three files into one note ------------------------------------


def _section_file(directory, section, note, ok=True):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{section}.json").write_text(
        json.dumps({"ok": ok, "note": note, "unit": section}), encoding="utf-8"
    )


def _full(section):
    return {key: "x" for key in deepsy.KEYS[section]}


def test_a_note_needs_all_three_sections(tmp_path):
    """Two of three is a shorter note, not a note. Scoring it would put a model
    judged on two thirds of its text beside models judged on all of it."""
    from tnb.scoring import deepsy_run

    session = Session(id="cz-r-0000abcd", source="czech-real", turns=())
    unit = tmp_path / "einfra" / deepsy.NAME_REAL / deepsy.PROMPT_VERSION / "m" / session.id

    _section_file(unit, "data", _full("data"))
    _section_file(unit, "plan", _full("plan"))
    assert not list(
        deepsy_run.from_generations([session], task_name=deepsy.NAME_REAL, cache_dir=tmp_path)
    )

    _section_file(unit, "clinical_hypotheses", _full("clinical_hypotheses"))
    candidates = list(
        deepsy_run.from_generations([session], task_name=deepsy.NAME_REAL, cache_dir=tmp_path)
    )
    assert len(candidates) == 1
    assert set(candidates[0].note) == {
        key for section in deepsy.SECTIONS for key in deepsy.KEYS[section]
    }


def test_a_section_the_generator_marked_failed_is_not_assembled(tmp_path):
    """The generator already decided it did not parse. Reading it again here
    could disagree with that, and then the cache and the table would say
    different things about the same reply."""
    from tnb.scoring import deepsy_run

    session = Session(id="cz-r-0000abcd", source="czech-real", turns=())
    unit = tmp_path / "einfra" / deepsy.NAME_REAL / deepsy.PROMPT_VERSION / "m" / session.id
    for section in deepsy.SECTIONS:
        _section_file(unit, section, _full(section))
    _section_file(unit, "plan", None, ok=False)

    assert not list(
        deepsy_run.from_generations([session], task_name=deepsy.NAME_REAL, cache_dir=tmp_path)
    )


def test_a_candidate_never_carries_a_transcript(tmp_path):
    """The same guarantee the Czech track makes: what reaches the judge is the
    note, never the session."""
    from tnb.scoring import deepsy_run

    session = Session(id="cz-r-0000abcd", source="czech-real", turns=())
    unit = tmp_path / "einfra" / deepsy.NAME_REAL / deepsy.PROMPT_VERSION / "m" / session.id
    for section in deepsy.SECTIONS:
        _section_file(unit, section, _full(section))

    candidate = next(
        deepsy_run.from_generations([session], task_name=deepsy.NAME_REAL, cache_dir=tmp_path)
    )
    assert candidate.conversation == ""
