import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
import psycopg
from psycopg.rows import dict_row
from .config import DATABASE_URL, SQLITE_PATH


def utcnow():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def local_db():
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_local():
    with local_db() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS dispositivos (
          id TEXT PRIMARY KEY, nome TEXT NOT NULL, modelo TEXT,
          localizacao TEXT, status TEXT NOT NULL DEFAULT 'offline',
          ultima_conexao TEXT, criado_em TEXT NOT NULL, sincronizado INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS analises (
          id TEXT PRIMARY KEY, dispositivo_id TEXT, data_hora TEXT NOT NULL,
          classificacao TEXT NOT NULL, cor_media REAL, regioes_anormais REAL,
          circularidade REAL, assimetria REAL, score_visual REAL,
          imagem_url TEXT, versao_algoritmo TEXT,
          criado_em TEXT NOT NULL, sincronizado INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS eventos_sistema (
          id TEXT PRIMARY KEY, dispositivo_id TEXT, data_hora TEXT NOT NULL,
          tipo TEXT NOT NULL, origem TEXT, mensagem TEXT NOT NULL,
          detalhes TEXT, sincronizado INTEGER NOT NULL DEFAULT 0
        );
        ''')


def remote_db():
    if not DATABASE_URL or 'USUARIO:SENHA@HOST' in DATABASE_URL:
        raise RuntimeError('Configure DATABASE_URL real em .env')
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=10)


def to_jsonable(row):
    if row is None:
        return None
    return json.loads(json.dumps(dict(row), default=str))
