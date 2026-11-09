import json
import logging
from datetime import UTC, datetime

# Campos permitidos nos logs (allowlist): identificadores, estados e números.
# Nunca: chaves, cookies, imagens, texto livre do provedor ou dados pessoais.
AUDIT_FIELDS = (
    'request_id', 'status', 'duration_ms', 'error_type', 'worker_status',
    'job_id', 'sample_id', 'device_id', 'attempt', 'model', 'outcome', 'classification',
    'http_status', 'provider_status', 'reason', 'state', 'algorithm_version',
    'calibration_version', 'published', 'publish_status',
)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            'timestamp': datetime.now(UTC).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
        }
        for name in AUDIT_FIELDS:
            if getattr(record, name, None) is not None:
                data[name] = getattr(record, name)
        return json.dumps(data)


def configure_logging():
    logger = logging.getLogger('orangevision.web')
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
