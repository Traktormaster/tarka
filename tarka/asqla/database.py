import asyncio

from alembic.config import Config
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection

from tarka.asqla.alembic import get_alembic_config, AlembicHelper


class Database(object):
    def __init__(self, alembic_dir: str, connect_url: str):
        self.alembic_dir = alembic_dir
        self.engine = create_async_engine(connect_url)
        self.alembic_head_at_startup = None

    def get_alembic_config(self) -> Config:
        return get_alembic_config(self.alembic_dir, str(self.engine.sync_engine.url))

    async def startup(self):
        """
        Bootstrap or migrate schema of the database to be up-to-date.
        """
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
        if self.alembic_head_at_startup != alembic_helper.get_head_revision():
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
