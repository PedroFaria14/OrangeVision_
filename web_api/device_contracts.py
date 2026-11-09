from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeviceRegistration(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID
    name: str = Field(min_length=2, max_length=100)

    @field_validator('name')
    @classmethod
    def normalize_name(cls, value):
        value = value.strip()
        if len(value) < 2 or any(not character.isprintable() for character in value):
            raise ValueError('Informe um nome válido para o equipamento.')
        return value


class CredentialRegistration(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID


class UserDevice(BaseModel):
    id: UUID
    name: str
    created_at: datetime | None
    can_manage_credentials: bool


class UserDevices(BaseModel):
    items: list[UserDevice]
    registration_enabled: bool
    managed_count: int = Field(ge=0)
    max_devices: int = Field(ge=1)
    api_base_url: str | None = None


class DeviceCredentialIssued(BaseModel):
    device: UserDevice
    credential: str | None = Field(repr=False)
    replayed: bool
