import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Union


async def call_subprocess_for_output(
    program: str,
    *args: str,
    decode: bool = True,
    decode_encoding: str = "utf-8",  # NOTE: also used for input_ if it is str
    decode_errors: str = "replace",
    kill_on_abandon: bool = False,
    wait_on_abandon: bool = False,
    input_: Optional[Union[bytes, str]] = None,
    **kwargs,
) -> dict:
    """
    Conveniently run a subprocess without blocking the asyncio loop and return its output.
    """
    proc = await asyncio.create_subprocess_exec(
        program,
        *args,
        stdin=kwargs.pop("stdin", asyncio.subprocess.PIPE if input_ is not None else None),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        **kwargs,
    )
    try:
        if isinstance(input_, str):
            input_ = input_.encode(decode_encoding)
        stdout, stderr = await proc.communicate(input_)
    finally:
        if proc.returncode is None:
            if kill_on_abandon:
                proc.kill()
            else:
                proc.terminate()
            if wait_on_abandon:
                await proc.wait()
    return {
        "out": stdout.decode(decode_encoding, decode_errors) if decode else stdout,
        "err": stderr.decode(decode_encoding, decode_errors) if decode else stderr,
        "rc": proc.returncode,
    }


async def _read_async_stream(proc, name, queue, decode, decode_encoding, decode_errors):
    async for line in getattr(proc, f"std{name}"):
        queue.put_nowait((name, line.decode(decode_encoding, decode_errors) if decode else line))


async def _read_finish_monitor(proc, out_t, err_t, queue):
    rc = await proc.wait()
    await asyncio.gather(out_t, err_t, return_exceptions=True)
    queue.put_nowait(rc)


@asynccontextmanager
async def call_subprocess_for_stream(
    program: str,
    *args: str,
    decode: bool = True,
    decode_encoding: str = "utf-8",
    decode_errors: str = "replace",
    kill_on_abandon: bool = False,
    **kwargs,
) -> AsyncGenerator[asyncio.Queue, None]:
    """
    Conveniently run a subprocess without blocking the asyncio loop and receive its output line-by-line using a queue.
    """
    proc = await asyncio.create_subprocess_exec(
        program, *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, **kwargs
    )
    q = asyncio.Queue()
    out_t = asyncio.create_task(_read_async_stream(proc, "out", q, decode, decode_encoding, decode_errors))
    err_t = asyncio.create_task(_read_async_stream(proc, "err", q, decode, decode_encoding, decode_errors))
    fin_t = asyncio.create_task(_read_finish_monitor(proc, out_t, err_t, q))
    try:
        yield q
    finally:
        if proc.returncode is None:
            if kill_on_abandon:
                proc.kill()
            else:
                proc.terminate()
            await asyncio.shield(fin_t)
