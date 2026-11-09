"""Fila de amostras: processamento local de arquivos, sem atuação física."""

import base64
import json
import secrets
import time
from pathlib import Path
from uuid import UUID, uuid4

from .api import ApiFailure, Offline
from .locking import device_lock
from .sample_status import analysis_identity, public_result


def sample_result(content, calibration=None, *, validated=False, detector=None):
    import cv2
    import numpy as np

    from .segmentation import (
        VisionFailure,
        measure_metrics,
        segment_detected,
        segment_fruit,
        segment_single_by_color,
        validate_frame,
    )
    from .vision import CalibratedVision

    result = {
        'state': 'awaiting_review',
        'reason': 'Sem classificação: calibração ausente ou não validada. Configure e confira a segmentação local.',
        'metrics': None,
        'classification': None,
        'calibration_version': None,
        'algorithm_version': 'image-acquisition-v1',
        'calibration_validated': False,
        'mask_base64': None,
    }
    try:
        frame = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
        validate_frame(frame)
        if detector is not None:
            result['detection'] = detector.detect(frame)
            result['algorithm_version'] = 'yolox-s-grabcut-v1'
            minimum_area = (calibration or {}).get('minimum_fruit_area_pixels') or 0
            # Localização por cor só com calibração validada que a habilite.
            color_fallback = bool(
                validated
                and calibration
                and calibration.get('color_fallback') is True
                and calibration.get('segmentation_method') == 'yolox-s-grabcut-v1'
            )
            segment = None
            if result['detection']['status'] != 'detected':
                if not color_fallback:
                    result.update(
                        state='not_evaluable',
                        reason='Nenhuma laranja detectada com score suficiente.'
                        if result['detection']['count'] == 0
                        else 'Mais de uma laranja detectada. Use uma fruta por captura.',
                    )
                    return result
            else:
                try:
                    segment = segment_detected(frame, result['detection']['box'], minimum_area)
                except VisionFailure:
                    # GrabCut pode recortar só um pedaço (área insuficiente) ou o
                    # contorno pode passar do recorte: com a calibração permitindo,
                    # tenta a localização por cor, que tem suas próprias recusas.
                    if not color_fallback:
                        raise
            if segment is None:
                # O detector COCO não confirmou: a fruta é localizada pela cor sobre
                # fundo neutro. O resultado não alega detecção de laranja pela IA.
                segment = segment_single_by_color(frame, calibration['fruit_hsv'], minimum_area)
                result['detection'] = None
                result['algorithm_version'] = 'opencv-hsv-fallback-v1'
            metrics = measure_metrics(
                segment,
                (calibration or {}).get('orange_hsv'),
                (calibration or {}).get('abnormal_hsv'),
                (calibration or {}).get('abnormal_detection'),
            )
            result.update(
                metrics={**metrics, 'visual_score': None},
                calibration_version=str(calibration.get('version') or 'rascunho')[:100]
                if calibration
                else None,
                reason='Sem classificação: calibração ausente ou não validada. '
                'Modelo sugere laranja; métricas de segmentação são experimentais.',
                mask_base64=base64.b64encode(
                    cv2.imencode('.png', segment.mask)[1].tobytes()
                ).decode('ascii'),
            )
            if validated and (calibration or {}).get('segmentation_method') == 'yolox-s-grabcut-v1':
                classified = CalibratedVision(calibration).classify_segment(segment)
                result.update(
                    state='completed',
                    metrics=classified['metrics'],
                    classification=classified['classification'],
                    reason=classified['reason']
                    if result['detection'] is not None
                    else 'Fruta localizada pela cor (detector não confirmou). ' + classified['reason'],
                    calibration_version=calibration['version'],
                    calibration_validated=True,
                )
            elif validated:
                result['reason'] = (
                    'Detecção e métricas disponíveis; a calibração carregada não foi validada para o método yolox-s-grabcut-v1.'
                )
            return result
        if not calibration or not calibration.get('fruit_hsv'):
            return result
        result['algorithm_version'] = 'opencv-hsv-contour-v2'
        segment = segment_fruit(
            frame, calibration['fruit_hsv'], calibration.get('minimum_fruit_area_pixels') or 0
        )
        if segment.touches_border:
            raise VisionFailure('Contorno toca a borda. Confira enquadramento e faixas de cor.')
        metrics = measure_metrics(
            segment,
            calibration.get('orange_hsv'),
            calibration.get('abnormal_hsv'),
            calibration.get('abnormal_detection'),
        )
        ok, mask = cv2.imencode('.png', segment.mask)
        if not ok:
            raise VisionFailure('Não foi possível gerar a máscara.')
        result.update(
            metrics={**metrics, 'visual_score': None},
            reason='Métricas experimentais de segmentação. Categoria aguarda calibração e avaliação.',
            mask_base64=base64.b64encode(mask.tobytes()).decode('ascii'),
            calibration_version=str(calibration.get('version', 'rascunho'))[:100],
        )
        if validated:
            classified = CalibratedVision(calibration).analyze(frame)
            result.update(
                state='completed',
                reason=classified['reason'],
                metrics=classified['metrics'],
                classification=classified['classification'],
                calibration_validated=True,
            )
        return result
    except VisionFailure as exc:
        return {
            **result,
            'state': 'not_evaluable',
            'reason': str(exc),
            'metrics': None,
            'mask_base64': None,
            'classification': None,
            'calibration_validated': False,
        }


