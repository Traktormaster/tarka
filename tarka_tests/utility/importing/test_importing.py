import json
import subprocess
import sys
import warnings

from tarka.utility.importing import import_optional


def _run(tmp_path, import_path: str):
    output_path = tmp_path / "_output.temp"
    p = subprocess.Popen([sys.executable, "-m", "tarka_tests.utility.importing.fwdimp", import_path, str(output_path)])
    try:
        assert p.wait(10) == 0
        return json.loads(output_path.read_bytes())
    finally:
        if p.poll() is None:
            p.terminate()
            p.wait(10)


def test_forward_import_recursively(tmp_path):
    r = _run(tmp_path, "tarka_tests.utility.importing.d0")
    assert r == [
        "tarka_tests.utility.importing.d0",
        "tarka_tests.utility.importing.d0.d1",
        "tarka_tests.utility.importing.d0.d1.f2",
        "tarka_tests.utility.importing.d0.f0",
        "tarka_tests.utility.importing.d0.f1",
    ], str(r)


def test_import_optional():
    with warnings.catch_warnings(record=True) as w:
        assert len(w) == 0
        assert import_optional("tarka_tests.utility.importing.d1") is None
        assert len(w) == 1
        assert "Can't import optional tarka_tests.utility.importing.d1" in str(w[-1].message)
        assert import_optional("tarka_tests.utility.importing.d2", False) is None
        assert len(w) == 1
