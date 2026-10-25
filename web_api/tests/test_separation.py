"""Regressão das fronteiras e do contrato público durante a refatoração."""

import ast
from pathlib import Path

import yaml

from web_api.main import create_app


def test_openapi_contract_did_not_change():
    artifact = Path(__file__).parents[2] / 'contracts' / 'web-openapi.yaml'
    assert create_app().openapi() == yaml.safe_load(artifact.read_text(encoding='utf-8'))


def test_existing_paths_and_schemas_remain_compatible_when_adding_endpoints():
    artifact = Path(__file__).parents[2] / 'contracts' / 'web-openapi.yaml'
    previous = yaml.safe_load(artifact.read_text(encoding='utf-8'))
    current = create_app().openapi()
    for path, contract in previous['paths'].items():
        assert current['paths'][path] == contract
    for name, schema in previous['components']['schemas'].items():
        updated = current['components']['schemas'][name]
        assert {key: value for key, value in updated.items() if key != 'properties'} == {
            key: value for key, value in schema.items() if key != 'properties'
        }
        for field, definition in schema.get('properties', {}).items():
            assert updated['properties'][field] == definition
        for field in set(updated.get('properties', {})) - set(schema.get('properties', {})):
            assert field not in updated.get('required', [])


def test_application_does_not_import_framework_database_or_device():
    folder = Path(__file__).parents[1] / 'application'
    forbidden = {'fastapi', 'psycopg', 'argon2', 'sqlite3', 'cv2', 'RPi', 'gpiozero'}
    for file in folder.glob('*.py'):
        for node in ast.walk(ast.parse(file.read_text(encoding='utf-8'))):
            if isinstance(node, ast.Import):
                assert not any(alias.name.split('.')[0] in forbidden for alias in node.names), file
            if isinstance(node, ast.ImportFrom):
                module = node.module or ''
                assert module.split('.')[0] not in forbidden, file
                assert 'infrastructure' not in module.split('.'), file
                assert 'api' not in module.split('.'), file


def test_http_routes_do_not_execute_sql_or_password_hashes():
    folder = Path(__file__).parents[1] / 'api'
    for file in folder.glob('*_routes.py'):
        tree = ast.parse(file.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {
                    'execute',
                    'executemany',
                    'hash_password',
                    'verify_password',
                }, file
