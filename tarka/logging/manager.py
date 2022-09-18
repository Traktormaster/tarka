from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional, Union


class LoggerHandlerManager:
    """
    The logger objects are global. The root logger especially may get handlers from different contexts and there
    is no native solution to track them. Using this a library or application can easily add/remove/update their
    handlers on any logger safely, without affecting handlers unknown to them.
    """

    _INSTANCES = {}

    @staticmethod
    def instance(logger: Optional[logging.Logger] = None) -> LoggerHandlerManager:
        """
        Automatic global singleton instance support for convenience. Any number of LoggerHandlerManager may be
        used with any logger, but commonly only one is needed for the root.
        Loggers made by libraries for their own use usually won't need this, since those loggers are only
        utilized by that codebase most of the time.
        """
        if logger is None:
            logger = logging.getLogger()
        lhm = LoggerHandlerManager._INSTANCES.get(logger)
        if lhm is None:
            LoggerHandlerManager._INSTANCES[logger] = lhm = LoggerHandlerManager(logger)
        return lhm

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self.handlers: dict[str, logging.Handler] = {}  # that we manage

    def has(self, name: str) -> bool:
        return name in self.handlers

    def get(self, name: str) -> Optional[logging.Handler]:
        return self.handlers.get(name)

    def clear(self, close: bool = True) -> None:
        """
        Remove all managed handlers from the logger.
        """
        while self.handlers:
            _, handler = self.handlers.popitem()
            self.logger.removeHandler(handler)
            if close:
                handler.close()

    def remove(self, name: str, close: bool = True) -> Optional[logging.Logger]:
        """
        Remove a managed handler from the logger by name.
        Return the removed logger or None if no logger is tracked by name.
        """
        handler = self.handlers.pop(name, None)
        if handler is not None:
            self.logger.removeHandler(handler)
            if close:
                handler.close()
        return handler

    def add(self, name: str, handler: logging.Handler, close: bool = True) -> Optional[logging.Logger]:
        """
        Add a handler, replacing the previous one with the same name if any.
        Returns the previous handler that was replaced, None otherwise.
        """
        replaced_handler = self.remove(name, close=close)
        self.logger.addHandler(handler)
        self.handlers[name] = handler
        return replaced_handler

    # specific, but generally useful handlers

    def remove_stderr_handler(self) -> None:
        self.remove("STDERR")

    def add_stderr_handler(self) -> logging.StreamHandler:
        handler = logging.StreamHandler(sys.stderr)
        self.add("STDERR", handler)
        return handler

    def remove_rotating_file_handler(self) -> None:
        self.remove("ROTFILE")

    def add_rotating_file_handler(
        self, log_directory: Union[str, Path], log_file_name: str = "rotating.log", max_bytes=4096000, backup_count=8
    ) -> logging.handlers.RotatingFileHandler:
        handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_directory, log_file_name),
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        self.add("ROTFILE", handler)
        return handler

    def remove_file_handler(self) -> None:
        self.remove("ONEFILE")

    def add_file_handler(self, log_file: Union[str, Path]) -> logging.FileHandler:
        handler = logging.FileHandler(log_file)
        self.add("ONEFILE", handler)
        return handler
