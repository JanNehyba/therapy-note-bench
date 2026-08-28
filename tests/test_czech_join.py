"""The English-to-Czech join, and the two ways nine points can lie.

Offline: the correlations here are computed over lists written in this file.
"""

from __future__ import annotations

import sys

from tnb.config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tools"))

import czech_join  # noqa: E402


def test_a_flat_column_is_not_correlated_with_anything():
    """Every model scoring 5.00 is the shape that put `organized` on the English
    page reporting a perfect judge agreement. A correlation over it is decided
    by whichever single model is not at the ceiling, or by nothing at all."""
    varied = [1.0, 2.0, 3.0, 4.0, 5.0]
    flat = [5.0] * 5

    assert czech_join.correlate(flat, varied) is None
    assert czech_join.correlate(varied, flat) is None
    assert czech_join.correlate(flat, flat) is None
    assert czech_join.correlate(varied, varied) is not None


def test_too_few_points_is_not_a_correlation():
    assert czech_join.correlate([1.0, 2.0], [1.0, 2.0]) is None


def test_the_p_value_is_exact_at_this_sample_size():
    """Nine models is 362,880 relabellings and they are all enumerated. An
    approximation would be defensible and would also mean the number moves
    between runs, which invites re-running until it is small."""
    a = [float(n) for n in range(9)]
    result = czech_join.correlate(a, a)

    assert result["exact"] is True
    assert result["n"] == 9
    assert result["rho"] == 1.0
    # Two of 362,880 orderings reach |rho| = 1: the identity and the reversal.
    assert result["p"] < 0.001


def test_a_reversed_ordering_is_as_significant_as_an_identical_one():
    """The test is two-tailed. "English predicts the opposite of Czech" would be
    a finding, not a null result, and hiding it behind a one-tailed test would
    be choosing the direction after seeing the data."""
    a = [float(n) for n in range(9)]
    forward = czech_join.correlate(a, a)
    backward = czech_join.correlate(a, list(reversed(a)))

    assert backward["rho"] == -1.0
    assert backward["p"] == forward["p"]


def test_noise_does_not_come_back_significant():
    """The guard against the thing nine points do best. This ordering was not
    chosen to fail -- it is what a middling shuffle looks like."""
    a = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
    b = [3.0, 7.0, 1.0, 9.0, 4.0, 2.0, 8.0, 5.0, 6.0]
    result = czech_join.correlate(a, b)

    assert abs(result["rho"]) < 0.5
    assert result["p"] > 0.05


def test_ties_are_ranked_at_their_average_and_not_dropped():
    """A Czech column where three models print the same value still ranks the
    others. Dropping the tied rows would silently shrink an already small n."""
    a = [1.0, 2.0, 2.0, 2.0, 5.0, 6.0]
    b = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    result = czech_join.correlate(a, b)

    assert result["n"] == 6, "no row was dropped for being tied"
    assert result["rho"] > 0.8


def test_the_confound_is_written_down_rather_than_left_to_the_reader():
    """The English scores are over 50 conversations and the Czech over the ten
    that were translated. It cannot be removed without recomputing the English
    side, so it is stated."""
    assert "two standings" in czech_join.CONFOUND
    assert "50 AnnoMI conversations" in czech_join.CONFOUND
    assert "both judges" in czech_join.READING
    assert "unmeasured" in czech_join.READING
