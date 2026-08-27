"""Whether the benchmark can still tell models apart — and the maths that says so.

This analysis exists to stop the leaderboard claiming a ranking the evidence
does not support, so its arithmetic is pinned against constructed cases where
the right answer is known in advance. Nothing here touches the network.
"""

from __future__ import annotations

import pytest

from tnb.scoring import saturation, tneval
from tnb.scoring.saturation import CriterionProfile


def _profile(**rates) -> CriterionProfile:
    return CriterionProfile(
        key="subjective-symptoms",
        text="Symptoms",
        section="subjective",
        by_system=dict(rates),
        human=rates.get("therapist"),
    )


# --- what a criterion is doing to the field ---------------------------------


def test_a_criterion_every_model_satisfies_is_used_up():
    """Nothing left to measure: a twelfth model cannot distinguish itself here."""
    assert _profile(a=1.0, b=0.98, c=0.95).verdict == "saturated"


def test_one_weak_model_keeps_a_criterion_alive():
    assert _profile(a=1.0, b=1.0, c=0.4).verdict == "discriminating"


def test_a_criterion_nobody_reaches_is_absent_not_hard():
    """`assessment-goals` -- measurable SMART goals -- is 0% for the therapist
    too. A transcript of one counselling session does not contain the answer, so
    a zero there says something about the corpus, not about the model."""
    assert _profile(a=0.02, b=0.0, c=0.04, therapist=0.0).verdict == "unreachable"


def test_a_criterion_the_models_fail_but_a_human_manages_is_not_unreachable():
    """If a therapist can write it, the question has an answer and a model
    failing it is a real failure."""
    assert _profile(a=0.02, b=0.0, c=0.04, therapist=0.40).verdict != "unreachable"


def test_the_human_is_never_counted_as_a_competitor():
    """The therapist is the reference the models are read against, not a row in
    the ranking; including them would move every threshold."""
    profile = _profile(a=1.0, b=0.95, therapist=0.30)
    assert profile.verdict == "saturated"
    assert "therapist" not in profile.models


# --- confidence intervals ----------------------------------------------------


def _scores(**systems) -> dict[str, dict[str, float]]:
    return {
        name: {str(index): value for index, value in enumerate(values)}
        for name, values in systems.items()
    }


def test_two_clearly_different_models_are_separated():
    intervals, beats = saturation.paired_intervals(
        _scores(strong=[0.9] * 30, weak=[0.2] * 30), samples=200
    )
    assert [i.system for i in intervals] == ["strong", "weak"]
    assert beats["strong"]["weak"] == 1.0
    assert saturation.indistinguishable(intervals, beats) == [["strong"], ["weak"]]


def test_a_tiny_but_consistent_lead_is_detected():
    """What the paired bootstrap buys, and worth stating plainly: a model that
    wins on *every* conversation is separable however small the margin, because
    no resample can reverse it. Consistency is the evidence, not the gap."""
    first = [0.5 + (index % 5) * 0.02 for index in range(40)]
    second = [value + 0.002 for value in first]
    intervals, beats = saturation.paired_intervals(_scores(a=first, b=second), samples=400)

    assert beats["b"]["a"] == 1.0
    assert saturation.indistinguishable(intervals, beats) == [["b"], ["a"]]


def test_a_larger_but_inconsistent_lead_is_not_separated():
    """The case limitations.md warns about: b averages higher, but wins and
    loses roughly at random. A ranking prints it as an order; the evidence does
    not support one."""
    first = [0.5] * 40
    second = [0.5 + (0.30 if index % 2 else -0.28) for index in range(40)]
    intervals, beats = saturation.paired_intervals(_scores(a=first, b=second), samples=600)

    assert max(beats["b"]["a"], beats["a"]["b"]) < 0.95
    assert saturation.indistinguishable(intervals, beats) == [["b", "a"]]


def test_the_bootstrap_is_paired_across_systems():
    """Every system wrote a note for the same conversations. Resampling them
    together removes the shared difficulty of a hard conversation instead of
    counting it as disagreement -- which is what makes a small, consistent gap
    detectable at all."""
    hard_easy = [0.1, 0.9] * 20
    intervals, beats = saturation.paired_intervals(
        _scores(a=hard_easy, b=[value + 0.05 for value in hard_easy]), samples=400
    )
    assert beats["b"]["a"] == 1.0, "a consistent lead survives a wildly varying corpus"


