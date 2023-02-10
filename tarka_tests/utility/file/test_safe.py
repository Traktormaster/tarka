import os
import random
from pathlib import Path

import pytest

from tarka.utility.file.safe import SafeFile


def test_file_safe_file(tmp_path: Path):
    sf = SafeFile(str(tmp_path / "best.json"))
    with pytest.raises(FileNotFoundError):
        sf.read()
    v1 = os.urandom(random.randint(500, 1000) * 20)
    sf.write(v1)
    assert set(item.name for item in tmp_path.iterdir()) == {"best.json"}
    assert sf.normal.read_bytes() == v1
    assert not sf.backup.exists()
    assert sf.read() == v1
    v2 = os.urandom(random.randint(500, 1000) * 20)
    sf.write(v2)
    assert set(item.name for item in tmp_path.iterdir()) == {"best.json", "best.json.bak"}
    assert sf.normal.read_bytes() == v2
    assert sf.backup.read_bytes() == v1
    assert sf.read() == v2
    sf.normal.unlink()
    assert set(item.name for item in tmp_path.iterdir()) == {"best.json.bak"}
    assert not sf.normal.exists()
    assert sf.backup.read_bytes() == v1
    assert sf.read() == v1
    sf.write(v2)
    assert set(item.name for item in tmp_path.iterdir()) == {"best.json", "best.json.bak"}
    assert sf.normal.read_bytes() == v2
    assert sf.backup.read_bytes() == v1
    assert sf.read() == v2
    v3 = os.urandom(random.randint(500, 1000) * 20)
    sf.write(v3)
    assert set(item.name for item in tmp_path.iterdir()) == {"best.json", "best.json.bak"}
    assert sf.normal.read_bytes() == v3
    assert sf.backup.read_bytes() == v2
    assert sf.read() == v3
