from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field

class DeviceIn(BaseModel):
    id: UUID
    nome: str = Field(min_length=1, max_length=100)
    modelo: str | None = None
    localizacao: str | None = None
    status: Literal['online', 'offline', 'manutencao'] = 'offline'
    ultima_conexao: datetime | None = None

class AnalysisIn(BaseModel):
    id: UUID
    dispositivo_id: UUID | None = None
    data_hora: datetime
    classificacao: Literal['APROVADA', 'ATENCAO', 'REVISAR']
    cor_media: float | None = Field(default=None, ge=0, le=100)
    regioes_anormais: float | None = Field(default=None, ge=0, le=100)
    circularidade: float | None = Field(default=None, ge=0, le=1)
    assimetria: float | None = Field(default=None, ge=0, le=100)
    score_visual: float | None = Field(default=None, ge=0, le=100)
    imagem_url: str | None = None
    versao_algoritmo: str | None = None

class EventIn(BaseModel):
    id: UUID
    dispositivo_id: UUID | None = None
    data_hora: datetime
    tipo: Literal['INFO', 'AVISO', 'ERRO']
    origem: str | None = None
    mensagem: str = Field(min_length=1)
    detalhes: dict[str, Any] | None = None
