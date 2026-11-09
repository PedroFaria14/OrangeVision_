from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, Query, Request, Security
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials

from ..application.sample_service import SampleService
from ..contracts import HttpErrorResponse
from ..evaluation_contracts import DecisionRequest, GeminiRequest
from ..infrastructure.sample_images import SampleImages
from ..infrastructure.sample_repository import SampleRepository
from ..inspection_contracts import DeviceOption
from ..sample_contracts import (
    AuthorizePhotoReview,
    ClaimSample,
    DeviceSampleEvaluations,
    ExecutorAcknowledgement,
    ExecutorHeartbeat,
    ImageSample,
    PhotoReviewAuthorized,
    QueueSample,
    SampleDeviceOption,
    SampleList,
    SampleResult,
    SamplesConfig,
)
from .dependencies import CurrentSession
from .inspection_routes import Lease as InspectionLease
from .inspection_routes import bearer
from .session_transport import check_csrf, check_origin

router = APIRouter()


def sample_service(request: Request):
    return SampleService(SampleRepository(request.app.state.settings), SampleImages())


Samples = Annotated[SampleService, Depends(sample_service)]


def sample_device(
    service: Samples, credential: Annotated[HTTPAuthorizationCredentials | None, Security(bearer)]
):
    return service.authenticate_device(credential.credentials if credential else None)


SampleDevice = Annotated[UUID, Depends(sample_device)]
SampleLease = Annotated[str, Header(alias='X-Sample-Lease', min_length=32, max_length=128)]
OriginalLease = Annotated[
    str | None, Header(alias='X-Original-Inspection-Lease', min_length=32, max_length=128)
]


@router.post('/api/device/samples/authorize-review', response_model=PhotoReviewAuthorized)
def authorize_photo_review(
    payload: AuthorizePhotoReview,
    device: SampleDevice,
    lease: InspectionLease,
    service: Samples,
    original_lease: OriginalLease = None,
):
    return service.authorize_review(
        device, payload.original_inspection_id, original_lease, payload.review_inspection_id, lease
    )


@router.post('/api/device/samples/review-capture', response_model=ImageSample, status_code=201)
def upload_review_capture(
    device: SampleDevice,
    lease: InspectionLease,
    service: Samples,
    review_inspection_id: UUID,
    request_id: UUID,
    captured_at: datetime,
    content: Annotated[bytes, Body(media_type='application/octet-stream')],
    original_inspection_id: UUID | None = None,
    original_lease: OriginalLease = None,
):
    return service.upload_review_capture(
        device,
        original_inspection_id,
        original_lease,
        review_inspection_id,
        lease,
        request_id,
        captured_at,
        content,
    )


@router.post('/api/device/samples/capture', response_model=ImageSample, status_code=201)
def device_capture(
    device: SampleDevice,
    lease: InspectionLease,
    service: Samples,
    inspection_id: UUID,
    request_id: UUID,
    captured_at: datetime,
    content: Annotated[bytes, Body(media_type='application/octet-stream')],
):
    return service.upload_capture(device, inspection_id, lease, request_id, captured_at, content)


@router.get('/api/samples/config', response_model=SamplesConfig)
def sample_config(session: CurrentSession, service: Samples):
    return {**service.configuration(), 'processing': 'device', 'max_upload_bytes': 5242880}


@router.get('/api/samples/devices', response_model=list[DeviceOption])
def sample_devices(session: CurrentSession, service: Samples):
    return service.devices(session['user']['id'])


@router.get('/api/samples/executors', response_model=list[SampleDeviceOption])
def sample_executors(session: CurrentSession, service: Samples):
    return service.devices(session['user']['id'])


@router.post('/api/device/samples/heartbeat', response_model=ExecutorAcknowledgement)
def sample_heartbeat(payload: ExecutorHeartbeat, device: SampleDevice, service: Samples):
    return service.heartbeat(device, payload.model_dump())


@router.get('/api/samples', response_model=SampleList)
def list_samples(
    session: CurrentSession,
    service: Samples,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
):
    return service.listing(session['user']['id'], limit, offset)


@router.post('/api/samples', response_model=ImageSample, status_code=201)
def upload_sample(
    request: Request,
    session: CurrentSession,
    service: Samples,
    request_id: UUID,
    filename: Annotated[str, Query(min_length=1, max_length=255)],
    content: Annotated[bytes, Body(media_type='application/octet-stream')],
):
    check_origin(request)
    check_csrf(request, session)
    return service.upload(session['user']['id'], request_id, filename, content)


