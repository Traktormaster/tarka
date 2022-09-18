"""
This provides a canonical binary serialization for the main Python primitive types.
The primary use-case is to be able to produce a deterministic checksum/signature of an arbitrary data structure,
but deserialization is implemented as well.
For faster, space-efficient and wide compatibility serialization where deterministic form is not needed, use msgpack.
"""
import hashlib
import re
import struct
from io import BytesIO
from typing import Type, Callable, Optional, Union, Any

from tarka.utility.algorithm.traverse import traverse, TraverseType, SORTED_STR_TRAVERSE, TraverseTypeMap

StreamProcessFn = Callable[[bytes], Any]
TraverseDeterministicTransformMap = dict[Type[TraverseType], Callable[[StreamProcessFn, TraverseType], None]]


def _ppd_int(acc: StreamProcessFn, o: int):
    b = str(o).encode("utf-8")
    acc(str(len(b)).encode("utf-8"))
    acc(b"i")
    acc(b)


def _ppd_str(acc: StreamProcessFn, o: str):
    b = o.encode("utf-8")
    acc(str(len(b)).encode("utf-8"))
    acc(b"s")
    acc(b)


def _ppd_float(acc: StreamProcessFn, o: float):
    acc(b"f")
    acc(struct.pack(">d", o))


def _ppd_bool(acc: StreamProcessFn, o: bool):
    acc(b"T" if o else b"F")


def _ppd_none_type(acc: StreamProcessFn, o):
    acc(b"N")


def _ppd_bytes(acc: StreamProcessFn, o: bytes):
    acc(str(len(o)).encode("utf-8"))
    acc(b"b")
    acc(o)


def _ppd_list(acc: StreamProcessFn, o: list):
    acc(str(len(o)).encode("utf-8"))
    acc(b"l")


def _ppd_dict(acc: StreamProcessFn, o: dict):
    acc(str(len(o) << 1).encode("utf-8"))
    acc(b"d")


def _ppd_tuple(acc: StreamProcessFn, o: tuple):
    acc(str(len(o)).encode("utf-8"))
    acc(b"t")


def _ppd_set(acc: StreamProcessFn, o: set):
    acc(str(len(o)).encode("utf-8"))
    acc(b"h")


def _ppd_frozenset(acc: StreamProcessFn, o: frozenset):
    acc(str(len(o)).encode("utf-8"))
    acc(b"H")


VERSION_TAG = b"1v"
PYTHON_PRIMITIVES_DETERMINISTIC_TRANSFORM_MAP: TraverseDeterministicTransformMap = {
    str: _ppd_str,
    int: _ppd_int,
    float: _ppd_float,
    bool: _ppd_bool,
    type(None): _ppd_none_type,
    bytes: _ppd_bytes,
    list: _ppd_list,
    dict: _ppd_dict,
    tuple: _ppd_tuple,
    set: _ppd_set,
    frozenset: _ppd_frozenset,
}


def deterministic_dumps(arg: TraverseType) -> bytes:
    """
    Get the canonical binary serialization of the object in whole.
    """
    buf = BytesIO()
    deterministic_transform(arg, buf.write)
    return buf.getvalue()


def deterministic_hash(arg: TraverseType, algo: str, **algo_kw) -> bytes:
    """
    Calculate the canonical hash of the object.
    """
    h = getattr(hashlib, algo)(**algo_kw)
    deterministic_transform(arg, h.update)
    return h.digest()


def deterministic_transform(arg: TraverseType, acc: StreamProcessFn) -> None:
    """
    Process the canonical binary serialization stream of the object.
    """
    _deterministic_transform(arg, acc, prefix=VERSION_TAG)


def _deterministic_transform(
    arg: TraverseType,
    acc: StreamProcessFn,
    tr_map: TraverseDeterministicTransformMap = None,
    traverse_map: TraverseTypeMap = None,
    prefix: bytes = None,
) -> None:
    if tr_map is None:
        tr_map = PYTHON_PRIMITIVES_DETERMINISTIC_TRANSFORM_MAP
    if traverse_map is None:
        traverse_map = SORTED_STR_TRAVERSE
    if prefix is not None:
        acc(prefix)
    for x in traverse(arg, traverse_map):
        tr_map[type(x)](acc, x)


