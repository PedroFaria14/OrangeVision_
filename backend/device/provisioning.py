"""Configuração local, sem rede, cadastro remoto, captura ou consumo de trabalhos."""

import getpass
import io
import json
import os
import sqlite3
import sys
import tempfile
import warnings
from contextlib import closing
from pathlib import Path

from dotenv.parser import parse_stream

from . import config
from .config import (
    CONNECTION_KEYS,
    ConfigurationError,
    connection_values,
    effective_values,
    local_values,
    read_local_text,
    validate_api_origin,
    validate_credential,
    validate_device_id,
)
from .locking import device_lock

GUIDANCE = 'Execute app/.venv/bin/python3 -m device configure em um terminal interativo.'
UNCONFIRMED = 'Autenticação ainda não confirmada; não foi feita nenhuma chamada à API.'


class ConfigurationCancelled(ConfigurationError):
    pass


class TerminalPrompts:
    def ask(self, text, *, secret=False):
        if secret:
            # getpass não pode cair silenciosamente para entrada com eco.
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                try:
                    return getpass.getpass(text).strip()
                except getpass.GetPassWarning:
                    raise ConfigurationError('Não foi possível ocultar a credencial neste terminal.') from None
        return input(text).strip()

    def tell(self, text):
        print(text)


class WindowPrompts:
    """Reusa Tkinter, como o diálogo de sessão; nunca cria servidor web."""
    def __enter__(self):
        try:
            import tkinter as tk
            from tkinter import messagebox, simpledialog
            self.root = tk.Tk()
            self.root.withdraw()
        except Exception:
            raise ConfigurationError('Não foi possível abrir o assistente local. ' + GUIDANCE) from None
        self.messagebox, self.simpledialog = messagebox, simpledialog
        return self

    def __exit__(self, *args):
        self.root.destroy()

    def ask(self, text, *, secret=False):
        value = self.simpledialog.askstring(
            'Configurar equipamento OrangeVision', text, parent=self.root,
            **({'show': '*'} if secret else {}),
        )
        if value is None:
            raise ConfigurationCancelled('Configuração cancelada; nenhum valor foi gravado.')
        return value.strip()

    def tell(self, text):
        self.messagebox.showinfo('Configuração OrangeVision', text, parent=self.root)


def interactive():
    return bool(sys.stdin and sys.stdin.isatty())


def _read_text(path):
    return read_local_text(path)


def _render(text, changes):
    remaining = dict(changes)
    parts = []
    for binding in parse_stream(io.StringIO(text)):
        if binding.key in changes:
            if binding.key in remaining:
                value = remaining.pop(binding.key).replace('\\', '\\\\').replace("'", "\\'")
                parts.append(f"{binding.key}='{value}'\n")
            # Duplicatas da mesma chave também são substituídas, não ficam ativas.
        else:
            parts.append(binding.original.string)
    result = ''.join(parts)
    if remaining and result and not result.endswith(('\n', '\r')):
        result += '\n'
    for key, value in remaining.items():
        value = value.replace('\\', '\\\\').replace("'", "\\'")
        result += f"{key}='{value}'\n"
    return result


