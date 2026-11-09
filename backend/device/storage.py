import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import uuid4


def utcnow():
    return datetime.now(UTC).isoformat()


class Store:
    def __init__(self, path):
        self.path = path

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA synchronous=FULL')
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.path.exists()
        with self.db() as db:
            if db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='analises'"
            ).fetchone():
                raise RuntimeError(
                    'Use banco separado; o SQLite legado não será modificado automaticamente.'
                )
            if new and os.name != 'nt':
                os.chmod(self.path, 0o600)
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('PRAGMA synchronous=FULL')
            db.executescript("""CREATE TABLE IF NOT EXISTS grants (
                id TEXT PRIMARY KEY, data TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 0);
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_grant ON grants(active) WHERE active=1;
                CREATE TABLE IF NOT EXISTS pairing_attempt (singleton INTEGER PRIMARY KEY CHECK(singleton=1),data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS capture_jobs (
                  request_id TEXT PRIMARY KEY,analysis_id TEXT UNIQUE NOT NULL,session_id TEXT NOT NULL REFERENCES grants(id),
                  state TEXT NOT NULL,created_at TEXT NOT NULL,error_type TEXT);
                CREATE UNIQUE INDEX IF NOT EXISTS one_capture ON capture_jobs((1)) WHERE state IN ('capturing','analyzing','recording');
                CREATE TABLE IF NOT EXISTS captured_analyses (id TEXT PRIMARY KEY,session_id TEXT NOT NULL REFERENCES grants(id),payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS outbox (
                  id TEXT PRIMARY KEY REFERENCES captured_analyses(id),session_id TEXT NOT NULL REFERENCES grants(id),
                  payload TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'pending',attempts INTEGER NOT NULL DEFAULT 0,
                  next_attempt REAL NOT NULL DEFAULT 0,last_error TEXT);
                CREATE TABLE IF NOT EXISTS camera_sample_outbox (
                  id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES grants(id),
                  captured_at TEXT NOT NULL, image BLOB NOT NULL,
                  state TEXT NOT NULL DEFAULT 'pending', error_type TEXT);
                CREATE TABLE IF NOT EXISTS camera_photo_drafts (
                  id TEXT PRIMARY KEY,captured_at TEXT NOT NULL,image BLOB NOT NULL,
                   detection TEXT NOT NULL,grant_data TEXT,state TEXT NOT NULL DEFAULT 'review');
                CREATE TABLE IF NOT EXISTS device_identity (
                  singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                  device_id TEXT NOT NULL,api_origin TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sample_claim_attempt (
                  singleton INTEGER PRIMARY KEY CHECK(singleton=1),data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sample_status (
                  sample_id TEXT PRIMARY KEY,
                  photo_id TEXT UNIQUE REFERENCES camera_sample_outbox(id),
                  confirmation TEXT NOT NULL DEFAULT 'received',
                  result TEXT,payload TEXT,claim_id TEXT,lease_token TEXT,
                  analysis_id TEXT,updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sample_evaluation_tracking (
                  sample_id TEXT PRIMARY KEY REFERENCES sample_status(sample_id),
                  tracking TEXT NOT NULL DEFAULT 'active',
                  response TEXT,failures INTEGER NOT NULL DEFAULT 0,last_error TEXT,
                  next_poll_at REAL NOT NULL DEFAULT 0,updated_at TEXT NOT NULL);
            """)
            db.execute('BEGIN IMMEDIATE')
            columns = {row[1] for row in db.execute('PRAGMA table_info(camera_sample_outbox)')}
            if 'review_grant_id' not in columns:
                db.execute(
                    'ALTER TABLE camera_sample_outbox ADD COLUMN review_grant_id TEXT REFERENCES grants(id)'
                )
            if 'original_source_known' not in columns:
                db.execute(
                    'ALTER TABLE camera_sample_outbox ADD COLUMN original_source_known INTEGER NOT NULL DEFAULT 1'
                )

    def bind_device(self, device_id, api_origin):
        from .provisioning import assert_database_identity

        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            assert_database_identity(self.path.resolve(), device_id, api_origin)
            db.execute(
                'INSERT OR IGNORE INTO device_identity VALUES (1,?,?)',
                (device_id, api_origin),
            )

    def save_camera_sample(self, identity, session_id, captured_at, content):
        if not content or len(content) > 5242880:
            raise RuntimeError('Captura excede o limite de 5 MiB.')
        with self.db() as db:
            self._save_camera_sample(db, identity, session_id, captured_at, content)

    def _save_camera_sample(
        self,
        db,
        identity,
        session_id,
        captured_at,
        content,
        review_grant_id=None,
        original_source_known=True,
    ):
        previous = db.execute(
            'SELECT session_id,captured_at,image,review_grant_id,original_source_known,state FROM camera_sample_outbox WHERE id=?',
            (identity,),
        ).fetchone()
        if previous:
            if (
                previous['session_id'] != session_id
                or previous['captured_at'] != captured_at
                or previous['image'] != content
                or bool(previous['original_source_known']) != original_source_known
            ):
                raise RuntimeError('Comando de captura já existe com outro conteúdo.')
            if previous['state'] == 'quarantined' and review_grant_id:
                db.execute(
                    "UPDATE camera_sample_outbox SET state='pending',review_grant_id=?,error_type=NULL WHERE id=?",
                    (review_grant_id, identity),
                )
            elif previous['review_grant_id'] != review_grant_id and previous['state'] != 'synced':
                raise RuntimeError('Comando já associado a outra autorização de envio.')
            return
        if (
            db.execute(
                "SELECT count(*) FROM camera_sample_outbox WHERE state!='synced'"
            ).fetchone()[0]
            >= 200
        ):
            raise RuntimeError(
                'Fila local de fotos cheia. Sincronize ou revise os envios pendentes.'
            )
        db.execute(
            'INSERT INTO camera_sample_outbox(id,session_id,captured_at,image,review_grant_id,original_source_known) VALUES (?,?,?,?,?,?)',
            (
                identity,
                session_id,
                captured_at,
                content,
                review_grant_id,
                int(original_source_known),
            ),
        )

    def save_photo_draft(self, identity, captured_at, content, detection, grant):
        if not content or len(content) > 5242880:
            raise RuntimeError('Foto excede o limite local de 5 MiB.')
        with self.db() as db:
            if (
                db.execute(
                    "SELECT count(*) FROM camera_photo_drafts WHERE state='review'"
                ).fetchone()[0]
                >= 20
            ):
                raise RuntimeError('Há muitas fotos aguardando confirmação neste equipamento.')
            db.execute(
                'INSERT INTO camera_photo_drafts(id,captured_at,image,detection,grant_data) VALUES (?,?,?,?,?)',
                (
                    identity,
                    captured_at,
                    content,
                    json.dumps(detection),
                    json.dumps(grant) if grant else None,
                ),
            )

    def latest_photo_draft(self):
        with self.db() as db:
            row = db.execute(
                "SELECT * FROM camera_photo_drafts WHERE state='review' ORDER BY captured_at DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return {
            **dict(row),
            'detection': json.loads(row['detection']),
            'grant': json.loads(row['grant_data']) if row['grant_data'] else None,
        }

    def reopen_quarantined_photo(self):
        with self.db() as db:
            row = db.execute(
                "SELECT d.id,o.image FROM camera_photo_drafts d JOIN camera_sample_outbox o ON o.id=d.id WHERE d.state='submitted' AND o.state='quarantined' AND o.original_source_known=1 ORDER BY d.captured_at DESC LIMIT 1"
            ).fetchone()
            if row:
                db.execute(
                    "UPDATE camera_photo_drafts SET state='review',image=? WHERE id=?",
                    (row['image'], row['id']),
                )

    def discard_photo_draft(self, identity):
        with self.db() as db:
            # Descarte solicitado explicitamente pelo botão Tirar outra; não remove fotos enviadas.
            db.execute(
                "UPDATE camera_photo_drafts SET state='discarded',image=X'' WHERE id=? AND state='review'",
                (identity,),
            )

    def confirm_photo_draft(self, identity, session_id, review_grant_id=None):
        with self.db() as db:
            row = db.execute('SELECT * FROM camera_photo_drafts WHERE id=?', (identity,)).fetchone()
            if (
                not row
                or (row['grant_data'] and json.loads(row['grant_data'])['id'] != session_id)
                or (not row['grant_data'] and not review_grant_id)
            ):
                raise RuntimeError('Foto não pertence à autorização informada.')
            if row['state'] == 'submitted':
                return
            if row['state'] != 'review':
                raise RuntimeError('Foto já descartada.')
            self._save_camera_sample(
                db,
                identity,
                session_id,
                row['captured_at'],
                row['image'],
                review_grant_id,
                bool(row['grant_data']),
            )
            db.execute(
                "UPDATE camera_photo_drafts SET state='submitted',image=X'' WHERE id=?", (identity,)
            )

    def pending_camera_samples(self):
        with self.db() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM camera_sample_outbox WHERE state='pending' ORDER BY captured_at LIMIT 1"
                ).fetchall()
            ]

    def camera_sample_counts(self):
        with self.db() as db:
            return dict(
                db.execute(
                    'SELECT state,count(*) FROM camera_sample_outbox GROUP BY state'
                ).fetchall()
            )

    def camera_sample_state(self, identity, state, error=None):
        if state not in ('synced', 'quarantined'):
            raise RuntimeError('Estado de envio inválido.')
        with self.db() as db:
            db.execute(
                "UPDATE camera_sample_outbox SET state=?,error_type=? WHERE id=? AND state='pending'",
                (state, error, identity),
            )

    def record_sample_receipt(self, photo_id, sample_id, analysis_id=None):
        """Confirma upload e associação remota juntos, sem reassociar a foto."""
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute(
                'SELECT photo_id,analysis_id FROM sample_status WHERE sample_id=?', (sample_id,)
            ).fetchone()
            if previous:
                if previous['photo_id'] not in (None, photo_id):
                    raise RuntimeError('Amostra já associada a outra foto local.')
                if analysis_id and previous['analysis_id'] not in (None, analysis_id):
                    raise RuntimeError('API retornou outro analysis_id para a mesma amostra.')
            db.execute(
                '''INSERT INTO sample_status(sample_id,photo_id,analysis_id,updated_at)
                VALUES (?,?,?,?) ON CONFLICT(sample_id) DO UPDATE SET
                photo_id=excluded.photo_id,
                analysis_id=coalesce(sample_status.analysis_id,excluded.analysis_id),
                updated_at=excluded.updated_at''',
                (sample_id, photo_id, analysis_id, utcnow()),
            )
            db.execute(
                "UPDATE camera_sample_outbox SET state='synced',error_type=NULL WHERE id=?",
                (photo_id,),
            )

    def sample_claim(self, attempt=None):
        with self.db() as db:
            if attempt is not None:
                db.execute('INSERT INTO sample_claim_attempt VALUES (1,?)', (json.dumps(attempt),))
            row = db.execute('SELECT data FROM sample_claim_attempt WHERE singleton=1').fetchone()
        return json.loads(row['data']) if row else None

    def clear_sample_claim(self):
        with self.db() as db:
            db.execute('DELETE FROM sample_claim_attempt')

    def start_sample_work(self, sample_id, attempt):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute(
                'SELECT confirmation FROM sample_status WHERE sample_id=?', (sample_id,)
            ).fetchone()
            # 'confirmed' = o servidor já aceitou o resultado anterior; se ele entrega a
            # amostra de novo, é um pedido de reprocessamento e o novo resultado vale.
            # Só um resultado ainda NÃO confirmado ('processing'/'pending') é protegido.
            if previous and previous['confirmation'] not in ('received', 'confirmed'):
                raise RuntimeError('Amostra já possui avaliação local; não será sobrescrita.')
            db.execute(
                '''INSERT INTO sample_status(sample_id,confirmation,claim_id,lease_token,updated_at)
                VALUES (?,'processing',?,?,?) ON CONFLICT(sample_id) DO UPDATE SET
                confirmation='processing',claim_id=excluded.claim_id,
                lease_token=excluded.lease_token,result=NULL,payload=NULL,
                analysis_id=CASE WHEN sample_status.confirmation='confirmed' THEN NULL
                    ELSE sample_status.analysis_id END,
                updated_at=excluded.updated_at''',
                (sample_id, attempt['claim_id'], attempt['lease_token'], utcnow()),
            )
            db.execute('DELETE FROM sample_claim_attempt')

    def pending_sample_work(self):
        with self.db() as db:
            row = db.execute(
                "SELECT * FROM sample_status WHERE confirmation IN ('processing','pending') "
                'ORDER BY updated_at,rowid LIMIT 1'
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        for key in ('result', 'payload'):
            result[key] = json.loads(result[key]) if result[key] else None
        return result

    def save_sample_result(self, sample_id, payload, summary):
        with self.db() as db:
            previous = db.execute(
                'SELECT claim_id,payload FROM sample_status WHERE sample_id=?', (sample_id,)
            ).fetchone()
            if not previous or previous['claim_id'] != payload['claim_id']:
                raise RuntimeError('Resultado não corresponde à reserva local da amostra.')
            if previous['payload'] and json.loads(previous['payload']) != payload:
                raise RuntimeError('Não é permitido alterar um resultado pendente de confirmação.')
            db.execute(
                "UPDATE sample_status SET result=?,payload=?,confirmation='pending',updated_at=? "
                'WHERE sample_id=?',
                (json.dumps(summary), json.dumps(payload), utcnow(), sample_id),
            )

    def confirm_sample_result(self, sample_id, summary, analysis_id):
        with self.db() as db:
            previous = db.execute(
                'SELECT analysis_id FROM sample_status WHERE sample_id=?', (sample_id,)
            ).fetchone()
            if not previous:
                raise RuntimeError('Confirmação sem avaliação local correspondente.')
            if analysis_id and previous['analysis_id'] not in (None, analysis_id):
                raise RuntimeError('API retornou outro analysis_id para a mesma amostra.')
            db.execute(
                "UPDATE sample_status SET result=?,confirmation='confirmed',"
                'analysis_id=coalesce(analysis_id,?),payload=NULL,claim_id=NULL,lease_token=NULL,'
                'updated_at=? WHERE sample_id=?',
                (json.dumps(summary), analysis_id, utcnow(), sample_id),
            )

    def due_sample_evaluation(self, now):
        """Próxima captura a consultar: captura local -> amostra remota -> sessão de origem."""
        with self.db() as db:
            row = db.execute(
                """SELECT s.sample_id,o.session_id,g.data,coalesce(t.failures,0) AS failures
                FROM sample_status s
                JOIN camera_sample_outbox o ON o.id=s.photo_id AND o.original_source_known=1
                JOIN grants g ON g.id=o.session_id
                LEFT JOIN sample_evaluation_tracking t ON t.sample_id=s.sample_id
                WHERE coalesce(t.tracking,'active')='active' AND coalesce(t.next_poll_at,0)<=?
                AND json_extract(g.data,'$.lease_token') IS NOT NULL
                ORDER BY coalesce(t.next_poll_at,0),s.updated_at DESC,s.rowid DESC LIMIT 1""",
                (now,),
            ).fetchone()
        if row is None:
            return None
        return {
            'sample_id': row['sample_id'],
            'inspection_id': row['session_id'],
            'lease_token': json.loads(row['data'])['lease_token'],
            'failures': row['failures'],
        }

    def save_sample_evaluation(self, sample_id, response, tracking, next_poll_at):
        with self.db() as db:
            db.execute(
                """INSERT INTO sample_evaluation_tracking
                (sample_id,tracking,response,failures,last_error,next_poll_at,updated_at)
                VALUES (?,?,?,0,NULL,?,?) ON CONFLICT(sample_id) DO UPDATE SET
                tracking=excluded.tracking,response=excluded.response,failures=0,last_error=NULL,
                next_poll_at=excluded.next_poll_at,updated_at=excluded.updated_at""",
                (sample_id, tracking, json.dumps(response), next_poll_at, utcnow()),
            )

    def sample_evaluation_failure(self, sample_id, error, tracking, next_poll_at):
        """Registra a falha de consulta sem apagar a última resposta válida."""
        with self.db() as db:
            db.execute(
                """INSERT INTO sample_evaluation_tracking
                (sample_id,tracking,failures,last_error,next_poll_at,updated_at)
                VALUES (?,?,1,?,?,?) ON CONFLICT(sample_id) DO UPDATE SET
                tracking=excluded.tracking,failures=sample_evaluation_tracking.failures+1,
                last_error=excluded.last_error,next_poll_at=excluded.next_poll_at,
                updated_at=excluded.updated_at""",
                (sample_id, tracking, error, next_poll_at, utcnow()),
            )

    def sample_evaluation(self, sample_id):
        with self.db() as db:
            row = db.execute(
                """SELECT s.sample_id,s.photo_id,o.session_id,o.original_source_known,
                t.tracking,t.response,t.last_error
                FROM sample_status s
                LEFT JOIN camera_sample_outbox o ON o.id=s.photo_id
                LEFT JOIN sample_evaluation_tracking t ON t.sample_id=s.sample_id
                WHERE s.sample_id=?""",
                (sample_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            'sample_id': row['sample_id'],
            'photo_id': row['photo_id'],
            'inspection_id': row['session_id'] if row['original_source_known'] else None,
            'tracking': row['tracking'] or 'active',
            'response': json.loads(row['response']) if row['response'] else None,
            'last_error': row['last_error'],
        }

    def latest_sample_status(self, *, receipt=False, pending=False):
        predicate = "confirmation IN ('processing','pending')" if pending else (
            'photo_id IS NOT NULL' if receipt else 'result IS NOT NULL'
        )
        with self.db() as db:
            row = db.execute(
                'SELECT sample_id,photo_id,confirmation,result,analysis_id,updated_at '
                'FROM sample_status WHERE ' + predicate
                + ' ORDER BY updated_at DESC,rowid DESC LIMIT 1'
            ).fetchone()
        if row is None:
            return None
        return {**dict(row), 'result': json.loads(row['result']) if row['result'] else None}

    def pairing_attempt(self, attempt=None):
        with self.db() as db:
            if attempt is not None:
                db.execute(
                    'INSERT INTO pairing_attempt VALUES (1,?) ON CONFLICT(singleton) DO UPDATE SET data=excluded.data',
                    (json.dumps(attempt),),
                )
            row = db.execute('SELECT data FROM pairing_attempt WHERE singleton=1').fetchone()
        return json.loads(row['data']) if row else None

    def save_grant(self, grant):
        with self.db() as db:
            db.execute('UPDATE grants SET active=0 WHERE active=1')
            db.execute(
                'INSERT INTO grants VALUES (?,?,1) ON CONFLICT(id) DO UPDATE SET data=excluded.data,active=1',
                (grant['id'], json.dumps(grant)),
            )
            db.execute('DELETE FROM pairing_attempt WHERE singleton=1')

    def clear_pairing(self):
        with self.db() as db:
            db.execute('DELETE FROM pairing_attempt WHERE singleton=1')

    def active_grant(self):
        with self.db() as db:
            row = db.execute('SELECT data FROM grants WHERE active=1').fetchone()
        return json.loads(row['data']) if row else None

    def grant(self, session_id):
        with self.db() as db:
            row = db.execute('SELECT data FROM grants WHERE id=?', (session_id,)).fetchone()
        if not row:
            raise RuntimeError('Autorização local não encontrada.')
        return json.loads(row['data'])

    def deactivate(self, session_id):
        with self.db() as db:
            db.execute('UPDATE grants SET active=0 WHERE id=?', (session_id,))

    def update_grant(self, grant):
        with self.db() as db:
            db.execute('UPDATE grants SET data=? WHERE id=?', (json.dumps(grant), grant['id']))

    def recover_interrupted(self):
        with self.db() as db:
            db.execute(
                "UPDATE capture_jobs SET state='interrupted',error_type='WorkerRestarted' WHERE state IN ('capturing','analyzing','recording')"
            )

    def reserve(self, request_id, session_id):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute(
                'SELECT * FROM capture_jobs WHERE request_id=?', (request_id,)
            ).fetchone()
            if row:
                if row['session_id'] != session_id:
                    raise RuntimeError('Comando pertence a outra sessão.')
                return dict(row), False
            analysis_id = str(uuid4())
            db.execute(
                "INSERT INTO capture_jobs(request_id,analysis_id,session_id,state,created_at) VALUES (?,?,?,'capturing',?)",
                (request_id, analysis_id, session_id, utcnow()),
            )
            return {
                'request_id': request_id,
                'analysis_id': analysis_id,
                'session_id': session_id,
                'state': 'capturing',
            }, True

    def job_state(self, request_id, state, error_type=None):
        with self.db() as db:
            db.execute(
                'UPDATE capture_jobs SET state=?,error_type=? WHERE request_id=?',
                (state, error_type, request_id),
            )

    def job(self, request_id):
        with self.db() as db:
            row = db.execute(
                'SELECT * FROM capture_jobs WHERE request_id=?', (request_id,)
            ).fetchone()
        return dict(row) if row else None

    def complete(self, request_id, payload):
        encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False)
        with self.db() as db:
            db.execute(
                'INSERT INTO captured_analyses VALUES (?,?,?)',
                (payload['id'], payload['inspection_session_id'], encoded),
            )
            db.execute(
                'INSERT INTO outbox(id,session_id,payload) VALUES (?,?,?)',
                (payload['id'], payload['inspection_session_id'], encoded),
            )
            db.execute(
                "UPDATE capture_jobs SET state='completed' WHERE request_id=?", (request_id,)
            )

    def due(self, now, limit=10, maximum_bytes=200000):
        with self.db() as db:
            rows = db.execute(
                "SELECT * FROM outbox WHERE state='pending' AND next_attempt<=? ORDER BY rowid LIMIT ?",
                (now, min(limit, 50)),
            ).fetchall()
        selected, size, session = [], 0, None
        for row in rows:
            if session is not None and row['session_id'] != session:
                continue
            length = len(row['payload'].encode())
            if selected and size + length > maximum_bytes:
                break
            if length > maximum_bytes:
                self.mark(row['id'], 'quarantined', 'PayloadTooLarge')
                continue
            selected.append(dict(row))
            size += length
            session = row['session_id']
        return selected

    def mark(self, analysis_id, state, error=None):
        with self.db() as db:
            db.execute(
                "UPDATE outbox SET state=?,last_error=? WHERE id=? AND state='pending'",
                (state, error, analysis_id),
            )

    def retry(self, row, now, delay, error_type):
        with self.db() as db:
            db.execute(
                "UPDATE outbox SET attempts=attempts+1,next_attempt=?,last_error=? WHERE id=? AND state='pending'",
                (now + delay, error_type, row['id']),
            )

    def counts(self):
        with self.db() as db:
            return {
                row['state']: row['count']
                for row in db.execute('SELECT state,count(*) AS count FROM outbox GROUP BY state')
            }
