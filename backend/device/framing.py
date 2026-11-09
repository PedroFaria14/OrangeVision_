"""Aviso de enquadramento no vídeo ao vivo: rápido e só orienta a captura.

Usa a mesma localização por cor da análise, numa cópia reduzida do quadro, para
antecipar as recusas mais comuns (borda, fruta pequena, duas frutas) e avisar de
fundo colorido ou pouca luz. Não classifica a fruta e não bloqueia a captura.
"""

from dataclasses import dataclass
from typing import Any

WIDTH = 320
BEST = 'Enquadramento bom. Pressione C para capturar.'
MESSAGES = {
    'none': 'Nenhuma fruta visivel: coloque a laranja no centro, sobre fundo liso.',
    'multiple': 'Mais de um objeto colorido: deixe so uma laranja no quadro.',
    'small': 'Fruta pequena: aproxime a camera ou a fruta.',
    'border': 'Fruta encostando na borda: centralize e deixe fundo em volta.',
}


@dataclass(frozen=True)
class FramingHint:
    tone: str  # 'green' (bom), 'orange' (atenção) ou 'red' (a análise deve recusar)
    message: str
    contour: Any = None  # contorno em coordenadas do quadro original


def framing_hint(frame, calibration):
    import cv2
    import numpy as np

    from .segmentation import (
        ColorLocateFailure,
        VisionFailure,
        mask_for,
        segment_single_by_color,
        validate_frame,
    )

    if not calibration or not calibration.get('fruit_hsv') or frame is None:
        return None
    validate_frame(frame)  # quadro inválido: sem dica (safe_framing_hint devolve None)
    scale = min(1.0, WIDTH / frame.shape[1])
    small = frame if scale == 1 else cv2.resize(
        frame,
        (max(1, round(frame.shape[1] * scale)), max(1, round(frame.shape[0] * scale))),
        interpolation=cv2.INTER_AREA,
    )
    minimum = (calibration.get('minimum_fruit_area_pixels') or 0) * scale * scale
    try:
        segment = segment_single_by_color(small, calibration['fruit_hsv'], minimum)
    except ColorLocateFailure as exc:
        return FramingHint('red', MESSAGES.get(exc.code, MESSAGES['none']))
    except VisionFailure:
        return FramingHint('red', MESSAGES['none'])
    contour = np.round(segment.contour / scale).astype(np.int32)
    frame_area = small.shape[0] * small.shape[1]
    fraction = segment.area / frame_area
    if fraction > 0.45:
        return FramingHint('orange', 'Fruta muito perto: afaste um pouco a camera.', contour)
    if fraction < 0.05:
        return FramingHint(
            'orange', 'Fruta pequena: aproxime para ocupar ~1/3 da imagem.', contour
        )
    # Cor de fruta fora dela (com folga): teclado, mesa ou objetos coloridos no fundo.
    around = cv2.dilate(
        segment.mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    )
    color = mask_for(segment.hsv, calibration['fruit_hsv'])
    stray = cv2.countNonZero(cv2.bitwise_and(color, cv2.bitwise_not(around))) / frame_area
    if stray > 0.06:
        return FramingHint(
            'orange', 'Fundo com cor parecida com a fruta: use fundo branco ou cinza.', contour
        )
    brightness = float(np.median(segment.hsv[..., 2][segment.mask > 0]))
    if brightness < 90:
        return FramingHint('orange', 'Pouca luz na fruta: ilumine de frente ou de cima.', contour)
    return FramingHint('green', BEST, contour)


def safe_framing_hint(frame, calibration):
    """Nunca derruba a janela: sem dica quando a checagem falha."""
    try:
        return framing_hint(frame, calibration)
    except Exception:
        return None
