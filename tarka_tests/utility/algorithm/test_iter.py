import random
from itertools import chain

import pytest

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
    for ascending in [True, False]:
        reorder = (lambda x: x) if ascending else lambda x: list(reversed(x))
        s = SENTINEL
        assert list(iter_merge_zip(reorder([]), reorder([]), ascending=ascending)) == reorder([])
        assert list(iter_merge_zip(reorder([1, 2]), reorder([]), ascending=ascending)) == reorder([(1, s), (2, s)])
        assert list(iter_merge_zip(reorder([]), reorder([1, 2]), ascending=ascending)) == reorder([(s, 1), (s, 2)])
        assert list(iter_merge_zip(reorder([1, 2]), reorder([1, 2]), ascending=ascending)) == reorder([(1, 1), (2, 2)])
        assert list(iter_merge_zip(reorder([1, 3]), reorder([2, 4]), ascending=ascending)) == reorder(
            [(1, s), (s, 2), (3, s), (s, 4)]
        )
        assert list(iter_merge_zip(reorder([2, 4]), reorder([1, 3]), ascending=ascending)) == reorder(
            [(s, 1), (2, s), (s, 3), (4, s)]
        )
        with pytest.raises(TypeError):
            list(
                iter_merge_zip(
                    reorder([(1, 5), (5, "a"), (7, 4)]), reorder([(2, 3), (5, 2), (8, 5)]), ascending=ascending
                )
            )
        assert list(
            iter_merge_zip(
                reorder([(1, 5), (2, "a")]), reorder([(2, 2), (3, 5)]), key=lambda x: x[0], ascending=ascending
            )
        ) == reorder([((1, 5), s), ((2, "a"), (2, 2)), (s, (3, 5))])
        s = NamedObject("__test-sentinel")
        assert list(iter_merge_zip(reorder([1, 3]), reorder([2, 3]), ascending=ascending, s=s)) == reorder(
            [(1, s), (s, 2), (3, 3)]
        )


def test_algorithm_iter_merge_two():
    for ascending in [True, False]:
        reorder = (lambda x: x) if ascending else lambda x: list(reversed(x))
        assert list(iter_merge_two(reorder([]), reorder([]), ascending=ascending)) == reorder([])
        assert list(iter_merge_two(reorder([1, 2]), reorder([]), ascending=ascending)) == reorder([1, 2])
        assert list(iter_merge_two(reorder([]), reorder([1, 2]), ascending=ascending)) == reorder([1, 2])
        assert list(iter_merge_two(reorder([1, 2]), reorder([1, 2]), ascending=ascending)) == reorder([1, 1, 2, 2])
        assert list(iter_merge_two(reorder([1, 3]), reorder([2, 4]), ascending=ascending)) == reorder([1, 2, 3, 4])
        assert list(iter_merge_two(reorder([2, 4]), reorder([1, 3]), ascending=ascending)) == reorder([1, 2, 3, 4])
        for _ in range(20):
            a = sorted(random.randint(1, 99) for _ in range(random.randint(20, 40)))
            b = sorted(random.randint(1, 99) for _ in range(random.randint(20, 40)))
            assert list(iter_merge_two(reorder(a), reorder(b), ascending=ascending)) == reorder(sorted(chain(a, b)))
        s = NamedObject("__test-sentinel")
        assert list(iter_merge_two(reorder([1, 3]), reorder([2, 3]), ascending=ascending, s=s)) == reorder([1, 2, 3, 3])
        with pytest.raises(TypeError):
            list(
                iter_merge_two(
                    reorder([(1, 5), (5, "a"), (7, 4)]), reorder([(2, 3), (5, 2), (8, 5)]), ascending=ascending
                )
            )
        assert list(
            iter_merge_two(
                reorder([(1, 5), (2, "a")]), reorder([(2, 2), (3, 5)]), key=lambda x: x[0], ascending=ascending
            )
        ) == reorder([(1, 5), *reorder([(2, "a"), (2, 2)]), (3, 5)])


def test_algorithm_iter_merge_and_unique():
    for merge in (iter_merge, iter_merge_unique):
        assert list(merge()) == []
        assert list(merge([])) == []
        assert list(merge([], [])) == []
        assert list(merge([], [], [])) == []
    for ascending in [True, False]:
        reorder = (lambda x: x) if ascending else lambda x: list(reversed(x))
        for n in range(1, 5):
            for _ in range(20):
                xs = [reorder(sorted(random.randint(1, 99) for _ in range(random.randint(15, 25)))) for _ in range(n)]
                xs.insert(random.randint(0, n - 1), [])
                assert list(iter_merge(*xs, ascending=ascending)) == sorted(chain(*xs), reverse=not ascending)
                assert list(iter_merge_unique(*xs, ascending=ascending)) == sorted(
                    set(chain(*xs)), reverse=not ascending
                )
        xs = [reorder([(1, 5), (5, "a"), (7, 4)]), reorder([(2, 3), (5, 2), (8, 5)]), reorder([(3, 3), (6, 5)])]
        with pytest.raises(TypeError):
            list(iter_merge(*xs, ascending=ascending))
        assert list(iter_merge(*xs, key=lambda x: x[0], ascending=ascending)) == reorder(
            [(1, 5), (2, 3), (3, 3), *reorder([(5, "a"), (5, 2)]), (6, 5), (7, 4), (8, 5)]
        )


def test_algorithm_iter_all_same():
    assert iter_all_same() is True
    assert iter_all_same([]) is True
    assert iter_all_same([False]) is True
    assert iter_all_same([None]) is True
    assert iter_all_same([5, 5]) is True
    assert iter_all_same([5, 5], [5]) is True
    assert iter_all_same([5, 4], [5]) is False
    assert iter_all_same([5, 5], [4]) is False
    assert iter_all_same(["tf", "tf"], ["tf"]) is True
    assert iter_all_same(["tf", 42], ["tf"]) is False
