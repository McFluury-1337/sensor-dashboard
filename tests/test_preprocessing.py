from preprocessing import normalize, standardize


def test_normalize_min_becomes_zero_and_max_becomes_one():
    result = normalize([10, 20, 30])
    assert result[0] == 0
    assert result[2] == 1


def test_normalize_middle_value_is_proportional():
    result = normalize([10, 20, 30])
    assert result[1] == 0.5


def test_normalize_constant_values_return_zero():
    assert normalize([5, 5, 5]) == [0, 0, 0]


def test_standardize_mean_is_approximately_zero():
    result = standardize([10, 20, 30])
    assert abs(sum(result) / len(result)) < 1e-9


def test_standardize_matches_known_z_scores():
    result = standardize([2, 4, 4, 4, 5, 5, 7, 9])
    assert round(result[0], 2) == -1.5
    assert round(result[-1], 2) == 2.0
