# Fotos da equipe

Adicione aqui somente retratos autorizados pelos integrantes. A página `/equipe`
identifica automaticamente as imagens pelo nome do arquivo:

| Integrante            | Nome do arquivo recomendado  |
| --------------------- | ---------------------------- |
| Felipe Kenzo          | `felipe-kenzo.webp`          |
| Kauan Fernandes       | `kauan-fernandes.webp`       |
| Marcelo Capeletto     | `marcelo-capeletto.webp`     |
| Pedro Faria           | `pedro-faria.webp`           |
| Glauber Sandi Martins | `glauber-sandi-martins.webp` |
| João Assis            | `joao-assis.webp`            |

Também são aceitos `.jpg`, `.jpeg`, `.png` e `.avif`, com extensão em minúsculas.
Mantenha somente uma imagem por integrante. Prefira retratos quadrados de cerca de
400 × 400 px, comprimidos e sem metadados privados. A foto é recortada com
`object-fit: cover`, sem alterar a proporção do card.

Os arquivos são assets públicos do site após o build. Não coloque documentos ou
arquivos privados nesta pasta. O Vite gera os URLs e inclui as fotos no build; faça
novo build/deploy depois de adicioná-las. Em desenvolvimento, reinicie o Vite caso
uma foto recém-adicionada não seja reconhecida.

Sem arquivo correspondente, o card mostra as iniciais e a indicação “Sem foto”, sem
requisitar uma imagem inexistente. Se uma imagem não carregar, o avatar mantém o
fallback de iniciais. Nenhuma foto de pessoa foi inventada ou incluída como exemplo.
