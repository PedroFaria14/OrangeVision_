"""Bancada local de imagens e câmera; não cria inspeções nem envia análises."""

import argparse
import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4


def sample_range(frame, rectangle):
    import cv2
    import numpy as np

    x, y, width, height = map(int, rectangle)
    if width <= 0 or height <= 0:
        raise ValueError('Seleção cancelada; nenhuma amostra adicionada.')
    if x < 0 or y < 0 or x + width > frame.shape[1] or y + height > frame.shape[0]:
        raise ValueError('Seleção fora da imagem.')
    pixels = cv2.cvtColor(frame[y : y + height, x : x + width], cv2.COLOR_BGR2HSV)
    lower = np.floor(np.percentile(pixels.reshape(-1, 3), 2, axis=0)).astype(int)
    upper = np.ceil(np.percentile(pixels.reshape(-1, 3), 98, axis=0)).astype(int)
    return [lower.tolist(), upper.tolist()]


def image_paths(source):
    path = Path(source)
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise ValueError('Arquivo ou pasta de imagens não encontrado.')
    paths = sorted(
        p
        for p in path.rglob('*')
        if p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.webp'} and p.is_file()
    )
    if not paths:
        raise ValueError('A pasta não contém imagens suportadas.')
    return paths


def source_rectangle(rectangle, source_shape, display_shape):
    """Converte seleção na miniatura para pixels da imagem original."""
    import math

    x, y, width, height = rectangle
    if width <= 0 or height <= 0:
        return (0, 0, 0, 0)
    sx, sy = source_shape[1] / display_shape[1], source_shape[0] / display_shape[0]
    left, top = max(0, math.floor(x * sx)), max(0, math.floor(y * sy))
    right = min(source_shape[1], math.ceil((x + width) * sx))
    bottom = min(source_shape[0], math.ceil((y + height) * sy))
    return left, top, right - left, bottom - top


SLIDERS = (
    ('H min', 0, 0, 179),
    ('H max', 1, 0, 179),
    ('S min', 0, 1, 255),
    ('S max', 1, 1, 255),
    ('V min', 0, 2, 255),
    ('V max', 1, 2, 255),
)
HSV_WINDOW = 'HSV - ultima amostra F'
MAIN_WINDOW = 'OrangeVision - bancada'


def set_sliders(limits):
    import cv2

    for name, side, channel, _ in SLIDERS:
        cv2.setTrackbarPos(name, HSV_WINDOW, limits[side][channel])


def open_hsv_controls():
    import cv2

    cv2.namedWindow(HSV_WINDOW, cv2.WINDOW_NORMAL)
    for name, _, _, maximum in SLIDERS:
        cv2.createTrackbar(name, HSV_WINDOW, 0, maximum, lambda _value: None)
    cv2.resizeWindow(HSV_WINDOW, 600, 300)


def edited(draft):
    draft['validated'] = False
    if not str(draft.get('version', '')).startswith('rascunho-'):
        draft['version'] = 'rascunho-' + uuid4().hex[:12]


def save_draft(draft, output):
    from .segmentation import validate_ranges

    for field in ('fruit_hsv', 'orange_hsv', 'abnormal_hsv'):
        if draft.get(field):
            validate_ranges(draft[field])
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    target = output / ('calibracao-' + uuid4().hex + '.json')
    with target.open('x', encoding='utf-8') as stream:
        json.dump(
            {**draft, 'validated': False, 'version': 'rascunho-' + uuid4().hex[:12]},
            stream,
            ensure_ascii=False,
            indent=2,
        )
    return target


def select_rectangle(frame, title):
    import cv2

    scale = min(1, 960 / frame.shape[1], 600 / frame.shape[0])
    selection = cv2.resize(
        frame, (max(1, round(frame.shape[1] * scale)), max(1, round(frame.shape[0] * scale)))
    )
    try:
        rectangle = cv2.selectROI(title, selection, showCrosshair=True)
    finally:
        cv2.destroyWindow(title)
    return source_rectangle(rectangle, frame.shape, selection.shape)


