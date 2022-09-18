"""
Safeguard against importing when not testing.
"""
from tarka.utility.envvar import parse_bool_envvar

if not parse_bool_envvar("ALLOW_TESTS_IMPORT"):
    raise Exception("Testing must be explicitly enabled by setting ALLOW_TESTS_IMPORT")
