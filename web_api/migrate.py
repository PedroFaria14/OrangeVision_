"""Aplicação manual da migration revisada; nunca executada pelo startup da API."""

import argparse
from pathlib import Path

import psycopg

from .config import Settings

MIGRATION = Path(__file__).parent / 'migrations' / '001_web_auth.sql'
EXPECTED_TABLES = ('users', 'sessions', 'device_access', 'auth_attempts')


def main():
    parser = argparse.ArgumentParser(description='Migration aditiva de autenticação OrangeVision.')
    parser.add_argument('--apply', action='store_true', help='Executar a migration explicitamente.')
    parser.add_argument('--migration', choices=('001', '002', '003', '004', '005'), default='001')
    args = parser.parse_args()
    migration = (
        MIGRATION
        if args.migration == '001'
        else MIGRATION.parent
        / {
            '002': '002_inspection_sessions.sql',
            '003': '003_image_samples.sql',
            '004': '004_sample_executor_detection.sql',
            '005': '005_sample_review_authorization.sql',
        }[args.migration]
    )
    expected = (
        EXPECTED_TABLES
        if args.migration == '001'
        else ('device_credentials', 'inspection_sessions', 'ingestion_receipts')
        if args.migration == '002'
        else ('image_samples',)
        if args.migration == '003'
        else ('image_samples', 'sample_executors')
        if args.migration == '004'
        else ('image_samples',)
    )
    if not args.apply:
        print(f'Plano: {migration.name}. Revisar SQL, histórico e ambiente antes de aplicar.')
        print(
            f'Nenhuma execução. Para aplicar após revisão/autorização: python -m web_api.migrate --migration {args.migration} --apply'
        )
        return

    try:
        settings = Settings.load()
        with psycopg.connect(settings.database_url, connect_timeout=5, autocommit=True) as db:
            # BEGIN/COMMIT e timeouts estão no SQL versionado. Falha não confirma DDL parcial.
            db.execute(migration.read_text(encoding='utf-8'), prepare=False)
            for table in expected:
                if not db.execute(
                    'SELECT to_regclass(%s) IS NOT NULL', (f'orangevision_web.{table}',)
                ).fetchone()[0]:
                    raise RuntimeError('Estrutura esperada não encontrada após a migration.')
        print(
            f'Migration {migration.name} aplicada. Tabelas confirmadas: {len(expected)}/{len(expected)}.'
        )
        print('Dados existentes preservados; nenhum proprietário foi atribuído ao histórico.')
    except Exception as exc:
        # Não imprimir a URL/credenciais ou mensagens de driver com dados da conexão.
        print(
            f'Migration não confirmada; tipo={type(exc).__name__}. Conferir o estado antes de repetir.'
        )
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
