"""Detecção local COCO/orange usando o ONNX oficial do OpenCV Zoo (YOLOX-S).

Preprocessamento/decodificação seguem o exemplo Apache-2.0 do OpenCV Zoo.
Score de detecção não é acurácia nem avaliação da qualidade da fruta.
"""

import hashlib
import time
from pathlib import Path
from threading import Lock

MODEL_NAME = 'opencv-zoo-yolox-s-2022nov'
MODEL_SHA256 = 'c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063'
MODEL_SIZE = 35858002
MODEL_URL = 'https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/object_detection_yolox/object_detection_yolox_2022nov.onnx'
MODEL_PATH = Path(__file__).parent / 'models' / 'yolox-s-2022nov.onnx'


def preprocess(frame):
    import cv2
    import numpy as np

    # YOLOX ValTransform(legacy=False): BGR 0..255, não RGB/normalização ImageNet.
    ratio = min(640 / frame.shape[0], 640 / frame.shape[1])
    work = cv2.resize(
        frame, (max(1, int(frame.shape[1] * ratio)), max(1, int(frame.shape[0] * ratio)))
    )
    padded = np.full((640, 640, 3), 114, dtype=np.float32)
    padded[: work.shape[0], : work.shape[1]] = work
    return np.ascontiguousarray(np.transpose(padded, (2, 0, 1))[None]), ratio


class ModelFailure(RuntimeError):
    pass


def verify_model(path):
    path = Path(path)
    if not path.is_file():
        raise ModelFailure('Modelo não instalado. Execute python -m backend.device.model_setup.')
    if (
        path.stat().st_size != MODEL_SIZE
        or hashlib.sha256(path.read_bytes()).hexdigest() != MODEL_SHA256
    ):
        raise ModelFailure(
            'Modelo incompatível ou corrompido. Confira o artefato oficial e seu SHA-256.'
        )


def decode_oranges(output, shape, ratio, threshold=0.35):
    import cv2
    import numpy as np

    output = np.asarray(output)
    if output.shape != (1, 8400, 85) or not np.isfinite(output).all():
        raise ModelFailure('Saída do modelo incompatível com o detector instalado.')
    grids, strides = [], []
    for stride in (8, 16, 32):
        x, y = np.meshgrid(np.arange(640 // stride), np.arange(640 // stride))
        grids.append(np.stack((x, y), axis=2).reshape(-1, 2))
        strides.append(np.full((x.size, 1), stride))
    grid, stride = np.concatenate(grids), np.concatenate(strides)
    predictions = output[0]
    classes = np.argmax(predictions[:, 5:], axis=1)
    scores = predictions[:, 4] * predictions[:, 54]  # COCO: orange é classe 49.
    indexes = np.flatnonzero((classes == 49) & (scores >= threshold) & (scores <= 1))
    boxes, confidences = [], []
    for index in indexes:
        center = (predictions[index, :2] + grid[index]) * stride[index] / ratio
        size = np.exp(np.clip(predictions[index, 2:4], -20, 20)) * stride[index] / ratio
        left = max(0, int(center[0] - size[0] / 2))
        top = max(0, int(center[1] - size[1] / 2))
        right = min(shape[1], int(center[0] + size[0] / 2))
        bottom = min(shape[0], int(center[1] + size[1] / 2))
        if right > left and bottom > top:
            boxes.append([left, top, right - left, bottom - top])
            confidences.append(float(scores[index]))
    if not boxes:
        return []
    keep = np.asarray(cv2.dnn.NMSBoxes(boxes, confidences, threshold, 0.5)).reshape(-1)
    return [{'box': boxes[index], 'score': confidences[index]} for index in keep[:100]]


class OrangeDetector:
    def __init__(self, path=MODEL_PATH, threshold=0.35):
        import cv2

        verify_model(path)
        if not 0 < threshold < 1:
            raise ModelFailure('O limiar do detector deve estar entre zero e um.')
        self.threshold = threshold
        self.lock = Lock()
        try:
            self.net = cv2.dnn.readNetFromONNX(str(path))
        except cv2.error as exc:
            raise ModelFailure(
                'OpenCV não conseguiu carregar o ONNX. Confira a versão e as dependências de visão.'
            ) from exc
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

    def detect(self, frame):
        from .segmentation import validate_frame

        validate_frame(frame)
        started = time.perf_counter()
        blob, ratio = preprocess(frame)
        with self.lock:
            self.net.setInput(blob)
            try:
                output = self.net.forward()
            except Exception as exc:
                raise ModelFailure(
                    'Falha na execução do detector local. Confira OpenCV e o modelo instalado.'
                ) from exc
        candidates = decode_oranges(output, frame.shape, ratio, self.threshold)
        count = len(candidates)
        single = candidates[0] if count == 1 else None
        return {
            'status': 'detected' if single else 'ambiguous' if count > 1 else 'not_detected',
            'label': 'orange' if single else None,
            'score': single['score'] if single else None,
            'box': single['box'] if single else None,
            'count': count,
            'model': MODEL_NAME,
            'inference_ms': round((time.perf_counter() - started) * 1000, 2),
        }
