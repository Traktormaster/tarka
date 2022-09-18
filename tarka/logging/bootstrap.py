from tarka.logging.patch import TarkaLoggingPatcher


def init_tarka_logging() -> None:
    """
    Use this in a top level __init__ module, to ensure the Logger.trace is patched early for use.
    """
    TarkaLoggingPatcher.patch_custom_level(5, "TRACE")