def test_the_same_data_gives_the_same_interval_twice():
    """A rebuilt page must be byte-identical or its diffs stop being readable."""
    scores = _scores(a=[0.4, 0.6, 0.5, 0.7] * 8, b=[0.3, 0.5, 0.6, 0.4] * 8)
    first, _ = saturation.paired_intervals(scores, samples=300)
    second, _ = saturation.paired_intervals(scores, samples=300)
    assert [(i.system, i.low, i.high) for i in first] == [(i.system, i.low, i.high) for i in second]


def test_an_interval_brackets_the_score_it_belongs_to():
    (interval,), _ = saturation.paired_intervals(_scores(a=[0.2, 0.4, 0.6, 0.8] * 6), samples=300)
    assert interval.low <= interval.mean <= interval.high


def test_too_few_sessions_produce_no_claim_at_all():
    """One conversation cannot support an interval, and inventing one would be
    worse than saying nothing."""
    assert saturation.paired_intervals(_scores(a=[0.5])) == ([], {})


def test_only_sessions_every_system_wrote_are_compared():
    """Two systems with the same coverage but different conversations are
    compared on the overlap alone. Scoring one on easy conversations and the
    other on hard ones must not read as a difference between the models."""
    scores = {
        "a": {"1": 0.9, "2": 0.9, "3": 0.5, "4": 0.5, "5": 0.5},
        "b": {"3": 0.5, "4": 0.5, "5": 0.5, "6": 0.1, "7": 0.1},
    }
    intervals, beats = saturation.paired_intervals(scores, samples=200)

    assert all(interval.sessions == 3 for interval in intervals), "sessions 3, 4 and 5"
    assert max(beats["a"]["b"], beats["b"]["a"]) < 0.95, "identical on the overlap"


# --- grouping ----------------------------------------------------------------


def test_a_group_holds_only_systems_none_of_which_beats_another():
    intervals, beats = saturation.paired_intervals(
        _scores(
            top=[0.9] * 30,
            middle_a=[0.5] * 30,
            middle_b=[0.5] * 30,
            bottom=[0.1] * 30,
        ),
        samples=200,
    )
    groups = saturation.indistinguishable(intervals, beats)
    assert ["middle_a", "middle_b"] in [sorted(group) for group in groups]
    assert ["top"] in groups and ["bottom"] in groups


@pytest.mark.parametrize("threshold", [0.9, 0.95, 0.99])
def test_a_stricter_threshold_never_splits_more(threshold):
    """Demanding more evidence can only merge groups, never divide them."""
    intervals, beats = saturation.paired_intervals(
        _scores(a=[0.6] * 30, b=[0.55] * 30, c=[0.2] * 30), samples=300
    )
    groups = saturation.indistinguishable(intervals, beats, threshold=threshold)
    assert sum(len(group) for group in groups) == 3


# --- bugs found by looking, each pinned so it cannot come back ---------------


def test_a_system_still_being_scored_does_not_void_the_analysis():
    """Found live: one model two conversations into its run collapsed the shared
    set to two and the whole analysis returned nothing. A partial system is left
    out, not allowed to take everyone with it."""
    scores = _scores(a=[0.5] * 50, b=[0.4] * 50, fresh=[0.9, 0.9])
    usable, partial = saturation.usable_systems(scores)

    assert usable == ["a", "b"]
    assert partial == ["fresh"]

    intervals, _ = saturation.paired_intervals(scores, samples=200)
    assert [i.system for i in intervals] == ["a", "b"]
    assert intervals[0].sessions == 50, "the full corpus, not the newcomer's two"


def test_a_system_scored_on_most_of_the_corpus_is_still_compared():
    """The cut is for runs in progress, not for a model that lost a few notes."""
    scores = _scores(a=[0.5] * 50, nearly=[0.4] * 45)
    usable, partial = saturation.usable_systems(scores)
    assert usable == ["a", "nearly"] and partial == []


def test_two_providers_serving_one_model_id_are_kept_apart():
    """The mistake the whole provider refactor exists to prevent, one layer up:
    keying answers on the model id alone merged two endpoints' judgements into
    one system that does not exist."""
    providers = {"qwen3.5-122b": {"einfra", "other"}, "gemma4": {"einfra"}}

    assert saturation.label_for("einfra", "qwen3.5-122b", providers) == "qwen3.5-122b (einfra)"
    assert saturation.label_for("other", "qwen3.5-122b", providers) == "qwen3.5-122b (other)"
    assert saturation.label_for("einfra", "gemma4", providers) == "gemma4", "unambiguous stays bare"


