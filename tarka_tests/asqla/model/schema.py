from typing import Optional

from sqlalchemy import Integer, Table, Column, BigInteger, String
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from tarka.asqla.types import UTCDateTime


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Thing(Base):
    __tablename__ = "thing"

    id: Mapped[int] = mapped_column(primary_key=True)
    ext_id: Mapped[int] = mapped_column(nullable=False, index=True, unique=True)
    value: Mapped[Optional[int]] = mapped_column(BigInteger())


USERS_TABLE = Table(
    "users",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ext_id", Integer, nullable=False, index=True, unique=True),
    # settings data
    Column("int0", BigInteger),
    Column("str0", String),
    Column("utc0", UTCDateTime),
)
