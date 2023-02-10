from threading import Thread
from typing import Optional, Sequence, Any, Callable


class AbstractThread(object):
    """
    Simple thread boilerplate or wrapper with support for stopping by request and a callback at exit.
    """

    __slots__ = ("__args", "__alive", "__t")

    def __init__(self, args: Optional[Sequence[Any]] = None):
        self.__args = args
        self.__alive: bool = True
        self.__t: Optional[Thread] = None

    def is_alive(self):
        """
        Determine if the thread is running and not terminating.
        """
        return self.__t is not None and self.__alive and self.__t.is_alive()

    def is_finished(self):
        """
        Determine if the thread has started and is still running.
        """
        return self.__t is not None and not self.__t.is_alive()

    def _keep_running(self):
        """
        The thread should poll this periodically to check if it has to terminate.
        """
        return self.__alive

    def start(
        self,
        args: Optional[Sequence[Any]] = None,
        callback: Optional[Callable[[], None]] = None,
        daemon: Optional[bool] = None,
        name_prefix: Optional[str] = None,
    ) -> None:
        if self.__t is not None or not self.__alive:
            raise Exception(f"Restarting {self.__class__.__name__} is not supported")
        if args is None:
            if self.__args is None:
                args = ()
            else:
                args = self.__args
        elif self.__args:
            raise Exception("Only provide thread arguments in __init__() or start()")
        self.__t = Thread(
            target=self._thread_wrapper,
            args=(callback, args),
            daemon=daemon,
            name=f"{name_prefix}-{self.__class__.__name__}" if name_prefix else self.__class__.__name__,
        )
        del self.__args  # help gc
        self.__t.start()

    def stop(self, timeout: Optional[float] = None) -> bool:
        """
        Request the thread to stop and wait for it if desired. Returns True if the thread has stopped before returning.
        """
        self.__alive = False
        if (timeout is None or timeout > 0) and not self.is_finished():
            self.__t.join(timeout)
        return self.is_finished()

    def _thread_wrapper(self, callback: Optional[Callable[[], None]], args: Sequence[Any]) -> None:
        """
        Provides a finish-callback functionality independent of the main thread execution.
        """
        try:
            self._thread(*args)
        finally:
            if callback:
                callback()

    def _thread(self, *args: Any) -> None:
        """
        Main thread execution must be implemented here.
        The args were received either from the __init__() or the start() call.
        """
        raise NotImplementedError()
