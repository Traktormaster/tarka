import asyncio
import time
import uuid
from functools import partialmethod

import pytest

from tarka.utility.aio_sqlite import AbstractAioSQLiteDatabase


class _SQLiteDbgException(Exception):
    pass


class _TestingAioSQLiteDatabase(AbstractAioSQLiteDatabase):
    __slots__ = ("_wal",)

    def __init__(self, wal: bool, *args):
        self._wal = wal
        AbstractAioSQLiteDatabase.__init__(self, *args)

    def _initialise(self):
        if self._wal:
            AbstractAioSQLiteDatabase._initialise(self)

    def _setup(self):
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS Data0 ("
            " account_id INTEGER,"
            " filename TEXT,"
            " meta BLOB,"
            " mtime REAL,"
            " PRIMARY KEY (account_id, filename)"
            ")"
        )
        self._con.execute("CREATE INDEX IF NOT EXISTS Data0_account_id ON  Data0(account_id)")
        self._con.execute("CREATE INDEX IF NOT EXISTS Data0_mtime ON  Data0(mtime)")

    def _update_impl(self, account_id, filename, meta, mtime):
        self._con.execute(
            "UPDATE Data0 SET meta = ?, mtime = ? WHERE account_id = ? AND filename = ?",
            (meta, mtime, account_id, filename),
        )

    def _insert_impl(self, account_id, filename, meta, mtime, error=None, delay=0.0):
        time.sleep(delay)
        if error:
            raise error
        self._con.execute(
            "INSERT INTO Data0(account_id, filename, meta, mtime) VALUES (?, ?, ?, ?)",
            (account_id, filename, meta, mtime),
        )

    def _get_impl(self, account_id, filename):
        rows = self._con.execute(
            "SELECT meta, mtime FROM Data0 WHERE account_id = ? AND filename = ?", (account_id, filename)
        ).fetchall()
        if rows:
            return rows[0]

    def _get_all_impl(self):
        return self._con.execute(
            "SELECT account_id, filename, meta, mtime FROM Data0 ORDER BY account_id, filename"
        ).fetchall()

    def _get_old_impl(self, limit: int = 10):
        return self._con.execute(
            "SELECT account_id, filename, meta, mtime FROM Data0 ORDER BY mtime ASC LIMIT ?", (limit,)
        ).fetchall()

    insert = partialmethod(AbstractAioSQLiteDatabase._run_job, _insert_impl)
    update = partialmethod(AbstractAioSQLiteDatabase._run_job, _update_impl)
    get = partialmethod(AbstractAioSQLiteDatabase._run_job, _get_impl)
    get_all = partialmethod(AbstractAioSQLiteDatabase._run_job, _get_all_impl)
    get_old = partialmethod(AbstractAioSQLiteDatabase._run_job, _get_old_impl)


@pytest.mark.asyncio
@pytest.mark.parametrize("wal", [False, True])
async def test_aio_sqlite_base(tmpdir, wal):
    args = wal, asyncio.get_event_loop(), str(tmpdir.join(str(uuid.uuid4()))), 10.0
    db = _TestingAioSQLiteDatabase(*args)
    with pytest.raises(AttributeError):
        await db.get_all()
    async with _TestingAioSQLiteDatabase.create(*args) as db:
        # this go according to plan
        assert await db.get_all() == []
        r2 = (5555, "/asdf/0", b"test", 9990.5)
        assert await db.get(*r2[:2]) is None
        await db.insert(*r2)
        assert await db.get_all() == [r2]
        assert await db.get(*r2[:2]) == r2[2:]
        assert await db.get_old() == [r2]
        r0 = (2555, "/asdf/0", b"test5", 9999.5)
        await db.insert(*r0)
        assert await db.get_all() == [r0, r2]
        assert await db.get(*r0[:2]) == r0[2:]
        assert await db.get_old() == [r2, r0]
        r1 = (4000, "/tmp/go", b"asdf", 20.0)
        await db.insert(*r1)
        assert await db.get_all() == [r0, r1, r2]
        assert await db.get(*r1[:2]) == r1[2:]
        assert await db.get_old() == [r1, r2, r0]
        assert await db.get_old(1) == [r1]
        assert await db.get_old(2) == [r1, r2]
        r1 = r1[:2] + (b"gogo", 50000.7)
        await db.update(*r1)
        assert await db.get_all() == [r0, r1, r2]
        assert await db.get(*r1[:2]) == r1[2:]
        assert await db.get_old() == [r2, r0, r1]

        # test different errors
        rx = (7000, "/tmp/where", b"op", 500.0)
        with pytest.raises(_SQLiteDbgException):
            await db.insert(*rx, _SQLiteDbgException())
        t = time.perf_counter()
        f0 = asyncio.create_task(db.insert(*rx, _SQLiteDbgException(), 1.5))
        f1 = asyncio.create_task(db.insert(*rx, timeout=0.5))
        f2 = asyncio.create_task(db.insert(*rx))
        f2.cancel()
        with pytest.raises(_SQLiteDbgException):
            await f0
        assert time.perf_counter() - t > 1.5
        with pytest.raises(asyncio.TimeoutError):
            await f1
        with pytest.raises(asyncio.CancelledError):
            await f2

        assert await db.get_all() == [r0, r1, r2]

        # add job after stop, test cancel
        f3 = asyncio.create_task(db.insert(*rx, _SQLiteDbgException(), 0.5))
        await asyncio.sleep(0.15)
        db.stop(0.05)
        with pytest.raises(asyncio.CancelledError):
            await db.insert(*rx)
        with pytest.raises(_SQLiteDbgException):
            await f3
