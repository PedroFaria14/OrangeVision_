"""Configuração exclusiva do serviço online; nenhum segredo vai para o React."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values, load_dotenv


@dataclass(frozen=True)
class Settings:
    database_url: str
    origins: tuple[str, ...]
    secure_cookie: bool
    session_seconds: int
    inspections_enabled: bool = False
    inspection_lease_seconds: int = 28800
    max_devices_per_user: int = 5
    device_api_base_url: str | None = None
    gemini_enabled: bool = False
    gemini_api_key: str = field(default='', repr=False)
    gemini_model: str = 'gemini-3.8-flash'
    gemini_timeout: int = 30
    gemini_daily_limit: int = 50
    gemini_user_daily_limit: int = 10
    gemini_inprocess: bool = False
    gemini_auto_adopt: bool = False
    # false: Gemini só roda quando alguém pede no site (segunda opinião sob demanda).
    gemini_auto_request: bool = True

    @classmethod
    def load(cls):
        load_dotenv(Path(__file__).parent / '.env', override=False)
        database_url = os.getenv('WEB_DATABASE_URL') or os.getenv('DATABASE_URL') or ''
        origins = tuple(
            x.strip().rstrip('/')
            for x in os.getenv(
                'WEB_ALLOWED_ORIGINS', 'http://127.0.0.1:5173,http://localhost:5173'
            ).split(',')
            if x.strip()
        )
        environment = os.getenv('WEB_ENV', 'development')
        if environment not in ('development', 'production'):
            raise RuntimeError('WEB_ENV deve ser development ou production.')
        production = environment == 'production'
        # Compatibilidade LOCAL opcional. Produção/Render não depende da pasta do Pi.
        if not database_url and not production:
            legacy_file = Path(__file__).parent.parent / 'backend' / '.env'
            if legacy_file.is_file():
                database_url = dotenv_values(legacy_file).get('DATABASE_URL') or ''
        seconds = int(os.getenv('WEB_SESSION_SECONDS', '28800'))
        if not database_url.startswith(('postgresql://', 'postgres://')):
            raise RuntimeError('Configure WEB_DATABASE_URL no ambiente exclusivo da API online.')
        if 'USUARIO:SENHA@HOST' in database_url:
            raise RuntimeError('Substitua a conexão de exemplo pela conexão do servidor.')
        if (
            not origins
            or '*' in origins
            or any(not x.startswith(('http://', 'https://')) for x in origins)
        ):
            raise RuntimeError('WEB_ALLOWED_ORIGINS exige origens explícitas.')
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                not parsed.hostname
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
            ):
                raise RuntimeError('Origens devem conter somente protocolo, host e porta opcional.')
        if production and any(not x.startswith('https://') for x in origins):
            raise RuntimeError('Produção exige origens HTTPS.')
        if not 300 <= seconds <= 86400:
            raise RuntimeError('WEB_SESSION_SECONDS deve estar entre 300 e 86400.')
        enabled = os.getenv('WEB_INSPECTIONS_ENABLED', 'false').lower()
        if enabled not in ('true', 'false'):
            raise RuntimeError('WEB_INSPECTIONS_ENABLED deve ser true ou false.')
        lease_seconds = int(os.getenv('WEB_INSPECTION_LEASE_SECONDS', '28800'))
        if not 900 <= lease_seconds <= 86400:
            raise RuntimeError('WEB_INSPECTION_LEASE_SECONDS deve estar entre 900 e 86400.')
        maximum = int(os.getenv('WEB_MAX_DEVICES_PER_USER', '5'))
        if not 1 <= maximum <= 100:
            raise RuntimeError('WEB_MAX_DEVICES_PER_USER deve estar entre 1 e 100.')
        device_api = os.getenv('WEB_DEVICE_API_BASE_URL', '').strip().rstrip('/') or None
        if device_api:
            parsed = urlsplit(device_api)
            if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                    or parsed.path or parsed.query or parsed.fragment):
                raise RuntimeError('WEB_DEVICE_API_BASE_URL exige somente uma origem HTTPS.')
        gemini_enabled = os.getenv('WEB_GEMINI_ENABLED', 'false').lower()
        if gemini_enabled not in ('true', 'false'):
            raise RuntimeError('WEB_GEMINI_ENABLED deve ser true ou false.')
        gemini_model = os.getenv('GEMINI_MODEL', 'gemini-3.8-flash').strip()
        if not gemini_model or len(gemini_model) > 100 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._' for c in gemini_model):
            raise RuntimeError('GEMINI_MODEL inválido.')
        inprocess = os.getenv('WEB_GEMINI_INPROCESS', 'false').lower()
        if inprocess not in ('true', 'false'):
            raise RuntimeError('WEB_GEMINI_INPROCESS deve ser true ou false.')
        auto_adopt = os.getenv('WEB_GEMINI_AUTO_ADOPT', 'false').lower()
        if auto_adopt not in ('true', 'false'):
            raise RuntimeError('WEB_GEMINI_AUTO_ADOPT deve ser true ou false.')
        auto_request = os.getenv('WEB_GEMINI_AUTO_REQUEST', 'true').lower()
        if auto_request not in ('true', 'false'):
            raise RuntimeError('WEB_GEMINI_AUTO_REQUEST deve ser true ou false.')
        timeout = int(os.getenv('GEMINI_TIMEOUT_SECONDS', '30'))
        daily = int(os.getenv('GEMINI_DAILY_LIMIT', '50'))
        per_user = int(os.getenv('GEMINI_USER_DAILY_LIMIT', '10'))
        if not 5 <= timeout <= 90 or not 1 <= daily <= 10000 or not 1 <= per_user <= daily:
            raise RuntimeError('Limites Gemini inválidos: timeout 5–90 s, chamadas/dia 1–10000 e limite por conta até o global.')
        return cls(
            database_url, origins, production, seconds, enabled == 'true', lease_seconds,
            maximum, device_api, gemini_enabled == 'true', os.getenv('GEMINI_API_KEY', ''),
            gemini_model, timeout, daily, per_user, inprocess == 'true', auto_adopt == 'true',
            auto_request == 'true',
        )
