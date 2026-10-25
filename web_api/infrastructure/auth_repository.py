from psycopg.errors import UniqueViolation

from ..application.errors import ApplicationError
from ..database import connection


class AuthRepository:
    def __init__(self, settings):
        self.settings = settings

    def consume_attempts(self, bucket_hashes, maximum):
        with connection(self.settings) as db:
            for bucket in bucket_hashes:
                row = db.execute(
                    """INSERT INTO orangevision_web.auth_attempts
                    (bucket,attempts,expires_at) VALUES (%s,1,now()+interval '15 minutes')
                    ON CONFLICT(bucket) DO UPDATE SET
                    attempts=CASE WHEN auth_attempts.expires_at <= now() THEN 1 ELSE auth_attempts.attempts+1 END,
                    expires_at=CASE WHEN auth_attempts.expires_at <= now() THEN now()+interval '15 minutes' ELSE auth_attempts.expires_at END
                    RETURNING attempts""",
                    (bucket,),
                ).fetchone()
                if row['attempts'] > maximum:
                    # Saída normal do context manager confirma inclusive a tentativa bloqueada.
                    return False
        return True

    def create_user(self, user_id, name, email, password_hash):
        try:
            with connection(self.settings) as db:
                db.execute(
                    'INSERT INTO orangevision_web.users(id,name,email,password_hash) VALUES (%s,%s,%s,%s)',
                    (user_id, name, email, password_hash),
                )
        except UniqueViolation as exc:
            raise ApplicationError(
                409, 'Não foi possível cadastrar com os dados informados.'
            ) from exc

    def find_user(self, email):
        with connection(self.settings) as db:
            return db.execute(
                'SELECT id,name,email,password_hash FROM orangevision_web.users WHERE email=%s',
                (email,),
            ).fetchone()

    def find_session(self, token_hash):
        with connection(self.settings) as db:
            return db.execute(
                """SELECT u.id,u.name,u.email,s.csrf_token FROM orangevision_web.sessions s
                JOIN orangevision_web.users u ON u.id=s.user_id
                WHERE s.token_hash=%s AND s.expires_at>now()""",
                (token_hash,),
            ).fetchone()

    def replace_session(self, old_hash, token_hash, user_id, csrf, expires_at):
        with connection(self.settings) as db:
            if old_hash:
                db.execute('DELETE FROM orangevision_web.sessions WHERE token_hash=%s', (old_hash,))
            db.execute(
                'INSERT INTO orangevision_web.sessions (token_hash,user_id,csrf_token,expires_at) VALUES (%s,%s,%s,%s)',
                (token_hash, user_id, csrf, expires_at),
            )

    def revoke_session(self, token_hash):
        with connection(self.settings) as db:
            db.execute('DELETE FROM orangevision_web.sessions WHERE token_hash=%s', (token_hash,))
