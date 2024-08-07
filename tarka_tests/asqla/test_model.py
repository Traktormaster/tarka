import os

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from tarka.asqla.alembic import AlembicHelper, get_alembic_config, NoHeadRevision
from tarka_tests.asqla.model.schema import Base
from tarka_tests.asqla.testing import start_db, ALEMBIC_DIR

FIRST_ALEMBIC_REVISION = "a9d481fef0bd"


def reflect_schema_table_names(conn):
    inspector = inspect(conn)
    return inspector.get_table_names()


async def clear_db(db_connect_url: str):
    engine = create_async_engine(db_connect_url)
    async with engine.begin() as conn:
        table_names = await conn.run_sync(reflect_schema_table_names)
        for table_name in table_names:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
    await engine.dispose()


async def create_db(db_connect_url: str, stamp: bool = True):
    engine = create_async_engine(db_connect_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if stamp:
            await conn.run_sync(AlembicHelper(get_alembic_config(ALEMBIC_DIR)).run, "stamp", "head")
    await engine.dispose()


async def _test_migration_down_and_from(db_connect_url, bottom_revision):
    head_revision = AlembicHelper(get_alembic_config(ALEMBIC_DIR)).get_head_revision()
    await clear_db(db_connect_url)
    async with start_db(db_connect_url) as db:
        assert db.alembic_head_at_startup == ""
        alembic_helper = AlembicHelper(db.get_alembic_config())
        try:
            async with db.engine.begin() as connection:
                alembic_head = await connection.run_sync(alembic_helper.run_strip_output, "current")
                assert alembic_head == head_revision + " (head)"
                await connection.run_sync(alembic_helper.run, "downgrade", bottom_revision)
        except AssertionError:
            raise
        except Exception as e:
            assert str(e).find("Downgrading through this migration may permanently drop critical data") >= 0, str(e)
        else:
            assert False, "Downgrade must fail for critical data without force"

        os.environ["TARKA_DB_MIGRATION_FORCE_DOWNGRADE"] = "1"
        try:
            async with db.engine.begin() as connection:
                alembic_head = await connection.run_sync(alembic_helper.run_strip_output, "current")
                assert alembic_head == head_revision + " (head)"
                await connection.run_sync(alembic_helper.run, "downgrade", bottom_revision)
                alembic_head = await connection.run_sync(alembic_helper.run_strip_output, "current")
                assert alembic_head == (bottom_revision + (" (head)" if head_revision == bottom_revision else ""))
        finally:
            os.environ.pop("TARKA_DB_MIGRATION_FORCE_DOWNGRADE", "")

    engine = create_async_engine(db_connect_url)
    try:
        async with engine.begin() as conn:
            table_names = await conn.run_sync(reflect_schema_table_names)
            assert set(table_names) == {"alembic_version"}
    finally:
        await engine.dispose()

    async with start_db(db_connect_url) as db:
        assert db.alembic_head_at_startup == bottom_revision
        alembic_helper = AlembicHelper(db.get_alembic_config())
        async with db.engine.begin() as connection:
            alembic_head = await connection.run_sync(alembic_helper.run_strip_output, "current")
            assert alembic_head == head_revision + " (head)"


async def _revision_helper(db_connect_url: str, create=False, assert_false=True):
    try:
        AlembicHelper(get_alembic_config(ALEMBIC_DIR)).get_head_revision()
    except NoHeadRevision:
        assert not Base.metadata.tables  # First revision from empty DB.
    else:
        if create:
            await create_db(db_connect_url)
        else:
            async with start_db(db_connect_url):
                pass  # Creates schema by Alembic HEAD.
    assert not assert_false, f"Created DB as {db_connect_url}"


@pytest.mark.order(10)
@pytest.mark.asyncio
async def test_model_asqla(db_connect_url):
    await clear_db(db_connect_url)
    # Database schema update+auto_revision:
    #   1. Uncomment the one line of code below and run the test to generate the current Alembic HEAD
    #   2. Set the db_connect_url of the test just run in the alembic.ini file if necessary
    #   3. Change schema.py (may have already been changed, unless create=True is used with _revision_helper)
    #   4. Call 'alembic revision --autogenerate -m "description"' to create the revision
    #   5. Revert temporary changes of 1 and 2.
    # await _revision_helper(db_connect_url)
    await _test_migration_down_and_from(db_connect_url, FIRST_ALEMBIC_REVISION)
