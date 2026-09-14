from __future__ import annotations

import logging
import os
import secrets
import stat
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
IMAGES_DIR = Path(os.getenv("IMAGES_DIR", str(BASE_DIR / "uploads" / "images")))


def _normalise_database_url(url: str) -> str:
    """Point a bare PostgreSQL URL at the installed psycopg (v3) driver.

    Hosts such as Render hand out postgres:// or postgresql:// URLs. SQLAlchemy
    maps both to psycopg2, which is not installed, so the API would crash on
    boot with ModuleNotFoundError instead of connecting.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = _normalise_database_url((os.getenv("DATABASE_URL") or "").strip())

# PostgreSQL is the only supported database, in every environment. There is
# deliberately no local fallback: a silent SQLite file hid schema and
# constraint differences that only surfaced against the real database.
if not DATABASE_URL.startswith("postgresql+"):
    raise RuntimeError(
        "DATABASE_URL must be set to a PostgreSQL URL, e.g. "
        "postgresql://user:password@localhost:5432/ai_job_intelligence. "
        "SQLite and other databases are not supported."
    )
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Browser origins allowed to call this API. Comma-separated. These were
# hardcoded to port 3000, which silently broke the app on any other port --
# the browser blocks the request and the UI shows only "Failed to fetch".
# A trailing slash is dropped: browsers send the Origin header without one, so
# "https://app.vercel.app/" would never match.
CORS_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "CORS_ORIGINS",
        # `npm run dev` serves the frontend on port 3001.
        "http://localhost:3001,http://127.0.0.1:3001",
    ).split(",")
    if origin.strip()
]

# Where the frontend lives, for links in emails ("reset your password").
# Defaults to the first allowed origin, which in production is the Vercel URL,
# so a deployment that has set CORS_ORIGINS needs nothing extra.
FRONTEND_URL = (os.getenv("FRONTEND_URL") or CORS_ORIGINS[0]).rstrip("/")

# Outgoing email (password reset, email verification). Any SMTP provider
# works: Gmail with an app password, Resend, Brevo, Mailgun... Leave SMTP_HOST
# unset to disable sending; in development the email is then written to the
# server log instead, so the links can still be used locally.
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "").strip() or SMTP_USERNAME
# "starttls" (port 587), "ssl" (port 465) or "none" (a local test server).
SMTP_SECURITY = (
    os.getenv("SMTP_SECURITY") or ("ssl" if SMTP_PORT == 465 else "starttls")
).strip().lower()

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# "development" | "production". Controls how strictly secrets are enforced.
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
IS_PRODUCTION = APP_ENV == "production"

# Values that must never be accepted as a signing key. The first was the
# hardcoded placeholder shipped in the source, so any token minted with it
# should be treated as forgeable by anyone who has read the repository.
_REJECTED_SECRETS = {
    "change-this-in-production",
    "changeme",
    "secret",
    "your-secret-key-here",
}

_SECRET_FILE = BASE_DIR / ".secret_key"
_MIN_SECRET_LENGTH = 32


def _read_local_secret() -> str | None:
    try:
        value = _SECRET_FILE.read_text(encoding="utf-8").strip()
        return value or None
    except FileNotFoundError:
        return None
    except OSError:
        logger.warning("Could not read %s", _SECRET_FILE.name)
        return None


def _write_local_secret(value: str) -> None:
    """Persist a generated development key, readable only by this user.

    Without persistence a new key would be generated on every restart, silently
    invalidating everyone's session each time the dev server reloads.
    """
    try:
        _SECRET_FILE.write_text(value, encoding="utf-8")
        _SECRET_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except OSError:
        logger.warning(
            "Could not persist a development signing key to %s; sessions will "
            "not survive a restart.",
            _SECRET_FILE.name,
        )


def _resolve_secret_key() -> str:
    """Return the JWT signing key, or refuse to start.

    Anyone holding this key can mint a valid token for any user, so it is
    treated as a hard requirement in production rather than something with a
    convenient default.
    """
    configured = (os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET_KEY") or "").strip()

    if configured:
        if configured.lower() in _REJECTED_SECRETS:
            raise RuntimeError(
                "SECRET_KEY is set to a known placeholder value. Anyone with "
                "access to this project's source could forge login tokens. "
                "Generate a real one with: python -c \"import secrets; "
                "print(secrets.token_urlsafe(48))\""
            )
        if len(configured) < _MIN_SECRET_LENGTH:
            raise RuntimeError(
                f"SECRET_KEY must be at least {_MIN_SECRET_LENGTH} characters. "
                "Generate one with: python -c \"import secrets; "
                "print(secrets.token_urlsafe(48))\""
            )
        return configured

    if IS_PRODUCTION:
        raise RuntimeError(
            "SECRET_KEY is required when APP_ENV=production. Set it in the "
            "environment. Generate one with: python -c \"import secrets; "
            "print(secrets.token_urlsafe(48))\""
        )

    existing = _read_local_secret()
    if existing and len(existing) >= _MIN_SECRET_LENGTH:
        return existing

    generated = secrets.token_urlsafe(48)
    _write_local_secret(generated)
    logger.warning(
        "No SECRET_KEY set. Generated a development key and stored it in %s "
        "(gitignored). Set SECRET_KEY explicitly before deploying.",
        _SECRET_FILE.name,
    )
    return generated


# Never log or expose this value.
SECRET_KEY = _resolve_secret_key()


# --- Stripe (subscriptions) ------------------------------------------------
#
# Four values, all from the environment, none ever in source control:
#
#   STRIPE_SECRET_KEY            sk_test_...  lets this server call Stripe's API
#   STRIPE_WEBHOOK_SECRET        whsec_...    proves a webhook really came from Stripe
#   STRIPE_PRICE_PRO_MONTHLY     price_...    the Pro monthly Price in your Stripe account
#   STRIPE_PRICE_PRO_YEARLY      price_...    the Pro yearly Price
#
# With any of them missing the app still runs; billing endpoints answer 503
# and every user is simply on the Free plan.


def _resolve_stripe_secret_key() -> str:
    """Return the Stripe API key, refusing anything that can move real money.

    This project is test-mode only. Stripe keys say which mode they belong to
    in their prefix: ``sk_test_`` / ``rk_test_`` are sandbox keys that can only
    ever create fake charges; ``sk_live_`` / ``rk_live_`` charge real cards.
    Refusing live keys at startup makes "accidentally charged someone" a
    configuration error that crashes loudly, not a surprise on a statement.
    """
    key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    if not key:
        return ""
    if key.startswith(("sk_live_", "rk_live_")):
        raise RuntimeError(
            "STRIPE_SECRET_KEY is a LIVE key. CareerLens billing runs in Stripe "
            "test mode only. Use the sk_test_... key from the Stripe dashboard "
            "(Developers > API keys, with 'Test mode' switched on)."
        )
    if not key.startswith(("sk_test_", "rk_test_")):
        raise RuntimeError(
            "STRIPE_SECRET_KEY does not look like a Stripe test key "
            "(expected it to start with sk_test_)."
        )
    return key


# Never log or expose these two values.
STRIPE_SECRET_KEY = _resolve_stripe_secret_key()
STRIPE_WEBHOOK_SECRET = (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()

# Price IDs are not secret (they appear in Checkout URLs), but they are
# configuration: they differ between your test account and anyone else's.
STRIPE_PRICE_PRO_MONTHLY = (os.getenv("STRIPE_PRICE_PRO_MONTHLY") or "").strip()
STRIPE_PRICE_PRO_YEARLY = (os.getenv("STRIPE_PRICE_PRO_YEARLY") or "").strip()

# True when checkout can actually be offered.
BILLING_ENABLED = bool(
    STRIPE_SECRET_KEY and STRIPE_PRICE_PRO_MONTHLY and STRIPE_PRICE_PRO_YEARLY
)
