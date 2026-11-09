"""Segmentação HSV compartilhada pela bancada e pelo classificador calibrado.

Encontrar um contorno não identifica a espécie da fruta.
"""

import math
from dataclasses import dataclass
from typing import Any


class VisionFailure(Exception):
    pass


class SelectionBoundaryFailure(VisionFailure):
    """Objeto alcançou o retângulo de segmentação, não necessariamente a foto."""


class ColorLocateFailure(VisionFailure):
    """Recusa da localização por cor, com um código curto para o aviso ao vivo."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


STAIN_METHOD = 'contrast-v1'
STAIN_WORK_DIAMETER = 400


def _ellipse(size):
    import cv2

    size = max(3, int(size)) | 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def _square(size):
    import cv2

    size = max(3, int(size)) | 1
    return cv2.getStructuringElement(cv2.MORPH_RECT, (size, size))


def validate_stain_rule(rule):
    """Regra opcional de manchas por contraste; None mantém as faixas abnormal_hsv."""
    if rule is None:
        return None
    if not isinstance(rule, dict) or rule.get('method') != STAIN_METHOD:
        raise VisionFailure(f'abnormal_detection exige method={STAIN_METHOD}.')
    contrast = rule.get('min_relative_contrast')
    if type(contrast) not in (int, float) or not 0.05 <= contrast <= 0.9:
        raise VisionFailure('min_relative_contrast precisa estar entre 0.05 e 0.9.')
    highlight = rule.get('highlight_percentile', 90)
    if type(highlight) not in (int, float) or not 50 <= highlight <= 100:
        raise VisionFailure('highlight_percentile precisa estar entre 50 e 100.')
    size = rule.get('max_stain_fraction', 0.25)
    if type(size) not in (int, float) or not 0.05 <= size <= 0.5:
        raise VisionFailure('max_stain_fraction precisa estar entre 0.05 e 0.5.')
    return rule


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


def segment_single_by_color(frame, ranges, minimum_area=0, dominance=0.25) -> SegmentedFruit:
    """Localiza uma única fruta pela cor, para quando o detector não a confirma.

    Pressupõe fundo neutro (branco/cinza). Recusa duas regiões de tamanho
    comparável e frutas que encostam na borda da foto: nunca classifica pedaços.
    Faixas finas de fundo com cor parecida (borda de teclado, reflexo da mesa)
    que tocam a fruta são cortadas antes de conferir a borda.
    """
    import cv2

    validate_frame(frame)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = mask_for(hsv, ranges)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel), cv2.MORPH_CLOSE, kernel)
    candidates, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not candidates:
        raise ColorLocateFailure(
            'none', 'Nenhuma fruta encontrada pela cor. Use fundo liso e a fruta inteira no quadro.'
        )
    areas = sorted((cv2.contourArea(contour) for contour in candidates), reverse=True)
    if len(areas) > 1 and areas[1] >= areas[0] * dominance:
        raise ColorLocateFailure(
            'multiple', 'Mais de uma fruta ou objeto colorido na foto. Use uma fruta por captura.'
        )
    filled = _cut_bridges(_filled(mask.shape, max(candidates, key=cv2.contourArea)))
    if cv2.countNonZero(filled) < minimum_area:
        raise ColorLocateFailure(
            'small', 'Fruta pequena demais na foto. Aproxime a câmera ou a fruta.'
        )
    segment = _segment_mask(hsv, filled, minimum_area)
    if segment.touches_border:
        raise ColorLocateFailure(
            'border', 'A fruta encosta na borda da foto. Enquadre a fruta inteira com fundo ao redor.'
        )
    return segment


def _filled(shape, contour):
    """Preenche manchas internas: uma mancha escura continua fazendo parte da fruta."""
    import cv2
    import numpy as np

    filled = np.zeros(shape, dtype=np.uint8)
    cv2.drawContours(filled, [contour], -1, 255, cv2.FILLED)
    return filled


def _cut_bridges(filled):
    """Remove pontes finas até objetos do fundo, mantendo o maior pedaço.

    A abertura usa ~1/10 do diâmetro: some com faixas estreitas (reflexos,
    bordas de objetos) sem comer a fruta, que é larga em todas as direções.
    """
    import cv2

    area = cv2.countNonZero(filled)
    if not area:
        return filled
    diameter = 2 * math.sqrt(area / math.pi)
    opened = cv2.morphologyEx(filled, cv2.MORPH_OPEN, _ellipse(max(9, diameter / 10)))
    pieces, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not pieces:
        return filled
    return _filled(filled.shape, max(pieces, key=cv2.contourArea))


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
        raise SelectionBoundaryFailure(
            'O contorno encostou no limite da seleção. Marque uma área maior em volta da fruta.'
        )
    return segment


def segment_detected(frame, box, minimum_area=0):
    """Amplia um recorte automático apertado sem ignorar a proteção de borda."""
    validate_frame(frame)
    if (
        not isinstance(box, (tuple, list)) or len(box) != 4
        or any(type(value) is not int for value in box)
    ):
        raise VisionFailure('Caixa de detecção inválida; não foi possível avaliar a fruta.')
    x, y, width, height = box
    if width <= 0 or height <= 0:
        raise VisionFailure('Caixa de detecção vazia; não foi possível avaliar a fruta.')
    if x <= 0 or y <= 0 or x + width >= frame.shape[1] or y + height >= frame.shape[0]:
        raise VisionFailure(
            'A detecção toca a borda da foto. Afaste a fruta/câmera e enquadre a fruta inteira com fundo ao redor.'
        )
    previous = None
    for fraction in (0.10, 0.25, 0.50):
        margin = max(3, math.ceil(max(width, height) * fraction))
        left, top = max(1, x - margin), max(1, y - margin)
        right, bottom = min(frame.shape[1] - 1, x + width + margin), min(frame.shape[0] - 1, y + height + margin)
        rectangle = (left, top, right - left, bottom - top)
        if rectangle == previous:
            break
        previous = rectangle
        try:
            return segment_guided(frame, rectangle, minimum_area)
        except SelectionBoundaryFailure:
            continue
    raise SelectionBoundaryFailure(
        'O contorno encostou no limite do recorte mesmo após ampliá-lo. '
        'Afaste a fruta, deixe fundo ao redor e confira iluminação/contraste. Nenhuma categoria foi produzida.'
    )


def contrast_stain_mask(segment: SegmentedFruit, rule):
    """Manchas = pontos bem mais escuros que a casca ao redor (black-hat no brilho).

    A sombra é um degradê largo e não é contada; mancha, pinta ou podridão é um
    vale estreito de brilho. O contraste é relativo ao brilho local, então vale
    tanto na parte iluminada quanto na sombreada. O brilho é limitado a um
    percentil da fruta para que o reflexo da luz não faça a casca vizinha parecer
    escura, e a faixa da borda (escurecida pela curvatura) fica de fora.
    """
    import cv2
    import numpy as np

    x, y, width, height = cv2.boundingRect(segment.contour)
    diameter = 2 * math.sqrt(segment.area / math.pi)
    # Recorte com margem: o custo não depende do tamanho da foto inteira.
    margin = math.ceil(diameter * 0.3) + 8
    top, left = max(0, y - margin), max(0, x - margin)
    bottom = min(segment.mask.shape[0], y + height + margin)
    right = min(segment.mask.shape[1], x + width + margin)
    inside = segment.mask[top:bottom, left:right]
    value = segment.hsv[top:bottom, left:right, 2]
    # Fruta grande (de perto) é medida numa cópia com ~STAIN_WORK_DIAMETER px: o filtro
    # cresce com o quadrado do diâmetro e travaria o Pi; a proporção das manchas não muda.
    scale = min(1.0, STAIN_WORK_DIAMETER / diameter)
    if scale < 1:
        size = (max(1, round(inside.shape[1] * scale)), max(1, round(inside.shape[0] * scale)))
        inside = cv2.resize(inside, size, interpolation=cv2.INTER_NEAREST)
        value = cv2.resize(value, size, interpolation=cv2.INTER_AREA)
        diameter *= scale
    cap = float(np.percentile(value[inside > 0], rule.get('highlight_percentile', 90)))
    # Fora da fruta vale 0: o fundo claro não cria contraste falso na borda.
    value = np.where(inside > 0, np.minimum(value, cap), 0).astype(np.uint8)
    # Manchas até esta fração do diâmetro; áreas escuras maiores contam pela borda.
    # Quadrado: o OpenCV calcula em tempo constante por pixel (a elipse custa
    # o quadrado do tamanho); nas fotos da bancada o resultado é o mesmo.
    kernel = _square(max(15, diameter * rule.get('max_stain_fraction', 0.25)))
    closed = cv2.morphologyEx(value, cv2.MORPH_CLOSE, kernel).astype(np.float32)
    contrast = (closed - value) / np.maximum(closed, 1)
    inner = cv2.erode(inside, _square(max(5, diameter / 15)))
    found = np.where((contrast > rule['min_relative_contrast']) & (inner > 0), 255, 0).astype(np.uint8)
    if scale < 1:
        found = cv2.resize(found, (right - left, bottom - top), interpolation=cv2.INTER_NEAREST)
    stains = np.zeros(segment.mask.shape, dtype=np.uint8)
    stains[top:bottom, left:right] = cv2.bitwise_and(found, segment.mask[top:bottom, left:right])
    return stains


def measure_metrics(segment: SegmentedFruit, orange_ranges=None, abnormal_ranges=None, stain_rule=None):
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

    stain_rule = validate_stain_rule(stain_rule)
    return {
        'orange_color_ratio': ratio(orange_ranges),
        'abnormal_region_ratio': ratio(abnormal_ranges)
        if stain_rule is None
        else cv2.countNonZero(contrast_stain_mask(segment, stain_rule)) / pixels,
        'circularity': 4 * math.pi * segment.area / (segment.perimeter * segment.perimeter),
        'asymmetry': cv2.countNonZero(cv2.bitwise_xor(cropped, cv2.flip(cropped, 1)))
        / (2 * pixels),
    }
