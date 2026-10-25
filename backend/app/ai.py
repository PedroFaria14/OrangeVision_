"""Camada opcional de interpretação. Não altera a classificação OpenCV."""
import os
from .logging_config import log

def interpret_analysis(analysis: dict) -> dict:
    enabled = os.getenv("AI_ENABLED", "false").lower() in ("true", "1", "yes")
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not enabled:
        log.info("IA desativada; análise segue sem IA")
        return {"status": "disabled", "interpretacao": None}
    if not key:
        log.warning("IA habilitada sem GEMINI_API_KEY; ignorando interpretação")
        return {"status": "unavailable", "interpretacao": None}
    try:
        from google import genai
    except ImportError:
        log.warning("Pacote google-genai ausente; IA ignorada")
        return {"status": "unavailable", "interpretacao": None}
    try:
        client = genai.Client(api_key=key)
        model = os.getenv("AI_MODEL", "gemini-2.5-flash")
        prompt = (
            "Descreva brevemente em português as métricas desta triagem visual "
            "de laranja, sem diagnosticar doenças ou alterar a classificação. "
            "Seja claro que são métricas experimentais e dependem de calibração. "
            f"Dados: {analysis}"
        )
        response = client.models.generate_content(model=model, contents=prompt)
        result = getattr(response, "text", None)
        if not result:
            log.warning("IA respondeu sem texto; continuando sem interpretação")
            return {"status": "unavailable", "interpretacao": None}
        log.info("Interpretação complementar de IA gerada")
        return {"status": "ok", "interpretacao": result}
    except Exception as exc:
        log.warning("IA indisponível (%s); fluxo principal preservado", type(exc).__name__)
        return {"status": "unavailable", "interpretacao": None}
