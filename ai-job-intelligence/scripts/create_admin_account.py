"""Create or promote a system administrator in the configured PostgreSQL DB.

Run from ``ai-job-intelligence`` with its virtual environment active. The
password is requested without echo and stored only as the application's bcrypt
hash. This is an explicit one-time command, not automatic startup seeding.
"""
from __future__ import annotations

import sys
from getpass import getpass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))
load_dotenv(PROJECT_DIR / ".env")

from ai_job_intelligence.models.user import User  # noqa: E402
from ai_job_intelligence.models.user_profile import UserProfile  # noqa: E402
from ai_job_intelligence.services.auth import hash_password  # noqa: E402
from ai_job_intelligence.services.database import SessionLocal  # noqa: E402
from ai_job_intelligence.services.password_policy import (  # noqa: E402
    PasswordPolicyError,
    validate_password,
)
from ai_job_intelligence.config import DATABASE_URL  # noqa: E402


def main() -> None:
    host = urlsplit(DATABASE_URL.replace("postgresql+psycopg://", "postgresql://", 1)).hostname
    if not host:
        raise SystemExit("DATABASE_URL has no database host; no changes made.")
    print(f"Target database host: {host}")
    if input("Type CREATE ADMIN to continue on this database: ") != "CREATE ADMIN":
        raise SystemExit("Cancelled; database unchanged.")

    email = input("Administrator email: ").strip().lower()
    if not email or "@" not in email:
        raise SystemExit("Enter a valid email address; database unchanged.")

    password = getpass("Administrator password (hidden): ")
    try:
        validate_password(password, email=email)
    except PasswordPolicyError as exc:
        raise SystemExit(f"{exc} Database unchanged.") from None

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(email=email, password_hash=hash_password(password))
            db.add(user)
            db.flush()
            profile = UserProfile(
                user_id=user.id,
                name="System Admin",
                role="admin",
            )
            db.add(profile)
        else:
            user.password_hash = hash_password(password)
            profile = db.get(UserProfile, user.id)
            if profile is None:
                profile = UserProfile(
                    user_id=user.id,
                    name="System Admin",
                    role="admin",
                )
                db.add(profile)
            else:
                profile.role = "admin"
                profile.token_version = (profile.token_version or 0) + 1

        db.commit()
        print(f"Administrator ready: {email}")
        print("Log in with the email and password entered above.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()