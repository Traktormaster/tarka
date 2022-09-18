import logging

from tarka.utility.algorithm.seq import seq_closest_index


def get_logging_levels_with_name(until_level: int = 101) -> list[int]:
    """
    It is astonishing that no public API exists to access the level-name mapping. The comments about levels
    say the NOTSET pseudo-level is the lower limit for user defined values. Since there should not be many
    more serious levels than FATAL, we iterate over all possible levels to see which has a name.
    We exclude the NOTSET from the returned collection.
    """
    levels = []
    for level in range(1, until_level):
        level_name = logging.getLevelName(level)
        if not level_name.startswith("Level "):
            levels.append(level)
    return levels


def calculate_named_logging_level(verbose: int = 0, silent: int = 0, default: int = logging.WARNING) -> int:
    """
    Calculate the most appropriate named logging level by verbosity and silence deltas relative to a default.
    """
    levels = get_logging_levels_with_name()
    default_index = seq_closest_index(levels, default)
    delta_index = silent - verbose
    return levels[min(max(0, default_index + delta_index), len(levels) - 1)]