@router.get(
    '/api/samples/{sample_id}/image',
    response_class=Response,
    responses={200: {'content': {'image/jpeg': {}}, 'description': 'Imagem privada normalizada.'}},
)
def sample_image(sample_id: UUID, session: CurrentSession, service: Samples):
    return Response(service.image(session['user']['id'], sample_id), media_type='image/jpeg')


@router.get(
    '/api/samples/{sample_id}/mask',
    response_class=Response,
    responses={200: {'content': {'image/png': {}}, 'description': 'Máscara privada da amostra.'}},
)
def sample_mask(sample_id: UUID, session: CurrentSession, service: Samples):
    return Response(
        service.image(session['user']['id'], sample_id, mask=True), media_type='image/png'
    )


@router.post('/api/samples/{sample_id}/queue', response_model=ImageSample)
def queue_sample(
    sample_id: UUID,
    payload: QueueSample,
    request: Request,
    session: CurrentSession,
    service: Samples,
):
    check_origin(request)
    check_csrf(request, session)
    return service.queue(session['user']['id'], sample_id, payload.device_id)


@router.post('/api/samples/{sample_id}/analysis', response_model=ImageSample,
             description='Registra uma captura concluída da própria conta no dashboard. Idempotente por amostra; requer migration 007 e inspeções ativas.')
def publish_sample(sample_id: UUID, request: Request, session: CurrentSession, service: Samples):
    check_origin(request)
    check_csrf(request, session)
    return service.publish(session['user']['id'], sample_id)


@router.post('/api/device/samples/claim', response_model=ImageSample | None)
def claim_sample(payload: ClaimSample, device: SampleDevice, service: Samples):
    return service.claim(device, payload.claim_id, payload.lease_token.get_secret_value())


@router.post('/api/samples/{sample_id}/evaluations/gemini', response_model=ImageSample, status_code=202)
def request_gemini(sample_id: UUID, payload: GeminiRequest, request: Request, session: CurrentSession, service: Samples):
    check_origin(request)
    check_csrf(request, session)
    return service.request_gemini(session['user']['id'], sample_id, payload.request_id)


@router.post('/api/samples/{sample_id}/decisions', response_model=ImageSample)
def decide_sample(sample_id: UUID, payload: DecisionRequest, request: Request, session: CurrentSession, service: Samples):
    check_origin(request)
    check_csrf(request, session)
    return service.decide(session['user']['id'], sample_id, payload)


@router.get(
    '/api/device/samples/{sample_id}/image',
    response_class=Response,
    responses={
        200: {
            'content': {'image/jpeg': {}},
            'description': 'Arquivo da reserva ativa do equipamento.',
        }
    },
)
def device_sample_image(
    sample_id: UUID, device: SampleDevice, lease: SampleLease, service: Samples
):
    return Response(service.device_image(device, sample_id, lease), media_type='image/jpeg')


@router.get(
    '/api/device/samples/{sample_id}/evaluations',
    response_model=DeviceSampleEvaluations,
    description='Consulta somente leitura das avaliações de uma captura do próprio equipamento. '
    'Exige a lease da sessão de origem, vale até uma hora após o encerramento ou expiração, '
    'não agenda Gemini, não consome a fila e não altera resultados.',
    responses={
        403: {'description': 'Vínculo da conta com o equipamento removido.', 'model': HttpErrorResponse},
        404: {'description': 'Amostra inexistente, de outro equipamento, sem sessão ou com lease incorreta.', 'model': HttpErrorResponse},
        410: {'description': 'Prazo de consulta encerrado; o resultado continua no site.', 'model': HttpErrorResponse},
        503: {'description': 'Banco indisponível, migration 008 ausente ou inspeções desativadas.', 'model': HttpErrorResponse},
    },
)
def device_sample_evaluations(
    sample_id: UUID, device: SampleDevice, lease: InspectionLease, service: Samples
):
    return service.device_evaluations(device, sample_id, lease)


@router.post('/api/device/samples/{sample_id}/result', response_model=ImageSample)
def finish_sample(
    sample_id: UUID,
    payload: SampleResult,
    device: SampleDevice,
    lease: SampleLease,
    service: Samples,
):
    return service.finish(device, sample_id, lease, payload)
