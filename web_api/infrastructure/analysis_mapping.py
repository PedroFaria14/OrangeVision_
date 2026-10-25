def adapt(row):
    """Mapeia percentuais legados para razões sem inventar métricas ou imagens."""

    def ratio(key):
        return float(row[key]) / 100 if row[key] is not None else None

    return {
        'id': row['id'],
        'device_id': row['dispositivo_id'],
        'timestamp': row['data_hora'],
        'classification': row['classificacao'],
        'calibration_version': row.get('calibration_version') or row['versao_algoritmo'],
        'inspection_session_id': row.get('inspection_session_id'),
        'classification_reason': row.get('classification_reason'),
        'metrics': {
            'orange_color_ratio': ratio('cor_media'),
            'abnormal_region_ratio': ratio('regioes_anormais'),
            'asymmetry': ratio('assimetria'),
            'circularity': row['circularidade'],
            'visual_score': row['score_visual'],
        },
    }
