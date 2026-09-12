"""Tests for the Alembic migrations and the start-up upgrade.

The test session's own schema is built purely by running the migrations
(conftest starts the app on an empty schema), so every other test already
exercises the "empty database" path. These cover the rest.
"""
from __future__ import annotations

import uuid

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text


def _head(migrate) -> str:
    return ScriptDirectory.from_config(migrate._alembic_config()).get_current_head()


def _differences(connection, metadata) -> list:
    ctx = MigrationContext.configure(connection, opts={"compare_type": True})
    return compare_metadata(ctx, metadata)


def test_models_and_migrations_describe_the_same_schema(client):
    """Guards against a model change shipped without a migration.

    If this fails after you edit a model, generate a migration with
    ``alembic revision --autogenerate -m "..."`` and review it.
    """
    from ai_job_intelligence.services.database import Base, engine

    with engine.connect() as conn:
        assert _differences(conn, Base.metadata) == []


def test_database_is_at_the_latest_migration(client):
    from ai_job_intelligence import migrate
    from ai_job_intelligence.services.database import engine

    with engine.connect() as conn:
        current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert current == _head(migrate)


def test_upgrade_is_safe_to_run_again(client):
    from ai_job_intelligence import migrate

    migrate.upgrade_database()
    migrate.upgrade_database()


@pytest.fixture
def legacy_schema(app_module, monkeypatch):
    """An engine on a fresh schema, swapped in for the app's engine."""
    import os

    from ai_job_intelligence import migrate
    from ai_job_intelligence.services import database

    schema = f"legacy_{uuid.uuid4().hex[:10]}"
    url = os.environ["DATABASE_URL"].split("?")[0]
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(f"{url}?options=-csearch_path%3D{schema}")

    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(migrate, "engine", engine)
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_a_pre_migration_database_is_caught_up_and_stamped(app_module, legacy_schema):
    """A database made by the old start-up code: the baseline tables (one of
    them missing), no alembic_version, and columns added by later releases
    missing -- then brought to the latest migration."""
    from alembic import command

    from ai_job_intelligence import migrate
    from ai_job_intelligence.services.database import Base

    # Shape it like a real old database: the baseline, minus what old
    # releases lacked, and no record of any migration.
    command.upgrade(migrate._alembic_config(), migrate.BASELINE_REVISION)
    with legacy_schema.begin() as conn:
        conn.execute(text("DROP TABLE alembic_version"))
        conn.execute(text("DROP TABLE messages"))
        conn.execute(text("ALTER TABLE cvs DROP COLUMN embedding"))
        conn.execute(text("ALTER TABLE interviews DROP COLUMN meeting_url"))
        conn.execute(text("ALTER TABLE user_profiles DROP COLUMN image_url"))
        conn.execute(text("INSERT INTO users (email, password_hash) VALUES ('old@x.com', 'h')"))

    migrate.upgrade_database()

    with legacy_schema.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == _head(migrate)
        # Missing table and columns are back, later migrations applied on top,
        # and the existing data survived.
        assert _differences(conn, Base.metadata) == []
        assert conn.execute(text("SELECT count(*) FROM users")).scalar() == 1


def test_an_empty_database_is_built_by_the_migrations(app_module, legacy_schema):
    from ai_job_intelligence import migrate
    from ai_job_intelligence.services.database import Base

    migrate.upgrade_database()

    with legacy_schema.connect() as conn:
        assert _differences(conn, Base.metadata) == []
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == _head(migrate)
