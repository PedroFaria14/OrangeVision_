import logging
import time
from uuid import uuid4

import psycopg
from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..application.errors import ApplicationError
from .session_transport import check_origin

log = logging.getLogger('orangevision.web')


def configure_http(app):
    @app.middleware('http')
    async def headers(request, call_next):
        started, request_id = time.monotonic(), str(uuid4())
        try:
            response = await call_next(request)
        except Exception as exc:
            log.error(
                'request_failed', extra={'request_id': request_id, 'error_type': type(exc).__name__}
            )
            response = JSONResponse(
                status_code=500, content={'detail': 'Não foi possível concluir a solicitação.'}
            )
        response.headers.update(
            {
                'Cache-Control': 'no-store',
                'X-Content-Type-Options': 'nosniff',
                'X-Request-ID': request_id,
                'Referrer-Policy': 'no-referrer',
            }
        )
        origin = request.headers.get('origin')
        if origin in request.app.state.settings.origins:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Vary'] = 'Origin'
        log.info(
            'request_completed',
            extra={
                'request_id': request_id,
                'status': response.status_code,
                'duration_ms': round((time.monotonic() - started) * 1000),
            },
        )
        return response

    @app.options('/api/{path:path}', include_in_schema=False)
    def preflight(request: Request, path: str):
        check_origin(request)
        return Response(
            status_code=204,
            headers={
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,X-CSRF-Token',
            },
        )

    @app.exception_handler(ApplicationError)
    async def application_error(request, exc):
        return JSONResponse(
            status_code=exc.status_code, content={'detail': exc.detail}, headers=exc.headers
        )

    @app.exception_handler(psycopg.Error)
    async def database_error(request, exc):
        log.error('database_operation_failed', extra={'error_type': type(exc).__name__})
        return JSONResponse(status_code=503, content={'detail': 'Serviço de dados indisponível.'})

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        details = [
            {
                'field': '.'.join(str(v) for v in error['loc'][1:]) or 'period',
                'message': 'Valor ausente ou inválido.',
            }
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={'detail': details})
