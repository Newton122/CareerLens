"""Password validation.

Follows NIST SP 800-63B: length and a blocklist of known-bad choices do far
more good than composition rules. Forcing a symbol and a digit mostly produces
"Password1!", which is both hard to remember and trivially guessable, so no
character-class requirements are imposed here.
"""
from __future__ import annotations

import re

MIN_LENGTH = 10
MAX_LENGTH = 128

# The passwords that actually appear at the top of breach corpora, plus the
# obvious keyboard walks. A real deployment should check a full breach list
# (e.g. the Have I Been Pwned k-anonymity range API) instead of this sample.
_COMMON_PASSWORDS = {
    "password", "password1", "password123", "passw0rd", "p@ssw0rd",
    "123456", "1234567", "12345678", "123456789", "1234567890",
    "qwerty", "qwertyui", "qwerty123", "asdfghjk", "zxcvbnm",
    "111111", "000000", "123123", "abc123", "abcd1234",
    "iloveyou", "admin", "administrator", "welcome", "welcome1",
    "letmein", "monkey", "dragon", "sunshine", "princess",
    "football", "baseball", "superman", "trustno1", "changeme",
    "secret", "secret123", "master", "shadow", "michael",
    "careerlens", "jobsearch", "resume123",
}


class PasswordPolicyError(ValueError):
    """The password is not acceptable. The message is safe to show the user."""


def _is_repetitive(password: str) -> bool:
    """True for 'aaaaaaaaaa' and similar single-character passwords."""
    return len(set(password)) <= 2


def _is_sequential(password: str) -> bool:
    """True for long runs like 'abcdefghij' or '1234567890'."""
    lowered = password.lower()
    ascending = descending = 1
    for a, b in zip(lowered, lowered[1:]):
        if ord(b) - ord(a) == 1:
            ascending += 1
            descending = 1
        elif ord(a) - ord(b) == 1:
            descending += 1
            ascending = 1
        else:
            ascending = descending = 1
        if ascending >= 8 or descending >= 8:
            return True
    return False


def validate_password(password: str, *, email: str | None = None) -> None:
    """Raise PasswordPolicyError if the password is unacceptable."""
    if len(password) < MIN_LENGTH:
        raise PasswordPolicyError(
            f"Password must be at least {MIN_LENGTH} characters. "
            "A short phrase you can remember works well."
        )

    if len(password) > MAX_LENGTH:
        raise PasswordPolicyError(
            f"Password must be at most {MAX_LENGTH} characters."
        )

    normalised = password.strip().lower()

    if normalised in _COMMON_PASSWORDS:
        raise PasswordPolicyError(
            "This password appears in lists of commonly used passwords. "
            "Please choose something less predictable."
        )

    # Also catch "password2024" style variants of a blocked base.
    stripped_digits = re.sub(r"\d+$", "", normalised)
    if stripped_digits and stripped_digits in _COMMON_PASSWORDS:
        raise PasswordPolicyError(
            "This password is a common password with digits appended. "
            "Please choose something less predictable."
        )

    if _is_repetitive(password):
        raise PasswordPolicyError(
            "Password must not be a single repeated character."
        )

    if _is_sequential(password):
        raise PasswordPolicyError(
            "Password must not be a long run of sequential characters."
        )

    if email:
        local = email.split("@")[0].strip().lower()
        if len(local) >= 4 and local in normalised:
            raise PasswordPolicyError(
                "Password must not contain your email address."
            )
