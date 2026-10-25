import json
import math
from pathlib import Path

from .segmentation import VisionFailure, measure_metrics, segment_fruit, validate_ranges

METRICS = ('orange_color_ratio', 'abnormal_region_ratio', 'circularity', 'asymmetry')


class CalibratedVision:
    def __init__(self, calibration):
        self.calibration = calibration
        self.segmentation_method = calibration.get('segmentation_method', 'hsv')
        if self.segmentation_method not in ('hsv', 'yolox-s-grabcut-v1'):
            raise VisionFailure('Método de segmentação da calibração não suportado.')
        if (
            calibration.get('validated') is not True
            or not isinstance(calibration.get('version'), str)
            or not 1 <= len(calibration['version']) <= 100
        ):
            raise VisionFailure('É necessária calibração identificada e validada com fotos reais.')
        for key in (('fruit_hsv',) if self.segmentation_method == 'hsv' else ()) + (
            'orange_hsv',
            'abnormal_hsv',
        ):
            validate_ranges(calibration.get(key))
        area = calibration.get('minimum_fruit_area_pixels')
        if type(area) not in (int, float) or not math.isfinite(area) or area <= 0:
            raise VisionFailure('Área mínima exige medição de bancada.')
        rules = calibration.get('score_rules', {})
        if not isinstance(rules, dict) or set(rules) != set(METRICS):
            raise VisionFailure('Configure exatamente as quatro regras de métricas documentadas.')
        for key in METRICS:
            rule = rules.get(key, {})
            if rule.get('direction') not in ('higher', 'lower'):
                raise VisionFailure('Regra de score não configurada.')
            for field in ('low', 'high', 'weight'):
                if type(rule.get(field)) not in (int, float) or not math.isfinite(rule[field]):
                    raise VisionFailure('Parâmetros numéricos do score são obrigatórios.')
            if (
                rule['high'] <= rule['low']
                or not math.isfinite(rule['high'] - rule['low'])
                or rule['weight'] <= 0
            ):
                raise VisionFailure('Intervalo e peso do score inválidos.')
        if not math.isfinite(sum(rule['weight'] for rule in rules.values())):
            raise VisionFailure('Soma de pesos do score inválida.')
        attention, approved = (
            calibration.get('attention_min_score'),
            calibration.get('approval_min_score'),
        )
        if (
            type(attention) not in (int, float)
            or type(approved) not in (int, float)
            or not 0 <= attention < approved <= 100
        ):
            raise VisionFailure('Limiares experimentais precisam ser fornecidos e validados.')

    @classmethod
    def load(cls, path):
        if not path:
            raise VisionFailure(
                'Configure CALIBRATION_PATH; não existe classificação padrão fictícia.'
            )
        return cls(json.loads(Path(path).read_text(encoding='utf-8')))

    def analyze(self, frame):
        if self.segmentation_method != 'hsv':
            raise VisionFailure(
                'Esta calibração exige detector IA e máscara automática compatível.'
            )
        segment = segment_fruit(
            frame, self.calibration['fruit_hsv'], self.calibration['minimum_fruit_area_pixels']
        )
        if segment.touches_border:
            raise VisionFailure(
                'Contorno toca a borda: enquadre a fruta inteira antes de classificar.'
            )
        return self.classify_segment(segment)

    def classify_segment(self, segment):
        if segment.touches_border:
            raise VisionFailure(
                'Contorno toca a borda: enquadre a fruta inteira antes de classificar.'
            )
        metrics = measure_metrics(
            segment, self.calibration['orange_hsv'], self.calibration['abnormal_hsv']
        )
        score, weights = 0.0, 0.0
        for key, value in metrics.items():
            if not math.isfinite(value) or value < 0:
                raise VisionFailure('Métrica não calculável.')
            rule = self.calibration['score_rules'][key]
            normalized = max(0.0, min(1.0, (value - rule['low']) / (rule['high'] - rule['low'])))
            score += (normalized if rule['direction'] == 'higher' else 1 - normalized) * rule[
                'weight'
            ]
            weights += rule['weight']
        metrics['visual_score'] = score / weights * 100
        if not math.isfinite(metrics['visual_score']):
            raise VisionFailure('Score não calculável; nenhuma classe foi produzida.')
        classification = (
            'APROVADA'
            if metrics['visual_score'] >= self.calibration['approval_min_score']
            else 'ATENCAO'
            if metrics['visual_score'] >= self.calibration['attention_min_score']
            else 'REVISAR'
        )
        return {
            'classification': classification,
            'metrics': metrics,
            'calibration_version': self.calibration['version'],
            'algorithm_version': 'opencv-hsv-contour-v2',
            'reason': f'Classificação experimental pelo score visual e calibração {self.calibration["version"]}; não é diagnóstico de doença ou qualidade interna.',
        }
