import os

import pytest


def _pg_connect_url():
    pg = os.environ.get("TARKA_TESTING_POSTGRESQL_CONNECT_URL")
    if not pg:
        pytest.skip("pg url no set")
    return pg


@pytest.fixture
def pg_connect_url():
    return _pg_connect_url()


@pytest.fixture(params=["aiosqlite", "asyncpg"])
def db_connect_url(tmp_path, request):
    if request.param == "aiosqlite":
        return f"sqlite+aiosqlite:///{(tmp_path / 'xy.db').as_posix()}"
    elif request.param == "asyncpg":
        return _pg_connect_url()
    else:
        assert False, "not implemented"
