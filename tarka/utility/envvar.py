"""
Handy functions to parse environment-variables to basic types.
"""

import os
from typing import Optional


def parse_bool_envvar(key: str, default: Optional[bool] = None) -> Optional[bool]:
    """
    Check if an environment variable is set with a "flag" value.

    :param key: Environment variable name to use.
    :param default: Value to return when the there is no environment variable with `key` name.
    :return: bool or `default`
    """
    if key not in os.environ:
        return default
    return os.environ[key].lower().strip() in ("1", "on", "yes", "true")


def parse_int_envvar(key: str, default: Optional[int] = None) -> Optional[int]:
    """
    Get an environment variable parsed as an integer.

    :param key: Environment variable name to use.
    :param default: Value to return when the there is no environment variable with `key` name.
    :return: int or `default`
    :raises ValueError when the environment variable's value can't be parsed as an integer.
    """
    if key not in os.environ:
        return default
    return int(os.environ[key])
