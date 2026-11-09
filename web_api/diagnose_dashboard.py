"""Diagnóstico explícito, somente leitura; não aplica SQL de migration nem exibe conexão."""
import json

from .config import Settings
from .database import connection
from .infrastructure.dashboard_readiness import inspect_dashboard


def main():
    try:
        settings = Settings.load()
        with connection(settings) as db:
            db.execute('SET TRANSACTION READ ONLY')
            report = inspect_dashboard(db, settings.inspections_enabled)
        print(json.dumps(report, ensure_ascii=False))
    except Exception as error:
        print(json.dumps({'status': 'diagnostic_failed', 'error_type': type(error).__name__}))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
