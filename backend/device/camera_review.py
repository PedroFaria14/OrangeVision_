"""Captura manual local primeiro; confirmação e autorização para envio depois."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .api import ApiFailure
from .worker import ClockFailure


class CaptureNotAuthorized(RuntimeError):
    pass


@dataclass(frozen=True)
class PhotoDraft:
    identity: str
    frame: Any
    captured_at: str
    detection: dict
    grant: dict | None


class CameraReview:
    def __init__(self, store, restore=True):
        self.store = store
        self.photo = None
        self.sending = False
        row = store.latest_photo_draft() if restore else None
        if row is None and restore:
            store.reopen_quarantined_photo()
            row=store.latest_photo_draft()
        if row:
            import cv2
            import numpy as np

            frame = cv2.imdecode(np.frombuffer(row['image'], np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                raise RuntimeError('Foto local não pôde ser recuperada.')
            self.photo = PhotoDraft(
                row['id'], frame, row['captured_at'], row['detection'], row['grant']
            )

    def take(self, frame, detection, captured_at, grant):
        import cv2

        if self.photo is not None or self.sending:
            return False
        if detection['status'] != 'detected':
            return False
        ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not ok:
            raise RuntimeError('Não foi possível salvar a foto.')
        identity = str(uuid4())
        self.store.save_photo_draft(identity, captured_at, encoded.tobytes(), detection, grant)
        self.photo = PhotoDraft(
            identity, frame.copy(), captured_at, deepcopy(detection), deepcopy(grant)
        )
        return True

    def retake(self):
        if self.photo is None or self.sending:
            return False
        self.store.discard_photo_draft(self.photo.identity)
        self.photo = None
        return True

    def submitted(self):
        self.photo = None
        self.sending = False


def confirm_photo(worker, photo):
    if photo.grant:
        try:
            authorized = worker._capture_grant(photo.grant)
        except ClockFailure:
            raise
        except RuntimeError:
            authorized = None
        if authorized:
            worker.store.confirm_photo_draft(photo.identity, authorized['id'])
            return 'Foto confirmada e salva para envio. Acompanhe o resultado em Amostras.'
    current = worker.store.active_grant()
    if not current or (photo.grant and current['id'] == photo.grant['id']):
        raise CaptureNotAuthorized(
            'Foto guardada. Clique CONECTAR SESSAO [P] e depois USAR ESTA FOTO.'
        )
    try:
        authorized = worker._capture_grant(current)
    except ClockFailure:
        raise
    except RuntimeError as exc:
        raise CaptureNotAuthorized(
            'Foto guardada. Clique CONECTAR SESSAO [P] para renovar a autorização.'
        ) from exc
    try:
        worker.api.authorize_camera_review(photo.grant, authorized)
    except ApiFailure as exc:
        if exc.status == 403:
            raise CaptureNotAuthorized(
                'A sessão não autoriza esta foto. Conecte com a conta original e verifique o equipamento.'
            ) from exc
        raise
    worker.store.confirm_photo_draft(
        photo.identity,
        photo.grant['id'] if photo.grant else authorized['id'],
        review_grant_id=authorized['id'],
    )
    return 'Foto confirmada e salva para envio. Acompanhe o resultado em Amostras.'


def connect_session(worker, code, cancel_previous=False):
    if cancel_previous:
        worker.cancel_pairing()
    worker.pair(code)
    return 'Sessão conectada. Use a foto guardada ou capture uma nova.'
