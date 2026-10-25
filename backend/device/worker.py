import secrets
from datetime import UTC, datetime, timedelta
from threading import Lock
from uuid import UUID, uuid4

from .api import ApiFailure, Offline

CLOCK_TOLERANCE_SECONDS = 30


class ClockFailure(RuntimeError):
    pass


class PairingFailure(RuntimeError):
    """Mensagem operacional controlada, sem valores de credenciais ou códigos."""


def validate_grant(grant, device_id, *, online=False):
    if str(UUID(grant['id'])) != grant['id'] or grant['device_id'] != device_id:
        raise RuntimeError('Resposta de sessão incompatível com o equipamento.')
    if (
        grant.get('state') != 'active'
        or not isinstance(grant.get('authorization_expires_at'), str)
        or not isinstance(grant.get('operator_name'), str)
    ):
        raise RuntimeError('Inspeção não está ativa ou a autorização é incompatível.')
    expiry = datetime.fromisoformat(grant['authorization_expires_at'].replace('Z', '+00:00'))
    if not isinstance(grant.get('started_at'), str):
        raise RuntimeError('Autorização sem referência de início.')
    started = datetime.fromisoformat(grant['started_at'].replace('Z', '+00:00'))
    if started.utcoffset() is None or datetime.now(UTC) < started - timedelta(
        seconds=CLOCK_TOLERANCE_SECONDS
    ):
        raise ClockFailure('Relógio local incompatível; ajuste UTC antes de capturar.')
    if expiry.utcoffset() is None or expiry <= datetime.now(UTC):
        raise RuntimeError('Autorização de inspeção expirada.')
    if online:
        if not isinstance(grant.get('observed_at'), str):
            raise RuntimeError('Resposta sem referência de horário do servidor.')
        observed = datetime.fromisoformat(grant['observed_at'].replace('Z', '+00:00'))
        if (
            observed.utcoffset() is None
            or abs((datetime.now(UTC) - observed).total_seconds()) > CLOCK_TOLERANCE_SECONDS
        ):
            raise ClockFailure('Ajuste UTC/NTP: relógio local difere do servidor.')
    return expiry


