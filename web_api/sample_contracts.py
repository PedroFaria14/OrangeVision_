from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

SampleState = Literal[
    'received', 'queued', 'processing', 'awaiting_review', 'completed', 'not_evaluable', 'failed'
]


class SampleMetrics(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    orange_color_ratio: float | None = Field(default=None, ge=0, le=1)
    abnormal_region_ratio: float | None = Field(default=None, ge=0, le=1)
    circularity: float | None = Field(default=None, ge=0)
    asymmetry: float | None = Field(default=None, ge=0, le=1)
    visual_score: float | None = Field(default=None, ge=0, le=100)


class Detection(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    status: Literal['detected', 'not_detected', 'ambiguous']
    label: Literal['orange'] | None = None
    score: float | None = Field(default=None, ge=0, le=1)
    box: list[int] | None = Field(default=None, min_length=4, max_length=4)
    count: int = Field(ge=0, le=100)
    model: str = Field(min_length=1, max_length=100)
    inference_ms: float = Field(ge=0, le=300000)

    @model_validator(mode='after')
    def coherent_detection(self):
        if self.box and (
            any(value < 0 for value in self.box) or self.box[2] <= 0 or self.box[3] <= 0
        ):
            raise ValueError('Caixa de detecção inválida.')
        if self.status == 'detected':
            if self.count != 1 or self.label != 'orange' or self.score is None or self.box is None:
                raise ValueError('Detecção única exige caixa e score.')
        elif self.label is not None or self.score is not None or self.box is not None:
            raise ValueError('Detecção não confirmada não pode afirmar uma fruta única.')
        if (self.status == 'not_detected' and self.count != 0) or (
            self.status == 'ambiguous' and self.count < 2
        ):
            raise ValueError('Contagem incompatível com a detecção.')
        return self


class SampleDeviceOption(BaseModel):
    id: UUID
    name: str
    last_seen_at: datetime | None = None
    executor_state: Literal['starting', 'ready', 'error', 'stopped'] | None = None
    executor_message: str | None = None
    executor_recent: bool = False
    model_version: str | None = None


class ExecutorHeartbeat(BaseModel):
    model_config = ConfigDict(extra='forbid')
    state: Literal['starting', 'ready', 'error', 'stopped']
    model_version: str | None = Field(default=None, max_length=100)
    message: str | None = Field(default=None, max_length=300)


class ExecutorAcknowledgement(BaseModel):
    last_seen_at: datetime


class ImageSample(BaseModel):
    id: UUID
    filename: str
    width: int
    height: int
    state: SampleState
    device_id: UUID | None
    metrics: SampleMetrics | None
    classification: Literal['APROVADA', 'ATENCAO', 'REVISAR'] | None
    reason: str | None
    calibration_version: str | None
    algorithm_version: str | None
    image_url: str
    mask_url: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    claim_expires_at: datetime | None
    detection: Detection | None = None
    source_inspection_id: UUID | None = None
    captured_at: datetime | None = None
    review_authorization_id: UUID | None = None


class AuthorizePhotoReview(BaseModel):
    model_config = ConfigDict(extra='forbid')
    original_inspection_id: UUID | None = None
    review_inspection_id: UUID


class PhotoReviewAuthorized(BaseModel):
    authorized: Literal[True] = True


class SampleList(BaseModel):
    items: list[ImageSample]
    total: int


class SamplesConfig(BaseModel):
    enabled: bool
    processing: Literal['device'] = 'device'
    max_upload_bytes: int = 5242880


class QueueSample(BaseModel):
    model_config = ConfigDict(extra='forbid')
    device_id: UUID


class ClaimSample(BaseModel):
    model_config = ConfigDict(extra='forbid')
    claim_id: UUID
    lease_token: SecretStr = Field(min_length=32, max_length=128)


class SampleResult(BaseModel):
    model_config = ConfigDict(extra='forbid')
    claim_id: UUID
    state: Literal['awaiting_review', 'completed', 'not_evaluable', 'failed']
    reason: str = Field(min_length=1, max_length=1000)
    metrics: SampleMetrics | None = None
    classification: Literal['APROVADA', 'ATENCAO', 'REVISAR'] | None = None
    calibration_version: str | None = Field(default=None, min_length=1, max_length=100)
    algorithm_version: str | None = Field(default=None, min_length=1, max_length=100)
    calibration_validated: bool = False
    mask_base64: str | None = Field(default=None, max_length=2000000)
    detection: Detection | None = None

    @model_validator(mode='after')
    def coherent_result(self):
        if self.state == 'completed':
            if self.detection is not None and self.detection.status != 'detected':
                raise ValueError('Resultado de qualidade não pode contradizer a detecção.')
            if self.algorithm_version == 'yolox-s-grabcut-v1' and self.detection is None:
                raise ValueError('Resultado IA exige evidência de detecção.')
            if (
                not self.calibration_validated
                or not self.classification
                or not self.calibration_version
                or not self.algorithm_version
                or self.metrics is None
                or any(value is None for value in self.metrics.model_dump().values())
            ):
                raise ValueError(
                    'Resultado completo exige calibração validada, categoria e métricas.'
                )
        elif self.classification is not None or (
            self.metrics and self.metrics.visual_score is not None
        ):
            raise ValueError('Amostra não concluída não pode fornecer categoria ou score.')
        if self.state in ('failed', 'not_evaluable') and self.metrics is not None:
            raise ValueError('Falhas não podem fornecer métricas como resultado utilizável.')
        return self
