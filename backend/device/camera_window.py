"""Janela de captura: detecção, revisão da foto e rede com estados independentes."""

import time
from datetime import UTC, datetime
from textwrap import wrap
from unicodedata import normalize
from uuid import uuid4

from .api import ApiFailure, Offline
from .camera_review import CameraReview, CaptureNotAuthorized, confirm_photo, connect_session
from .detector import MODEL_NAME, ModelFailure
from .samples import flush_camera_samples, process_one
from .worker import ClockFailure, PairingFailure

WINDOW = 'OrangeVision - captura integrada'


def action_at(x, y, reviewing):
    if not 555 <= y <= 605:
        return None
    if 8 <= x <= (220 if reviewing else 190):
        return 'use' if reviewing else 'capture'
    if reviewing and 235 <= x <= 470:
        return 'retake'
    if 500 <= x <= 810:
        return 'connect'
    return None


def error_message(error):
    if isinstance(error, (ClockFailure, ModelFailure, CaptureNotAuthorized, PairingFailure)):
        return str(error)
    if isinstance(error, ApiFailure):
        return f'API HTTP {error.status}. Confira servidor, credencial e autorização.'
    if isinstance(error, Offline):
        return 'Sem conexão. A foto salva permanece neste equipamento.'
    return f'Operação não concluída ({type(error).__name__}). Confira a captura e a sessão.'


