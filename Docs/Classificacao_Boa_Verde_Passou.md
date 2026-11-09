# Classificação Boa / Verde / Passou — câmera, site e gráficos

## Como funciona

```
Câmera (Pi) ──► localiza a fruta ──► mede a casca ──► categoria sugerida ──► Web API
                 YOLOX + GrabCut      % laranja         Boa      = APROVADA       │
                 ou, se a IA não      % verde           Verde    = ATENCAO        ▼
                 confirmar, pela cor  % manchas         Passou   = REVISAR    Site: você valida
                                                                              ──► histórico e gráficos
```

1. **Localizar a fruta.** O detector YOLOX (modelo COCO) reconhece bem laranja madura, mas
   confunde laranja verde com maçã e laranja manchada com outros objetos. Com a calibração
   `color_fallback: true`, quando a IA não confirma, a fruta é localizada **pela cor** sobre
   fundo neutro. O resultado informa isso: *"Fruta localizada pela cor (detector não confirmou)"*.
2. **Medir a casca** (somente dentro da fruta): proporção laranja, verde e de manchas
   escuras/marrons, além de circularidade e assimetria.
3. **Regras explícitas** (`ripeness-rules-v1`), na ordem:
   | Regra | Categoria |
   | --- | --- |
   | verde ≥ 40% da casca | **Verde** → ATENCAO |
   | manchas ≥ 14% | **Passou** → REVISAR |
   | manchas ≤ 5%, verde ≤ 15% e laranja ≥ 60% | **Boa** → APROVADA |
   | demais casos | **Intermediária** → ATENCAO |
4. **Validação no site.** Em **Amostras**, cada foto mostra a sugestão local (e a do Gemini,
   se ativo) e os botões **Validar como Aprovada / Atenção / Revisar**. Resultados locais com
   calibração validada já entram nos gráficos; a sua decisão pode confirmar ou corrigir.

Limites: avalia só a superfície visível. Não detecta podridão interna. Laranja-pera pode
estar madura com casca esverdeada — ajuste os limiares para a variedade usada.

## Calibração

Arquivo: `backend/device/calibracao-laranja.json` (versão `laranja-cor-v1-20261108`),
gerado e conferido com as fotos rotuladas de `backend/calibration/`: **9/9 acertos**.
São poucas fotos e várias são imagens de referência; para uso real, fotografe mais frutas
na bancada e gere de novo:

```bash
python -m device.calibrate --fotos calibration --saida device/calibracao-laranja.json --marcar-validada
```

Pastas aceitas: `aprovadas`/`boa`, `atencao`/`verde`, `revisar`/`passou`. A ferramenta só
marca `validated: true` se **todas** as fotos forem classificadas como o rótulo humano.

## Ativação (ordem)

1. **Banco** — migrations 007 e 008 (aditivas, em transação). Revisar e aplicar:
   ```bash
   python -m web_api.migrate --migration 007 --apply
   python -m web_api.migrate --migration 008 --apply
   python -m web_api.diagnose_dashboard   # esperado: "status": "enabled"
   ```
2. **Web API (Render)** — `WEB_INSPECTIONS_ENABLED=true`; redeploy.
3. **Site (Vercel)** — publicar o frontend com os botões de validação.
4. **Raspberry** — copiar para o Pi os arquivos de `backend/device/` alterados:
   `calibrate.py`, `vision.py`, `segmentation.py`, `samples.py`, `camera_review.py`,
   `camera_window.py`, `__main__.py`, `calibracao-laranja.json` e `tests/test_ripeness.py`.
   No `device/.env` do Pi: `CALIBRATION_PATH=calibracao-laranja.json` e remover
   `GEMINI_API_KEY` (o Pi não usa a chave). Reiniciar a câmera.

## Roteiro da demonstração

Preparação: fundo branco ou cinza liso, luz branca constante, câmera fixa, uma fruta por
vez, inteira no quadro e com fundo ao redor. Abrir uma sessão de inspeção no site.

1. **Laranja boa** — a IA detecta, captura automática ou [C] → *Boa: casca 90% laranja…*
2. **Laranja verde** — a IA hesita; pressione [C] para capturar → *Verde: 57% verde…*
3. **Laranja com manchas** — [C] → *Passou / manchas: 16% manchas…*
4. **Site → Amostras** — mostrar a sugestão, a foto e a máscara; clicar **Validar como …**.
5. **Dashboard** — gráfico de distribuição por classificação atualizado com as três frutas.

Se aparecer *"A fruta encosta na borda"* ou *"Mais de uma fruta"*: afaste a câmera, retire
folhas/objetos coloridos do quadro e capture de novo. Essas recusas são proteções, não erros.