def retry(operation):
    for attempt in range(3):
        try:
            return operation()
        except (Offline, ApiFailure) as exc:
            if isinstance(exc, ApiFailure) and exc.status < 500 and exc.status != 429:
                raise
            if attempt == 2:
                raise
            time.sleep(min(300, max(2**attempt, getattr(exc, 'retry_after', None) or 0)))


def flush_camera_samples(store, api, *, on_event=None):
    events = []
    for row in store.pending_camera_samples():
        grant = store.grant(row['session_id'])
        original = grant if row.get('original_source_known', 1) else None
        if on_event:
            on_event({'kind': 'uploading', 'photo_id': row['id']})
        try:
            if row.get('review_grant_id'):
                review = store.grant(row['review_grant_id'])
                response = retry(
                    lambda original=original, review=review, row=row: api.upload_camera_review(
                        original, review, row['id'], row['captured_at'], row['image']
                    )
                )
            else:
                response = retry(
                    lambda grant=grant, row=row: api.upload_camera_sample(
                        grant, row['id'], row['captured_at'], row['image']
                    )
                )
            sample_id = str(UUID(response['id']))
            analysis_id = analysis_identity(response.get('analysis_id'))
            if response.get('source_inspection_id') != (original['id'] if original else None):
                raise RuntimeError('Resposta de envio incompatível com a sessão original.')
            store.record_sample_receipt(row['id'], sample_id, analysis_id)
            events.append('synced')
            if on_event:
                on_event({
                    'kind': 'synced', 'photo_id': row['id'], 'sample_id': sample_id,
                    'analysis_id': analysis_id,
                })
            print('Foto confirmada no site:', row['id'])
        except ApiFailure as exc:
            if exc.status in (400, 403, 404, 409, 413, 422):
                store.camera_sample_state(row['id'], 'quarantined', f'HTTP{exc.status}')
                events.append('quarantined')
                if on_event:
                    on_event({'kind': 'quarantined', 'photo_id': row['id'], 'status': exc.status})
                print('Envio de foto exige revisão local:', row['id'], f'HTTP {exc.status}')
            else:
                raise
    return events


def process_one(api, calibration=None, *, validated=False, detector=None, on_event=None, store=None):
    if store is not None:
        # Janela e CLI compartilham a mesma reserva, não criam envios paralelos.
        with device_lock(store.path.with_suffix('.samples.lock')):
            return _process_one(api, calibration, validated, detector, on_event, store)
    return _process_one(api, calibration, validated, detector, on_event, None)


