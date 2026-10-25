"""Instala apenas o modelo oficial fixado por tamanho e SHA-256; nunca carrega pickle."""

import hashlib

import requests

from .detector import MODEL_PATH, MODEL_SHA256, MODEL_SIZE, MODEL_URL, ModelFailure, verify_model


def main():
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    license_path = MODEL_PATH.parent / 'LICENSE.yolox.txt'
    if not license_path.exists():
        response = requests.get(
            'https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/object_detection_yolox/LICENSE',
            timeout=30,
        )
        response.raise_for_status()
        if len(response.content) > 32000 or 'Apache License' not in response.text:
            raise ModelFailure('Licença do modelo não confirmada.')
        with license_path.open('xb') as stream:
            stream.write(response.content)
    if MODEL_PATH.exists():
        verify_model(MODEL_PATH)
        print('Modelo existente verificado:', MODEL_PATH)
        return
    temporary = MODEL_PATH.with_suffix('.part')
    size, checksum = 0, hashlib.sha256()
    created = False
    try:
        with requests.get(MODEL_URL, stream=True, timeout=(10, 90)) as response:
            response.raise_for_status()
            with temporary.open('xb') as stream:
                created = True
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > MODEL_SIZE:
                        raise ModelFailure('Download excedeu o tamanho do modelo esperado.')
                    checksum.update(chunk)
                    stream.write(chunk)
        if size != MODEL_SIZE or checksum.hexdigest() != MODEL_SHA256:
            raise ModelFailure('Download não corresponde ao SHA-256 oficial fixado.')
        temporary.replace(MODEL_PATH)
        print('Modelo instalado e verificado:', MODEL_PATH)
    finally:
        if created and temporary.exists():
            temporary.unlink()


if __name__ == '__main__':
    main()
