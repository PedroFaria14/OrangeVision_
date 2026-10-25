import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            'timestamp': datetime.now(UTC).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
        }
        for name in ('request_id', 'status', 'duration_ms', 'error_type'):
            if hasattr(record, name):
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
