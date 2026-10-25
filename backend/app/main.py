import json
import secrets
import time
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, Depends, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .config import API_KEY, CORS_ORIGINS
from .db import init_local, local_db, remote_db, utcnow, to_jsonable
from .schemas import DeviceIn, AnalysisIn, EventIn
from .sync import sync_pending
from .logging_config import log
from .ai import interpret_analysis

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_local()
    log.info('API iniciada | SQLite inicializado | Neon configurado: %s', 'sim' if __import__('os').getenv('DATABASE_URL', '').startswith('postgresql://') and 'USUARIO:SENHA@HOST' not in __import__('os').getenv('DATABASE_URL', '') else 'não')
    yield

app = FastAPI(title='OrangeVision API', version='1.0.0', lifespan=lifespan)
@app.middleware("http")
async def request_log(request, call_next):
    start = time.monotonic()
    try:
        response = await call_next(request)
        log.info("%s %s | HTTP %s | %.0f ms", request.method, request.url.path, response.status_code, (time.monotonic() - start) * 1000)
        return response
    except Exception:
        log.exception("Falha ao atender %s %s", request.method, request.url.path)
        raise

app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=['GET','POST'], allow_headers=['X-API-Key','Content-Type'])


def auth(x_api_key: str | None = Header(default=None)):
    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail='Chave de API inválida')

@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'orangevision-api'}

@app.post('/api/dispositivos', dependencies=[Depends(auth)], status_code=201)
def create_device(item: DeviceIn):
    d = item.model_dump(mode='json')
    with local_db() as db:
        db.execute('''INSERT INTO dispositivos (id,nome,modelo,localizacao,status,ultima_conexao,criado_em,sincronizado)
            VALUES (?,?,?,?,?,?,?,0) ON CONFLICT(id) DO UPDATE SET
            nome=excluded.nome,modelo=excluded.modelo,localizacao=excluded.localizacao,
            status=excluded.status,ultima_conexao=excluded.ultima_conexao,sincronizado=0''',
            (d['id'],d['nome'],d['modelo'],d['localizacao'],d['status'],d['ultima_conexao'],utcnow()))
    log.info('Dispositivo salvo localmente: %s', d['id'])
    return {'id': d['id'], 'saved_locally': True}

@app.post('/api/analises', dependencies=[Depends(auth)], status_code=201)
def create_analysis(item: AnalysisIn):
    d = item.model_dump(mode='json')
    cols = list(d) + ['criado_em','sincronizado']
    values = list(d.values()) + [utcnow(),0]
    with local_db() as db:
        try:
            db.execute(f"INSERT INTO analises ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})", values)
        except __import__('sqlite3').IntegrityError:
            return {'id':d['id'],'saved_locally':True,'already_exists':True}
    log.info('Análise registrada localmente | id=%s | classe=%s | score=%s', d['id'], d['classificacao'], d['score_visual'])
    return {'id':d['id'],'saved_locally':True,'already_exists':False}

@app.post('/api/eventos', dependencies=[Depends(auth)], status_code=201)
def create_event(item: EventIn):
    d = item.model_dump(mode='json')
    d['detalhes'] = json.dumps(d['detalhes']) if d['detalhes'] is not None else None
    with local_db() as db:
        try:
            db.execute('INSERT INTO eventos_sistema (id,dispositivo_id,data_hora,tipo,origem,mensagem,detalhes,sincronizado) VALUES (?,?,?,?,?,?,?,0)', tuple(d.values()))
        except __import__('sqlite3').IntegrityError:
            return {'id':d['id'],'already_exists':True}
    return {'id':d['id'],'saved_locally':True}

@app.post('/api/sincronizar', dependencies=[Depends(auth)])
def synchronize():
    try:
        counts = sync_pending()
        log.info('Sincronização Neon concluída: %s', counts)
        return {'synced': counts}
    except Exception as exc:
        log.error('Falha na sincronização Neon: %s', type(exc).__name__)
        raise HTTPException(status_code=503, detail='Neon indisponível ou conexão não configurada') from exc

@app.get('/api/analises', dependencies=[Depends(auth)])
def list_analyses(limit: int = Query(default=50,ge=1,le=500)):
    try:
        with remote_db() as db:
            rows = db.execute('SELECT * FROM analises ORDER BY data_hora DESC LIMIT %s',(limit,)).fetchall()
        return [to_jsonable(r) for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=503, detail='Não foi possível consultar Neon') from exc

@app.get('/api/dispositivos', dependencies=[Depends(auth)])
def list_devices():
    try:
        with remote_db() as db:
            rows = db.execute('SELECT * FROM dispositivos ORDER BY criado_em DESC').fetchall()
        return [to_jsonable(r) for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=503, detail='Não foi possível consultar Neon') from exc

@app.get('/api/eventos', dependencies=[Depends(auth)])
def list_events(limit: int = Query(default=50,ge=1,le=500)):
    try:
        with remote_db() as db:
            rows = db.execute('SELECT * FROM eventos_sistema ORDER BY data_hora DESC LIMIT %s',(limit,)).fetchall()
        return [to_jsonable(r) for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=503, detail='Não foi possível consultar Neon') from exc

@app.get('/api/dashboard/resumo', dependencies=[Depends(auth)])
def dashboard_summary():
    try:
        with remote_db() as db:
            row = db.execute('''SELECT COUNT(*) AS total,
                COUNT(*) FILTER (WHERE classificacao='APROVADA') AS aprovadas,
                COUNT(*) FILTER (WHERE classificacao='ATENCAO') AS atencao,
                COUNT(*) FILTER (WHERE classificacao='REVISAR') AS revisar,
                ROUND(100.0 * COUNT(*) FILTER (WHERE classificacao='APROVADA') / NULLIF(COUNT(*),0),2) AS taxa_aprovacao
                FROM analises''').fetchone()
        return to_jsonable(row)
    except Exception as exc:
        raise HTTPException(status_code=503, detail='Não foi possível consultar Neon') from exc


@app.post('/api/ia/interpretar', dependencies=[Depends(auth)])
def ai_interpret(item: AnalysisIn):
    # IA apenas complementa a explicação; não substitui a classificação local.
    return interpret_analysis(item.model_dump(mode='json'))
