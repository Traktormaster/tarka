from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Union, TypeVar, Type

from tarka.logging.handler import (
    AbstractHandlerConfig,
    NamedHandlersAndHandlerConfigs,
    StreamHandlerConfig,
    RotatingFileHandlerConfig,
    FileHandlerConfig,
)

_HandlerT = TypeVar("_HandlerT", bound=logging.Handler)
_AbstractHandlerConfigT = TypeVar("_AbstractHandlerConfigT", bound=AbstractHandlerConfig)


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

    # handler configs and setup convenience

    def remove_config(self, hc: AbstractHandlerConfig) -> None:
        self.remove(hc.name)

    def add_config(self, hc: Type[_AbstractHandlerConfigT[_HandlerT]]) -> _HandlerT:
        handler = hc.create()
        self.add(hc.name, handler)
        return handler

    def setup_handlers(self, nh_or_hc_list: NamedHandlersAndHandlerConfigs) -> None:
        # NOTE: When using the handler-config classes, one could specify the same handler multiple times with
        # different attributes for example, but the manager-name shall be different in that case!
        names_set_up = set()
        for nh_or_hc in nh_or_hc_list:
            if isinstance(nh_or_hc, AbstractHandlerConfig):
                name = nh_or_hc.name
                handler = nh_or_hc.create()
            elif (
                isinstance(nh_or_hc, tuple)
                and len(nh_or_hc) == 2
                and isinstance(nh_or_hc[0], str)
                and isinstance(nh_or_hc[1], logging.Handler)
            ):
                name, handler = nh_or_hc
            else:
                raise Exception(f"Invalid handler or config for setup: {nh_or_hc}")
            if name in names_set_up:
                raise Exception(
                    f"Already set up handler with name {name!r}: {self.get(name)} "
                    "Duplicate uses of the same handler config class need to have a unique name!"
                )
            self.add(name, handler)
            names_set_up.add(name)

    # specific, but generally useful handlers

    def remove_stderr_handler(self) -> None:
        self.remove(StreamHandlerConfig.DEFAULT_NAME)

    def add_stderr_handler(self) -> logging.StreamHandler:
        return self.add_config(StreamHandlerConfig())

    def remove_rotating_file_handler(self) -> None:
        self.remove(RotatingFileHandlerConfig.DEFAULT_NAME)

    def add_rotating_file_handler(
        self, log_directory: Union[str, Path], log_file_name: str = "rotating.log", max_bytes=4096000, backup_count=8
    ) -> logging.handlers.RotatingFileHandler:
        return self.add_config(RotatingFileHandlerConfig(log_directory, log_file_name, max_bytes, backup_count))

    def remove_file_handler(self) -> None:
        self.remove(FileHandlerConfig.DEFAULT_NAME)

    def add_file_handler(self, log_file: Union[str, Path]) -> logging.FileHandler:
        return self.add_config(FileHandlerConfig(log_file))
