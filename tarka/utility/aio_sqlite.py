import asyncio
import sqlite3
import time
from contextlib import contextmanager, asynccontextmanager
from functools import partial
import queue
from typing import Callable, Optional, Any, Sequence, TypeVar, Type, AsyncContextManager

import wait_for2

from tarka.utility.thread import AbstractThread


def _callback_result(future: asyncio.Future, result):
    if not future.done():
        future.set_result(result)


def _callback_exception(future: asyncio.Future, exc):
    if not future.done():
        future.set_exception(exc)


def sqlite_retry(
    fn: Callable[[], Any],
    retry_timeout: Optional[float] = None,
    wait_time: float = 0.001,
    max_wait_time: float = 0.15,
    wait_multiplier: float = 1.5,
) -> Any:
    """
    Simple retry logic for handling SQLite operational errors when necessary. Keep in mind that using this can and
    should be avoided usually, because the builtin busy_timeout handler is set up by default. There are a few
    exceptions that do not utilize the busy_handler even if it is set, like the wal_checkpoint pragma.

    The wait time can be absolute (to the process by time.perf_counter()) to retry until, or a duration to retry for.
    The duration can be expressed by negative values, which will be translated into absolute time when the first error
    is raised.
    """
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
        time.sleep(wait_time)
        # adjust wait time to backoff next time if error persists
        if wait_time < max_wait_time:
            wait_time *= wait_multiplier


_ClsT = TypeVar("_ClsT")


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

    __slots__ = ("_loop", "_con", "_request_queue", "_timeout", "started", "closed")

    @classmethod
    @asynccontextmanager
    async def create(cls: Type[_ClsT], *args, **kwargs) -> AsyncContextManager[_ClsT]:
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

    def __init__(self, sqlite_db_path: str, sqlite_timeout: float = 60.0):
        self._loop = asyncio.get_running_loop()
        self._con: sqlite3.Connection = None
        self._request_queue: queue.Queue = None
        self._timeout = sqlite_timeout
        AbstractThread.__init__(self, (sqlite_db_path,))
        self.started = asyncio.Event()
        self.closed = asyncio.Event()

    async def wait_ready(self):
        if self.is_alive():  # only wait for start/stop if the worker thread has been started
            started_task = self._loop.create_task(self.started.wait())
            closed_task = self._loop.create_task(self.closed.wait())
            _, pending = await asyncio.wait([started_task, closed_task], return_when=asyncio.FIRST_COMPLETED)
            if pending:  # cleanup tasks to avoid them being logged as abandoned
                for t in pending:
                    t.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
        if self.closed.is_set() or not self.started.is_set():
            raise Exception(f"SQLite connection could not start for {self.__class__.__name__}")

    def start(
        self,
        args: Optional[Sequence[Any]] = None,
        callback: Optional[Callable[[], None]] = None,
        daemon: Optional[bool] = None,
        name_prefix: Optional[str] = None,
    ):
        if args is not None:  # pragma: no cover
            raise ValueError("SQLite worker does not support custom args at start.")
        if callback is not None:  # pragma: no cover
            raise ValueError("SQLite worker does not support custom callback. Use the 'closed' event.")
        if daemon not in (None, False):  # pragma: no cover
            raise ValueError("SQLite worker must not be daemon to ensure cleanup.")
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

    def _thread(self, db_path: str) -> None:
        """
        SQLite connection and request executor thread.
        """
        self._con = sqlite3.connect(db_path, timeout=self._timeout, isolation_level=None)
        try:
            # initialise the db
            self._initialise()
            with self._transact(begin_immediate=True):
                self._setup()
            self._loop.call_soon_threadsafe(self.started.set)
            # run job queue
            while True:
                job = self._request_queue.get()
                if job is None:
                    break
                process_fn, args, post_process_fn, aio_future, begin_immediate = job
                if aio_future.done():  # Could have been cancelled before we got to it.
                    continue
                try:
                    with self._transact(begin_immediate):
                        result = process_fn(self, *args)
                    if post_process_fn:
                        post_process_fn(self)
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
    def _transact(self, begin_immediate: bool):
        if begin_immediate:
            self._con.execute("BEGIN IMMEDIATE")
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

        The "busy_timeout" pragma does not need to be set here, as the python binding of SQLite3 does that in the
        connection, for which it uses the "timeout" argument.

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
        Use in WAL mode with NORMAL synchronous operation to ensure writes are synced to storage!
        When guaranteed durability is required at a point, this can be used as a post-process callback like:

            mut_xy = partialmethod(AbstractAioSQLiteDatabase._run_job, _mut_xy_impl, post_process_fn=_checkpoint)

        If there are multiple writer processes the checkpoint api call can easily return SQLITE_BUSY.
        If the database is used by a single process in a single instance, such will not happen.
        """
        if self._con.execute("PRAGMA wal_checkpoint(TRUNCATE);").fetchall()[0][0] != 0:
            raise sqlite3.OperationalError("WAL checkpoint failed: SQLITE_BUSY")

    def _checkpoint_retrying(self):
        """
        To be used similarly to ._checkpoint(), but this will implicitly retry similar to normal operations as
        configured initial timeout value.
        Use if multiple connections are expected to operate on the DB and one will require explicit checkpoints
        at specific places this may work well enough.
        Keep in mind though, that if more durability is required, the synchronous pragma could be tuned instead.
        """
        sqlite_retry(self._checkpoint, retry_timeout=-self._timeout)
