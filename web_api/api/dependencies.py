from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, Request, Security
from fastapi.exceptions import RequestValidationError
from fastapi.security import APIKeyCookie
from pydantic import ValidationError

from ..application.auth_service import AuthService
from ..application.query_service import QueryService
from ..contracts import Filters
from ..infrastructure.analysis_repository import AnalysisRepository
from ..infrastructure.auth_repository import AuthRepository
from ..infrastructure.passwords import PasswordSecurity
from .session_transport import COOKIE

cookie_scheme = APIKeyCookie(name=COOKIE, auto_error=False)


def get_auth_service(request: Request) -> AuthService:
    settings = request.app.state.settings
    return AuthService(AuthRepository(settings), PasswordSecurity(), settings.session_seconds)


def get_query_service(request: Request) -> QueryService:
    return QueryService(AnalysisRepository(request.app.state.settings))


AuthDependency = Annotated[AuthService, Depends(get_auth_service)]
QueryDependency = Annotated[QueryService, Depends(get_query_service)]


def current_session(service: AuthDependency, token: Annotated[str | None, Security(cookie_scheme)]):
    return service.session(token)


def parse_filters(
    start: datetime | None = None,
    end: datetime | None = None,
    classification: Literal['APROVADA', 'ATENCAO', 'REVISAR'] | None = None,
    device_id: UUID | None = None,
):
    try:
        return Filters(start=start, end=end, classification=classification, device_id=device_id)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


CurrentSession = Annotated[dict, Depends(current_session)]
QueryFilters = Annotated[Filters, Depends(parse_filters)]
