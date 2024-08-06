import asyncio
import random
from typing import Any, Union, Callable, Optional

import pytest
from sqlalchemy import insert, update, select, delete
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from tarka.asqla.tx import AbstractRetryableTransaction, TransactionExecutor, SessionTransactionExecutor
from tarka_tests.asqla.model.schema import Thing
from tarka_tests.asqla.testing import start_db


class ConflictTestingTransaction(AbstractRetryableTransaction):
    def __init__(self, conn_or_session: Union[AsyncConnection, AsyncSession], ext_id: int, counter_fn: Callable):
        if isinstance(conn_or_session, AsyncSession):
            self.session = conn_or_session
            self.conn = None
        elif isinstance(conn_or_session, AsyncConnection):
            self.session = None
            self.conn = conn_or_session
        else:
            raise NotImplementedError()
        self.ext_id = ext_id
        self.counter_fn = counter_fn

    async def run(self) -> Any:
        self.counter_fn()
        if self.session:
            thing = (await self.session.execute(select(Thing).where(Thing.ext_id == self.ext_id))).one()[0]
            await asyncio.sleep(0.05 + 0.05 * random.random())
            thing.value = (thing.value or 0) + 1
            await self.session.commit()
        else:
            value = (await self.conn.execute(select(Thing.value).where(Thing.ext_id == self.ext_id))).scalar_one()
            await asyncio.sleep(0.05 + 0.05 * random.random())
            await self.conn.execute(update(Thing).values(value=(value or 0) + 1).where(Thing.ext_id == self.ext_id))


@pytest.mark.order(20)
@pytest.mark.asyncio
async def test_tx_asqla(tmp_path, db_connect_url):
    async with start_db(db_connect_url) as db:
        async with db.engine.connect() as conn:
            async with conn.begin():
                await conn.execute(delete(Thing))
                await conn.execute(insert(Thing).values([dict(ext_id=105), dict(ext_id=106), dict(ext_id=108)]))

        async def get_value(ext_id) -> Optional[int]:
            async with db.engine.connect() as conn_:
                return (await conn_.execute(select(Thing.value).where(Thing.ext_id == ext_id))).scalar_one()

        c = 0

        def counter_fn():
            nonlocal c
            c += 1

        def f0(cos):
            return ConflictTestingTransaction(cos, 106, counter_fn)

        assert c == 0
        assert (await get_value(106)) is None
        await db.serializable_tx(f0).run()
        assert c == 1
        assert (await get_value(106)) == 1
        await db.session_serializable_tx(f0).run()
        assert c == 2
        assert (await get_value(106)) == 2

        c_prev = c
        parallel = 11
        await asyncio.gather(*[db.serializable_tx(f0).run() for _ in range(parallel)])
        assert (await get_value(106)) == 2 + parallel
        assert c > c_prev + parallel
        c_prev = c
        await asyncio.gather(*[db.session_serializable_tx(f0).run() for _ in range(parallel)])
        assert (await get_value(106)) == 2 + parallel * 2
        assert c > c_prev + parallel
        c_prev = c

        # Negative test, that the transactions do not add up without SERIALIZABLE isolation_level.
        await asyncio.gather(*[TransactionExecutor(db.engine, f0).run() for _ in range(parallel)])
        assert (await get_value(106)) == 2 + parallel * 2 + 1
        assert c == c_prev + parallel
        c_prev = c
        await asyncio.gather(*[SessionTransactionExecutor(db.session_maker, f0).run() for _ in range(parallel)])
        assert (await get_value(106)) == 2 + parallel * 2 + 2
        assert c == c_prev + parallel
        c_prev = c
