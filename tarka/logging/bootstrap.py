import logging
from typing import Dict

from tarka.logging.handler import NamedHandlersAndHandlerConfigs, StreamHandlerConfig
from tarka.logging.hook import setup_logging_exception_hooks
from tarka.logging.level import LoggingLevelOrNamedLoggingLevelConfig, NamedLoggingLevelConfig
from tarka.logging.manager import LoggerHandlerManager
from tarka.logging.patch import TarkaLoggingPatcher


def init_tarka_logging() -> None:
    """
    Use this in a top level __init__ module, to ensure the Logger.trace is patched early for use.
    """
    TarkaLoggingPatcher.patch_custom_level(5, "TRACE")


def setup_basic_logging(
    root_handlers: NamedHandlersAndHandlerConfigs = None,
    logger_levels: Dict[str, LoggingLevelOrNamedLoggingLevelConfig] = None,
    setup_exc_hooks: bool = True,
    root_logger_level: LoggingLevelOrNamedLoggingLevelConfig = logging.WARNING,
) -> None:
    """
    Convenience function to setup loggers and handlers easily.
        - Setup handlers for the root logger. (because error logging shall be setup globally)
        - Setup levels for the specified loggers.

    A typical usage example:
        parser = argparse.ArgumentParser()
        parser.add_argument("--verbose", "-v", action="count", default=0)
        parser.add_argument("--silent", "-s", action="count", default=0)
        parser.add_argument("--log_file", help="path to write log to")
        parser.add_argument("--log_backups", type=int, default=16, help="how many log files to keep when rotating")
        args = parser.parse_args()
        setup_basic_logging(
            root_handlers=[RotatingFileHandlerConfig(args.log_file, backup_count=args.log_backups)],
            logger_levels={__name__: NamedLoggingLevelConfig(args.verbose, args.silent, default=logging.INFO)},
        )

    This should be used as early as possible in the application's lifespan.
    """
    if not root_handlers:  # Just select stderr for default.
        root_handlers = [StreamHandlerConfig()]

    root_lhm = LoggerHandlerManager.instance()
    root_lhm.setup_handlers(root_handlers)
    NamedLoggingLevelConfig.apply(root_lhm.logger, root_logger_level)

    for logger_name, level in (logger_levels or {}).items():
        NamedLoggingLevelConfig.apply(logging.getLogger(logger_name), level)

    if setup_exc_hooks:
        setup_logging_exception_hooks()
