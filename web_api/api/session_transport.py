import secrets

from fastapi import HTTPException, Request, Response

COOKIE = 'orangevision_session'


def check_origin(request: Request) -> None:
    if request.headers.get('origin') not in request.app.state.settings.origins:
        raise HTTPException(403, 'Origem não autorizada.')


def check_csrf(request: Request, session: dict) -> None:
    if not secrets.compare_digest(request.headers.get('x-csrf-token', ''), session['csrf_token']):
        raise HTTPException(403, 'Não foi possível validar esta operação.')


def client_identity(request: Request) -> str:
    # Não confiar em X-Forwarded-For sem proxy explicitamente confiável.
    return request.client.host if request.client else 'unknown'


def set_session_cookie(response: Response, settings, token: str) -> None:
    response.set_cookie(
        COOKIE,
        token,
        max_age=settings.session_seconds,
        httponly=True,
        secure=settings.secure_cookie,
        samesite='lax',
        path='/api',
    )


def clear_session_cookie(response: Response, settings) -> None:
    response.delete_cookie(
        COOKIE, path='/api', secure=settings.secure_cookie, httponly=True, samesite='lax'
    )
