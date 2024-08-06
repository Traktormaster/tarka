from contextlib import asynccontextmanager
from typing import AsyncContextManager, Union

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, AsyncConnection


@asynccontextmanager
async def pg_try_advisory_lock(cos: Union[AsyncConnection, AsyncSession], *keys: int) -> AsyncContextManager[bool]:
    """
    Acquire advisory session lock, yields False if the lock was not acquired.
    """
    locked = (await cos.execute(select(func.pg_try_advisory_lock(*keys)))).scalar_one()
    try:
        yield locked
    finally:
        if locked:
            unlocked = (await cos.execute(select(func.pg_advisory_unlock(*keys)))).scalar_one()
            assert unlocked


@asynccontextmanager
async def pg_advisory_lock(cos: Union[AsyncConnection, AsyncSession], *keys: int) -> AsyncContextManager:
    """
    Acquire advisory session lock, block until acquired.
    """
    (await cos.execute(select(func.pg_advisory_lock(*keys)))).scalar_one()
    try:
        yield
    finally:
        (await cos.execute(select(func.pg_advisory_unlock(*keys)))).scalar_one()
