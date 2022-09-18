import logging

from tarka.logging.manager import LoggerHandlerManager


def test_logger_handler_manager(tmp_path):
    assert LoggerHandlerManager.instance().logger is logging.getLogger()
    logger = logging.getLogger("test_logger_handler_manager")
    logger.propagate = False
    lhm = LoggerHandlerManager.instance(logger)
    assert lhm.logger is logger
    assert lhm is LoggerHandlerManager.instance(logger)
    assert lhm is not LoggerHandlerManager(logger)

    assert not lhm.logger.handlers
    assert not lhm.handlers

    other = logging.StreamHandler()
    lhm.logger.addHandler(other)

    assert lhm.logger.handlers == [other]
    assert not lhm.handlers

    # custom
    assert lhm.has("Custom") is False
    assert lhm.get("Custom") is None

    custom1 = logging.StreamHandler()
    custom2 = logging.StreamHandler()

    assert lhm.add("Custom", custom1) is None
    assert lhm.has("Custom") is True
    assert lhm.get("Custom") is custom1

    assert lhm.add("Custom", custom2) is custom1
    assert lhm.has("Custom") is True
    assert lhm.get("Custom") is custom2

    assert lhm.remove("Custom") is custom2
    assert lhm.has("Custom") is False
    assert lhm.get("Custom") is None

    assert lhm.add("Custom1", custom1) is None
    assert lhm.add("Custom2", custom2) is None
    assert lhm.has("Custom") is False
    assert lhm.get("Custom") is None
    assert lhm.has("Custom1") is True
    assert lhm.get("Custom1") is custom1
    assert lhm.has("Custom2") is True
    assert lhm.get("Custom2") is custom2
    lhm.clear()
    assert lhm.has("Custom") is False
    assert lhm.get("Custom") is None
    assert lhm.has("Custom1") is False
    assert lhm.get("Custom1") is None
    assert lhm.has("Custom2") is False
    assert lhm.get("Custom2") is None

    assert lhm.logger.handlers == [other]

    # stderr
    err = lhm.add_stderr_handler()
    assert lhm.has("STDERR") is True
    assert lhm.get("STDERR") is err
    lhm.remove_stderr_handler()
    assert lhm.has("STDERR") is False
    assert lhm.get("STDERR") is None
    err2 = lhm.add_stderr_handler()
    assert lhm.has("STDERR") is True
    assert lhm.get("STDERR") is err2
    assert err is not err2

    # rotating file
    rot = lhm.add_rotating_file_handler(tmp_path)
    assert lhm.has("ROTFILE") is True
    assert lhm.get("ROTFILE") is rot
    lhm.remove_rotating_file_handler()
    assert lhm.has("ROTFILE") is False
    assert lhm.get("ROTFILE") is None
    rot2 = lhm.add_rotating_file_handler(tmp_path)
    assert lhm.has("ROTFILE") is True
    assert lhm.get("ROTFILE") is rot2
    assert rot is not rot2

    # one file
    log_path = tmp_path / "asdf.log"
    one = lhm.add_file_handler(log_path)
    assert lhm.has("ONEFILE") is True
    assert lhm.get("ONEFILE") is one
    lhm.remove_file_handler()
    assert lhm.has("ONEFILE") is False
    assert lhm.get("ONEFILE") is None
    one2 = lhm.add_file_handler(log_path)
    assert lhm.has("ONEFILE") is True
    assert lhm.get("ONEFILE") is one2
    assert one is not one2
