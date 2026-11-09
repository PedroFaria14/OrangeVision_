"""Worker Gemini: processo independente (python -m web_api.gemini_worker [--once])
ou thread dentro da Web API (WEB_GEMINI_INPROCESS=true), sem serviço pago extra."""
import argparse
import logging
import threading

from .config import Settings
from .infrastructure.gemini_jobs import GeminiJobs, process_once
from .infrastructure.gemini_provider import GeminiProvider
from .observability import configure_logging

FATAL = ('provider_credentials', 'model_unavailable', 'provider_request_invalid')
log = logging.getLogger('orangevision.web')


def worker_ready(settings):
    return settings.gemini_enabled and bool(settings.gemini_api_key)


def run_loop(settings, stop=None, *, once=False, jobs=None, provider=None, process=process_once):
    """Processa a fila até `stop` ser sinalizado. Retorna o último status.

    Os jobs ficam no PostgreSQL com lease e token: várias instâncias (ou a API
    reiniciando) não duplicam nem sobrescrevem uma avaliação.
    """
    stop = stop or threading.Event()
    jobs = jobs or GeminiJobs(settings)
    provider = provider or GeminiProvider(settings)
    status = 'idle'
    while not stop.is_set():
        try:
            status = process(jobs, provider)
            log.info('gemini_worker_cycle', extra={'worker_status': status})
            if status in FATAL or once:
                return status
            delay = 5 if status == 'idle' else 1
        except Exception as error:
            log.error('gemini_worker_failed', extra={'error_type': type(error).__name__})
            status = 'failed'
            if once:
                return status
            delay = 10
        stop.wait(delay)
    return status


class InProcessWorker:
    """Thread daemon da Web API; para junto com o processo, sem abrir porta."""

    def __init__(self, settings, **loop_options):
        self.settings, self.loop_options = settings, loop_options
        self.stop_event = threading.Event()
        self.thread = None
        self.status = None

    def _run(self):
        self.status = run_loop(self.settings, self.stop_event, **self.loop_options)
        if self.status in FATAL:
            log.error('gemini_worker_stopped', extra={'worker_status': self.status})

    def start(self):
        self.thread = threading.Thread(target=self._run, name='gemini-worker', daemon=True)
        self.thread.start()
        log.info('gemini_worker_started', extra={'worker_status': 'in_process'})
        return self

    def stop(self, timeout=5):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout)


def start_in_process(settings, **loop_options):
    """Inicia o worker na API somente se pedido e configurado; nunca derruba a API."""
    if not settings.gemini_inprocess:
        return None
    if not worker_ready(settings):
        log.error('gemini_worker_not_started', extra={'worker_status': 'missing_configuration'})
        return None
    return InProcessWorker(settings, **loop_options).start()


def main():
    parser = argparse.ArgumentParser(description='Worker persistente Gemini OrangeVision.')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    configure_logging()
    settings = Settings.load()
    if not worker_ready(settings):
        raise SystemExit('Configure WEB_GEMINI_ENABLED=true e GEMINI_API_KEY no ambiente privado do worker.')
    try:
        status = run_loop(settings, once=args.once)
    except KeyboardInterrupt:
        return
    if status in FATAL:
        raise SystemExit('Confira chave/permissões, modelo ou contrato Gemini e reinicie o worker.')
    if args.once and status == 'failed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
