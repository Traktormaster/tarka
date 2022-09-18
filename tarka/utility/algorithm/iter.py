from typing import Iterable, Any, TypeVar, Generator, Iterator, Hashable

_HashableT = TypeVar("_HashableT", bound=Hashable)
_AnyT = TypeVar("_AnyT", bound=Any)


def iter_unique(*item_iters: Iterable[_HashableT]) -> Generator[_HashableT, None, None]:
    """
    Yield unique(ly hashable) items for the iterables.
    """
    seen = set()
    for item_iter in item_iters:
        for item in item_iter:
            if item not in seen:
                seen.add(item)
                yield item


def iter_merge_two(a: Iterable[_AnyT], b: Iterable[_AnyT]) -> Generator[_AnyT, None, None]:
    """
    Two-way merge using the iterator interface.
    The iterators must yield their items sorted in ascending order.
    """
    a = iter(a)
    b = iter(b)
    s = object()  # sentinel object as end-of-iteration marker
    try:
        i = next(a)
    except StopIteration:
        i = s
    try:
        j = next(b)
    except StopIteration:
        j = s
    while i is not s and j is not s:
        if i <= j:
            yield i
            try:
                i = next(a)
            except StopIteration:
                i = s
        else:
            yield j
            try:
                j = next(b)
            except StopIteration:
                j = s
    if i is not s:
        yield i
        while True:
            try:
                yield next(a)
            except StopIteration:
                break
    if j is not s:
        yield j
        while True:
            try:
                yield next(b)
            except StopIteration:
                break


def iter_merge(*item_iters: Iterable[_AnyT]) -> Iterator[_AnyT]:
    """
    Multi merge using the iterator interface.
    The iterators must yield their items sorted in ascending order.
    """
    if not item_iters:
        return iter(())
    m = iter(item_iters[0])
    for i in range(1, len(item_iters)):
        m = iter_merge_two(m, iter(item_iters[i]))
    return m


def iter_merge_unique(*item_iters: Iterable[_AnyT]) -> Generator[_AnyT, None, None]:
    """
    Yield unique items for the iterables by merge-iterating over them.
    The iterators must yield their items sorted in ascending order.
    """
    m = iter_merge(*item_iters)
    try:
        last_item = next(m)
    except StopIteration:
        return  # all empty
    yield last_item
    try:
        while True:
            item = next(m)
            if item != last_item:
                yield item
                last_item = item
    except StopIteration:
        pass


def iter_all_same(*item_iters: Iterable[Any]) -> bool:
    """
    Check if all values equal in the iterables.
    """
    # select first value
    for i in range(len(item_iters)):
        it = iter(item_iters[i])
        for value in it:
            break
        else:
            continue  # empty iterable
        break
    else:
        return True  # all iterables are empty
    # continue iterable of first value
    for v in it:
        if value != v:
            return False
    i += 1
    while i < len(item_iters):
        for v in item_iters[i]:
            if value != v:
                return False
        i += 1
    return True
