# Detector local

Artefato: OpenCV Zoo YOLOX-S 2022nov, COCO, entrada BGR 640×640,
padding superior/esquerdo 114, sem divisão por 255, saída bruta [1,8400,85].
Classe COCO orange = 49. Não é modelo de classificação de qualidade.

Fonte e licença Apache-2.0:
https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_yolox
https://github.com/opencv/opencv_zoo/blob/main/models/object_detection_yolox/LICENSE

SHA-256 fixado no ponteiro Git LFS oficial:
`c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063`
Tamanho: 35.858.002 bytes. Instalar com `python -m backend.device.model_setup`.
O ONNX já exportado evita instalar PyTorch no Raspberry. É YOLOX-S, não Nano;
latência/memória precisam ser medidas no hardware real, sem promessa de FPS.
Não distribuir o binário sem preservar a licença original e atribuição.

O layout de cor segue o ValTransform não legado do YOLOX original:
https://github.com/Megvii-BaseDetection/YOLOX/blob/main/yolox/data/data_augment.py
O demo atual do Zoo faz uma troca RGB adicional; essa troca não é usada aqui.
Esse detalhe foi conferido no ensaio local e protegido por teste de canais.
