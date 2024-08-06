import asyncio
from contextlib import asynccontextmanager
from typing import Type, Dict, Any

from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker

from tarka.asqla.alembic import get_alembic_config, AlembicHelper
from tarka.asqla.tx import (
    TransactionExecutor,
    RetryableTransactionFactory,
    SessionTransactionExecutor,
    RetryableSessionTransactionFactory,
)


class Database(object):
    engine: AsyncEngine = None
    serializable_engine: AsyncEngine = None
    session_maker: Type[AsyncSession] = None

    def __init__(
        self,
        alembic_dir: str,
        connect_url: str,
        engine_kwargs: Dict[str, Any] = None,  # like echo, connect_args, etc.
        session_maker_kwargs: Dict[str, Any] = None,  # like expire_on_commit, autoflush, etc.
        aiosqlite_serializable_begin: str = "BEGIN",  # serializable tx support workaround for aiosqlite
    ):
        self.alembic_dir = alembic_dir
        self._connect_url = connect_url
        self._engine_kwargs = engine_kwargs
        self._session_maker_kwargs = session_maker_kwargs
        self._aiosqlite_serializable_begin = aiosqlite_serializable_begin
        self.alembic_head_at_startup = ""

    def get_alembic_config(self) -> Config:
        return get_alembic_config(self.alembic_dir, str(self.engine.sync_engine.url))

    async def _init_engine(self):
        """
        If further customization is necessary for the engines, this shall be overridden.
        To switch SQLite to WAL mode for example:

            if self.engine.dialect.name == "sqlite":
                @event.listens_for(self.engine.sync_engine, "connect")
                def _setup_sqlite_connection(dbapi_con, con_record):
                    dbapi_con.execute("PRAGMA journal_mode = WAL;")
                    dbapi_con.execute("PRAGMA synchronous = NORMAL;")
        """
        self.engine = create_async_engine(self._connect_url, **(self._engine_kwargs or {}))
        self.serializable_engine = self.engine.execution_options(isolation_level="SERIALIZABLE")
        if self.engine.driver == "aiosqlite" and self._aiosqlite_serializable_begin:
            # aiosqlite (<=0.20) does not honor the isolation_level with appropriate BEGIN commands, in fact it
            # never issues begin commands, transactions always start implicitly for reads.
            # SQLite itself does not support concurrent mutating transactions in any mode. In WAL journal_mode, there
            # can be parallel and concurrent readers, but writing is always with an exclusive lock. In this sense "any"
            # transaction will actually be serializable provided that an explicit BEGIN is emitted. The actual
            # difference is the point and time that parallel connections encounter locking errors.
            # The workaround (if not disabled) is to explicitly execute a BEGIN command at transaction start.
            # The command can be set for the database (DEFERRED, IMMEDIATE or EXCLUSIVE) when relevant.
            @event.listens_for(self.serializable_engine.sync_engine, "begin")
            def do_begin(conn):
                conn.exec_driver_sql(self._aiosqlite_serializable_begin)

        self.session_maker = sessionmaker(self.engine, class_=AsyncSession, **(self._session_maker_kwargs or {}))

    async def startup(self):
        """
        Initialize engine first, then bootstrap or migrate schema of the database to be up-to-date.
        """
        await self._init_engine()
        alembic_helper = AlembicHelper(self.get_alembic_config())
        retry = 0
        while True:  # handle conflicting migration attempt by parallel workers
            try:
                async with self.engine.begin() as connection:
                    connection: AsyncConnection
                    self.alembic_head_at_startup = await connection.run_sync(alembic_helper.run_strip_output, "current")

                    await self._upgrade(alembic_helper, connection)
                    await self._start_hook(connection)
            except DatabaseError:
                if retry >= 5:
                    raise
                retry += 1
                await asyncio.sleep(0.25)
            else:
                break

    async def _upgrade(self, alembic_helper: AlembicHelper, connection: AsyncConnection):
        if not self.alembic_head_at_startup.endswith(" (head)"):
            await self._pre_upgrade_hook(connection)
            await connection.run_sync(alembic_helper.run, "upgrade", "head")
            await self._post_upgrade_hook(connection)

    async def _pre_upgrade_hook(self, connection: AsyncConnection):
        """
        Place to put custom DDL commands before alembic upgrade.
        Keep in mind that it is usually better to implement all changes as alembic revisions.
        NOTE: This is called before bootstrap (first upgrade) as well.
        """

    async def _post_upgrade_hook(self, connection: AsyncConnection):
        """
        Place to put custom DDL commands after alembic upgrade.
        Keep in mind that it is usually better to implement all changes as alembic revisions.
        """

    async def _start_hook(self, connection: AsyncConnection):
        """
        Place to put custom DDL commands that are executed each time a server starts.
        The connection is currently at the HEAD alembic revision, in the upgrade transaction.
        """

    async def shutdown(self):
        await self.engine.dispose()

    @asynccontextmanager
    async def run(self):
        """
        Convenience wrapper for startup & shutdown.
        """
        await self.startup()
        try:
            yield self
        finally:
            await self.shutdown()

    def serializable_tx(self, tx_factory: RetryableTransactionFactory) -> TransactionExecutor:
        """
        Get a transaction executor with SERIALIZABLE isolation_level and automatic retry.
        """
        return TransactionExecutor(self.serializable_engine, tx_factory)

    def session_serializable_tx(self, tx_factory: RetryableSessionTransactionFactory) -> SessionTransactionExecutor:
        """
        Get an ORM transaction executor with SERIALIZABLE isolation_level and automatic retry.
        """
        return SessionTransactionExecutor(self.session_maker, tx_factory, engine=self.serializable_engine)
