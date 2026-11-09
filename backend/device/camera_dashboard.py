"""Painel OpenCV leve: captura, envio, sessão e qualidade são estados distintos."""

from datetime import datetime
from functools import lru_cache
from unicodedata import normalize

from .api import connection_guidance
from .sample_evaluations import evaluation_view
from .sample_status import analysis_identity
from .worker import validate_grant

BACKGROUND = (23, 19, 17)
PANEL = (39, 33, 29)
TEXT = (240, 237, 234)
MUTED = (170, 163, 154)
ORANGE = (35, 140, 245)
GREEN = (120, 205, 90)
RED = (105, 105, 245)


def failure_notice(error):
    return connection_guidance(error)


class DashboardStatus:
    def __init__(self):
        self.upload = 'Nenhuma foto enviada nesta execucao.'
        self.upload_tone = 'muted'
        self.analysis = 'Qualidade nao avaliada.'
        self.analysis_detail = 'Detectar laranja nao avalia sua qualidade.'
        self.analysis_tone = 'muted'
        self.sample = None
        self.result_summary = None
        self.registration_sample = None
        self.analysis_id = None
        self.registration = 'Sem confirmacao de registro.'
        self.registration_detail = 'Receber a foto nao confirma inclusao no historico.'
        self.registration_tone = 'muted'
        self.counts = {}
        self.session = 'Sem autorizacao local valida.'
        self.session_detail = 'Use Sessao [P] para conectar.'
        self.session_valid = False
        self.evaluation = evaluation_view(None)

    def restore(self, store):
        receipt = store.latest_sample_status(receipt=True)
        if receipt:
            self.handle({'kind': 'synced', **receipt})
        latest = store.latest_sample_status()
        if latest:
            self.handle({
                **latest,
                'kind': 'result' if latest['confirmation'] == 'confirmed' else 'result_pending',
            })
        pending = store.latest_sample_status(pending=True)
        if pending and pending['result'] is None:
            self.handle({'kind': 'processing', 'sample_id': pending['sample_id']})

    def _registration(self, sample_id, analysis_id=None, *, confirmed=False):
        if self.registration_sample != sample_id:
            self.registration_sample, self.analysis_id = sample_id, None
        try:
            identity = analysis_identity(analysis_id)
        except RuntimeError:
            identity = None
        if identity:
            self.analysis_id = identity
        if self.analysis_id:
            self.registration = 'Registrada no historico.'
            self.registration_detail = 'Graficos dependem do periodo e dos filtros.'
            self.registration_tone = 'green'
        elif confirmed:
            self.registration = 'API nao confirmou registro.'
            self.registration_detail = 'Resposta sem analysis_id. Nao afirmar inclusao nos graficos.'
            self.registration_tone = 'muted'
        else:
            self.registration = 'Confirmacao de registro pendente.'
            self.registration_detail = 'A API pode ter recebido. Nao sera criado outro envio de analise.'
            self.registration_tone = 'orange'

    def refresh(self, store, device_id):
        self.counts = store.camera_sample_counts()
        # Sempre pela amostra exibida: resposta tardia de outra captura nunca aparece aqui.
        self.evaluation = evaluation_view(
            store.sample_evaluation(self.registration_sample) if self.registration_sample else None
        )
        grant = store.active_grant()
        self.session_valid = False
        if not grant:
            self.session = 'Nao pareado neste equipamento.'
            self.session_detail = 'Use Sessao [P] para conectar.'
            return
        try:
            expiry = validate_grant(grant, device_id)
        except (RuntimeError, ValueError, KeyError, TypeError) as exc:
            self.session = 'Autorizacao local indisponivel.'
            self.session_detail = str(exc)
            return
        self.session_valid = True
        self.session = 'Pareado: ' + grant['operator_name']
        self.session_detail = (
            f'Valido ate {expiry.astimezone():%d/%m %H:%M %Z}. '
            'Pareado nao significa online.'
        )

    def handle(self, event):
        kind = event['kind']
        if kind == 'uploading':
            self.upload = 'Enviando foto ao servidor...'
            self.upload_tone = 'orange'
        elif kind == 'synced':
            self.upload = 'Recebida pelo servidor: ' + event['sample_id'][:8]
            self.upload_tone = 'green'
            self._registration(event['sample_id'], event.get('analysis_id'))
        elif kind == 'quarantined':
            self.upload = f'Envio retido (HTTP {event["status"]}). Revise a autorizacao.'
            self.upload_tone = 'red'
        elif kind == 'upload_error':
            self.upload = 'Envio sem confirmacao; API pode ter recebido. ' + failure_notice(event['error'])
            self.upload_tone = 'red'
        elif kind == 'processing':
            self.sample = event['sample_id']
            self.result_summary = None
            self.analysis = 'Em analise...'
            self.analysis_detail = 'Amostra recebida para processamento; nao e o video ao vivo.'
            self.analysis_tone = 'orange'
            self._registration(self.sample)
        elif kind in ('result', 'result_pending'):
            self.sample = event['sample_id']
            result = event['result']
            self.result_summary = result
            category = result.get('classification')
            labels = {
                'APROVADA': ('Aprovada pela calibracao', 'green'),
                'ATENCAO': ('Atencao: conferir a fruta', 'orange'),
                'REVISAR': ('Revisar a fruta', 'red'),
            }
            if (
                result.get('state') == 'completed'
                and result.get('calibration_validated') is True
                and category in labels
            ):
                self.analysis, self.analysis_tone = labels[category]
            else:
                self.analysis = {
                    'not_evaluable': 'Imagem nao avaliavel.',
                    'failed': 'Falha na analise.',
                }.get(result.get('state'), 'Qualidade nao avaliada.')
                self.analysis_tone = 'muted'
            self.analysis_detail = result.get('reason') or 'Confira o resultado em Amostras.'
            if (
                kind == 'result_pending' and result.get('state') == 'completed'
                and category in labels and result.get('calibration_validated') is True
            ):
                self.analysis += ' (local)'
            self._registration(
                self.sample, event.get('analysis_id'), confirmed=kind == 'result'
            )
        elif kind == 'analysis_error':
            if self.sample != event.get('sample_id') or self.result_summary is None:
                self.sample = event.get('sample_id')
                self.result_summary = None
                self.analysis = 'Avaliacao pendente.'
                self.analysis_detail = 'Nao foi possivel concluir a avaliacao desta amostra.'
                self.analysis_tone = 'orange'
            self._registration(self.sample)
            self.registration_detail = (
                'Registro anterior preservado. ' if self.analysis_id else
                'Resposta nao confirmada; API pode ter recebido. '
            ) + failure_notice(event['error'])


