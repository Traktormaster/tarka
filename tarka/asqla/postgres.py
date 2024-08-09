import warnings
from contextlib import asynccontextmanager
from typing import AsyncContextManager, Union

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, AsyncConnection


async def _pg_advisory_unlock(cos: Union[AsyncConnection, AsyncSession], *keys: int):
    unlocked = (await cos.execute(select(func.pg_advisory_unlock(*keys)))).scalar_one()
    if not unlocked:
        warnings.warn(
            "An inner scope has released the pg_try_advisory_lock() before the lock manager context did so explicitly. "
            "If such is expected, then call the lock manager with 'unlock=False' or restructure the transaction and"
            "locking to be strictly nested."
        )


@asynccontextmanager
async def pg_try_advisory_lock(
    cos: Union[AsyncConnection, AsyncSession], *keys: int, unlock: bool = True
) -> AsyncContextManager[bool]:
    """
    Acquire advisory session lock, yields False if the lock was not acquired.
    """
    locked = (await cos.execute(select(func.pg_try_advisory_lock(*keys)))).scalar_one()
    try:
        yield locked
    finally:
        if locked and unlock:
            await _pg_advisory_unlock(cos, *keys)


@asynccontextmanager
async def pg_advisory_lock(
    cos: Union[AsyncConnection, AsyncSession], *keys: int, unlock: bool = True
) -> AsyncContextManager:
    """
    Acquire advisory session lock, block until acquired.
    """
    (await cos.execute(select(func.pg_advisory_lock(*keys)))).scalar_one()
    try:
        yield
    finally:
        if unlock:
            await _pg_advisory_unlock(cos, *keys)
