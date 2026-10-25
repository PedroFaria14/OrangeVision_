import secrets
from contextlib import contextmanager
from threading import BoundedSemaphore

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from ..application.errors import ApplicationError

hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))
hash_slots = BoundedSemaphore(2)


@contextmanager
def hash_capacity():
    if not hash_slots.acquire(blocking=False):
        raise ApplicationError(429, 'Autenticação ocupada. Tente novamente.', {'Retry-After': '5'})
    try:
        yield
    finally:
        hash_slots.release()


class PasswordSecurity:
    def hash_password(self, password: str) -> str:
        with hash_capacity():
            return hasher.hash(password)

    def verify_password(self, stored_hash: str | None, password: str) -> bool:
        with hash_capacity():
            try:
                return hasher.verify(stored_hash or DUMMY_HASH, password)
            except (VerificationError, InvalidHashError):
                return False
