import random
from itertools import chain

from tarka.utility.algorithm.iter import (
    iter_unique,
    iter_merge_two,
    iter_merge,
    iter_merge_unique,
    iter_all_same,
    iter_merge_zip,
    SENTINEL,
)
from tarka.utility.sentinel import NamedObject


def test_algorithm_iter_unique():
    assert list(iter_unique([])) == []
    assert list(iter_unique([], ())) == []
    assert list(iter_unique([], (), set())) == []
    assert list(iter_unique([], (), set(), dict())) == []
    assert list(iter_unique([1, 2])) == [1, 2]
    assert list(iter_unique([1, 1, 2, 1])) == [1, 2]
    assert list(iter_unique([1, 2])) == [1, 2]
    assert list(iter_unique([1, 1, 2, 1, 3], (4, 3, 2, 1, 5), {6})) == [1, 2, 3, 4, 5, 6]
    assert set(iter_unique({8, 6, 2, 1}, {8, 5, 2, 4}, [1, 5, 7], {3, 9, 0, 4, 5})) == {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}


def test_algorithm_iter_merge_zip():
    s = SENTINEL
    assert list(iter_merge_zip([], [])) == []
    assert list(iter_merge_zip([1, 2], [])) == [(1, s), (2, s)]
    assert list(iter_merge_zip([], [1, 2])) == [(s, 1), (s, 2)]
    assert list(iter_merge_zip([1, 2], [1, 2])) == [(1, 1), (2, 2)]
    assert list(iter_merge_zip([1, 3], [2, 4])) == [(1, s), (s, 2), (3, s), (s, 4)]
    assert list(iter_merge_zip([2, 4], [1, 3])) == [(s, 1), (2, s), (s, 3), (4, s)]
    s = NamedObject("__test-sentinel")
    assert list(iter_merge_zip([1, 3], [2, 3], s)) == [(1, s), (s, 2), (3, 3)]


def test_algorithm_iter_merge_two():
    assert list(iter_merge_two([], [])) == []
    assert list(iter_merge_two([1, 2], [])) == [1, 2]
    assert list(iter_merge_two([], [1, 2])) == [1, 2]
    assert list(iter_merge_two([1, 2], [1, 2])) == [1, 1, 2, 2]
    assert list(iter_merge_two([1, 3], [2, 4])) == [1, 2, 3, 4]
    assert list(iter_merge_two([2, 4], [1, 3])) == [1, 2, 3, 4]
    for _ in range(20):
        a = sorted(random.randint(1, 99) for _ in range(random.randint(20, 40)))
        b = sorted(random.randint(1, 99) for _ in range(random.randint(20, 40)))
        assert list(iter_merge_two(a, b)) == sorted(chain(a, b))
    s = NamedObject("__test-sentinel")
    assert list(iter_merge_two([1, 3], [2, 3], s)) == [1, 2, 3, 3]


def test_algorithm_iter_merge_and_unique():
    for merge in (iter_merge, iter_merge_unique):
        assert list(merge()) == []
        assert list(merge([])) == []
        assert list(merge([], [])) == []
        assert list(merge([], [], [])) == []
    for n in range(1, 5):
        for _ in range(20):
            xs = [sorted(random.randint(1, 99) for _ in range(random.randint(15, 25))) for _ in range(n)]
            xs.insert(random.randint(0, n - 1), [])
            assert list(iter_merge(*xs)) == sorted(chain(*xs))
            assert list(iter_merge_unique(*xs)) == sorted(set(chain(*xs)))


def test_algorithm_iter_all_same():
    assert iter_all_same() is True
    assert iter_all_same([]) is True
    assert iter_all_same([False]) is True
    assert iter_all_same([None]) is True
    assert iter_all_same([5, 5]) is True
    assert iter_all_same([5, 5], [5]) is True
    assert iter_all_same([5, 4], [5]) is False
    assert iter_all_same([5, 5], [4]) is False
