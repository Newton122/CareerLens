"""Bring the database schema up to date without starting the web server.

    PYTHONPATH=src python -m ai_job_intelligence.init_db

The server does the same thing automatically at start-up (see migrate.py),
so this is only needed to prepare a database ahead of time. It used to call
``Base.metadata.create_all``, which bypasses the migration history.
"""
from ai_job_intelligence.migrate import upgrade_database


def init_db() -> None:
    upgrade_database()
    print("Database schema is up to date.")


if __name__ == "__main__":
    init_db()
