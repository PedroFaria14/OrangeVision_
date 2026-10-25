import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL', '')
SQLITE_PATH = Path(os.getenv('SQLITE_PATH', './data/orangevision_local.db'))
API_KEY = os.getenv('API_KEY', '')
CORS_ORIGINS = [s.strip() for s in os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',') if s.strip()]
SYNC_INTERVAL_SECONDS = int(os.getenv('SYNC_INTERVAL_SECONDS', '30'))

if not API_KEY or API_KEY.startswith('SUBSTITUA_'):
    raise RuntimeError('Configure API_KEY no .env antes de iniciar.')
