import sqlalchemy
from sqlalchemy import Integer, Table, Column, BigInteger, String

from tarka.asqla.types import UTCDateTime

METADATA = sqlalchemy.MetaData()


USERS_TABLE = Table(
    "users",
    METADATA,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ext_id", Integer, nullable=False, index=True, unique=True),
    # settings data
    Column("int0", BigInteger),
    Column("str0", String),
    Column("utc0", UTCDateTime),
)
