import subprocess
import sys


def test_logging_patch():
    t = subprocess.check_output([sys.executable, "-m", "tarka_tests.logging.patch"], text=True)
    assert (
        t
        == """WARNING: x-l1 1 - yes
WARNING: y-l0 1 - yes
ERROR: root 1 - yes
ERROR: x-l1 2 - yes
ERROR: root 2 - yes
WARNING: x-l1 3 - yes
WARNING: y-l1 3 - yes
WARNING: y-l0 3 - yes
WARNING: root 3 - yes
UNBUG: x-l1 4
UNBUG: y-l1 4 - yes
UNBUG: y-l0 4 - yes
UNBUG: root 4
DEBUG: x-l1 4 - yes
DEBUG: y-l0 4 - yes
DEBUG: y-l1 4 - yes
"""
    ), repr(t)
