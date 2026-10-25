"""Segmentação HSV compartilhada pela bancada e pelo classificador calibrado.

Encontrar um contorno não identifica a espécie da fruta.
"""

import math
from dataclasses import dataclass
from typing import Any


class VisionFailure(Exception):
    pass


def validate_ranges(ranges):
    if not isinstance(ranges, list) or not ranges:
        raise VisionFailure('Faixas HSV precisam ser calibradas.')
    for limits in ranges:
        if (
            not isinstance(limits, (list, tuple))
            or len(limits) != 2
            or any(not isinstance(vector, (list, tuple)) or len(vector) != 3 for vector in limits)
        ):
            raise VisionFailure('Cada faixa HSV exige dois vetores de três canais.')
        for index, maximum in enumerate((179, 255, 255)):
            if any(type(vector[index]) is not int for vector in limits):
                raise VisionFailure('Faixas HSV exigem canais inteiros, sem truncamento.')
            if not 0 <= limits[0][index] <= limits[1][index] <= maximum:
                raise VisionFailure('Limites HSV inválidos: o mínimo não pode exceder o máximo.')


def validate_frame(frame):
    import numpy as np

    if (
        frame is None
        or getattr(frame, 'ndim', 0) != 3
        or frame.shape[2] != 3
        or frame.size == 0
        or frame.shape[0] * frame.shape[1] > 16000000
        or frame.dtype != np.uint8
    ):
        raise VisionFailure('Imagem inválida ou acima do limite de memória.')


def mask_for(hsv, ranges):
    import cv2
    import numpy as np

    validate_ranges(ranges)
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lower, upper in ranges:
        mask |= cv2.inRange(hsv, np.array(lower, dtype=np.uint8), np.array(upper, dtype=np.uint8))
    return mask


@dataclass(frozen=True)
class SegmentedFruit:
    hsv: Any
    mask: Any
    contour: Any
    area: float
    perimeter: float
    touches_border: bool


def segment_fruit(frame, ranges, minimum_area=0) -> SegmentedFruit:
    import cv2

    validate_frame(frame)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    return _segment_mask(hsv, mask_for(hsv, ranges), minimum_area)


def _segment_mask(hsv, selected_mask, minimum_area):
    import cv2
    import numpy as np

    if (
        type(minimum_area) not in (int, float)
        or not math.isfinite(minimum_area)
        or minimum_area < 0
    ):
        raise VisionFailure('Área mínima de segmentação inválida.')
    candidates, _ = cv2.findContours(selected_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not candidates:
        raise VisionFailure('Nenhuma região candidata encontrada. Confira a fruta e as faixas HSV.')
    contour = max(candidates, key=cv2.contourArea)
    area, perimeter = cv2.contourArea(contour), cv2.arcLength(contour, True)
    if area < minimum_area or area <= 0 or perimeter <= 0:
        raise VisionFailure('Segmentação insuficiente; nenhuma classe foi produzida.')
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    cv2.drawContours(mask, [contour], -1, 255, cv2.FILLED)
    x, y, width, height = cv2.boundingRect(contour)
    touches_border = x == 0 or y == 0 or x + width == hsv.shape[1] or y + height == hsv.shape[0]
    return SegmentedFruit(hsv, mask, contour, area, perimeter, touches_border)


def segment_guided(frame, rectangle, minimum_area=0) -> SegmentedFruit:
    """GrabCut assistido, somente para uma imagem congelada da bancada.

    O retângulo deve envolver a fruta e incluir um pouco de fundo. Não reconhece
    espécie nem garante separar uma mão que esteja sobreposta à casca.
    """
    import cv2
    import numpy as np

    validate_frame(frame)
    if (
        not isinstance(rectangle, (tuple, list))
        or len(rectangle) != 4
        or any(type(value) is not int for value in rectangle)
    ):
        raise VisionFailure('Seleção inválida: marque um retângulo ao redor da fruta.')
    x, y, width, height = rectangle
    if width <= 0 or height <= 0:
        raise VisionFailure('Seleção cancelada. Pressione B para selecionar a fruta.')
    if x <= 0 or y <= 0 or x + width >= frame.shape[1] or y + height >= frame.shape[0]:
        raise VisionFailure(
            'Deixe uma margem de fundo em volta da seleção, sem tocar as bordas da foto.'
        )
    # Limita custo e memória do ajuste interativo, inclusive em fotos grandes.
    scale = min(1, 960 / frame.shape[1], 960 / frame.shape[0])
    work = cv2.resize(
        frame, (max(1, round(frame.shape[1] * scale)), max(1, round(frame.shape[0] * scale)))
    )
    sx, sy = work.shape[1] / frame.shape[1], work.shape[0] / frame.shape[0]
    left, top = max(1, math.floor(x * sx)), max(1, math.floor(y * sy))
    right, bottom = (
        min(work.shape[1] - 1, math.ceil((x + width) * sx)),
        min(work.shape[0] - 1, math.ceil((y + height) * sy)),
    )
    if right - left < 3 or bottom - top < 3:
        raise VisionFailure('Seleção pequena demais. Marque a fruta inteira e uma margem de fundo.')
    labels = np.zeros(work.shape[:2], dtype=np.uint8)
    try:
        cv2.grabCut(
            work,
            labels,
            (left, top, right - left, bottom - top),
            np.zeros((1, 65), np.float64),
            np.zeros((1, 65), np.float64),
            3,
            cv2.GC_INIT_WITH_RECT,
        )
    except cv2.error as exc:
        raise VisionFailure(
            'Não foi possível separar o objeto. Tente outra seleção ou outra foto com mais contraste.'
        ) from exc
    selected = np.where((labels == cv2.GC_FGD) | (labels == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    selected = cv2.resize(
        selected, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST
    )
    segment = _segment_mask(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV), selected, minimum_area)
    bx, by, bw, bh = cv2.boundingRect(segment.contour)
    if bx <= x or by <= y or bx + bw >= x + width or by + bh >= y + height:
        raise VisionFailure(
            'O contorno encostou no limite da seleção. Marque uma área maior em volta da fruta.'
        )
    return segment


def measure_metrics(segment: SegmentedFruit, orange_ranges=None, abnormal_ranges=None):
    import cv2

    pixels = cv2.countNonZero(segment.mask)
    if not pixels:
        raise VisionFailure('Região da fruta vazia.')
    x, y, width, height = cv2.boundingRect(segment.contour)
    cropped = segment.mask[y : y + height, x : x + width]

    def ratio(ranges):
        if not ranges:
            return None  # Sem amostra não significa zero medido.
        return (
            cv2.countNonZero(cv2.bitwise_and(mask_for(segment.hsv, ranges), segment.mask)) / pixels
        )

    return {
        'orange_color_ratio': ratio(orange_ranges),
        'abnormal_region_ratio': ratio(abnormal_ranges),
        'circularity': 4 * math.pi * segment.area / (segment.perimeter * segment.perimeter),
        'asymmetry': cv2.countNonZero(cv2.bitwise_xor(cropped, cv2.flip(cropped, 1)))
        / (2 * pixels),
    }
