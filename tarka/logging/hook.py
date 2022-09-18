import logging
import sys
import threading


def logging_excepthook(type_, value, traceback):
    logging.getLogger().critical("Unhandled exception", exc_info=(type_, value, traceback))


def logging_unraisablehook(unraisable):
    logging.getLogger().critical(
        "%s: %r",
        "Exception ignored in" if unraisable.err_msg is None else unraisable.err_msg,
        unraisable.object,
        exc_info=(unraisable.exc_type, unraisable.exc_value, unraisable.exc_traceback),
    )


def logging_threading_excepthook(args):
    if args.exc_type is not SystemExit:
        logging.getLogger().critical(
            "Unhandled exception in %r", args.thread, exc_info=(args.exc_type, args.exc_value, args.exc_traceback)
        )


def setup_logging_exception_hooks(
    excepthook: bool = True, unraisablehook: bool = True, threading_excepthook: bool = True
) -> None:
    if excepthook and not hasattr(sys, "original_excepthook"):
        sys.original_excepthook = sys.excepthook
        sys.excepthook = logging_excepthook
    if unraisablehook and not hasattr(sys, "original_unraisablehook"):
        sys.original_unraisablehook = sys.unraisablehook
        sys.unraisablehook = logging_unraisablehook
    if threading_excepthook and not hasattr(threading, "original_excepthook"):
        threading.original_excepthook = threading.excepthook
        threading.excepthook = logging_threading_excepthook
