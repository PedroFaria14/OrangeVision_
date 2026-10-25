"""Entrypoint online. Não inicializa SQLite, câmera, GPIO ou sincronizador."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.analysis_routes import router as analysis_router
from .api.auth_routes import router as auth_router
from .api.body_limit import DeviceBodyLimit
from .api.http import configure_http
from .api.inspection_routes import router as inspection_router
from .api.sample_routes import router as sample_router
from .config import Settings
from .contracts import (
    HttpErrorResponse,
    ValidationErrorResponse,
)
from .observability import configure_logging


def create_app(settings=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.settings = settings or Settings.load()
        configure_logging()
        yield

    app = FastAPI(
        title='OrangeVision Online API',
        version='2.0.0',
        lifespan=lifespan,
        description='API online separada do Raspberry. Datas com offset, início inclusivo e fim exclusivo. '
        'Usuários novos não têm dispositivos. Histórico append-only e limitado a 100 itens por página. '
        'Campos métricos ausentes permanecem null. Razões 0–1; score experimental 0–100. '
        'Sem snapshot comum entre endpoints; as_of é horário da consulta.',
        responses={
            401: {'description': 'Sessão ausente ou expirada.', 'model': HttpErrorResponse},
            403: {
                'description': 'Sem permissão ou origem/CSRF inválidos.',
                'model': HttpErrorResponse,
            },
            404: {
                'description': 'Recurso inexistente ou não autorizado.',
                'model': HttpErrorResponse,
            },
            409: {'description': 'Conflito de cadastro.', 'model': HttpErrorResponse},
            422: {'description': 'Campos ausentes/inválidos.', 'model': ValidationErrorResponse},
            429: {
                'description': 'Limite de tentativas/capacidade. Consultar Retry-After.',
                'model': HttpErrorResponse,
            },
            500: {
                'description': 'Falha interna sem exposição de dados.',
                'model': HttpErrorResponse,
            },
            503: {
                'description': 'Banco indisponível ou migration ainda não aplicada.',
                'model': HttpErrorResponse,
            },
        },
    )

    configure_http(app)
    app.add_middleware(DeviceBodyLimit)

    @app.get('/health')
    def health():
        return {'status': 'ok', 'service': 'orangevision-web'}

    app.include_router(auth_router)
    app.include_router(analysis_router)
    app.include_router(inspection_router)
    app.include_router(sample_router)

    return app


app = create_app()
