import getpass
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
import requests
from backend.device import __main__ as cli
from backend.device import config, provisioning
from backend.device.api import ApiFailure, DeviceApi, Offline, connection_guidance
from backend.device.config import ConfigurationError, DeviceSettings, connection_values
from backend.device.storage import Store

IDENTITY = '3463e012-1fc6-4473-89f3-cdbf88ec5f5a'
ORIGIN = 'https://api.example.test'
CREDENTIAL = 'synthetic-private-credential-for-tests-only-0001'
ROTATED = 'synthetic-private-credential-for-tests-only-0002'


class Prompts:
    def __init__(self, answers=()):
        self.answers = iter(answers)
        self.questions = []
        self.messages = []

    def ask(self, text, *, secret=False):
        self.questions.append((text, secret))
        answer = next(self.answers)
        if isinstance(answer, BaseException):
            raise answer
        return answer

    def tell(self, text):
        self.messages.append(text)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    path = tmp_path / 'device' / '.env'
    path.parent.mkdir()
    monkeypatch.setattr(config, 'CONFIG_PATH', path)
    for key in (*config.CONNECTION_KEYS, 'DEVICE_SQLITE_PATH', 'CAMERA_ADAPTER', 'CAMERA_INDEX',
                'CAMERA_WIDTH', 'CAMERA_HEIGHT', 'CALIBRATION_PATH', 'ALLOW_INSECURE_LOCAL_API'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(provisioning, 'interactive', lambda: True)

    def forbidden(*args, **kwargs):
        pytest.fail('Configurar não pode acessar rede, câmera, pareamento ou trabalhos.')

    monkeypatch.setattr(requests.sessions.Session, 'request', forbidden)
    monkeypatch.setattr(requests.sessions.Session, 'post', forbidden)
    monkeypatch.setattr(requests.sessions.Session, 'get', forbidden)
    return path


def write_config(path, *, credential=CREDENTIAL, identity=IDENTITY, origin=ORIGIN, extra=''):
    path.write_text(
        f'DEVICE_ID={identity}\nWEB_API_BASE_URL={origin}\n'
        f'DEVICE_INGEST_CREDENTIAL={credential}\n' + extra
    )


def test_first_use_saves_private_configuration_without_side_effects(isolated):
    prompts = Prompts([IDENTITY, ORIGIN + '/', CREDENTIAL])
    values = provisioning.configure(prompts=prompts)
    assert connection_values(values) == {
        'DEVICE_ID': IDENTITY, 'WEB_API_BASE_URL': ORIGIN,
        'DEVICE_INGEST_CREDENTIAL': CREDENTIAL,
    }
    assert [secret for _, secret in prompts.questions] == [False, False, True]
    assert stat.S_IMODE(isolated.stat().st_mode) == 0o600
    assert not (isolated.parent / 'data').exists()
    assert 'Autenticação ainda não confirmada' in prompts.messages[-1]
    assert CREDENTIAL not in '\n'.join(prompts.messages)
    assert not list(isolated.parent.glob('.env-*'))


def test_complete_configuration_is_reused_without_tty_or_questions(isolated, monkeypatch):
    write_config(isolated, extra='CAMERA_WIDTH=640\nCAMERA_HEIGHT=480\n')
    original = isolated.read_bytes()
    monkeypatch.setattr(provisioning, 'interactive', lambda: False)
    settings = DeviceSettings.load()
    assert settings.device_id == IDENTITY and settings.api_url == ORIGIN
    assert settings.width == 640 and settings.height == 480
    assert settings.database == isolated.parent / 'data/device_pipeline.db'
    assert settings.credential == CREDENTIAL
    assert CREDENTIAL not in repr(settings)
    assert isolated.read_bytes() == original
    assert not (isolated.parent / 'data').exists()


def test_incomplete_file_preserves_unrelated_settings_and_comments(isolated):
    original = (
        '# camera e banco existentes\nCAMERA_ADAPTER=usb\nCAMERA_WIDTH=640\n'
        'CAMERA_HEIGHT=480\nDEVICE_SQLITE_PATH=data/custom.db\n'
        "MODEL_CUSTOM='modelo-local.onnx'\nCALIBRATION_PATH=calibration/real.json\n"
        f'DEVICE_ID={IDENTITY}\nWEB_API_BASE_URL={ORIGIN}\n'
    )
    isolated.write_text(original)
    prompts = Prompts([CREDENTIAL])
    provisioning.configure(prompts=prompts)
    assert len(prompts.questions) == 1 and prompts.questions[0][1]
    for line in original.splitlines():
        if not line.startswith(('DEVICE_ID=', 'WEB_API_BASE_URL=')):
            assert line in isolated.read_text()
    assert config.local_values()['DEVICE_SQLITE_PATH'] == 'data/custom.db'


@pytest.mark.parametrize('cancel', ['cancelar', EOFError(), KeyboardInterrupt()])
@pytest.mark.parametrize('existing', [False, True])
def test_cancel_never_saves_partial_values(isolated, cancel, existing):
    if existing:
        isolated.write_text('# preservar\nCAMERA_WIDTH=640\n')
    original = isolated.read_bytes() if existing else None
    with pytest.raises(provisioning.ConfigurationCancelled):
        provisioning.configure(prompts=Prompts([IDENTITY, ORIGIN, cancel]))
    assert (isolated.read_bytes() if isolated.exists() else None) == original
    assert not list(isolated.parent.glob('.env-*'))


def test_invalid_answers_are_explained_without_echoing_the_secret(isolated):
    bad_secret = 'private invalid secret must not appear'
    prompts = Prompts(['invalid-uuid', IDENTITY, 'https://api.example.test/api', ORIGIN,
                       bad_secret, CREDENTIAL])
    provisioning.configure(prompts=prompts)
    messages = '\n'.join(prompts.messages)
    assert 'UUID' in messages and 'sem /api' in messages and 'credencial privada completa' in messages
    assert bad_secret not in messages and CREDENTIAL not in messages


@pytest.mark.parametrize('url', [
    'http://api.example.test', 'https://api.example.test/api', 'https://api.example.test/docs',
    'https://user:password@api.example.test', 'https://api.example.test?x=1',
    'https://api.example.test#fragment', 'https://api.example.test?',
    'https://api.example.test:99999', 'https://api.example.test:',
    'https://bad%host', 'https://-bad.example.test', 'https://api.example.test\\evil',
    'https://api.example.test\n', '',
])
def test_invalid_api_origins_are_rejected(url):
    with pytest.raises(ConfigurationError):
        config.validate_api_origin(url)


def test_equivalent_origin_and_uuid_are_normalized():
    assert config.validate_api_origin('HTTPS://API.EXAMPLE.TEST:443/') == ORIGIN
    assert config.validate_device_id(IDENTITY.upper()) == IDENTITY
    with pytest.raises(ConfigurationError):
        config.validate_device_id('00000000-0000-0000-0000-000000000000')


def test_credential_rotation_preserves_identity_database_sessions_and_outbox(isolated):
    write_config(isolated, extra='CAMERA_WIDTH=640\nMODEL_CUSTOM=local.onnx\n')
    store = Store(provisioning.database_path(config.effective_values()))
    store.initialize()
    store.bind_device(IDENTITY, ORIGIN)
    grant = {'id': str(uuid4()), 'device_id': IDENTITY, 'lease_token': 'test-only-lease'}
    store.save_grant(grant)
    store.pairing_attempt({'pairing_code': 'test-only-code'})
    store.save_camera_sample(str(uuid4()), grant['id'], 'test-stamp', b'pending-photo')
    store.save_photo_draft(str(uuid4()), 'test-stamp', b'draft-photo', {}, grant)
    with store.db() as db:
        before = list(db.iterdump())
    prompts = Prompts([ROTATED])
    provisioning.configure(rotate=True, prompts=prompts)
    with store.db() as db:
        assert list(db.iterdump()) == before
    assert store.active_grant() == grant
    assert store.camera_sample_counts() == {'pending': 1}
    assert len(prompts.questions) == 1 and prompts.questions[0][1]
    values = config.local_values()
    assert values['DEVICE_ID'] == IDENTITY and values['WEB_API_BASE_URL'] == ORIGIN
    assert values['DEVICE_INGEST_CREDENTIAL'] == ROTATED
    assert values['MODEL_CUSTOM'] == 'local.onnx'


def test_environment_has_precedence_but_rotation_does_not_save_unused_secret(isolated, monkeypatch):
    write_config(isolated)
    monkeypatch.setenv('DEVICE_INGEST_CREDENTIAL', ROTATED)
    assert DeviceSettings.load().credential == ROTATED
    before = isolated.read_bytes()
    prompts = Prompts()
    with pytest.raises(ConfigurationError, match='precedência'):
        provisioning.configure(rotate=True, prompts=prompts)
    assert not prompts.questions and isolated.read_bytes() == before


@pytest.mark.parametrize('key,value', [('DEVICE_ID', str(uuid4())),
                                      ('WEB_API_BASE_URL', 'https://another-api.example.test')])
def test_environment_cannot_silently_change_identity_or_api(isolated, monkeypatch, key, value):
    write_config(isolated)
    before = isolated.read_bytes()
    monkeypatch.setenv(key, value)
    with pytest.raises(ConfigurationError, match='bloqueada'):
        DeviceSettings.load()
    assert isolated.read_bytes() == before


def test_sqlite_binding_blocks_new_device_even_if_env_file_was_replaced(isolated):
    write_config(isolated)
    path = provisioning.database_path(config.effective_values())
    store = Store(path)
    store.initialize()
    store.bind_device(IDENTITY, ORIGIN)
    write_config(isolated, identity=str(uuid4()))
    with pytest.raises(ConfigurationError, match='outro equipamento'):
        DeviceSettings.load()
    with store.db() as db:
        assert db.execute('SELECT device_id FROM device_identity').fetchone()[0] == IDENTITY


def test_legacy_history_of_another_device_is_never_reassigned(isolated):
    write_config(isolated)
    store = Store(provisioning.database_path(config.effective_values()))
    store.initialize()
    grant = {'id': str(uuid4()), 'device_id': str(uuid4())}
    store.save_grant(grant)
    store.save_camera_sample(str(uuid4()), grant['id'], 'stamp', b'original-photo')
    with pytest.raises(ConfigurationError, match='outro equipamento'):
        DeviceSettings.load()
    assert store.active_grant() == grant
    assert store.pending_camera_samples()[0]['image'] == b'original-photo'


def test_noninteractive_missing_configuration_does_not_wait_or_open_window(isolated, monkeypatch):
    monkeypatch.setattr(provisioning, 'interactive', lambda: False)
    monkeypatch.setattr(provisioning, 'WindowPrompts', lambda: pytest.fail('No GUI when unattended.'))
    with pytest.raises(ConfigurationError, match='device configure'):
        DeviceSettings.load(window=True)
    assert not isolated.exists()
    assert not (isolated.parent / 'data').exists()


@pytest.mark.parametrize('command', ['configure', 'update-credential'])
def test_explicit_configuration_commands_do_not_create_api_or_camera(isolated, monkeypatch, command):
    write_config(isolated)
    monkeypatch.setattr(cli, 'DeviceApi', lambda _: pytest.fail('No API during configuration.'))
    monkeypatch.setattr(cli, 'Store', lambda _: pytest.fail('No SQLite initialization during configuration.'))
    prompts = Prompts([ROTATED] if command == 'update-credential' else [])
    monkeypatch.setattr(provisioning, 'TerminalPrompts', lambda: prompts)
    monkeypatch.setattr('sys.argv', ['device', command])
    cli.main()
    assert not (isolated.parent / 'data').exists()


def test_failed_atomic_replace_keeps_original_and_removes_temporary_file(isolated, monkeypatch):
    write_config(isolated)
    before = isolated.read_bytes()

    def failed(*args):
        raise OSError('synthetic disk error')

    monkeypatch.setattr(provisioning.os, 'replace', failed)
    with pytest.raises(OSError):
        provisioning.configure(rotate=True, prompts=Prompts([ROTATED]))
    assert isolated.read_bytes() == before
    assert not list(isolated.parent.glob('.env-*'))


def test_duplicate_credentials_are_removed_without_touching_other_entries(isolated):
    write_config(isolated, extra=f'DEVICE_INGEST_CREDENTIAL={CREDENTIAL}\nCAMERA_INDEX=2\n')
    provisioning.configure(rotate=True, prompts=Prompts([ROTATED]))
    assert isolated.read_text().count('DEVICE_INGEST_CREDENTIAL=') == 1
    assert config.local_values()['CAMERA_INDEX'] == '2'


def test_terminal_credential_uses_getpass_and_never_falls_back_to_echo(monkeypatch):
    asked = []
    monkeypatch.setattr(provisioning.getpass, 'getpass', lambda text: asked.append(text) or CREDENTIAL)
    assert provisioning.TerminalPrompts().ask('credential', secret=True) == CREDENTIAL
    assert asked == ['credential']

    def warning(text):
        import warnings
        warnings.warn('no hidden input', getpass.GetPassWarning, stacklevel=2)

    monkeypatch.setattr(provisioning.getpass, 'getpass', warning)
    with pytest.raises(ConfigurationError, match='ocultar'):
        provisioning.TerminalPrompts().ask('credential', secret=True)


@pytest.mark.parametrize('failure,label', [
    (Offline('private-detail'), 'rede'), (ApiFailure(503), 'indisponível'),
    (ApiFailure(401), 'Credencial recusada'), (ApiFailure(403), 'Permissão recusada'),
])
def test_runtime_failures_preserve_configuration_without_reprompt(isolated, monkeypatch, failure, label):
    write_config(isolated)
    settings = DeviceSettings.load()
    before = isolated.read_bytes()
    monkeypatch.setattr(provisioning, 'configure', lambda **k: pytest.fail('Network failure is not onboarding.'))
    api = DeviceApi(settings)

    def failed(*args, **kwargs):
        raise failure

    monkeypatch.setattr(api.http, 'request', failed)
    with pytest.raises(type(failure)):
        api.status({'id': str(uuid4()), 'lease_token': 'test-only'})
    message = connection_guidance(failure)
    assert label in message
    assert 'private-detail' not in message and CREDENTIAL not in message
    assert DeviceSettings.load().credential == CREDENTIAL
    assert isolated.read_bytes() == before
    assert api.http.verify is True
    assert api.http.headers['Authorization'] == 'Bearer ' + CREDENTIAL
    api.close()


def test_invalid_environment_is_not_overwritten_by_wizard(isolated, monkeypatch):
    write_config(isolated)
    before = isolated.read_bytes()
    monkeypatch.setenv('DEVICE_INGEST_CREDENTIAL', 'invalid-secret')
    with pytest.raises(ConfigurationError, match='ambiente'):
        provisioning.configure(prompts=Prompts())
    assert isolated.read_bytes() == before


def test_symbolic_link_configuration_is_not_read_or_overwritten(isolated):
    target = isolated.with_name('private-source')
    write_config(target)
    before = target.read_bytes()
    isolated.symlink_to(target)
    with pytest.raises(ConfigurationError):
        provisioning.configure(rotate=True, prompts=Prompts([ROTATED]))
    assert target.read_bytes() == before


def test_window_bootstrap_uses_existing_local_dialog_with_hidden_credential(isolated, monkeypatch):
    import sys

    calls = []
    answers = iter([IDENTITY, ORIGIN, CREDENTIAL])
    root = SimpleNamespace(withdraw=lambda: None, destroy=lambda: calls.append('destroyed'))
    tkinter = SimpleNamespace(
        Tk=lambda: root,
        messagebox=SimpleNamespace(showinfo=lambda *a, **k: None),
        simpledialog=SimpleNamespace(askstring=lambda *a, **k: calls.append(k) or next(answers)),
    )
    monkeypatch.setitem(sys.modules, 'tkinter', tkinter)
    settings = DeviceSettings.load(window=True)
    assert settings.device_id == IDENTITY
    assert [call.get('show') for call in calls if isinstance(call, dict)] == [None, None, '*']
    assert calls[-1] == 'destroyed'


def test_configure_if_needed_is_noninteractive_and_does_not_claim_connected(
    isolated, monkeypatch, capsys
):
    write_config(isolated)
    monkeypatch.setattr(provisioning, 'interactive', lambda: False)
    monkeypatch.setattr(cli, 'DeviceApi', lambda _: pytest.fail('No API during local check.'))
    monkeypatch.setattr('sys.argv', ['device', 'configure', '--if-needed'])
    cli.main()
    output = capsys.readouterr().out
    assert 'Autenticação ainda não confirmada' in output
    assert 'conectado' not in output.lower() and CREDENTIAL not in output
    assert not (isolated.parent / 'data').exists()


def test_noninteractive_startup_explains_missing_configuration_without_initializing_db(
    isolated, monkeypatch, capsys
):
    monkeypatch.setattr(provisioning, 'interactive', lambda: False)
    monkeypatch.setattr('sys.argv', ['device', 'status'])
    monkeypatch.setattr(cli, 'DeviceApi', lambda _: pytest.fail('No API when config is missing.'))
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1
    assert 'device configure' in capsys.readouterr().out
    assert not isolated.exists() and not (isolated.parent / 'data').exists()


def test_private_credential_is_not_echoed_by_auth_failure_response(isolated, monkeypatch):
    write_config(isolated)
    api = DeviceApi(DeviceSettings.load())
    captured = []

    def rejected(*args, **kwargs):
        captured.append(kwargs)
        return SimpleNamespace(status_code=401, headers={}, text=CREDENTIAL)

    monkeypatch.setattr(api.http, 'request', rejected)
    with pytest.raises(ApiFailure) as exc:
        api.status({'id': str(uuid4()), 'lease_token': 'test-only'})
    assert 'Credencial recusada' in connection_guidance(exc.value)
    assert CREDENTIAL not in str(exc.value)
    assert captured[0].get('verify', True) is True
    api.close()


def test_camera_environment_settings_keep_precedence(isolated, monkeypatch):
    write_config(isolated, extra='CAMERA_WIDTH=640\nCAMERA_HEIGHT=480\n')
    monkeypatch.setenv('CAMERA_WIDTH', '320')
    assert DeviceSettings.load().width == 320
    assert config.local_values()['CAMERA_WIDTH'] == '640'


def test_legacy_history_of_same_device_can_be_bound_without_modifying_pending_images(isolated):
    write_config(isolated)
    store = Store(provisioning.database_path(config.effective_values()))
    store.initialize()
    grant = {'id': str(uuid4()), 'device_id': IDENTITY}
    store.save_grant(grant)
    store.save_camera_sample(str(uuid4()), grant['id'], 'stamp', b'original-photo')
    store.bind_device(IDENTITY, ORIGIN)
    assert store.pending_camera_samples()[0]['image'] == b'original-photo'
    assert store.active_grant() == grant


def test_atomic_writer_does_not_overwrite_concurrent_configuration_changes(isolated):
    write_config(isolated)
    original = isolated.read_text()
    isolated.write_text(original + '# another process\n')
    current = isolated.read_bytes()
    with pytest.raises(ConfigurationError, match='outro processo'):
        provisioning.atomic_save(isolated, {'DEVICE_INGEST_CREDENTIAL': ROTATED}, original)
    assert isolated.read_bytes() == current


def test_headless_camera_missing_configuration_never_initializes_camera_or_api(
    isolated, monkeypatch, capsys
):
    from backend.device import inspect as camera_app

    monkeypatch.setattr(provisioning, 'interactive', lambda: False)
    monkeypatch.setattr('sys.argv', ['device.inspect', '--headless'])
    monkeypatch.setattr(camera_app, 'Camera', lambda _: pytest.fail('No camera during setup.'))
    monkeypatch.setattr(camera_app, 'DeviceApi', lambda _: pytest.fail('No API during setup.'))
    with pytest.raises(SystemExit) as exc:
        camera_app.main()
    assert exc.value.code == 1
    assert 'device configure' in capsys.readouterr().out
    assert not (isolated.parent / 'data').exists()


@pytest.mark.parametrize('option,command', [
    ('configurar', 'configure'), ('atualizar-credencial', 'update-credential'),
])
def test_launcher_configuration_actions_do_not_run_model_or_camera(tmp_path, option, command):
    root = tmp_path / 'project'
    interpreter = root / 'app/.venv/bin/python3'
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text('#!/bin/bash\nprintf "%s\\n" "$@" > calls.txt\n')
    interpreter.chmod(0o700)
    launcher = root / 'start.sh'
    launcher.write_text((Path(__file__).resolve().parents[2] / 'start.sh').read_text())
    result = subprocess.run(['bash', str(launcher), option], cwd=tmp_path,
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0
    assert (root / 'calls.txt').read_text().splitlines() == ['-m', 'device', command]
