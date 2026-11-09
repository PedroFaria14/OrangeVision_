"""Prepara PostgreSQL descartável em Docker e executa somente os testes de equipamentos."""
import os
import secrets
import subprocess
import sys
import time

import psycopg


def main(tests=None):
    name = f'orangevision-device-test-{os.getpid()}'
    password = secrets.token_hex(24)

    def docker(*args):
        return subprocess.check_output(['docker', *args], text=True, stderr=subprocess.PIPE).strip()

    started = False
    try:
        docker('run', '--detach', '--rm', '--name', name, '--publish', '127.0.0.1::5432',
               '--env', f'POSTGRES_PASSWORD={password}', '--env', 'POSTGRES_DB=orangevision_devices_test', 'postgres:16-alpine')
        started = True
        port = docker('port', name, '5432/tcp').rsplit(':', 1)[1]
        url = f'postgresql://postgres:{password}@127.0.0.1:{port}/orangevision_devices_test'
        for _ in range(40):
            try:
                with psycopg.connect(url, connect_timeout=1):
                    break
            except psycopg.Error:
                time.sleep(.5)
        else:
            raise RuntimeError('PostgreSQL descartável não iniciou.')
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', *(tests or ['web_api/tests/test_devices_postgres.py']), '-q'],
            env={**os.environ, 'OV_DEVICE_TEST_DATABASE_URL': url}, check=False,
        )
        return result.returncode
    except Exception as error:
        print(f'Teste descartável não concluído; tipo={type(error).__name__}.')
        return 1
    finally:
        if started:
            docker('stop', name)


if __name__ == '__main__':
    raise SystemExit(main())
