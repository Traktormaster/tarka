import pytest

from tarka.utility.utf8 import is_utf8_codepoint_start, is_utf8_codepoint_continuation, iter_chunk_keep_utf8_codepoints


def test_is_utf8_codepoint():
    byte_values = set(range(256))
    start_values = set(i for i in byte_values if is_utf8_codepoint_start(i))
    cont_values = set(i for i in byte_values if is_utf8_codepoint_continuation(i))
    assert not start_values.intersection(cont_values)
    assert start_values.union(cont_values) == byte_values


def test_iter_chunk_keep_utf8_codepoints():
    def _f(*args):
        return list(iter_chunk_keep_utf8_codepoints(*args))

    b1 = "a".encode()
    b2 = "é".encode()
    b3 = "❤".encode()
    b4 = "😴".encode()

    assert _f(b4, 4) == [b4]
    assert _f(b1, 4) == [b1]
    assert _f(b4 * 2, 4) == [b4, b4]
    assert _f(b3 * 2, 4) == [b3, b3]
    assert _f(b2 * 4, 4) == [b2 * 2, b2 * 2]
    assert _f(b1 * 8, 4) == [b1 * 4, b1 * 4]
    assert _f(b4 * 2, 5) == [b4, b4]
    assert _f(b1 + b4 * 2, 5) == [b1 + b4, b4]
    assert _f(b2 + b4 * 2, 5) == [b2, b4, b4]
    assert _f(b3 + b4 * 2, 5) == [b3, b4, b4]
    assert _f(b3 * 3, 5) == [b3, b3, b3]
    assert _f(b3 * 3, 6) == [b3 + b3, b3]

    invalid = b"\x80" * 9
    with pytest.raises(RuntimeError):
        _f(invalid, 3)
    assert _f(invalid, 4) == [b"\x80", b"\x80", b"\x80", b"\x80", b"\x80", b"\x80\x80\x80\x80"]
    assert _f(invalid, 5) == [b"\x80\x80", b"\x80\x80", b"\x80\x80\x80\x80\x80"]
    assert _f(invalid, 6) == [b"\x80\x80\x80", b"\x80\x80\x80\x80\x80\x80"]
    assert _f(invalid, 7) == [b"\x80\x80\x80\x80", b"\x80\x80\x80\x80\x80"]
    assert _f(invalid, 8) == [b"\x80\x80\x80\x80\x80", b"\x80\x80\x80\x80"]
    assert _f(invalid, 9) == [b"\x80\x80\x80\x80\x80\x80\x80\x80\x80"]
    assert _f(invalid, 10) == [b"\x80\x80\x80\x80\x80\x80\x80\x80\x80"]
