import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from dotenv import load_dotenv


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
    def load(cls):
        load_dotenv(Path(__file__).parent / '.env', override=False)
        device_id = str(UUID(os.environ['DEVICE_ID']))
        url = os.environ['WEB_API_BASE_URL'].rstrip('/')
        parsed = urlsplit(url)
        local_http = os.getenv(
            'ALLOW_INSECURE_LOCAL_API', 'false'
        ) == 'true' and parsed.hostname in ('localhost', '127.0.0.1')
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and local_http):
            raise RuntimeError('API exige HTTPS; HTTP local precisa de autorização explícita.')
        if (
            not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in ('', '/')
        ):
            raise RuntimeError('WEB_API_BASE_URL exige somente a origem da API.')
        credential = os.environ['DEVICE_INGEST_CREDENTIAL']
        if len(credential) < 32:
            raise RuntimeError('Configure a credencial real do equipamento.')
        base = Path(__file__).parent
        raw_database = Path(os.getenv('DEVICE_SQLITE_PATH', 'data/device_pipeline.db'))
        database = (raw_database if raw_database.is_absolute() else base / raw_database).resolve()
        calibration = os.getenv('CALIBRATION_PATH', '')
        width, height = int(os.getenv('CAMERA_WIDTH', '0')), int(os.getenv('CAMERA_HEIGHT', '0'))
        if width < 0 or height < 0 or width * height > 16000000:
            raise RuntimeError('Resolução fora do limite de memória configurado.')
        return cls(
            device_id,
            url,
            credential,
            database,
            base / 'data' / 'camera.worker.lock',
            (
                (
                    Path(calibration) if Path(calibration).is_absolute() else base / calibration
                ).resolve()
                if calibration
                else None
            ),
            os.getenv('CAMERA_ADAPTER', ''),
            int(os.getenv('CAMERA_INDEX', '0')),
            width,
            height,
        )
