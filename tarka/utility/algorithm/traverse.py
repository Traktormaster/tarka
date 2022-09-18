from typing import Callable, Union, TypeVar, Type, Optional, Iterator

JSONPrimitiveTypes = Union[str, int, float, list, dict, bool, None]
PythonPrimitiveTypes = Union[JSONPrimitiveTypes, bytes, tuple, set, frozenset]

TraverseType = TypeVar("TraverseType")
TraverseTypeMap = dict[Type[TraverseType], Callable[[TraverseType], Optional[Iterator[TraverseType]]]]


NATIVE_TRAVERSE: TraverseTypeMap = {
    list: lambda o: iter(o),
    tuple: lambda o: iter(o),
    set: lambda o: iter(o),
    frozenset: lambda o: iter(o),
    dict: lambda o: (x for k_v in o.items() for x in k_v),
}

# Only use this if all items in collection objects are comparable. (usually the same type).
SORTED_NAIVE_TRAVERSE: TraverseTypeMap = {
    **NATIVE_TRAVERSE,
    set: lambda o: iter(sorted(o)),
    frozenset: lambda o: iter(sorted(o)),
    dict: lambda o: iter(x for k in sorted(o.keys()) for x in (k, o[k])),
}

# Prefer to use the naive sorted traverse-map if possible for performance reasons.
SORTED_STR_TRAVERSE: TraverseTypeMap = {
    **NATIVE_TRAVERSE,
    set: lambda o: iter(sorted(o, key=lambda x: str(x))),
    frozenset: lambda o: iter(sorted(o, key=lambda x: str(x))),
    dict: lambda o: iter(x for k in sorted(o.keys(), key=lambda x: str(x)) for x in (k, o[k])),
}


class TraverseCycleError(RuntimeError):
    pass


def traverse(o: TraverseType, type_map: TraverseTypeMap = None) -> Iterator[TraverseType]:
    """
    Recursively traverse over an object structure by customizable traversal rules by object type.
    Each visited object is yielded and are directly followed by their children if any.
    The implementation uses a stack of iterator objects, it has no recursion depth limit.
    The objects that yield children are tracked in the traversal path to avoid cycles.
    """
    if type_map is None:
        # Use the native iteration order of primitive types if no traversal map is specified.
        type_map = NATIVE_TRAVERSE
    path: set[int] = set()
    stack: list[tuple[TraverseType, Iterator[TraverseType]]] = []
    yield o
    t = type_map.get(type(o))
    if t:
        if (o_id := id(o)) in path:
            raise TraverseCycleError()
        path.add(o_id)
        stack.append((o_id, t(o)))
    while stack:
        try:
            o = next(stack[-1][1])
        except StopIteration:
            path.remove(stack.pop()[0])
            continue
        yield o
        t = type_map.get(type(o))
        if t:
            if (o_id := id(o)) in path:
                raise TraverseCycleError()
            path.add(o_id)
            stack.append((o_id, t(o)))
