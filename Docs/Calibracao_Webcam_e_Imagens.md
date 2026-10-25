# Bancada: webcam USB e base de fotos

Execute os comandos na raiz `OrangeVision`. A bancada é local: não precisa de
pareamento, não envia análises à API e não altera a sessão do operador.

Para ver as fotos no site, use a nova página privada **Amostras** e envie os
arquivos salvos com S. Esse envio é explícito pela galeria; S continua salvando
somente no dispositivo. Guia completo em `Docs/Amostras_Estados_Processamento.md`.
Amostras ficam separadas das inspeções e podem aguardar avaliação sem categoria.

## Fluxo simplificado: segurar, congelar e selecionar

Este é o modo recomendado para preparar capturas segurando a fruta na mão.
Deixe a webcam apoiada; não é preciso ajustar as barras HSV para começar.

```powershell
Set-Location "D:\Estudo_Pedro\USF\Arquitetura\Projeto\Orange\OrangeVision_"
.\backend\.venv-device\Scripts\python.exe -m backend.device.lab --camera 0
```

1. Mostre a laranja inteira, procurando não cobrir seu contorno com os dedos.
2. Clique na janela e pressione **Espaço**. O título passa a **CONGELADA**;
   agora você pode baixar a mão. A câmera permanece aberta, mas novos frames
   não substituem a foto enquanto ela estiver congelada.
3. Pressione **B** e desenhe um retângulo envolvendo a fruta inteira **com um
   pouco de fundo ao redor**, sem encostar nas bordas da foto. Enter confirma;
   Esc cancela. B também congela automaticamente a câmera se estiver ao vivo.
4. Aguarde a separação assistida e confira máscara e contorno. Se incluir a mão
   ou o fundo, use B para tentar outra seleção ou Espaço para tirar outra foto.
5. **S** salva a foto original congelada, sem desenhos. Espaço retorna ao vivo e
   descarta a seleção anterior, evitando aplicá-la a outra posição/fruta. Q sai.

O mesmo B funciona com `--images "calibracao-local\Laranja-Seleta.webp"` ou
uma pasta de fotos. N/P trocam a foto e descartam a seleção assistida anterior.
Não existe seleção ou classificação reaproveitada silenciosamente de outra foto.

Essa separação usa **GrabCut do OpenCV**, guiado pelo retângulo. Não é um modelo
treinado de reconhecimento de laranjas. A imagem de trabalho é limitada a 960 px
no maior lado; a máscara é mapeada de volta à resolução original. As métricas
assistidas são exploratórias e não devem ser comparadas como se fossem medidas
idênticas às da segmentação HSV do executor.

**Limites importantes:** mão e casca com cores semelhantes ou sobrepostas podem
continuar juntas; partes cobertas pelos dedos não são reconstruídas. Se isso
ocorrer, refaça a captura ou mude a forma de segurar. Confira visualmente o
contorno antes de usar a foto como exemplo. A seleção não prova espécie/qualidade.

No modo assistido a categoria e o score ficam indisponíveis, mesmo com uma
calibração HSV carregada: a seleção manual não valida outro algoritmo.
O/D permitem explorar as correspondências de cor dentro da região; F muda para
o ajuste HSV avançado. G grava somente faixas de cor em um rascunho não validado,
**não** guarda o retângulo como se fosse calibração geral da câmera. Se você
usou apenas B, S é o comando útil para guardar a foto para os próximos testes.

O funcionamento final sem seleção manual (chegada → estabilidade → análise →
retirada) continua sendo uma etapa de implementação e validação separada.

## Webcam USB

A bancada exige OpenCV com janelas. No ambiente da bancada, substitua a versão
headless se estiver instalada (não mantenha ambas, pois compartilham `cv2`):

```powershell
.\backend\.venv-device\Scripts\python.exe -m pip uninstall -y opencv-python-headless
.\backend\.venv-device\Scripts\python.exe -m pip install -r backend/device/requirements-lab.txt
```

`requirements-vision.txt` continua destinado ao executor sem interface gráfica.

Feche o aplicativo Câmera e outros programas que utilizem a webcam.

```powershell
.\backend\.venv-device\Scripts\python.exe -m backend.device.lab --camera 0
```

Se abrir a câmera interna, saia com Q e teste `--camera 1`.
Não é necessário alterar o `.env` para utilizar a bancada.

## Base de fotos

```powershell
.\backend\.venv-device\Scripts\python.exe -m backend.device.lab --images "D:\Fotos de laranjas"
```

Também aceita um único arquivo. Pastas são percorridas inclusive nas subpastas;
rótulos e divisões de classes não são interpretados automaticamente.
N avança e P volta. São aceitos JPG, JPEG, PNG, BMP e WebP.

