from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from ..application.device_service import DeviceService
from ..device_contracts import (
    CredentialRegistration,
    DeviceCredentialIssued,
    DeviceRegistration,
    UserDevices,
)
from ..infrastructure.device_repository import DeviceRepository
from .dependencies import CurrentSession
from .session_transport import check_csrf, check_origin

router = APIRouter()


def get_device_service(request: Request):
    settings = request.app.state.settings
    return DeviceService(
        DeviceRepository(settings), settings.max_devices_per_user, settings.device_api_base_url
    )


DeviceDependency = Annotated[DeviceService, Depends(get_device_service)]


@router.get('/api/devices', response_model=UserDevices)
def list_devices(value: CurrentSession, service: DeviceDependency):
    return service.list_devices(value['user']['id'])


@router.post(
    '/api/devices', status_code=201, response_model=DeviceCredentialIssued,
    responses={200: {'model': DeviceCredentialIssued, 'description': 'Comando já confirmado, sem segredo.'}},
)
def register_device(
    payload: DeviceRegistration, request: Request, response: Response,
    value: CurrentSession, service: DeviceDependency,
):
    check_origin(request)
    check_csrf(request, value)
    result = service.register(value['user']['id'], payload.request_id, payload.name)
    response.status_code = 200 if result.replayed else 201
    return result


@router.post('/api/devices/{device_id}/credentials', response_model=DeviceCredentialIssued)
def rotate_credential(
    device_id: UUID, payload: CredentialRegistration, request: Request,
    value: CurrentSession, service: DeviceDependency,
):
    check_origin(request)
    check_csrf(request, value)
    return service.rotate(value['user']['id'], device_id, payload.request_id)
