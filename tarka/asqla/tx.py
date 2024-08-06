import asyncio
import inspect
import random
import sqlite3
from typing import Any, Callable, Awaitable, Union, Type, Optional

from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, AsyncConnection


class AbstractRetryableTransaction:
    async def run(self) -> Any:
        raise NotImplementedError()


_MaybeRetryableTransaction = Union[AbstractRetryableTransaction, Awaitable[AbstractRetryableTransaction]]


class AbstractTransactionExecutor:
    def __init__(self, retry_delay: Optional[float] = None):
        self.retry_delay = retry_delay if retry_delay and retry_delay > 0 else 0

    async def run(self) -> Any:
        while True:
            try:
                return await self._run_tx()
            except OperationalError as e:
                # SQLite: This catches locking errors in both the rollback and WAL modes.
                if isinstance(e.orig, sqlite3.OperationalError) and e.orig.args == ("database is locked",):
                    pass
                else:
                    raise e
            except DBAPIError as e:
                # Postgresql: https://www.postgresql.org/docs/current/mvcc-serialization-failure-handling.html
                if e.orig and hasattr(e.orig, "sqlstate") and e.orig.sqlstate == "40001":
                    pass
                else:
                    raise e
            # TODO: implement more backend specific error handling (MariaDB, etc.)
            if self.retry_delay > 0:
                await asyncio.sleep(self.retry_delay * random.random())

    async def _run_tx(self) -> Any:
        raise NotImplementedError()

    async def _check_run_tx(self, tmp: _MaybeRetryableTransaction) -> Any:
        if inspect.isawaitable(tmp):
            tmp = await tmp
        if not isinstance(tmp, AbstractRetryableTransaction):
            raise Exception(f"not AbstractRetryableTransaction: {tmp}")
        return await tmp.run()


RetryableTransactionFactory = Callable[[AsyncConnection], _MaybeRetryableTransaction]


class TransactionExecutor(AbstractTransactionExecutor):

    def __init__(
        self, engine: AsyncEngine, tx_factory: RetryableTransactionFactory, retry_delay: Optional[float] = None
    ):
        AbstractTransactionExecutor.__init__(self, retry_delay)
        self.engine = engine
        self.tx_factory = tx_factory

    async def _run_tx(self) -> Any:
        async with self.engine.connect() as conn:
            async with conn.begin():
                return await self._check_run_tx(self.tx_factory(conn))


RetryableSessionTransactionFactory = Callable[[AsyncSession], _MaybeRetryableTransaction]


class SessionTransactionExecutor(AbstractTransactionExecutor):
    def __init__(
        self,
        session_maker: Type[AsyncSession],
        tx_factory: RetryableSessionTransactionFactory,
        engine: Optional[AsyncEngine] = None,
        retry_delay: Optional[float] = None,
    ):
        AbstractTransactionExecutor.__init__(self, retry_delay)
        self.session_maker = session_maker
        self.tx_factory = tx_factory
        self._session_maker_kwargs = {}
        if engine:
            self._session_maker_kwargs["bind"] = engine

    async def _run_tx(self) -> Any:
        async with self.session_maker(**self._session_maker_kwargs) as session:
            async with session.begin():
                return await self._check_run_tx(self.tx_factory(session))
