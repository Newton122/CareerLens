"""How Alembic connects to the database and finds the models.

Alembic runs this file for every command (``upgrade``, ``revision``...). It
uses the app's own engine, so the database URL comes from DATABASE_URL via
config.py -- never from alembic.ini -- and the test suite's throwaway schema
(set through the URL's search_path option) is respected automatically.

``target_metadata`` is every table the models define. ``alembic revision
--autogenerate`` compares it with the live database and writes the
difference as a new migration, which you then read and correct by hand.
"""
from __future__ import annotations

from alembic import context

import ai_job_intelligence.models  # noqa: F401  (imports every model, so every table is known)
from ai_job_intelligence.config import DATABASE_URL
from ai_job_intelligence.services.database import Base, engine

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Print the SQL instead of running it (``alembic upgrade head --sql``)."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run against the database, on a connection passed in or a fresh one."""
    connection = context.config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    with engine.connect() as connection:
        _run(connection)


def _run(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
