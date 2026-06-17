import argparse
import os
import sys
import time

import pytest

from tarka.utility.subprocess.aio import call_subprocess_for_output, call_subprocess_for_stream


@pytest.mark.asyncio
async def test_subprocess_aio_output():
    r = await call_subprocess_for_output(sys.executable, os.path.abspath(__file__), "--", "5")
    assert r == {
        "out": "out line 0\nout line 1\nout line 2\nout line 3\nout line 4\n",
        "err": "err line 0\nerr line 1\nerr line 2\nerr line 3\nerr line 4\n",
        "rc": 0,
    }
    r = await call_subprocess_for_output(sys.executable, os.path.abspath(__file__), "--", "5", decode=False)
    assert r == {
        "out": b"out line 0\nout line 1\nout line 2\nout line 3\nout line 4\n",
        "err": b"err line 0\nerr line 1\nerr line 2\nerr line 3\nerr line 4\n",
        "rc": 0,
    }


@pytest.mark.asyncio
async def test_subprocess_aio_stream():
    # async with asyncio.timeout(2.5):
    async with call_subprocess_for_stream(sys.executable, os.path.abspath(__file__), "--", "5") as pq:
        for i in range(5):
            assert (await pq.get()) == ("out", f"out line {i}\n")
            assert (await pq.get()) == ("err", f"err line {i}\n")
        assert (await pq.get()) == 0
    assert pq.empty()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("lines", type=int)
    args = parser.parse_args()
    i = 0
    for _ in range(args.lines):
        time.sleep(0.1)
        sys.stdout.write(f"out line {i}\n")
        sys.stdout.flush()
        time.sleep(0.1)
        sys.stderr.write(f"err line {i}\n")
        sys.stderr.flush()
        i += 1


if __name__ == "__main__":
    main()
