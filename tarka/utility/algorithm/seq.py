from bisect import bisect_left
from typing import Sequence, Any, Union


def seq_eq(a: Sequence, b: Sequence) -> bool:
    """
    Usable to check equality of items in a list and tuple. (or any custom sequence object)
    """
    if len(a) != len(b):
        return False
    return all(map(lambda x, y: x == y, a, b))


def seq_closest(seq: Sequence[Union[float, int]], value: Union[float, int]) -> Union[float, int]:
    """
    Return the closest numerical value in an ascending sorted sequence.
    In case of two values being equally close, choose the smaller.
    """
    if len(seq) == 0:
        raise ValueError("Can't find closest value in empty sequence")
    pos = bisect_left(seq, value)
    if pos == 0:
        return seq[0]
    if pos == len(seq):
        return seq[-1]
    before = seq[pos - 1]
    after = seq[pos]
    if after - value < value - before:
        return after
    return before


def seq_closest_index(seq: Sequence[Union[float, int]], value: Union[float, int]) -> int:
    """
    Return the index of the closest numerical value in an ascending sorted sequence.
    In case of two values being equally close, choose the earlier.
    """
    if len(seq) == 0:
        raise ValueError("Can't find closest value in empty sequence")
    pos = bisect_left(seq, value)
    if pos == 0:
        return 0
    if pos == len(seq):
        return len(seq) - 1
    before = seq[pos - 1]
    after = seq[pos]
    if after - value < value - before:
        return pos
    return pos - 1