def test_answers_from_two_providers_do_not_merge(tmp_path):
    from tnb import judge

    for provider in ("einfra", "other"):
        path = judge.cache_path(
            judge.DEFAULT_MODEL,
            tneval.JUDGE_PROMPT_VERSION,
            provider,
            "qwen3.5-122b",
            "0",
            "x.y",
            root=tmp_path,
        )
        judge.write_cached(
            path,
            {
                "ok": True,
                "provider": provider,
                "system_id": "qwen3.5-122b",
                "session_id": "0",
                "unit": "subjective.rubric_completeness.subjective-symptoms",
                "answer": "Yes" if provider == "einfra" else "No",
            },
        )

    answers = saturation.load_answers(tmp_path)
    assert len(answers) == 2, "one bucket each, not one merged model"


def test_a_second_judge_prompt_version_is_never_mixed_in(tmp_path):
    """Two versions of the rubric are two instruments. The analysis reads one
    version's directory, not the whole judge's, or the leaderboard's central
    rule would break where nobody was looking."""
    from tnb import judge

    for version, answer in ((tneval.JUDGE_PROMPT_VERSION, "Yes"), ("tneval-rubric-v2", "No")):
        judge.write_cached(
            judge.cache_path(
                judge.DEFAULT_MODEL, version, "einfra", "gemma4", "0", "x.y", root=tmp_path
            ),
            {
                "ok": True,
                "provider": "einfra",
                "system_id": "gemma4",
                "session_id": "0",
                "unit": "subjective.rubric_completeness.subjective-symptoms",
                "answer": answer,
            },
        )

    answers = saturation.load_answers(tmp_path)
    assert len(answers) == 1
    assert list(answers.values())[0]["subjective.rubric_completeness.subjective-symptoms"] == "Yes"


def test_a_still_scoring_system_does_not_shape_the_criterion_bars(tmp_path):
    """The panel excluded a half-scored system from the ranking and let it set
    the min and max of every criterion bar beside it -- one panel saying two
    different things about who was measured."""
    answers = {
        ("full", str(i)): {"subjective.rubric_completeness.subjective-symptoms": "Yes"}
        for i in range(20)
    }
    answers[("fresh", "0")] = {"subjective.rubric_completeness.subjective-symptoms": "No"}

    everyone = saturation.per_criterion(answers)
    filtered = saturation.per_criterion(answers, include=["full"])

    assert everyone[0].verdict == "discriminating", "the newcomer drags the bar open"
    assert filtered[0].verdict == "saturated", "and is excluded once the filter applies"


def test_a_failed_judge_call_never_reaches_a_numerator(tmp_path):
    """The one guard holding failed calls out of every saturation number.

    A record with `ok: false` carries whatever text came back before the call
    died -- an empty string, or a fragment of the judge's own reasoning. Read as
    an answer, a fragment that happens not to start with "yes" counts as the
    model missing a criterion, which is the model's fault for something the
    judge did. `load_answers` skips it and nothing else in this module checks.
    """
    from tnb import judge

    units = {
        "subjective.rubric_completeness.subjective-symptoms": ("Yes", True),
        "subjective.rubric_completeness.subjective-history": ("", False),
        # The shape actually found on disk: the answer is a fragment of the
        # judge's thinking, cut off when the output budget ran out.
        "subjective.rubric_completeness.subjective-context": (
            'g., "The client has',
            False,
        ),
    }
    for unit, (answer, ok) in units.items():
        judge.write_cached(
            judge.cache_path(
                judge.DEFAULT_MODEL,
                tneval.JUDGE_PROMPT_VERSION,
                "einfra",
                "gemma4",
                "0",
                unit,
                root=tmp_path,
            ),
            {
                "ok": ok,
                "provider": "einfra",
                "system_id": "gemma4",
                "session_id": "0",
                "unit": unit,
                "answer": answer,
                "error": None if ok else "HTTP429: rate limit",
            },
        )

    answers = saturation.load_answers(tmp_path)

    assert list(answers) == [("gemma4", "0")]
    assert list(answers[("gemma4", "0")]) == [
        "subjective.rubric_completeness.subjective-symptoms"
    ], "the one that worked, and only that"


