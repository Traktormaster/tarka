import os
from pathlib import Path

import pytest

from tarka.logging.utility import get_log_file_path


def test_get_log_file_path(tmp_path: Path):
    home = Path("~").expanduser()

    assert get_log_file_path("~/my.log") == home.joinpath("my.log")
    assert get_log_file_path(os.path.join(str(home), "my.log")) == home.joinpath("my.log")
    assert get_log_file_path(Path("~/my.log")) == home.joinpath("my.log")
    assert get_log_file_path(home / "my.log") == home.joinpath("my.log")

    log_dir = tmp_path / "asd" / "mno" / "qwe"
    assert not log_dir.exists()
    p = get_log_file_path(log_dir)
    assert p.parent == log_dir
    assert p.name.endswith(".log")
    p2 = get_log_file_path(log_dir)
    assert p2.parent == log_dir
    assert p2.name.endswith(".log")

    assert p.name != p2.name

    assert get_log_file_path(p) == p
    assert get_log_file_path(p2) == p2

    p.write_text("yes")
    with pytest.raises(OSError):
        get_log_file_path(p / "x")
    with pytest.raises(OSError):
        get_log_file_path(p / "x.log")
