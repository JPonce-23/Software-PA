"""Shared bounds for passwords passed to bcrypt."""

MAX_BCRYPT_PASSWORD_BYTES = 72


def is_within_bcrypt_limit(password: str) -> bool:
    return len(password.encode("utf-8")) <= MAX_BCRYPT_PASSWORD_BYTES
