import os

import pytest

from tarka.utility.envvar import parse_bool_envvar, parse_int_envvar


def test_tarka_envvar_parsers(monkeypatch):
    n = "_TEST_ENV_VAR_NAME"
    assert n not in os.environ

    assert parse_bool_envvar(n) is None
    assert parse_int_envvar(n) is None

    assert parse_bool_envvar(n, False) is False
    assert parse_bool_envvar(n, True) is True
    assert parse_int_envvar(n, 0) == 0
    assert parse_int_envvar(n, 10) == 10

    for raw, boolean, numeric, string in [
        ("1", True, 1, "1"),
        ("YES", True, Exception, "YES"),
        ("On", True, Exception, "On"),
        ("true", True, Exception, "true"),
        ("0", False, 0, "0"),
        ("10", False, 10, "10"),
        ("-1", False, -1, "-1"),
        ("", False, Exception, ""),
        ("asd", False, Exception, "asd"),
        ("/path/to/file", False, Exception, "/path/to/file"),
    ]:
        monkeypatch.setenv(n, raw)

        assert parse_bool_envvar(n) == boolean
        if not isinstance(numeric, int):
            with pytest.raises(numeric):
                parse_int_envvar(n)
        else:
            assert parse_int_envvar(n) == numeric
