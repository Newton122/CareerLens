"""Bring the database schema up to date, at start-up.

Schema changes live in ``migrations/versions/`` as numbered Alembic
migrations. ``upgrade_database()`` applies any the database doesn't have yet,
and is called from the app's lifespan before the first request.

Three kinds of database arrive here:

* **Empty** (a new deployment, or the test suite's throwaway schema):
  every migration runs, starting with baseline 0001, which creates the tables.
* **Already migrated**: only newer migrations run, if there are any.
* **Legacy** -- created before migrations existed, by the old start-up code.
  It has tables but no ``alembic_version`` table. The old start-up code is run
  one last time to add any columns it is missing, then the database is
  *stamped* as 0001 (recorded as having the baseline without running it,
  since its tables already exist) and upgraded normally from there.

A PostgreSQL advisory lock -- a named lock held only for this job -- makes a
second server process wait instead of migrating the same database at the
same moment.
"""
from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

import ai_job_intelligence.models  # noqa: F401  (registers every table)
from ai_job_intelligence.services.database import engine

logger = logging.getLogger(__name__)

BASELINE_REVISION = "0001"

# Any fixed number unique to this app; it names the advisory lock.
_MIGRATION_LOCK_KEY = 482_117_203


def _alembic_config() -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    return cfg


def upgrade_database() -> None:
    """Apply every migration the database doesn't have yet."""
    with engine.connect() as lock_conn:
        lock_conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _MIGRATION_LOCK_KEY})
        lock_conn.commit()
        try:
            _upgrade()
        finally:
            lock_conn.execute(
                text("SELECT pg_advisory_unlock(:k)"), {"k": _MIGRATION_LOCK_KEY}
            )
            lock_conn.commit()


def _upgrade() -> None:
    cfg = _alembic_config()
    with engine.connect() as conn:
        tables = set(inspect(conn).get_table_names())

    if "alembic_version" not in tables and "users" in tables:
        logger.warning(
            "Database predates migrations: catching it up and stamping it as %s",
            BASELINE_REVISION,
        )
        _bring_legacy_database_to_baseline()
        command.stamp(cfg, BASELINE_REVISION)

    command.upgrade(cfg, "head")


# --- the pre-migration start-up code (legacy databases only) -------------


def _create_missing_baseline_tables() -> None:
    """Create any baseline table the database lacks, exactly as 0001 does."""
    path = Path(__file__).parent / "migrations" / "versions" / "0001_baseline_schema.py"
    spec = importlib.util.spec_from_file_location("careerlens_migration_0001", path)
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)

    with engine.begin() as conn:
        existing = set(inspect(conn).get_table_names())
        # Operations.context makes ``op`` inside the migration module act on
        # this connection, just as it does during a normal upgrade.
        with Operations.context(MigrationContext.configure(conn)):
            for name, create in baseline.BASELINE_TABLES.items():
                if name not in existing:
                    logger.warning("Creating missing table %s", name)
                    create()


def _add_missing_columns(table: str, columns: list[tuple[str, str]]) -> None:
    """Add any of ``columns`` that ``table`` does not already have.

    Two things this has to get right on PostgreSQL:

    * The live schema is inspected and a plain ADD COLUMN is issued only for
      what is missing, so each startup reports exactly what it changed.
    * A failed statement aborts the whole transaction, so every later statement
      on that connection fails as well. Each column therefore gets its own
      transaction: a permission error on one table cannot cascade into a failed
      startup.
    """
    with engine.connect() as conn:
        inspector = inspect(conn)
        if table not in inspector.get_table_names():
            return
        existing = {c["name"] for c in inspector.get_columns(table)}

    for name, col_type in columns:
        if name in existing:
            continue
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(f'ALTER TABLE {table} ADD COLUMN "{name}" {col_type}')
                )
            logger.info("Added column %s.%s", table, name)
        except Exception as exc:
            logger.error("Could not add column %s.%s: %s", table, name, exc)


def _bring_legacy_database_to_baseline() -> None:
    """The pre-migration start-up code, kept to catch old databases up.

    Before Alembic, the server created missing tables and added missing
    columns every time it started. A database built that way may be missing
    columns added later, so it is brought fully up to date here -- once --
    and only then stamped as baseline 0001. From then on only migrations
    change the schema.

    Missing tables are created from the baseline migration's own definitions,
    never from the current models: the models describe the *latest* schema,
    and anything newer than the baseline must be left for the later
    migrations to add, or they would fail finding it already there.
    """
    _create_missing_baseline_tables()

    _add_missing_columns(
        "user_profiles",
        [
            ("description", "TEXT"),
            ("industry", "VARCHAR"),
            ("company_size", "VARCHAR"),
            ("website", "VARCHAR"),
            ("linkedin", "VARCHAR"),
            ("twitter", "VARCHAR"),
            ("image_url", "VARCHAR"),
        ],
    )
    # Cache of the parsed CandidateProfile -- see services/cv_profile.py.
    # embedding/embedding_version -- see services/vector_store.py.
    _add_missing_columns(
        "cvs",
        [
            ("profile_json", "TEXT"),
            ("profile_version", "INTEGER"),
            ("profile_parsed_at", "TIMESTAMP"),
            ("embedding", "TEXT"),
            ("embedding_version", "INTEGER"),
        ],
    )
    _add_missing_columns(
        "jobs",
        [
            ("embedding", "TEXT"),
            ("embedding_version", "INTEGER"),
        ],
    )
    # How a candidate actually attends. Added after the table shipped with
    # only a free-text location, which left video calls with nowhere to put a
    # link. Defaults are set inline so existing rows read as a video call of
    # the standard length rather than as nulls the UI has to special-case.
    _add_missing_columns(
        "interviews",
        [
            ("mode", "VARCHAR(20) DEFAULT 'video' NOT NULL"),
            ("meeting_url", "TEXT"),
            ("dial_in", "VARCHAR(64)"),
            ("contact_email", "VARCHAR(255)"),
            ("contact_phone", "VARCHAR(64)"),
            ("duration_minutes", "INTEGER DEFAULT 45 NOT NULL"),
            ("timezone", "VARCHAR(64)"),
        ],
    )

    # experience_match/education_match became nullable: null now means "the
    # posting did not state this", which is different from a score of zero.
    for column in ("experience_match", "education_match"):
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(f"ALTER TABLE analyses ALTER COLUMN {column} DROP NOT NULL")
                )
        except Exception as exc:
            # Already nullable, or the table was just built by create_all from
            # the current model; either way there is nothing to relax.
            logger.debug("Could not relax analyses.%s: %s", column, exc)

    # Note: name/role/company live on user_profiles, not users. Earlier code
    # also tried to add them to the users table; nothing reads them there, and
    # the app's DB role does not own that table, so the attempt only produced
    # errors. Dropped deliberately.
    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE user_profiles SET role = 'job_seeker' WHERE role IS NULL")
            )
    except Exception as exc:
        logger.error("Could not backfill null user_profiles.role: %s", exc)
