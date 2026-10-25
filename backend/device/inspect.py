"""Câmera integrada: detecção local, captura autorizada e envio como amostra."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from .api import DeviceApi
from .camera import Camera, CameraFailure
from .camera_review import CaptureNotAuthorized
from .camera_window import run_window
from .config import DeviceSettings
from .detector import ModelFailure, OrangeDetector
from .locking import device_lock
from .segmentation import VisionFailure
from .storage import Store
from .worker import ClockFailure, Worker


def overlap(first, second):
    x = max(first[0], second[0])
    y = max(first[1], second[1])
    right = min(first[0] + first[2], second[0] + second[2])
    bottom = min(first[1] + first[3], second[1] + second[3])
    area = max(0, right - x) * max(0, bottom - y)
    return area / (first[2] * first[3] + second[2] * second[3] - area) if area else 0


class CaptureGate:
    """Uma captura por presença; exige estabilidade e retirada confirmada."""

    def __init__(self, stable_seconds=1.2, removal_seconds=1, require_clear=False):
        self.stable_seconds, self.removal_seconds = stable_seconds, removal_seconds
        self.armed = not require_clear
        self.previous = None
        self.since = None
        self.absent = None
        self.frames = 0

    def observe(self, detection, now):
        if detection['status'] != 'detected':
            self.previous = None
            self.since = None
            self.frames = 0
            if detection['status'] == 'not_detected':
                if self.absent is None:
                    self.absent = now
                if now - self.absent >= self.removal_seconds:
                    self.armed = True
            else:
                self.absent = None
            return False
        self.absent = None
        box = detection['box']
        if self.previous is None or overlap(self.previous, box) < 0.8:
            self.since = now
            self.frames = 0
        self.previous = box
        self.frames += 1
        return self.armed and self.frames >= 3 and now - self.since >= self.stable_seconds

    def captured(self):
        self.armed = False
        self.absent = None


def persist_capture(worker, grant, frame, captured_at, identity):
    import cv2

    try:
        authorized = worker._capture_grant(grant)
    except ClockFailure:
        raise
    except RuntimeError as exc:
        raise CaptureNotAuthorized(
            'Sessão expirada/inativa. Q para sair, pareie e reabra a câmera.'
        ) from exc
    ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise RuntimeError('Não foi possível codificar a captura.')
    worker.store.save_camera_sample(identity, authorized['id'], captured_at, encoded.tobytes())
    return 'Foto salva localmente. Aguardando envio ao site.'


def main():
    import cv2

    parser = argparse.ArgumentParser(
        description='OrangeVision: câmera com detecção e envio de amostras autorizadas.'
    )
    parser.add_argument('--camera', type=int)
    parser.add_argument('--width', type=int, default=640)
    parser.add_argument('--height', type=int, default=480)
    parser.add_argument(
        '--auto', action='store_true', help='Capturar após estabilidade e aguardar retirada.'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Modo automático sem janela, adequado ao Raspberry sem monitor.',
    )
    parser.add_argument(
        '--calibration', help='Calibração validada especificamente para yolox-s-grabcut-v1.'
    )
    args = parser.parse_args()
    if not args.headless and not any(
        line.strip().startswith('GUI:') and 'NONE' not in line
        for line in cv2.getBuildInformation().splitlines()
    ):
        parser.error(
            'Este modo precisa de interface gráfica e requirements-lab.txt. Use samples --loop --ai em modo sem monitor.'
        )
    settings = DeviceSettings.load()
    settings = replace(
        settings,
        camera_adapter='usb' if args.camera is not None else settings.camera_adapter or 'usb',
        camera_index=args.camera if args.camera is not None else settings.camera_index,
        width=args.width,
        height=args.height,
    )
    store = Store(settings.database)
    store.initialize()
    api = DeviceApi(settings)
    camera = None
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='orangevision-upload')
    automatic = args.auto or args.headless
    calibration = None
    try:
        if args.calibration:
            from .vision import CalibratedVision

            calibration = CalibratedVision.load(args.calibration).calibration
            if calibration.get('segmentation_method') != 'yolox-s-grabcut-v1':
                raise ModelFailure(
                    'A calibração precisa ser validada para o método yolox-s-grabcut-v1.'
                )
        detector = OrangeDetector()
        with device_lock(settings.lock_path):
            camera = Camera(settings)
            worker = Worker(settings.device_id, store, api)
            gate = CaptureGate(require_clear=automatic)
            run_window(
                camera,
                detector,
                worker,
                api,
                pool,
                gate,
                automatic,
                args.headless,
                calibration,
                persist_capture,
            )
    except (ModelFailure, ClockFailure, VisionFailure, CameraFailure) as exc:
        print(str(exc))
    except KeyboardInterrupt:
        print('Encerrando. Fotos confirmadas localmente permanecem na fila.')
    finally:
        if camera:
            camera.close()
        if not args.headless:
            try:
                cv2.destroyAllWindows()
            except cv2.error:
                pass
        pool.shutdown(wait=True, cancel_futures=True)
        api.close()


if __name__ == '__main__':
    main()
