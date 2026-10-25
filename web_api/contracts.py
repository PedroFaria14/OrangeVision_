"""Contratos HTTP definidos antes das rotas e publicados no OpenAPI 3.1."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)


class Credentials(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: EmailStr
    password: SecretStr = Field(min_length=12, max_length=128)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()


class Registration(Credentials):
    name: str = Field(min_length=2, max_length=100)

    @field_validator('name')
    @classmethod
    def validate_name(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError('Informe pelo menos dois caracteres.')
        return value


class PublicUser(BaseModel):
    id: UUID
    name: str
    email: str


class Session(BaseModel):
    user: PublicUser
    csrf_token: str


class Message(BaseModel):
    message: str


class FieldIssue(BaseModel):
    field: str
    message: str


class ValidationErrorResponse(BaseModel):
    detail: list[FieldIssue]


class HttpErrorResponse(BaseModel):
    detail: str


class Filters(BaseModel):
    start: datetime | None = None
    end: datetime | None = None
    classification: Literal['APROVADA', 'ATENCAO', 'REVISAR'] | None = None
    device_id: UUID | None = None

    @model_validator(mode='after')
    def validate_period(self):
        for value in (self.start, self.end):
            if value and value.utcoffset() is None:
                raise ValueError('Datas exigem fuso horário.')
        if self.start and self.end and self.start >= self.end:
            raise ValueError('O início deve ser anterior ao fim exclusivo.')
        return self


class Metrics(BaseModel):
    orange_color_ratio: float | None = Field(ge=0, le=1)
    abnormal_region_ratio: float | None = Field(ge=0, le=1)
    circularity: float | None = Field(ge=0)
    asymmetry: float | None = Field(ge=0, le=1)
    visual_score: float | None = Field(ge=0, le=100)


class Analysis(BaseModel):
    id: UUID
    device_id: UUID | None
    timestamp: datetime
    classification: Literal['APROVADA', 'ATENCAO', 'REVISAR']
    metrics: Metrics
    calibration_version: str | None
    image_url: None = None
    lot: None = None
    synced_at: None = None
    inspection_session_id: UUID | None = None
    classification_reason: str | None = None


class AnalysisPage(BaseModel):
    items: list[Analysis]
    total: int
    as_of: datetime


class Summary(BaseModel):
    total: int
    approved: int
    attention: int
    review: int
    approval_rate: float | None
    latest_analysis_at: datetime | None
    as_of: datetime


class PeriodSummary(Summary):
    start: datetime
    end: datetime
    observed_end: datetime
    in_progress: bool
    not_approved: int = Field(ge=0)


class CountChange(BaseModel):
    absolute: int
    percent: float | None


class PeriodChanges(BaseModel):
    total: CountChange
    approved: CountChange
    attention: CountChange
    review: CountChange
    not_approved: CountChange
    approval_rate_pp: float | None


class PeriodComparison(BaseModel):
    current: PeriodSummary
    previous: PeriodSummary
    changes: PeriodChanges
    as_of: datetime
    timezone: Literal['America/Sao_Paulo'] = 'America/Sao_Paulo'
    boundary: Literal['start-inclusive-end-exclusive'] = 'start-inclusive-end-exclusive'


class Bucket(BaseModel):
    start: datetime
    approved: int
    attention: int
    review: int


class Timeseries(BaseModel):
    items: list[Bucket]
    timezone: str = 'America/Sao_Paulo'
    granularity: str = 'day'
    coverage: str = 'observed-only'
    as_of: datetime
