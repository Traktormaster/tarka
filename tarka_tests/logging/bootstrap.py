import logging

import pytest

from tarka.logging.bootstrap import init_tarka_logging, setup_basic_logging
from tarka.logging.handler import StreamHandlerConfig
from tarka.logging.level import NamedLoggingLevelConfig


def main():
    assert logging.getLevelName(5) == "Level 5"
    init_tarka_logging()
    assert logging.getLevelName(5) == "TRACE"
    init_tarka_logging()
    assert logging.getLevelName(5) == "TRACE"

    with pytest.raises(Exception, match="Already set up handler with name"):
        setup_basic_logging([StreamHandlerConfig(), StreamHandlerConfig()])
    assert [h.__class__ for h in logging.getLogger().handlers] == [logging.StreamHandler]

    setup_basic_logging(
        [StreamHandlerConfig(), StreamHandlerConfig(name="DOUBLE"), ("TRIPLE", logging.StreamHandler())],
        logger_levels={"tarka_testx": NamedLoggingLevelConfig(silent=1)},
        root_logger_level=logging.INFO,
    )
    assert [h.__class__ for h in logging.getLogger().handlers] == [logging.StreamHandler] * 3
    assert logging.getLogger().level == logging.INFO
    assert logging.getLogger("tarka_testx").level == logging.ERROR


if __name__ == "__main__":
    main()
