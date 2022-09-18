import pytest

from tarka.utility.algorithm.seq import seq_eq, seq_closest, seq_closest_index


def test_algorithm_seq_eq():
    for a, b, r in [
        ([], (), True),
        ([1], (1,), True),
        ([None], (None,), True),
        ([None, "a"], (None, "a"), True),
        ([None], (None, "a"), False),
        ([None, "a"], (None,), False),
        ([], (None,), False),
        ([None], (), False),
        ([False], (True,), False),
    ]:
        assert seq_eq(a, b) is r, f"{r}\n{a}\n{b}"
        assert seq_eq(b, a) is r, f"{r}\n{a}\n{b}"


def test_algorithm_seq_closest():
    with pytest.raises(ValueError):
        seq_closest([], 5)
    s = [1, 5, 8, 9]
    for v, r in [(0, 1), (1, 1), (2, 1), (3, 1), (4, 5), (5, 5), (6, 5), (7, 8), (8, 8), (9, 9), (10, 9)]:
        assert seq_closest(s, v) == r


def test_algorithm_seq_closest_index():
    with pytest.raises(ValueError):
        seq_closest_index([], 5)
    s = [1, 5, 8, 9]
    for v, r in [(0, 0), (1, 0), (2, 0), (3, 0), (4, 1), (5, 1), (6, 1), (7, 2), (8, 2), (9, 3), (10, 3)]:
        assert seq_closest_index(s, v) == r
