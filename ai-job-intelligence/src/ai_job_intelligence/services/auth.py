import bcrypt
from jose import jwt
from datetime import datetime, timedelta, timezone

# Resolved from the environment; see config._resolve_secret_key. Never hardcode
# a signing key here -- anyone who can read the source could then mint a valid
# token for any account.
from ai_job_intelligence.config import SECRET_KEY

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# bcrypt only ever reads the first 72 bytes of a password. passlib, which this
# module used before, cut longer passwords to 72 bytes silently; newer bcrypt
# releases raise instead. Truncating explicitly keeps every hash created under
# passlib verifying exactly as before. (The password policy allows up to 128
# characters; the extra characters simply add no strength, as they never did.)
_BCRYPT_MAX_BYTES = 72


def _secret(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """A salted bcrypt hash in the standard ``$2b$12$...`` format."""
    return bcrypt.hashpw(_secret(password), bcrypt.gensalt()).decode("ascii")


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    try:
        return bcrypt.checkpw(_secret(plain_password), hashed_password.encode("ascii"))
    except ValueError:
        # Not a bcrypt hash at all (corrupt row); treat as a wrong password.
        return False


# A valid bcrypt hash of a value nobody knows, used to spend the same time
# hashing when an account does not exist as when it does.
_DUMMY_HASH = hash_password("no-such-account-placeholder")


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
        verify_password(plain_password, _DUMMY_HASH)
        return False
    return verify_password(plain_password, hashed_password)


def create_access_token(user_id: int, token_version: int = 0) -> str:
    """A signed login token for ``user_id``, valid for 24 hours.

    ``ver`` is the account's token_version when the token was issued. Raising
    the version (on password reset) makes every older token fail the check in
    auth_dependency, which is how a reset signs the account out everywhere.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "ver": token_version,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )