import hashlib

from tarka.utility.serialize.deterministic import (
    deterministic_dumps,
    deterministic_loads,
    deterministic_transform,
    deterministic_hash,
)


def test_deterministic():
    def _deterministic_sha256(arg):
        h = hashlib.sha256()
        deterministic_transform(arg, h.update)
        return h.digest()

    for o, b in [
        (None, b"1vN"),
        (889, b"1v3i889"),
        ("yés", b"1v4sy\xc3\xa9s"),
        ([45, "tsX"], b"1v2l2i453stsX"),
        ([[], (), {}, set(), frozenset()], b"1v5l0l0t0d0h0H"),
        ([-2, 3.73, True, False, None, b"xx", "ss"], b"1v7l2i-2f@\r\xd7\n=p\xa3\xd7TFN2bxx2sss"),
        ({"k0": (5, 9), ("h", 8): None, "a": b"t"}, b"1v6d2t1sh1i8N1sa1bt2sk02t1i51i9"),
        ({"k0": {(5, 9), b"data", 55, "str", None}, False: True}, b"1v4dFT2sk05h2t1i51i92i55N4bdata3sstr"),
        ({(5,), (), b"qq", 55, "str", True, frozenset([3, 5])}, b"1v7h0t1t1i52i55T2bqq2H1i31i53sstr"),
    ]:
        tmp = deterministic_dumps(o)
        assert tmp == b, str(tmp)
        tmp = deterministic_loads(b)
        assert tmp == o, str(tmp)
        tmp = _deterministic_sha256(o)
        assert tmp == hashlib.sha256(b).digest(), str(tmp)
        tmp = deterministic_hash(o, "sha512")
        assert tmp == hashlib.sha512(b).digest(), str(tmp)
        tmp = deterministic_hash(o, "blake2b", digest_size=32)
        assert tmp == hashlib.blake2b(b, digest_size=32).digest(), str(tmp)
