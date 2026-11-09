"""Integração local, sem Gemini real: PostgreSQL descartável em Docker."""
from .run_device_postgres import main

if __name__ == '__main__':
    raise SystemExit(main(['web_api/tests/test_dual_evaluations_postgres.py']))
