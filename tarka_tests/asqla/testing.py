import os
from contextlib import asynccontextmanager
from typing import AsyncContextManager

from tarka.asqla.database import Database

HERE = os.path.dirname(os.path.abspath(__file__))
ALEMBIC_DIR = os.path.join(HERE, "model", "alembic")


@asynccontextmanager
async def start_db(db_connect_url: str) -> AsyncContextManager[Database]:
    db = Database(ALEMBIC_DIR, db_connect_url)
    async with db.run() as db_:
        assert db is db_
        yield db_
