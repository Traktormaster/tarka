import gc
import logging
import sys
import threading

from tarka.logging.hook import (
    setup_logging_exception_hooks,
    logging_excepthook,
    logging_unraisablehook,
    logging_threading_excepthook,
)


class _BadDel:
    def __init__(self):
        self.v = 5

    def __del__(self):
        raise Exception("Bad del")


def main():
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logging.getLogger().addHandler(h)

    sys_eh = sys.excepthook
    sys_uh = sys.unraisablehook
    thr_eh = threading.excepthook

    assert not hasattr(sys, "original_excepthook")
    assert not hasattr(sys, "original_unraisablehook")
    assert not hasattr(threading, "original_excepthook")
    assert sys.excepthook is sys_eh
    assert sys.unraisablehook is sys_uh
    assert threading.excepthook is thr_eh
    setup_logging_exception_hooks(excepthook=False, unraisablehook=False, threading_excepthook=False)
    assert not hasattr(sys, "original_excepthook")
    assert not hasattr(sys, "original_unraisablehook")
    assert not hasattr(threading, "original_excepthook")
    assert sys.excepthook is sys_eh
    assert sys.unraisablehook is sys_uh
    assert threading.excepthook is thr_eh
    setup_logging_exception_hooks(unraisablehook=False, threading_excepthook=False)
    assert sys.original_excepthook is sys_eh
    assert not hasattr(sys, "original_unraisablehook")
    assert not hasattr(threading, "original_excepthook")
    assert sys.excepthook is logging_excepthook
    assert sys.unraisablehook is sys_uh
    assert threading.excepthook is thr_eh
    setup_logging_exception_hooks(threading_excepthook=False)
    assert sys.original_excepthook is sys_eh
    assert sys.original_unraisablehook is sys_uh
    assert not hasattr(threading, "original_excepthook")
    assert sys.excepthook is logging_excepthook
    assert sys.unraisablehook is logging_unraisablehook
    assert threading.excepthook is thr_eh
    setup_logging_exception_hooks()
    assert sys.original_excepthook is sys_eh
    assert sys.original_unraisablehook is sys_uh
    assert threading.original_excepthook is thr_eh
    assert sys.excepthook is logging_excepthook
    assert sys.unraisablehook is logging_unraisablehook
    assert threading.excepthook is logging_threading_excepthook
    setup_logging_exception_hooks()
    assert sys.original_excepthook is sys_eh
    assert sys.original_unraisablehook is sys_uh
    assert threading.original_excepthook is thr_eh
    assert sys.excepthook is logging_excepthook
    assert sys.unraisablehook is logging_unraisablehook
    assert threading.excepthook is logging_threading_excepthook

    def _t():
        raise Exception("Sad thread")

    t = threading.Thread(target=_t)
    t.start()
    t.join()

    x = _BadDel()
    v = x.v
    del x
    gc.collect()
    assert v == 5

    raise Exception("Sad main")


if __name__ == "__main__":
    main()
