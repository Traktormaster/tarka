"""
${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from tarka.utility.envvar import parse_bool_envvar
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    if not parse_bool_envvar("TARKA_DB_MIGRATION_FORCE_DOWNGRADE"):
        raise Exception(
            "Downgrading through this migration may permanently drop critical data\n"
            "set 'TARKA_DB_MIGRATION_FORCE_DOWNGRADE' env-var to '1' to do it anyway"
        )
    ${downgrades if downgrades else "pass"}
