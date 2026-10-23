"""Copy local CareerLens PostgreSQL data into an empty Neon database.

Run from the ai-job-intelligence directory with its virtual environment active.
The local source URL is read from .env; the Neon URL is requested without echo.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import psycopg
from dotenv import dotenv_values


def _normalise_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _pg_environment(url: str) -> dict[str, str]:
    parsed = urlsplit(_normalise_url(url))
    options = parse_qs(parsed.query)
    environment = os.environ.copy()
    environment.update(
        {
            "PGHOST": parsed.hostname or "",
            "PGPORT": str(parsed.port or 5432),
            "PGDATABASE": unquote(parsed.path.lstrip("/").split("?", 1)[0]),
            "PGUSER": unquote(parsed.username or ""),
            "PGPASSWORD": unquote(parsed.password or ""),
            "PGSSLMODE": options.get("sslmode", ["prefer"])[0],
        }
    )
    if "channel_binding" in options:
        environment["PGCHANNELBINDING"] = options["channel_binding"][0]
    return environment


def _application_tables(cursor: psycopg.Cursor) -> set[str]:
    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
          AND table_name <> 'alembic_version'
        """
    )
    return {row[0] for row in cursor.fetchall()}


def _counts(cursor: psycopg.Cursor, tables: set[str]) -> dict[str, int]:
    counts = {}
    for table in sorted(tables):
        cursor.execute(f'SELECT count(*) FROM public."{table}"')
        counts[table] = cursor.fetchone()[0]
    return counts


def main() -> None:
    source = dotenv_values(Path(__file__).resolve().parents[1] / ".env").get(
        "DATABASE_URL"
    )
    if not source:
        raise SystemExit("DATABASE_URL is missing from ai-job-intelligence/.env")
    source = _normalise_url(source)
    source_host = urlsplit(source).hostname
    if not source_host or source_host not in {"localhost", "127.0.0.1"}:
        raise SystemExit(
            "The source DATABASE_URL must point to your local database. "
            "This script will not copy from a remote database."
        )

    target = getpass("Neon PostgreSQL URL (hidden input): ").strip()
    if not target.startswith(("postgresql://", "postgres://")):
        raise SystemExit("Expected a PostgreSQL URL.")

    source_environment = _pg_environment(source)
    target_environment = _pg_environment(target)

    try:
        source_connection = psycopg.connect(source, connect_timeout=10)
        target_connection = psycopg.connect(target, connect_timeout=10)
    except psycopg.Error as exc:
        raise SystemExit(
            f"Could not connect to source or Neon ({type(exc).__name__}). "
            "Check the local database and Neon URL."
        ) from None

    with source_connection, target_connection:
        with source_connection.cursor() as source_cursor:
            source_tables = _application_tables(source_cursor)
            if not source_tables:
                raise SystemExit("The local source database has no application tables.")
            source_cursor.execute("SELECT version_num FROM public.alembic_version")
            source_revisions = {row[0] for row in source_cursor.fetchall()}
            source_counts = _counts(source_cursor, source_tables)

        with target_connection.cursor() as target_cursor:
            target_tables = _application_tables(target_cursor)
            missing = source_tables - target_tables
            extra = target_tables - source_tables
            if missing or extra:
                raise SystemExit(
                    "Source and Neon schemas differ. "
                    f"Missing in Neon: {sorted(missing)}; "
                    f"extra in Neon: {sorted(extra)}."
                )

            target_cursor.execute("SELECT version_num FROM public.alembic_version")
            target_revisions = {row[0] for row in target_cursor.fetchall()}
            if source_revisions != target_revisions:
                raise SystemExit(
                    "Migration revisions differ. "
                    f"Local: {sorted(source_revisions)}; "
                    f"Neon: {sorted(target_revisions)}."
                )

            nonempty = {
                table: count
                for table, count in _counts(target_cursor, target_tables).items()
                if count
            }

    print("Local row counts:", source_counts)
    if nonempty:
        print("Current Neon rows to be replaced:", nonempty)
        if input("Type REPLACE TARGET to back up Neon and replace its app data: ") != "REPLACE TARGET":
            raise SystemExit("Cancelled; Neon was not changed.")
    elif input("Type IMPORT to copy these records into empty Neon: ") != "IMPORT":
        raise SystemExit("Cancelled; no data was imported.")

    if nonempty:
        backup_dir = Path.home() / ".careerlens-backups"
        backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        backup_dir.chmod(0o700)
        descriptor, backup_name = tempfile.mkstemp(
            prefix="neon-before-import-",
            suffix="-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".dump",
            dir=backup_dir,
        )
        os.close(descriptor)
        backup_path = Path(backup_name)
        backup_path.chmod(0o600)
        subprocess.run(
            [
                "pg_dump",
                "--format=custom",
                "--no-owner",
                "--no-acl",
                "--file",
                str(backup_path),
            ],
            env=target_environment,
            check=True,
        )
        print(f"Neon backup saved locally: {backup_path}")

        with psycopg.connect(target, connect_timeout=10) as target_connection:
            with target_connection.cursor() as target_cursor:
                table_list = ", ".join(
                    f'public."{table}"' for table in sorted(target_tables)
                )
                target_cursor.execute(
                    f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"
                )

    with tempfile.NamedTemporaryFile(
        prefix="careerlens-local-", suffix=".dump"
    ) as dump:
        subprocess.run(
            [
                "pg_dump",
                "--format=custom",
                "--no-owner",
                "--no-acl",
                "--exclude-table=public.alembic_version",
                "--file",
                dump.name,
            ],
            env=source_environment,
            check=True,
        )
        subprocess.run(
            [
                "pg_restore",
                "--data-only",
                "--single-transaction",
                "--exit-on-error",
                "--no-owner",
                "--no-acl",
                "--dbname",
                target_environment["PGDATABASE"],
                dump.name,
            ],
            env=target_environment,
            check=True,
        )

    with psycopg.connect(target, connect_timeout=10) as target_connection:
        with target_connection.cursor() as target_cursor:
            imported_counts = _counts(
                target_cursor, _application_tables(target_cursor)
            )
    if imported_counts != source_counts:
        raise SystemExit(
            "Import completed, but row counts differ. "
            f"Local: {source_counts}; Neon: {imported_counts}."
        )
    print("Import verified. Local and Neon row counts match.")
    print("CV and profile-image files must be transferred separately.")


if __name__ == "__main__":
    main()