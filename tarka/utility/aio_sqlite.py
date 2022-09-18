import asyncio
import sqlite3
import time
from contextlib import contextmanager, asynccontextmanager
from functools import partial
import queue
from typing import Callable, Optional, Any, Sequence

import wait_for2

from tarka.utility.thread import AbstractThread


def _callback_result(future: asyncio.Future, result):
    if not future.done():
        future.set_result(result)


def _callback_exception(future: asyncio.Future, exc):
    if not future.done():
        future.set_exception(exc)


def _sqlite_retry(fn: Callable[[], Any], retry_timeout: Optional[float] = None, wait_time: float = 0.001):
    while True:
        try:
            return fn()
        except sqlite3.OperationalError:
            if not retry_timeout:
                raise
            elif retry_timeout < 0:
                retry_timeout = time.perf_counter() - retry_timeout
            elif time.perf_counter() > retry_timeout:
                raise
            else:  # NOTE: no wait for the first retry
                time.sleep(wait_time)


class AbstractAioSQLiteDatabase(AbstractThread):
    """
    Provide a lightweight asyncio compatible, customizable interface to an arbitrary SQLite database in a safe way.
    All SQL connection operations are restricted to be executed on the worker thread, guaranteeing serialization
    requirements. If more processes would access the database the transaction_mode selector can be used, but job
    specific transaction handling would be needed for optimal performance.

    Requests shall be implemented like this:

        def _get_all_impl(self):
            return self._con.execute("SELECT x FROM y").fetchall()

        get_all = partialmethod(AbstractAioSQLiteDatabase._run_job, _get_all_impl)

    """

    __slots__ = ("_loop", "_con", "_request_queue", "started", "closed")

    @classmethod
    @asynccontextmanager
    async def create(cls, *args, **kwargs):
        """
        Strict start-stop helper for automatic cleanup.
        """
        self = cls(*args, **kwargs)
        try:
            self.start()
            await self.wait_ready()
            yield self
        finally:
            self.stop()

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        sqlite_db_path: str,
        sqlite_timeout: float = 60.0,
    ):
        self._loop = loop
        self._con: sqlite3.Connection = None
        self._request_queue: queue.Queue = None
        AbstractThread.__init__(self, (sqlite_db_path, sqlite_timeout))
        self.started = asyncio.Event()
        self.closed = asyncio.Event()

    async def wait_ready(self):
        await asyncio.wait(
            [self._loop.create_task(self.started.wait()), self._loop.create_task(self.closed.wait())],
            return_when=asyncio.FIRST_COMPLETED,
        )
        if self.closed.is_set():
            raise Exception(f"SQLite connection could not start for {self.__class__.__name__}")
        assert self.started.is_set()

    def start(
        self,
        args: Optional[Sequence[Any]] = None,
        callback: Optional[Callable[[], None]] = None,
        daemon: Optional[bool] = False,
        name_prefix: Optional[str] = None,
    ):
        if args is not None:  # pragma: no cover
            raise ValueError("SQLite worker does not support custom args at start.")
        if callback is not None:  # pragma: no cover
            raise ValueError("SQLite worker does not support custom callback. Use the 'closed' event.")
        if daemon is not False:  # pragma: no cover
            raise ValueError("SQLite worker must not be daemon to ensure consistency at cleanup.")
        self._request_queue = queue.Queue()
        AbstractThread.start(self, None, partial(self._loop.call_soon_threadsafe, self.closed.set), False, name_prefix)

    def stop(self, timeout: Optional[float] = 0) -> bool:
        """
        The default timeout is zero, we assume the .closed event will be used to wait for cleanup in asyncio.
        """
        q = self._request_queue  # saving a reference resolves race-conditions with worker thread
        if q is not None:
            q.put_nowait(None)
        return AbstractThread.stop(self, timeout)

    def _thread(self, db_path: str, timeout: float) -> None:
        """
        SQLite connection and request executor thread.
        """
        self._con = sqlite3.connect(db_path, timeout=timeout, isolation_level=None)
        try:
            # initialise the db
            _sqlite_retry(self._initialise, retry_timeout=-timeout)
            with self._transact(begin_immediate=True, retry_timeout=-timeout):
                self._setup()
            self._loop.call_soon_threadsafe(self.started.set)
            # run job queue
            while True:
                job = self._request_queue.get()
                if job is None:
                    break
                process_fn, args, post_process_fn, aio_future, begin_immediate = job
                if aio_future.done():
                    continue
                try:
                    with self._transact(begin_immediate, retry_timeout=-timeout):
                        result = process_fn(self, *args)
                    if post_process_fn:
                        _sqlite_retry(partial(post_process_fn, self), retry_timeout=-timeout)
                    self._loop.call_soon_threadsafe(_callback_result, aio_future, result)
                except Exception as e:
                    self._loop.call_soon_threadsafe(_callback_exception, aio_future, e)
        finally:
            # prevent more jobs to be queued
            q = self._request_queue
            self._request_queue = None
            # notify dead jobs if any
            try:
                while True:
                    job = q.get_nowait()
                    if job:
                        job[3].cancel()
            except queue.Empty:
                pass
            # close the database
            con = self._con
            self._con = None
            con.close()

    @contextmanager
    def _transact(self, begin_immediate: bool, retry_timeout: Optional[float] = None):
        if begin_immediate:
            _sqlite_retry(partial(self._con.execute, "BEGIN IMMEDIATE"), retry_timeout)
        else:
            self._con.execute("BEGIN")
        try:
            yield
        except BaseException:
            self._con.execute("ROLLBACK")
            raise
        else:
            self._con.execute("COMMIT")

    async def _run_job(
        self,
        process_fn: Callable,
        *args,
        post_process_fn: Optional[Callable] = None,
        begin_immediate: bool = True,
        timeout: Optional[float] = None,
    ):
        """
        This is designed to be used as

            get_xy = partialmethod(AbstractAioSQLiteDatabase._run_job, _get_xy_impl)

        which means the wrapped function is not yet bound in the expression. The self argument is automatically
        passed by the worker thread to make it work.
        This will raise AttributeError if the database has been closed.
        """
        f = self._loop.create_future()
        self._request_queue.put_nowait((process_fn, args, post_process_fn, f, begin_immediate))
        return await wait_for2.wait_for(f, timeout)

    def _initialise(self):
        """
        The connection is ready and the database initialization like pragma definitions shall be done here.

        By default the db will use WAL journaling and NORMAL sync policy. These supply the highest throughput
        with persistence, when the application can choose to ensure durability at any point by issuing a checkpoint.
        Additionally the "wal_autocheckpoint" pragma could be tuned depending on the database use-pattern.

        NOTE: Current execution is not inside a transaction!
        """
        self._con.execute("PRAGMA journal_mode = WAL;")
        self._con.execute("PRAGMA synchronous = NORMAL;")

    def _setup(self):
        """
        The connection is ready and the database initialization like schema shall be done.
        """
        raise NotImplementedError()

    def _checkpoint(self):
        """
        Only use in WAL mode.
        When guaranteed durability is required at a point, this can be used as a post-process callback like:

            mut_xy = partialmethod(AbstractAioSQLiteDatabase._run_job, _mut_xy_impl, post_process_fn=_checkpoint)

        If there are multiple writer processes the checkpoint api call can easily return SQLITE_BUSY. The
        post-processing is wrapped in _sqlite_retry so this is naively handled.
        If the database is used by a single process in a single instance, such will not happen. It will not happen
        when other instances are exclusively readers and do not acquire write-locks either.
        """
        if self._con.execute("PRAGMA wal_checkpoint(TRUNCATE);").fetchall()[0][0] != 0:
            raise sqlite3.OperationalError("WAL checkpoint failed")
