import asyncio
from contextlib import AsyncExitStack

import pytest

from tarka.asqla.postgres import pg_try_advisory_lock, pg_advisory_lock
from tarka_tests.asqla.testing import start_db


@pytest.mark.order(30)
@pytest.mark.asyncio
async def test_postgres_asqla(pg_connect_url):
    async with start_db(pg_connect_url) as db:
        async with AsyncExitStack() as stack:
            cs = []
            for _ in range(3):
                cs.append(await stack.enter_async_context(db.engine.connect()))
            async with pg_try_advisory_lock(cs[0], 55, 21) as l0:
                assert l0
                async with pg_try_advisory_lock(cs[1], 55, 21) as l1:
                    assert not l1
                    async with pg_try_advisory_lock(cs[1], 103) as l1_2:
                        assert l1_2
                        async with pg_try_advisory_lock(cs[0], 103) as l0_2:
                            assert not l0_2
                    async with pg_try_advisory_lock(cs[0], 55, 21) as l0_1:
                        assert l0_1
            async with pg_try_advisory_lock(cs[1], 55, 21) as l1:
                assert l1

            values = []

            async def _lock_and_append(delay, value, *args):
                async with pg_advisory_lock(*args):
                    values.append(value)
                    await asyncio.sleep(delay)
                    values.append(value)

            ts = [asyncio.create_task(_lock_and_append(0.2, 10, cs[0], 77))]
            await asyncio.sleep(0.05)
            ts.append(asyncio.create_task(_lock_and_append(0.2, 20, cs[1], 77)))
            await asyncio.sleep(0.05)
            ts.append(asyncio.create_task(_lock_and_append(0.2, 30, cs[2], 77)))
            await asyncio.gather(*ts)
            assert values == [10, 10, 20, 20, 30, 30]
