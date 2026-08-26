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
        ("gemini-3.7-flash", "google"),
        ("google/gemini-3.1-pro-preview", "google"),
        ("google_gemini-3.7-flash", "google"),
        ("gemma4", "google"),
        ("gpt-5.6-luna", "openai"),
        ("gpt-5.6-terra", "openai"),
        ("gpt-oss-120b", "openai"),
        ("kimi-k3", None),
        ("glm-5.2", None),
        ("therapist", None),
    ],
)
def test_a_system_is_placed_with_the_vendor_that_built_it(system, family):
    """The two traps run the other way from how this test first read them.

    It used to assert `gpt-oss-120b -> None`, on the argument that it is "an
    OpenAI-named model nobody at OpenAI serves". Who serves the weights is not
    the question. Self-preference is about the vendor that *built* the text's
    generator, and both `gpt-oss-120b` and `gemma4` were built by a judge's
    vendor -- OpenAI and Google DeepMind respectively.

    Whether the effect actually carries across an open-weight sibling is an
    open question. Leaving them in the comparison group answered it "no" with
    no evidence, in the one group the whole estimate is measured against, and
    both published effects read "not detected" with an interval near zero.
    Excluding them makes the panel say less, which is the direction an
    unanswered question should move a claim.
    """
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
    assert effects[B].family == "openai"
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


def _partial_scores(systems: dict[str, int], value: float) -> dict[str, dict[str, float]]:
    """One judge's per-session scores, `systems` giving each one's session count."""
    return {
        system: {str(i): value for i in range(sessions)} for system, sessions in systems.items()
    }


def test_a_system_still_being_scored_does_not_shrink_everyone_elses_evidence():
    """`shared` is an intersection, so a partial system takes the panel with it.

    Saturation was given this guard after one model two conversations into its
    run collapsed the shared set to two and voided the whole analysis. This
    module was written later and never got it, so the same run would have
    published a self-preference interval computed over two conversations
    without saying so.
    """
    full = {"google_gemini-3.7-flash": 50, "gemma4": 50, "qwen3.5-122b": 50}
    by_judge = {
        "gemini-3.1-pro-preview": _partial_scores({**full, "half-done": 3}, 0.60),
        "gpt-5.6-terra": _partial_scores({**full, "half-done": 3}, 0.55),
    }

    effects = preference.compare(
        by_judge, judge_a="gemini-3.1-pro-preview", judge_b="gpt-5.6-terra"
    )

    assert effects, "the three finished systems are still comparable"
    assert all(e.n_sessions == 50 for e in effects), "not 3"


def test_too_few_shared_conversations_reports_nothing_at_all():
    """A bootstrap that resamples three numbers has an interval saying nothing.

    Reporting it anyway is worse than reporting nothing: the panel's whole
    purpose is to tell a reader how much the judges can be trusted, and an
    interval built on three conversations answers that question falsely.
    """
    tiny = {"google_gemini-3.7-flash": 3, "gemma4": 3, "qwen3.5-122b": 3}
    by_judge = {
        "gemini-3.1-pro-preview": _partial_scores(tiny, 0.60),
        "gpt-5.6-terra": _partial_scores(tiny, 0.55),
    }

    assert (
        preference.compare(by_judge, judge_a="gemini-3.1-pro-preview", judge_b="gpt-5.6-terra")
        == []
    )


def test_the_comparison_group_is_named_not_only_counted():
    """The estimate is only as good as this group, and a count cannot be checked.

    A reader who sees "against 14 neutral systems" cannot see that two of the
    fourteen were the judges' own vendors. A reader who sees the names can.
    """
    by_judge = {
        A: _scores({"gemini-3.7-flash": 0.68, "kimi-k3": 0.55, "glm-5.2": 0.50}),
        B: _scores({"gemini-3.7-flash": 0.60, "kimi-k3": 0.55, "glm-5.2": 0.50}),
    }

    effect = next(e for e in preference.compare(by_judge, judge_a=A, judge_b=B) if e.judge == A)

    assert effect.neutral == ("glm-5.2", "kimi-k3")
    assert effect.n_neutral == len(effect.neutral)


def test_a_judges_own_open_weight_sibling_is_not_its_control_group():
    """The defect, put back as data: `gemma4` is Google's, like judge A.

    A marks every Google model 0.08 above B. With `gemma4` counted as neutral
    that rise appears on both sides of the subtraction and the panel reports a
    fraction of the real effect -- here 0.04 instead of 0.08 -- as "not
    detected".
    """
    by_judge = {
        A: _scores({"gemini-3.7-flash": 0.68, "gemma4": 0.63, "kimi-k3": 0.55}),
        B: _scores({"gemini-3.7-flash": 0.60, "gemma4": 0.55, "kimi-k3": 0.55}),
    }

    effect = next(e for e in preference.compare(by_judge, judge_a=A, judge_b=B) if e.judge == A)

    assert "gemma4" not in effect.neutral
    assert effect.neutral == ("kimi-k3",)
    assert effect.estimate == pytest.approx(0.08)
    assert effect.detected is True


