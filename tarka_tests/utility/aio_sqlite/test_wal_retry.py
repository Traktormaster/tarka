import asyncio
import time
import uuid
from contextlib import AsyncExitStack
from functools import partialmethod, partial

import pytest

from tarka.utility.aio_sqlite import AbstractAioSQLiteDatabase, _sqlite_retry


class _SQLiteDbgException(Exception):
    pass


class _TestingAioSQLiteDatabase(AbstractAioSQLiteDatabase):
    def _setup(self):
        self._con.execute("CREATE TABLE IF NOT EXISTS Data0 (key TEXT PRIMARY KEY, value TEXT)")

    def _write_impl(self, key, value, error=None, delay=0.0):
        time.sleep(delay)
        if error:
            raise error
        c = self._con.cursor()
        c.execute("REPLACE INTO Data0(key, value) VALUES (?, ?)", (key, value))
        return c.lastrowid

    def _read_impl(self, key):
        rows = self._con.execute("SELECT value FROM Data0 WHERE key = ?", (key,)).fetchall()
        if rows:
            return rows[0][0]

    def _retry_checkpoint(self):
        _sqlite_retry(partial(AbstractAioSQLiteDatabase._checkpoint, self), -10)

    checkpoint = partialmethod(AbstractAioSQLiteDatabase._run_job, _retry_checkpoint, begin_immediate=False)
    write_checkpoint = partialmethod(
        AbstractAioSQLiteDatabase._run_job, _write_impl, post_process_fn=AbstractAioSQLiteDatabase._checkpoint
    )
    write = partialmethod(AbstractAioSQLiteDatabase._run_job, _write_impl)
    write_no_immediate = partialmethod(AbstractAioSQLiteDatabase._run_job, _write_impl, begin_immediate=False)
    read = partialmethod(AbstractAioSQLiteDatabase._run_job, _read_impl, begin_immediate=False)


@pytest.mark.asyncio
async def test_aio_sqlite_wal_retry(tmpdir):
    loop = asyncio.get_event_loop()
    db_path = str(tmpdir.join(str(uuid.uuid4())))
    async with AsyncExitStack() as stack:
        dba = await stack.enter_async_context(_TestingAioSQLiteDatabase.create(loop, db_path, 10.0))
        dbb = await stack.enter_async_context(_TestingAioSQLiteDatabase.create(loop, db_path, 10.0))
        dbc = await stack.enter_async_context(_TestingAioSQLiteDatabase.create(loop, db_path, 10.0))
        await asyncio.sleep(0.25)  # all need to start up to have stable locking

        await dba.write("kx", "vx")
        assert await dbc.read("kx") == "vx"

        t = time.perf_counter()

        async def _read_before(db_, k_, r_):
            v_ = await db_.read(k_)
            assert time.perf_counter() < t
            assert v_ == r_

        # test multiple writes serialize and allow parallel reads
        t = time.perf_counter() + 0.5
        at = asyncio.create_task(dba.write("k0", "v0", None, 0.5))
        await asyncio.sleep(0.1)
        await _read_before(dbc, "kx", "vx")
        await _read_before(dbc, "k0", None)
        bt = asyncio.create_task(dbb.write("k1", "v1", None, 0.025))
        await asyncio.sleep(0.1)
        await _read_before(dbc, "kx", "vx")
        await _read_before(dbc, "k0", None)
        await _read_before(dbc, "k1", None)
        await at
        assert not bt.done()
        assert time.perf_counter() >= t
        await bt
        assert await dbc.read("kx") == "vx"
        assert await dbc.read("k0") == "v0"
        assert await dbc.read("k1") == "v1"

        # tx fail is handled well
        t = time.perf_counter() + 0.5
        at = asyncio.create_task(dba.write("k0", "v2", _SQLiteDbgException(), 0.5))
        await asyncio.sleep(0.1)
        bt = asyncio.create_task(dbb.write("k0", "v3", None, 0.5))
        await asyncio.sleep(0.1)
        await _read_before(dbc, "k0", "v0")
        with pytest.raises(_SQLiteDbgException):
            await at
        t += 0.5
        await _read_before(dbc, "k0", "v0")
        await bt
        assert time.perf_counter() >= t
        assert await dbc.read("kx") == "vx"
        assert await dbc.read("k0") == "v3"
        assert await dbc.read("k1") == "v1"

        # test non-immediate write behaviour
        t = time.perf_counter() + 0.5
        at = asyncio.create_task(dba.write("k0", "v4", None, 0.5))
        await asyncio.sleep(0.1)
        await _read_before(dbc, "k0", "v3")
        await dbb.write_no_immediate("k0", "v5")  # deferred waits without retry loop
        assert at.done()
        assert time.perf_counter() >= t
        assert await dbc.read("kx") == "vx"
        assert await dbc.read("k0") == "v5"
        assert await dbc.read("k1") == "v1"

        # test checkpoint retry behaviour
        t = time.perf_counter() + 0.5
        at = asyncio.create_task(dba.write_checkpoint("k2", "v2", None, 0.5))
        bt = asyncio.create_task(dbb.checkpoint())
        await asyncio.sleep(0.1)
        ts = [
            *[asyncio.create_task(dba.write_checkpoint("k2", f"v{10+i}", None)) for i in range(20)],
            *[asyncio.create_task(dbb.checkpoint()) for i in range(20)],
        ]
        # parallel reads still work, no checkpoint mode impedes readers
        await _read_before(dbc, "k2", None)
        await asyncio.gather(at, bt, *ts)
        assert await dbc.read("k2") == "v29"
