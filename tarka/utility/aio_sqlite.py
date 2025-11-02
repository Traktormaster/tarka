from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from typing import Callable, Optional, Any, Sequence

import wait_for2

from tarka.utility.aio_worker import (
    AbstractAioWorker,
    AbstractAioWorkerJob,
    AbstractAioWorkerJobFuture,
    AioWorkerJobFuture,
    ThreadWorkerJobFuture,
)


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


class AioSQLiteJob(AbstractAioWorkerJob):
    __slots__ = ("process_fn", "args", "post_process_fn", "begin_immediate")

    def __init__(
        self,
        future: AbstractAioWorkerJobFuture,
        process_fn: Callable[[AbstractAioSQLiteDatabase, ...], Any],
        args,
        post_process_fn: Callable[[AbstractAioSQLiteDatabase], None],
        begin_immediate: bool,
    ):
        AbstractAioWorkerJob.__init__(self, future)
        self.process_fn = process_fn
        self.args = args
        self.post_process_fn = post_process_fn
        self.begin_immediate = begin_immediate

    def execute(self, worker: AbstractAioSQLiteDatabase) -> Any:
        with worker._transact(self.begin_immediate):
            result = self.process_fn(worker, *self.args)
        if self.post_process_fn:
            self.post_process_fn(worker)
        return result


class AbstractAioSQLiteDatabase(AbstractAioWorker):
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

    __slots__ = ("_con", "_timeout")

    def __init__(self, sqlite_db_path: str, sqlite_timeout: float = 60.0):
        self._con: sqlite3.Connection = None
        self._timeout = sqlite_timeout
        AbstractAioWorker.__init__(self, (sqlite_db_path,))

    def start(
        self,
        args: Optional[Sequence[Any]] = None,
        callback: Optional[Callable[[], None]] = None,
        daemon: Optional[bool] = None,
        name_prefix: Optional[str] = None,
    ):
        if args is not None:  # pragma: no cover
            raise ValueError("SQLite worker does not support custom args at start.")
        AbstractAioWorker.start(self, None, callback, daemon, name_prefix)

    def _thread_init(self, db_path: str):
        self._con = sqlite3.connect(db_path, timeout=self._timeout, isolation_level=None)
        # initialise the db
        self._initialise()
        with self._transact(begin_immediate=True):
            self._setup()

    def _thread_poll(self):
        pass  # Not used.

    def _thread_cleanup(self):
        # close the database
        con = self._con
        self._con = None
        if con:
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
        self._request_queue.put_nowait(
            AioSQLiteJob(AioWorkerJobFuture(f), process_fn, args, post_process_fn, begin_immediate)
        )
        return await wait_for2.wait_for(f, timeout)

    def _run_call(
        self,
        process_fn: Callable,
        *args,
        post_process_fn: Optional[Callable] = None,
        begin_immediate: bool = True,
        timeout: Optional[float] = None,
    ):
        """
        This is designed to be used as

            get_xy = partialmethod(AbstractAioSQLiteDatabase._run_call, _get_xy_impl)

        which means the wrapped function is not yet bound in the expression. The self argument is automatically
        passed by the worker thread to make it work.
        This will raise AttributeError if the database has been closed.
        """
        jf = ThreadWorkerJobFuture()
        self._request_queue.put_nowait(AioSQLiteJob(jf, process_fn, args, post_process_fn, begin_immediate))
        return jf.get_result(timeout)

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

    async def _method_job(self, *args, **kwargs):
        raise RuntimeError("Use ._run_job() instead.")

    async def _method_call(self, *args, **kwargs):
        raise RuntimeError("Use ._run_call() instead.")
