"""Self-preference: measured as a difference of differences, with an interval.

The arithmetic is checked against constructed data where the true answer is
known by construction, because on real data there is nothing to check it
against — that is the whole reason the panel exists.
"""

from __future__ import annotations

import pytest

from tnb.scoring import preference

A = "gemini-3.1-pro-preview"
B = "gpt-5.6-terra"
SESSIONS = [str(n) for n in range(30)]


def _scores(values: dict[str, float]) -> dict[str, dict[str, float]]:
    """One flat score per system, repeated over every conversation."""
    return {system: dict.fromkeys(SESSIONS, value) for system, value in values.items()}


# --- which family a system belongs to -----------------------------------------


@pytest.mark.parametrize(
    "system,family",
    [
        ("gemini-3.7-flash", "gemini"),
        ("google/gemini-3.1-pro-preview", "gemini"),
        ("google_gemini-3.7-flash", "gemini"),
        ("gpt-5.6-luna", "gpt-5.6"),
        ("gpt-5.6-terra", "gpt-5.6"),
        ("kimi-k3", None),
        ("gpt-oss-120b", None),
        ("therapist", None),
    ],
)
def test_a_system_is_placed_in_the_right_family(system, family):
    """`gpt-oss-120b` is the trap: an OpenAI-named model nobody at OpenAI serves."""
    assert preference.family_of(system) == family


# --- the arithmetic -----------------------------------------------------------


def test_two_judges_that_agree_show_no_effect():
    by_judge = {
        A: _scores({"gemini-3.7-flash": 0.6, "gpt-5.6-luna": 0.5, "kimi-k3": 0.55}),
        B: _scores({"gemini-3.7-flash": 0.6, "gpt-5.6-luna": 0.5, "kimi-k3": 0.55}),
    }

    effects = preference.compare(by_judge, judge_a=A, judge_b=B)

    assert len(effects) == 2
    for effect in effects:
        assert effect.estimate == pytest.approx(0.0)
        assert effect.detected is False


def test_a_uniformly_stricter_judge_shows_no_effect():
    """The constant gap between two instruments is not self-preference.

    B marks everybody 0.1 lower. Subtracting the two means removes it, which is
    the whole reason this is a difference of differences.
    """
    by_judge = {
        A: _scores({"gemini-3.7-flash": 0.6, "gpt-5.6-luna": 0.5, "kimi-k3": 0.55}),
        B: _scores({"gemini-3.7-flash": 0.5, "gpt-5.6-luna": 0.4, "kimi-k3": 0.45}),
    }

    effects = preference.compare(by_judge, judge_a=A, judge_b=B)

    for effect in effects:
        assert effect.estimate == pytest.approx(0.0)
        assert effect.detected is False


def test_a_judge_that_favours_its_own_family_is_caught():
    """A marks the Gemini models 0.08 higher than B does, and nobody else."""
    by_judge = {
        A: _scores({"gemini-3.7-flash": 0.68, "gpt-5.6-luna": 0.5, "kimi-k3": 0.55}),
        B: _scores({"gemini-3.7-flash": 0.60, "gpt-5.6-luna": 0.5, "kimi-k3": 0.55}),
    }

    effects = {e.judge: e for e in preference.compare(by_judge, judge_a=A, judge_b=B)}

    assert effects[A].estimate == pytest.approx(0.08)
    assert effects[A].detected is True


def test_the_other_judge_is_measured_with_the_sign_the_right_way_round():
    """B favouring GPT must read as B's effect, not as A's mirrored one.

    This caught a real defect. Measuring each judge against "everyone else"
    puts the other judge's family in the comparison group, so B favouring GPT by
    0.12 came out as A favouring Gemini by 0.06. The comparison group is now the
    systems neither judge wrote.
    """
    by_judge = {
        A: _scores({"gemini-3.7-flash": 0.6, "gpt-5.6-luna": 0.50, "kimi-k3": 0.55}),
        B: _scores({"gemini-3.7-flash": 0.6, "gpt-5.6-luna": 0.62, "kimi-k3": 0.55}),
    }

    effects = {e.judge: e for e in preference.compare(by_judge, judge_a=A, judge_b=B)}

    assert effects[B].estimate == pytest.approx(0.12)
    assert effects[B].family == "gpt-5.6"
    assert effects[A].estimate == pytest.approx(0.0)


def test_floating_point_residue_is_not_a_finding():
    """Two judges that agree exactly produced [-4.2e-17, -4.2e-17], which
    excludes zero and read as a detected bias 15 orders of magnitude below
    anything measurable."""
    by_judge = {
        A: _scores({"gemini-3.7-flash": 0.6, "gpt-5.6-luna": 0.5, "kimi-k3": 0.55}),
        B: _scores({"gemini-3.7-flash": 0.5, "gpt-5.6-luna": 0.4, "kimi-k3": 0.45}),
    }

    for effect in preference.compare(by_judge, judge_a=A, judge_b=B):
        assert abs(effect.estimate) < 1e-9
        assert effect.detected is False


