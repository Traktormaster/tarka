import pytest

from tarka.utility.algorithm.traverse import (
    traverse,
    TraverseCycleError,
    NATIVE_TRAVERSE,
    SORTED_NAIVE_TRAVERSE,
    SORTED_STR_TRAVERSE,
)


def test_traverse_root_types():
    assert list(traverse("bob")) == ["bob"]
    assert list(traverse(77)) == [77]
    assert list(traverse(8.5)) == [8.5]
    tmp = [8, 3, "bc"]
    assert list(traverse(tmp)) == [tmp, 8, 3, "bc"]
    tmp = {"lemon": 5, 95: "yes"}
    assert list(traverse(tmp)) == [tmp, "lemon", 5, 95, "yes"]
    assert list(traverse(True)) == [True]
    assert list(traverse(None)) == [None]
    assert list(traverse(b"bob")) == [b"bob"]
    tmp = (8, 3, "bc")
    assert list(traverse(tmp)) == [tmp, 8, 3, "bc"]
    tmp = {8, 3, "bc"}
    assert list(traverse(tmp)) == [tmp, *tmp]
    tmp = frozenset([8, 3, "bc"])
    assert list(traverse(tmp)) == [tmp, *tmp]


def test_traverse_cycles():
    r = []
    r.append(r)
    with pytest.raises(TraverseCycleError):
        list(traverse(r))
    r = []
    t = (r,)
    r.append(t)
    with pytest.raises(TraverseCycleError):
        list(traverse(r))
    with pytest.raises(TraverseCycleError):
        list(traverse(t))


def test_traverse_mappings():
    root = set()
    for i in range(0, 500, 10):
        root.add(str(i))
    assert list(traverse(root)) == [root, *root]
    assert list(traverse(root, NATIVE_TRAVERSE)) == [root, *root]
    assert list(traverse(root, SORTED_NAIVE_TRAVERSE)) == [root, *sorted(root)]
    assert list(traverse(root, SORTED_STR_TRAVERSE)) == [root, *sorted(root, key=lambda x: str(x))]
    root.add(88)
    assert list(traverse(root, NATIVE_TRAVERSE)) == [root, *root]
    with pytest.raises(TypeError):
        list(traverse(root, SORTED_NAIVE_TRAVERSE))
    assert list(traverse(root, SORTED_STR_TRAVERSE)) == [root, *sorted(root, key=lambda x: str(x))]
