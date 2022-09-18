import logging

from tarka.logging.formatter import create_logging_formatter


def test_create_logging_formatter():
    lr = logging.makeLogRecord(
        {
            "name": "root",
            "msg": "such error %r",
            "args": ("wow",),
            "levelname": "ERROR",
            "levelno": 40,
            "pathname": "/home/nandor/PycharmProjects/tarka/tarka_tests/logging/patch.py",
            "filename": "patch.py",
            "module": "patch",
            "exc_info": None,
            "exc_text": None,
            "stack_info": None,
            "lineno": 24,
            "funcName": "main",
            "created": 1657284220.656869,
            "msecs": 656.8689346313477,
            "relativeCreated": 8629.859447479248,
            "thread": 140628902299456,
            "threadName": "MainThread",
            "processName": "MainProcess",
            "process": 12631,
        }
    )
    for kw, r in [
        ({}, "2022-07-08 14:43:40.656|E|root:main:24| such error 'wow'"),
        ({"fmt": logging.BASIC_FORMAT}, "ERROR:root:such error 'wow'"),
        ({"time_format": "%y%m%d:%H%M%S"}, "220708:144340.656|E|root:main:24| such error 'wow'"),
        ({"msec_format": "%s,%03d"}, "2022-07-08 14:43:40,656|E|root:main:24| such error 'wow'"),
        ({"concise_asctime": True}, "220708 144340.656|E|root:main:24| such error 'wow'"),
        ({"include_thread": True}, "2022-07-08 14:43:40.656|140628902299456|E|root:main:24| such error 'wow'"),
        (
            {"concise_asctime": True, "include_thread": True},
            "220708 144340.656|140628902299456|E|root:main:24| such error 'wow'",
        ),
    ]:
        assert create_logging_formatter(**kw).format(lr) == r, f"{kw}\n{r}"
