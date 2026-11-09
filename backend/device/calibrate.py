"""Gera e confere a calibração de cor (Boa / Verde / Passou) com fotos rotuladas.

Uso, na pasta que contém device/:

    python -m device.calibrate --fotos calibration --saida device/calibracao-laranja.json
    python -m device.calibrate --fotos calibration --saida device/calibracao-laranja.json --marcar-validada

As subpastas de --fotos definem o rótulo humano de cada foto:
    aprovadas | boa     -> APROVADA (boa)
    atencao   | verde   -> ATENCAO  (verde / intermediária)
    revisar   | passou  -> REVISAR  (passou / manchas)

Os limiares partem dos valores abaixo, medidos nas fotos de referência do projeto.
A calibração só é marcada como validada se TODAS as fotos rotuladas que puderem ser
avaliadas forem classificadas como o rótulo humano. Poucas fotos não garantem
acurácia em campo: tire mais fotos com a mesma luz, fundo e distância da bancada.
"""

import argparse
import copy
import json
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path

LABELS = {
    'aprovadas': 'APROVADA', 'aprovada': 'APROVADA', 'boa': 'APROVADA', 'boas': 'APROVADA',
    'atencao': 'ATENCAO', 'verde': 'ATENCAO', 'verdes': 'ATENCAO',
    'revisar': 'REVISAR', 'passou': 'REVISAR', 'passadas': 'REVISAR', 'ruim': 'REVISAR',
}
NAMES = {'APROVADA': 'Boa', 'ATENCAO': 'Verde/atenção', 'REVISAR': 'Passou'}
EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}

# Faixas HSV do OpenCV (H 0-179, S/V 0-255).
DEFAULT_CALIBRATION = {
    'version': 'laranja-cor-v3',
    'validated': False,
    'segmentation_method': 'yolox-s-grabcut-v1',
    'color_fallback': True,
    'minimum_fruit_area_pixels': 8000,
    # Casca de laranja madura até verde; fundo neutro (baixa saturação) fica de fora.
    'fruit_hsv': [[[5, 70, 60], [90, 255, 255]]],
    # Casca madura: laranja até amarela (laranja-pera), sem a faixa do verde.
    'orange_hsv': [[[5, 80, 90], [30, 255, 255]]],
    # Faixas antigas de manchas (usadas só sem abnormal_detection).
    'abnormal_hsv': [[[0, 0, 0], [179, 255, 70]], [[0, 40, 30], [30, 255, 140]]],
    # Manchas = pontos >=25% mais escuros que a casca ao redor; sombra e reflexo não contam.
    'abnormal_detection': {
        'method': 'contrast-v1',
        'min_relative_contrast': 0.25,
        'max_stain_fraction': 0.25,
        'highlight_percentile': 90,
    },
    'score_rules': {
        'orange_color_ratio': {'low': 0.3, 'high': 0.85, 'direction': 'higher', 'weight': 0.35},
        'abnormal_region_ratio': {'low': 0.03, 'high': 0.15, 'direction': 'lower', 'weight': 0.45},
        'circularity': {'low': 0.5, 'high': 0.85, 'direction': 'higher', 'weight': 0.1},
        'asymmetry': {'low': 0.05, 'high': 0.3, 'direction': 'lower', 'weight': 0.1},
    },
    'attention_min_score': 45,
    'approval_min_score': 75,
    'classification_rules': {
        'method': 'ripeness-rules-v1',
        # Tom 28-30 é casca amarela iluminada nesta câmera; verde de verdade fica acima.
        'green_hsv': [[[31, 50, 50], [90, 255, 255]]],
        'verde_min_green_ratio': 0.35,
        'passou_min_abnormal_ratio': 0.12,
        'boa_max_abnormal_ratio': 0.05,
        'boa_max_green_ratio': 0.20,
        'boa_min_orange_ratio': 0.60,
    },
}


def load_frame(path, max_width=1280):
    import cv2
    import numpy as np

    frame = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return None
    if frame.shape[1] > max_width:
        scale = max_width / frame.shape[1]
        frame = cv2.resize(frame, (max_width, round(frame.shape[0] * scale)))
    return frame


