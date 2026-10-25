import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from .errors import ApplicationError
from .ports import AuthStore, PasswordCodec


def digest(value: str) -> str:
    # Digest de identificador aleatório/bucket; nunca substitui Argon2id para senha.
    return hashlib.sha256(value.encode()).hexdigest()


def public_session(row: dict, csrf: str) -> dict:
    return {'user': {key: row[key] for key in ('id', 'name', 'email')}, 'csrf_token': csrf}


@dataclass(frozen=True)
class IssuedSession:
    token: str = field(repr=False)
    data: dict = field(repr=False)


class AuthService:
    def __init__(self, store: AuthStore, passwords: PasswordCodec, session_seconds: int):
        self.store = store
        self.passwords = passwords
        self.session_seconds = session_seconds

    def limit_attempts(self, identity: str, email: str) -> None:
        buckets = (digest(f'ip:{identity}'), digest(f'email:{email}'))
        if not self.store.consume_attempts(buckets, maximum=10):
            raise ApplicationError(
                429, 'Muitas tentativas. Aguarde 15 minutos.', {'Retry-After': '900'}
            )

    def register(self, name: str, email: str, password: str, identity: str) -> dict:
        self.limit_attempts(identity, email)
        self.store.create_user(uuid4(), name, email, self.passwords.hash_password(password))
        return {'message': 'Cadastro concluído. Entre para continuar.'}

    def login(
        self, email: str, password: str, identity: str, old_token: str | None
    ) -> IssuedSession:
        self.limit_attempts(identity, email)
        user = self.store.find_user(email)
        valid = self.passwords.verify_password(user['password_hash'] if user else None, password)
        if not valid or not user:
            raise ApplicationError(401, 'E-mail ou senha inválidos.')
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.store.replace_session(
            digest(old_token) if old_token else None,
            digest(token),
            user['id'],
            csrf,
            datetime.now(UTC) + timedelta(seconds=self.session_seconds),
        )
        return IssuedSession(token, public_session(user, csrf))

    def session(self, token: str | None) -> dict:
        if not token or len(token) > 128:
            raise ApplicationError(401, 'Sessão ausente ou expirada.')
        row = self.store.find_session(digest(token))
        if not row:
            raise ApplicationError(401, 'Sessão ausente ou expirada.')
        return public_session(row, row['csrf_token'])

    def logout(self, token: str) -> None:
        self.store.revoke_session(digest(token))
