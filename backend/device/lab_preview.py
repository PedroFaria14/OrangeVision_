"""Prévia local, sem chamadas à API e sem presumir identificação da espécie."""

from textwrap import wrap
from unicodedata import normalize

from .segmentation import VisionFailure, measure_metrics, segment_fruit, validate_frame


def preview_frame(
    frame, calibration, classifier=None, *, guided_segment=None, frozen=False, notice=None
):
    """Retorna painel BGR e medições; não altera imagem nem calibração recebidas."""
    import cv2
    import numpy as np

    validate_frame(frame)
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    outline = frame.copy()
    snapshot = {
        'status': 'awaiting_sample',
        'reason': 'Espaço congela a imagem; B seleciona a fruta inteira. F ajusta as cores no modo avançado.',
        'area_pixels': None,
        'metrics': {},
        'classification': None,
        'visual_score': None,
        'species_verified': False,
        'frozen': frozen,
        'segmentation_method': 'guided-grabcut' if guided_segment is not None else 'hsv',
    }
    if notice:
        snapshot.update(status='not_evaluable', reason=notice)
    elif guided_segment is not None or calibration.get('fruit_hsv'):
        try:
            segment = (
                guided_segment
                if guided_segment is not None
                else segment_fruit(
                    frame,
                    calibration['fruit_hsv'],
                    calibration.get('minimum_fruit_area_pixels') or 0,
                )
            )
            mask = segment.mask
            snapshot['area_pixels'] = segment.area
            color = (0, 0, 220) if segment.touches_border else (40, 180, 40)
            cv2.drawContours(outline, [segment.contour], -1, color, max(1, frame.shape[1] // 300))
            if segment.touches_border:
                raise VisionFailure(
                    'Contorno toca a borda. Afaste a fruta ou ajuste a faixa para excluir o fundo.'
                )
            snapshot['metrics'] = measure_metrics(
                segment, calibration.get('orange_hsv'), calibration.get('abnormal_hsv')
            )
            snapshot.update(
                status='candidate',
                reason=(
                    'Seleção assistida: confira se a mão e o fundo ficaram de fora. Sem categoria automática.'
                    if guided_segment is not None
                    else 'Região candidata encontrada. Confira o contorno: a espécie não foi confirmada.'
                ),
            )
            if (
                classifier is not None
                and calibration.get('validated') is True
                and guided_segment is None
            ):
                result = classifier.analyze(frame)
                snapshot.update(
                    classification=result['classification'],
                    visual_score=result['metrics']['visual_score'],
                )
        except VisionFailure as exc:
            snapshot.update(status='not_evaluable', reason=str(exc), metrics={})
    return render_panel(frame, mask, outline, snapshot), snapshot


def render_panel(frame, mask, outline, snapshot):
    import cv2
    import numpy as np

    width, height = 360, 270
    panel = np.full((height + 210, width * 3, 3), 245, dtype=np.uint8)

    def text(message, position, scale=0.48, color=(35, 35, 35)):
        # A fonte Hershey do OpenCV não oferece acentuação; terminal/JSON mantêm UTF-8.
        ascii_text = normalize('NFKD', message).encode('ascii', 'ignore').decode()
        cv2.putText(
            panel, ascii_text, position, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA
        )

    for index, (image, title) in enumerate(
        (
            (frame, 'Original - CONGELADA' if snapshot.get('frozen') else 'Original - ao vivo'),
            (cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR), 'Mascara - maior regiao'),
            (outline, 'Contorno candidato (nao confirma especie)'),
        )
    ):
        scale = min(width / image.shape[1], height / image.shape[0])
        w, h = max(1, round(image.shape[1] * scale)), max(1, round(image.shape[0] * scale))
        resized = cv2.resize(
            image, (w, h), interpolation=cv2.INTER_NEAREST if index == 1 else cv2.INTER_AREA
        )
        x, y = index * width + (width - w) // 2, 28 + (height - h) // 2
        panel[y : y + h, x : x + w] = resized
        text(title, (index * width + 8, 19), scale=0.43)

    status = {
        'awaiting_sample': 'AGUARDANDO AJUSTE',
        'candidate': 'REGIAO CANDIDATA',
        'not_evaluable': 'NAO FOI POSSIVEL AVALIAR',
    }[snapshot['status']]
    text(status, (12, 324), scale=0.6)
    for index, line in enumerate(wrap(snapshot['reason'], width=125)[:2]):
        text(line, (12, 348 + index * 20))
    metrics = snapshot['metrics']

    def number(value, percent=False):
        return '---' if value is None else (f'{value * 100:.1f}%' if percent else f'{value:.3f}')

    text(
        f'Area: {number(snapshot["area_pixels"])} px | Circularidade: {number(metrics.get("circularity"))} | Assimetria: {number(metrics.get("asymmetry"))}',
        (12, 392),
    )
    text(
        f'Cor laranja: {number(metrics.get("orange_color_ratio"), True)} | Regioes anormais: {number(metrics.get("abnormal_region_ratio"), True)}',
        (12, 414),
    )
    unavailable = (
        'indisponivel - selecao assistida'
        if snapshot.get('segmentation_method') == 'guided-grabcut'
        else 'indisponivel - calibracao nao validada'
    )
    text(
        f'Categoria: {snapshot["classification"] or unavailable} | Score: {number(snapshot["visual_score"])}',
        (12, 436),
    )
    text(
        'Espaco: congelar/voltar | B: selecionar fruta | S: foto | F/O/D: cores | R: limpar | G: rascunho | N/P | Q: sair',
        (12, 464),
        scale=0.44,
    )
    return panel
