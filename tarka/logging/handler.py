import logging
import logging.handlers
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import Union, Sequence, Tuple, TypeVar, Generic, Optional

from tarka.logging.formatter import HandlerFormatterOrHandlerFormatterConfig, HandlerFormatterConfig

_HandlerT = TypeVar("_HandlerT", bound=logging.Handler)


class AbstractHandlerConfig(Generic[_HandlerT]):
    name: str

    def __init__(self, formatter: Optional[HandlerFormatterOrHandlerFormatterConfig]):
        self.formatter = formatter or HandlerFormatterConfig()

    def create(self) -> _HandlerT:
        handler = self._create()
        if self.formatter:
            HandlerFormatterConfig.apply(handler, self.formatter)
        return handler

    def _create(self) -> _HandlerT:
        raise NotImplementedError()


class RotatingFileHandlerConfig(AbstractHandlerConfig[logging.handlers.RotatingFileHandler]):
    DEFAULT_NAME = "ROTFILE"

    def __init__(
        self,
        log_path: Union[str, Path],
        log_file_name: str = None,
        max_bytes: int = 4096000,
        backup_count: int = 8,
        ensure_directory: bool = True,
        formatter: Optional[HandlerFormatterOrHandlerFormatterConfig] = None,
        name: str = DEFAULT_NAME,
    ):
        AbstractHandlerConfig.__init__(self, formatter)
        self.name = name
        log_path = Path(log_path)
        if log_file_name is None:
            self.log_directory = log_path.parent
            self.log_file_name = log_path.name
        else:
            self.log_directory = log_path
            self.log_file_name = log_file_name
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.ensure_directory = ensure_directory

    def _create(self) -> logging.handlers.RotatingFileHandler:
        if self.ensure_directory:
            self.log_directory.mkdir(parents=True, exist_ok=True)
        return logging.handlers.RotatingFileHandler(
            str(self.log_directory / self.log_file_name),
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
        )


class FileHandlerConfig(AbstractHandlerConfig[logging.FileHandler]):
    DEFAULT_NAME = "ONEFILE"

    def __init__(
        self,
        log_path: Union[str, Path],
        log_file_name: str = None,
        ensure_directory: bool = True,
        formatter: Optional[HandlerFormatterOrHandlerFormatterConfig] = None,
        name: str = DEFAULT_NAME,
    ):
        AbstractHandlerConfig.__init__(self, formatter)
        self.name = name
        log_path = Path(log_path)
        if log_file_name is None:
            self.log_directory = log_path.parent
            self.log_file_name = log_path.name
        else:
            self.log_directory = log_path
            self.log_file_name = log_file_name
        self.ensure_directory = ensure_directory

    def _create(self) -> logging.FileHandler:
        if self.ensure_directory:
            self.log_directory.mkdir(parents=True, exist_ok=True)
        return logging.FileHandler(str(self.log_directory / self.log_file_name))


class StreamHandlerConfig(AbstractHandlerConfig[logging.StreamHandler]):
    DEFAULT_NAME = "STDERR"

    def __init__(
        self,
        stream: TextIOWrapper = None,
        formatter: Optional[HandlerFormatterOrHandlerFormatterConfig] = None,
        name: str = DEFAULT_NAME,
    ):
        AbstractHandlerConfig.__init__(self, formatter)
        self.name = name
        # NOTE: We acquire the reference to the stderr stream in the method body, so we'll see the current stream
        # if any post-import monkey-patching is being used.
        if stream is None:
            stream = sys.stderr
        self.stream = stream

    def _create(self) -> logging.StreamHandler:
        return logging.StreamHandler(self.stream)


NamedHandlersAndHandlerConfigs = Sequence[Union[Tuple[str, logging.Handler], AbstractHandlerConfig]]
