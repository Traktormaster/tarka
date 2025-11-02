from __future__ import annotations
import asyncio
import queue
import threading
import time
from contextlib import asynccontextmanager
from functools import partial
from typing import Optional, Sequence, Any, Callable, TypeVar, Type, AsyncContextManager

import wait_for2

from tarka.utility.thread import AbstractThread


def _callback_result(future: asyncio.Future, result):
    if not future.done():
        future.set_result(result)


def _callback_exception(future: asyncio.Future, exc):
    if not future.done():
        future.set_exception(exc)


class AbstractAioWorkerJobFuture:
    __slots__ = ()

    def done(self) -> bool:
        raise NotImplementedError()

    def cancel(self):
        raise NotImplementedError()

    def set_result(self, result):
        raise NotImplementedError()

    def set_exception(self, exc):
        raise NotImplementedError()


class AioWorkerJobFuture(AbstractAioWorkerJobFuture):
    __slots__ = ("future",)

    def __init__(self, future: asyncio.Future):
        self.future = future

    def done(self) -> bool:
        return self.future.done()

    def cancel(self):
        return self.future.cancel()

    def set_result(self, result):
        self.future.get_loop().call_soon_threadsafe(_callback_result, self.future, result)

    def set_exception(self, exc):
        self.future.get_loop().call_soon_threadsafe(_callback_exception, self.future, exc)


class ThreadWorkerJobFuture(AbstractAioWorkerJobFuture):
    __slots__ = ("event", "result", "state")

    STATE_WAIT = 0
    STATE_RESULT = 1
    STATE_EXCEPTION = 2
    STATE_CANCEL = 3

    def __init__(self):
        self.event = threading.Event()
        self.result = None
        self.state = self.STATE_WAIT

    def done(self) -> bool:
        return bool(self.state)

    def cancel(self):
        if self.state == self.STATE_WAIT:
            self.state = self.STATE_CANCEL
            self.event.set()

    def set_result(self, result):
        self.result = result
        self.state = self.STATE_RESULT
        self.event.set()

    def set_exception(self, exc):
        self.result = exc
        self.state = self.STATE_EXCEPTION
        self.event.set()

    def get_result(self, timeout=None):
        if not self.event.wait(timeout):
            self.cancel()
            raise TimeoutError
        if self.state == self.STATE_WAIT:
            raise Exception("Job result is not set")
        elif self.state == self.STATE_CANCEL:
            raise Exception("Job result is cancelled")
        elif self.state == self.STATE_RESULT:
            return self.result
        elif not isinstance(self.result, Exception):
            raise Exception(f"Job result is not an exception: {self.result}")
        raise self.result


class AbstractAioWorkerJob:
    __slots__ = ("future",)

    execute: Callable[[AbstractAioWorker], Any]

    def __init__(self, future: AbstractAioWorkerJobFuture):
        self.future = future


class PartialMethodAioWorkerJob(AbstractAioWorkerJob):
    __slots__ = ("impl_fn", "args")

    def __init__(self, future: AbstractAioWorkerJobFuture, impl_fn: Callable[[AbstractAioWorker, ...], Any], args):
        AbstractAioWorkerJob.__init__(self, future)
        self.impl_fn = impl_fn
        self.args = args

    def execute(self, worker: AbstractAioWorker) -> Any:
        return self.impl_fn(worker, *self.args)


_ClsT = TypeVar("_ClsT")


class PollTimedQueue(queue.Queue):
    def __init__(self, poll_timeout: float, maxsize=0):
        self.poll_timeout = poll_timeout
        self.next_poll = time.perf_counter() + self.poll_timeout
        queue.Queue.__init__(self, maxsize)

    def get(self, block=True, timeout=None):
        try:
            timeout = self.next_poll - time.perf_counter()
            if timeout < 0.0:  #
                raise queue.Empty
            return queue.Queue.get(self, timeout=timeout)
        except queue.Empty:
            self.next_poll = time.perf_counter() + self.poll_timeout
            raise


