"""Executa a integração de amostras/gráficos somente em PostgreSQL descartável."""
from .run_device_postgres import main

if __name__ == '__main__':
    raise SystemExit(main(['web_api/tests/test_sample_publication_postgres.py']))