## Começar pela segmentação (sem IA)

Primeiro teste com a imagem já presente no projeto:

```powershell
Set-Location "D:\Estudo_Pedro\USF\Arquitetura\Projeto\Orange\OrangeVision_"
.\backend\.venv-device\Scripts\python.exe -m backend.device.lab --images "calibracao-local\Laranja-Seleta.webp"
```

A janela mostra três painéis: **original**, **máscara da maior região** (branco
no preto) e **contorno candidato**. No modo avançado, F abre os controles HSV;
eles também são abertos ao carregar faixas F de um rascunho/calibração. Fechar
essa janela auxiliar não encerra a bancada.

1. Clique na janela da imagem e pressione **F**.
2. Na seleção, marque um trecho da casca, sem fundo, e confirme com Enter.
   Imagens grandes são reduzidas apenas para facilitar essa seleção. Os pixels
   selecionados são convertidos para as coordenadas originais.
3. Confira se a máscara cobre a fruta e exclui o fundo. Ajuste H min/max (matiz),
   S min/max (saturação) e V min/max (luminosidade) na janela HSV. Os controles
   alteram **somente a última amostra F**; amostras anteriores continuam unidas.
   Coletar F/O/D congela a webcam para que as amostras sejam tomadas na mesma foto.
4. Se faltarem partes da casca, experimente ampliar a faixa ou coletar outra
   amostra F em uma região diferente. Uma faixa muito ampla pode incluir fundo,
   folha e sombra. **R** limpa as três listas de amostras e a seleção assistida em memória para recomeçar;
   não apaga fotos nem arquivos de calibração.
5. **O** adiciona uma referência de cor laranja; **D** uma região anormal real.
   Os respectivos percentuais ficam `---` até suas amostras existirem. Ausência
   de uma amostra não significa ausência medida de defeitos.
6. **A** imprime o estado e as métricas atuais no terminal. **G** salva um novo
   JSON não validado. **Q** sai; **S** continua salvando somente a foto original,
   sem contorno, texto ou máscara sobrepostos.

Teclas maiúsculas e minúsculas são aceitas; não precisa digitar no PowerShell.
Uma faixa com mínimo maior que máximo mostra erro na prévia e não é salva por G.

Para navegar pelo conjunto atual:

```powershell
.\backend\.venv-device\Scripts\python.exe -m backend.device.lab --images "calibracao-local"
```

Use N/P para trocar de foto. Ajustes se mantêm entre as fotos, permitindo verificar
se as mesmas faixas funcionam em imagens diferentes. O programa não transforma
nomes como `atencao1.jpg` em rótulos de qualidade nem aprende com uma pasta sozinho.

Para retomar um rascunho salvo, substitua o nome abaixo pelo caminho mostrado ao
pressionar G:

```powershell
.\backend\.venv-device\Scripts\python.exe -m backend.device.lab --images "calibracao-local" --draft "calibracao-local\calibracao-SEU_ARQUIVO.json"
```

O mesmo ajuste pode ser aberto com `--camera 0 --draft "caminho-do-rascunho.json"`.
Faixas úteis em foto de estúdio podem não servir para a iluminação da webcam.

### Como interpretar a prévia

- **Aguardando ajuste:** ainda não há amostra F.
- **Região candidata:** existe um contorno compatível com as faixas selecionadas;
  não é identificação de espécie. O algoritmo escolhe a maior região: mantenha
  apenas uma fruta no enquadramento e confira visualmente o contorno.
- **Não foi possível avaliar:** ausência de contorno utilizável, faixa inválida,
  área insuficiente ou contorno tocando uma borda da imagem. Pode ser uma fruta
  cortada ou seleção indevida do fundo; não significa categoria Revisar.
- Área, circularidade e assimetria são experimentais e dependem da segmentação.
  Um contorno serrilhado pode reduzir a circularidade mesmo numa fruta redonda.
- Cor verde não é automaticamente defeito. Os percentuais são correspondências
  às amostras de cor, não diagnóstico nem prova de qualidade interna.

`--minimum-area NUMERO` permite informar um limite medido de área na resolução
original, em pixels. A prévia aceita zero para exploração e mostra candidatos
pequenos; o classificador continua exigindo área mínima positiva e calibrada.
Não redimensionamos a imagem usada nas métricas, somente sua apresentação.

Esta etapa não implementa identificação geral de laranjas, treinamento de IA,
detecção automática de estabilidade/retirada nem registro automático no site.
No Raspberry, a bancada requer sessão gráfica e OpenCV com janelas; o executor
sem interface continua usando o adaptador de câmera e o fluxo autorizado próprios.