def test_a_half_answered_session_does_not_enter_the_bootstrap():
    """The leaderboard's headline drops it; this path did not.

    A note answered on 3 of 23 criteria is already caught -- `aggregate` gives
    it no completeness at all. The one that got through is subtler: a judge
    that answered subjective and objective in full and never reached assessment
    and plan produces a completeness of **1.0** averaged over two sections,
    with an empty `incomplete` and nothing anywhere saying it is half a
    measurement. Resampling that is worse than losing it, because judge
    failures cluster on the notes that are hard to read: the bias runs one way.
    """
    # All 23 criteria across all four SOAP sections: `is_complete` is about the
    # whole note, so answering one section in full is still a partial note.
    complete = {
        f"{section}.rubric_completeness.{key}": "Yes"
        for section in tneval.SOAP_SECTIONS
        for key in tneval.criteria_keys(section)
    }
    half = {
        unit: answer
        for unit, answer in complete.items()
        if unit.split(".")[0] in ("subjective", "objective")
    }
    assert tneval.aggregate(half).headline["completeness"] == 1.0, "and it looks perfect"

    scores = saturation.per_session_scores(
        {
            ("gemma4", "0"): dict(complete),
            ("gemma4", "1"): half,
            # Three of twenty-three: `aggregate` already refuses this one.
            ("gemma4", "2"): dict(list(complete.items())[:3]),
        }
    )

    assert list(scores["gemma4"]) == ["0"]


def test_two_judge_settings_in_one_cache_are_not_averaged_together(tmp_path):
    """The cache is scoped by judge model and prompt version, not by settings.

    A thinking budget is a setting: raising it from 128 to 256 re-asks every
    question, so mid-run the directory holds both and averaging across them
    reports a number no single judge produced. The leaderboard's rule that two
    fingerprints never share a table has to hold here too, and this is the one
    place it was not enforced.
    """
    from tnb import judge

    for session, budget, answer in (("0", 128, "Yes"), ("1", 256, "No"), ("2", 256, "No")):
        judge.write_cached(
            judge.cache_path(
                judge.DEFAULT_MODEL,
                tneval.JUDGE_PROMPT_VERSION,
                "einfra",
                "gemma4",
                session,
                "subjective.rubric_completeness.subjective-symptoms",
                root=tmp_path,
            ),
            {
                "ok": True,
                "provider": "einfra",
                "system_id": "gemma4",
                "session_id": session,
                "unit": "subjective.rubric_completeness.subjective-symptoms",
                "answer": answer,
                "judge_fingerprint": {"model": judge.DEFAULT_MODEL, "thinking_budget": budget},
            },
        )

    answers = saturation.load_answers(tmp_path)

    assert sorted(session for _system, session in answers) == ["1", "2"], "the larger set"
    assert answers.chosen_fingerprint["thinking_budget"] == 256
    assert sum(answers.other_fingerprints.values()) == 1, "and it says what it left out"


def test_two_loads_do_not_share_their_bookkeeping(tmp_path):
    """`tnb preference` loads both judges in one process. A mutable attribute
    on the class rather than the instance would have them report each other's
    ignored fingerprints."""
    first = saturation.load_answers(tmp_path)
    first.other_fingerprints["only-mine"] = 1

    assert saturation.load_answers(tmp_path).other_fingerprints == {}


def test_a_system_with_nothing_of_its_own_reports_no_mean_rather_than_zero():
    """`own_mean` was `0.0` when there was nothing to average, and the page
    prints it: "the table shows 0.000, over all 0 of its own".

    Zero is not what such a system scored; it is what nobody measured. The page
    has always guarded on `!= null` — Python was the side that would not say
    it, and the serialiser would have thrown on the honest value.
    """
    from tnb.scoring import saturation

    empty = saturation.Interval(system="x", mean=0.5, low=0.4, high=0.6, sessions=10)

    assert empty.own_mean is None, "the default is an absence, not a zero"

    payload = saturation.interval_json(empty)
    assert payload["own_mean"] is None, "and the serialiser passes it through"

    measured = saturation.Interval(
        system="y", mean=0.5, low=0.4, high=0.6, sessions=10, own_sessions=12, own_mean=0.5123
    )
    assert saturation.interval_json(measured)["own_mean"] == 0.5123, "a real one still arrives"


def test_own_mean_is_not_claimed_to_be_the_tables_figure():
    """It is not, for 10 of the 19 rows under the first judge, by up to 0.0070.

    The leaderboard admits a note on `Scores.is_complete` -- all four sections
    of every measure -- and this analysis, which reads only the answer cache,
    admits it on `rests_on_every_section("completeness")`, because the note text
    is not in the cache and which conciseness questions should have been asked
    cannot be reconstructed. The weaker test keeps more notes and produces a
    different mean over them.

    Held on the prose, because the defect was the prose.
    """
    import inspect

    source = inspect.getsource(saturation.Interval)
    assert "what the table shows" not in source, (
        "own_mean is not the table's figure and the comment must not say it is"
    )
    assert "is_complete" in source and "rests_on_every_section" in source, (
        "the comment has to say which two tests differ, or the next reader repeats it"
    )