def test_the_sentence_says_which_reason_applies():
    """ "an interval that includes zero, or is smaller than 0.005" was printed of
    [+0.004, +0.032], which does not include zero.

    Both branches were true of an earlier run and only one is true of this one.
    A reader was left to work out which half applied, from numbers to three
    places beside a threshold given to one.
    """
    by_judge = {
        A: _scores({"gemini-3.7-flash": 0.604, "gpt-5.6-luna": 0.5, "kimi-k3": 0.55}),
        B: _scores({"gemini-3.7-flash": 0.600, "gpt-5.6-luna": 0.5, "kimi-k3": 0.55}),
    }
    effect = next(e for e in preference.compare(by_judge, judge_a=A, judge_b=B) if e.judge == A)
    assert effect.low > 0 and not effect.detected, "above zero, below the noise floor"

    said = preference.describe(effect)
    assert "clears zero by less than" in said
    assert "includes zero" not in said

    flat = {
        A: _scores({"gemini-3.7-flash": 0.6, "kimi-k3": 0.55}),
        B: _scores({"gemini-3.7-flash": 0.6, "kimi-k3": 0.55}),
    }
    zero = next(e for e in preference.compare(flat, judge_a=A, judge_b=B) if e.judge == A)
    assert "includes zero" in preference.describe(zero)


def test_a_vendor_is_named_the_way_a_sentence_names_it():
    """The family key is a slug because it is matched against model ids. It
    reached the page as one: "Read its column for a openai model"."""
    by_judge = {
        A: _scores({"gemini-3.7-flash": 0.68, "kimi-k3": 0.55}),
        B: _scores({"gemini-3.7-flash": 0.60, "kimi-k3": 0.55}),
    }
    said = preference.describe(
        next(e for e in preference.compare(by_judge, judge_a=A, judge_b=B) if e.judge == A)
    )

    assert "Google" in said
    assert "a google model" not in said and "a openai model" not in said


def test_the_interval_covers_the_systems_it_generalises_over():
    """The published sentence is "this judge scores its own vendor's models
    higher". That is a claim about a vendor, and the leaderboard marks *rows*
    with it — so the three or four models the mean is over are a sample.

    Resampling conversations alone treated them as the whole vendor, and that
    is what produced the one "detected" verdict this repository published. With
    the systems resampled too it is [-0.002, +0.059] and includes zero.
    """
    import random
    import statistics

    from tnb.scoring import preference as module

    # A judge whose own family is genuinely higher on average, carried by ONE
    # of its three systems. Resampling conversations cannot see that; resampling
    # systems must.
    by_judge = {
        A: _scores(
            {
                "gemini-3.7-flash": 0.75,
                "gemini-3.1-pro-preview": 0.60,
                "gemma4": 0.60,
                "kimi-k3": 0.60,
                "glm-5": 0.60,
                "qwen3.5-int4": 0.60,
            }
        ),
        B: _scores(
            {
                "gemini-3.7-flash": 0.60,
                "gemini-3.1-pro-preview": 0.60,
                "gemma4": 0.60,
                "kimi-k3": 0.60,
                "glm-5": 0.60,
                "qwen3.5-int4": 0.60,
            }
        ),
    }
    effect = next(e for e in module.compare(by_judge, judge_a=A, judge_b=B) if e.judge == A)

    assert effect.estimate == pytest.approx(0.05, abs=1e-9), "one system of three, +0.15"
    # Exactly zero, not below it: with three systems and one carrying the
    # effect, 29% of draws pick none of it, so the 2.5th percentile is the
    # mean of the two that show nothing.
    assert effect.low <= 0 < effect.high, (
        "an effect resting on one of three systems cannot exclude zero"
    )
    assert not effect.detected

    # And the point estimate is still over the systems as observed, not resampled.
    assert effect.own == pytest.approx(0.05, abs=1e-9)


def test_an_effect_every_system_shows_is_still_detected():
    """The widening must not swallow a real one: if every member of the family
    is higher, resampling the family changes nothing."""
    from tnb.scoring import preference as module

    by_judge = {
        A: _scores(
            {
                "gemini-3.7-flash": 0.70,
                "gemini-3.1-pro-preview": 0.70,
                "gemma4": 0.70,
                "kimi-k3": 0.60,
                "glm-5": 0.60,
                "qwen3.5-int4": 0.60,
            }
        ),
        B: _scores(
            {
                "gemini-3.7-flash": 0.60,
                "gemini-3.1-pro-preview": 0.60,
                "gemma4": 0.60,
                "kimi-k3": 0.60,
                "glm-5": 0.60,
                "qwen3.5-int4": 0.60,
            }
        ),
    }
    effect = next(e for e in module.compare(by_judge, judge_a=A, judge_b=B) if e.judge == A)

    assert effect.estimate == pytest.approx(0.10, abs=1e-9)
    assert effect.detected, "unanimous within the family, so the interval holds"