class Worker:
    def __init__(self, device_id, store, api, camera=None, vision=None):
        self.device_id, self.store, self.api, self.camera, self.vision = (
            device_id,
            store,
            api,
            camera,
            vision,
        )
        self.busy = Lock()

    def pair(self, code=None):
        if not self.busy.acquire(blocking=False):
            raise RuntimeError('Aguarde a captura terminar antes de trocar operador.')
        try:
            old = self.store.active_grant()
            if old:
                if old.get('state') in ('closing', 'blocked'):
                    raise PairingFailure(
                        'Reconcilie e encerre a autorização local antes de trocar operador.'
                    )
                try:
                    validate_grant(old, self.device_id)
                except RuntimeError:
                    pass
                else:
                    raise PairingFailure('Encerre a sessão local antes de parear outra pessoa.')
            attempt = self.store.pairing_attempt()
            if attempt is None:
                if code is None:
                    raise PairingFailure(
                        'Nenhuma tentativa pendente. Inicie uma inspeção no site e use pair com o novo código.'
                    )
                attempt = {
                    'pairing_code': code,
                    'activation_id': str(uuid4()),
                    'lease_token': secrets.token_urlsafe(32),
                }
                self.store.pairing_attempt(attempt)
            elif code is not None and attempt['pairing_code'] != code:
                raise PairingFailure(
                    'Há pareamento não confirmado. Use pair --resume para recuperar a mesma tentativa ou cancel-pairing para reconciliar seu encerramento.'
                )
            result = self.api.pair(attempt)
            if result.get('state') == 'closing':
                raise PairingFailure(
                    'A sessão aguarda encerramento local. Use cancel-pairing para reconciliar a tentativa antes de iniciar outra.'
                )
            validate_grant(result, self.device_id, online=True)
            grant = {**result, 'lease_token': attempt['lease_token']}
            self.store.save_grant(grant)
            return {
                'id': grant['id'],
                'operator_name': grant['operator_name'],
                'authorization_expires_at': grant['authorization_expires_at'],
            }
        finally:
            self.busy.release()

    def close_inspection(self):
        if not self.busy.acquire(blocking=False):
            raise RuntimeError('Aguarde a captura terminar; ela mantém a sessão original.')
        try:
            grant = self.store.active_grant()
            if not grant:
                return
            result = self.api.closed(grant)
            if result['state'] not in ('closed', 'expired'):
                raise RuntimeError('Encerramento ainda não confirmado.')
            self.store.deactivate(grant['id'])
        finally:
            self.busy.release()

    def cancel_pairing(self):
        if not self.busy.acquire(blocking=False):
            raise RuntimeError('Equipamento ocupado.')
        try:
            attempt = self.store.pairing_attempt()
            if not attempt:
                return
            try:
                result = self.api.pair(attempt)
                if result['state'] in ('active', 'closing'):
                    self.api.closed({**result, 'lease_token': attempt['lease_token']})
            except ApiFailure as exc:
                if exc.status not in (403, 404, 409):
                    raise
            self.store.clear_pairing()
        finally:
            self.busy.release()

    def capture(self, request_id):
        request_id = str(UUID(request_id))
        if not self.busy.acquire(blocking=False):
            raise RuntimeError('Equipamento ocupado; não foi aceita uma segunda captura.')
        job, fresh = None, False
        try:
            grant = self.store.active_grant()
            if not grant:
                raise RuntimeError('Pareie uma sessão autorizada antes de capturar.')
            grant = self._capture_grant(grant)
            job, fresh = self.store.reserve(request_id, grant['id'])
            if not fresh:
                if job['state'] == 'completed':
                    return job['analysis_id']
                raise RuntimeError(
                    'Comando existente não concluído. Não haverá repetição automática da captura.'
                )
            if not self.camera or not self.vision:
                raise RuntimeError('Câmera e calibração precisam estar configuradas.')
            timestamp = datetime.now(UTC).isoformat()
            frame = self.camera.capture()
            self.store.job_state(request_id, 'analyzing')
            result = self.vision.analyze(frame)
            self.store.job_state(request_id, 'recording')
            payload = {
                **result,
                'id': job['analysis_id'],
                'inspection_session_id': job['session_id'],
                'timestamp': timestamp,
            }
            self.store.complete(request_id, payload)
            return job['analysis_id']
        except BaseException as exc:
            if job and fresh:
                self.store.job_state(
                    request_id,
                    'failed' if isinstance(exc, Exception) else 'interrupted',
                    type(exc).__name__,
                )
            raise
        finally:
            self.busy.release()

    def _capture_grant(self, grant):
        # Validade temporal não é recuperada por erro de rede nem por relógio atrasado.
        validate_grant({**grant, 'state': 'active'}, self.device_id)
        try:
            observed = self.api.status(grant)
        except Offline as exc:
            if grant['state'] != 'active':
                raise RuntimeError(
                    'Autorização local bloqueada/encerrando; confirme online.'
                ) from exc
            return grant
        except ApiFailure as exc:
            if exc.status not in (429, 500, 502, 503, 504):
                self.store.update_grant({**grant, 'state': 'blocked'})
                raise
            if grant['state'] != 'active':
                raise RuntimeError('Autorização local não pode ser retomada offline.') from exc
            return grant
        if observed['id'] != grant['id'] or observed['device_id'] != self.device_id:
            raise RuntimeError('Resposta não pertence à autorização local.')
        if observed['state'] in ('closing', 'closed', 'expired'):
            self.store.update_grant({**grant, 'state': observed['state']})
            if observed['state'] == 'closing':
                try:
                    reply = self.api.closed(grant)
                    if reply['state'] not in ('closed', 'expired'):
                        raise RuntimeError('Encerramento local ainda não confirmado.')
                except (Offline, ApiFailure) as exc:
                    raise RuntimeError(
                        'Encerramento observado; confirmação pendente, sem nova captura.'
                    ) from exc
            self.store.deactivate(grant['id'])
            raise RuntimeError('Sessão encerrada; captura bloqueada.')
        validate_grant(observed, self.device_id, online=True)
        updated = {**grant, **observed, 'lease_token': grant['lease_token']}
        self.store.update_grant(updated)
        return updated
