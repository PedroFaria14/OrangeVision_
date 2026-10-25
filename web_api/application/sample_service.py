import base64
import binascii
import hashlib
import json

from .auth_service import digest
from .errors import ApplicationError


class SampleService:
    def __init__(self, repository, images):
        self.repository, self.images = repository, images

    def ready(self):
        return self.repository.ready()

    def require_ready(self):
        if not self.ready():
            raise ApplicationError(503, 'Amostras ainda não ativadas neste ambiente.')

    def devices(self, owner):
        self.require_ready()
        return self.repository.devices(owner)

    def heartbeat(self, device, payload):
        return self.repository.heartbeat(device, payload)

    def upload(self, owner, request_id, filename, content):
        self.require_ready()
        image, width, height = self.images.normalize(content)
        name = filename.replace('\\', '/').split('/')[-1]
        name = (
            ''.join(character for character in name if character.isprintable()).strip()[:120]
            or 'imagem'
        )
        return self.repository.upload(
            owner, request_id, hashlib.sha256(content).hexdigest(), name, image, width, height
        )

    def upload_capture(self, device, inspection_id, lease, request_id, captured_at, content):
        if captured_at.utcoffset() is None:
            raise ApplicationError(422, 'Horário da captura exige fuso.')
        image, width, height = self.images.normalize(content)
        return self.repository.upload(
            None,
            request_id,
            hashlib.sha256(content).hexdigest(),
            'captura-' + str(request_id) + '.jpg',
            image,
            width,
            height,
            inspection_id=inspection_id,
            captured_at=captured_at,
            device=device,
            lease_hash=digest(lease),
        )

    def authorize_review(self, device, original_id, original_lease, review_id, review_lease):
        self.repository.authorize_review(
            device,
            original_id,
            digest(original_lease) if original_lease else None,
            review_id,
            digest(review_lease),
        )
        return {'authorized': True}

    def upload_review_capture(
        self,
        device,
        original_id,
        original_lease,
        review_id,
        review_lease,
        request_id,
        captured_at,
        content,
    ):
        if captured_at.utcoffset() is None:
            raise ApplicationError(422, 'Horário da foto exige fuso.')
        image, width, height = self.images.normalize(content)
        return self.repository.upload(
            None,
            request_id,
            hashlib.sha256(content).hexdigest(),
            'captura-' + str(request_id) + '.jpg',
            image,
            width,
            height,
            inspection_id=original_id,
            captured_at=captured_at,
            device=device,
            lease_hash=digest(original_lease) if original_lease else None,
            review_authorization_id=review_id,
            review_lease_hash=digest(review_lease),
        )

    def listing(self, owner, limit, offset):
        self.require_ready()
        return self.repository.listing(owner, limit, offset)

    def image(self, owner, identity, mask=False):
        self.require_ready()
        return self.repository.image(owner, identity, mask)

    def queue(self, owner, identity, device):
        self.require_ready()
        return self.repository.queue(owner, identity, device)

    def authenticate_device(self, token):
        if not token or len(token) < 32 or len(token) > 256:
            raise ApplicationError(401, 'Equipamento não autorizado.')
        device = self.repository.authenticate_device(digest(token))
        if not device:
            raise ApplicationError(401, 'Equipamento não autorizado.')
        self.require_ready()
        return device['device_id']

    def claim(self, device, claim_id, lease_token):
        return self.repository.claim(device, claim_id, digest(lease_token))

    def device_image(self, device, identity, lease):
        return self.repository.device_image(device, identity, digest(lease))

    def finish(self, device, identity, lease, result):
        payload = result.model_dump(mode='json')
        if payload.get('detection') is None:
            payload.pop(
                'detection', None
            )  # Preserva o digest de resultados anteriores à extensão de IA.
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        ).hexdigest()
        mask = None
        if result.mask_base64 is not None or (result.detection and result.detection.box):
            # Autoriza antes de decodificar/validar o artefato enviado pelo equipamento.
            row = self.repository.assignment(device, identity, result.claim_id, digest(lease))
            if result.detection and result.detection.box:
                x, y, width, height = result.detection.box
                if x + width > row['width'] or y + height > row['height']:
                    raise ApplicationError(422, 'Detecção fora da imagem.')
        if result.mask_base64 is not None:
            try:
                content = base64.b64decode(result.mask_base64, validate=True)
            except (ValueError, binascii.Error) as exc:
                raise ApplicationError(422, 'Máscara inválida.') from exc
            mask = self.images.mask(content, row['width'], row['height'])
        return self.repository.finish(device, identity, digest(lease), payload, payload_hash, mask)