TraverseDeterministicTransformUnmap = dict[bytes, tuple[int, Callable[[bytes], TraverseType]]]

DYNAMIC_LENGTH_VALUE = -5
DYNAMIC_LENGTH_COLLECTION = -10
PYTHON_PRIMITIVES_DETERMINISTIC_TRANSFORM_UNMAP: TraverseDeterministicTransformUnmap = {
    b"s": (DYNAMIC_LENGTH_VALUE, lambda v: v.decode("utf-8")),
    b"i": (DYNAMIC_LENGTH_VALUE, lambda v: int(v.decode("utf-8"))),
    b"f": (8, lambda v: struct.unpack(">d", v)[0]),
    b"T": (0, lambda _: True),
    b"F": (0, lambda _: False),
    b"N": (0, lambda _: None),
    b"b": (DYNAMIC_LENGTH_VALUE, lambda v: v),
    b"l": (DYNAMIC_LENGTH_COLLECTION, lambda l: l),
    b"d": (DYNAMIC_LENGTH_COLLECTION, lambda l: {l[i]: l[i + 1] for i in range(0, len(l), 2)}),
    b"t": (DYNAMIC_LENGTH_COLLECTION, lambda l: tuple(l)),
    b"h": (DYNAMIC_LENGTH_COLLECTION, lambda l: set(l)),
    b"H": (DYNAMIC_LENGTH_COLLECTION, lambda l: frozenset(l)),
}

LOAD_NUM_RE = re.compile(rb"([0-9]+)")


class _LoadParent:
    __slots__ = ("parent_index", "children", "child")

    def __init__(self, parent_index: int, children: int):
        self.parent_index = parent_index
        self.children = children
        self.child = 0

    def next_child(self) -> tuple[int, int, bool]:
        c = self.child
        assert c < self.children
        self.child = c + 1
        return self.parent_index, c, self.child == self.children


def deterministic_loads(b: bytes) -> TraverseType:
    """
    Restore the object from the canonical binary serialization.
    Implemented without recursion.
    """
    if not b.startswith(VERSION_TAG):
        raise ValueError()
    # List of Tuple[parent-index, child-index, collection--type-value-fn, collection-length-accum OR self-value]
    data_map: list[tuple[int, int, Optional[Callable], Union[list[TraverseType], TraverseType]]] = []
    parent_stack: list[_LoadParent] = [_LoadParent(-1, 1)]
    i = len(VERSION_TAG)
    while i < len(b):
        nm = LOAD_NUM_RE.match(b, i)
        if nm:
            g = nm.group(1)
            num = int(g.decode("utf-8"))
            i += len(g)
        else:
            num = None
        t = b[i : i + 1]
        len_type, val_fn = PYTHON_PRIMITIVES_DETERMINISTIC_TRANSFORM_UNMAP[t]
        if (num is None) is not (len_type >= 0):
            ValueError()
        if num is None:
            num = len_type
        i += 1
        pi, nc, pd = parent_stack[-1].next_child()
        if pd:
            try:
                parent_stack.pop()
            except IndexError:
                raise ValueError()
        if len_type == DYNAMIC_LENGTH_COLLECTION:
            if num > 0:
                parent_stack.append(_LoadParent(len(data_map), num))
            data_map.append((pi, nc, val_fn, [None] * num))
        else:
            data_map.append((pi, nc, None, val_fn(b[i : i + num])))
            i += num
    if parent_stack:
        # serialized data did not end correctly
        raise ValueError()
    for i in range(len(data_map) - 1, 0, -1):
        parent_index, child_index, collection_type_value_fn, value = data_map[i]
        data_map[parent_index][3][child_index] = (
            value if collection_type_value_fn is None else collection_type_value_fn(value)
        )
    _, _, collection_type_value_fn, value = data_map[0]
    return value if collection_type_value_fn is None else collection_type_value_fn(value)
