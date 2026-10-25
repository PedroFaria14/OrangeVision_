from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator


class DeviceOption(BaseModel):
    id: UUID
    name: str


class DeviceInspection(BaseModel):
    id: UUID
    device_id: UUID
    operator_name: str
    state: Literal['pending', 'active', 'closing', 'closed', 'expired']
    created_at: datetime
    pairing_expires_at: datetime
    started_at: datetime | None
    authorization_expires_at: datetime | None
    closed_at: datetime | None
    observed_at: datetime


class Inspection(DeviceInspection):
    user_id: UUID


class InspectionConfig(BaseModel):
    enabled: bool
    ownership: Literal['inspection-session', 'device-access']


class StartInspection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    device_id: UUID
    request_id: UUID
    pairing_code: SecretStr = Field(min_length=32, max_length=128)


class PairInspection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    pairing_code: SecretStr = Field(min_length=32, max_length=128)
    activation_id: UUID
    lease_token: SecretStr = Field(min_length=32, max_length=128)


class IngestMetrics(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    orange_color_ratio: float = Field(ge=0, le=1)
    abnormal_region_ratio: float = Field(ge=0, le=1)
    circularity: float = Field(ge=0)
    asymmetry: float = Field(ge=0, le=1)
    visual_score: float = Field(ge=0, le=100)


class IngestAnalysis(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: UUID
    inspection_session_id: UUID
    timestamp: datetime
    classification: Literal['APROVADA', 'ATENCAO', 'REVISAR']
    metrics: IngestMetrics
    calibration_version: str = Field(min_length=1, max_length=100)
    algorithm_version: str = Field(min_length=1, max_length=50)
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator('timestamp')
    @classmethod
    def require_offset(cls, value):
        if value.utcoffset() is None:
            raise ValueError('Timestamp exige fuso horário.')
        return value


class IngestBatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    contract_version: Literal['1'] = '1'
    items: list[IngestAnalysis] = Field(min_length=1, max_length=50)

    @model_validator(mode='after')
    def one_session(self):
        if len({item.inspection_session_id for item in self.items}) != 1:
            raise ValueError('Cada lote pertence a uma única sessão de inspeção.')
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError('Cada análise aparece uma única vez por lote.')
        return self


class IngestResult(BaseModel):
    id: UUID
    status: Literal['accepted', 'duplicate', 'conflict', 'rejected']


class IngestResponse(BaseModel):
    items: list[IngestResult]
