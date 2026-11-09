"""Dados públicos de uma avaliação; nunca incluem lease, claim ou imagem."""

from uuid import UUID

RESULT_STATES = {'completed', 'awaiting_review', 'not_evaluable', 'failed'}
PUBLIC_FIELDS = (
    'state', 'classification', 'reason', 'calibration_validated',
    'calibration_version', 'algorithm_version',
)


def analysis_identity(value):
    if value is None or value == '':
        return None
    try:
        identity = UUID(value)
        if identity.int == 0:
            raise ValueError
        return str(identity)
    except (ValueError, TypeError, AttributeError):
        raise RuntimeError('API retornou analysis_id inválido; registro não confirmado.') from None


def public_result(payload, response=None):
    result = {key: payload.get(key) for key in PUBLIC_FIELDS}
    if response is not None:
        if not isinstance(response, dict) or response.get('state') not in RESULT_STATES:
            raise RuntimeError('Resposta de avaliação incompatível; confirmação pendente.')
        for key in PUBLIC_FIELDS:
            if key in response:
                result[key] = response[key]
    if result.get('state') not in RESULT_STATES:
        raise RuntimeError('Estado de avaliação incompatível.')
    if result.get('classification') not in (None, 'APROVADA', 'ATENCAO', 'REVISAR'):
        raise RuntimeError('Categoria de avaliação incompatível; confirmação pendente.')
    if result.get('reason') is not None and not isinstance(result['reason'], str):
        raise RuntimeError('Motivo de avaliação incompatível; confirmação pendente.')
    if result.get('calibration_validated') is not None and type(result['calibration_validated']) is not bool:
        raise RuntimeError('Validação de calibração incompatível; confirmação pendente.')
    return result
