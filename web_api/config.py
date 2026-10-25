"""Configuração exclusiva do serviço online; nenhum segredo vai para o React."""

import os
from dataclasses import dataclass
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
        return cls(database_url, origins, production, seconds, enabled == 'true', lease_seconds)
