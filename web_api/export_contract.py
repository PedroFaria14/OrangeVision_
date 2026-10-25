"""Exporta o contrato já definido pelos schemas HTTP; não acessa o banco."""

from pathlib import Path

import yaml

from .main import create_app


def main():
    target = Path(__file__).parent.parent / 'contracts' / 'web-openapi.yaml'
    target.write_text(
        yaml.safe_dump(create_app().openapi(), sort_keys=False, allow_unicode=True),
        encoding='utf-8',
    )
    print('OpenAPI 3.1 exportado para contracts/web-openapi.yaml')


if __name__ == '__main__':
    main()
