"""Diagnóstico local da chave/modelo Gemini: UMA chamada com imagem sintética pequena.

Uso (PowerShell, na raiz OrangeVision):
    $env:GEMINI_API_KEY = 'sua-chave'
    web_api\\.venv-web\\Scripts\\python.exe tools\\gemini_check.py [modelo]

Mostra só o status HTTP, o tempo e a mensagem de erro do Google. Não imprime a chave.
Consome 1 chamada da cota da chave (não conta no limite do OrangeVision).
"""
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from web_api.infrastructure.gemini_provider import GeminiProvider  # noqa: E402

# JPEG 1x1 laranja válido.
IMAGE = bytes.fromhex(
    'ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c'
    '1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b'
    '080001000101011100ffc4001f0000010501010101010100000000000000000102030405060708090a0bffc400b510'
    '0002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552'
    'd1f02433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465'
    '666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8'
    'b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda00080101'
    '00003f00fbd3ffd9'
)


def main():
    key = os.getenv('GEMINI_API_KEY', '').strip()
    if not key:
        raise SystemExit('Defina GEMINI_API_KEY nesta janela do terminal antes de rodar.')
    model = sys.argv[1] if len(sys.argv) > 1 else os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')
    print('Modelo:', model)
    try:
        with urlopen(Request(f'https://generativelanguage.googleapis.com/v1beta/models?pageSize=200',
                             headers={'x-goog-api-key': key}), timeout=30) as response:
            names = [m['name'].split('/')[-1] for m in json.load(response).get('models', [])
                     if 'generateContent' in m.get('supportedGenerationMethods', [])]
        print('Modelo existe para esta chave:', 'sim' if model in names else 'NÃO')
        print('Modelos flash disponíveis:', ', '.join(n for n in names if 'flash' in n) or '-')
    except (HTTPError, URLError, TimeoutError) as error:
        print('Não foi possível listar modelos:', getattr(error, 'code', type(error).__name__))

    settings = type('S', (), {'gemini_api_key': key, 'gemini_timeout': 90})()
    provider = GeminiProvider(settings)
    original = provider.opener.open

    def traced(request, timeout):
        try:
            with original(request, timeout=timeout) as response:
                content = response.read(65537)
            try:
                data = json.loads(content)
                outputs = data.get('outputs', [])
                print('Resposta: status =', data.get('status'), '| chaves =', sorted(data))

                def shape(value, depth=0):
                    # Estrutura e textos curtos; sem dados binários.
                    pad = '    ' * depth
                    if isinstance(value, dict):
                        for key, item in value.items():
                            if isinstance(item, (dict, list)):
                                print(f'{pad}{key}:')
                                shape(item, depth + 1)
                            else:
                                print(f'{pad}{key} = {str(item)[:300]!r}')
                    elif isinstance(value, list):
                        for index, item in enumerate(value[:6]):
                            print(f'{pad}[{index}]')
                            shape(item, depth + 1)

                print('steps:')
                shape(data.get('steps'), 1)
                for item in outputs if isinstance(outputs, list) else []:
                    text = item.get('text', '') if isinstance(item, dict) else ''
                    print('  saída tipo =', item.get('type') if isinstance(item, dict) else type(item).__name__,
                          '| texto =', text[:600])
            except ValueError:
                print('Resposta não-JSON:', content[:300])

            class Replay:
                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

                def read(self, size=-1):
                    return content

            return Replay()
        except HTTPError as error:
            body = error.read(2000).decode('utf-8', 'replace')
            try:
                body = json.loads(body).get('error', {}).get('message', body)
            except ValueError:
                pass
            print(f'HTTP {error.code}: {body}')
            raise

    provider.opener.open = traced
    started = time.monotonic()
    try:
        result, usage = provider.assess(IMAGE, model)
        print(f'OK em {time.monotonic() - started:.1f}s:', result.model_dump(), usage)
    except Exception as error:
        print(f'Falhou em {time.monotonic() - started:.1f}s:', getattr(error, 'code', type(error).__name__))


if __name__ == '__main__':
    main()