def atomic_save(path, changes, original):
    if _read_text(path) != original:
        raise ConfigurationError('Configuração alterada por outro processo. Execute o assistente novamente.')
    descriptor, temporary = tempfile.mkstemp(prefix='.env-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='') as stream:
            os.chmod(temporary, 0o600)
            stream.write(_render(original, changes))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != 'nt':
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def database_path(values):
    raw = Path(values.get('DEVICE_SQLITE_PATH') or 'data/device_pipeline.db')
    return (raw if raw.is_absolute() else config.CONFIG_PATH.parent / raw).resolve()


def guard_identity(values):
    """Checagem somente leitura, inclusive de instalações anteriores sem binding."""
    identity = validate_device_id(values.get('DEVICE_ID'))
    origin = validate_api_origin(
        values.get('WEB_API_BASE_URL'),
        allow_local=values.get('ALLOW_INSECURE_LOCAL_API') == 'true',
    )
    saved = local_values()
    for key, validator, selected in (
        ('DEVICE_ID', validate_device_id, identity),
        ('WEB_API_BASE_URL', lambda value: validate_api_origin(
            value, allow_local=values.get('ALLOW_INSECURE_LOCAL_API') == 'true'
        ), origin),
    ):
        try:
            previous = validator(saved.get(key))
        except ConfigurationError:
            continue
        if previous != selected:
            raise ConfigurationError(
                f'{key} difere da configuração local. Troca de identidade/API bloqueada; '
                'use a configuração original para preservar sessões e pendências.'
            )
    assert_database_identity(database_path(values), identity, origin)


def assert_database_identity(path, identity, origin):
    if not path.exists():
        return
    try:
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'device_identity' in tables:
                binding = db.execute('SELECT device_id,api_origin FROM device_identity WHERE singleton=1').fetchone()
                if binding and binding != (identity, origin):
                    raise ConfigurationError('SQLite pertence a outro equipamento ou API. Operação bloqueada.')
            if 'analises' in tables:
                raise ConfigurationError('Banco legado não pode ser usado como SQLite do dispositivo.')
            if 'grants' in tables:
                for (content,) in db.execute('SELECT data FROM grants'):
                    grant = json.loads(content)
                    if validate_device_id(grant.get('device_id')) != identity:
                        raise ConfigurationError('Histórico pertence a outro equipamento. Operação bloqueada.')
            # Um pareamento pendente sem referência de identidade não pode ser migrado às cegas.
            if 'pairing_attempt' in tables and db.execute('SELECT 1 FROM pairing_attempt LIMIT 1').fetchone():
                bound = 'device_identity' in tables and db.execute('SELECT 1 FROM device_identity').fetchone()
                original = local_values().get('DEVICE_ID')
                if not bound and validate_device_id(original) != identity:
                    raise ConfigurationError('Recupere a identidade original antes de retomar o pareamento.')
    except (sqlite3.Error, ValueError, KeyError, TypeError):
        raise ConfigurationError('Não foi possível conferir a identidade do SQLite. Nenhum dado foi alterado.') from None


def configure(*, rotate=False, prompts=None):
    if not interactive():
        raise ConfigurationError('Sem terminal interativo; nenhuma pergunta será feita. ' + GUIDANCE)
    prompts = prompts or TerminalPrompts()
    path = config.CONFIG_PATH
    with device_lock(path.with_name('.configuration.lock')):
        original = _read_text(path)
        values = effective_values()
        changes = {}
        try:
            if rotate:
                if 'DEVICE_INGEST_CREDENTIAL' in os.environ:
                    raise ConfigurationError(
                        'A credencial vem do ambiente e tem precedência. Atualize-a na origem '
                        'do ambiente ou remova essa variável antes de usar update-credential.'
                    )
                validate_device_id(values.get('DEVICE_ID'))
                validate_api_origin(values.get('WEB_API_BASE_URL'), allow_local=values.get('ALLOW_INSECURE_LOCAL_API') == 'true')
                guard_identity(values)
                keys = ('DEVICE_INGEST_CREDENTIAL',)
            else:
                keys = CONNECTION_KEYS
            prompts.tell(
                'Use os dados do equipamento já cadastrado no site, em Equipamentos. '
                'Este assistente não cria equipamento, UUID ou inspeção. '
                'Cancele com Ctrl+C ou digite cancelar; nada será salvo parcialmente.'
            )
            validators = {
                'DEVICE_ID': validate_device_id,
                'WEB_API_BASE_URL': lambda value: validate_api_origin(
                    value, allow_local=values.get('ALLOW_INSECURE_LOCAL_API') == 'true'
                ),
                'DEVICE_INGEST_CREDENTIAL': validate_credential,
            }
            explanations = {
                'DEVICE_ID': 'DEVICE_ID — UUID fornecido pelo site, não gere outro: ',
                'WEB_API_BASE_URL': 'WEB_API_BASE_URL — origem HTTPS da API, sem /api ou /docs: ',
                'DEVICE_INGEST_CREDENTIAL': 'DEVICE_INGEST_CREDENTIAL — credencial privada do site (oculta, sem Bearer): ',
            }
            for key in keys:
                validator = validators[key]
                if not rotate:
                    try:
                        validator(values.get(key))
                        continue
                    except ConfigurationError:
                        if key in os.environ:
                            raise ConfigurationError(f'{key} inválida no ambiente. Corrija a variável na origem.') from None
                while True:
                    answer = prompts.ask(explanations[key], secret=key == 'DEVICE_INGEST_CREDENTIAL')
                    if answer.lower() == 'cancelar':
                        raise ConfigurationCancelled('Configuração cancelada; nenhum valor foi gravado.')
                    try:
                        changes[key] = validator(answer)
                    except ConfigurationError as exc:
                        prompts.tell(str(exc))
                    else:
                        values[key] = changes[key]
                        break
            connection_values(values)
            guard_identity(values)
            if changes:
                # Persistir também campos completos vindos do ambiente no primeiro uso.
                updates = changes if rotate else connection_values(values)
                atomic_save(path, updates, original)
                prompts.tell('Configuração salva com permissões privadas. ' + UNCONFIRMED)
            else:
                prompts.tell('Configuração existente reutilizada. ' + UNCONFIRMED)
            if rotate:
                prompts.tell('Credencial atualizada. Reinicie os executores; identidade e histórico preservados.')
            return effective_values()
        except (EOFError, KeyboardInterrupt):
            raise ConfigurationCancelled('Configuração cancelada; nenhum valor foi gravado.') from None


def ensure_configuration(*, window=False):
    values = effective_values()
    try:
        connection_values(values)
    except ConfigurationError:
        if not interactive():
            raise ConfigurationError('Configuração ausente ou inválida. ' + GUIDANCE) from None
        if window:
            with WindowPrompts() as prompts:
                return configure(prompts=prompts)
        return configure()
    return values