class AbstractAioWorker(AbstractThread):
    """
    A lightweight asyncio compatible, customizable interface to an arbitrary thread worker.
    """

    __slots__ = ("_loop", "_poll_timeout", "_request_queue", "started", "closed")

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

    def __init__(self, args: Optional[Sequence[Any]] = None, poll_timeout: Optional[float] = None):
        if poll_timeout is not None and poll_timeout <= 0.0:  # pragma: no cover
            raise ValueError("Aio worker 'poll_timeout' must be greater than zero or None.")
        self._loop = asyncio.get_running_loop()
        self._poll_timeout = poll_timeout
        self._request_queue: queue.Queue = None
        AbstractThread.__init__(self, args)
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
            raise Exception(f"Aio worker could not start for {self.__class__.__name__}")

    def start(
        self,
        args: Optional[Sequence[Any]] = None,
        callback: Optional[Callable[[], None]] = None,
        daemon: Optional[bool] = None,
        name_prefix: Optional[str] = None,
    ):
        if callback is not None:  # pragma: no cover
            raise ValueError("Aio worker does not support custom callback. Use the 'closed' event.")
        if daemon not in (None, False):  # pragma: no cover
            raise ValueError("Aio worker must not be daemon to ensure cleanup.")
        self._request_queue = queue.Queue() if self._poll_timeout is None else PollTimedQueue(self._poll_timeout)
        AbstractThread.start(self, None, partial(self._loop.call_soon_threadsafe, self.closed.set), False, name_prefix)

    def stop(self, timeout: Optional[float] = 0) -> bool:
        """
        The default timeout is zero, we assume the .closed event will be used to wait for cleanup in asyncio.
        """
        q = self._request_queue  # local reference resolves race-conditions with worker thread
        if q is not None:
            q.put_nowait(None)
        return AbstractThread.stop(self, timeout)

    def _thread(self, *args: Any) -> None:
        """
        General worker and request executor thread.
        """
        try:
            self._thread_init(*args)
            self._loop.call_soon_threadsafe(self.started.set)
            # run job queue
            while True:
                try:
                    job = self._request_queue.get()
                except queue.Empty:
                    self._thread_poll()
                    continue
                if not isinstance(job, AbstractAioWorkerJob):
                    break
                if job.future.done():  # Could have been cancelled before we got to it.
                    continue
                try:
                    result = job.execute(self)
                    job.future.set_result(result)
                except Exception as e:
                    job.future.set_exception(e)
        finally:
            # prevent more jobs to be queued
            q = self._request_queue
            self._request_queue = None
            # notify dead jobs if any
            try:
                while True:
                    job = q.get_nowait()
                    if isinstance(job, AbstractAioWorkerJob):
                        job.future.cancel()
            except queue.Empty:
                pass
            self._thread_cleanup()

    def _thread_init(self, *args: Any):
        """
        Setup facilities and states for work. The args are passed from __init__ or start.
        """
        raise NotImplementedError()

    def _thread_poll(self):
        """
        Called periodically when poll_timeout is configured.
        """
        raise NotImplementedError()

    def _thread_cleanup(self):
        """
        Cleanup everything before thread exit.
        """
        raise NotImplementedError()

    async def _method_job(self, impl_fn: Callable, *args, timeout: Optional[float] = None) -> Any:
        """
        This is designed to be used as

            get_xy = partialmethod(AbstractAioWorker._method_job, _get_xy_impl)

        which means the wrapped function is not yet bound in the expression. The self argument is automatically
        passed by the worker thread to make it work.
        """
        f = self._loop.create_future()
        self._request_queue.put_nowait(PartialMethodAioWorkerJob(AioWorkerJobFuture(f), impl_fn, args))
        return await wait_for2.wait_for(f, timeout)

    def _method_call(self, impl_fn: Callable, *args, timeout: Optional[float] = None) -> Any:
        """
        This is designed to be used as

            get_xy = partialmethod(AbstractAioWorker._method_call, _get_xy_impl)

        which means the wrapped function is not yet bound in the expression. The self argument is automatically
        passed by the worker thread to make it work.
        """
        jf = ThreadWorkerJobFuture()
        self._request_queue.put_nowait(PartialMethodAioWorkerJob(jf, impl_fn, args))
        return jf.get_result(timeout)
