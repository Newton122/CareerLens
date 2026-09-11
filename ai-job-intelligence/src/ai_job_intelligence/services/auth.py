from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone

# Resolved from the environment; see config._resolve_secret_key. Never hardcode
# a signing key here -- anyone who can read the source could then mint a valid
# token for any account.
from ai_job_intelligence.config import SECRET_KEY

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


# A valid bcrypt hash of a value nobody knows, used to spend the same time
# hashing when an account does not exist as when it does.
_DUMMY_HASH = pwd_context.hash("no-such-account-placeholder")


def verify_password_constant_time(
    plain_password: str,
    hashed_password: str | None,
) -> bool:
    """Verify a password, doing the same work whether or not the account exists.

    bcrypt is deliberately slow, so returning early for an unknown email made
    the response ~130x faster than for a known one. That difference is enough
    to enumerate which addresses are registered, which is a privacy leak and a
    useful first step for an attacker.
    """
    if hashed_password is None:
        pwd_context.verify(plain_password, _DUMMY_HASH)
        return False
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "exp": expire,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )