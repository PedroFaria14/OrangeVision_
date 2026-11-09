import json
import math
from pathlib import Path

from .segmentation import (
    VisionFailure,
    measure_metrics,
    segment_fruit,
    validate_ranges,
    validate_stain_rule,
)

METRICS = ('orange_color_ratio', 'abnormal_region_ratio', 'circularity', 'asymmetry')
RULES_METHOD = 'ripeness-rules-v1'
RULE_LIMITS = (
    'verde_min_green_ratio',
    'passou_min_abnormal_ratio',
    'boa_max_abnormal_ratio',
    'boa_max_green_ratio',
    'boa_min_orange_ratio',
)


def ripeness_category(rules, orange, green, abnormal):
    """Categoria por regras explícitas: verde e passou são eixos diferentes do score."""
    if green >= rules['verde_min_green_ratio']:
        return 'ATENCAO', 'Verde'
    if abnormal >= rules['passou_min_abnormal_ratio']:
        return 'REVISAR', 'Passou / manchas'
    if (
        abnormal <= rules['boa_max_abnormal_ratio']
        and green <= rules['boa_max_green_ratio']
        and orange >= rules['boa_min_orange_ratio']
    ):
        return 'APROVADA', 'Boa'
    return 'ATENCAO', 'Intermediária'


class CalibratedVision:
    def __init__(self, calibration):
        if not isinstance(calibration, dict):
            raise VisionFailure('A calibração deve ser um objeto JSON identificado e validado.')
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
        # Manchas por contraste local (sombra não conta); sem a chave, faixas abnormal_hsv.
        self.stain_rule = validate_stain_rule(calibration.get('abnormal_detection'))
        fallback = calibration.get('color_fallback', False)
        if type(fallback) is not bool:
            raise VisionFailure('color_fallback deve ser true ou false.')
        if fallback:
            validate_ranges(calibration.get('fruit_hsv'))
        self.rules = calibration.get('classification_rules')
        if self.rules is not None:
            if not isinstance(self.rules, dict) or self.rules.get('method') != RULES_METHOD:
                raise VisionFailure(f'classification_rules exige method={RULES_METHOD}.')
            validate_ranges(self.rules.get('green_hsv'))
            for key in RULE_LIMITS:
                value = self.rules.get(key)
                if type(value) not in (int, float) or not 0 < value < 1:
                    raise VisionFailure(f'Regra de categoria {key} precisa estar entre 0 e 1.')
            if self.rules['boa_max_abnormal_ratio'] >= self.rules['passou_min_abnormal_ratio']:
                raise VisionFailure('Manchas aceitas como boa precisam ser menores que o limite de passou.')
            if self.rules['boa_max_green_ratio'] >= self.rules['verde_min_green_ratio']:
                raise VisionFailure('Verde aceito como boa precisa ser menor que o limite de verde.')

    @classmethod
    def load(cls, path):
        if not path:
            raise VisionFailure(
                'Configure CALIBRATION_PATH; não existe classificação padrão fictícia.'
            )
        file = Path(path)
        if file.is_dir():
            raise VisionFailure(
                'CALIBRATION_PATH aponta para uma pasta. Informe um arquivo JSON de calibração validada, não a pasta de fotos.'
            )
        try:
            calibration = json.loads(file.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise VisionFailure(
                'Não foi possível ler a calibração. Confira o caminho, acesso e formato JSON do arquivo validado.'
            ) from None
        return cls(calibration)

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
            segment,
            self.calibration['orange_hsv'],
            self.calibration['abnormal_hsv'],
            self.stain_rule,
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
        reason = f'Classificação experimental pelo score visual e calibração {self.calibration["version"]}; não é diagnóstico de doença ou qualidade interna.'
        if self.rules is not None:
            green = measure_metrics(segment, self.rules['green_hsv'])['orange_color_ratio']
            classification, label = ripeness_category(
                self.rules, metrics['orange_color_ratio'], green, metrics['abnormal_region_ratio']
            )
            reason = (
                f'{label}: casca {metrics["orange_color_ratio"]:.0%} laranja, {green:.0%} verde, '
                f'{metrics["abnormal_region_ratio"]:.0%} manchas escuras. '
                f'Regras {RULES_METHOD}, calibração {self.calibration["version"]}. '
                'Avalia só a superfície visível; não é diagnóstico interno.'
            )
        return {
            'classification': classification,
            'metrics': metrics,
            'calibration_version': self.calibration['version'],
            'algorithm_version': 'opencv-hsv-contour-v2',
            'reason': reason,
        }
