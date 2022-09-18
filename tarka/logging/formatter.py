import logging
import logging.handlers
from datetime import datetime


LOGGER_FORMAT_VERBOSE = "%(asctime)s|%(levelname).1s|%(name)s:%(funcName)s:%(lineno)d| %(message)s"
LOGGER_FORMAT_VERBOSE_THREAD = "%(asctime)s|%(thread)d|%(levelname).1s|%(name)s:%(funcName)s:%(lineno)d| %(message)s"
LOGGER_FORMAT_TIME_CONCISE = "%y%m%d %H%M%S"
LOGGER_FORMAT_MSEC_WITH_DOT = "%s.%03d"  # use decimal dot


def create_logging_formatter(
    fmt: str = None,
    time_format: str = None,
    msec_format: str = None,
    concise_asctime: bool = False,
    include_thread: bool = False,
) -> logging.Formatter:
    """
    Better default formats and support for overriding the formatting of asctime, which has no API. (datefmt lacks msec)
    """
    if fmt:
        pass
    elif include_thread:
        fmt = LOGGER_FORMAT_VERBOSE_THREAD
    else:
        fmt = LOGGER_FORMAT_VERBOSE
    formatter = logging.Formatter(fmt)
    if formatter.usesTime():  # noqa: this is not publicly documented... should be avaialable since Python 3.2
        if time_format:
            pass
        elif concise_asctime:
            time_format = LOGGER_FORMAT_TIME_CONCISE
        else:
            time_format = logging.Formatter.default_time_format
        if msec_format:
            pass
        else:
            msec_format = LOGGER_FORMAT_MSEC_WITH_DOT
        msec_format % (datetime.now().strftime(time_format), 123456)  # validate
        formatter.default_time_format = time_format
        formatter.default_msec_format = msec_format
    return formatter
