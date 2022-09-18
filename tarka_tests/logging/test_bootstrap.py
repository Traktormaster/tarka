import subprocess
import sys


def test_logging_bootstrap():
    subprocess.check_call([sys.executable, "-m", "tarka_tests.logging.bootstrap"])
