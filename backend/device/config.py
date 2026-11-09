import io
import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from dotenv import dotenv_values

CONFIG_PATH = Path(__file__).parent / '.env'
CONNECTION_KEYS = ('DEVICE_ID', 'WEB_API_BASE_URL', 'DEVICE_INGEST_CREDENTIAL')


class ConfigurationError(RuntimeError):
    pass


def local_values(path=None):
    return dict(dotenv_values(stream=io.StringIO(read_local_text(path)), interpolate=False))


def read_local_text(path=None):
    path = path or CONFIG_PATH
    if path.is_symlink():
        raise ConfigurationError('A configuração local não pode ser um link simbólico.')
    try:
        descriptor = os.open(
            path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
        )
    except FileNotFoundError:
        return ''
    except OSError:
        raise ConfigurationError('Não foi possível ler o arquivo local com segurança. Verifique acesso e links simbólicos.') from None
    with os.fdopen(descriptor, encoding='utf-8', newline='') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ConfigurationError('A configuração local deve ser um arquivo regular, não um link ou dispositivo.')
        return stream.read()


def effective_values(path=None):
    # Não copiar o .env para os.environ: isso confundiria valores herdados com
    # valores locais e impediria a rotação de credencial no mesmo processo.
    return {**local_values(path), **os.environ}


def validate_device_id(value):
    try:
        identity = UUID(value or '')
    except (ValueError, TypeError, AttributeError):
        raise ConfigurationError('DEVICE_ID deve ser o UUID emitido em Equipamentos no site.') from None
    if identity.int == 0:
        raise ConfigurationError('DEVICE_ID não pode ser o UUID nulo.')
    return str(identity)


def validate_api_origin(value, *, allow_local=False):
    try:
        if not value or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError
        parsed = urlsplit(value)
        local = allow_local and parsed.hostname in ('localhost', '127.0.0.1')
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and local):
            raise ValueError
        if (
            not parsed.hostname or parsed.username is not None or parsed.password is not None
            or '?' in value or '#' in value or parsed.path not in ('', '/')
            or parsed.port == 0 or parsed.netloc.endswith(':') or '\\' in value
        ):
            raise ValueError
        # Validar o host sem DNS e normalizar origens equivalentes.
        host = parsed.hostname.encode('idna').decode('ascii').lower().rstrip('.')
        if ':' in host:
            from ipaddress import IPv6Address
            host = '[' + str(IPv6Address(host)) + ']'
        elif len(host) > 253 or any(
            re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) is None
            for label in host.split('.')
        ):
            raise ValueError
        port = parsed.port
        if port is not None and port != (443 if parsed.scheme == 'https' else 80):
            host += f':{port}'
        return f'{parsed.scheme}://{host}'
    except (ValueError, TypeError, UnicodeError, AttributeError):
        raise ConfigurationError(
            'WEB_API_BASE_URL deve ser a origem HTTPS da API, sem /api, /docs, '
            'usuário, consulta ou fragmento.'
        ) from None


def validate_credential(value):
    if (
        not isinstance(value, str) or not 32 <= len(value) <= 4096
        or value.startswith(('SUBSTITUA_', 'YOUR_', 'CHANGE_ME'))
        or re.fullmatch(r'[A-Za-z0-9._~+/\-]+=*', value) is None
    ):
        raise ConfigurationError(
            'DEVICE_INGEST_CREDENTIAL deve ser a credencial privada completa emitida pelo site '
            '(sem o prefixo Bearer).'
        )
    return value


def connection_values(values):
    return {
        'DEVICE_ID': validate_device_id(values.get('DEVICE_ID')),
        'WEB_API_BASE_URL': validate_api_origin(
            values.get('WEB_API_BASE_URL'),
            allow_local=values.get('ALLOW_INSECURE_LOCAL_API') == 'true',
        ),
        'DEVICE_INGEST_CREDENTIAL': validate_credential(values.get('DEVICE_INGEST_CREDENTIAL')),
    }


@dataclass(frozen=True)
class DeviceSettings:
    device_id: str
    api_url: str
    credential: str = field(repr=False)
    database: Path
    lock_path: Path
    calibration_path: Path | None
    camera_adapter: str
    camera_index: int
    width: int
    height: int

    @classmethod
    def load(cls, *, window=False):
        from .provisioning import ensure_configuration, guard_identity

        values = ensure_configuration(window=window)
        connection = connection_values(values)
        guard_identity(values)
        base = CONFIG_PATH.parent
        raw_database = Path(values.get('DEVICE_SQLITE_PATH') or 'data/device_pipeline.db')
        database = (raw_database if raw_database.is_absolute() else base / raw_database).resolve()
        calibration = values.get('CALIBRATION_PATH', '')
        try:
            width, height = int(values.get('CAMERA_WIDTH') or '0'), int(values.get('CAMERA_HEIGHT') or '0')
            camera_index = int(values.get('CAMERA_INDEX') or '0')
        except ValueError:
            raise ConfigurationError('CAMERA_WIDTH, CAMERA_HEIGHT e CAMERA_INDEX exigem inteiros.') from None
        if width < 0 or height < 0 or width * height > 16000000:
            raise RuntimeError('Resolução fora do limite de memória configurado.')
        return cls(
            connection['DEVICE_ID'],
            connection['WEB_API_BASE_URL'],
            connection['DEVICE_INGEST_CREDENTIAL'],
            database,
            base / 'data' / 'camera.worker.lock',
            (
                (
                    Path(calibration) if Path(calibration).is_absolute() else base / calibration
                ).resolve()
                if calibration
                else None
            ),
            values.get('CAMERA_ADAPTER') or '',
            camera_index,
            width,
            height,
        )
