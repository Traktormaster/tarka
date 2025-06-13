import os
from contextlib import asynccontextmanager
from typing import AsyncContextManager, Dict, Any

from tarka.asqla.database import Database

HERE = os.path.dirname(os.path.abspath(__file__))
ALEMBIC_DIR = os.path.join(HERE, "model", "alembic")


@asynccontextmanager
async def start_db(
    db_connect_url: str, engine_kwargs: Dict[str, Any] = None, aiosqlite_serializable_begin: str = "BEGIN"
) -> AsyncContextManager[Database]:
    db = Database(ALEMBIC_DIR, db_connect_url, engine_kwargs, aiosqlite_serializable_begin=aiosqlite_serializable_begin)
    async with db.run() as db_:
        assert db is db_
        yield db_
