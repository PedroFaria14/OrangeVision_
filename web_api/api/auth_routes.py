from fastapi import APIRouter, Header, Request, Response

from ..contracts import Credentials, Message, Registration, Session
from .dependencies import AuthDependency, CurrentSession
from .session_transport import (
    COOKIE,
    check_csrf,
    check_origin,
    clear_session_cookie,
    client_identity,
    set_session_cookie,
)

router = APIRouter()


@router.post('/api/auth/register', status_code=201, response_model=Message)
def register(payload: Registration, request: Request, service: AuthDependency):
    check_origin(request)
    return service.register(
        payload.name, payload.email, payload.password.get_secret_value(), client_identity(request)
    )


@router.post('/api/auth/login', response_model=Session)
def login(payload: Credentials, request: Request, response: Response, service: AuthDependency):
    check_origin(request)
    issued = service.login(
        payload.email,
        payload.password.get_secret_value(),
        client_identity(request),
        request.cookies.get(COOKIE),
    )
    set_session_cookie(response, request.app.state.settings, issued.token)
    return issued.data


@router.get('/api/auth/session', response_model=Session)
def session(value: CurrentSession):
    return value


@router.post('/api/auth/logout', status_code=204)
def logout(
    request: Request,
    response: Response,
    value: CurrentSession,
    service: AuthDependency,
    csrf_token: str | None = Header(default=None, alias='X-CSRF-Token'),
):
    check_origin(request)
    check_csrf(request, value)
    service.logout(request.cookies[COOKIE])
    clear_session_cookie(response, request.app.state.settings)
