"""Gera o artefato público sem carregar .env, conectar ao banco ou iniciar serviços."""

import argparse
from pathlib import Path

import yaml

from .main import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    artifact = Path(__file__).parents[1] / 'contracts' / 'web-openapi.yaml'
    current = create_app().openapi()
    previous = yaml.safe_load(artifact.read_text(encoding='utf-8'))
    for path, definition in previous['paths'].items():
        if current['paths'].get(path) != definition:
            raise RuntimeError(
                'Uma operação publicada foi alterada; revisar compatibilidade antes de exportar.'
            )
    for name, definition in previous['components']['schemas'].items():
        updated = current['components']['schemas'].get(name, {})
        if (
            {key: value for key, value in updated.items() if key != 'properties'}
            != {key: value for key, value in definition.items() if key != 'properties'}
            or any(
                updated.get('properties', {}).get(field) != spec
                for field, spec in definition.get('properties', {}).items()
            )
            or any(
                field in updated.get('required', [])
                for field in set(updated.get('properties', {}))
                - set(definition.get('properties', {}))
            )
        ):
            raise RuntimeError(
                'Um schema publicado foi alterado; revisar compatibilidade antes de exportar.'
            )
    if args.write:
        artifact.write_text(
            yaml.safe_dump(current, allow_unicode=True, sort_keys=False), encoding='utf-8'
        )
        print('OpenAPI exportado; operações e schemas anteriores preservados.')
    else:
        print('Compatibilidade verificada. Use --write para atualizar o artefato.')


if __name__ == '__main__':
    main()
