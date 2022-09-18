import logging

from tarka.logging.level import get_logging_levels_with_name, calculate_named_logging_level
from tarka.logging.patch import TarkaLoggingPatcher


def main():
    levels = [
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL,
    ]
    assert get_logging_levels_with_name() == levels
    TarkaLoggingPatcher.patch_custom_level(logging.DEBUG - 5, "TRACE")
    levels.insert(0, logging.DEBUG - 5)
    assert get_logging_levels_with_name() == levels

    assert calculate_named_logging_level() == logging.WARNING
    assert calculate_named_logging_level(1) == logging.INFO
    assert calculate_named_logging_level(2) == logging.DEBUG
    assert calculate_named_logging_level(3) == logging.TRACE
    assert calculate_named_logging_level(4) == logging.TRACE
    assert calculate_named_logging_level(silent=1) == logging.ERROR
    assert calculate_named_logging_level(silent=2) == logging.CRITICAL
    assert calculate_named_logging_level(silent=3) == logging.CRITICAL
    assert calculate_named_logging_level(3, 1) == logging.DEBUG
    assert calculate_named_logging_level(3, 1, logging.ERROR) == logging.INFO


if __name__ == "__main__":
    main()
