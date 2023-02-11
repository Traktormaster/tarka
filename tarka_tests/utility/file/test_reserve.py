import os
import re
import uuid
from pathlib import Path
from typing import Union, Tuple

from tarka.utility.file.reserve import ReserveFile


def test_file_reserve(tmp_path: Path):
    root = tmp_path / str(uuid.uuid4())
    root.mkdir()
    rf = ReserveFile()

    def _reserve(in_: str, out_: Union[Tuple[str, str], str]):
        def _check(o_):
            if isinstance(out_, str):
                assert o_ == out_
            else:
                assert re.match("^" + re.escape(out_[0]) + r"\w{8}" + re.escape(out_[1]) + "$", o_)

        for args in [(root, in_), (root / in_,)]:
            fd, o = rf.open_reserve(*args)
            os.write(fd, c := os.urandom(16))
            os.close(fd)
            assert (root / o).read_bytes() == c
            _check(o)
            (root / o).unlink()
            o = rf.reserve(*args)
            _check(o)
            if len(args) == 2:
                (root / o).unlink()

    for i_name, o_name in [
        # created as-is
        ("a", "a"),
        (".a", ".a"),
        (".foo.", ".foo."),
        (". .a.txt", ". .a.txt"),
        (". .ab.cd.tar.gz", ". .ab.cd.tar.gz"),
        # conflicts with as-is
        ("a", ("a", "")),
        (".a", (".a", "")),
        (".foo.", (".foo.", "")),
        (". .a.txt", (". .a", ".txt")),
        (". .ab.cd.tar.gz", (". .ab.cd", ".tar.gz")),
        # truncates
        ("a" * 300 + ".txt", "a" * 251 + ".txt"),
        ("a" * 300 + ".txt", ("a" * 243, ".txt")),
        ("a" * 150 + "." + "x" * 150, "a" * 128 + "x" * 127),
        ("a" * 150 + "." + "x" * 150, ("a" * 124, "x" * 123)),  # conflicts
        ("a" * 150 + "." + "y" * 149, "a" * 128 + "y" * 127),
    ]:
        _reserve(i_name, o_name)