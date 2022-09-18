import subprocess
import sys


def test_logging_level_utility():
    subprocess.check_call([sys.executable, "-m", "tarka_tests.logging.level"])