def _process_one(api, calibration, validated, detector, on_event, store):
    work = store.pending_sample_work() if store is not None else None
    if work:
        identity = work['sample_id']
        attempt = {'claim_id': work['claim_id'], 'lease_token': work['lease_token']}
    else:
        attempt = store.sample_claim() if store is not None else None
        if attempt is None:
            attempt = {'claim_id': str(uuid4()), 'lease_token': secrets.token_urlsafe(32)}
            if store is not None:
                store.sample_claim(attempt)
        job = retry(lambda: api.claim_sample(attempt))
        if job is None:
            if store is not None:
                store.clear_sample_claim()
            return None
        identity = str(UUID(job['id']))
        if store is not None:
            store.start_sample_work(identity, attempt)
            work = store.pending_sample_work()
    if on_event:
        on_event({'kind': 'processing', 'sample_id': identity})
    if work and work['payload'] is not None:
        payload = work['payload']
    else:
        content = retry(lambda: api.sample_image(identity, attempt['lease_token']))
        try:
            result = sample_result(content, calibration, validated=validated, detector=detector)
        except Exception:
            # Não envia stack trace, segredos ou mensagens de driver ao servidor.
            result = {'state': 'failed', 'reason': 'Falha técnica no processamento local da amostra.'}
        payload = {**result, 'claim_id': attempt['claim_id']}
        if store is not None:
            store.save_sample_result(identity, payload, public_result(payload))
    if on_event:
        on_event({
            'kind': 'result_pending', 'sample_id': identity, 'result': public_result(payload),
            'analysis_id': work.get('analysis_id') if work else None,
        })
    response = retry(lambda: api.finish_sample(identity, attempt['lease_token'], payload))
    summary = public_result(payload, response)
    analysis_id = analysis_identity(response.get('analysis_id'))
    if store is not None:
        store.confirm_sample_result(identity, summary, analysis_id)
        analysis_id = analysis_id or (work.get('analysis_id') if work else None)
    if on_event:
        on_event({
            'kind': 'result', 'sample_id': identity,
            'result': summary, 'analysis_id': analysis_id,
        })
    return {'id': identity, 'state': summary['state'], 'analysis_id': analysis_id}


def run_samples(api, draft=None, calibration=None, loop=False, ai=False, camera_store=None):
    from .detector import MODEL_NAME, OrangeDetector
    from .vision import CalibratedVision

    api.heartbeat_samples('starting', MODEL_NAME if ai else None, 'Iniciando executor de amostras.')
    try:
        detector = OrangeDetector() if ai else None
    except Exception:
        api.heartbeat_samples(
            'error', MODEL_NAME, 'Detector não disponível. Instale/verifique o modelo local.'
        )
        raise

    settings = CalibratedVision.load(Path(calibration)).calibration if calibration else None
    if draft:
        settings = json.loads(Path(draft).read_text(encoding='utf-8'))
        if not isinstance(settings, dict):
            raise RuntimeError('Rascunho de amostras inválido.')
        settings['validated'] = False
    while True:
        try:
            api.heartbeat_samples(
                'ready',
                MODEL_NAME if ai else None,
                'Executor consultando fila com IA.' if ai else 'Executor consultando fila sem IA.',
            )
            if camera_store is not None:
                flush_camera_samples(camera_store, api)
            result = process_one(
                api, settings, validated=bool(calibration), detector=detector, store=camera_store
            )
            print(
                json.dumps(result, ensure_ascii=False)
                if result
                else 'Nenhuma amostra aguardando este equipamento.'
            )
        except (Offline, ApiFailure) as exc:
            transient = isinstance(exc, Offline) or exc.status >= 500 or exc.status in (409, 429)
            if not loop or not transient:
                raise
            print(
                'Sem confirmação do processamento. A amostra permanece no servidor; nova tentativa após reconexão ou vencimento da reserva.'
            )
        if not loop:
            return
        time.sleep(5)
