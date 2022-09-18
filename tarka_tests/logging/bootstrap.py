import logging

from tarka.logging.bootstrap import init_tarka_logging


def main():
    assert logging.getLevelName(5) == "Level 5"
    init_tarka_logging()
    assert logging.getLevelName(5) == "TRACE"
    init_tarka_logging()
    assert logging.getLevelName(5) == "TRACE"


if __name__ == "__main__":
    main()
