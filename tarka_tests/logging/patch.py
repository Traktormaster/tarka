import logging
import sys

from tarka.logging.patch import TarkaLoggingPatcher

ROOT_LOGGER = logging.getLogger()
X_L0_LOGGER = logging.getLogger("x")
X_L1_LOGGER = logging.getLogger("x.x")
Y_L0_LOGGER = logging.getLogger("y")
Y_L1_LOGGER = logging.getLogger("y.y")


def main():
    assert not ROOT_LOGGER.handlers
    assert ROOT_LOGGER.level == logging.WARNING
    for logger in [X_L0_LOGGER, X_L1_LOGGER, Y_L0_LOGGER, Y_L1_LOGGER]:
        assert not logger.handlers
        assert logger.level == logging.NOTSET
        assert logger.getEffectiveLevel() == logging.WARNING

    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    ROOT_LOGGER.addHandler(h)

    # basic operation
    X_L1_LOGGER.warning("x-l1 1 - yes")
    Y_L0_LOGGER.warning("y-l0 1 - yes")
    ROOT_LOGGER.error("root 1 - yes")

    # check no-propagate behaviour
    Y_L0_LOGGER.propagate = False
    assert Y_L0_LOGGER.getEffectiveLevel() == logging.WARNING  # level still inherited
    X_L1_LOGGER.error("x-l1 2 - yes")
    Y_L1_LOGGER.error("y-l1 2 - last-resort")
    Y_L0_LOGGER.error("y-l0 2 - last-resort")
    ROOT_LOGGER.error("root 2 - yes")

    # check copy handlers
    TarkaLoggingPatcher.copy_logger_handlers(Y_L0_LOGGER)
    X_L1_LOGGER.warning("x-l1 3 - yes")
    Y_L1_LOGGER.warning("y-l1 3 - yes")
    Y_L0_LOGGER.warning("y-l0 3 - yes")
    ROOT_LOGGER.warning("root 3 - yes")

    # test custom level
    TarkaLoggingPatcher.patch_custom_level(logging.DEBUG - 5, "UNBUG")
    TarkaLoggingPatcher.patch_custom_level(logging.DEBUG + 5, "UNBUG")  # noop, does not overwrite name
    Y_L0_LOGGER.setLevel("UNBUG")
    X_L1_LOGGER.unbug("x-l1 4")
    Y_L1_LOGGER.unbug("y-l1 4 - yes")
    Y_L0_LOGGER.unbug("y-l0 4 - yes")
    ROOT_LOGGER.unbug("root 4")

    # test create shadow root
    assert not TarkaLoggingPatcher.HANDLER_CHANGE_HOOKS
    TarkaLoggingPatcher.make_logger_shadow_root(ROOT_LOGGER)
    TarkaLoggingPatcher.hook_logger_mirror_handlers(X_L0_LOGGER, X_L0_LOGGER)
    TarkaLoggingPatcher.hook_logger_mirror_handlers(ROOT_LOGGER)
    assert not TarkaLoggingPatcher.HANDLER_CHANGE_HOOKS
    assert not X_L0_LOGGER.handlers
    assert X_L0_LOGGER.propagate
    TarkaLoggingPatcher.make_logger_shadow_root(X_L0_LOGGER)
    TarkaLoggingPatcher.patch_handler_tracking()  # noop, only patches hooks once
    assert TarkaLoggingPatcher.HANDLER_CHANGE_HOOKS
    assert X_L0_LOGGER.handlers == ROOT_LOGGER.handlers
    assert not X_L0_LOGGER.propagate
    assert X_L0_LOGGER.getEffectiveLevel() == logging.WARNING  # level still inherited
    X_L0_LOGGER.setLevel(logging.DEBUG)
    X_L1_LOGGER.debug("x-l1 4 - yes")
    X_L0_LOGGER.debug("y-l0 4 - yes")
    Y_L1_LOGGER.debug("y-l1 4 - yes")
    ROOT_LOGGER.debug("root 4")

    # test handler hooks by shadow root
    ROOT_LOGGER.removeHandler(h)
    assert not ROOT_LOGGER.handlers
    assert X_L0_LOGGER.handlers == ROOT_LOGGER.handlers
    ROOT_LOGGER.addHandler(h)
    assert ROOT_LOGGER.handlers
    assert X_L0_LOGGER.handlers == ROOT_LOGGER.handlers


if __name__ == "__main__":
    main()
