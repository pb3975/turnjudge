"""percentile(): empty input, and values below/equal/above the sorted list."""
from jev_review.calibrate import percentile


def test_percentile_empty_list_is_nan():
    result = percentile([], 5.0)
    assert result != result  # nan != nan


def test_percentile_below_all_is_zero():
    assert percentile([1.0, 2.0, 3.0], 0.0) == 0.0


def test_percentile_equal_to_one_is_midpoint():
    assert percentile([1.0, 2.0, 3.0, 4.0], 2.0) == 37.5


def test_percentile_above_all_is_hundred():
    assert percentile([1.0, 2.0, 3.0], 4.0) == 100.0