def main():
    parser = argparse.ArgumentParser(
        description='Bancada OrangeVision: webcam ou fotos, sem envio à API.'
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--camera', type=int, help='Índice da webcam USB: 0, 1, ...')
    source.add_argument('--images', help='Uma foto ou pasta de fotos (inclusive subpastas).')
    calibration_source = parser.add_mutually_exclusive_group()
    calibration_source.add_argument(
        '--calibration', help='Calibração validada para análise experimental local.'
    )
    calibration_source.add_argument(
        '--draft', help='Retomar faixas de um rascunho sem habilitar classificação.'
    )
    parser.add_argument(
        '--minimum-area',
        type=float,
        help='Área mínima em pixels originais para a prévia, medida na bancada.',
    )
    parser.add_argument(
        '--output', default='calibracao-local', help='Pasta para novas capturas e rascunhos.'
    )
    args = parser.parse_args()

    import cv2
    import numpy as np

    from .lab_preview import preview_frame
    from .segmentation import segment_guided, validate_frame, validate_ranges
    from .vision import CalibratedVision, VisionFailure

    camera = None
    try:
        if 'GUI:                           NONE' in cv2.getBuildInformation() or not any(
            line.strip().startswith('GUI:') and 'NONE' not in line
            for line in cv2.getBuildInformation().splitlines()
        ):
            raise ValueError(
                'OpenCV sem suporte a janelas. Instale requirements-lab.txt no ambiente da bancada.'
            )
        vision = CalibratedVision.load(Path(args.calibration)) if args.calibration else None
        draft = (
            deepcopy(vision.calibration)
            if vision
            else json.loads(
                Path(__file__).with_name('calibration.example.json').read_text(encoding='utf-8')
            )
        )
        if args.draft:
            loaded = json.loads(Path(args.draft).read_text(encoding='utf-8'))
            if not isinstance(loaded, dict):
                raise ValueError('O rascunho precisa ser um objeto JSON.')
            draft.update(loaded)
        if not vision:
            edited(draft)
        for field in ('fruit_hsv', 'orange_hsv', 'abnormal_hsv'):
            if not isinstance(draft.get(field), list):
                raise ValueError('Faixas de cor do rascunho devem ser listas.')
            if draft[field]:
                validate_ranges(draft[field])
        if args.minimum_area is not None:
            import math

            if not math.isfinite(args.minimum_area) or args.minimum_area < 0:
                raise ValueError('Informe uma área mínima finita e não negativa.')
            draft['minimum_fruit_area_pixels'] = args.minimum_area
            edited(draft)
        output = Path(args.output)
        paths = image_paths(args.images) if args.images else []
        index = 0
        loaded_index = None
        frame = None
        dirty = True
        frozen = False
        guided_segment = None
        notice = None
        if args.camera is not None:
            camera = cv2.VideoCapture(args.camera)
            if not camera.isOpened():
                raise ValueError(
                    'Webcam indisponível. Feche outros aplicativos ou teste outro índice.'
                )
        print('Q: sair | S: salvar imagem | N/P: próxima/anterior foto | A: analisar')
        print(
            'Espaço: congelar/voltar ao vivo | B: selecionar a fruta inteira na imagem congelada.'
        )
        print(
            'F: amostra da fruta | O: cor laranja saudável | D: região anormal | G: salvar rascunho'
        )
        print('R: limpar amostras | Barras HSV: ajustar a última amostra F, com prévia imediata.')
        print('Selecione somente a região desejada e pressione Enter; Esc cancela.')
        print('Amostras geram um rascunho NÃO VALIDADO; não definem qualidade automaticamente.')
        cv2.namedWindow(MAIN_WINDOW, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(MAIN_WINDOW, 1080, 480)
        hsv_open = False
        if draft['fruit_hsv']:
            open_hsv_controls()
            hsv_open = True
            set_sliders(draft['fruit_hsv'][-1])
        while True:
            if camera is not None and (frame is None or not frozen):
                ok, frame = camera.read()
                if not ok:
                    raise ValueError('A webcam não forneceu uma imagem.')
                dirty = True
            elif camera is None and loaded_index != index:
                frame = cv2.imdecode(
                    np.fromfile(str(paths[index]), dtype=np.uint8), cv2.IMREAD_COLOR
                )
                if frame is None:
                    raise ValueError('Imagem ilegível: ' + str(paths[index]))
                loaded_index = index
                dirty = True
                print('Foto:', paths[index])
            validate_frame(frame)
            if hsv_open and cv2.getWindowProperty(HSV_WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                hsv_open = False
            if hsv_open and draft['fruit_hsv']:
                limits = [[0, 0, 0], [0, 0, 0]]
                for name, side, channel, _ in SLIDERS:
                    limits[side][channel] = cv2.getTrackbarPos(name, HSV_WINDOW)
                if limits != draft['fruit_hsv'][-1]:
                    draft['fruit_hsv'][-1] = limits
                    edited(draft)
                    guided_segment = None
                    notice = None
                    dirty = True
            if dirty:
                panel, snapshot = preview_frame(
                    frame,
                    draft,
                    vision if draft.get('validated') is True else None,
                    guided_segment=guided_segment,
                    frozen=frozen or camera is None,
                    notice=notice,
                )
                dirty = False
            cv2.imshow(MAIN_WINDOW, panel)
            key = cv2.waitKey(30) & 0xFF
            if ord('A') <= key <= ord('Z'):
                key += ord('a') - ord('A')
            if key == ord('q') or cv2.getWindowProperty(MAIN_WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
            if key == ord(' ') and camera is not None:
                frozen = not frozen
                guided_segment = None
                notice = None
                dirty = True
                print(
                    'Imagem congelada: pode baixar a mão. Pressione B para selecionar a fruta.'
                    if frozen
                    else 'Câmera ao vivo. Seleção anterior descartada.'
                )
            elif key == ord('b'):
                if camera is not None:
                    frozen = True
                rectangle = select_rectangle(frame, 'Fruta inteira - inclua margem de fundo')
                try:
                    print('Separando a região selecionada…')
                    guided_segment = segment_guided(
                        frame, rectangle, draft.get('minimum_fruit_area_pixels') or 0
                    )
                    notice = None
                    print(
                        'Confira o contorno e se a mão ficou de fora. S salva a foto original congelada.'
                    )
                except VisionFailure as exc:
                    guided_segment = None
                    notice = str(exc)
                    print(notice)
                dirty = True
            elif key in (ord('n'), ord('p')) and paths:
                index = (index + (1 if key == ord('n') else -1)) % len(paths)
                guided_segment = None
                notice = None
                dirty = True
                print('Foto:', paths[index])
            elif key == ord('s'):
                output.mkdir(parents=True, exist_ok=True)
                target = output / ('captura-' + uuid4().hex + '.png')
                ok, encoded = cv2.imencode('.png', frame)
                if not ok:
                    raise ValueError('Não foi possível codificar a captura.')
                with target.open('xb') as stream:
                    stream.write(encoded.tobytes())
                print('Imagem salva:', target, '| resolução:', frame.shape[1], 'x', frame.shape[0])
            elif key in (ord('f'), ord('o'), ord('d')):
                field = {ord('f'): 'fruit_hsv', ord('o'): 'orange_hsv', ord('d'): 'abnormal_hsv'}[
                    key
                ]
                if camera is not None:
                    frozen = True
                    dirty = True
                rectangle = select_rectangle(frame, 'Amostra')
                try:
                    draft[field].append(sample_range(frame, rectangle))
                    edited(draft)
                    if field == 'fruit_hsv':
                        guided_segment = None
                        if not hsv_open:
                            open_hsv_controls()
                            hsv_open = True
                        set_sliders(draft[field][-1])
                    notice = None
                    dirty = True
                    print('Amostras', field, ':', len(draft[field]))
                except ValueError as exc:
                    print(str(exc))
            elif key == ord('r'):
                for field in ('fruit_hsv', 'orange_hsv', 'abnormal_hsv'):
                    draft[field] = []
                edited(draft)
                guided_segment = None
                notice = None
                dirty = True
                print('Amostras limpas somente em memória. Pressione F para recomeçar.')
            elif key == ord('g'):
                try:
                    target = save_draft(draft, output)
                    print(
                        'Rascunho salvo:',
                        target,
                        '| faltam critérios e validação com imagens separadas.',
                    )
                    if guided_segment is not None:
                        print(
                            'G grava as faixas de cor; a seleção assistida desta foto não vira calibração automática.'
                        )
                except VisionFailure as exc:
                    print('Rascunho não salvo:', str(exc))
            elif key == ord('a'):
                print(json.dumps(snapshot, ensure_ascii=False))
    except (ValueError, OSError, VisionFailure, cv2.error) as exc:
        parser.exit(1, str(exc) + '\n')
    finally:
        if camera is not None:
            camera.release()
        try:
            cv2.destroyAllWindows()
        except cv2.error:
            pass  # Builds headless não implementam nem a limpeza de janelas.


if __name__ == '__main__':
    main()
