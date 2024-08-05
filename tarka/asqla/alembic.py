import os
from io import StringIO

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Connection


def get_alembic_config(alembic_dir: str, sqlalchemy_url: str = None) -> Config:
    alembic_cfg = Config(os.path.join(alembic_dir, "alembic.ini"))
    alembic_cfg.set_main_option("script_location", alembic_dir.replace("%", "%%"))
    if sqlalchemy_url:
        alembic_cfg.set_main_option("sqlalchemy.url", str(sqlalchemy_url).replace("%", "%%"))
    alembic_cfg.attributes["skip-logging-setup"] = True  # do not mess up the server logging
    return alembic_cfg


class NoHeadRevision(Exception):
    pass


class AlembicHelper:
    def __init__(self, config: Config):
        self.config = config

    def run(self, conn: Connection, alembic_command: str, *args: str) -> str:
        """
        Call the alembic CLI.
        """
        self.config.attributes["connection"] = conn
        self.config.stdout = StringIO()
        getattr(command, alembic_command)(self.config, *args)
        return self.config.stdout.getvalue()

    def run_strip_output(self, conn: Connection, alembic_command: str, *args: str) -> str:
        return self.run(conn, alembic_command, *args).strip()

    def get_head_revision(self) -> str:
        """
        Get current single head revision.
        """
        script = ScriptDirectory.from_config(self.config)
        revs = list(script.get_revisions("head"))
        if len(revs) != 1:
            raise NoHeadRevision()
        return revs[0].revision
