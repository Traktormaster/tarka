from typing import Generator


def is_utf8_codepoint_start(b: int) -> bool:
    """
    Returns True if the byte-value could be the first byte of an UTF-8 codepoint.
    NOTE: Currently not used, more than 4 bytes sequence starts are also accepted. This should not be a problem,
    because they do not collide with the encoding of continuation bytes.
    :param b: assumed to be in range(256) like a value of a bytes sequence
    """
    return b < 0x80 or 0xC0 <= b


def is_utf8_codepoint_continuation(b: int) -> bool:
    """
    Returns True if the byte-value could be a continuation byte of an UTF-8 codepoint.
    :param b: a value of a bytes sequence
    """
    return 0x80 <= b < 0xC0


def iter_chunk_keep_utf8_codepoints(
    bs: bytes, chunk_size_max: int, longest_encoded_codepoint: int = 4
) -> Generator[bytes, None, None]:
    """
    Split the input bytes array into maximum-length chunks while respecting utf8 codepoint boundaries.
    """
    if chunk_size_max < longest_encoded_codepoint:
        raise RuntimeError("can't chunk utf8 shorter than longest encoded codepoint")
    i = 0
    j = chunk_size_max
    while j < len(bs):
        for _ in range(longest_encoded_codepoint - 1):
            if is_utf8_codepoint_start(bs[j]):
                break
            j -= 1
        yield bs[i:j]
        i = j
        j += chunk_size_max
    yield bs[i:]
