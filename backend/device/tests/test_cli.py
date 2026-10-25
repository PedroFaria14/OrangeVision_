import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from backend.device import __main__ as cli
from backend.device.api import ApiFailure, Offline
from backend.device.storage import Store


@pytest.fixture
def cli_settings(tmp_path, monkeypatch):
    settings = SimpleNamespace(
        database=tmp_path / 'cli.db', lock_path=tmp_path / 'worker.lock', device_id=str(uuid4())
    )
    monkeypatch.setattr(cli.DeviceSettings, 'load', lambda: settings)
    return settings


@pytest.mark.parametrize(
    'failure,expected',
    [
        (ApiFailure(401), 'HTTP 401'),
        (ApiFailure(409), 'HTTP 409'),
        (Offline('private-response-body'), 'Sem comunicação'),
    ],
)
def test_pair_failure_explains_action_without_echoing_secrets(
    cli_settings, monkeypatch, capsys, failure, expected
):
    class Api:
        def pair(self, attempt):
            raise failure

        def close(self):
            pass

    monkeypatch.setattr(cli, 'DeviceApi', lambda _: Api())
    monkeypatch.setattr(cli.getpass, 'getpass', lambda _: 'private-pairing-code')
    monkeypatch.setattr('sys.argv', ['device', 'pair'])
    with pytest.raises(SystemExit) as result:
        cli.main()
    assert result.value.code == 1
    output = capsys.readouterr().out
    assert expected in output
    assert 'private-pairing-code' not in output
    assert 'private-response-body' not in output
    assert Store(cli_settings.database).pairing_attempt() is not None


def test_status_reports_pending_attempt_without_disclosing_code_or_lease(
    cli_settings, monkeypatch, capsys
):
    store = Store(cli_settings.database)
    store.initialize()
    store.pairing_attempt(
        {
            'pairing_code': 'private-code',
            'lease_token': 'private-lease',
            'activation_id': str(uuid4()),
        }
    )
    monkeypatch.setattr(cli, 'DeviceApi', lambda _: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr('sys.argv', ['device', 'status'])
    cli.main()
    output = capsys.readouterr().out
    assert json.loads(output)['pairing_pending'] is True
    assert 'private-code' not in output
    assert 'private-lease' not in output
