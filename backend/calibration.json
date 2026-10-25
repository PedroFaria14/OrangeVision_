"""Leitura e validação básica de parâmetros experimentais do OrangeVision."""
import json
import os
from pathlib import Path


def load_calibration(path: str | None = None) -> dict:
    path = path or os.getenv("CALIBRATION_PATH", "./config/calibration.json")
    file = Path(path)
    if not file.is_file():
        raise FileNotFoundError(f"Calibração não encontrada: {file.resolve()}")
    data = json.loads(file.read_text(encoding="utf-8"))
    for key in ("fruit_hsv_ranges", "abnormal_hsv_ranges", "min_fruit_area_px", "scoring"):
        if key not in data:
            raise ValueError(f"Campo obrigatório ausente na calibração: {key}")
    for item in data["fruit_hsv_ranges"] + data["abnormal_hsv_ranges"]:
        for field in ("lower", "upper"):
            hsv = item[field]
            if len(hsv) != 3 or not (0 <= hsv[0] <= 179 and 0 <= hsv[1] <= 255 and 0 <= hsv[2] <= 255):
                raise ValueError(f"Faixa HSV inválida: {item}")
        if any(lo > hi for lo, hi in zip(item["lower"], item["upper"])):
            raise ValueError(f"Limites HSV invertidos: {item}")
    if data["min_fruit_area_px"] <= 0:
        raise ValueError("min_fruit_area_px deve ser positivo")
    weights = data["scoring"]["weights"]
    if abs(sum(weights.values()) - 1.0) > 1e-6:
        raise ValueError("Pesos da pontuação devem somar 1")
    approved = data["scoring"]["approved_min_score"]
    attention = data["scoring"]["attention_min_score"]
    if not 0 <= attention < approved <= 100:
        raise ValueError("Limites de classificação inválidos")
    return data


if __name__ == "__main__":
    config = load_calibration()
    print("Calibração carregada:", config["version"])
    print("Área mínima:", config["min_fruit_area_px"], "pixels")
    print("Faixas da fruta:", len(config["fruit_hsv_ranges"]))