def evaluate(path, calibration, detector=None):
    """Mesmo caminho da câmera: detector + GrabCut; senão, localização pela cor."""
    from .segmentation import (
        VisionFailure,
        measure_metrics,
        segment_detected,
        segment_fruit,
        segment_single_by_color,
    )
    from .vision import CalibratedVision

    frame = load_frame(path)
    if frame is None:
        return {'error': 'imagem ilegível'}
    vision = CalibratedVision({**calibration, 'validated': True})
    minimum = calibration['minimum_fruit_area_pixels']
    note, segment = '', None
    if detector is not None:
        detection = detector.detect(frame)
        if detection['status'] == 'detected':
            try:
                segment = segment_detected(frame, detection['box'], minimum)
                note = 'detector'
            except VisionFailure:
                segment = None
    if segment is None:
        try:
            segment = segment_single_by_color(frame, calibration['fruit_hsv'], minimum)
            note = 'cor'
        except VisionFailure as exc:
            # Mede mesmo assim para conferir os limiares, mas avisa que a câmera recusaria.
            segment = segment_fruit(frame, calibration['fruit_hsv'], 0)
            note = f'recusada na câmera: {exc}'
    if segment.touches_border:
        # A câmera recusaria; mede só para conferir os limiares de cor.
        note = note if note.startswith('recusada') else 'recusada na câmera: fruta encosta na borda'
        segment = replace(segment, touches_border=False)
    classified = vision.classify_segment(segment)
    rules = calibration['classification_rules']
    return {
        'predicted': classified['classification'],
        'orange': classified['metrics']['orange_color_ratio'],
        'green': measure_metrics(segment, rules['green_hsv'])['orange_color_ratio'],
        'abnormal': classified['metrics']['abnormal_region_ratio'],
        'score': classified['metrics']['visual_score'],
        'note': note,
    }


def collect(folder):
    photos = []
    for child in sorted(Path(folder).iterdir()):
        label = LABELS.get(child.name.lower())
        if child.is_dir() and label:
            photos += [
                (file, label) for file in sorted(child.iterdir())
                if file.suffix.lower() in EXTENSIONS
            ]
    return photos


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--fotos', required=True, help='Pasta com subpastas aprovadas/atencao/revisar.')
    parser.add_argument('--saida', required=True, help='Arquivo JSON de calibração a gerar.')
    parser.add_argument('--base', help='Calibração JSON existente para conferir/ajustar.')
    parser.add_argument('--versao', help='Identificador da versão gerada.')
    parser.add_argument('--sem-detector', action='store_true', help='Não carrega o modelo YOLOX.')
    parser.add_argument(
        '--marcar-validada', action='store_true',
        help='Marca validated=true somente se todas as fotos rotuladas forem acertadas.',
    )
    args = parser.parse_args(argv)
    calibration = copy.deepcopy(
        json.loads(Path(args.base).read_text(encoding='utf-8')) if args.base else DEFAULT_CALIBRATION
    )
    calibration['version'] = args.versao or f'laranja-cor-v3-{date.today():%Y%m%d}'
    photos = collect(args.fotos)
    if not photos:
        print('Nenhuma foto encontrada. Use subpastas aprovadas/, atencao/ e revisar/.')
        return 2
    detector = None
    if not args.sem_detector:
        from .detector import OrangeDetector

        detector = OrangeDetector()
    print(f'{"foto":28} {"rótulo":14} {"previsto":14} laranja  verde  manchas  ok  observação')
    hits, total, rows = 0, 0, []
    for path, label in photos:
        result = evaluate(path, calibration, detector)
        if 'error' in result:
            print(f'{path.name[:28]:28} {NAMES[label]:14} {"-":14} {result["error"]}')
            continue
        ok = result['predicted'] == label
        total += 1
        hits += ok
        rows.append({'foto': path.name, 'rotulo': label, **result, 'acerto': ok})
        print(
            f'{path.name[:28]:28} {NAMES[label]:14} {NAMES[result["predicted"]]:14} '
            f'{result["orange"]:6.0%} {result["green"]:6.0%} {result["abnormal"]:7.0%}  '
            f'{"sim" if ok else "NÃO":3} {result["note"]}'
        )
    accuracy = hits / total if total else 0
    print(f'\nAcertos: {hits}/{total} ({accuracy:.0%}).')
    calibration['validated'] = bool(args.marcar_validada and total and hits == total)
    calibration['validation_report'] = {
        'photos': total, 'hits': hits, 'date': date.today().isoformat(),
        'note': 'Conferência com fotos rotuladas; avalia apenas a superfície visível.',
    }
    output = Path(args.saida)
    output.write_text(json.dumps(calibration, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Calibração gravada em {output} (validated={str(calibration["validated"]).lower()}).')
    if args.marcar_validada and not calibration['validated']:
        print('Não marcada como validada: corrija as fotos/limiares que erraram e rode de novo.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