def render_frame(
    frame,
    detection,
    reviewing,
    sending,
    automatic,
    auto_ready,
    armed,
    capture_notice,
    connection_notice,
):
    import cv2
    import numpy as np

    visible = frame.copy()
    if detection['status'] == 'detected' and detection.get('box'):
        x, y, width, height = detection['box']
        cv2.rectangle(visible, (x, y), (x + width, y + height), (0, 180, 0), 2)
        label = 'Laranja'
        (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
        left = max(0, min(x, frame.shape[1] - tw - 12))
        top = max(0, y - th - baseline - 10)
        cv2.rectangle(
            visible, (left, top), (left + tw + 12, top + th + baseline + 8), (0, 105, 0), -1
        )
        cv2.putText(
            visible,
            label,
            (left + 6, top + th + 3),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
    canvas = np.full((720, 960, 3), 245, np.uint8)
    scale = min(960 / frame.shape[1], 520 / frame.shape[0])
    image = cv2.resize(
        visible, (max(1, int(frame.shape[1] * scale)), max(1, int(frame.shape[0] * scale)))
    )
    canvas[: image.shape[0], : image.shape[1]] = image

    def text(message, point, scale=0.5):
        value = normalize('NFKD', message).encode('ascii', 'ignore').decode()
        cv2.putText(
            canvas, value, point, cv2.FONT_HERSHEY_SIMPLEX, scale, (25, 25, 25), 1, cv2.LINE_AA
        )

    detected = detection['status'] == 'detected'
    summary = (
        'Foto capturada. Usar confirma; Tirar outra descarta esta foto.'
        if reviewing
        else (
            'Laranja detectada pelo modelo. Pode capturar.'
            if detected
            else 'Aguardando laranja.'
            if detection.get('count', 0) == 0
            else 'Mostre uma laranja por vez.'
        )
    )
    if automatic and not reviewing:
        summary += ' Automático: ' + (
            'pronto'
            if auto_ready
            else 'aguardando estabilidade'
            if armed
            else 'retire a fruta para liberar a próxima'
        )
    text(summary, (8, 541), 0.49)

    def button(left, right, label, enabled, color):
        cv2.rectangle(canvas, (left, 555), (right, 605), color if enabled else (175, 175, 175), -1)
        cv2.putText(
            canvas,
            label,
            (left + 8, 586),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    if reviewing:
        button(8, 220, 'USAR ESTA FOTO [U]', not sending, (30, 115, 30))
        button(235, 470, 'TIRAR OUTRA [R]', not sending, (135, 85, 35))
    else:
        button(8, 190, 'CAPTURAR [C]', detected and not sending, (25, 120, 210))
    button(500, 810, 'CONECTAR SESSAO [P]', not sending, (100, 70, 45))
    for index, line in enumerate(wrap(capture_notice, 125)[:2]):
        text(line, (8, 631 + index * 21), 0.46)
    text('Conexão: ' + connection_notice[:130], (8, 681), 0.43)
    text(
        f'{"AUTOMÁTICO" if automatic else "MANUAL"} | IA: {detection["inference_ms"]:.0f} ms | Q: sair | A: alternar modo | categoria é avaliada depois',
        (8, 706),
        0.43,
    )
    return canvas


def run_window(
    camera, detector, worker, api, pool, gate, automatic, headless, calibration, save_automatic
):
    import cv2

    review = CameraReview(worker.store, restore=not headless)
    capture_future = None
    capture_kind = None
    maintenance_future = None
    capture_notice = (
        'Foto anterior recuperada. Use ou tire outra.'
        if review.photo
        else 'Posicione a laranja e clique em Capturar ou pressione C.'
    )
    connection_notice = 'Aguardando contato com o servidor.'
    last_poll = -5.0
    clicks = []

    def maintenance():
        api.heartbeat_samples('ready', MODEL_NAME, 'Câmera integrada e fila com IA.')
        events = flush_camera_samples(worker.store, api)
        result = process_one(api, calibration, validated=calibration is not None, detector=detector)
        if 'quarantined' in events:
            return 'Há foto retida localmente. Confira autorização/limite no terminal.'
        if result:
            return 'Resultado disponível no site: ' + result['state']
        if 'synced' in events:
            return 'Foto enviada ao site. Executor conectado.'
        return 'Executor conectado.'

    if not headless:
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW, 960, 680)

        def mouse(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONUP:
                action = action_at(x, y, review.photo is not None)
                if action:
                    clicks.append(action)

        cv2.setMouseCallback(WINDOW, mouse)
    print(
        'C: capturar | U/Enter: usar foto | R: tirar outra | P: conectar sessão | A: automático | Q: sair.'
    )
    print('Detecção da fruta e categoria de qualidade são informações separadas.')
    while True:
        if capture_future is not None and capture_future.done():
            try:
                capture_notice = capture_future.result()
                if capture_kind == 'review':
                    review.submitted()
                elif capture_kind == 'connect':
                    review.sending = False
                if capture_kind != 'connect':
                    gate.captured()  # Só bloqueia automático após salvar efetivamente na outbox.
            except Exception as error:
                capture_notice = error_message(error)
                review.sending = False
                if capture_kind == 'automatic':
                    automatic = False
            print(capture_notice)
            capture_future = None
        if maintenance_future is not None and maintenance_future.done():
            try:
                message = maintenance_future.result()
            except Exception as error:
                message = error_message(error)
            if message != connection_notice:
                print('Conexão:', message)
            connection_notice = message
            maintenance_future = None
            if (
                not headless
                and review.photo is None
                and capture_future is None
                and worker.store.camera_sample_counts().get('quarantined', 0)
            ):
                recovered = CameraReview(worker.store)
                if recovered.photo:
                    review = recovered
                    capture_notice = 'Envio interrompido. Foto recuperada: P conecta a sessão; U confirma o envio.'

        if review.photo:
            frame = review.photo.frame
            detection = review.photo.detection
            captured_at = review.photo.captured_at
            ready = False
        else:
            frame = camera.capture()
            captured_at = datetime.now(UTC).isoformat()
            detection = detector.detect(frame)
            ready = gate.observe(detection, time.monotonic())
        if not headless:
            canvas = render_frame(
                frame,
                detection,
                review.photo is not None,
                review.sending,
                automatic,
                ready,
                gate.armed,
                capture_notice,
                connection_notice,
            )
            cv2.imshow(WINDOW, canvas)
        key = cv2.waitKey(20) & 0xFF if not headless else -1
        if 65 <= key <= 90:
            key += 32
        if not headless and (
            key == ord('q') or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1
        ):
            break
        action = clicks.pop(0) if clicks else None
        if key == ord('c'):
            action = 'capture'
        elif key in (ord('u'), 10, 13):
            action = 'use'
        elif key == ord('r'):
            action = 'retake'
        elif key == ord('p'):
            action = 'connect'
        elif key == ord('a') and not review.photo:
            automatic = not automatic

        if action == 'connect' and not review.sending and capture_future is None:
            try:
                from .session_dialog import ask_connection_code

                response = ask_connection_code(worker)
                if response:
                    review.sending = True
                    capture_kind = 'connect'
                    capture_future = pool.submit(connect_session, worker, *response)
                    capture_notice = 'Conectando sessão. A foto guardada não será descartada…'
            except Exception as error:
                capture_notice = error_message(error)
        elif action == 'capture' and review.sending:
            capture_notice = 'Conectando sessão. Aguarde concluir antes de capturar.'
        elif action == 'capture' and not review.photo:
            try:
                if review.take(frame, detection, captured_at, worker.store.active_grant()):
                    capture_notice = (
                        'Foto capturada e salva. Escolha Usar esta foto ou Tirar outra.'
                    )
                else:
                    capture_notice = 'Aguardando detecção de uma laranja para capturar.'
            except Exception as error:
                capture_notice = (
                    f'Não foi possível salvar a captura ({type(error).__name__}). Tente novamente.'
                )
            print(capture_notice)
        elif action == 'retake' and review.photo and not review.sending:
            review.retake()
            capture_notice = 'Mostre a laranja e capture novamente.'
        elif action == 'use' and review.photo and not review.sending and capture_future is None:
            review.sending = True
            capture_kind = 'review'
            # Pode aguardar uma consulta em andamento, mas nunca descarta o pedido de confirmação.
            capture_future = pool.submit(confirm_photo, worker, review.photo)
            capture_notice = 'Foto salva. Confirmando autorização para enviar…'
        elif automatic and ready and review.photo is None and capture_future is None:
            grant = worker.store.active_grant()
            if not grant:
                automatic = False
                capture_notice = 'Automático pausado: pareie uma sessão antes de enviar fotos.'
                print(capture_notice)
            else:
                capture_kind = 'automatic'
                capture_future = pool.submit(
                    save_automatic, worker, grant, frame.copy(), captured_at, str(uuid4())
                )
                capture_notice = 'Salvando captura automática autorizada…'

        now = time.monotonic()
        if maintenance_future is None and capture_future is None and now - last_poll >= 5:
            maintenance_future = pool.submit(maintenance)
            last_poll = now
