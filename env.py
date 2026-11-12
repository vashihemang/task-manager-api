import os
import re
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.config import DATABASE_URL, Base
import db.database  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
database_url = make_url(DATABASE_URL)
if database_url.get_backend_name() != "postgresql":
    raise RuntimeError("Alembic migrations are supported only on PostgreSQL")


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    schema = os.getenv("ALEMBIC_SCHEMA")
    if schema and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", schema):
        raise ValueError("ALEMBIC_SCHEMA must be a simple PostgreSQL schema name")

    connectable = create_engine(database_url, poolclass=NullPool)
    with connectable.connect() as connection:
        if schema:
            connection.execute(text(f'SET search_path TO "{schema}"'))
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