def action_at(x, y, reviewing):
    if not 555 <= y <= 605:
        return None
    if 16 <= x <= 220:
        return 'use' if reviewing else 'capture'
    if 235 <= x <= 470:
        return 'retake' if reviewing else 'details'
    if 500 <= x <= 810:
        return 'connect'
    if 824 <= x <= 944:
        return 'mode'
    return None


def _text(canvas, message, point, scale=0.48, color=TEXT):
    import cv2

    value = normalize('NFKD', str(message)).encode('ascii', 'ignore').decode()
    cv2.putText(canvas, value, point, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)


@lru_cache(maxsize=64)
def _wrapped(message, width, scale):
    import cv2

    value = normalize('NFKD', str(message)).encode('ascii', 'ignore').decode()
    lines, line = [], ''
    for word in value.split():
        # Also split long identifiers/URLs so text never spills into another card.
        while cv2.getTextSize(word, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)[0][0] > width:
            split = max(1, len(word) // 2)
            while cv2.getTextSize(word[:split], cv2.FONT_HERSHEY_SIMPLEX, scale, 1)[0][0] > width:
                split -= 1
            if line:
                lines.append(line)
                line = ''
            lines.append(word[:split])
            word = word[split:]
        candidate = (line + ' ' + word).strip()
        if cv2.getTextSize(candidate, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)[0][0] > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return tuple(lines)


def _lines(canvas, message, x, y, width, max_lines=2, color=MUTED, scale=0.42, offset=0, truncate=True):
    lines = _wrapped(str(message), width, scale)
    for index, line in enumerate(lines[offset:offset + max_lines]):
        if truncate and index == max_lines - 1 and len(lines) > offset + max_lines:
            line = line[:-3] + '...'
        _text(canvas, line, (x, y + index * 19), scale, color)


@lru_cache(maxsize=1)
def _background():
    import cv2
    import numpy as np

    canvas = np.full((720, 960, 3), BACKGROUND, np.uint8)
    cv2.rectangle(canvas, (0, 0), (959, 3), ORANGE, -1)
    _text(canvas, 'ORANGE / VISION', (18, 36), 0.76, ORANGE)
    _text(canvas, 'ESTACAO DE INSPECAO', (18, 60), 0.38, MUTED)
    for top, bottom in ((84, 170), (176, 240), (246, 336), (342, 412), (418, 534)):
        cv2.rectangle(canvas, (664, top), (944, bottom), PANEL, -1)
    cv2.rectangle(canvas, (16, 84), (648, 534), (12, 11, 10), -1)
    cv2.rectangle(canvas, (16, 619), (944, 690), PANEL, -1)
    return canvas


def _render_evaluation_details(canvas, status, tones):
    evaluation = status.evaluation
    _text(canvas, 'Captura local: ' + evaluation['photo_id'], (30, 136), 0.38)
    _text(canvas, 'Amostra remota: ' + (status.registration_sample or 'nenhuma'), (30, 157), 0.38)
    _text(canvas, 'Sessao de origem: ' + evaluation['inspection_id'], (30, 178), 0.38)
    _lines(canvas, evaluation['gemini'], 30, 206, 602, 1, tones[evaluation['tone']], 0.46)
    _lines(canvas, evaluation['detail'], 30, 228, 602, 3, TEXT)
    _text(canvas, 'Avaliacao local registrada na API:', (30, 298), 0.36, ORANGE)
    _lines(canvas, evaluation['local'], 30, 318, 602, 2)
    _text(canvas, 'Resultado adotado:', (30, 370), 0.36, ORANGE)
    _lines(canvas, evaluation['adopted'], 30, 390, 602, 2, TEXT)
    _lines(canvas, evaluation['comparison'], 30, 437, 602, 1)
    _lines(canvas, evaluation['notice'], 30, 464, 602, 2)
    _text(canvas, evaluation['observed'], (30, 515), 0.36, MUTED)


def _render_framing(canvas, image, left, top, scale, framing):
    """Contorno da fruta e faixa com a dica de enquadramento sobre o vídeo."""
    import cv2
    import numpy as np

    color = {'green': GREEN, 'orange': ORANGE, 'red': RED}.get(framing.tone, MUTED)
    if framing.contour is not None:
        # Desenha na cópia redimensionada: o quadro da câmera segue intacto para a IA.
        contour = np.round(np.asarray(framing.contour) * scale).astype(np.int32)
        cv2.drawContours(image, [contour], -1, color, 2, cv2.LINE_AA)
        canvas[top:top + image.shape[0], left:left + image.shape[1]] = image
    cv2.rectangle(canvas, (16, 84), (648, 110), (12, 11, 10), -1)
    cv2.circle(canvas, (30, 97), 6, color, -1, cv2.LINE_AA)
    _lines(canvas, framing.message, 44, 102, 596, 1, color, 0.44)


def render_frame(
    frame, detection, reviewing, sending, automatic, auto_ready, armed,
    capture_notice, connection_notice, *, dashboard=None, details=False, details_page=0,
    framing=None,
):
    import cv2

    status = dashboard or DashboardStatus()
    canvas = _background().copy()
    visible = frame.copy() if reviewing else frame
    # An old detection must never be drawn as a box on a different live frame.
    if reviewing and detection.get('box'):
        x, y, width, height = detection['box']
        cv2.rectangle(visible, (x, y), (x + width, y + height), GREEN, 2)
        _text(visible, 'Laranja', (max(0, x), max(14, y - 8)), 0.5, GREEN)
    scale = min(632 / frame.shape[1], 450 / frame.shape[0])
    image = cv2.resize(visible, (int(frame.shape[1] * scale), int(frame.shape[0] * scale)))
    left, top = 16 + (632 - image.shape[1]) // 2, 84 + (450 - image.shape[0]) // 2
    canvas[top:top + image.shape[0], left:left + image.shape[1]] = image
    if framing is not None and not details:
        _render_framing(canvas, image, left, top, scale, framing)
    detected = detection['status'] == 'detected'
    _text(canvas, 'REVISAO DA FOTO' if reviewing else 'CAMERA AO VIVO', (470, 58), 0.4, ORANGE)
    _text(canvas, 'SESSAO LOCAL', (678, 104), 0.4, ORANGE)
    _lines(canvas, status.session, 678, 125, 252, 1, GREEN if status.session_valid else TEXT)
    _lines(canvas, status.session_detail, 678, 145, 252, 2)
    _text(canvas, 'ENVIO DA FOTO', (678, 194), 0.4, ORANGE)
    tones = {'muted': MUTED, 'orange': ORANGE, 'green': GREEN, 'red': RED}
    _lines(canvas, status.upload, 678, 214, 252, 2, tones[status.upload_tone])
    _text(canvas, 'QUALIDADE LOCAL / ULTIMA AMOSTRA', (678, 264), 0.36, ORANGE)
    _lines(canvas, status.analysis, 678, 285, 252, 1, tones[status.analysis_tone])
    _lines(canvas, status.analysis_detail, 678, 304, 252, 1)
    if status.sample:
        _text(canvas, 'Amostra: ' + status.sample[:8] + ' | I: motivo', (678, 326), 0.34, MUTED)
    _text(canvas, 'REGISTRO NO HISTORICO', (678, 360), 0.38, ORANGE)
    _lines(canvas, status.registration, 678, 380, 252, 1, tones[status.registration_tone])
    if status.registration_sample:
        _text(canvas, 'Amostra: ' + status.registration_sample[:8], (678, 402), 0.35, MUTED)
    evaluation = status.evaluation
    _text(canvas, 'WEB API / GEMINI', (678, 436), 0.38, ORANGE)
    _lines(canvas, evaluation['gemini'], 678, 457, 252, 1, tones[evaluation['tone']])
    _lines(canvas, evaluation['adopted'], 678, 476, 252, 1, TEXT, 0.38)
    _lines(canvas, evaluation['comparison'], 678, 495, 252, 1, MUTED, 0.38)
    _lines(canvas, evaluation['notice'], 678, 516, 252, 1, MUTED, 0.34)
    counts = status.counts
    _text(canvas, f'Fila: {counts.get("pending", 0)} | Retidas: {counts.get("quarantined", 0)}',
          (666, 35), 0.38)
    _text(canvas, f'Recebidas pela API: {counts.get("synced", 0)}', (666, 59), 0.36, MUTED)

    summary = 'Foto guardada: confirme em USAR FOTO.' if reviewing else (
        'Laranja detectada (ultimo quadro analisado).' if detected else
        'Mostre uma laranja por vez.' if detection.get('count', 0) > 1 else
        'IA processando / aguardando laranja.'
    )
    _text(canvas, summary, (18, 548), 0.43, GREEN if detected else MUTED)

    def button(left, right, label, enabled, color=ORANGE):
        cv2.rectangle(canvas, (left, 555), (right, 605), color if enabled else PANEL, -1)
        _text(canvas, label, (left + 10, 585), 0.46, BACKGROUND if enabled else MUTED)

    button(16, 220, 'USAR FOTO [U]' if reviewing else 'CAPTURAR [C]', not sending)
    if reviewing:
        button(235, 470, 'TIRAR OUTRA [R]', not sending, MUTED)
    else:
        button(235, 470, 'DETALHES [I]', True, MUTED)
    button(500, 810, 'PAREADO / SESSAO [P]' if status.session_valid else 'CONECTAR SESSAO [P]',
           not sending, GREEN if status.session_valid else ORANGE)
    button(824, 944, 'MODO [A]', not reviewing and not sending, MUTED)
    _lines(canvas, capture_notice, 28, 643, 902, 2, TEXT, 0.46)
    _lines(canvas, 'API: ' + connection_notice, 28, 681, 902, 1, MUTED, 0.39)
    mode = 'AUTO: pronto' if auto_ready else 'AUTO: estabilize' if armed else 'AUTO: retire a fruta'
    _text(canvas, (mode if automatic else 'MANUAL') +
          f' | IA: {detection.get("inference_ms", 0):.0f} ms | I: detalhes | A: modo | Q: sair',
          (18, 709), 0.38, MUTED)
    _text(canvas, datetime.now().strftime('%H:%M:%S'), (868, 709), 0.38, MUTED)
    if details:
        cv2.rectangle(canvas, (16, 84), (648, 534), PANEL, -1)
        _text(canvas, 'DETALHES / [ ]: paginas / I: voltar', (30, 112), 0.46, ORANGE)
        pages = max(1, (len(_wrapped(str(status.analysis_detail), 602, 0.42)) + 6) // 7)
        page = details_page % (pages + 1)
        if page == pages:
            _render_evaluation_details(canvas, status, tones)
            return canvas
        _text(canvas, 'Amostra: ' + (status.sample or 'nenhuma'), (30, 142), 0.4)
        _lines(canvas, status.analysis, 30, 171, 602, 2, tones[status.analysis_tone])
        _text(canvas, f'Motivo ({page + 1}/{pages}) | ]: proxima pagina / Web API:', (30, 200), 0.36, MUTED)
        _lines(canvas, status.analysis_detail, 30, 224, 602, 7, TEXT, offset=page * 7, truncate=False)
        _lines(canvas, status.registration, 30, 365, 602, 1, tones[status.registration_tone])
        _text(canvas, 'Registro da amostra: ' + (status.registration_sample or 'nenhuma'), (30, 392), 0.4)
        _text(canvas, 'analysis_id: ' + (status.analysis_id or 'nao confirmado'), (30, 419), 0.4)
        _lines(canvas, status.registration_detail, 30, 448, 602, 4)
    return canvas