def test_an_effect_below_the_noise_floor_is_not_reported():
    """Half a point of completeness is inside what the page already calls noise."""
    by_judge = {
        A: _scores({"gemini-3.7-flash": 0.603, "gpt-5.6-luna": 0.5, "kimi-k3": 0.55}),
        B: _scores({"gemini-3.7-flash": 0.600, "gpt-5.6-luna": 0.5, "kimi-k3": 0.55}),
    }

    effect = next(e for e in preference.compare(by_judge, judge_a=A, judge_b=B) if e.judge == A)

    assert effect.estimate == pytest.approx(0.003)
    assert effect.detected is False, "below NEGLIGIBLE"


def test_the_interval_widens_when_the_evidence_is_noisy():
    """Two systems disagreeing wildly per conversation must not read as precise."""
    import random

    rng = random.Random(11)
    noisy = {
        A: {"gemini-3.7-flash": {}, "kimi-k3": {}},
        B: {"gemini-3.7-flash": {}, "kimi-k3": {}},
    }
    for session in SESSIONS:
        for system in ("gemini-3.7-flash", "kimi-k3"):
            noisy[A][system][session] = rng.uniform(0, 1)
            noisy[B][system][session] = rng.uniform(0, 1)

    effect = next(e for e in preference.compare(noisy, judge_a=A, judge_b=B) if e.judge == A)

    assert effect.high - effect.low > 0.1
    assert effect.detected is False


# --- refusing to answer -------------------------------------------------------


def test_a_judge_that_wrote_no_notes_gets_no_effect():
    """Nothing to measure, so nothing is reported."""
    by_judge = {
        "some-neutral-judge": _scores({"kimi-k3": 0.5, "gemma4": 0.6}),
        B: _scores({"kimi-k3": 0.5, "gemma4": 0.6}),
    }

    effects = preference.compare(by_judge, judge_a="some-neutral-judge", judge_b=B)

    assert effects == []


def test_a_family_with_no_comparison_group_is_skipped():
    """Every system being Gemini leaves no neutral system to subtract."""
    by_judge = {
        A: _scores({"gemini-3.7-flash": 0.6, "gemini-3.1-pro-preview": 0.65}),
        B: _scores({"gemini-3.7-flash": 0.6, "gemini-3.1-pro-preview": 0.65}),
    }

    assert preference.compare(by_judge, judge_a=A, judge_b=B) == []


def test_only_conversations_both_judges_scored_are_compared():
    """A difference taken over two different session sets is not a difference."""
    by_judge = {
        A: _scores({"gemini-3.7-flash": 0.6, "kimi-k3": 0.5}),
        B: _scores({"gemini-3.7-flash": 0.6, "kimi-k3": 0.5}),
    }
    del by_judge[B]["kimi-k3"]["0"]
    del by_judge[B]["kimi-k3"]["1"]

    effect = next(e for e in preference.compare(by_judge, judge_a=A, judge_b=B) if e.judge == A)

    assert effect.n_sessions == len(SESSIONS) - 2


def test_too_little_evidence_produces_nothing_rather_than_a_number():
    tiny = {
        A: {"gemini-3.7-flash": {"0": 0.6}, "kimi-k3": {"0": 0.5}},
        B: {"gemini-3.7-flash": {"0": 0.6}, "kimi-k3": {"0": 0.5}},
    }

    assert preference.compare(tiny, judge_a=A, judge_b=B) == []


# --- what it says -------------------------------------------------------------


def test_a_null_result_is_stated_as_one_and_not_as_absence():
    by_judge = {
        A: _scores({"gemini-3.7-flash": 0.6, "kimi-k3": 0.55}),
        B: _scores({"gemini-3.7-flash": 0.6, "kimi-k3": 0.55}),
    }
    effect = next(e for e in preference.compare(by_judge, judge_a=A, judge_b=B) if e.judge == A)

    sentence = preference.describe(effect)

    assert "no detectable preference" in sentence
    assert "not the same as absent" in sentence


def test_a_detected_effect_tells_the_reader_what_to_do_with_it():
    by_judge = {
        A: _scores({"gemini-3.7-flash": 0.70, "kimi-k3": 0.55}),
        B: _scores({"gemini-3.7-flash": 0.60, "kimi-k3": 0.55}),
    }
    effect = next(e for e in preference.compare(by_judge, judge_a=A, judge_b=B) if e.judge == A)

    sentence = preference.describe(effect)

    assert "0.100" in sentence
    assert "higher" in sentence


def test_the_bootstrap_is_reproducible():
    by_judge = {
        A: _scores({"gemini-3.7-flash": 0.62, "kimi-k3": 0.55}),
        B: _scores({"gemini-3.7-flash": 0.60, "kimi-k3": 0.55}),
    }

    first = preference.compare(by_judge, judge_a=A, judge_b=B)
    second = preference.compare(by_judge, judge_a=A, judge_b=B)

    assert [e.low for e in first] == [e.low for e in second]
    assert [e.high for e in first] == [e.high for e in second]
