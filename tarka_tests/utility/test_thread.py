import time

from tarka.utility.thread import AbstractThread


class _TestingAbstractThread(AbstractThread):
    __slots__ = ()

    def _thread(self, event: list[bool]) -> None:
        while True:
            time.sleep(0.15)
            if event[0]:
                break
            if not self._keep_running():
                break
        time.sleep(0.3)


def test_abstract_thread_terminate_with_stop():
    event = [False, False]

    def _cb():
        event[1] = True

    t = _TestingAbstractThread((event,))
    assert t.is_alive() is False
    assert t._keep_running() is True
    assert t.is_finished() is False
    t.start(callback=_cb)
    assert t.is_alive() is True
    assert t._keep_running() is True
    assert t.is_finished() is False

    time.sleep(0.35)
    assert t.is_alive() is True
    assert t._keep_running() is True
    assert t.is_finished() is False
    t.stop(0.0)
    assert t.is_alive() is False
    assert t._keep_running() is False
    assert t.is_finished() is False
    time.sleep(0.2)
    assert t.is_alive() is False
    assert t._keep_running() is False
    assert t.is_finished() is False
    assert event[1] is False
    time.sleep(0.3)
    assert t.is_alive() is False
    assert t._keep_running() is False
    assert t.is_finished() is True
    assert event[1] is True


def test_abstract_thread_terminate_without_stop():
    event = [False, False]

    def _cb():
        event[1] = True

    t = _TestingAbstractThread()
    assert t.is_alive() is False
    assert t._keep_running() is True
    assert t.is_finished() is False
    t.start(args=(event,), callback=_cb)
    assert t.is_alive() is True
    assert t._keep_running() is True
    assert t.is_finished() is False

    time.sleep(0.35)
    assert t.is_alive() is True
    assert t._keep_running() is True
    assert t.is_finished() is False
    event[0] = True
    assert t._keep_running() is True
    assert t.is_finished() is False
    time.sleep(0.2)
    assert t.is_alive() is True
    assert t._keep_running() is True
    assert t.is_finished() is False
    assert event[1] is False
    time.sleep(0.3)
    assert t.is_alive() is False
    assert t._keep_running() is True
    assert t.is_finished() is True
    assert event[1] is True
