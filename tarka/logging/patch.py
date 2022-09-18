"""
The builtin logging facility works with global object instances which make them difficult to customize.
Yet this module shall add additional functionality to logging while keeping it completely compatible.
"""
import logging
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class _HandlerMirrorHook:
    src: logging.Logger
    trg: logging.Logger

    def __call__(self, logger: logging.Logger, add: bool, handler: logging.Handler) -> None:
        if logger is self.src:
            if add:
                self.trg.addHandler(handler)
            else:
                self.trg.removeHandler(handler)


HandlerChangeHook = Callable[[logging.Logger, bool, logging.Handler], None]


class TarkaLoggingPatcher:
    HANDLER_TRACKING_PATCHED = False
    HANDLER_CHANGE_HOOKS: list[HandlerChangeHook] = []

    @classmethod
    def patch_handler_tracking(cls) -> None:
        """
        Add a callback hook to the Logger class for handler changes.
        """
        if cls.HANDLER_TRACKING_PATCHED:
            return

        def _logger_add_handler_override(self, handler) -> None:
            self.original_addHandler(handler)
            for hook in cls.HANDLER_CHANGE_HOOKS:
                hook(self, True, handler)

        def _logger_remove_handler_override(self, handler) -> None:
            self.original_removeHandler(handler)
            for hook in cls.HANDLER_CHANGE_HOOKS:
                hook(self, False, handler)

        logging.Logger.original_addHandler = logging.Logger.addHandler
        logging.Logger.addHandler = _logger_add_handler_override
        logging.Logger.original_removeHandler = logging.Logger.removeHandler
        logging.Logger.removeHandler = _logger_remove_handler_override
        cls.HANDLER_TRACKING_PATCHED = True

    @classmethod
    def hook_logger_mirror_handlers(cls, logger: logging.Logger, src_logger: Optional[logging.Logger] = None) -> None:
        """
        Copy the handlers to the logger from the source (root logger by default) and keep them in sync.
        This is useful when not propagating loggers need to be used, but they shall have the handlers of the root.
        """
        if src_logger is None:
            src_logger = logging.getLogger()
        if logger is src_logger:
            return
        cls.patch_handler_tracking()  # ensure hooks are patched in
        mirror_hook = _HandlerMirrorHook(src_logger, logger)
        if mirror_hook not in cls.HANDLER_CHANGE_HOOKS:
            cls.HANDLER_CHANGE_HOOKS.append(mirror_hook)
        cls.copy_logger_handlers(logger, src_logger)

    @classmethod
    def make_logger_shadow_root(cls, logger: logging.Logger) -> None:
        """
        Makes a logger (that is not root) stop propagating while mirroring the handlers from the root.
        This allows setting different levels for each library while all logging to the same handlers.
        """
        if logger is logging.getLogger():
            return
        logger.propagate = False
        cls.hook_logger_mirror_handlers(logger)

    @classmethod
    def copy_logger_handlers(cls, logger: logging.Logger, src_logger: Optional[logging.Logger] = None) -> None:
        """
        Copy the handlers to the logger from the source (root logger by default).
        """
        if src_logger is None:
            src_logger = logging.getLogger()
        for handler in src_logger.handlers:
            logger.addHandler(handler)

    @classmethod
    def patch_custom_level(cls, level: int, name: str) -> None:
        """
        Patch a custom log level to the Logger class.
        """
        assert name.isupper()
        if hasattr(logging.Logger, name.lower()):
            return  # assuming already patched

        logging.addLevelName(level, name)
        setattr(logging, name, level)

        def custom_log(self, message, *args, **kws):
            self._log(level, message, args, **kws)

        setattr(logging.Logger, name.lower(), custom_log)