## Coletar calibração

Use fundo contrastante, câmera fixa e iluminação uniforme. Na janela:

- **S**: salva a imagem atual em `calibracao-local`, sem sobrescrever capturas.
- **F**: selecione uma pequena região somente da fruta.
- **O**: selecione uma região de cor laranja considerada saudável.
- **D**: selecione uma região anormal real, usando exemplos com defeitos.
- Na seleção, Enter confirma e Esc cancela.
- Repita em diferentes frutas e imagens; **G** salva um novo rascunho JSON.
- **Q**: sai e libera a câmera.

As faixas HSV são estimadas pelos percentis 2 e 98 dos pixels selecionados.
Elas são sugestões: sombras, brilho e cores próximas exigem revisão. Amostras
heterogêneas, especialmente próximas ao limite circular do canal H, podem
produzir faixas excessivamente amplas. Não selecione fundo junto com a fruta.

Os rascunhos mantêm `validated: false`. Ainda é necessário medir a área mínima,
ajustar as quatro regras de score, seus pesos e limiares de classe e verificar
a segmentação e as classificações contra referências humanas. Não basta mudar
`validated` para true. Separe imagens de ajuste e teste por fruta/origem,
evitando imagens da mesma fruta nos dois grupos. Valide também fotos da webcam.
Uma base de doenças não define automaticamente aprovação comercial.

## Testar uma calibração validada

```powershell
.\backend\.venv-device\Scripts\python.exe -m backend.device.lab --images "D:\Fotos de teste" --calibration "D:\Calibracoes\calibracao.json"
.\backend\.venv-device\Scripts\python.exe -m backend.device.lab --camera 0 --calibration "D:\Calibracoes\calibracao.json"
```

A prévia mostra a categoria e o score somente com `--calibration` validada.
**A** imprime o resultado no terminal; ele não entra no histórico de inspeções.
Editar faixas, limpar amostras ou mudar a área mínima invalida a classificação
daquela prévia; é necessário revisar e validar a nova configuração antes de
classificar. `--draft` nunca habilita categorias, mesmo se o arquivo recebido
declarar `validated: true`. G sempre grava uma nova versão com `validated: false`.
No modo HSV, as duas fontes e o executor compartilham segmentação e métricas.
O modo assistido B é apenas exploratório e não habilita o classificador.
O classificador passa a recusar contornos tocando a borda (`opencv-hsv-contour-v2`),
evitando classificar fruta parcialmente enquadrada. Não foi alterada a fórmula
das métricas ou dos pesos do score. A bancada não treina um modelo de IA.

Após validar, configure `CAMERA_ADAPTER=usb`, `CAMERA_INDEX`, resolução real e
`CALIBRATION_PATH` no `.env` do executor para capturas autorizadas. Dimensões em
pixels mudam com a resolução; mantenha a montagem e a resolução da calibração.
Não use fotos antigas da base como se fossem capturas atuais de uma inspeção.

## Evidência da implementação

`Docs/segmentacao-previa-experimental.png` apresenta um ensaio com a foto
`Laranja-Seleta.webp` e faixa estimada de uma amostra da casca. É uma prévia
experimental: há partes do contorno ainda a ajustar e nenhuma categoria foi
atribuída. A abertura dos painéis e controles foi exercitada no Windows com
entrada de arquivo. Isso não equivale à validação da webcam/Raspberry físicos.

Verificação da primeira etapa de segmentação: **49 testes do executor aprovados**, lint e formatação
Python aprovados. Um ensaio de prévia percorreu os 24 arquivos atuais com a faixa
experimental da amostra: 18 produziram região candidata e 6 ficaram como não
avaliáveis, sem falha de processamento nem categoria atribuída. Esses números
descrevem estados do algoritmo; não significam identificação correta de espécie,
aprovação de frutas ou medição de acurácia. Os testes também verificam ausência
de valores fictícios, recusa de contorno cortado, correspondência das métricas
entre bancada/executor e gravação de rascunhos sem validar/sobrescrever arquivos.

Rodada de congelamento/seleção assistida: **59 testes do executor aprovados**.
Incluem preservação do mesmo frame durante Espaço/B/S, retomada da aquisição
somente ao voltar ao vivo, descarte da seleção na troca de foto, limites de
memória do GrabCut e bloqueio de categoria na seleção assistida. A prévia real
em `Docs/segmentacao-assistida-experimental.png` usa a imagem de arquivo já
existente. A abertura dos painéis e o caminho B/A/Q foram exercitados no Windows
com uma seleção automatizada. Captura física segurando a laranja e desempenho
no Raspberry continuam exigindo teste pelo operador.
