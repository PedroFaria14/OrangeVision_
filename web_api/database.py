from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


@contextmanager
def connection(settings):
    with psycopg.connect(
        settings.database_url,
        row_factory=dict_row,
        connect_timeout=5,
    ) as db:
        # Poolers podem rejeitar `options` no startup. SET LOCAL vale somente para
        # esta transação, sem deixar configuração na conexão física compartilhada.
        db.execute('SET LOCAL statement_timeout = 10000')
        yield db
