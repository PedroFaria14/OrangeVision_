from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal['APROVADA', 'ATENCAO', 'REVISAR']


class VisualAssessment(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    evaluable: bool
    classification: Category | None
    reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode='after')
    def coherent(self):
        if self.evaluable != (self.classification is not None):
            raise ValueError('Categoria exige imagem avaliável.')
        return self


class Evaluation(BaseModel):
    id: UUID
    origin: Literal['local', 'gemini']
    state: Literal['completed', 'awaiting_review', 'not_evaluable', 'failed']
    classification: Category | None
    reason: str
    criteria_version: str
    model_version: str | None
    created_at: datetime


class GeminiJob(BaseModel):
    id: UUID
    state: Literal['queued', 'running', 'retry_wait', 'completed', 'failed']
    attempts: int
    error_code: str | None
    updated_at: datetime


class AdoptedDecision(BaseModel):
    revision: int
    origin: Literal['local', 'gemini', 'human']
    classification: Category
    reason: str
    created_at: datetime


class GeminiRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    request_id: UUID
    expected_revision: int = Field(ge=0)
    evaluation_id: UUID | None = None
    classification: Category
    reason: str = Field(min_length=5, max_length=1000)
