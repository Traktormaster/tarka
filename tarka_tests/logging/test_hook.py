import subprocess
import sys


def test_logging_hook():
    try:
        subprocess.check_output([sys.executable, "-m", "tarka_tests.logging.hook"], text=True)
    except subprocess.CalledProcessError as e:
        assert e.returncode == 1
        assert e.stdout.find("Unhandled exception in <Thread(Thread-1") >= 0, str(e.stdout)
        assert e.stdout.find("Exception: Sad thread") >= 0, str(e.stdout)
        assert e.stdout.find("Exception ignored in: <function _BadDel.__del__ at") >= 0, str(e.stdout)
        assert e.stdout.find("Exception: Bad del") >= 0, str(e.stdout)
        assert e.stdout.find("Unhandled exception\n") >= 0, str(e.stdout)
        assert e.stdout.find("Exception: Sad main") >= 0, str(e.stdout)
    else:
        assert False
