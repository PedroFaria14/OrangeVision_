# OrangeVision — calibração inicial (experimental)

Esta configuração é **um ponto de partida**, não uma calibração validada. Fotos reais, iluminação estável e anotações humanas são necessárias antes de confiar nas classificações.

## Instalação

1. Copie `calibration.json` para `config/calibration.json` na raiz do backend.
2. Copie `calibration.py` para `app/calibration.py`.
3. Acrescente ao `.env`:

   ```dotenv
   CALIBRATION_PATH=./config/calibration.json
   ```

4. Teste na raiz do projeto:

   ```bash
   python -m app.calibration
   ```

5. No futuro módulo de visão, use `from app.calibration import load_calibration` e `config = load_calibration()`.

## O que significam os valores

- `fruit_hsv_ranges`: intervalos HSV (OpenCV: H=0–179, S/V=0–255) para gerar máscara inicial de cor laranja.
- `abnormal_hsv_ranges`: intervalos experimentais para regiões escuras/esverdeadas, **sempre restritos à máscara da fruta**.
- `min_fruit_area_px`: área mínima do contorno em pixels; depende da distância e resolução da câmera.
- `min_abnormal_region_area_px`: remove pequenos ruídos.
- `morphology_kernel_px`: tamanho sugerido do filtro morfológico.
- `scoring.weights`: pesos de penalização de manchas, circularidade e assimetria; somam 1.
- `approved_min_score` e `attention_min_score`: limites experimentais. Exemplo: score >=75 = APROVADA; 45–74,99 = ATENCAO; <45 = REVISAR.

**Atenção:** o código incluído apenas **lê e valida** a configuração; não implementa o algoritmo OpenCV nem a fórmula de score. As faixas de cor isoladamente não bastam para detectar toda a fruta: manchas e regiões verdes podem ficar fora da máscara laranja. Na implementação real, a segmentação da fruta deve ser independente da detecção de defeitos para não excluir regiões anormais. Não é possível inferir qualidade interna ou doença apenas com esses parâmetros.

## Como calibrar com imagens reais

1. Fotografe diversas laranjas em iluminação e distância constantes, incluindo exemplos aprovados e com defeitos visuais.
2. Separe imagens para ajuste e outras para validação, sem misturar imagens da mesma fruta nos dois conjuntos.
3. Observe os valores HSV das regiões da casca e ajuste `fruit_hsv_ranges`.
4. Marque manualmente regiões anormais e ajuste `abnormal_hsv_ranges` e áreas mínimas.
5. Ajuste os pesos e limites com exemplos rotulados, documentando falsos positivos e negativos.
6. Teste em novas imagens e registre resultados antes de declarar acurácia.
