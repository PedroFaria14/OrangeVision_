import time
from app.db import init_local
from app.sync import sync_pending
from app.config import SYNC_INTERVAL_SECONDS
from app.logging_config import log

def main():
    init_local()
    log.info("Sincronizador iniciado | intervalo=%ss", SYNC_INTERVAL_SECONDS)
    try:
        while True:
            try:
                counts = sync_pending()
                log.info("Neon: registros sincronizados %s", counts)
            except Exception as exc:
                log.warning("Sem sincronização neste ciclo (%s); dados permanecem no SQLite", type(exc).__name__)
            time.sleep(max(5, SYNC_INTERVAL_SECONDS))
    except KeyboardInterrupt:
        log.info("Sincronizador encerrado pelo usuário")

if __name__ == "__main__":
    main()
