from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..application.errors import ApplicationError
from ..application.inspection_service import InspectionService
from ..infrastructure.inspection_repository import InspectionRepository
from ..inspection_contracts import (
    DeviceInspection,
    DeviceOption,
    IngestBatch,
    IngestResponse,
    Inspection,
    InspectionConfig,
    PairInspection,
    StartInspection,
)
from .dependencies import CurrentSession
from .session_transport import check_csrf, check_origin

router = APIRouter()
bearer = HTTPBearer(auto_error=False, scheme_name='DeviceCredential')


def inspection_service(request: Request):
    settings = request.app.state.settings
    if not settings.inspections_enabled:
        raise ApplicationError(503, 'Inspeções estão desativadas neste ambiente.')
    return InspectionService(InspectionRepository(settings), settings.inspection_lease_seconds)


Service = Annotated[InspectionService, Depends(inspection_service)]


def authenticated_device(
    service: Service, credential: Annotated[HTTPAuthorizationCredentials | None, Security(bearer)]
):
    return service.authenticate_device(credential.credentials if credential else None)['device_id']


Device = Annotated[UUID, Depends(authenticated_device)]
Lease = Annotated[str, Header(alias='X-Inspection-Lease', min_length=32, max_length=128)]


@router.get('/api/inspections/config', response_model=InspectionConfig)
def configuration(request: Request, session: CurrentSession):
    return {
        'enabled': request.app.state.settings.inspections_enabled,
        'ownership': 'inspection-session'
        if request.app.state.settings.inspections_enabled
        else 'device-access',
    }


@router.get('/api/inspections/devices', response_model=list[DeviceOption])
def devices(session: CurrentSession, service: Service):
    return service.devices(session['user']['id'])


@router.get('/api/inspections/current', response_model=list[Inspection])
def current(session: CurrentSession, service: Service):
    return service.current(session['user']['id'])


@router.post('/api/inspections', response_model=Inspection, status_code=201)
def start(payload: StartInspection, request: Request, session: CurrentSession, service: Service):
    check_origin(request)
    check_csrf(request, session)
    return service.start(
        session['user']['id'],
        payload.device_id,
        payload.request_id,
        payload.pairing_code.get_secret_value(),
    )


@router.post('/api/inspections/{inspection_id}/close', response_model=Inspection)
def close(inspection_id: UUID, request: Request, session: CurrentSession, service: Service):
    check_origin(request)
    check_csrf(request, session)
    return service.request_close(session['user']['id'], inspection_id)


@router.post('/api/device/inspections/pair', response_model=DeviceInspection)
def pair(payload: PairInspection, device: Device, service: Service):
    return service.pair(
        device,
        payload.pairing_code.get_secret_value(),
        payload.activation_id,
        payload.lease_token.get_secret_value(),
    )


@router.get('/api/device/inspections/{inspection_id}', response_model=DeviceInspection)
def device_status(inspection_id: UUID, device: Device, lease: Lease, service: Service):
    return service.device_session(device, inspection_id, lease)


@router.post('/api/device/inspections/{inspection_id}/closed', response_model=DeviceInspection)
def device_closed(inspection_id: UUID, device: Device, lease: Lease, service: Service):
    return service.acknowledge_close(device, inspection_id, lease)


@router.post('/api/ingest/analyses', response_model=IngestResponse)
def ingest(payload: IngestBatch, device: Device, lease: Lease, service: Service):
    return service.ingest(device, lease, payload.items)
